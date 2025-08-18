"""
登录检测器

负责检测用户是否已成功登录前程无忧
"""

import time
import logging
from typing import List
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from core.exceptions import LoginError, LoginTimeoutError


class LoginDetector:
    """登录状态检测器"""
    
    def __init__(self, driver, config: dict):
        """
        初始化登录检测器
        
        Args:
            driver: Selenium WebDriver实例
            config: 配置字典
        """
        self.driver = driver
        self.login_config = config['login']
        self.logger = logging.getLogger(__name__)
    
    def wait_for_login(self) -> bool:
        """
        等待用户完成登录
        
        Returns:
            登录是否成功
            
        Raises:
            LoginTimeoutError: 登录等待超时
            LoginError: 登录过程中出现错误
        """
        self.logger.info("等待用户登录...")
        self._show_login_instructions()
        
        timeout = self.login_config['wait_timeout']
        check_interval = self.login_config['check_interval']
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # 检查是否已登录
                if self.is_logged_in():
                    self.logger.info("✅ 登录成功检测到!")
                    return True
                
                # 检查是否有登录错误
                if self.has_login_error():
                    self.logger.warning("⚠️ 检测到登录错误，请检查用户名密码")
                
                # 等待一段时间后再次检查
                time.sleep(check_interval)
                
            except Exception as e:
                self.logger.warning(f"登录检测过程中出现异常: {e}")
                time.sleep(check_interval)
        
        # 超时处理
        elapsed_time = time.time() - start_time
        raise LoginTimeoutError(f"登录等待超时 ({elapsed_time:.1f}秒)")
    
    def is_logged_in(self) -> bool:
        """
        检测是否已登录
        
        Returns:
            是否已登录
        """
        success_indicators = self.login_config['success_indicators']
        
        for selector in success_indicators:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element and element.is_displayed():
                    self.logger.debug(f"找到登录成功指示器: {selector}")
                    return True
            except (NoSuchElementException, Exception):
                continue
        
        return False
    
    def has_login_error(self) -> bool:
        """
        检测是否有登录错误
        
        Returns:
            是否有登录错误
        """
        failure_indicators = self.login_config['failure_indicators']
        
        for selector in failure_indicators:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element and element.is_displayed():
                    error_text = element.text
                    self.logger.warning(f"登录错误: {error_text}")
                    return True
            except (NoSuchElementException, Exception):
                continue
        
        return False
    
    def get_login_status_info(self) -> dict:
        """
        获取详细的登录状态信息
        
        Returns:
            登录状态信息字典
        """
        status_info = {
            'is_logged_in': False,
            'has_error': False,
            'found_indicators': [],
            'error_messages': [],
            'current_url': self.driver.current_url,
            'page_title': self.driver.title
        }
        
        # 检查登录成功指示器
        success_indicators = self.login_config['success_indicators']
        for selector in success_indicators:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element and element.is_displayed():
                    status_info['found_indicators'].append(selector)
                    status_info['is_logged_in'] = True
            except:
                continue
        
        # 检查错误指示器
        failure_indicators = self.login_config['failure_indicators']
        for selector in failure_indicators:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element and element.is_displayed():
                    status_info['has_error'] = True
                    status_info['error_messages'].append(element.text)
            except:
                continue
        
        return status_info
    
    def wait_for_specific_element(self, selector: str, timeout: int = 10) -> bool:
        """
        等待特定元素出现
        
        Args:
            selector: CSS选择器
            timeout: 超时时间（秒）
            
        Returns:
            元素是否出现
        """
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return True
        except TimeoutException:
            return False
    
    def check_login_page_loaded(self) -> bool:
        """
        检查登录页面是否已加载
        
        Returns:
            登录页面是否已加载
        """
        login_page_indicators = [
            "input[type='password']",
            ".login-form",
            "#loginForm",
            ".password-input"
        ]
        
        for selector in login_page_indicators:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element and element.is_displayed():
                    return True
            except:
                continue
        
        return False
    
    def _show_login_instructions(self):
        """显示登录指导信息"""
        print("\n" + "="*60)
        print("🔐 请在浏览器中完成登录操作")
        print("="*60)
        print("📋 登录步骤:")
        print("   1. 在打开的浏览器窗口中输入用户名和密码")
        print("   2. 完成验证码验证（如果需要）")
        print("   3. 点击登录按钮")
        print("   4. 等待页面跳转，程序将自动检测登录状态")
        print()
        print("⏰ 最大等待时间: {} 秒".format(self.login_config['wait_timeout']))
        print("🔄 检测间隔: {} 秒".format(self.login_config['check_interval']))
        print("="*60 + "\n")
    
    def force_check_login(self) -> dict:
        """
        强制检查当前登录状态（用于调试）
        
        Returns:
            详细的状态信息
        """
        self.logger.info("强制检查登录状态...")
        status_info = self.get_login_status_info()
        
        self.logger.info(f"当前URL: {status_info['current_url']}")
        self.logger.info(f"页面标题: {status_info['page_title']}")
        self.logger.info(f"是否已登录: {status_info['is_logged_in']}")
        self.logger.info(f"是否有错误: {status_info['has_error']}")
        
        if status_info['found_indicators']:
            self.logger.info(f"找到的登录指示器: {status_info['found_indicators']}")
        
        if status_info['error_messages']:
            self.logger.warning(f"错误信息: {status_info['error_messages']}")
        
        return status_info