"""
会话恢复器
负责检测会话失效并自动重新连接
"""

import time
import logging
from typing import Optional, Callable, Dict, Any
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import WebDriverException

from .browser_manager import BrowserManager
from .login_manager import LoginManager
from ..core.exceptions import SessionRecoveryError


class SessionRecovery:
    """会话恢复器"""
    
    def __init__(self, browser_manager: BrowserManager, login_manager: LoginManager, config: Dict[str, Any]):
        """
        初始化会话恢复器
        
        Args:
            browser_manager: 浏览器管理器
            login_manager: 登录管理器
            config: 配置字典
        """
        self.browser_manager = browser_manager
        self.login_manager = login_manager
        self.config = config
        self.recovery_config = config.get('session_recovery', {})
        self.logger = logging.getLogger(__name__)
        
        # 恢复配置
        self.max_retry_attempts = self.recovery_config.get('max_retry_attempts', 3)
        self.retry_delay = self.recovery_config.get('retry_delay', 30)  # 秒
        self.session_check_timeout = self.recovery_config.get('session_check_timeout', 10)
        
        # 统计信息
        self.recovery_stats = {
            'total_recoveries': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0,
            'last_recovery_time': None
        }
    
    def is_session_valid(self, driver: Optional[WebDriver] = None) -> bool:
        """
        检查会话是否有效
        
        Args:
            driver: WebDriver实例，如果为None则使用browser_manager中的driver
            
        Returns:
            会话是否有效
        """
        if driver is None:
            driver = self.browser_manager.get_driver()
        
        if not driver:
            self.logger.debug("WebDriver不存在，会话无效")
            return False
        
        try:
            # 检查driver是否还活跃
            if not self.browser_manager.is_driver_alive():
                self.logger.debug("WebDriver连接已断开")
                return False
            
            # 执行简单的JavaScript检查
            result = driver.execute_script("return document.readyState;")
            if result != "complete":
                self.logger.debug(f"页面状态异常: {result}")
                return False
            
            # 检查当前URL
            current_url = driver.current_url
            if not current_url or "about:blank" in current_url:
                self.logger.debug(f"URL异常: {current_url}")
                return False
            
            # 检查是否仍然登录
            if hasattr(self.login_manager, 'force_check_login'):
                is_logged_in = self.login_manager.force_check_login()
                if not is_logged_in:
                    self.logger.debug("登录状态已失效")
                    return False
            
            return True
            
        except WebDriverException as e:
            self.logger.debug(f"WebDriver异常，会话无效: {e}")
            return False
        except Exception as e:
            self.logger.warning(f"会话检查异常: {e}")
            return False
    
    def recover_session(self, test_keyword: str = "test") -> bool:
        """
        恢复会话
        
        Args:
            test_keyword: 用于会话验证的测试关键词
            
        Returns:
            是否恢复成功
        """
        self.logger.info("🔄 开始会话恢复...")
        self.recovery_stats['total_recoveries'] += 1
        self.recovery_stats['last_recovery_time'] = time.time()
        
        for attempt in range(1, self.max_retry_attempts + 1):
            try:
                self.logger.info(f"🔄 会话恢复尝试 {attempt}/{self.max_retry_attempts}")
                
                # 1. 关闭现有的WebDriver
                self._cleanup_existing_session()
                
                # 2. 等待一段时间
                if attempt > 1:
                    self.logger.info(f"⏳ 等待 {self.retry_delay} 秒后重试...")
                    time.sleep(self.retry_delay)
                
                # 3. 重新创建WebDriver
                driver = self.browser_manager.create_driver()
                if not driver:
                    self.logger.error(f"❌ 尝试 {attempt}: WebDriver创建失败")
                    continue
                
                # 4. 尝试重新登录
                login_success = self.login_manager.start_login_session(
                    save_session=True,
                    test_keyword=test_keyword
                )
                
                if login_success:
                    # 5. 验证会话是否有效
                    if self.is_session_valid(driver):
                        self.logger.info(f"✅ 会话恢复成功 (尝试 {attempt}/{self.max_retry_attempts})")
                        self.recovery_stats['successful_recoveries'] += 1
                        return True
                    else:
                        self.logger.warning(f"⚠️ 尝试 {attempt}: 登录成功但会话验证失败")
                else:
                    self.logger.warning(f"⚠️ 尝试 {attempt}: 重新登录失败")
                
            except Exception as e:
                self.logger.error(f"❌ 尝试 {attempt} 异常: {e}")
                continue
        
        # 所有尝试都失败了
        self.logger.error(f"❌ 会话恢复失败，已尝试 {self.max_retry_attempts} 次")
        self.recovery_stats['failed_recoveries'] += 1
        return False
    
    def _cleanup_existing_session(self):
        """清理现有会话"""
        try:
            self.logger.debug("🧹 清理现有会话...")
            
            # 关闭WebDriver
            self.browser_manager.quit_driver()
            
            # 重置登录状态
            if hasattr(self.login_manager, 'is_logged_in'):
                self.login_manager.is_logged_in = False
            
            # 短暂等待确保资源释放
            time.sleep(2)
            
        except Exception as e:
            self.logger.warning(f"清理现有会话时出错: {e}")
    
    def handle_session_timeout(self, operation_name: str = "操作", test_keyword: str = "test") -> bool:
        """
        处理会话超时
        
        Args:
            operation_name: 操作名称，用于日志记录
            test_keyword: 用于会话验证的测试关键词
            
        Returns:
            是否成功恢复会话
        """
        self.logger.warning(f"⚠️ 检测到会话超时 - {operation_name}")
        
        # 尝试恢复会话
        recovery_success = self.recover_session(test_keyword)
        
        if recovery_success:
            self.logger.info(f"✅ 会话恢复成功，可以继续 {operation_name}")
            return True
        else:
            self.logger.error(f"❌ 会话恢复失败，无法继续 {operation_name}")
            return False
    
    def with_session_recovery(self, operation: Callable, operation_name: str = "操作", 
                            test_keyword: str = "test", max_retries: int = 2) -> Any:
        """
        带会话恢复的操作执行器
        
        Args:
            operation: 要执行的操作函数
            operation_name: 操作名称
            test_keyword: 用于会话验证的测试关键词
            max_retries: 最大重试次数
            
        Returns:
            操作结果
            
        Raises:
            SessionRecoveryError: 会话恢复失败
        """
        for attempt in range(max_retries + 1):
            try:
                # 检查会话是否有效
                if not self.is_session_valid():
                    if attempt == 0:
                        self.logger.warning(f"⚠️ 会话无效，尝试恢复后执行 {operation_name}")
                        if not self.recover_session(test_keyword):
                            raise SessionRecoveryError(f"会话恢复失败，无法执行 {operation_name}")
                    else:
                        self.logger.error(f"❌ 重试后会话仍然无效，放弃执行 {operation_name}")
                        raise SessionRecoveryError(f"多次尝试后会话恢复失败")
                
                # 执行操作
                result = operation()
                return result
                
            except WebDriverException as e:
                if "invalid session id" in str(e).lower() or "session deleted" in str(e).lower():
                    self.logger.warning(f"⚠️ 检测到会话失效异常: {e}")
                    if attempt < max_retries:
                        if self.recover_session(test_keyword):
                            self.logger.info(f"🔄 会话恢复成功，重试 {operation_name} (尝试 {attempt + 2}/{max_retries + 1})")
                            continue
                        else:
                            raise SessionRecoveryError(f"会话恢复失败: {e}")
                    else:
                        raise SessionRecoveryError(f"达到最大重试次数，会话恢复失败: {e}")
                else:
                    # 其他WebDriver异常，直接抛出
                    raise
            except Exception as e:
                # 非会话相关异常，直接抛出
                raise
        
        raise SessionRecoveryError(f"未知错误，操作 {operation_name} 执行失败")
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """
        获取恢复统计信息
        
        Returns:
            恢复统计信息
        """
        stats = self.recovery_stats.copy()
        
        # 计算成功率
        if stats['total_recoveries'] > 0:
            stats['success_rate'] = stats['successful_recoveries'] / stats['total_recoveries']
        else:
            stats['success_rate'] = 0.0
        
        # 格式化最后恢复时间
        if stats['last_recovery_time']:
            stats['last_recovery_time_formatted'] = time.strftime(
                '%Y-%m-%d %H:%M:%S', 
                time.localtime(stats['last_recovery_time'])
            )
        
        return stats
    
    def reset_stats(self):
        """重置统计信息"""
        self.recovery_stats = {
            'total_recoveries': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0,
            'last_recovery_time': None
        }
        self.logger.info("会话恢复统计信息已重置")