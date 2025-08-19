"""
独立登录管理器

负责管理用户登录流程，与内容提取功能完全分离
"""

import time
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from .browser_manager import BrowserManager
from .session_manager import SessionManager
from ..core.exceptions import LoginError, LoginTimeoutError


class LoginManager:
    """独立登录管理器"""
    
    def __init__(self, config: dict, browser_manager: Optional[BrowserManager] = None):
        """
        初始化登录管理器
        
        Args:
            config: 配置字典
            browser_manager: 浏览器管理器实例，如果为None则自动创建
        """
        self.config = config
        self.login_config = config.get('login', {})
        self.mode_config = config.get('mode', {})
        
        # 组件初始化
        self.browser_manager = browser_manager or BrowserManager(config)
        self.session_manager = SessionManager(config)
        self.login_detector = None  # 延迟初始化
        
        self.logger = logging.getLogger(__name__)
        
        # 状态管理
        self.is_logged_in = False
        self.login_start_time = None
        self.current_session_file = None
    
    def start_login_session(self, save_session: bool = True, session_file: Optional[str] = None) -> bool:
        """
        启动登录会话
        
        Args:
            save_session: 是否保存会话
            session_file: 会话文件路径
            
        Returns:
            是否登录成功
            
        Raises:
            LoginError: 登录过程中出现错误
            LoginTimeoutError: 登录超时
        """
        try:
            self.logger.info("🚀 启动独立登录会话")
            self.login_start_time = time.time()
            
            # 1. 检查是否可以使用保存的会话
            if self.mode_config.get('use_saved_session', True):
                if self._try_load_existing_session(session_file):
                    self.logger.info("✅ 使用保存的会话登录成功")
                    self.is_logged_in = True
                    return True
            
            # 2. 启动浏览器
            driver = self.browser_manager.create_driver()
            
            # 3. 初始化登录检测器
            self.login_detector = LoginDetector(driver, self.config)
            
            # 4. 导航到登录页面
            self._navigate_to_login_page()
            
            # 5. 等待用户完成登录
            login_success = self.login_detector.wait_for_login()
            
            if login_success:
                self.is_logged_in = True
                self.logger.info("✅ 登录成功")
                
                # 6. 保存会话（如果需要）
                if save_session:
                    self._save_current_session(session_file)
                
                return True
            else:
                self.logger.error("❌ 登录失败")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 登录会话启动失败: {e}")
            raise LoginError(f"登录会话启动失败: {e}")
    
    def _try_load_existing_session(self, session_file: Optional[str] = None) -> bool:
        """
        尝试加载现有会话
        
        Args:
            session_file: 会话文件路径
            
        Returns:
            是否加载成功
        """
        try:
            # 获取会话信息
            session_info = self.session_manager.get_session_info(session_file)
            if not session_info or session_info.get('is_expired', True):
                self.logger.info("没有有效的保存会话")
                return False
            
            self.logger.info(f"🔄 尝试加载保存的会话: {session_info['filepath']}")
            
            # 启动浏览器
            driver = self.browser_manager.create_driver()
            
            # 加载会话
            if self.session_manager.load_session(driver, session_file):
                # 验证会话是否有效
                if self.session_manager.is_session_valid(driver):
                    self.current_session_file = session_info['filepath']
                    return True
                else:
                    self.logger.warning("保存的会话无效，需要重新登录")
                    return False
            else:
                return False
                
        except Exception as e:
            self.logger.warning(f"加载保存会话失败: {e}")
            return False
    
    def _navigate_to_login_page(self) -> None:
        """导航到登录页面"""
        login_url = self.login_config.get('login_url')
        if not login_url:
            raise LoginError("配置中未找到登录URL")
        
        self.logger.info(f"🌐 导航到登录页面: {login_url}")
        
        driver = self.browser_manager.get_driver()
        if not driver:
            raise LoginError("WebDriver未初始化")
        
        try:
            driver.get(login_url)
            
            # 等待页面加载
            wait = self.browser_manager.create_wait(15)
            wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
            
            self.logger.info("✅ 登录页面加载完成")
            
        except Exception as e:
            self.logger.error(f"❌ 导航到登录页面失败: {e}")
            raise LoginError(f"导航到登录页面失败: {e}")
    
    def _save_current_session(self, session_file: Optional[str] = None) -> None:
        """
        保存当前会话
        
        Args:
            session_file: 会话文件路径
        """
        try:
            driver = self.browser_manager.get_driver()
            if not driver:
                self.logger.warning("WebDriver不存在，无法保存会话")
                return
            
            if self.session_manager.save_session(driver, session_file):
                self.current_session_file = session_file or self.session_manager.default_session_file
                self.logger.info(f"💾 会话已保存到: {self.current_session_file}")
            
        except Exception as e:
            self.logger.warning(f"保存会话失败: {e}")
    
    def check_login_status(self) -> Dict[str, Any]:
        """
        检查当前登录状态
        
        Returns:
            登录状态信息
        """
        status_info = {
            'is_logged_in': self.is_logged_in,
            'login_start_time': self.login_start_time,
            'current_session_file': self.current_session_file,
            'browser_alive': self.browser_manager.is_driver_alive()
        }
        
        # 如果有登录检测器，获取详细状态
        if self.login_detector:
            try:
                detailed_status = self.login_detector.get_login_status_info()
                status_info.update(detailed_status)
            except Exception as e:
                self.logger.warning(f"获取详细登录状态失败: {e}")
        
        return status_info
    
    def force_check_login(self) -> bool:
        """
        强制检查当前是否已登录
        
        Returns:
            是否已登录
        """
        try:
            driver = self.browser_manager.get_driver()
            if not driver:
                return False
            
            # 使用会话管理器检查
            is_valid = self.session_manager.is_session_valid(driver)
            self.is_logged_in = is_valid
            
            return is_valid
            
        except Exception as e:
            self.logger.warning(f"强制检查登录状态失败: {e}")
            return False
    
    def logout(self) -> bool:
        """
        登出（清除会话）
        
        Returns:
            是否登出成功
        """
        try:
            self.logger.info("🚪 执行登出操作")
            
            # 删除保存的会话文件
            if self.current_session_file:
                self.session_manager.delete_session(self.current_session_file)
            
            # 清除浏览器数据
            driver = self.browser_manager.get_driver()
            if driver:
                driver.delete_all_cookies()
                driver.execute_script("localStorage.clear();")
                driver.execute_script("sessionStorage.clear();")
            
            # 重置状态
            self.is_logged_in = False
            self.current_session_file = None
            self.login_start_time = None
            
            self.logger.info("✅ 登出成功")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 登出失败: {e}")
            return False
    
    def get_browser_manager(self) -> BrowserManager:
        """
        获取浏览器管理器实例
        
        Returns:
            浏览器管理器
        """
        return self.browser_manager
    
    def get_session_manager(self) -> SessionManager:
        """
        获取会话管理器实例
        
        Returns:
            会话管理器
        """
        return self.session_manager
    
    def close(self) -> None:
        """关闭登录管理器，清理资源"""
        try:
            self.logger.info("🧹 关闭登录管理器")
            
            # 如果配置了自动保存会话且当前已登录，则保存会话
            if (self.mode_config.get('auto_save_session', True) and 
                self.is_logged_in and 
                not self.current_session_file):
                self._save_current_session()
            
            # 关闭浏览器
            self.browser_manager.quit_driver()
            
            self.logger.info("✅ 登录管理器已关闭")
            
        except Exception as e:
            self.logger.error(f"❌ 关闭登录管理器时出错: {e}")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


