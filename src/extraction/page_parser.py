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
                if max_results and processed_count >= max_results:
                    break
                
                try:
                    job_data = self._parse_job_element(job_element)
                    
                    if job_data:
                        jobs.append(job_data)
                        processed_count += 1
                        
                        # 只在每10个职位时输出一次进度
                        if processed_count % 10 == 0 or processed_count <= 5:
                            self.logger.info(f"✅ 已处理 {processed_count} 个职位")
                    
                except Exception as e:
                    self.logger.warning(f"❌ 解析职位 {i} 失败: {str(e)[:50]}...")
                    continue
            
            self.logger.info(f"✅ 职位列表解析完成，共解析 {len(jobs)} 个职位")
            return jobs
            
        except Exception as e:
            self.logger.error(f"❌ 解析职位列表失败: {e}")
            raise PageParseError(f"解析职位列表失败: {e}")
    
    def _wait_for_page_stable(self, driver: webdriver.Chrome, timeout: int = 3) -> None:
        """
        等待页面稳定加载（超快速版本）
        
        Args:
            driver: WebDriver实例
            timeout: 超时时间（默认3秒）
        """
        try:
            # 大幅减少超时时间，快速失败
            WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except TimeoutException:
            # 快速失败，不记录详细日志
            pass
    
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
        解析单个职位元素（高性能版本）
        """
        try:
            job_data = {
                'extracted_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'qiancheng',
                'url': "",
                'needs_click_extraction': True
            }
            
            # 快速提取标题
            job_data['title'] = self._extract_title_fast(job_element)
            
            # 快速批量提取字段
            field_data = self._extract_multiple_fields_fast(job_element)
            job_data.update(field_data)
            
            # 生成职位指纹
            job_data['job_fingerprint'] = generate_job_fingerprint(
                job_data.get('title', ''),
                job_data.get('company', ''),
                job_data.get('salary', ''),
                job_data.get('location', '')
            )
            
            return job_data
            
        except Exception as e:
            return None
    
    def _extract_title_fast(self, job_element) -> str:
        """快速提取职位标题 - JavaScript增强版"""
        try:
            # 方法1: 标准Selenium提取
            for selector in ['.jname a', '.jname', '.job-title']:
                try:
                    element = job_element.find_element(By.CSS_SELECTOR, selector)
                    text = element.text.strip()
                    if text:
                        return text
                    # 尝试title属性
                    title = element.get_attribute('title')
                    if title:
                        return title.strip()
                except:
                    continue
            
            # 方法2: JavaScript提取 - 针对动态内容和属性提取
            try:
                # 获取driver实例（通过job_element的parent获取）
                driver = job_element._parent
                
                title = driver.execute_script("""
                    var parentElement = arguments[0];
                    
                    // 针对HTML结构：<span class="jname text-cut" title="职位标题">职位标题</span>
                    var jnameElement = parentElement.querySelector('.jname');
                    if (jnameElement) {
                        // 优先使用title属性（最可靠）
                        var titleAttr = jnameElement.getAttribute('title');
                        if (titleAttr && titleAttr.trim()) {
                            return titleAttr.trim();
                        }
                        
                        // 其次使用textContent（处理动态内容）
                        var textContent = jnameElement.textContent || jnameElement.innerText;
                        if (textContent && textContent.trim()) {
                            return textContent.trim();
                        }
                        
                        // 尝试子元素的文本内容
                        var childLink = jnameElement.querySelector('a');
                        if (childLink) {
                            var linkText = childLink.textContent || childLink.innerText || childLink.getAttribute('title');
                            if (linkText && linkText.trim()) {
                                return linkText.trim();
                            }
                        }
                    }
                    
                    // 备用选择器
                    var backupSelectors = ['.job-title', '[class*="jname"]', '[title]'];
                    for (var i = 0; i < backupSelectors.length; i++) {
                        var element = parentElement.querySelector(backupSelectors[i]);
                        if (element) {
                            var text = element.getAttribute('title') ||
                                      element.textContent ||
                                      element.innerText;
                            if (text && text.trim()) {
                                return text.trim();
                            }
                        }
                    }
                    
                    return '';
                """, job_element)
                
                if title and title.strip():
                    self.logger.debug(f"✅ JavaScript提取职位标题成功: {title}")
                    return title.strip()
                    
            except Exception as e:
                self.logger.debug(f"JavaScript提取职位标题失败: {e}")
            
            return "未知职位"
        except:
            return "未知职位"
    
    def _extract_title(self, job_element) -> str:
        """保留原方法以兼容性"""
        return self._extract_title_fast(job_element)
    
    def _extract_text_by_selector(self, parent_element, selector: str, default: str = "") -> str:
        """通过选择器提取文本（超快速版本）"""
        try:
            element = parent_element.find_element(By.CSS_SELECTOR, selector)
            text = element.text.strip()
            return text if text else default
        except:
            return default
    
    def _extract_multiple_fields_fast(self, job_element) -> Dict[str, str]:
        """超高性能批量提取 - JavaScript增强版"""
        try:
            # 方法1: 标准Selenium提取
            all_elements = job_element.find_elements(By.CSS_SELECTOR,
                '.cname a, .cname, .area, .sal, .experience, .education')
            
            # 预设默认值
            results = {
                'company': "未知公司",
                'location': "未知地点",
                'salary': "薪资面议",
                'experience': "经验不限",
                'education': "学历不限"
            }
            
            # 遍历找到的元素，根据类名快速分类
            for element in all_elements:
                try:
                    classes = element.get_attribute('class') or ''
                    text = element.text.strip()
                    if not text:
                        text = element.get_attribute('title') or ''
                        text = text.strip()
                    
                    if not text:
                        continue
                    
                    # 快速分类匹配
                    if 'cname' in classes and results['company'] == "未知公司":
                        results['company'] = text
                    elif 'area' in classes and results['location'] == "未知地点":
                        results['location'] = text
                    elif 'sal' in classes and results['salary'] == "薪资面议":
                        results['salary'] = text
                    elif 'experience' in classes and results['experience'] == "经验不限":
                        results['experience'] = text
                    elif 'education' in classes and results['education'] == "学历不限":
                        results['education'] = text
                        
                except:
                    continue
            
            # 方法2: JavaScript提取 - 处理未提取到的字段
            try:
                # 检查哪些字段还是默认值，需要JavaScript提取
                missing_fields = [k for k, v in results.items() if v.startswith("未知") or v.startswith("薪资面议") or v.startswith("经验不限") or v.startswith("学历不限")]
                
                if missing_fields:
                    driver = job_element._parent
                    js_results = driver.execute_script("""
                        var parentElement = arguments[0];
                        var results = {};
                        
                        // 提取公司名称
                        var companySelectors = ['.cname a', '.cname', '[class*="cname"]', '.company'];
                        for (var i = 0; i < companySelectors.length; i++) {
                            var element = parentElement.querySelector(companySelectors[i]);
                            if (element) {
                                var text = element.textContent || element.innerText || element.getAttribute('title');
                                if (text && text.trim()) {
                                    results.company = text.trim();
                                    break;
                                }
                            }
                        }
                        
                        // 提取地点
                        var locationSelectors = ['.area', '[class*="area"]', '.location'];
                        for (var i = 0; i < locationSelectors.length; i++) {
                            var element = parentElement.querySelector(locationSelectors[i]);
                            if (element) {
                                var text = element.textContent || element.innerText || element.getAttribute('title');
                                if (text && text.trim()) {
                                    results.location = text.trim();
                                    break;
                                }
                            }
                        }
                        
                        // 提取薪资
                        var salarySelectors = ['.sal', '[class*="sal"]', '.salary'];
                        for (var i = 0; i < salarySelectors.length; i++) {
                            var element = parentElement.querySelector(salarySelectors[i]);
                            if (element) {
                                var text = element.textContent || element.innerText || element.getAttribute('title');
                                if (text && text.trim()) {
                                    results.salary = text.trim();
                                    break;
                                }
                            }
                        }
                        
                        // 提取经验要求
                        var expSelectors = ['.experience', '[class*="experience"]', '.exp'];
                        for (var i = 0; i < expSelectors.length; i++) {
                            var element = parentElement.querySelector(expSelectors[i]);
                            if (element) {
                                var text = element.textContent || element.innerText || element.getAttribute('title');
                                if (text && text.trim()) {
                                    results.experience = text.trim();
                                    break;
                                }
                            }
                        }
                        
                        // 提取学历要求
                        var eduSelectors = ['.education', '[class*="education"]', '.edu'];
                        for (var i = 0; i < eduSelectors.length; i++) {
                            var element = parentElement.querySelector(eduSelectors[i]);
                            if (element) {
                                var text = element.textContent || element.innerText || element.getAttribute('title');
                                if (text && text.trim()) {
                                    results.education = text.trim();
                                    break;
                                }
                            }
                        }
                        
                        return results;
                    """, job_element)
                    
                    # 更新结果，只覆盖成功提取的字段
                    if js_results:
                        for field in missing_fields:
                            if field in js_results and js_results[field]:
                                results[field] = js_results[field]
                                self.logger.debug(f"✅ JavaScript提取{field}成功: {js_results[field]}")
                        
            except Exception as e:
                self.logger.debug(f"JavaScript批量提取失败: {e}")
            
            return results
            
        except:
            return {
                'company': "未知公司",
                'location': "未知地点",
                'salary': "薪资面议",
                'experience': "经验不限",
                'education': "学历不限"
            }

    
    
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
            
            # 统一使用快速等待，不区分模式
            self._wait_for_page_stable(driver, timeout=2)  # 统一2秒快速等待
            
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
                self.search_selectors.get('next_page', '.btn-next'),  # 修正默认值
                '.btn-next',           # 51job实际使用的选择器
                'button.btn-next',     # 更具体的按钮选择器
                '.btn_next',           # 旧版本选择器
                '.next',
                '.page-next',
                '.next-page',
                '.pager-next',
                'a[title*="下一页"]',
                'a[title*="next"]',
                '.pagination .next',
                '.pagination-next',
                '.page-item.next a',
                '.page-link[aria-label*="Next"]'
            ]
            
            self.logger.debug(f"🔍 检查下一页按钮，优先使用: {next_page_selectors[0]}")
            
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
    
    def navigate_to_next_page(self, driver: webdriver.Chrome, current_page: Optional[int] = None) -> bool:
        """
        导航到下一页 - 增强版AJAX检测和重试恢复机制
        
        Args:
            driver: WebDriver实例
            current_page: 当前页码（可选），如果提供则使用，否则自动检测
            
        Returns:
            是否成功导航到下一页
        """
        try:
            self.logger.info("🔄 尝试导航到下一页")
            
            # 获取当前页码信息
            if current_page is not None:
                current_page_number = current_page
                self.logger.info(f"📄 使用传入的当前页码: {current_page_number}")
            else:
                current_page_info = self.get_current_page_info(driver)
                current_page_number = current_page_info.get('current_page', 1)
                self.logger.info(f"📄 检测到的当前页码: {current_page_number}")
            
            target_page_number = current_page_number + 1
            
            self.logger.info(f"📄 当前页码: {current_page_number}, 目标页码: {target_page_number}")
            
            # 记录当前页面状态用于验证
            current_url = driver.current_url
            current_page_signature = self._get_page_content_signature(driver)
            
            # 第一次尝试：标准下一页导航
            if self._attempt_next_page_click(driver, current_url, current_page_signature, current_page_number):
                self.logger.info("✅ 标准下一页导航成功")
                return True
            
            # 第二次尝试：刷新页面并恢复到目标页码
            self.logger.warning("⚠️ 标准下一页导航失败，尝试刷新页面恢复")
            if self._recover_to_target_page(driver, target_page_number):
                self.logger.info("✅ 页面刷新恢复成功")
                return True
            
            self.logger.error("❌ 所有导航尝试都失败")
            return False
            
        except Exception as e:
            self.logger.error(f"❌ 导航到下一页失败: {e}")
            return False
    
    def _attempt_next_page_click(self, driver: webdriver.Chrome, current_url: str, current_page_signature: str, current_page_number: int) -> bool:
        """
        尝试点击下一页按钮
        
        Args:
            driver: WebDriver实例
            current_url: 当前URL
            current_page_signature: 当前页面签名
            current_page_number: 当前页码
            
        Returns:
            是否成功
        """
        try:
            target_page = current_page_number + 1
            self.logger.info(f"🎯 尝试从第 {current_page_number} 页导航到第 {target_page} 页")
            
            # 方法1: 优先尝试下一页按钮（最自然的导航方式）
            next_page_selectors = [
                'button.btn-next',      # 51job主要选择器
                '.btn-next',            # 备用选择器
                '.next',                # 通用选择器
                '.page-next'            # 另一种可能
            ]
            
            for selector in next_page_selectors:
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, selector)
                    
                    # 检查按钮是否可用
                    if next_button.is_enabled() and next_button.is_displayed():
                        classes = next_button.get_attribute('class') or ''
                        disabled_attr = next_button.get_attribute('disabled')
                        
                        if 'disabled' not in classes.lower() and not disabled_attr:
                            self.logger.info(f"➡️ 点击下一页按钮: {selector}")
                            
                            # 滚动到按钮位置
                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_button)
                            time.sleep(0.3)
                            
                            # 点击下一页按钮
                            ActionChains(driver).click(next_button).perform()
                            
                            # 验证页面跳转是否成功
                            if self._verify_page_navigation(driver, current_url, current_page_signature, target_page):
                                self.logger.info(f"✅ 下一页按钮点击成功，已到达第 {target_page} 页")
                                return True
                    
                except NoSuchElementException:
                    continue
                except Exception as e:
                    self.logger.debug(f"下一页按钮点击失败 {selector}: {e}")
                    continue
            
            # 方法2: 下一页按钮失败后，尝试直接点击目标页码（备选方案）
            self.logger.warning("⚠️ 下一页按钮不可用，尝试直接页码点击")
            try:
                # 使用JavaScript查找目标页码链接
                page_link = driver.execute_script(f"""
                    var links = document.querySelectorAll('.pagination a, .page-item a, .pager a');
                    for (var i = 0; i < links.length; i++) {{
                        if (links[i].textContent.trim() === '{target_page}') {{
                            return links[i];
                        }}
                    }}
                    return null;
                """)
                
                if page_link:
                    self.logger.info(f"🔢 直接点击页码 {target_page}")
                    
                    # 滚动到页码位置
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", page_link)
                    time.sleep(0.5)
                    
                    # 点击页码
                    ActionChains(driver).click(page_link).perform()
                    
                    # 验证页面跳转是否成功
                    if self._verify_page_navigation(driver, current_url, current_page_signature, target_page):
                        self.logger.info(f"✅ 直接页码点击成功，已到达第 {target_page} 页")
                        return True
                        
            except Exception as e:
                self.logger.debug(f"直接页码点击失败: {e}")
            
            self.logger.warning("⚠️ 所有导航方法都失败了")
            return False
            
        except Exception as e:
            self.logger.error(f"尝试点击下一页失败: {e}")
            return False
    
    def _recover_to_target_page(self, driver: webdriver.Chrome, target_page_number: int) -> bool:
        """
        刷新页面并恢复到目标页码
        
        Args:
            driver: WebDriver实例
            target_page_number: 目标页码
            
        Returns:
            是否成功恢复
        """
        try:
            self.logger.info(f"🔄 开始页面恢复流程，目标页码: {target_page_number}")
            
            # 刷新页面（回到第1页）
            self.logger.info("🔄 刷新页面...")
            driver.refresh()
            
            # 等待页面加载
            time.sleep(3)
            
            # 🔧 FIX: 页面刷新后重新应用薪资过滤器
            self.logger.info("🔧 FIX: 页面刷新后重新应用薪资过滤器")
            self._reapply_salary_filter(driver)
            
            # 验证是否回到第1页
            page_info = self.get_current_page_info(driver)
            current_page = page_info.get('current_page', 1)
            self.logger.info(f"📄 刷新后当前页码: {current_page}")
            
            # 🐛 DEBUG: 检查页面刷新后的状态
            self.logger.warning("🐛 DEBUG: 页面刷新后需要重新应用薪资过滤器")
            self.logger.warning("🐛 DEBUG: 当前页面URL: " + driver.current_url)
            
            # 如果目标页码是1，直接返回成功
            if target_page_number <= 1:
                self.logger.info("✅ 目标页码为1，恢复完成")
                return True
            
            # 逐页导航到目标页码
            return self._navigate_to_specific_page(driver, target_page_number)
            
        except Exception as e:
            self.logger.error(f"页面恢复失败: {e}")
            return False
    
    def _navigate_to_specific_page(self, driver: webdriver.Chrome, target_page: int) -> bool:
        """
        导航到指定页码
        
        Args:
            driver: WebDriver实例
            target_page: 目标页码
            
        Returns:
            是否成功导航
        """
        try:
            self.logger.info(f"🎯 开始导航到第 {target_page} 页")
            
            # 获取当前页码
            current_page_info = self.get_current_page_info(driver)
            current_page = current_page_info.get('current_page', 1)
            
            # 🐛 DEBUG: 详细记录页码检测信息
            self.logger.warning(f"🐛 DEBUG: 当前页码检测结果: {current_page_info}")
            self.logger.warning(f"🐛 DEBUG: 当前URL: {driver.current_url}")
            
            # 如果已经在目标页，直接返回成功
            if current_page == target_page:
                self.logger.info(f"✅ 已在目标页 {target_page}")
                return True
            
            # 尝试直接点击页码按钮
            if self._try_direct_page_click(driver, target_page):
                self.logger.info(f"✅ 直接点击页码 {target_page} 成功")
                return True
            
            # 如果直接点击失败，逐页导航
            self.logger.info(f"🔄 开始逐页导航从第 {current_page} 页到第 {target_page} 页")
            
            for step in range(current_page, target_page):
                self.logger.info(f"📄 导航到第 {step + 1} 页...")
                
                # 🐛 DEBUG: 记录导航前状态
                pre_nav_url = driver.current_url
                self.logger.warning(f"🐛 DEBUG: 导航前URL: {pre_nav_url}")
                
                # 尝试点击下一页
                if not self._attempt_single_next_page_click(driver):
                    self.logger.error(f"❌ 导航到第 {step + 1} 页失败")
                    return False
                
                # 验证页码
                time.sleep(2)  # 等待页面加载
                page_info = self.get_current_page_info(driver)
                actual_page = page_info.get('current_page', 1)
                
                # 🐛 DEBUG: 记录导航后状态
                post_nav_url = driver.current_url
                self.logger.warning(f"🐛 DEBUG: 导航后URL: {post_nav_url}")
                self.logger.warning(f"🐛 DEBUG: URL是否变化: {pre_nav_url != post_nav_url}")
                self.logger.warning(f"🐛 DEBUG: 页码检测结果: {page_info}")
                
                if actual_page != step + 1:
                    self.logger.error(f"❌ 页码验证失败，期望第 {step + 1} 页，实际第 {actual_page} 页")
                    self.logger.error(f"🐛 DEBUG: 可能的原因 - 页码检测逻辑错误或页面未正确跳转")
                    return False
                
                self.logger.info(f"✅ 成功到达第 {actual_page} 页")
            
            return True
            
        except Exception as e:
            self.logger.error(f"导航到指定页码失败: {e}")
            return False
    
    def _try_direct_page_click(self, driver: webdriver.Chrome, target_page: int) -> bool:
        """
        尝试直接点击页码按钮
        
        Args:
            driver: WebDriver实例
            target_page: 目标页码
            
        Returns:
            是否成功
        """
        try:
            # 尝试多种页码选择器
            page_selectors = [
                f'a[href*="page={target_page}"]',  # 包含page参数的链接
                f'a[href*="p={target_page}"]',     # 包含p参数的链接
                f'.pagination a:contains("{target_page}")',  # 分页器中的页码
                f'.page-item a:contains("{target_page}")',   # Bootstrap样式页码
                f'a:contains("{target_page}")'     # 任何包含页码的链接
            ]
            
            for selector in page_selectors:
                try:
                    # 使用JavaScript查找包含目标页码的元素
                    page_element = driver.execute_script(f"""
                        var elements = document.querySelectorAll('a');
                        for (var i = 0; i < elements.length; i++) {{
                            var element = elements[i];
                            if (element.textContent && element.textContent.trim() === '{target_page}') {{
                                return element;
                            }}
                        }}
                        return null;
                    """)
                    
                    if page_element:
                        self.logger.info(f"找到页码 {target_page} 的直接链接")
                        
                        # 滚动到元素位置
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", page_element)
                        time.sleep(0.5)
                        
                        # 点击页码
                        page_element.click()
                        time.sleep(2)
                        
                        # 验证是否成功
                        page_info = self.get_current_page_info(driver)
                        actual_page = page_info.get('current_page', 1)
                        
                        if actual_page == target_page:
                            return True
                    
                except Exception as e:
                    self.logger.debug(f"直接页码点击失败 {selector}: {e}")
                    continue
            
            return False
            
        except Exception as e:
            self.logger.debug(f"尝试直接页码点击失败: {e}")
            return False
    
    def _attempt_single_next_page_click(self, driver: webdriver.Chrome) -> bool:
        """
        尝试单次下一页点击（用于逐页导航）
        
        Args:
            driver: WebDriver实例
            
        Returns:
            是否成功
        """
        try:
            next_page_selectors = [
                'button.btn-next',
                '.btn-next',
                '.next',
                '.page-next'
            ]
            
            for selector in next_page_selectors:
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if next_button.is_enabled() and next_button.is_displayed():
                        classes = next_button.get_attribute('class') or ''
                        disabled_attr = next_button.get_attribute('disabled')
                        
                        if 'disabled' not in classes.lower() and not disabled_attr:
                            # 滚动到按钮位置
                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_button)
                            time.sleep(0.3)
                            
                            # 点击按钮
                            ActionChains(driver).click(next_button).perform()
                            return True
                    
                except NoSuchElementException:
                    continue
                except Exception as e:
                    self.logger.debug(f"单次下一页点击失败 {selector}: {e}")
                    continue
            
            return False
            
        except Exception as e:
            self.logger.debug(f"单次下一页点击失败: {e}")
            return False
    
    def _get_page_content_signature(self, driver: webdriver.Chrome) -> str:
        """
        获取页面内容签名，用于检测AJAX更新
        
        Args:
            driver: WebDriver实例
            
        Returns:
            页面内容签名字符串
        """
        try:
            # 获取职位列表的关键信息作为签名
            signature_data = driver.execute_script("""
                // 获取职位列表的关键信息
                var jobElements = document.querySelectorAll('.joblist-item, .job-item');
                var signatures = [];
                
                for (var i = 0; i < Math.min(jobElements.length, 5); i++) {
                    var job = jobElements[i];
                    var title = '';
                    var company = '';
                    
                    // 提取职位标题
                    var titleEl = job.querySelector('.jname a, .jname, .job-title');
                    if (titleEl) title = titleEl.textContent.trim();
                    
                    // 提取公司名称
                    var companyEl = job.querySelector('.cname a, .cname, .company');
                    if (companyEl) company = companyEl.textContent.trim();
                    
                    if (title || company) {
                        signatures.push(title + '|' + company);
                    }
                }
                
                return signatures.join('::');
            """)
            
            return str(signature_data) if signature_data else ""
            
        except Exception as e:
            self.logger.debug(f"获取页面签名失败: {e}")
            return ""
    
    def _verify_page_navigation(self, driver: webdriver.Chrome, original_url: str, original_signature: str, expected_page: Optional[int] = None) -> bool:
        """
        验证页面导航是否成功
        
        Args:
            driver: WebDriver实例
            original_url: 原始URL
            original_signature: 原始页面签名
            expected_page: 期望的目标页码
            
        Returns:
            是否成功导航
        """
        max_attempts = 10  # 最多检查10次
        wait_interval = 0.5  # 每次等待0.5秒
        
        for attempt in range(max_attempts):
            try:
                # 等待一小段时间让页面更新
                time.sleep(wait_interval)
                
                # 优先检查页码是否正确（如果提供了expected_page）
                if expected_page is not None:
                    current_page_info = self.get_current_page_info(driver)
                    current_page = current_page_info.get('current_page', 1)
                    
                    if current_page == expected_page:
                        self.logger.info(f"✅ 页码验证成功，已到达第 {expected_page} 页")
                        return True
                    elif attempt < max_attempts - 1:  # 不是最后一次尝试
                        self.logger.debug(f"页码检测为 {current_page}，期望 {expected_page}，继续等待... (尝试 {attempt + 1}/{max_attempts})")
                        continue
                
                # 检查URL是否变化
                current_url = driver.current_url
                if current_url != original_url:
                    self.logger.info(f"✅ URL已变化，成功导航到下一页: {current_url}")
                    return True
                
                # 检查页面内容是否变化（AJAX情况）
                current_signature = self._get_page_content_signature(driver)
                if current_signature and current_signature != original_signature:
                    self.logger.info("✅ 页面内容已更新（AJAX加载）")
                    # 额外验证：检查是否有新的职位元素
                    if self._verify_new_job_content(driver):
                        return True
                
                # 检查页面是否正在加载
                if self._is_page_loading(driver):
                    self.logger.debug(f"页面正在加载中... (尝试 {attempt + 1}/{max_attempts})")
                    continue
                
            except Exception as e:
                self.logger.debug(f"验证页面导航时出错 (尝试 {attempt + 1}): {e}")
                continue
        
        self.logger.warning("⚠️ 页面导航验证失败，内容可能未更新")
        return False
    
    def _verify_new_job_content(self, driver: webdriver.Chrome) -> bool:
        """
        验证是否有新的职位内容加载
        
        Args:
            driver: WebDriver实例
            
        Returns:
            是否有新内容
        """
        try:
            # 检查职位列表是否存在且有内容
            job_elements = driver.find_elements(By.CSS_SELECTOR, '.joblist-item, .job-item')
            if len(job_elements) > 0:
                # 检查第一个职位是否有有效内容
                first_job = job_elements[0]
                title_element = first_job.find_element(By.CSS_SELECTOR, '.jname a, .jname, .job-title')
                if title_element and title_element.text.strip():
                    self.logger.debug(f"验证成功：找到 {len(job_elements)} 个职位，第一个职位: {title_element.text.strip()}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"验证新职位内容失败: {e}")
            return False
    
    def _is_page_loading(self, driver: webdriver.Chrome) -> bool:
        """
        检查页面是否正在加载
        
        Args:
            driver: WebDriver实例
            
        Returns:
            是否正在加载
        """
        try:
            # 检查页面加载状态
            ready_state = driver.execute_script("return document.readyState")
            if ready_state != "complete":
                return True
            
            # 检查是否有加载指示器
            loading_indicators = driver.find_elements(By.CSS_SELECTOR,
                '.loading, .spinner, .loader, [class*="loading"], [class*="spinner"]')
            
            for indicator in loading_indicators:
                if indicator.is_displayed():
                    return True
            
            return False
            
        except Exception:
            return False
    
    def get_current_page_info(self, driver: webdriver.Chrome) -> Dict[str, Any]:
        """
        获取当前页面信息（增强版页码检测）
        
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
            
            # 🔧 FIX: 增强页码检测逻辑
            detected_page = self._detect_current_page_enhanced(driver)
            page_info['current_page'] = detected_page
            
            return page_info
            
        except Exception as e:
            self.logger.error(f"获取页面信息失败: {e}")
            return {'current_page': 1, 'has_next': False}
    
    def _detect_current_page_enhanced(self, driver: webdriver.Chrome) -> int:
        """
        简化版页码检测方法 - 专注于两个主要检测方式
        
        Args:
            driver: WebDriver实例
            
        Returns:
            当前页码
        """
        try:
            self.logger.debug("🔍 开始简化页码检测")
            
            # 方法1: 检测高亮页码元素 <li class="number active">2</li>
            try:
                active_page_element = driver.find_element(By.CSS_SELECTOR, 'li.number.active')
                page_text = active_page_element.text.strip()
                if page_text.isdigit():
                    page_num = int(page_text)
                    self.logger.info(f"✅ 从高亮元素检测到页码: {page_num}")
                    return page_num
            except Exception as e:
                self.logger.debug(f"高亮元素检测失败: {e}")
            
            # 方法2: 检测输入框值 <input id="jump_page" type="number">
            try:
                jump_page_input = driver.find_element(By.CSS_SELECTOR, 'input#jump_page[type="number"]')
                input_value = jump_page_input.get_attribute('value')
                if input_value and input_value.isdigit():
                    page_num = int(input_value)
                    self.logger.info(f"✅ 从输入框检测到页码: {page_num}")
                    return page_num
                else:
                    # 尝试使用JavaScript获取输入框值
                    js_value = driver.execute_script("return document.getElementById('jump_page').value;")
                    if js_value and str(js_value).isdigit():
                        page_num = int(js_value)
                        self.logger.info(f"✅ 从输入框(JS)检测到页码: {page_num}")
                        return page_num
            except Exception as e:
                self.logger.debug(f"输入框检测失败: {e}")
            
            # 备用方法: URL参数检测
            try:
                from urllib.parse import urlparse, parse_qs
                parsed_url = urlparse(driver.current_url)
                query_params = parse_qs(parsed_url.query)
                
                for param in ['page', 'p', 'pageNum']:
                    if param in query_params:
                        page_num = int(query_params[param][0])
                        if page_num > 0:
                            self.logger.info(f"✅ 从URL参数检测到页码: {page_num}")
                            return page_num
            except Exception as e:
                self.logger.debug(f"URL参数检测失败: {e}")
            
            self.logger.warning("⚠️ 所有检测方法失败，返回默认页码1")
            return 1
            
        except Exception as e:
            self.logger.error(f"❌ 页码检测异常: {e}")
            return 1
    
    def _reapply_salary_filter(self, driver: webdriver.Chrome) -> None:
        """
        重新应用薪资过滤器（3-4万）
        
        Args:
            driver: WebDriver实例
        """
        try:
            self.logger.info("🔧 重新应用薪资过滤器（3-4万）")
            
            # 等待页面稳定
            time.sleep(2)
            
            # 使用JavaScript查找包含"3-4万"文本的元素
            salary_element = None
            
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
                    self.logger.info("✅ 找到薪资过滤器元素，准备点击")
                    
                    # 滚动到元素位置
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", salary_element)
                    time.sleep(1)
                    
                    # 尝试点击
                    try:
                        salary_element.click()
                        self.logger.info("✅ 薪资过滤器重新应用成功")
                        time.sleep(3)  # 等待过滤器生效
                    except:
                        # 尝试JavaScript点击
                        driver.execute_script("arguments[0].click();", salary_element)
                        self.logger.info("✅ 薪资过滤器重新应用成功（JavaScript点击）")
                        time.sleep(3)
                else:
                    self.logger.warning("⚠️ 未找到薪资过滤器元素")
                    
            except Exception as e:
                self.logger.warning(f"⚠️ 重新应用薪资过滤器失败: {e}")
                
        except Exception as e:
            self.logger.error(f"❌ 重新应用薪资过滤器时出错: {e}")