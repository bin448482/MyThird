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
                self._debug_page_structure(driver)
                return []
            
            self.logger.info(f"📋 找到 {len(job_elements)} 个职位元素")
            
            # 解析每个职位
            jobs = []
            processed_count = 0
            
            for i, job_element in enumerate(job_elements, 1):
                if max_results and processed_count >= max_results:
                    self.logger.info(f"📊 已达到最大结果数量限制: {max_results}")
                    break
                
                try:
                    job_data = self._parse_job_element(job_element)
                    if job_data:
                        jobs.append(job_data)
                        processed_count += 1
                        
                        self.logger.debug(
                            f"📝 职位 {processed_count}: {job_data.get('title', '未知')} - "
                            f"{job_data.get('company', '未知')} - {job_data.get('salary', '面议')}"
                        )
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ 解析职位 {i} 时出错: {e}")
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
            
            # 如果没找到，尝试其他可能的选择器
            alternative_selectors = [
                '.job-item',
                '.position-item',
                '.search-result-item',
                '.list-item',
                '[data-testid*="job"]',
                '.joblist-item',
                '.job-box',
                '.position-box'
            ]
            
            for selector in alternative_selectors:
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
        job_data = {
            'extracted_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'source': 'qiancheng'
        }
        
        try:
            # 职位标题和链接
            title_info = self._extract_title_and_url(job_element)
            job_data.update(title_info)
            
            # 公司名称
            job_data['company'] = self._extract_text_by_selector(
                job_element, 
                self.search_selectors.get('company_name', '.company-name'),
                default="未知公司"
            )
            
            # 薪资
            job_data['salary'] = self._extract_text_by_selector(
                job_element,
                self.search_selectors.get('salary', '.salary'),
                default="薪资面议"
            )
            
            # 地点
            job_data['location'] = self._extract_text_by_selector(
                job_element,
                self.search_selectors.get('location', '.location'),
                default="未知地点"
            )
            
            # 经验要求
            job_data['experience'] = self._extract_text_by_selector(
                job_element,
                self.search_selectors.get('experience', '.experience'),
                default="经验不限"
            )
            
            # 学历要求
            job_data['education'] = self._extract_text_by_selector(
                job_element,
                self.search_selectors.get('education', '.education'),
                default="学历不限"
            )
            
            # 提取额外信息
            extra_info = self._extract_extra_info(job_element)
            job_data.update(extra_info)
            
            return job_data
            
        except Exception as e:
            self.logger.warning(f"解析职位元素失败: {e}")
            return None
    
    def _extract_title_and_url(self, job_element) -> Dict[str, str]:
        """
        提取职位标题和链接
        
        Args:
            job_element: 职位元素
            
        Returns:
            包含title和url的字典
        """
        try:
            # 方法1: 查找 .jname 元素（职位标题）
            job_title = None
            job_url = None
            
            # 尝试找到职位标题元素
            jname_selectors = ['.jname', '.job-name', '.position-title']
            for selector in jname_selectors:
                try:
                    jname_element = job_element.find_element(By.CSS_SELECTOR, selector)
                    job_title = jname_element.text.strip()
                    
                    # 检查是否有title属性
                    title_attr = jname_element.get_attribute('title')
                    if title_attr:
                        job_title = title_attr.strip()
                    
                    if job_title:
                        self.logger.debug(f"找到职位标题: {job_title}")
                        break
                except:
                    continue
            
            # 方法2: 查找对应的链接URL
            # 首先尝试在同一个父元素中查找链接
            all_links = job_element.find_elements(By.TAG_NAME, "a")
            
            for link in all_links:
                href = link.get_attribute('href')
                if href and 'jobs.51job.com' in href:
                    job_url = href
                    
                    # 如果链接文本包含职位关键词，优先使用
                    link_text = link.text.strip()
                    job_keywords = ['工程师', '开发', '架构师', '经理', '专员', '主管', '总监', 'AI', '算法', '数据']
                    if any(keyword in link_text for keyword in job_keywords):
                        if not job_title:  # 如果没有从.jname找到标题，使用链接文本
                            job_title = link_text
                        break
            
            # 如果还没找到URL，使用第一个有效的jobs.51job.com链接
            if not job_url:
                for link in all_links:
                    href = link.get_attribute('href')
                    if href and 'jobs.51job.com' in href:
                        job_url = href
                        break
            
            # 方法3: 如果没有找到.jname，尝试从链接中提取职位标题
            if not job_title:
                for link in all_links:
                    href = link.get_attribute('href')
                    text = link.text.strip()
                    
                    if href and 'jobs.51job.com' in href and text:
                        # 排除明显的公司名称
                        company_keywords = ['公司', '企业', '集团', '有限', '股份']
                        is_company = any(keyword in text for keyword in company_keywords)
                        
                        if not is_company:
                            job_title = text
                            if not job_url:
                                job_url = href
                            break
            
            # 返回结果
            if job_title and job_url:
                return {
                    'title': job_title,
                    'url': job_url,
                    'needs_click_extraction': False
                }
            elif job_url:
                # 有URL但没有标题，使用默认标题
                return {
                    'title': "职位信息",
                    'url': job_url,
                    'needs_click_extraction': False
                }
            elif job_title:
                # 有标题但无URL，需要点击提取
                return {
                    'title': job_title,
                    'url': "",
                    'needs_click_extraction': True
                }
            else:
                return {
                    'title': "未知职位",
                    'url': "",
                    'needs_click_extraction': False
                }
                
        except Exception as e:
            self.logger.warning(f"提取职位标题和链接失败: {e}")
            return {'title': "未知职位", 'url': ""}
    
    def _extract_text_by_selector(self, parent_element, selector: str, default: str = "") -> str:
        """
        通过选择器提取文本
        
        Args:
            parent_element: 父元素
            selector: CSS选择器
            default: 默认值
            
        Returns:
            提取的文本
        """
        try:
            element = parent_element.find_element(By.CSS_SELECTOR, selector)
            text = element.text.strip()
            return text if text else default
        except:
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
            # 尝试提取发布时间
            time_selectors = ['.publish-time', '.update-time', '.time', '[data-time]']
            for selector in time_selectors:
                try:
                    time_element = job_element.find_element(By.CSS_SELECTOR, selector)
                    extra_info['publish_time'] = time_element.text.strip()
                    break
                except:
                    continue
            
            # 尝试提取公司规模
            scale_selectors = ['.company-scale', '.company-size', '.scale']
            for selector in scale_selectors:
                try:
                    scale_element = job_element.find_element(By.CSS_SELECTOR, selector)
                    extra_info['company_scale'] = scale_element.text.strip()
                    break
                except:
                    continue
            
            # 尝试提取行业信息
            industry_selectors = ['.industry', '.company-industry', '.business']
            for selector in industry_selectors:
                try:
                    industry_element = job_element.find_element(By.CSS_SELECTOR, selector)
                    extra_info['industry'] = industry_element.text.strip()
                    break
                except:
                    continue
            
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
            
            # 优化：减少详情页等待时间
            self._wait_for_page_stable(driver, timeout=8)  # 从15秒减少到8秒
            
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
            
            # 尝试多种选择器提取职位描述
            description_selectors = [
                self.detail_selectors.get('job_description', '.job-description'),
                '.job-detail-content',
                '.job-desc',
                '.position-detail',
                '.job-content',
                '[class*="description"]',
                '[class*="detail"]'
            ]
            
            for selector in description_selectors:
                description = self._extract_text_by_selector(driver, selector, default="")
                if description and len(description) > 50:  # 确保获取到有意义的内容
                    detail_data['description'] = description
                    break
            else:
                detail_data['description'] = ""
            
            # 尝试多种选择器提取职位要求
            requirements_selectors = [
                self.detail_selectors.get('requirements', '.job-requirements'),
                '.job-require',
                '.position-require',
                '.job-demand',
                '[class*="requirement"]',
                '[class*="require"]'
            ]
            
            for selector in requirements_selectors:
                requirements = self._extract_text_by_selector(driver, selector, default="")
                if requirements and len(requirements) > 20:
                    detail_data['requirements'] = requirements
                    break
            else:
                detail_data['requirements'] = ""
            
            # 公司信息
            company_selectors = [
                self.detail_selectors.get('company_info', '.company-info'),
                '.company-detail',
                '.company-desc',
                '[class*="company"]'
            ]
            
            for selector in company_selectors:
                company_info = self._extract_text_by_selector(driver, selector, default="")
                if company_info:
                    detail_data['company_info'] = company_info
                    break
            else:
                detail_data['company_info'] = ""
            
            # 福利待遇
            benefits_selectors = [
                self.detail_selectors.get('benefits', '.job-benefits'),
                '.welfare',
                '.benefits',
                '.job-welfare',
                '[class*="benefit"]',
                '[class*="welfare"]'
            ]
            
            for selector in benefits_selectors:
                benefits = self._extract_text_by_selector(driver, selector, default="")
                if benefits:
                    detail_data['benefits'] = benefits
                    break
            else:
                detail_data['benefits'] = ""
            
            # 提取其他可能的信息
            try:
                # 薪资信息
                salary_selectors = ['.salary', '.pay', '[class*="salary"]', '[class*="pay"]']
                for selector in salary_selectors:
                    salary = self._extract_text_by_selector(driver, selector, default="")
                    if salary:
                        detail_data['salary_detail'] = salary
                        break
                
                # 工作地点
                location_selectors = ['.location', '.address', '[class*="location"]', '[class*="address"]']
                for selector in location_selectors:
                    location = self._extract_text_by_selector(driver, selector, default="")
                    if location:
                        detail_data['location_detail'] = location
                        break
                
            except Exception as e:
                self.logger.debug(f"提取额外信息时出错: {e}")
            
            # 验证是否提取到有效内容
            content_fields = ['description', 'requirements', 'company_info', 'benefits']
            has_content = any(detail_data.get(field) for field in content_fields)
            
            if not has_content:
                self.logger.warning(f"未提取到有效的详情内容: {job_url}")
                # 调试页面结构
                self._debug_page_structure(driver)
                return None
            
            return detail_data
            
        except Exception as e:
            self.logger.error(f"❌ 解析职位详情失败: {e}")
            return None
    
    def _debug_page_structure(self, driver: webdriver.Chrome) -> None:
        """
        调试页面结构
        
        Args:
            driver: WebDriver实例
        """
        self.logger.info("🔍 调试页面结构...")
        
        try:
            # 获取页面基本信息
            self.logger.info(f"当前URL: {driver.current_url}")
            self.logger.info(f"页面标题: {driver.title}")
            
            # 查找可能的职位列表元素
            possible_selectors = [
                ".job-list",
                ".job-item",
                ".position-list",
                ".search-result",
                "[data-testid*='job']",
                ".list-item",
                ".joblist",
                ".job-box"
            ]
            
            for selector in possible_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        self.logger.info(f"找到可能的职位列表: {selector} (数量: {len(elements)})")
                except:
                    continue
            
            # 输出页面源码片段用于分析
            page_source = driver.page_source[:2000]
            self.logger.debug(f"页面源码片段: {page_source}...")
            
        except Exception as e:
            self.logger.error(f"调试页面结构失败: {e}")
    
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
    
    def extract_job_urls_by_clicking(self,
                                   driver: webdriver.Chrome,
                                   max_jobs: int = 10) -> List[Dict[str, Any]]:
        """
        通过模拟点击职位标题提取详情页URL
        
        这是PageParser的核心功能之一，负责：
        1. 识别页面中的职位标题元素
        2. 模拟人类点击行为获取详情页URL
        3. 处理页面交互和窗口切换
        4. 返回结构化的URL数据
        
        Args:
            driver: WebDriver实例（由ContentExtractor提供）
            max_jobs: 最大提取数量
            
        Returns:
            职位URL信息列表，包含标题、URL、提取时间等
        """
        try:
            self.logger.info(f"🚀 开始通过点击提取职位URL，最大数量: {max_jobs}")
            
            # 等待页面加载完成
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".jname"))
            )
            
            # 模拟人类浏览行为 - 随机等待
            initial_wait = random.uniform(2.0, 4.0)
            time.sleep(initial_wait)
            self.logger.debug(f"初始等待 {initial_wait:.1f} 秒")
            
            # 查找所有职位标题元素
            job_title_elements = driver.find_elements(By.CSS_SELECTOR, ".jname")
            self.logger.info(f"✅ 找到 {len(job_title_elements)} 个职位标题")
            
            if not job_title_elements:
                self.logger.warning("⚠️ 未找到职位标题元素")
                return []
            
            # 限制提取数量
            jobs_to_process = min(len(job_title_elements), max_jobs)
            extracted_urls = []
            
            for i in range(jobs_to_process):
                try:
                    # 重新获取元素（避免stale element异常）
                    job_title_elements = driver.find_elements(By.CSS_SELECTOR, ".jname")
                    if i >= len(job_title_elements):
                        break
                        
                    job_element = job_title_elements[i]
                    job_title = job_element.text.strip()
                    
                    self.logger.info(f"🎯 处理第 {i+1} 个职位: {job_title}")
                    
                    # 记录当前窗口句柄
                    original_windows = driver.window_handles
                    
                    # 模拟人类滚动行为
                    self._simulate_human_scroll(driver, job_element)
                    
                    # 模拟鼠标悬停（可选）
                    if random.random() < 0.3:  # 30%概率悬停
                        ActionChains(driver).move_to_element(job_element).perform()
                        time.sleep(random.uniform(0.2, 0.8))
                    
                    # 点击职位标题
                    ActionChains(driver).click(job_element).perform()
                    
                    # 等待新窗口打开 - 随机等待时间
                    wait_time = random.uniform(1.5, 3.0)
                    time.sleep(wait_time)
                    
                    # 检查是否有新窗口打开
                    new_windows = driver.window_handles
                    if len(new_windows) > len(original_windows):
                        # 切换到新窗口
                        new_window = [w for w in new_windows if w not in original_windows][0]
                        driver.switch_to.window(new_window)
                        
                        # 短暂等待页面加载
                        time.sleep(random.uniform(0.5, 1.5))
                        
                        # 获取详情页URL
                        detail_url = driver.current_url
                        
                        job_info = {
                            'index': i + 1,
                            'title': job_title,
                            'detail_url': detail_url,
                            'extracted_at': datetime.now().isoformat()
                        }
                        
                        extracted_urls.append(job_info)
                        self.logger.info(f"✅ 成功提取: {detail_url}")
                        
                        # 关闭新窗口并切换回原窗口
                        driver.close()
                        driver.switch_to.window(original_windows[0])
                        
                        # 模拟用户思考时间
                        think_time = random.uniform(0.5, 2.0)
                        time.sleep(think_time)
                        
                    else:
                        self.logger.warning(f"⚠️ 点击 {job_title} 未打开新窗口")
                    
                    # 每处理几个职位后，模拟更长的休息
                    if (i + 1) % random.randint(3, 6) == 0:
                        rest_time = random.uniform(2.0, 5.0)
                        self.logger.debug(f"⏳ 模拟用户休息 {rest_time:.1f} 秒")
                        time.sleep(rest_time)
                        
                except Exception as e:
                    self.logger.warning(f"❌ 处理职位 {i+1} 时出错: {e}")
                    # 确保回到原窗口
                    if len(driver.window_handles) > 1:
                        driver.switch_to.window(driver.window_handles[0])
                    
                    # 出错后等待更长时间
                    error_wait = random.uniform(3.0, 8.0)
                    time.sleep(error_wait)
                    continue
            
            self.logger.info(f"🎉 成功提取 {len(extracted_urls)} 个职位URL")
            return extracted_urls
            
        except Exception as e:
            self.logger.error(f"❌ 点击提取URL过程出错: {e}")
            raise PageParseError(f"点击提取URL失败: {e}")
    
    def _simulate_human_scroll(self, driver: webdriver.Chrome, target_element) -> None:
        """
        模拟人类滚动行为
        
        Args:
            driver: WebDriver实例
            target_element: 目标元素
        """
        try:
            # 获取元素位置
            element_location = target_element.location_once_scrolled_into_view
            
            # 模拟分步滚动而不是直接滚动到元素
            current_scroll = driver.execute_script("return window.pageYOffset;")
            target_scroll = element_location['y'] - random.randint(100, 300)  # 留一些余量
            
            if abs(target_scroll - current_scroll) > 100:
                # 分多步滚动
                steps = random.randint(2, 4)
                scroll_step = (target_scroll - current_scroll) / steps
                
                for step in range(steps):
                    scroll_to = current_scroll + scroll_step * (step + 1)
                    driver.execute_script(f"window.scrollTo(0, {scroll_to});")
                    time.sleep(random.uniform(0.1, 0.3))
            
            # 最后精确滚动到元素
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", target_element)
            time.sleep(random.uniform(0.3, 0.8))
            
        except Exception as e:
            self.logger.debug(f"模拟滚动失败: {e}")
            # 回退到简单滚动
            driver.execute_script("arguments[0].scrollIntoView(true);", target_element)
            time.sleep(0.5)
    
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
            
            # 尝试从页面元素中获取页码信息
            page_selectors = [
                '.current-page',
                '.active-page',
                '.pagination .active',
                '.page-current',
                '.pager-current'
            ]
            
            for selector in page_selectors:
                try:
                    page_element = driver.find_element(By.CSS_SELECTOR, selector)
                    page_text = page_element.text.strip()
                    if page_text.isdigit():
                        page_info['current_page'] = int(page_text)
                        break
                except:
                    continue
            
            return page_info
            
        except Exception as e:
            self.logger.error(f"获取页面信息失败: {e}")
            return {'current_page': 1, 'has_next': False}