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
        
        self.logger = logging.getLogger(__name__)
        
        # 状态管理
        self.current_keyword = None
        self.extraction_results = []
        self.extraction_start_time = None
    
    def extract_from_search_url(self,
                               search_url: str,
                               keyword: Optional[str] = None,
                               max_results: Optional[int] = None,
                               save_results: bool = True,
                               extract_details: bool = False,
                               max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        从搜索URL提取职位信息（支持多页）
        
        Args:
            search_url: 搜索页面URL
            keyword: 搜索关键词（用于记录）
            max_results: 最大结果数量
            save_results: 是否保存结果
            extract_details: 是否提取详情页内容（需要点击获取URL）
            max_pages: 最大页数，如果为None则使用配置中的值
            
        Returns:
            提取的职位信息列表
            
        Raises:
            ContentExtractionError: 内容提取失败
        """
        try:
            self.logger.info(f"🚀 开始从搜索URL提取内容: {search_url}")
            self.extraction_start_time = time.time()
            self.current_keyword = keyword or self._extract_keyword_from_url(search_url)
            max_jobs = max_results or self.search_config.get('strategy', {}).get('max_results_per_keyword', 50)
            
            # 获取分页配置
            strategy_config = self.search_config.get('strategy', {})
            enable_pagination = strategy_config.get('enable_pagination', True)
            max_pages_config = max_pages or strategy_config.get('max_pages', 10)
            page_delay_min = strategy_config.get('page_delay', 2)
            page_delay_max = strategy_config.get('page_delay_max', 5)
            
            self.logger.info(f"📄 分页配置: 启用={enable_pagination}, 最大页数={max_pages_config}")
            
            # 1. 准备浏览器
            driver = self._prepare_browser()
            
            # 2. 导航到搜索页面
            self._navigate_to_page(driver, search_url)
            
            # 3. 多页提取逻辑
            all_results = []
            current_page = 1
            
            while current_page <= max_pages_config:
                try:
                    self.logger.info(f"📊 正在处理第 {current_page} 页")
                    
                    # 获取当前页面信息
                    page_info = self.page_parser.get_current_page_info(driver)
                    self.logger.info(f"📍 当前页面: {page_info.get('current_page', current_page)}")
                    
                    # 解析当前页面的职位信息
                    page_results = self.page_parser.parse_job_list(driver, max_jobs)
                    
                    if page_results:
                        # 为每个结果添加页码信息
                        for result in page_results:
                            result['page_number'] = current_page
                            result['keyword'] = self.current_keyword
                        
                        all_results.extend(page_results)
                        self.logger.info(f"✅ 第 {current_page} 页提取到 {len(page_results)} 个职位")
                        
                        # 检查是否已达到最大结果数
                        if len(all_results) >= max_jobs:
                            self.logger.info(f"📊 已达到最大结果数限制: {max_jobs}")
                            all_results = all_results[:max_jobs]  # 截取到指定数量
                            break
                    else:
                        self.logger.warning(f"⚠️ 第 {current_page} 页未提取到职位信息")
                    
                    # 检查是否启用分页以及是否有下一页
                    if not enable_pagination or current_page >= max_pages_config:
                        self.logger.info(f"📄 已达到最大页数限制: {max_pages_config}")
                        break
                    
                    if not self.page_parser.has_next_page(driver):
                        self.logger.info("📄 没有更多页面，提取完成")
                        break
                    
                    # 导航到下一页
                    self.logger.info(f"🔄 准备导航到第 {current_page + 1} 页")
                    
                    # 页面间延迟
                    delay_time = random.uniform(page_delay_min, page_delay_max)
                    self.logger.info(f"⏳ 页面间延迟 {delay_time:.1f} 秒")
                    time.sleep(delay_time)
                    
                    if not self.page_parser.navigate_to_next_page(driver):
                        self.logger.warning("❌ 导航到下一页失败，停止分页提取")
                        break
                    
                    current_page += 1
                    
                except Exception as e:
                    self.logger.error(f"❌ 处理第 {current_page} 页时出错: {e}")
                    break
            
            # 4. 如果需要详情页内容，处理所有页面的结果
            if extract_details and all_results:
                self.logger.info("🔗 开始提取详情页URL和内容...")
                
                # 重新导航到第一页进行详情提取（如果需要）
                if current_page > 1:
                    self.logger.info("🔄 返回第一页进行详情提取")
                    self._navigate_to_page(driver, search_url)
                
                # 4.1 通过点击获取详情页URL（仅处理前几页的结果以避免过长时间）
                detail_extract_limit = min(len(all_results), 20)  # 限制详情提取数量
                url_results = self.page_parser.extract_job_urls_by_clicking(driver, detail_extract_limit)
                
                if url_results:
                    # 4.2 提取详情页内容
                    detail_urls = [item['detail_url'] for item in url_results if item.get('detail_url')]
                    if detail_urls:
                        details = self.extract_job_details(detail_urls)
                        
                        # 4.3 合并基本信息和详情信息
                        self._merge_job_data(all_results, url_results, details)
            
            # 5. 处理结果
            if all_results:
                self.extraction_results = all_results
                
                # 6. 保存结果（如果需要）
                if save_results:
                    self._save_extraction_results(all_results)
                
                self.logger.info(f"✅ 多页内容提取完成，共 {current_page} 页，提取 {len(all_results)} 个职位")
            else:
                self.logger.warning("⚠️ 未提取到任何职位信息")
            
            return all_results
            
        except Exception as e:
            self.logger.error(f"❌ 内容提取失败: {e}")
            raise ContentExtractionError(f"内容提取失败: {e}")
    
    def extract_from_keyword(self,
                           keyword: str,
                           max_results: Optional[int] = None,
                           save_results: bool = True,
                           extract_details: bool = False,
                           max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        根据关键词提取职位信息（支持多页）
        
        Args:
            keyword: 搜索关键词
            max_results: 最大结果数量
            save_results: 是否保存结果
            extract_details: 是否提取详情页内容
            max_pages: 最大页数，如果为None则使用配置中的值
            
        Returns:
            提取的职位信息列表
        """
        try:
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
            
        except Exception as e:
            self.logger.error(f"❌ 基于关键词的内容提取失败: {e}")
            raise ContentExtractionError(f"基于关键词的内容提取失败: {e}")
    
    def extract_job_details(self, job_urls: List[str]) -> List[Dict[str, Any]]:
        """
        提取职位详情信息
        
        Args:
            job_urls: 职位详情页URL列表
            
        Returns:
            职位详情信息列表
        """
        try:
            self.logger.info(f"📄 开始提取 {len(job_urls)} 个职位的详情信息")
            
            driver = self._prepare_browser()
            details = []
            
            # 随机打乱URL顺序，避免按顺序访问的模式
            shuffled_urls = job_urls.copy()
            random.shuffle(shuffled_urls)
            
            for i, job_url in enumerate(shuffled_urls, 1):
                try:
                    self.logger.info(f"📝 提取职位详情 {i}/{len(shuffled_urls)}: {job_url}")
                    
                    # 详情页：延长等待时间，避免反爬检测
                    if self.behavior_simulator:
                        self.behavior_simulator.random_delay(2.0, 5.0)  # 详情页延长到2-5秒
                    else:
                        time.sleep(random.uniform(3.0, 8.0))  # 详情页延长到3-8秒
                    
                    # 使用简化的详情页解析
                    detail = self._extract_job_detail_simplified(driver, job_url)
                    if detail:
                        details.append(detail)
                        
                        # 保存单个职位详情
                        self.data_storage.save_job_detail(detail, job_url)
                        
                        # 详情页：增加阅读时间模拟
                        if self.behavior_simulator and random.random() < 0.6:  # 增加到60%概率模拟阅读
                            self.behavior_simulator.random_delay(1.0, 3.0)  # 延长阅读时间
                    
                    # 详情页：适当增加休息时间
                    if i % random.randint(5, 8) == 0:  # 详情页休息频率适中
                        rest_time = random.uniform(4.0, 8.0)  # 详情页休息时间延长
                        self.logger.info(f"⏳ 模拟用户休息 {rest_time:.1f} 秒...")
                        time.sleep(rest_time)
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ 提取职位详情失败 {job_url}: {e}")
                    # 详情页失败后延长等待时间
                    time.sleep(random.uniform(10.0, 25.0))  # 从5-15秒延长到10-25秒
                    continue
            
            self.logger.info(f"✅ 职位详情提取完成，共提取 {len(details)} 个详情")
            return details
            
        except Exception as e:
            self.logger.error(f"❌ 职位详情提取失败: {e}")
            raise ContentExtractionError(f"职位详情提取失败: {e}")
    
    def _extract_job_detail_simplified(self, driver, job_url: str) -> Optional[Dict[str, Any]]:
        """
        简化的职位详情提取方法
        
        Args:
            driver: WebDriver实例
            job_url: 职位详情URL
            
        Returns:
            职位详情数据
        """
        try:
            # 直接导航，减少复杂的模拟
            driver.get(job_url)
            
            # 详情页：延长等待时间
            time.sleep(random.uniform(2.0, 4.0))  # 从1-2.5秒延长到2-4秒
            
            # 检查是否被重定向或阻止
            current_url = driver.current_url
            if 'error' in current_url.lower() or 'block' in current_url.lower() or 'captcha' in current_url.lower():
                self.logger.warning(f"检测到可能的反爬页面: {current_url}")
                return None
            
            # 简化的页面交互：只做基本滚动
            if self.behavior_simulator and random.random() < 0.5:  # 50%概率进行简单滚动
                self.behavior_simulator.simulate_scroll('down', random.randint(300, 500))
                time.sleep(random.uniform(0.5, 1.0))
                driver.execute_script("window.scrollTo(0, 0);")
            
            # 解析页面内容
            detail_data = self.page_parser.parse_job_detail(driver, job_url)
            
            return detail_data
            
        except Exception as e:
            self.logger.error(f"简化提取职位详情失败: {e}")
            return None
    
        
    def extract_job_urls_by_clicking(self,
                                   search_url: str,
                                   max_jobs: int = 10,
                                   save_results: bool = True) -> List[Dict[str, Any]]:
        """
        通过模拟点击提取职位详情页URL
        
        ContentExtractor作为协调器，负责流程管理和浏览器会话
        具体的页面解析工作委托给PageParser
        
        Args:
            search_url: 搜索页面URL
            max_jobs: 最大提取数量
            save_results: 是否保存结果
            
        Returns:
            职位URL信息列表
        """
        try:
            self.logger.info(f"🔗 开始提取职位详情页URL: {search_url}")
            
            # 1. 准备浏览器会话（ContentExtractor的职责）
            driver = self._prepare_browser()
            
            # 2. 导航到搜索页面（ContentExtractor的职责）
            self._navigate_to_page(driver, search_url)
            
            # 3. 委托PageParser进行页面解析和URL提取
            extracted_urls = self.page_parser.extract_job_urls_by_clicking(driver, max_jobs)
            
            # 4. 处理结果保存（ContentExtractor的职责）
            if save_results and extracted_urls:
                filename = self._save_url_extraction_results(extracted_urls)
                if filename:
                    self.logger.info(f"💾 URL提取结果已保存: {filename}")
            
            return extracted_urls
            
        except Exception as e:
            self.logger.error(f"❌ URL提取失败: {e}")
            raise ContentExtractionError(f"URL提取失败: {e}")
    
    def extract_job_urls_from_keyword(self,
                                    keyword: str,
                                    max_jobs: int = 10,
                                    save_results: bool = True) -> List[Dict[str, Any]]:
        """
        根据关键词提取职位详情页URL
        
        Args:
            keyword: 搜索关键词
            max_jobs: 最大提取数量
            save_results: 是否保存结果
            
        Returns:
            职位URL信息列表
        """
        try:
            # 构建搜索URL
            search_url = self.url_builder.build_search_url(keyword)
            self.logger.info(f"🔍 使用关键词 '{keyword}' 构建搜索URL: {search_url}")
            
            # 提取URL
            return self.extract_job_urls_by_clicking(
                search_url,
                max_jobs=max_jobs,
                save_results=save_results
            )
            
        except Exception as e:
            self.logger.error(f"❌ 基于关键词的URL提取失败: {e}")
            raise ContentExtractionError(f"基于关键词的URL提取失败: {e}")
    
    def _merge_job_data(self,
                       basic_jobs: List[Dict[str, Any]],
                       url_jobs: List[Dict[str, Any]],
                       detail_jobs: List[Dict[str, Any]]) -> None:
        """
        合并职位基本信息、URL信息和详情信息
        
        Args:
            basic_jobs: 基本职位信息列表
            url_jobs: URL信息列表
            detail_jobs: 详情信息列表
        """
        try:
            # 创建URL和详情的映射
            url_map = {item['title']: item for item in url_jobs}
            detail_map = {item['url']: item for item in detail_jobs if item.get('url')}
            
            # 合并数据
            for job in basic_jobs:
                job_title = job.get('title', '')
                
                # 添加URL信息
                if job_title in url_map:
                    url_info = url_map[job_title]
                    job['detail_url'] = url_info.get('detail_url', '')
                    job['url_extracted_at'] = url_info.get('extracted_at', '')
                
                # 添加详情信息
                detail_url = job.get('detail_url', '')
                if detail_url in detail_map:
                    detail_info = detail_map[detail_url]
                    job.update({
                        'description': detail_info.get('description', ''),
                        'requirements': detail_info.get('requirements', ''),
                        'company_info': detail_info.get('company_info', ''),
                        'benefits': detail_info.get('benefits', ''),
                        'detail_extracted_at': detail_info.get('extracted_at', '')
                    })
                
                # 标记为包含详情信息
                job['has_details'] = bool(detail_url and detail_url in detail_map)
            
            self.logger.info(f"✅ 数据合并完成，{len([j for j in basic_jobs if j.get('has_details')])} 个职位包含详情信息")
            
        except Exception as e:
            self.logger.error(f"❌ 合并职位数据失败: {e}")
    
    def _save_url_extraction_results(self, extracted_urls: List[Dict[str, Any]]) -> str:
        """
        保存URL提取结果
        
        Args:
            extracted_urls: 提取的URL列表
            
        Returns:
            保存的文件路径
        """
        try:
            if not extracted_urls:
                return ""
            
            import json
            from datetime import datetime
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"extracted_job_urls_{timestamp}.json"
            
            result = {
                'timestamp': datetime.now().isoformat(),
                'total_urls': len(extracted_urls),
                'urls': extracted_urls
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            return filename
            
        except Exception as e:
            self.logger.error(f"❌ 保存URL提取结果失败: {e}")
            return ""
    
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
                if self.session_manager.is_session_valid(driver):
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
                
                # 调试模式不需要额外等待
                time.sleep(0.2)
                
            elif self.behavior_simulator and random.random() < 0.2:  # 只有20%概率使用复杂导航
                # 生产模式：偶尔使用自然导航
                success = self.behavior_simulator.natural_navigate_to_url(url)
                if not success:
                    self.logger.warning("自然导航失败，使用标准导航")
                    driver.get(url)
                    wait = self.browser_manager.create_wait(8)
                    wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                    time.sleep(random.uniform(0.5, 1.0))
            else:
                # 标准导航方式
                driver.get(url)
                
                # 减少等待时间
                wait = self.browser_manager.create_wait(8)  # 从20秒减少到8秒
                wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                
                # 大幅减少额外等待时间
                time.sleep(random.uniform(0.3, 1.0))  # 从3秒减少到0.3-1秒
            
            self.logger.info("✅ 页面导航完成")
            
        except Exception as e:
            self.logger.error(f"❌ 页面导航失败: {e}")
            raise ContentExtractionError(f"页面导航失败: {e}")
    
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
                        self.logger.info(f"⏳ 等待 {delay_between_keywords} 秒后处理下一个关键词...")
                        time.sleep(delay_between_keywords)
                    
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
    
    def close(self) -> None:
        """关闭内容提取器，清理资源"""
        try:
            self.logger.info("🧹 关闭内容提取器")
            
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