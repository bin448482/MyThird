"""
内容提取器

作为高层协调器，专注于：
- 流程管理：协调整个提取过程的执行流程
- 浏览器会话管理：处理浏览器创建、导航、会话保持
- 组件协调：统一调度PageParser、DataStorage等组件
- 结果处理：汇总、保存和管理提取结果

具体的页面解析工作委托给PageParser完成
"""

import time
import logging
import random
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

from .page_parser import PageParser
from .data_storage import DataStorage
from ..auth.browser_manager import BrowserManager
from ..auth.session_manager import SessionManager
from ..search.url_builder import SearchURLBuilder
from ..utils.behavior_simulator import BehaviorSimulator
from ..utils.fingerprint import generate_job_fingerprint, extract_job_key_info
from ..database.operations import DatabaseManager
from ..core.exceptions import ContentExtractionError


class ContentExtractor:
    """
    内容提取器 - 高层协调器
    
    职责：
    1. 流程管理 - 控制提取流程的执行顺序
    2. 浏览器会话 - 管理浏览器实例和会话状态
    3. 组件协调 - 统一调度各个功能组件
    4. 结果处理 - 汇总和保存提取结果
    
    不直接进行页面解析，而是委托给专门的组件
    """
    
    def __init__(self, config: dict, browser_manager: Optional[BrowserManager] = None):
        """
        初始化内容提取器
        
        Args:
            config: 配置字典
            browser_manager: 浏览器管理器实例，如果为None则自动创建
        """
        self.config = config
        self.mode_config = config.get('mode', {})
        self.search_config = config.get('search', {})
        
        # 组件初始化
        self.browser_manager = browser_manager or BrowserManager(config)
        self.session_manager = SessionManager(config)
        self.page_parser = PageParser(config)
        self.data_storage = DataStorage(config)
        self.url_builder = SearchURLBuilder(config)
        self.behavior_simulator = None  # 延迟初始化，需要driver实例
        
        # 添加登录模式控制器 - 新增部分
        from ..auth.login_mode_controller import LoginModeController
        self.login_controller = LoginModeController(config, self.browser_manager)
        
        self.logger = logging.getLogger(__name__)
        
        # 状态管理
        self.current_keyword = None
        self.extraction_results = []
        self.extraction_start_time = None
    
   
    
    def extract_from_keyword(self,
                           keyword: str,
                           max_results: Optional[int] = None,
                           save_results: bool = True,
                           extract_details: bool = False,
                           max_pages: Optional[int] = None,
                           max_retry_attempts: int = 2) -> List[Dict[str, Any]]:
        """
        根据关键词提取职位信息（支持登录模式和重试机制）
        
        Args:
            keyword: 搜索关键词
            max_results: 最大结果数量
            save_results: 是否保存结果
            extract_details: 是否提取详情页内容
            max_pages: 最大页数，如果为None则使用配置中的值
            max_retry_attempts: 最大重试次数
            
        Returns:
            提取的职位信息列表
        """
        retry_count = 0
        
        while retry_count <= max_retry_attempts:
            try:
                if retry_count > 0:
                    self.logger.info(f"🔄 第 {retry_count + 1} 次尝试提取关键词 '{keyword}' 的职位信息")
                else:
                    self.logger.info(f"🚀 开始提取关键词 '{keyword}' 的职位信息")
                
                # 新增：检查并启动登录模式
                if self.login_controller.is_login_mode_enabled():
                    self.logger.info("🔐 启用登录模式，开始登录工作流...")
                    login_success = self.login_controller.start_login_workflow(keyword)
                    if not login_success:
                        raise ContentExtractionError("登录失败，无法继续提取")
                    self.logger.info("✅ 登录成功，继续内容提取")
                else:
                    self.logger.info("🔓 使用无登录模式进行内容提取")
                
                # 构建搜索URL
                search_url = self.url_builder.build_search_url(keyword)
                self.logger.info(f"🔍 使用关键词 '{keyword}' 构建搜索URL: {search_url}")
                
                # 提取内容
                return self.extract_from_search_url(
                    search_url,
                    keyword=keyword,
                    max_results=max_results,
                    save_results=save_results,
                    extract_details=extract_details,
                    max_pages=max_pages
                )
                
            except ContentExtractionError as e:
                error_msg = str(e)
                if "登录状态丢失" in error_msg and retry_count < max_retry_attempts:
                    retry_count += 1
                    self.logger.warning(f"⚠️ 登录状态丢失，准备第 {retry_count + 1} 次重试...")
                    
                    # 清理当前状态，准备重试
                    try:
                        # 重置浏览器会话
                        if hasattr(self, 'browser_manager') and self.browser_manager:
                            self.browser_manager.quit_driver()
                            time.sleep(2)  # 等待浏览器完全关闭
                    except:
                        pass
                    
                    continue
                else:
                    self.logger.error(f"❌ 基于关键词的内容提取失败: {e}")
                    raise
            except Exception as e:
                self.logger.error(f"❌ 基于关键词的内容提取失败: {e}")
                raise ContentExtractionError(f"基于关键词的内容提取失败: {e}")
        
        # 如果所有重试都失败
        raise ContentExtractionError(f"经过 {max_retry_attempts + 1} 次尝试后仍然失败")
    
    def extract_job_details(self, job_urls: List[str]) -> List[Dict[str, Any]]:
        """
        提取职位详情信息（带指纹验证去重）
        
        Args:
            job_urls: 职位详情页URL列表
            
        Returns:
            职位详情信息列表
        """
        try:
            self.logger.info(f"📄 开始提取 {len(job_urls)} 个职位的详情信息")
            
            # 预先过滤已存在的职位URL（基于指纹验证）
            filtered_urls = self._filter_existing_job_urls(job_urls)
            skipped_count = len(job_urls) - len(filtered_urls)
            
            if skipped_count > 0:
                self.logger.info(f"🔍 指纹验证完成：跳过 {skipped_count} 个已存在的职位，待提取 {len(filtered_urls)} 个")
            
            if not filtered_urls:
                self.logger.info("✅ 所有职位都已存在，无需重复提取")
                return []
            
            driver = self._prepare_browser()
            details = []
            
            # 随机打乱URL顺序，避免按顺序访问的模式
            shuffled_urls = filtered_urls.copy()
            random.shuffle(shuffled_urls)
            
            for i, job_url in enumerate(shuffled_urls, 1):
                try:
                    self.logger.info(f"📝 提取职位详情 {i}/{len(shuffled_urls)}: {job_url}")
                    
                    # 详情页：延长等待时间，避免反爬检测 - COMMENTED FOR SPEED
                    # if self.behavior_simulator:
                    #     self.behavior_simulator.random_delay(1.0, 5.0)  # 详情页延长到2-5秒
                    # else:
                    #     time.sleep(random.uniform(3.0, 8.0))  # 详情页延长到3-8秒
                    
                    # 使用简化的详情页解析
                    detail = self._extract_job_detail_simplified(driver, job_url)
                    if detail:
                        details.append(detail)
                        
                        # 保存单个职位详情到数据库（替代JSON文件）
                        success = self.data_storage.save_job_detail(detail, job_url, self.current_keyword)
                        if success:
                            self.logger.debug(f"💾 职位详情已保存到数据库: {detail.get('title', '')}")
                        
                        # 详情页：增加阅读时间模拟 - COMMENTED FOR SPEED
                        if self.behavior_simulator and random.random() < 0.6:  # 增加到60%概率模拟阅读
                            self.behavior_simulator.random_delay(1.0, 3.0)  # 延长阅读时间
                    
                    # 详情页：适当增加休息时间 - COMMENTED FOR SPEED
                    # if i % random.randint(5, 8) == 0:  # 详情页休息频率适中
                    #     rest_time = random.uniform(4.0, 8.0)  # 详情页休息时间延长
                    #     self.logger.info(f"⏳ 模拟用户休息 {rest_time:.1f} 秒...")
                    #     time.sleep(rest_time)
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ 提取职位详情失败 {job_url}: {e}")
                    # 详情页失败后延长等待时间 - COMMENTED FOR SPEED
                    # time.sleep(random.uniform(10.0, 25.0))  # 从5-15秒延长到10-25秒
                    continue
            
            self.logger.info(f"✅ 职位详情提取完成，共提取 {len(details)} 个详情，跳过重复 {skipped_count} 个")
            return details
            
        except Exception as e:
            self.logger.error(f"❌ 职位详情提取失败: {e}")
            raise ContentExtractionError(f"职位详情提取失败: {e}")
    
    def _extract_job_detail_simplified(self, driver, job_url: str) -> Optional[Dict[str, Any]]:
        """
        简化的职位详情提取方法（带指纹验证）
        
        Args:
            driver: WebDriver实例
            job_url: 职位详情URL
            
        Returns:
            职位详情数据
        """
        try:
            # 直接导航，减少复杂的模拟
            driver.get(job_url)
            
            # 详情页：延长等待时间 - COMMENTED FOR SPEED
            # time.sleep(random.uniform(2.0, 4.0))  # 从1-2.5秒延长到2-4秒
            
            # 检查是否被重定向或阻止
            current_url = driver.current_url
            if 'error' in current_url.lower() or 'block' in current_url.lower() or 'captcha' in current_url.lower():
                self.logger.warning(f"检测到可能的反爬页面: {current_url}")
                return None
            
            # 简化的页面交互：只做基本滚动
            if self.behavior_simulator and random.random() < 0.5:  # 50%概率进行简单滚动
                self.behavior_simulator.simulate_scroll('down', random.randint(300, 500))
                # time.sleep(random.uniform(0.5, 1.0))  # COMMENTED FOR SPEED
                driver.execute_script("window.scrollTo(0, 0);")
            
            # 解析页面内容
            detail_data = self.page_parser.parse_job_detail(driver, job_url)
            
            if detail_data:
                # 为详情数据生成指纹
                job_fingerprint = generate_job_fingerprint(
                    detail_data.get('title', ''),
                    detail_data.get('company', ''),
                    detail_data.get('salary', ''),
                    detail_data.get('location', '')
                )
                detail_data['job_fingerprint'] = job_fingerprint
                
                # 再次检查指纹是否已存在（双重保险）
                if self.data_storage.check_job_fingerprint_exists(
                    detail_data.get('title', ''),
                    detail_data.get('company', ''),
                    detail_data.get('salary', ''),
                    detail_data.get('location', '')
                ):
                    self.logger.debug(f"职位详情已存在（指纹验证），跳过: {detail_data.get('title', '')}")
                    return None
            
            return detail_data
            
        except Exception as e:
            self.logger.error(f"简化提取职位详情失败: {e}")
            return None
    
        
    
    def _merge_job_data(self,
                       basic_jobs: List[Dict[str, Any]],
                       url_jobs: List[Dict[str, Any]],
                       detail_jobs: List[Dict[str, Any]]) -> None:
        """
        合并职位基本信息、URL信息和详情信息，并更新数据库
        
        Args:
            basic_jobs: 基本职位信息列表
            url_jobs: URL信息列表
            detail_jobs: 详情信息列表
        """
        try:
            self.logger.info(f"🔄 开始合并数据: 基本信息{len(basic_jobs)}个, URL信息{len(url_jobs)}个, 详情信息{len(detail_jobs)}个")
            
            # 创建更精确的映射关系
            # 使用多种匹配策略：标题匹配、标题+公司匹配、索引匹配
            url_map_by_title = {item['title']: item for item in url_jobs}
            url_map_by_index = {item.get('index', i+1): item for i, item in enumerate(url_jobs)}
            detail_map = {item['url']: item for item in detail_jobs if item.get('url')}
            
            # 合并数据并更新数据库
            updated_count = 0
            matched_count = 0
            
            for i, job in enumerate(basic_jobs):
                job_title = job.get('title', '').strip()
                job_company = job.get('company', '').strip()
                
                self.logger.debug(f"🔍 处理职位 {i+1}: {job_title} @ {job_company}")
                
                # 尝试多种匹配策略找到对应的URL信息
                url_info = None
                match_method = ""
                
                # 策略1: 精确标题匹配
                if job_title in url_map_by_title:
                    url_info = url_map_by_title[job_title]
                    match_method = "标题匹配"
                
                # 策略2: 索引匹配（基于提取顺序）
                elif (i + 1) in url_map_by_index:
                    url_info = url_map_by_index[i + 1]
                    match_method = "索引匹配"
                
                # 策略3: 模糊标题匹配（处理标题略有差异的情况）
                else:
                    for url_title, url_data in url_map_by_title.items():
                        if self._titles_similar(job_title, url_title):
                            url_info = url_data
                            match_method = "模糊匹配"
                            break
                
                if url_info:
                    matched_count += 1
                    detail_url = url_info.get('detail_url', '')
                    
                    self.logger.info(f"✅ 匹配成功 ({match_method}): {job_title} -> {detail_url}")
                    
                    # 更新job对象中的URL信息
                    job['detail_url'] = detail_url
                    job['url'] = detail_url  # 重要：同时更新url字段
                    job['url_extracted_at'] = url_info.get('extracted_at', '')
                    
                    # 更新数据库中的URL
                    if detail_url:
                        success = self.data_storage.update_job_with_detail_url(
                            job_title, job_company, detail_url
                        )
                        if success:
                            updated_count += 1
                else:
                    self.logger.warning(f"⚠️ 未找到匹配的URL信息: {job_title} @ {job_company}")
                
                # 添加详情信息
                detail_url = job.get('detail_url', '') or job.get('url', '')
                if detail_url and detail_url in detail_map:
                    detail_info = detail_map[detail_url]
                    job.update({
                        'description': detail_info.get('description', ''),
                        'requirements': detail_info.get('requirements', ''),
                        'company_info': detail_info.get('company_info', ''),
                        'benefits': detail_info.get('benefits', ''),
                        'detail_extracted_at': detail_info.get('extracted_at', '')
                    })
                    self.logger.debug(f"📄 添加详情信息: {job_title}")
                
                # 标记为包含详情信息
                job['has_details'] = bool(detail_url and detail_url in detail_map)
            
            self.logger.info(f"✅ 数据合并完成:")
            self.logger.info(f"   - 成功匹配URL: {matched_count}/{len(basic_jobs)} 个职位")
            self.logger.info(f"   - 包含详情信息: {len([j for j in basic_jobs if j.get('has_details')])} 个职位")
            self.logger.info(f"   - 数据库URL更新: {updated_count} 个职位")
            
        except Exception as e:
            self.logger.error(f"❌ 合并职位数据失败: {e}")
            import traceback
            self.logger.error(f"错误详情: {traceback.format_exc()}")
    
    def _titles_similar(self, title1: str, title2: str, threshold: float = 0.8) -> bool:
        """
        检查两个职位标题是否相似
        
        Args:
            title1: 第一个标题
            title2: 第二个标题
            threshold: 相似度阈值
            
        Returns:
            是否相似
        """
        try:
            if not title1 or not title2:
                return False
            
            # 简单的相似度检查：去除空格后比较
            clean_title1 = title1.strip().lower().replace(' ', '')
            clean_title2 = title2.strip().lower().replace(' ', '')
            
            # 完全匹配
            if clean_title1 == clean_title2:
                return True
            
            # 包含关系检查
            if clean_title1 in clean_title2 or clean_title2 in clean_title1:
                return True
            
            # 简单的编辑距离检查
            def levenshtein_ratio(s1, s2):
                if len(s1) == 0:
                    return len(s2)
                if len(s2) == 0:
                    return len(s1)
                
                # 创建矩阵
                matrix = [[0] * (len(s2) + 1) for _ in range(len(s1) + 1)]
                
                # 初始化第一行和第一列
                for i in range(len(s1) + 1):
                    matrix[i][0] = i
                for j in range(len(s2) + 1):
                    matrix[0][j] = j
                
                # 填充矩阵
                for i in range(1, len(s1) + 1):
                    for j in range(1, len(s2) + 1):
                        if s1[i-1] == s2[j-1]:
                            cost = 0
                        else:
                            cost = 1
                        matrix[i][j] = min(
                            matrix[i-1][j] + 1,      # 删除
                            matrix[i][j-1] + 1,      # 插入
                            matrix[i-1][j-1] + cost  # 替换
                        )
                
                # 计算相似度
                max_len = max(len(s1), len(s2))
                if max_len == 0:
                    return 1.0
                return 1.0 - (matrix[len(s1)][len(s2)] / max_len)
            
            similarity = levenshtein_ratio(clean_title1, clean_title2)
            return similarity >= threshold
            
        except Exception as e:
            self.logger.debug(f"标题相似度检查失败: {e}")
            return False
    
    
    def _prepare_browser(self):
        """
        准备浏览器
        
        Returns:
            WebDriver实例
        """
        try:
            # 检查是否需要使用保存的会话
            if self.mode_config.get('use_saved_session', False):
                if self._try_load_session():
                    driver = self.browser_manager.get_driver()
                    if driver and self.browser_manager.is_driver_alive():
                        self.logger.info("✅ 使用已有的浏览器会话")
                        # 初始化行为模拟器
                        if not self.behavior_simulator:
                            self.behavior_simulator = BehaviorSimulator(driver, self.config)
                        return driver
            
            # 创建新的浏览器实例
            driver = self.browser_manager.create_driver()
            
            # 初始化行为模拟器
            self.behavior_simulator = BehaviorSimulator(driver, self.config)
            
            # 如果配置了跳过登录，直接返回
            if self.mode_config.get('skip_login', False):
                self.logger.info("🔄 开发模式：跳过登录检查")
                return driver
            
            # 尝试加载会话
            if self.mode_config.get('use_saved_session', True):
                self._try_load_session()
            
            return driver
            
        except Exception as e:
            self.logger.error(f"❌ 准备浏览器失败: {e}")
            raise ContentExtractionError(f"准备浏览器失败: {e}")
    
    def _try_load_session(self) -> bool:
        """
        尝试加载保存的会话
        
        Returns:
            是否加载成功
        """
        try:
            session_file = self.mode_config.get('session_file')
            session_info = self.session_manager.get_session_info(session_file)
            
            if not session_info or session_info.get('is_expired', True):
                self.logger.info("没有有效的保存会话")
                return False
            
            driver = self.browser_manager.get_driver()
            if not driver:
                driver = self.browser_manager.create_driver()
            
            if self.session_manager.load_session(driver, session_file):
                if self.session_manager.is_session_valid(driver, self.current_keyword or "test"):
                    self.logger.info("✅ 会话加载成功")
                    return True
                else:
                    self.logger.warning("⚠️ 会话无效")
                    return False
            
            return False
            
        except Exception as e:
            self.logger.warning(f"加载会话失败: {e}")
            return False
    
    def _navigate_to_page(self, driver, url: str) -> None:
        """
        导航到指定页面（优化版本）
        
        Args:
            driver: WebDriver实例
            url: 目标URL
        """
        try:
            self.logger.info(f"🌐 导航到页面: {url}")
            
            # 检查是否为开发/调试模式
            is_debug_mode = self.mode_config.get('development', False) or self.mode_config.get('debug', False)
            
            # 根据模式选择导航策略
            if is_debug_mode:
                # 调试模式：快速导航，最小等待
                self.logger.info("🔧 调试模式：使用快速导航")
                driver.get(url)
                
                # 最小等待时间
                wait = self.browser_manager.create_wait(5)
                wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                
                # 调试模式不需要额外等待 - COMMENTED FOR SPEED
                # time.sleep(0.2)
                
            elif self.behavior_simulator and random.random() < 0.2:  # 只有20%概率使用复杂导航
                # 生产模式：偶尔使用自然导航
                success = self.behavior_simulator.natural_navigate_to_url(url)
                if not success:
                    self.logger.warning("自然导航失败，使用标准导航")
                    driver.get(url)
                    wait = self.browser_manager.create_wait(8)
                    wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                    # time.sleep(random.uniform(0.5, 1.0))  # COMMENTED FOR SPEED
            else:
                # 标准导航方式
                driver.get(url)
                
                # 减少等待时间
                wait = self.browser_manager.create_wait(8)  # 从20秒减少到8秒
                wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                
                # 大幅减少额外等待时间 - COMMENTED FOR SPEED
                # time.sleep(random.uniform(0.3, 1.0))  # 从3秒减少到0.3-1秒
            
            self.logger.info("✅ 页面导航完成")
            
        except Exception as e:
            self.logger.error(f"❌ 页面导航失败: {e}")
            raise ContentExtractionError(f"页面导航失败: {e}")
    
    def _click_salary_filter(self, driver) -> None:
        """
        点击薪资过滤器（3-4万）
        
        Args:
            driver: WebDriver实例
        """
        try:
            self.logger.info("🎯 开始点击薪资过滤器（3-4万）")
            
            # 🐛 DEBUG: 记录调用薪资过滤器的上下文
            self.logger.warning("🐛 DEBUG: _click_salary_filter 被调用")
            self.logger.warning(f"🐛 DEBUG: 当前URL: {driver.current_url}")
            
            # 等待页面稳定
            time.sleep(2)
            
            # 多种选择器策略来查找薪资过滤器
            salary_filter_selectors = [
                'a[data-v-1cfe2d3c].ch span[data-v-1cfe2d3c]:contains("3-4万")',  # 精确匹配
                'a.ch span:contains("3-4万")',  # 简化匹配
                'a[class*="ch"] span:contains("3-4万")',  # 部分类名匹配
                'a span:contains("3-4万")',  # 最宽泛匹配
                'span:contains("3-4万")',  # 直接匹配span
                '*[data-v-1cfe2d3c]:contains("3-4万")'  # 任何包含data-v属性的元素
            ]
            
            # 使用JavaScript查找包含"3-4万"文本的元素
            salary_element = None
            
            # 方法1: 使用JavaScript查找文本内容
            try:
                salary_element = driver.execute_script("""
                    // 查找所有包含"3-4万"文本的元素
                    var elements = document.querySelectorAll('*');
                    for (var i = 0; i < elements.length; i++) {
                        var element = elements[i];
                        if (element.textContent && element.textContent.includes('3-4万')) {
                            // 优先选择链接元素
                            if (element.tagName === 'A' || element.closest('a')) {
                                return element.tagName === 'A' ? element : element.closest('a');
                            }
                        }
                    }
                    
                    // 如果没找到链接，返回第一个包含文本的元素
                    for (var i = 0; i < elements.length; i++) {
                        var element = elements[i];
                        if (element.textContent && element.textContent.includes('3-4万')) {
                            return element;
                        }
                    }
                    return null;
                """)
                
                if salary_element:
                    self.logger.info("✅ 通过JavaScript找到薪资过滤器元素")
                
            except Exception as e:
                self.logger.debug(f"JavaScript查找失败: {e}")
            
            # 方法2: 使用XPath查找
            if not salary_element:
                try:
                    from selenium.webdriver.common.by import By
                    xpath_selectors = [
                        "//a[contains(@class, 'ch')]//span[contains(text(), '3-4万')]",
                        "//a//span[contains(text(), '3-4万')]",
                        "//span[contains(text(), '3-4万')]",
                        "//*[contains(text(), '3-4万')]"
                    ]
                    
                    for xpath in xpath_selectors:
                        try:
                            elements = driver.find_elements(By.XPATH, xpath)
                            if elements:
                                salary_element = elements[0]
                                self.logger.info(f"✅ 通过XPath找到薪资过滤器元素: {xpath}")
                                break
                        except:
                            continue
                            
                except Exception as e:
                    self.logger.debug(f"XPath查找失败: {e}")
            
            # 如果找到元素，尝试点击
            if salary_element:
                try:
                    # 滚动到元素位置
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", salary_element)
                    time.sleep(1)
                    
                    # 尝试多种点击方式
                    click_success = False
                    
                    # 方式1: 标准点击
                    try:
                        salary_element.click()
                        click_success = True
                        self.logger.info("✅ 标准点击薪资过滤器成功")
                    except Exception as e:
                        self.logger.debug(f"标准点击失败: {e}")
                    
                    # 方式2: JavaScript点击
                    if not click_success:
                        try:
                            driver.execute_script("arguments[0].click();", salary_element)
                            click_success = True
                            self.logger.info("✅ JavaScript点击薪资过滤器成功")
                        except Exception as e:
                            self.logger.debug(f"JavaScript点击失败: {e}")
                    
                    # 方式3: ActionChains点击
                    if not click_success:
                        try:
                            from selenium.webdriver.common.action_chains import ActionChains
                            ActionChains(driver).click(salary_element).perform()
                            click_success = True
                            self.logger.info("✅ ActionChains点击薪资过滤器成功")
                        except Exception as e:
                            self.logger.debug(f"ActionChains点击失败: {e}")
                    
                    if click_success:
                        # 等待过滤器生效
                        time.sleep(3)
                        self.logger.info("🎯 薪资过滤器点击完成，等待页面更新")
                    else:
                        self.logger.warning("⚠️ 所有点击方式都失败，但继续执行")
                        
                except Exception as e:
                    self.logger.warning(f"⚠️ 点击薪资过滤器时出错: {e}")
            else:
                self.logger.warning("⚠️ 未找到薪资过滤器元素，跳过点击")
                # 打印页面信息用于调试
                try:
                    page_source_snippet = driver.page_source[:1000] if len(driver.page_source) > 1000 else driver.page_source
                    self.logger.debug(f"页面源码片段: {page_source_snippet}")
                except:
                    pass
            
        except Exception as e:
            self.logger.error(f"❌ 点击薪资过滤器失败: {e}")
            # 不抛出异常，继续执行后续流程
    
    def _extract_keyword_from_url(self, url: str) -> str:
        """
        从URL中提取关键词
        
        Args:
            url: 搜索URL
            
        Returns:
            提取的关键词
        """
        try:
            from urllib.parse import parse_qs, urlparse
            
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            
            # 尝试从不同的参数中提取关键词
            keyword_params = ['keyword', 'kw', 'q', 'search']
            
            for param in keyword_params:
                if param in query_params and query_params[param]:
                    return query_params[param][0]
            
            # 如果无法提取，返回默认值
            return "未知关键词"
            
        except Exception as e:
            self.logger.warning(f"从URL提取关键词失败: {e}")
            return "未知关键词"
    
    def _save_extraction_results(self, results: List[Dict[str, Any]]) -> None:
        """
        保存提取结果
        
        Args:
            results: 提取结果列表
        """
        try:
            if not results:
                return
            
            # 保存搜索结果
            saved_file = self.data_storage.save_search_results(
                results, 
                self.current_keyword,
                format='both'  # 同时保存JSON和CSV
            )
            
            # 保存详细信息到数据库
            self.data_storage.save_job_details(results, self.current_keyword)
            
            if saved_file:
                self.logger.info(f"💾 提取结果已保存: {saved_file}")
            
        except Exception as e:
            self.logger.error(f"❌ 保存提取结果失败: {e}")
    
    def extract_multiple_keywords(self,
                                keywords: List[str],
                                max_results_per_keyword: Optional[int] = None,
                                delay_between_keywords: int = 5,
                                max_pages_per_keyword: Optional[int] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        批量提取多个关键词的职位信息（支持多页）
        
        Args:
            keywords: 关键词列表
            max_results_per_keyword: 每个关键词的最大结果数
            delay_between_keywords: 关键词之间的延迟时间（秒）
            max_pages_per_keyword: 每个关键词的最大页数
            
        Returns:
            按关键词分组的提取结果
        """
        try:
            self.logger.info(f"🔍 开始批量提取 {len(keywords)} 个关键词的职位信息")
            
            all_results = {}
            
            for i, keyword in enumerate(keywords, 1):
                try:
                    self.logger.info(f"📊 处理关键词 {i}/{len(keywords)}: {keyword}")
                    
                    results = self.extract_from_keyword(
                        keyword,
                        max_results=max_results_per_keyword,
                        save_results=True,
                        max_pages=max_pages_per_keyword
                    )
                    
                    all_results[keyword] = results
                    
                    # 添加延迟（除了最后一个关键词）
                    if i < len(keywords):
                        self.logger.info(f"⏳ 等待 {delay_between_keywords} 秒后处理下一个关键词... - COMMENTED FOR SPEED")
                        # time.sleep(delay_between_keywords)
                    
                except Exception as e:
                    self.logger.error(f"❌ 处理关键词 '{keyword}' 失败: {e}")
                    all_results[keyword] = []
                    continue
            
            # 统计总结果
            total_results = sum(len(results) for results in all_results.values())
            self.logger.info(f"✅ 批量提取完成，共提取 {total_results} 个职位")
            
            return all_results
            
        except Exception as e:
            self.logger.error(f"❌ 批量提取失败: {e}")
            raise ContentExtractionError(f"批量提取失败: {e}")
    
    def get_extraction_summary(self) -> Dict[str, Any]:
        """
        获取提取摘要信息
        
        Returns:
            提取摘要字典
        """
        elapsed_time = None
        if self.extraction_start_time:
            elapsed_time = time.time() - self.extraction_start_time
        
        return {
            'keyword': self.current_keyword,
            'total_results': len(self.extraction_results),
            'extraction_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'elapsed_seconds': elapsed_time,
            'browser_alive': self.browser_manager.is_driver_alive(),
            'config_mode': {
                'skip_login': self.mode_config.get('skip_login', False),
                'use_saved_session': self.mode_config.get('use_saved_session', False),
                'development': self.mode_config.get('development', False)
            }
        }
    
    def get_extraction_results(self) -> List[Dict[str, Any]]:
        """
        获取当前提取结果
        
        Returns:
            提取结果列表
        """
        return self.extraction_results.copy()
    
    def get_login_status_summary(self) -> Dict[str, Any]:
        """
        获取登录状态摘要信息
        
        Returns:
            登录状态摘要字典
        """
        try:
            # 获取基本提取摘要
            basic_summary = self.get_extraction_summary()
            
            # 获取登录状态信息
            login_status = self.login_controller.get_login_status_summary()
            
            # 合并信息
            return {
                **basic_summary,
                'login_status': login_status,
                'extraction_mode': 'login_mode' if login_status.get('login_mode_enabled', False) else 'anonymous_mode'
            }
            
        except Exception as e:
            self.logger.error(f"获取登录状态摘要失败: {e}")
            return self.get_extraction_summary()
    
    def close(self) -> None:
        """关闭内容提取器，清理资源"""
        try:
            self.logger.info("🧹 关闭内容提取器")
            
            # 关闭登录控制器
            if hasattr(self, 'login_controller') and self.login_controller:
                self.login_controller.close()
            
            # 如果配置了重用会话，不关闭浏览器
            if not self.mode_config.get('close_on_complete', True):
                self.logger.info("💡 配置为保持浏览器会话，不关闭浏览器")
                return
            
            # 关闭浏览器
            self.browser_manager.quit_driver()
            
            self.logger.info("✅ 内容提取器已关闭")
            
        except Exception as e:
            self.logger.error(f"❌ 关闭内容提取器时出错: {e}")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
    
    
    def _filter_duplicate_jobs(self, job_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤重复职位（基于指纹）
        
        Args:
            job_results: 职位结果列表
            
        Returns:
            去重后的职位列表
        """
        try:
            if not job_results:
                return []
            
            # 提取所有指纹
            fingerprints = [job.get('job_fingerprint') for job in job_results if job.get('job_fingerprint')]
            
            if not fingerprints:
                self.logger.warning("职位列表中没有指纹信息，跳过去重检查")
                return job_results
            
            # 批量检查指纹是否存在
            db_manager = DatabaseManager(self.data_storage.db_path)
            existing_fingerprints = db_manager.batch_check_fingerprints(fingerprints)
            
            # 过滤重复职位
            filtered_results = []
            for job in job_results:
                fingerprint = job.get('job_fingerprint')
                if fingerprint and existing_fingerprints.get(fingerprint, False):
                    self.logger.debug(f"跳过重复职位: {job.get('title', '')} - {job.get('company', '')}")
                    continue
                filtered_results.append(job)
            
            return filtered_results
            
        except Exception as e:
            self.logger.error(f"过滤重复职位失败: {e}")
            return job_results
    
    def _filter_existing_job_urls(self, job_urls: List[str]) -> List[str]:
        """
        过滤已存在的职位URL（基于指纹验证）
        
        Args:
            job_urls: 职位URL列表
            
        Returns:
            过滤后的URL列表
        """
        try:
            if not job_urls:
                return []
            
            filtered_urls = []
            
            for job_url in job_urls:
                try:
                    # 从URL中尝试提取基本信息进行指纹验证
                    # 这里我们需要先访问页面获取基本信息，或者使用其他方式
                    # 为了简化，我们可以检查URL是否已经在数据库中
                    
                    # 生成基于URL的临时job_id来检查
                    temp_job_id = self.data_storage._generate_job_id(job_url, "", "")
                    
                    # 使用DatabaseManager检查是否存在
                    db_manager = DatabaseManager(self.data_storage.db_path)
                    if not db_manager.job_exists(temp_job_id):
                        filtered_urls.append(job_url)
                    else:
                        self.logger.debug(f"跳过已存在的职位URL: {job_url}")
                        
                except Exception as e:
                    self.logger.warning(f"检查职位URL时出错，将其包含在提取列表中: {job_url} - {e}")
                    filtered_urls.append(job_url)  # 出错时保守处理，包含该URL
            
            return filtered_urls
            
        except Exception as e:
            self.logger.error(f"过滤职位URL失败: {e}")
            return job_urls  # 出错时返回原始列表
    
    def _save_extraction_results(self, results: List[Dict[str, Any]]) -> None:
        """
        保存提取结果（修复版本，确保URL和基本信息一起保存）
        
        Args:
            results: 提取结果列表
        """
        try:
            if not results:
                return
            
            self.logger.info(f"💾 开始保存提取结果: {len(results)} 条记录")
            
            # 验证数据完整性
            complete_jobs = []
            incomplete_jobs = []
            
            for job in results:
                title = job.get('title', '').strip()
                company = job.get('company', '').strip()
                url = job.get('url', '').strip()
                
                if title and company:
                    complete_jobs.append(job)
                    if url:
                        self.logger.debug(f"✅ 完整职位: {title} @ {company} - {url[:50]}...")
                    else:
                        self.logger.debug(f"⚠️ 缺少URL: {title} @ {company}")
                else:
                    incomplete_jobs.append(job)
                    self.logger.warning(f"❌ 不完整职位: title='{title}', company='{company}'")
            
            self.logger.info(f"📊 数据验证: 完整{len(complete_jobs)}个, 不完整{len(incomplete_jobs)}个")
            
            # 主要保存到数据库
            database_config = self.config.get('database', {})
            if database_config.get('enabled', True):
                # 只保存完整的职位数据
                if complete_jobs:
                    self.data_storage._save_to_database(complete_jobs, self.current_keyword)
                    self.logger.info(f"💾 完整职位已保存到数据库: {len(complete_jobs)} 条记录")
                
                # 对于不完整的数据，记录但不保存
                if incomplete_jobs:
                    self.logger.warning(f"⚠️ 跳过不完整的职位数据: {len(incomplete_jobs)} 条")
            
            # 可选：仍然保存文件作为备份（如果配置启用）
            backup_files = self.config.get('backup', {}).get('save_files', False)
            if backup_files and complete_jobs:
                saved_file = self.data_storage.save_search_results(
                    complete_jobs,
                    self.current_keyword,
                    format='json'  # 只保存JSON作为备份
                )
                if saved_file:
                    self.logger.info(f"📁 备份文件已保存: {saved_file}")
            
        except Exception as e:
            self.logger.error(f"❌ 保存提取结果失败: {e}")
            import traceback
            self.logger.error(f"错误详情: {traceback.format_exc()}")
    
    def get_deduplication_summary(self) -> Dict[str, Any]:
        """
        获取去重摘要信息
        
        Returns:
            去重摘要字典
        """
        try:
            # 获取去重统计
            dedup_stats = self.data_storage.get_deduplication_stats()
            
            # 获取基本提取摘要
            basic_summary = self.get_extraction_summary()
            
            # 合并信息
            return {
                **basic_summary,
                'deduplication': dedup_stats,
                'efficiency_improvement': {
                    'duplicate_rate': dedup_stats.get('deduplication_rate', 0),
                    'unique_jobs': dedup_stats.get('unique_fingerprints', 0),
                    'total_processed': dedup_stats.get('total_jobs', 0)
                }
            }
            
        except Exception as e:
            self.logger.error(f"获取去重摘要失败: {e}")
            return self.get_extraction_summary()
    
    def _filter_new_jobs_by_fingerprint_with_elements(self, page_jobs: List[Dict[str, Any]], job_elements: List) -> List[Dict[str, Any]]:
        """
        通过指纹过滤出新职位，同时保留对应的页面元素
        
        Args:
            page_jobs: 页面职位列表
            job_elements: 对应的页面DOM元素列表
            
        Returns:
            包含职位数据和对应元素的列表，格式: [{'job_data': job, 'element': element}, ...]
        """
        try:
            if not page_jobs:
                return []
            
            # 确保职位数据和元素数量一致
            if len(page_jobs) != len(job_elements):
                self.logger.warning(f"⚠️ 职位数据({len(page_jobs)})和页面元素({len(job_elements)})数量不匹配")
                min_count = min(len(page_jobs), len(job_elements))
                page_jobs = page_jobs[:min_count]
                job_elements = job_elements[:min_count]
            
            # 为每个职位生成指纹
            for job in page_jobs:
                if not job.get('job_fingerprint'):
                    job['job_fingerprint'] = generate_job_fingerprint(
                        job.get('title', ''),
                        job.get('company', ''),
                        job.get('salary', ''),
                        job.get('location', '')
                    )
            
            # 提取所有指纹
            fingerprints = [job['job_fingerprint'] for job in page_jobs]
            
            # 批量检查指纹是否存在
            db_manager = DatabaseManager(self.data_storage.db_path)
            existing_fingerprints = db_manager.batch_check_fingerprints(fingerprints)
            
            # 过滤出新职位，同时保留对应的页面元素
            new_jobs_with_elements = []
            for i, job in enumerate(page_jobs):
                fingerprint = job['job_fingerprint']
                if not existing_fingerprints.get(fingerprint, False):
                    new_jobs_with_elements.append({
                        'job_data': job,
                        'element': job_elements[i]
                    })
                else:
                    self.logger.debug(f"跳过已存在职位: {job.get('title', '')} - {job.get('company', '')}")
            
            self.logger.info(f"🔍 指纹过滤: 总数 {len(page_jobs)}, 新职位 {len(new_jobs_with_elements)}, 重复 {len(page_jobs) - len(new_jobs_with_elements)}")
            return new_jobs_with_elements
            
        except Exception as e:
            self.logger.error(f"指纹过滤失败: {e}")
            # 出错时返回原始列表，尽量保持数据和元素的对应关系
            fallback_result = []
            min_count = min(len(page_jobs), len(job_elements))
            for i in range(min_count):
                fallback_result.append({
                    'job_data': page_jobs[i],
                    'element': job_elements[i]
                })
            return fallback_result
    
    def _extract_new_jobs_details_immediately(self, driver, new_jobs_with_elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        立即提取新职位的详情信息（增强登录状态保护）
        
        Args:
            driver: WebDriver实例
            new_jobs_with_elements: 包含职位数据和对应页面元素的列表
                                   格式: [{'job_data': job, 'element': element}, ...]
            
        Returns:
            包含详情信息的完整职位列表
        """
        try:
            if not new_jobs_with_elements:
                return []
            
            # 需要导入selenium相关模块
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.action_chains import ActionChains
            
            self.logger.info(f"📄 开始立即提取 {len(new_jobs_with_elements)} 个新职位的详情信息")
            results = []
            
            # 处理每个新职位（现在有了正确的数据和元素对应关系）
            for job_index, job_item in enumerate(new_jobs_with_elements):
                job = job_item['job_data']
                job_element = job_item['element']
                job_title = job.get('title', '').strip()
                
                self.logger.info(f"🎯 处理第 {job_index+1}/{len(new_jobs_with_elements)} 个新职位: {job_title}")
                
                try:
                    # 移除详情页登录状态检查，因为有重复检测机制保护
                    # 记录当前窗口句柄
                    original_windows = driver.window_handles
                    
                    # 模拟人类滚动行为
                    self._simulate_scroll_to_element(driver, job_element)
                    
                    # 等待元素稳定
                    time.sleep(0.5)
                    
                    # 检查元素是否可点击
                    if not self._is_element_clickable(driver, job_element):
                        failed_job_info = {
                            'title': job.get('title', ''),
                            'company': job.get('company', ''),
                            'location': job.get('location', ''),
                            'salary': job.get('salary', ''),
                            'url': job.get('url', ''),
                            'reason': '元素不可点击'
                        }
                        self.logger.warning(f"⚠️ 元素不可点击 - 标题: {failed_job_info['title']}, 公司: {failed_job_info['company']}")
                        self._log_failed_job(failed_job_info)
                        continue
                    
                    # 使用BehaviorSimulator进行更自然的交互
                    if self.behavior_simulator:
                        # 使用自然鼠标移动
                        self.behavior_simulator.simulate_human_mouse_move(job_element)
                        
                        # 模拟短暂观察
                        if random.random() < 0.4:
                            self.behavior_simulator.simulate_reading_pause(50)
                    else:
                        # 回退到简单的鼠标悬停
                        if random.random() < 0.3:
                            ActionChains(driver).move_to_element(job_element).perform()
                            time.sleep(random.uniform(0.2, 0.5))
                    
                    # 尝试多种点击方式（带重试机制）
                    click_success = self._try_multiple_click_methods_with_retry(driver, job_element, max_retries=3)
                    if not click_success:
                        failed_job_info = {
                            'title': job.get('title', ''),
                            'company': job.get('company', ''),
                            'location': job.get('location', ''),
                            'salary': job.get('salary', ''),
                            'url': job.get('url', ''),
                            'reason': '所有点击方法和重试都失败'
                        }
                        self.logger.warning(f"⚠️ 点击失败 - 标题: {failed_job_info['title']}, 公司: {failed_job_info['company']}")
                        self._log_failed_job(failed_job_info)
                        continue
                    
                    # 等待新窗口打开 - COMMENTED FOR SPEED
                    # wait_time = random.uniform(1.0, 2.0)
                    # time.sleep(wait_time)
                    
                    # 检查是否有新窗口打开
                    new_windows = driver.window_handles
                    if len(new_windows) > len(original_windows):
                        # 切换到新窗口
                        new_window = [w for w in new_windows if w not in original_windows][0]
                        driver.switch_to.window(new_window)
                        
                        # 短暂等待页面加载 - COMMENTED FOR SPEED
                        time.sleep(random.uniform(1.5, 4.0))
                        
                        # 获取详情页URL
                        detail_url = driver.current_url
                        job['url'] = detail_url
                        
                        # 提取详情信息
                        detail_info = self.page_parser.parse_job_detail(driver, detail_url)
                        
                        if detail_info:
                            # 合并列表信息和详情信息
                            complete_job = {**job, **detail_info}
                            
                            # 立即保存到数据库
                            success = self.data_storage.save_job_detail(complete_job, detail_url, self.current_keyword)
                            if success:
                                results.append(complete_job)
                                self.logger.info(f"✅ 成功处理并保存: {job.get('title', '')}")
                            else:
                                self.logger.warning(f"⚠️ 保存失败: {job.get('title', '')}")
                        else:
                            self.logger.warning(f"⚠️ 详情提取失败: {job.get('title', '')}")
                        
                        # 关闭新窗口并切换回原窗口
                        driver.close()
                        driver.switch_to.window(original_windows[0])
                        
                        # 新增：登录模式下的延迟
                        if self.login_controller.is_login_mode_enabled():
                            # 添加延迟，避免反爬虫检测
                            delay = self.login_controller.login_config.get('detail_page_delay', 3.0)
                            time.sleep(delay)
                        
                        # 思考时间 - COMMENTED FOR SPEED
                        # think_time = random.uniform(0.5, 2.0)
                        # time.sleep(think_time)
                        
                    else:
                        # 记录失败的job信息到日志
                        failed_job_info = {
                            'title': job.get('title', ''),
                            'company': job.get('company', ''),
                            'location': job.get('location', ''),
                            'salary': job.get('salary', ''),
                            'url': job.get('url', ''),
                            'reason': '点击未打开新窗口'
                        }
                        self.logger.warning(f"⚠️ 点击失败 - 标题: {failed_job_info['title']}, 公司: {failed_job_info['company']}")
                        self._log_failed_job(failed_job_info)
                    
                    # 每处理几个职位后，模拟更长的休息 - COMMENTED FOR SPEED
                    # if (i + 1) % random.randint(3, 6) == 0:
                    #     rest_time = random.uniform(2.0, 5.0)
                    #     self.logger.info(f"⏳ 模拟用户休息 {rest_time:.1f} 秒")
                    #     time.sleep(rest_time)
                        
                except Exception as e:
                    # 记录异常失败的job信息
                    failed_job_info = {
                        'title': job.get('title', ''),
                        'company': job.get('company', ''),
                        'location': job.get('location', ''),
                        'salary': job.get('salary', ''),
                        'url': job.get('url', ''),
                        'reason': f'处理异常: {str(e)}'
                    }
                    self.logger.warning(f"❌ 处理职位异常 - 标题: {failed_job_info['title']}, 公司: {failed_job_info['company']}, 错误: {e}")
                    self._log_failed_job(failed_job_info)
                    
                    # 确保回到原窗口
                    if len(driver.window_handles) > 1:
                        driver.switch_to.window(driver.window_handles[0])
                    
                    # 错误后等待时间 - COMMENTED FOR SPEED
                    # error_wait = random.uniform(3.0, 8.0)
                    # time.sleep(error_wait)
                    continue
            
            self.logger.info(f"🎉 详情提取完成，成功处理 {len(results)} 个职位")
            return results
            
        except Exception as e:
            self.logger.error(f"❌ 立即提取详情信息失败: {e}")
            return []
    
    def _save_list_jobs_immediately(self, new_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        立即保存列表职位信息（不提取详情）
        
        Args:
            new_jobs: 新职位列表
            
        Returns:
            保存成功的职位列表
        """
        try:
            if not new_jobs:
                return []
            
            self.logger.info(f"💾 开始立即保存 {len(new_jobs)} 个列表职位信息")
            results = []
            
            for job in new_jobs:
                try:
                    # 使用数据存储器保存职位信息
                    success = self.data_storage.save_job_detail(job, job.get('url', ''), self.current_keyword)
                    if success:
                        results.append(job)
                        self.logger.debug(f"✅ 保存列表职位: {job.get('title', '')} - {job.get('company', '')}")
                    else:
                        self.logger.warning(f"⚠️ 保存失败: {job.get('title', '')} - {job.get('company', '')}")
                        
                except Exception as e:
                    self.logger.warning(f"❌ 保存职位时出错: {e}")
                    continue
            
            self.logger.info(f"💾 列表职位保存完成，成功保存 {len(results)} 个职位")
            return results
            
        except Exception as e:
            self.logger.error(f"❌ 保存列表职位失败: {e}")
            return []
    
    def _simulate_scroll_to_element(self, driver, target_element) -> None:
        """
        模拟滚动到元素位置
        
        Args:
            driver: WebDriver实例
            target_element: 目标元素
        """
        try:
            # 滚动到元素位置
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", target_element)
            # time.sleep(random.uniform(0.3, 0.8))  # COMMENTED FOR SPEED
            
        except Exception as e:
            self.logger.debug(f"模拟滚动失败: {e}")
            # 回退到简单滚动
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", target_element)
                # time.sleep(0.5)  # COMMENTED FOR SPEED
            except:
                pass
    
    def _log_failed_job(self, failed_job_info: Dict[str, Any]) -> None:
        """
        记录失败的job信息到日志文件
        
        Args:
            failed_job_info: 失败的job信息字典
        """
        try:
            import json
            import os
            from datetime import datetime
            
            # 确保logs目录存在
            logs_dir = "logs"
            if not os.path.exists(logs_dir):
                os.makedirs(logs_dir)
            
            # 创建失败job日志文件
            failed_jobs_file = os.path.join(logs_dir, "failed_jobs.json")
            
            # 添加时间戳
            failed_job_info['failed_at'] = datetime.now().isoformat()
            failed_job_info['extraction_session'] = getattr(self, 'current_keyword', 'unknown')
            
            # 读取现有的失败记录
            failed_jobs = []
            if os.path.exists(failed_jobs_file):
                try:
                    with open(failed_jobs_file, 'r', encoding='utf-8') as f:
                        failed_jobs = json.load(f)
                except:
                    failed_jobs = []
            
            # 添加新的失败记录
            failed_jobs.append(failed_job_info)
            
            # 保存到文件
            with open(failed_jobs_file, 'w', encoding='utf-8') as f:
                json.dump(failed_jobs, f, ensure_ascii=False, indent=2)
            
            self.logger.debug(f"失败job信息已记录到: {failed_jobs_file}")
            
        except Exception as e:
            self.logger.error(f"记录失败job信息时出错: {e}")
    
    def _is_element_clickable(self, driver, element) -> bool:
        """
        检查元素是否可点击
        
        Args:
            driver: WebDriver实例
            element: 要检查的元素
            
        Returns:
            是否可点击
        """
        try:
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait
            
            # 检查元素是否可见和可点击
            if not element.is_displayed():
                return False
            
            if not element.is_enabled():
                return False
            
            # 检查元素是否被其他元素遮挡
            try:
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                time.sleep(0.3)
                
                # 尝试获取元素位置
                location = element.location_once_scrolled_into_view
                size = element.size
                
                if location and size and size['width'] > 0 and size['height'] > 0:
                    return True
                    
            except Exception as e:
                self.logger.debug(f"检查元素可点击性时出错: {e}")
                return False
            
            return False
            
        except Exception as e:
            self.logger.debug(f"检查元素可点击性失败: {e}")
            return False
    
    def _try_multiple_click_methods_with_retry(self, driver, element, max_retries: int = 3) -> bool:
        """
        尝试多种点击方法（带重试机制）
        
        Args:
            driver: WebDriver实例
            element: 要点击的元素
            max_retries: 最大重试次数
            
        Returns:
            是否点击成功
        """
        for retry in range(max_retries):
            try:
                self.logger.debug(f"尝试点击，第 {retry + 1}/{max_retries} 次")
                
                # 每次重试前重新检查元素状态
                if not self._is_element_clickable(driver, element):
                    self.logger.debug(f"第 {retry + 1} 次重试：元素不可点击，等待后重试")
                    time.sleep(1 + retry * 0.5)  # 递增等待时间
                    continue
                
                # 尝试点击
                if self._try_multiple_click_methods(driver, element):
                    self.logger.debug(f"第 {retry + 1} 次重试成功")
                    return True
                
                # 失败后等待
                if retry < max_retries - 1:
                    wait_time = 1 + retry * 0.5
                    self.logger.debug(f"第 {retry + 1} 次重试失败，等待 {wait_time} 秒后重试")
                    time.sleep(wait_time)
                    
                    # 重新滚动到元素位置
                    self._simulate_scroll_to_element(driver, element)
                    
            except Exception as e:
                self.logger.debug(f"第 {retry + 1} 次重试出现异常: {e}")
                if retry < max_retries - 1:
                    time.sleep(1 + retry * 0.5)
                    continue
        
        return False
    
    def _find_job_elements_with_multiple_selectors(self, driver) -> List:
        """
        使用多种选择器策略查找职位元素
        
        Args:
            driver: WebDriver实例
            
        Returns:
            职位元素列表
        """
        from selenium.webdriver.common.by import By
        
        # 多种选择器策略，按优先级排序
        selectors = [
            ".jname",  # 原始选择器
            ".job-title",  # 通用职位标题选择器
            "[data-job-id]",  # 带job-id属性的元素
            "a[href*='job']",  # 包含job的链接
            ".job-item .title",  # 职位项目中的标题
            ".position-title",  # 职位标题
            ".job-name",  # 职位名称
            ".jobname"  # 职位名称变体
        ]
        
        job_elements = []
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    self.logger.debug(f"使用选择器 '{selector}' 找到 {len(elements)} 个元素")
                    job_elements = elements
                    break
            except Exception as e:
                self.logger.debug(f"选择器 '{selector}' 失败: {e}")
                continue
        
        if not job_elements:
            # 如果所有选择器都失败，尝试通用方法
            try:
                # 查找所有可能的职位链接
                all_links = driver.find_elements(By.TAG_NAME, "a")
                job_elements = [link for link in all_links
                              if link.get_attribute("href") and "job" in link.get_attribute("href").lower()]
                if job_elements:
                    self.logger.debug(f"使用通用方法找到 {len(job_elements)} 个职位链接")
            except Exception as e:
                self.logger.warning(f"通用方法也失败: {e}")
        
        return job_elements
    
    def _try_multiple_click_methods(self, driver, element) -> bool:
        """
        尝试多种点击方法
        
        Args:
            driver: WebDriver实例
            element: 要点击的元素
            
        Returns:
            是否点击成功
        """
        try:
            original_windows = driver.window_handles
            
            # 方法1: 标准ActionChains点击
            try:
                ActionChains(driver).click(element).perform()
                time.sleep(1.0)
                if len(driver.window_handles) > len(original_windows):
                    return True
            except Exception as e:
                self.logger.debug(f"ActionChains点击失败: {e}")
            
            # 方法2: 直接element.click()
            try:
                element.click()
                time.sleep(1.0)
                if len(driver.window_handles) > len(original_windows):
                    return True
            except Exception as e:
                self.logger.debug(f"element.click()失败: {e}")
            
            # 方法3: JavaScript点击
            try:
                driver.execute_script("arguments[0].click();", element)
                time.sleep(1.0)
                if len(driver.window_handles) > len(original_windows):
                    return True
            except Exception as e:
                self.logger.debug(f"JavaScript点击失败: {e}")
            
            # 方法4: 尝试点击子元素（如果存在链接）
            try:
                from selenium.webdriver.common.by import By
                link_element = element.find_element(By.TAG_NAME, "a")
                if link_element:
                    link_element.click()
                    time.sleep(1.0)
                    if len(driver.window_handles) > len(original_windows):
                        return True
            except Exception as e:
                self.logger.debug(f"子元素点击失败: {e}")
            
            return False
            
        except Exception as e:
            self.logger.debug(f"多种点击方法都失败: {e}")
            return False
    
    
    def extract_from_search_url(self,
                               search_url: str,
                               keyword: Optional[str] = None,
                               max_results: Optional[int] = None,
                               save_results: bool = True,
                               extract_details: bool = False,
                               max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        从搜索URL提取职位信息（同步版本）
        
        Args:
            search_url: 搜索页面URL
            keyword: 搜索关键词
            max_results: 最大结果数量
            save_results: 是否保存结果
            extract_details: 是否提取详情页内容
            max_pages: 最大页数
            
        Returns:
            提取的职位信息列表
        """
        try:
            self.logger.info(f"🚀 开始从搜索URL提取职位信息: {search_url}")
            self.logger.info(f"📊 参数: 关键词='{keyword}', 最大结果={max_results}, 最大页数={max_pages}, 提取详情={extract_details}")
            
            # 设置当前关键词和开始时间
            self.current_keyword = keyword or self._extract_keyword_from_url(search_url)
            self.extraction_start_time = time.time()
            self.extraction_results = []
            
            # 准备浏览器
            driver = self._prepare_browser()
            
            # 导航到搜索页面
            self._navigate_to_page(driver, search_url)
            
            # 点击薪资过滤器（3-4万）- 每次关键词搜索执行一次
            self.logger.warning("🐛 DEBUG: 准备点击薪资过滤器（初始搜索）")
            self._click_salary_filter(driver)
            self.logger.warning("🐛 DEBUG: 薪资过滤器点击完成（初始搜索）")
            
            # 获取配置参数
            max_pages = max_pages or self.search_config.get('strategy', {}).get('max_pages', 5)
            
            # 主循环：逐页处理
            current_page = 1
            all_results = []
            
            self.logger.info(f"🔄 开始逐页处理，最大页数: {max_pages}")
            
            while current_page <= max_pages:
                try:
                    self.logger.info(f"📄 处理第 {current_page} 页")
                    
                    # 计算当前页面需要的职位数量
                    remaining_needed = max_results - len(all_results) if max_results else None
                    page_max_results = remaining_needed if remaining_needed and remaining_needed < 50 else None
                    
                    # 使用同步方法解析职位列表
                    page_jobs = self.page_parser.parse_job_list(driver, page_max_results)
                    
                    if not page_jobs:
                        self.logger.warning(f"⚠️ 第 {current_page} 页未找到职位信息")
                        break
                    
                    self.logger.info(f"📋 第 {current_page} 页找到 {len(page_jobs)} 个职位")
                    
                    # 为每个职位添加页面信息
                    for job in page_jobs:
                        job['page_number'] = current_page
                        job['search_keyword'] = self.current_keyword
                    
                    # 过滤新职位并处理
                    from selenium.webdriver.common.by import By
                    job_elements = driver.find_elements(By.CSS_SELECTOR, ".jname")
                    new_jobs_with_elements = self._filter_new_jobs_by_fingerprint_with_elements(page_jobs, job_elements)
                    
                    if not new_jobs_with_elements:
                        self.logger.info(f"✅ 第 {current_page} 页所有职位都已存在，跳过详情提取")
                    else:
                        self.logger.info(f"🆕 第 {current_page} 页发现 {len(new_jobs_with_elements)} 个新职位")
                        
                        # 对新职位立即提取详情并保存
                        if extract_details:
                            page_results = self._extract_new_jobs_details_immediately(driver, new_jobs_with_elements)
                        else:
                            # 如果不提取详情，直接保存列表信息
                            new_jobs_only = [item['job_data'] for item in new_jobs_with_elements]
                            page_results = self._save_list_jobs_immediately(new_jobs_only)
                        
                        all_results.extend(page_results)
                        
                        self.logger.info(f"💾 第 {current_page} 页成功处理 {len(page_results)} 个职位")
                    
                    # 检查是否达到最大结果数量
                    if max_results and len(all_results) >= max_results:
                        self.logger.info(f"📊 已达到最大结果数量限制: {max_results}")
                        break
                    
                    # 检查是否有下一页
                    if not self.page_parser.has_next_page(driver):
                        self.logger.info("📄 已到达最后一页")
                        break
                    
                    # 导航到下一页
                    if current_page < max_pages:
                        self.logger.info(f"➡️ 准备进入第 {current_page + 1} 页")
                        
                        # 新增：页面跳转前检查登录状态
                        if self.login_controller.is_login_mode_enabled():
                            if not self.login_controller.validate_login_before_page_navigation(self.current_keyword):
                                self.logger.error("❌ 登录状态验证失败，无法继续抽取")
                                # 登录状态丢失且无法恢复，重新开始抽取流程
                                raise ContentExtractionError("登录状态丢失，需要重新开始抽取流程")
                        
                        # 🐛 DEBUG: 记录页面跳转前的状态
                        self.logger.warning(f"🐛 DEBUG: 准备从第 {current_page} 页跳转到第 {current_page + 1} 页")
                        
                        # 导航到下一页 - 传递当前页码
                        if not self.page_parser.navigate_to_next_page(driver, current_page):
                            # 尝试恢复到目标页面
                            target_page = current_page + 1
                            self.logger.warning(f"⚠️ 导航到第 {target_page} 页失败，尝试恢复")
                            
                            # 使用页面解析器的恢复方法
                            if not self.page_parser._recover_to_target_page(driver, target_page):
                                self.logger.warning(f"⚠️ 第 {target_page} 页恢复失败，结束提取")
                                self.logger.warning("🐛 DEBUG: 导航失败且恢复失败，可能导致薪资过滤器状态丢失")
                                break
                            
                            # 如果恢复成功，继续处理
                            self.logger.info(f"✅ 成功恢复到第 {target_page} 页")
                        
                        # 🐛 DEBUG: 检查页面跳转后是否需要重新应用薪资过滤器
                        self.logger.warning("🐛 DEBUG: 页面跳转完成，检查是否需要重新应用薪资过滤器")
                    
                    current_page += 1
                    
                except Exception as e:
                    self.logger.error(f"❌ 处理第 {current_page} 页时出错: {e}")
                    # 尝试继续处理下一页
                    current_page += 1
                    continue
            
            # 更新提取结果
            self.extraction_results = all_results
            
            # 注释掉重复保存，因为职位已在立即提取时保存
            # if save_results and all_results:
            #     self._save_extraction_results(all_results)
            self.logger.info(f"💾 职位已在提取过程中立即保存，跳过重复保存")
            
            # 输出最终统计
            elapsed_time = time.time() - self.extraction_start_time
            self.logger.info(f"✅ 提取完成!")
            self.logger.info(f"📊 总计处理 {current_page - 1} 页，提取 {len(all_results)} 个职位")
            self.logger.info(f"⏱️ 总耗时: {elapsed_time:.2f} 秒")
            
            return all_results
            
        except Exception as e:
            self.logger.error(f"❌ 从搜索URL提取职位信息失败: {e}")
            raise ContentExtractionError(f"从搜索URL提取职位信息失败: {e}")