"""
登录模式控制器

统一管理登录模式的开关、会话验证和登录流程控制
"""

import time
import logging
import json
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

from .browser_manager import BrowserManager
from .session_manager import SessionManager
from .login_manager import LoginManager
from ..core.exceptions import LoginError, LoginTimeoutError


class LoginModeController:
    """
    登录模式控制器
    
    职责：
    1. 登录模式开关控制
    2. 登录工作流程管理
    3. 会话状态验证和恢复
    4. 详情页访问前的登录验证
    """
    
    def __init__(self, config: dict, browser_manager: Optional[BrowserManager] = None):
        """
        初始化登录模式控制器
        
        Args:
            config: 配置字典
            browser_manager: 浏览器管理器实例，如果为None则自动创建
        """
        self.config = config
        self.login_config = config.get('login_mode', {})
        self.login_settings = config.get('login', {})
        self.mode_config = config.get('mode', {})
        
        # 组件初始化
        self.browser_manager = browser_manager or BrowserManager(config)
        self.session_manager = SessionManager(config)
        self.login_manager = None  # 延迟初始化
        
        self.logger = logging.getLogger(__name__)
        
        # 状态管理
        self.is_login_workflow_active = False
        self.last_session_validation = None
        self.login_attempts = 0
        self.current_session_file = None
        
        # 页面状态管理
        self.saved_page_states = {}  # 保存的页面状态
        self.current_page_state = None  # 当前页面状态
    
    def is_login_mode_enabled(self) -> bool:
        """
        检查是否启用登录模式 - 核心开关方法
        
        Returns:
            是否启用登录模式
        """
        enabled = self.login_config.get('enabled', False)
        self.logger.debug(f"登录模式状态: {'启用' if enabled else '禁用'}")
        return enabled
    
    def start_login_workflow(self, test_keyword: str = "test") -> bool:
        """
        启动登录工作流程 - 核心入口方法
        
        Args:
            test_keyword: 用于会话验证的测试关键词
        
        Returns:
            是否登录成功
            
        Raises:
            LoginError: 登录过程中出现错误
        """
        try:
            if not self.is_login_mode_enabled():
                self.logger.info("🔓 登录模式未启用，跳过登录流程")
                return True
            
            self.logger.info("🔐 启动登录工作流程")
            self.is_login_workflow_active = True
            self.login_attempts = 0
            
            # 1. 尝试恢复保存的会话
            if self._try_restore_saved_session(test_keyword):
                self.logger.info("✅ 使用保存的会话登录成功")
                return True
            
            # 2. 执行人工登录流程
            max_attempts = self.login_config.get('max_login_attempts', 3)
            retry_delay = self.login_config.get('login_retry_delay', 10)
            
            while self.login_attempts < max_attempts:
                self.login_attempts += 1
                self.logger.info(f"🔑 开始第 {self.login_attempts}/{max_attempts} 次登录尝试")
                
                try:
                    if self._execute_manual_login(test_keyword):
                        self.logger.info("✅ 人工登录成功")
                        
                        # 3. 保存新的会话
                        if self.login_config.get('auto_save_session', True):
                            self._save_current_session()
                        
                        return True
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ 第 {self.login_attempts} 次登录尝试失败: {e}")
                
                # 如果不是最后一次尝试，等待后重试
                if self.login_attempts < max_attempts:
                    self.logger.info(f"⏳ 等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
            
            # 所有尝试都失败
            self.logger.error(f"❌ 登录失败，已尝试 {max_attempts} 次")
            raise LoginError(f"登录失败，已尝试 {max_attempts} 次")
            
        except Exception as e:
            self.logger.error(f"❌ 登录工作流程失败: {e}")
            raise LoginError(f"登录工作流程失败: {e}")
        finally:
            self.is_login_workflow_active = False
    
    def validate_login_before_details(self, test_keyword: str = "test") -> bool:
        """
        详情页访问前的登录验证 - 关键保护方法
        
        Args:
            test_keyword: 用于会话验证的测试关键词
        
        Returns:
            登录状态是否有效
        """
        try:
            if not self.is_login_mode_enabled():
                return True
            
            if not self.login_config.get('require_login_for_details', True):
                self.logger.debug("配置为详情页不需要登录验证")
                return True
            
            # 检查会话验证间隔
            validation_interval = self.login_config.get('session_validation_interval', 300)
            current_time = time.time()
            
            if (self.last_session_validation and
                current_time - self.last_session_validation < validation_interval):
                self.logger.debug("会话验证间隔未到，跳过验证")
                return True
            
            # 执行会话验证
            self.logger.debug("🔍 验证详情页访问前的登录状态")
            
            driver = self.browser_manager.get_driver()
            if not driver:
                self.logger.warning("⚠️ WebDriver不存在，无法验证登录状态")
                return False
            
            # 保存当前页面状态
            page_state = self.save_current_page_state(driver)
            
            # 使用会话管理器检查登录状态（保持当前页面状态）
            is_valid = self.session_manager.is_session_valid(driver, test_keyword, preserve_current_page=True)
            self.last_session_validation = current_time
            
            if not is_valid:
                self.logger.warning("⚠️ 登录状态无效，尝试恢复会话")
                
                # 尝试恢复会话
                if self._try_restore_saved_session(test_keyword):
                    self.logger.info("✅ 会话恢复成功")
                    # 恢复页面状态
                    if page_state:
                        self.restore_page_state(driver, page_state)
                    return True
                else:
                    self.logger.error("❌ 会话恢复失败，需要重新登录")
                    # 尝试恢复页面状态
                    if page_state:
                        self.restore_page_state(driver, page_state)
                    return False
            
            self.logger.debug("✅ 登录状态验证通过")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 登录状态验证失败: {e}")
            return False
    
    def _try_restore_saved_session(self, test_keyword: str = "test") -> bool:
        """
        尝试恢复保存的会话
        
        Args:
            test_keyword: 用于会话验证的测试关键词
        
        Returns:
            是否恢复成功
        """
        try:
            session_file = self.mode_config.get('session_file')
            if not session_file:
                self.logger.debug("未配置会话文件路径")
                return False
            
            # 检查会话文件是否存在
            if not Path(session_file).exists():
                self.logger.debug(f"会话文件不存在: {session_file}")
                return False
            
            # 获取会话信息
            session_info = self.session_manager.get_session_info(session_file)
            if not session_info or session_info.get('is_expired', True):
                self.logger.info("保存的会话已过期")
                return False
            
            self.logger.info(f"🔄 尝试恢复保存的会话: {session_file}")
            
            # 确保浏览器已启动 - 添加网络异常处理
            driver = self.browser_manager.get_driver()
            if not driver:
                try:
                    driver = self.browser_manager.create_driver()
                except Exception as browser_e:
                    self.logger.error(f"⚠️ 浏览器创建失败: {browser_e}")
                    return False
            
            # 加载会话 - 添加网络异常处理
            try:
                if self.session_manager.load_session(driver, session_file):
                    # 验证会话是否有效（减少页面跳转，使用保守验证策略）
                    try:
                        if self.session_manager.is_session_valid(driver, test_keyword, preserve_current_page=True):
                            self.current_session_file = session_file
                            self.logger.info("✅ 会话恢复成功")
                            return True
                        else:
                            self.logger.warning("⚠️ 恢复的会话无效")
                            return False
                    except Exception as validation_e:
                        self.logger.warning(f"⚠️ 会话验证过程中发生异常: {validation_e}")
                        return False
                else:
                    self.logger.warning("⚠️ 会话加载失败")
                    return False
            except Exception as load_e:
                self.logger.warning(f"⚠️ 会话加载过程中发生异常: {load_e}")
                return False
                
        except Exception as e:
            self.logger.warning(f"恢复会话失败: {e}")
            return False
    
    def _execute_manual_login(self, test_keyword: str = "test") -> bool:
        """
        执行人工登录流程
        
        Args:
            test_keyword: 用于会话验证的测试关键词
        
        Returns:
            是否登录成功
        """
        try:
            # 初始化登录管理器
            if not self.login_manager:
                self.login_manager = LoginManager(self.config, self.browser_manager)
            
            # 启动登录会话
            session_file = self.mode_config.get('session_file')
            return self.login_manager.start_login_session(
                save_session=self.login_config.get('auto_save_session', True),
                session_file=session_file,
                test_keyword=test_keyword
            )
            
        except Exception as e:
            self.logger.error(f"人工登录执行失败: {e}")
            return False
    
    def _save_current_session(self) -> None:
        """保存当前会话"""
        try:
            session_file = self.mode_config.get('session_file')
            if not session_file:
                self.logger.warning("未配置会话文件路径，无法保存会话")
                return
            
            driver = self.browser_manager.get_driver()
            if not driver:
                self.logger.warning("WebDriver不存在，无法保存会话")
                return
            
            if self.session_manager.save_session(driver, session_file):
                self.current_session_file = session_file
                self.logger.info(f"💾 会话已保存到: {session_file}")
            else:
                self.logger.warning("⚠️ 会话保存失败")
                
        except Exception as e:
            self.logger.warning(f"保存会话失败: {e}")
    
    def get_login_status_summary(self) -> Dict[str, Any]:
        """
        获取登录状态摘要
        
        Returns:
            登录状态摘要字典
        """
        try:
            # 基本状态信息
            status = {
                'login_mode_enabled': self.is_login_mode_enabled(),
                'workflow_active': self.is_login_workflow_active,
                'login_attempts': self.login_attempts,
                'current_session_file': self.current_session_file,
                'last_validation': self.last_session_validation,
                'browser_alive': self.browser_manager.is_driver_alive()
            }
            
            # 如果有登录管理器，获取详细状态
            if self.login_manager:
                login_status = self.login_manager.check_login_status()
                status.update({
                    'login_status': login_status,
                    'is_logged_in': login_status.get('is_logged_in', False)
                })
            else:
                status.update({
                    'login_status': None,
                    'is_logged_in': False
                })
            
            # 配置信息
            status['config'] = {
                'website': self.login_config.get('website', 'unknown'),
                'require_login_for_details': self.login_config.get('require_login_for_details', True),
                'auto_save_session': self.login_config.get('auto_save_session', True),
                'max_login_attempts': self.login_config.get('max_login_attempts', 3)
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"获取登录状态摘要失败: {e}")
            return {
                'login_mode_enabled': False,
                'error': str(e)
            }
    
    def force_logout(self) -> bool:
        """
        强制登出
        
        Returns:
            是否登出成功
        """
        try:
            self.logger.info("🚪 执行强制登出")
            
            # 使用登录管理器登出
            if self.login_manager:
                success = self.login_manager.logout()
            else:
                success = True
            
            # 清理本地状态
            self.current_session_file = None
            self.last_session_validation = None
            self.login_attempts = 0
            self.is_login_workflow_active = False
            
            if success:
                self.logger.info("✅ 强制登出成功")
            else:
                self.logger.warning("⚠️ 强制登出部分失败")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ 强制登出失败: {e}")
            return False
    
    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """
        获取当前会话信息
        
        Returns:
            会话信息字典，如果没有会话则返回None
        """
        try:
            if not self.current_session_file:
                return None
            
            return self.session_manager.get_session_info(self.current_session_file)
            
        except Exception as e:
            self.logger.error(f"获取会话信息失败: {e}")
            return None
    
    def close(self) -> None:
        """关闭登录模式控制器，清理资源"""
        try:
            self.logger.info("🧹 关闭登录模式控制器")
            
            # 如果配置了自动保存会话且当前有活跃会话，则保存
            if (self.login_config.get('auto_save_session', True) and 
                self.browser_manager.is_driver_alive() and
                not self.current_session_file):
                self._save_current_session()
            
            # 关闭登录管理器
            if self.login_manager:
                self.login_manager.close()
            
            self.logger.info("✅ 登录模式控制器已关闭")
            
        except Exception as e:
            self.logger.error(f"❌ 关闭登录模式控制器时出错: {e}")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
    
    def validate_login_before_page_navigation(self, test_keyword: str = "test") -> bool:
        """
        页面跳转前的登录验证 - 简化版本
        
        Args:
            test_keyword: 用于会话验证的测试关键词
        
        Returns:
            登录状态是否有效，如果无效且无法恢复则返回False
        """
        try:
            if not self.is_login_mode_enabled():
                return True
            
            self.logger.debug("🔍 页面跳转前验证登录状态")
            
            driver = self.browser_manager.get_driver()
            if not driver:
                self.logger.warning("⚠️ WebDriver不存在，无法验证登录状态")
                return False
            
            # 检查登录状态
            is_valid = self.session_manager.is_session_valid(driver, test_keyword, preserve_current_page=True)
            
            if not is_valid:
                self.logger.warning("⚠️ 登录状态无效，尝试恢复会话")
                
                # 尝试恢复会话
                if self._try_restore_saved_session(test_keyword):
                    self.logger.info("✅ 会话恢复成功")
                    return True
                else:
                    self.logger.error("❌ 会话恢复失败")
                    # 尝试等待人工登录
                    return self._wait_for_manual_login(test_keyword)
            
            self.logger.debug("✅ 登录状态验证通过")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 页面跳转前登录状态验证失败: {e}")
            return False
    
    def _wait_for_manual_login(self, test_keyword: str = "test", max_wait_minutes: int = 10) -> bool:
        """
        等待人工登录
        
        Args:
            test_keyword: 用于会话验证的测试关键词
            max_wait_minutes: 最大等待时间（分钟）
        
        Returns:
            是否成功登录
        """
        try:
            self.logger.warning(f"⏳ 等待人工登录，最大等待时间: {max_wait_minutes} 分钟")
            self.logger.warning("💡 请在浏览器中手动登录，程序将自动检测登录状态")
            
            driver = self.browser_manager.get_driver()
            if not driver:
                return False
            
            start_time = time.time()
            max_wait_seconds = max_wait_minutes * 60
            check_interval = 30  # 每30秒检查一次
            
            while time.time() - start_time < max_wait_seconds:
                try:
                    # 检查登录状态
                    if self.session_manager.is_session_valid(driver, test_keyword, preserve_current_page=True):
                        self.logger.info("✅ 检测到手动登录成功")
                        
                        # 保存新的会话
                        if self.login_config.get('auto_save_session', True):
                            self._save_current_session()
                        
                        return True
                    
                    # 等待下次检查
                    remaining_time = max_wait_seconds - (time.time() - start_time)
                    if remaining_time > 0:
                        wait_time = min(check_interval, remaining_time)
                        self.logger.info(f"⏳ 等待中... 剩余时间: {remaining_time/60:.1f} 分钟")
                        time.sleep(wait_time)
                    
                except Exception as e:
                    self.logger.debug(f"检查登录状态时出错: {e}")
                    time.sleep(check_interval)
                    continue
            
            self.logger.error(f"❌ 等待人工登录超时 ({max_wait_minutes} 分钟)")
            return False
            
        except Exception as e:
            self.logger.error(f"❌ 等待人工登录失败: {e}")
            return False