# 为了兼容性，创建一个简化的LoginDetector类
class LoginDetector:
    """登录检测器（从原有代码移植）"""
    
    def __init__(self, driver, config: dict):
        self.driver = driver
        self.login_config = config['login']
        self.logger = logging.getLogger(__name__)
    
    def wait_for_login(self) -> bool:
        """等待用户完成登录"""
        self.logger.info("等待用户登录...")
        self._show_login_instructions()
        
        timeout = self.login_config['wait_timeout']
        check_interval = self.login_config['check_interval']
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if self.is_logged_in():
                    self.logger.info("✅ 登录成功检测到!")
                    return True
                
                if self.has_login_error():
                    self.logger.warning("⚠️ 检测到登录错误，请检查用户名密码")
                
                time.sleep(check_interval)
                
            except Exception as e:
                self.logger.warning(f"登录检测过程中出现异常: {e}")
                time.sleep(check_interval)
        
        elapsed_time = time.time() - start_time
        raise LoginTimeoutError(f"登录等待超时 ({elapsed_time:.1f}秒)")
    
    def is_logged_in(self) -> bool:
        """检测是否已登录"""
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import NoSuchElementException
        
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
        """检测是否有登录错误"""
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import NoSuchElementException
        
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
        """获取详细的登录状态信息"""
        from selenium.webdriver.common.by import By
        
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