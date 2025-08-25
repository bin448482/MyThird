"""
按钮识别引擎

负责识别和点击各种招聘网站的申请按钮
"""

import logging
import time
import re
from typing import Optional, List, Dict, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains

from .models import ButtonInfo, SubmissionStatus


class ButtonRecognitionEngine:
    """通用按钮识别引擎"""
    
    def __init__(self, driver, config: Dict[str, Any]):
        """
        初始化按钮识别引擎
        
        Args:
            driver: WebDriver实例
            config: 配置字典
        """
        self.driver = driver
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 按钮识别配置
        self.button_config = config.get('button_recognition', {})
        self.timeout = self.button_config.get('timeout', 10)
        self.retry_attempts = self.button_config.get('retry_attempts', 3)
        
        # 预定义的按钮选择器（按网站分类）
        self.button_selectors = self._load_button_selectors()
    
    def _load_button_selectors(self) -> Dict[str, List[str]]:
        """加载按钮选择器配置"""
        default_selectors = {
            'qiancheng': [  # 51job
                "a.but_sq#app_ck",
                "a[onclick*='delivery']",
                "a[track-type='NewTrackButtonClick']",
                "button:contains('申请职位')",
                "a:contains('申请职位')",
                ".apply-btn",
                "#apply-button"
            ],
            'zhilian': [  # 智联招聘
                "button.apply-btn",
                "a.apply-position",
                "button:contains('立即申请')",
                "a:contains('立即申请')",
                ".btn-apply"
            ],
            'boss': [  # Boss直聘
                "button.btn-apply",
                "a.start-chat-btn",
                "button:contains('立即沟通')",
                "a:contains('立即沟通')",
                ".chat-btn"
            ],
            'lagou': [  # 拉勾网
                "a.position-apply-btn",
                "button:contains('申请')",
                ".apply-btn"
            ],
            'generic': [  # 通用选择器
                "button:contains('申请')",
                "button:contains('投递')",
                "button:contains('立即申请')",
                "a:contains('申请职位')",
                "a:contains('投递简历')",
                ".apply-btn",
                ".submit-btn",
                "#apply",
                "#submit"
            ]
        }
        
        # 从配置中加载自定义选择器
        configured_selectors = self.button_config.get('selectors', {})
        default_selectors.update(configured_selectors)
        
        return default_selectors
    
    def detect_website(self, url: str) -> str:
        """
        检测网站类型
        
        Args:
            url: 当前页面URL
            
        Returns:
            网站类型标识
        """
        url_lower = url.lower()
        
        if '51job.com' in url_lower:
            return 'qiancheng'
        elif 'zhaopin.com' in url_lower:
            return 'zhilian'
        elif 'zhipin.com' in url_lower:
            return 'boss'
        elif 'lagou.com' in url_lower:
            return 'lagou'
        else:
            return 'generic'
    
    def find_application_button(self, url: str = None) -> Optional[ButtonInfo]:
        """
        识别申请按钮
        
        Args:
            url: 页面URL，用于确定网站类型
            
        Returns:
            按钮信息或None
        """
        try:
            if url is None:
                url = self.driver.current_url
            
            website_type = self.detect_website(url)
            self.logger.info(f"检测到网站类型: {website_type}")
            
            # 获取对应网站的选择器
            selectors = self.button_selectors.get(website_type, [])
            if website_type != 'generic':
                # 添加通用选择器作为备选
                selectors.extend(self.button_selectors.get('generic', []))
            
            # 尝试每个选择器
            for selector in selectors:
                button_info = self._try_find_button_by_selector(selector)
                if button_info:
                    self.logger.info(f"找到申请按钮: {selector}")
                    return button_info
            
            # 如果没有找到，尝试智能识别
            button_info = self._smart_button_detection()
            if button_info:
                self.logger.info("通过智能识别找到申请按钮")
                return button_info
            
            self.logger.warning("未找到申请按钮")
            return None
            
        except Exception as e:
            self.logger.error(f"识别申请按钮失败: {e}")
            return None
    
    def _try_find_button_by_selector(self, selector: str) -> Optional[ButtonInfo]:
        """
        尝试通过选择器查找按钮
        
        Args:
            selector: CSS选择器
            
        Returns:
            按钮信息或None
        """
        try:
            # 处理包含文本的选择器
            if ':contains(' in selector:
                return self._find_button_by_text(selector)
            
            # 等待元素出现
            wait = WebDriverWait(self.driver, 3)
            element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            
            # 检查元素是否可见和可点击
            if not element.is_displayed():
                return None
            
            # 获取按钮信息
            button_info = self._extract_button_info(element, selector)
            
            # 验证按钮是否真的是申请按钮
            if self._validate_button(button_info):
                return button_info
            
            return None
            
        except (TimeoutException, NoSuchElementException):
            return None
        except Exception as e:
            self.logger.debug(f"选择器 {selector} 查找失败: {e}")
            return None
    
    def _find_button_by_text(self, selector: str) -> Optional[ButtonInfo]:
        """
        通过文本内容查找按钮
        
        Args:
            selector: 包含:contains()的选择器
            
        Returns:
            按钮信息或None
        """
        try:
            # 解析选择器中的文本
            match = re.search(r':contains\([\'"]?([^\'"]+)[\'"]?\)', selector)
            if not match:
                return None
            
            text = match.group(1)
            base_selector = selector.split(':contains(')[0]
            
            # 查找所有匹配的元素
            elements = self.driver.find_elements(By.CSS_SELECTOR, base_selector)
            
            for element in elements:
                if element.is_displayed() and text in element.text:
                    button_info = self._extract_button_info(element, selector)
                    if self._validate_button(button_info):
                        return button_info
            
            return None
            
        except Exception as e:
            self.logger.debug(f"文本查找失败: {e}")
            return None
    
    def _smart_button_detection(self) -> Optional[ButtonInfo]:
        """
        智能按钮检测
        
        Returns:
            按钮信息或None
        """
        try:
            # 申请相关的关键词
            apply_keywords = [
                '申请职位', '投递简历', '立即申请', '申请', '投递',
                '立即沟通', '开始聊聊', '立即投递', '马上申请'
            ]
            
            # 查找所有可能的按钮元素
            button_elements = []
            
            # 查找button元素
            buttons = self.driver.find_elements(By.TAG_NAME, 'button')
            button_elements.extend(buttons)
            
            # 查找a元素
            links = self.driver.find_elements(By.TAG_NAME, 'a')
            button_elements.extend(links)
            
            # 查找input[type=submit]元素
            submits = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="submit"]')
            button_elements.extend(submits)
            
            # 检查每个元素
            for element in button_elements:
                if not element.is_displayed():
                    continue
                
                element_text = element.text.strip()
                
                # 检查文本是否包含申请关键词
                for keyword in apply_keywords:
                    if keyword in element_text:
                        button_info = self._extract_button_info(element, f"text:{keyword}")
                        if self._validate_button(button_info):
                            return button_info
                
                # 检查onclick属性
                onclick = element.get_attribute('onclick')
                if onclick and ('apply' in onclick.lower() or 'delivery' in onclick.lower()):
                    button_info = self._extract_button_info(element, "onclick")
                    if self._validate_button(button_info):
                        return button_info
            
            return None
            
        except Exception as e:
            self.logger.error(f"智能按钮检测失败: {e}")
            return None
    
    def _extract_button_info(self, element, selector: str) -> ButtonInfo:
        """
        提取按钮信息
        
        Args:
            element: WebElement
            selector: 选择器
            
        Returns:
            按钮信息
        """
        try:
            # 获取元素位置
            location = element.location
            size = element.size
            position = {
                'x': location['x'] + size['width'] // 2,
                'y': location['y'] + size['height'] // 2
            }
            
            button_info = ButtonInfo(
                selector=selector,
                element_type=element.tag_name,
                text=element.text.strip(),
                onclick=element.get_attribute('onclick'),
                href=element.get_attribute('href'),
                position=position,
                confidence=self._calculate_confidence(element)
            )
            
            return button_info
            
        except Exception as e:
            self.logger.error(f"提取按钮信息失败: {e}")
            return ButtonInfo(selector=selector, element_type="unknown", text="")
    
    def _validate_button(self, button_info: ButtonInfo) -> bool:
        """
        验证按钮是否为申请按钮
        
        Args:
            button_info: 按钮信息
            
        Returns:
            是否为有效的申请按钮
        """
        if not button_info or not button_info.text:
            return False
        
        text = button_info.text.lower()
        
        # 排除明显不是申请按钮的文本
        exclude_keywords = [
            '取消', '关闭', '返回', '上一步', '下一步',
            '登录', '注册', '搜索', '筛选', '收藏'
        ]
        
        for keyword in exclude_keywords:
            if keyword in text:
                return False
        
        # 检查是否包含申请相关关键词
        apply_keywords = [
            '申请', '投递', '立即', '马上', '沟通', '聊聊'
        ]
        
        for keyword in apply_keywords:
            if keyword in text:
                return True
        
        # 检查onclick属性
        if button_info.onclick:
            onclick_lower = button_info.onclick.lower()
            if 'delivery' in onclick_lower or 'apply' in onclick_lower:
                return True
        
        return False
    
    def _calculate_confidence(self, element) -> float:
        """
        计算识别置信度
        
        Args:
            element: WebElement
            
        Returns:
            置信度 (0-1)
        """
        confidence = 0.5  # 基础置信度
        
        text = element.text.strip().lower()
        
        # 根据文本内容调整置信度
        if '申请职位' in text:
            confidence += 0.4
        elif '立即申请' in text:
            confidence += 0.3
        elif '申请' in text:
            confidence += 0.2
        elif '投递' in text:
            confidence += 0.2
        
        # 根据元素类型调整
        if element.tag_name == 'button':
            confidence += 0.1
        elif element.tag_name == 'a':
            confidence += 0.05
        
        # 根据CSS类名调整
        class_name = element.get_attribute('class') or ''
        if 'apply' in class_name.lower() or 'submit' in class_name.lower():
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def click_button_safely(self, button_info: ButtonInfo) -> bool:
        """
        安全点击按钮
        
        Args:
            button_info: 按钮信息
            
        Returns:
            是否点击成功
        """
        try:
            # 重新定位元素（避免stale element问题）
            element = self._relocate_element(button_info)
            if not element:
                self.logger.error("无法重新定位按钮元素")
                return False
            
            # 滚动到元素可见
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(1)
            
            # 等待元素可点击
            wait = WebDriverWait(self.driver, self.timeout)
            clickable_element = wait.until(EC.element_to_be_clickable(element))
            
            # 尝试多种点击方式
            for attempt in range(self.retry_attempts):
                try:
                    # 方式1: 直接点击
                    clickable_element.click()
                    self.logger.info("按钮点击成功（直接点击）")
                    return True
                    
                except ElementClickInterceptedException:
                    try:
                        # 方式2: JavaScript点击
                        self.driver.execute_script("arguments[0].click();", clickable_element)
                        self.logger.info("按钮点击成功（JavaScript点击）")
                        return True
                        
                    except Exception:
                        try:
                            # 方式3: ActionChains点击
                            actions = ActionChains(self.driver)
                            actions.move_to_element(clickable_element).click().perform()
                            self.logger.info("按钮点击成功（ActionChains点击）")
                            return True
                            
                        except Exception as e:
                            self.logger.warning(f"点击尝试 {attempt + 1} 失败: {e}")
                            time.sleep(1)
                            continue
                
                except Exception as e:
                    self.logger.warning(f"点击尝试 {attempt + 1} 失败: {e}")
                    time.sleep(1)
                    continue
            
            self.logger.error("所有点击尝试都失败了")
            return False
            
        except Exception as e:
            self.logger.error(f"安全点击按钮失败: {e}")
            return False
    
    def _relocate_element(self, button_info: ButtonInfo):
        """
        重新定位元素
        
        Args:
            button_info: 按钮信息
            
        Returns:
            WebElement或None
        """
        try:
            if ':contains(' in button_info.selector:
                return self._find_element_by_text(button_info)
            elif button_info.selector.startswith('text:'):
                return self._find_element_by_text(button_info)
            elif button_info.selector == 'onclick':
                return self._find_element_by_onclick(button_info)
            else:
                return self.driver.find_element(By.CSS_SELECTOR, button_info.selector)
                
        except Exception as e:
            self.logger.error(f"重新定位元素失败: {e}")
            return None
    
    def _find_element_by_text(self, button_info: ButtonInfo):
        """通过文本查找元素"""
        elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{button_info.text}')]")
        for element in elements:
            if element.is_displayed() and element.text.strip() == button_info.text:
                return element
        return None
    
    def _find_element_by_onclick(self, button_info: ButtonInfo):
        """通过onclick属性查找元素"""
        if not button_info.onclick:
            return None
        
        elements = self.driver.find_elements(By.XPATH, f"//*[@onclick='{button_info.onclick}']")
        for element in elements:
            if element.is_displayed():
                return element
        return None
    
    def handle_application_form(self) -> bool:
        """
        处理申请表单（如果有）
        
        Returns:
            是否处理成功
        """
        try:
            # 等待可能出现的表单
            time.sleep(2)
            
            # 查找表单
            forms = self.driver.find_elements(By.TAG_NAME, 'form')
            if not forms:
                self.logger.info("没有发现申请表单")
                return True
            
            self.logger.info("发现申请表单，尝试处理")
            
            # 查找提交按钮
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:contains('提交')",
                "button:contains('确认申请')",
                "button:contains('确认')"
            ]
            
            for selector in submit_selectors:
                try:
                    if ':contains(' in selector:
                        # 处理包含文本的选择器
                        submit_button = self._find_submit_button_by_text(selector)
                    else:
                        submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if submit_button and submit_button.is_displayed():
                        submit_button.click()
                        self.logger.info("申请表单提交成功")
                        return True
                        
                except Exception:
                    continue
            
            self.logger.warning("未找到表单提交按钮")
            return False
            
        except Exception as e:
            self.logger.error(f"处理申请表单失败: {e}")
            return False
    
    def _find_submit_button_by_text(self, selector: str):
        """通过文本查找提交按钮"""
        match = re.search(r':contains\([\'"]?([^\'"]+)[\'"]?\)', selector)
        if not match:
            return None
        
        text = match.group(1)
        base_selector = selector.split(':contains(')[0]
        
        elements = self.driver.find_elements(By.CSS_SELECTOR, base_selector)
        for element in elements:
            if element.is_displayed() and text in element.text:
                return element
        
        return None
    
    def check_application_success(self) -> bool:
        """
        检查申请是否成功
        
        Returns:
            是否申请成功
        """
        try:
            # 等待页面响应
            time.sleep(3)
            
            # 成功指示器
            success_indicators = [
                "申请成功",
                "投递成功",
                "简历已投递",
                "申请已提交",
                "投递完成",
                "success",
                "submitted",
                "applied"
            ]
            
            page_source = self.driver.page_source.lower()
            
            for indicator in success_indicators:
                if indicator.lower() in page_source:
                    self.logger.info(f"检测到成功指示器: {indicator}")
                    return True
            
            # 检查URL变化（可能跳转到成功页面）
            current_url = self.driver.current_url.lower()
            if 'success' in current_url or 'applied' in current_url:
                self.logger.info("URL显示申请成功")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"检查申请成功状态失败: {e}")
            return False