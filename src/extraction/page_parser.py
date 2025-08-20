"""
页面解析器

负责所有页面解析工作，包括：
- 解析职位列表页面，提取职位基本信息
- 解析职位详情页面，提取详细信息
- 通过点击操作获取职位详情页URL
- 页面结构分析和调试
"""

import time
import logging
import random
from datetime import datetime
from typing import Dict, List, Optional, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from ..core.exceptions import PageParseError
from ..utils.fingerprint import generate_job_fingerprint, extract_job_key_info


class PageParser:
    """页面解析器"""
    
    def __init__(self, config: dict):
        """
        初始化页面解析器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.selectors = config.get('selectors', {})
        self.search_selectors = self.selectors.get('search_page', {})
        self.detail_selectors = self.selectors.get('job_detail', {})
        self.logger = logging.getLogger(__name__)
    
    def parse_job_list(self, driver: webdriver.Chrome, max_results: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        解析职位列表页面
        
        Args:
            driver: WebDriver实例
            max_results: 最大结果数量
            
        Returns:
            职位信息列表
            
        Raises:
            PageParseError: 页面解析失败
        """
        try:
            self.logger.info("📊 开始解析职位列表页面")
            
            # 等待页面稳定
            self._wait_for_page_stable(driver)
            
            # 获取职位列表元素
            job_elements = self._get_job_elements(driver)
            
            if not job_elements:
                self.logger.warning("⚠️ 未找到职位列表元素")
                self.logger.warning("💡 提示: 建议人工检查页面结构，可能需要更新选择器")
                return []
            
            self.logger.info(f"📋 找到 {len(job_elements)} 个职位元素")
            
            # 解析每个职位
            jobs = []
            processed_count = 0
            
            self.logger.info(f"🔄 开始逐个解析职位元素...")
            
            for i, job_element in enumerate(job_elements, 1):
                self.logger.info(f"🎯 正在处理第 {i}/{len(job_elements)} 个职位元素")
                
                if max_results and processed_count >= max_results:
                    self.logger.info(f"📊 已达到最大结果数量限制: {max_results}")
                    break
                
                try:
                    self.logger.debug(f"📝 开始解析职位元素 {i}...")
                    job_data = self._parse_job_element(job_element)
                    self.logger.debug(f"📝 职位元素 {i} 解析完成")
                    
                    if job_data:
                        jobs.append(job_data)
                        processed_count += 1
                        
                        self.logger.info(
                            f"✅ 职位 {processed_count}: {job_data.get('title', '未知')} - "
                            f"{job_data.get('company', '未知')} - {job_data.get('salary', '面议')}"
                        )
                    else:
                        self.logger.warning(f"⚠️ 职位元素 {i} 解析结果为空")
                    
                except Exception as e:
                    self.logger.error(f"❌ 解析职位 {i} 时出错: {e}")
                    import traceback
                    self.logger.error(f"错误详情: {traceback.format_exc()}")
                    continue
            
            self.logger.info(f"✅ 职位列表解析完成，共解析 {len(jobs)} 个职位")
            return jobs
            
        except Exception as e:
            self.logger.error(f"❌ 解析职位列表失败: {e}")
            raise PageParseError(f"解析职位列表失败: {e}")
    
    def _wait_for_page_stable(self, driver: webdriver.Chrome, timeout: int = 10) -> None:
        """
        等待页面稳定加载（优化版本）
        
        Args:
            driver: WebDriver实例
            timeout: 超时时间
        """
        try:
            # 等待页面加载完成
            WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            # 优化：减少额外等待时间
            time.sleep(0.5)  # 从2秒减少到0.5秒
            
            self.logger.debug("页面已稳定加载")
            
        except TimeoutException:
            self.logger.warning("页面加载超时，继续尝试解析")
    
    def _get_job_elements(self, driver: webdriver.Chrome) -> List:
        """
        获取职位列表元素
        
        Args:
            driver: WebDriver实例
            
        Returns:
            职位元素列表
        """
        job_list_selector = self.search_selectors.get('job_list', '.job-list-item')
        
        try:
            # 如果job_list_selector是容器选择器（如.joblist），需要查找其子元素
            if job_list_selector == '.joblist':
                # 在.joblist容器内查找职位项
                job_item_selectors = [
                    '.joblist .joblist-item',
                    '.joblist > div',
                    '.joblist li',
                    '.joblist [data-jobid]',
                    '.joblist .job-item'
                ]
                
                for selector in job_item_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            self.logger.debug(f"在容器内找到职位项: {selector} (数量: {len(elements)})")
                            return elements
                    except:
                        continue
                
                # 如果找不到子元素，尝试直接使用容器的直接子元素
                try:
                    container = driver.find_element(By.CSS_SELECTOR, job_list_selector)
                    # 获取容器的所有直接子元素
                    job_elements = container.find_elements(By.XPATH, "./*")
                    if job_elements:
                        self.logger.debug(f"使用容器直接子元素，找到 {len(job_elements)} 个")
                        return job_elements
                except:
                    pass
            else:
                # 直接使用配置的选择器
                job_elements = driver.find_elements(By.CSS_SELECTOR, job_list_selector)
                if job_elements:
                    self.logger.debug(f"使用选择器 '{job_list_selector}' 找到 {len(job_elements)} 个元素")
                    return job_elements
            
            # 如果没找到，尝试51job的具体选择器（基于实际页面结构）
            # 只保留最可能的选择器，避免无效的DOM查询
            fallback_selectors = [
                '.joblist-item',  # 51job的实际职位项选择器
                '.job-item'       # 通用备选
            ]
            
            for selector in fallback_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        self.logger.info(f"使用备用选择器 '{selector}' 找到 {len(elements)} 个元素")
                        return elements
                except:
                    continue
            
            return []
            
        except Exception as e:
            self.logger.error(f"获取职位元素失败: {e}")
            return []
    
    def _parse_job_element(self, job_element) -> Optional[Dict[str, Any]]:
        """
        解析单个职位元素
        
        Args:
            job_element: 职位元素
            
        Returns:
            职位数据字典
        """
        self.logger.debug("🔍 开始解析职位元素...")
        
        job_data = {
            'extracted_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'source': 'qiancheng'
        }
        
        try:
            # 职位标题
            self.logger.debug("📝 提取职位标题...")
            job_title = self._extract_title(job_element)
            job_data.update({
                'title': job_title,
                'url': "",  # URL需要通过点击获取
                'needs_click_extraction': True
            })
            self.logger.debug(f"📝 标题提取完成: {job_title}")
            
            # 公司名称
            self.logger.debug("🏢 提取公司名称...")
            job_data['company'] = self._extract_text_by_selector(
                job_element,
                self.search_selectors.get('company_name', '.cname'),
                default="未知公司"
            )
            self.logger.debug(f"🏢 公司名称: {job_data['company']}")
            
            # 薪资
            self.logger.debug("💰 提取薪资信息...")
            job_data['salary'] = self._extract_text_by_selector(
                job_element,
                self.search_selectors.get('salary', '.sal'),
                default="薪资面议"
            )
            self.logger.debug(f"💰 薪资: {job_data['salary']}")
            
            # 地点
            self.logger.debug("📍 提取地点信息...")
            job_data['location'] = self._extract_text_by_selector(
                job_element,
                self.search_selectors.get('location', '.area'),
                default="未知地点"
            )
            self.logger.debug(f"📍 地点: {job_data['location']}")
            
            # 经验要求
            self.logger.debug("🎓 提取经验要求...")
            job_data['experience'] = self._extract_text_by_selector(
                job_element,
                self.search_selectors.get('experience', '.experience'),
                default="经验不限"
            )
            self.logger.debug(f"🎓 经验: {job_data['experience']}")
            
            # 学历要求
            self.logger.debug("📚 提取学历要求...")
            job_data['education'] = self._extract_text_by_selector(
                job_element,
                self.search_selectors.get('education', '.education'),
                default="学历不限"
            )
            self.logger.debug(f"📚 学历: {job_data['education']}")
            
            # 提取额外信息
            self.logger.debug("ℹ️ 提取额外信息...")
            extra_info = self._extract_extra_info(job_element)
            job_data.update(extra_info)
            self.logger.debug("ℹ️ 额外信息提取完成")
            
            # 生成职位指纹
            self.logger.debug("🔍 生成职位指纹...")
            job_fingerprint = generate_job_fingerprint(
                job_data.get('title', ''),
                job_data.get('company', ''),
                job_data.get('salary', ''),
                job_data.get('location', '')
            )
            job_data['job_fingerprint'] = job_fingerprint
            self.logger.debug(f"🔍 职位指纹: {job_fingerprint}")
            
            self.logger.debug("✅ 职位元素解析完成")
            return job_data
            
        except Exception as e:
            self.logger.error(f"❌ 解析职位元素失败: {e}")
            import traceback
            self.logger.error(f"错误详情: {traceback.format_exc()}")
            return None
    
    def _extract_title(self, job_element) -> str:
        """
        提取职位标题
        
        Args:
            job_element: 职位元素
            
        Returns:
            职位标题字符串
        """
        try:
            # 从配置中获取职位标题选择器
            title_selector = self.search_selectors.get('job_title', '.jname a')
            
            # 尝试提取职位标题
            try:
                # 首先尝试配置的选择器
                title_element = job_element.find_element(By.CSS_SELECTOR, title_selector)
                job_title = title_element.text.strip()
                
                # 如果文本为空，尝试title属性
                if not job_title:
                    job_title = title_element.get_attribute('title')
                    if job_title:
                        job_title = job_title.strip()
                
                if job_title:
                    self.logger.debug(f"通过配置选择器找到职位标题: {job_title}")
                    return job_title
                    
            except Exception as e:
                self.logger.debug(f"配置选择器 '{title_selector}' 未找到元素: {e}")
            
            # 如果配置选择器失败，尝试51job的具体选择器
            fallback_selectors = ['.jname', '.jname a', '.job-title', '.position-title']
            
            for selector in fallback_selectors:
                try:
                    title_element = job_element.find_element(By.CSS_SELECTOR, selector)
                    job_title = title_element.text.strip()
                    
                    if not job_title:
                        job_title = title_element.get_attribute('title')
                        if job_title:
                            job_title = job_title.strip()
                    
                    if job_title:
                        self.logger.debug(f"通过备用选择器 '{selector}' 找到职位标题: {job_title}")
                        return job_title
                        
                except Exception:
                    continue
            
            # 如果都没找到，返回默认值
            self.logger.warning("未找到职位标题")
            return "未知职位"
                
        except Exception as e:
            self.logger.warning(f"提取职位标题失败: {e}")
            return "未知职位"
    
    def _extract_text_by_selector(self, parent_element, selector: str, default: str = "") -> str:
        """
        通过选择器提取文本（优化版本）
        
        Args:
            parent_element: 父元素
            selector: CSS选择器
            default: 默认值
            
        Returns:
            提取的文本
        """
        try:
            # 添加超时机制，避免长时间等待
            element = parent_element.find_element(By.CSS_SELECTOR, selector)
            text = element.text.strip()
            return text if text else default
        except Exception:
            # 快速失败，不记录详细错误信息
            return default
    
    def _extract_extra_info(self, job_element) -> Dict[str, Any]:
        """
        提取额外信息
        
        Args:
            job_element: 职位元素
            
        Returns:
            额外信息字典
        """
        extra_info = {}
        
        try:
            # 简化额外信息提取，只提取最重要的信息
            # 发布时间（51job通常不在列表页显示）
            publish_time = self._extract_text_by_selector(job_element, '.time', default="")
            if publish_time:
                extra_info['publish_time'] = publish_time
            
            # 公司规模（51job通常不在列表页显示）
            company_scale = self._extract_text_by_selector(job_element, '.company-scale', default="")
            if company_scale:
                extra_info['company_scale'] = company_scale
            
        except Exception as e:
            self.logger.debug(f"提取额外信息时出错: {e}")
        
        return extra_info
    
    def parse_job_detail(self, driver: webdriver.Chrome, job_url: str) -> Optional[Dict[str, Any]]:
        """
        解析职位详情页面
        
        Args:
            driver: WebDriver实例
            job_url: 职位详情URL
            
        Returns:
            职位详情数据
        """
        try:
            self.logger.info(f"📄 解析职位详情: {job_url}")
            
            # 根据模式调整详情页等待时间
            config_mode = getattr(self, 'config', {}).get('mode', {})
            is_debug_mode = config_mode.get('development', False) or config_mode.get('debug', False)
            
            if is_debug_mode:
                # 开发模式：快速等待
                self._wait_for_page_stable(driver, timeout=3)  # 开发模式3秒
            else:
                # 生产模式：正常等待
                self._wait_for_page_stable(driver, timeout=6)  # 生产模式6秒
            
            # 检查页面是否正常加载
            page_title = driver.title
            if not page_title or '404' in page_title or 'error' in page_title.lower():
                self.logger.warning(f"页面可能未正常加载: {page_title}")
                return None
            
            detail_data = {
                'url': job_url,
                'extracted_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'page_title': page_title
            }
            
            # 使用多种选择器提取职位描述
            description = ""
            description_selectors = [
                '.bmsg.job_msg.inbox',  # 51job精确选择器
                '.bmsg',                # 51job简化选择器
                '.job_msg',             # 51job备用选择器
                '.job-detail-content',  # 通用选择器
                '.job-description',     # 通用选择器
                '.job_bt',              # 51job另一个可能的选择器
                '[class*="job_msg"]',   # 包含job_msg的类名
                '[class*="description"]' # 包含description的类名
            ]
            
            for selector in description_selectors:
                try:
                    description = self._extract_text_by_selector(driver, selector, default="")
                    if description and len(description) > 20:  # 降低最小长度要求
                        detail_data['description'] = description
                        self.logger.info(f"✅ 使用选择器 '{selector}' 提取职位描述成功 (长度: {len(description)})")
                        break
                except Exception as e:
                    self.logger.debug(f"选择器 '{selector}' 提取失败: {e}")
                    continue
            
            if not description or len(description) <= 20:
                # 如果所有选择器都失败，尝试获取页面主要文本内容
                try:
                    # 尝试获取页面body中的主要文本内容
                    main_content = driver.execute_script("""
                        // 尝试找到包含职位描述的主要内容区域
                        var selectors = ['.bmsg', '.job_msg', '.job-detail', '.content', '.main'];
                        for (var i = 0; i < selectors.length; i++) {
                            var element = document.querySelector(selectors[i]);
                            if (element && element.innerText && element.innerText.length > 50) {
                                return element.innerText;
                            }
                        }
                        return '';
                    """)
                    
                    if main_content and len(main_content) > 20:
                        detail_data['description'] = main_content
                        self.logger.info(f"✅ 使用JavaScript提取职位描述成功 (长度: {len(main_content)})")
                    else:
                        detail_data['description'] = ""
                        self.logger.warning("⚠️ 未找到有效的职位描述内容")
                        
                except Exception as e:
                    detail_data['description'] = ""
                    self.logger.warning(f"⚠️ JavaScript提取职位描述失败: {e}")
            else:
                self.logger.debug(f"职位描述提取成功，长度: {len(description)} 字符")
            
            # 对于51job，职位要求通常包含在描述中，不需要单独提取
            # 避免重复内容，直接设置为空，让RAG系统后续处理
            detail_data['requirements'] = ""
            
            # 快速设置默认值，避免不必要的DOM查询
            detail_data['company_info'] = ""
            detail_data['benefits'] = ""
            
            # 仅在开发模式下提取额外信息
            config_mode = getattr(self, 'config', {}).get('mode', {})
            is_debug_mode = config_mode.get('development', False) or config_mode.get('debug', False)
            
            if is_debug_mode:
                self.logger.debug("🔧 开发模式: 提取额外信息...")
                
                # 公司信息 - 使用配置中的选择器
                company_info = self._extract_text_by_selector(
                    driver,
                    self.detail_selectors.get('company_info', '.company-info'),
                    default=""
                )
                detail_data['company_info'] = company_info
                
                # 福利待遇 - 使用配置中的选择器
                benefits = self._extract_text_by_selector(
                    driver,
                    self.detail_selectors.get('benefits', '.job-benefits'),
                    default=""
                )
                detail_data['benefits'] = benefits
            else:
                self.logger.debug("🚀 生产模式: 跳过额外信息提取以提升性能")
            
            # 验证是否提取到有效内容（修复逻辑）
            content_fields = ['description', 'requirements', 'company_info', 'benefits']
            has_content = any(detail_data.get(field) and len(str(detail_data.get(field)).strip()) > 10 for field in content_fields)
            
            # 特别检查核心字段
            description = detail_data.get('description', '').strip()
            requirements = detail_data.get('requirements', '').strip()
            
            # 如果有描述或要求内容，就认为提取成功
            if description and len(description) > 20:
                has_content = True
                self.logger.info(f"✅ 成功提取职位描述，长度: {len(description)} 字符")
            elif requirements and len(requirements) > 20:
                has_content = True
                self.logger.info(f"✅ 成功提取职位要求，长度: {len(requirements)} 字符")
            
            if not has_content:
                self.logger.warning(f"⚠️ 未提取到有效的详情内容: {job_url}")
                self.logger.warning("💡 提示: 如果页面确实包含内容，建议人工检查页面结构和选择器")
                self.logger.warning("🔍 可能原因: 页面选择器不匹配、需要额外等待时间、或页面结构发生变化")
                return None
            
            return detail_data
            
        except Exception as e:
            self.logger.error(f"❌ 解析职位详情失败: {e}")
            return None
    
    
    def get_page_info(self, driver: webdriver.Chrome) -> Dict[str, Any]:
        """
        获取页面基本信息
        
        Args:
            driver: WebDriver实例
            
        Returns:
            页面信息字典
        """
        try:
            return {
                'url': driver.current_url,
                'title': driver.title,
                'ready_state': driver.execute_script("return document.readyState"),
                'page_height': driver.execute_script("return document.body.scrollHeight"),
                'viewport_height': driver.execute_script("return window.innerHeight"),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            self.logger.error(f"获取页面信息失败: {e}")
            return {}
    
    
    def has_next_page(self, driver: webdriver.Chrome) -> bool:
        """
        检查是否有下一页
        
        Args:
            driver: WebDriver实例
            
        Returns:
            是否有下一页
        """
        try:
            # 尝试多种下一页按钮选择器
            next_page_selectors = [
                self.search_selectors.get('next_page', '.btn_next'),
                '.next-page',
                '.page-next',
                '.btn-next',
                '.pager-next',
                'a[title*="下一页"]',
                'a[title*="next"]',
                '.pagination .next',
                '.pagination-next',
                '.page-item.next a',
                '.page-link[aria-label*="Next"]'
            ]
            
            for selector in next_page_selectors:
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, selector)
                    
                    # 检查按钮是否可用（不是禁用状态）
                    if next_button.is_enabled() and next_button.is_displayed():
                        # 检查是否有disabled类或属性
                        classes = next_button.get_attribute('class') or ''
                        disabled_attr = next_button.get_attribute('disabled')
                        
                        if 'disabled' not in classes.lower() and not disabled_attr:
                            self.logger.debug(f"找到可用的下一页按钮: {selector}")
                            return True
                    
                except NoSuchElementException:
                    continue
                except Exception as e:
                    self.logger.debug(f"检查下一页按钮时出错 {selector}: {e}")
                    continue
            
            self.logger.debug("未找到可用的下一页按钮")
            return False
            
        except Exception as e:
            self.logger.error(f"检查下一页失败: {e}")
            return False
    
    def navigate_to_next_page(self, driver: webdriver.Chrome) -> bool:
        """
        导航到下一页
        
        Args:
            driver: WebDriver实例
            
        Returns:
            是否成功导航到下一页
        """
        try:
            self.logger.info("🔄 尝试导航到下一页")
            
            # 记录当前页面URL用于验证
            current_url = driver.current_url
            
            # 尝试多种下一页按钮选择器
            next_page_selectors = [
                self.search_selectors.get('next_page', '.btn_next'),
                '.next-page',
                '.page-next',
                '.btn-next',
                '.pager-next',
                'a[title*="下一页"]',
                'a[title*="next"]',
                '.pagination .next',
                '.pagination-next',
                '.page-item.next a',
                '.page-link[aria-label*="Next"]'
            ]
            
            for selector in next_page_selectors:
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, selector)
                    
                    # 检查按钮是否可用
                    if next_button.is_enabled() and next_button.is_displayed():
                        classes = next_button.get_attribute('class') or ''
                        disabled_attr = next_button.get_attribute('disabled')
                        
                        if 'disabled' not in classes.lower() and not disabled_attr:
                            self.logger.info(f"点击下一页按钮: {selector}")
                            
                            # 滚动到按钮位置
                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_button)
                            time.sleep(random.uniform(0.5, 1.0))
                            
                            # 模拟人类点击行为
                            if random.random() < 0.3:  # 30%概率先悬停
                                ActionChains(driver).move_to_element(next_button).perform()
                                time.sleep(random.uniform(0.2, 0.5))
                            
                            # 点击下一页按钮
                            ActionChains(driver).click(next_button).perform()
                            
                            # 等待页面加载
                            wait_time = random.uniform(2.0, 4.0)
                            time.sleep(wait_time)
                            
                            # 等待页面稳定
                            self._wait_for_page_stable(driver, timeout=10)
                            
                            # 验证是否成功跳转到下一页
                            new_url = driver.current_url
                            if new_url != current_url:
                                self.logger.info(f"✅ 成功导航到下一页: {new_url}")
                                return True
                            else:
                                # URL没变，可能是AJAX加载，检查页面内容是否变化
                                time.sleep(1.0)
                                self.logger.info("✅ 页面内容已更新（AJAX加载）")
                                return True
                    
                except NoSuchElementException:
                    continue
                except Exception as e:
                    self.logger.warning(f"点击下一页按钮失败 {selector}: {e}")
                    continue
            
            self.logger.warning("⚠️ 未找到可用的下一页按钮")
            return False
            
        except Exception as e:
            self.logger.error(f"❌ 导航到下一页失败: {e}")
            return False
    
    def get_current_page_info(self, driver: webdriver.Chrome) -> Dict[str, Any]:
        """
        获取当前页面信息
        
        Args:
            driver: WebDriver实例
            
        Returns:
            页面信息字典
        """
        try:
            # 尝试获取页码信息
            page_info = {
                'url': driver.current_url,
                'title': driver.title,
                'current_page': 1,
                'total_pages': None,
                'has_next': self.has_next_page(driver)
            }
            
            # 尝试从URL中提取页码
            import re
            from urllib.parse import urlparse, parse_qs
            
            parsed_url = urlparse(driver.current_url)
            query_params = parse_qs(parsed_url.query)
            
            # 常见的页码参数
            page_params = ['page', 'p', 'pageNum', 'pageIndex', 'currentPage']
            for param in page_params:
                if param in query_params:
                    try:
                        page_info['current_page'] = int(query_params[param][0])
                        break
                    except (ValueError, IndexError):
                        continue
            
            # 尝试从页面元素中获取页码信息 - 使用最常见的选择器
            try:
                page_element = driver.find_element(By.CSS_SELECTOR, '.pagination .active')
                page_text = page_element.text.strip()
                if page_text.isdigit():
                    page_info['current_page'] = int(page_text)
            except:
                # 如果失败，尝试51job的页码选择器
                try:
                    page_element = driver.find_element(By.CSS_SELECTOR, '.current-page')
                    page_text = page_element.text.strip()
                    if page_text.isdigit():
                        page_info['current_page'] = int(page_text)
                except:
                    pass
            
            return page_info
            
        except Exception as e:
            self.logger.error(f"获取页面信息失败: {e}")
            return {'current_page': 1, 'has_next': False}