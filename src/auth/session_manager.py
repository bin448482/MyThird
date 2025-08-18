"""
会话管理器

负责浏览器会话的保存、加载和验证
"""

import json
import pickle
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

from core.exceptions import SessionError


class SessionManager:
    """会话管理器"""
    
    def __init__(self, config: dict):
        """
        初始化会话管理器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.login_config = config.get('login', {})
        self.mode_config = config.get('mode', {})
        self.logger = logging.getLogger(__name__)
        
        # 默认会话文件路径
        self.default_session_file = self.mode_config.get(
            'session_file', 
            'data/session.json'
        )
    
    def save_session(self, driver: webdriver.Chrome, filepath: Optional[str] = None) -> bool:
        """
        保存浏览器会话
        
        Args:
            driver: WebDriver实例
            filepath: 保存路径，如果为None则使用默认路径
            
        Returns:
            是否保存成功
        """
        if filepath is None:
            filepath = self.default_session_file
        
        try:
            self.logger.info(f"💾 保存会话到: {filepath}")
            
            # 创建目录
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            # 收集会话数据
            session_data = self._collect_session_data(driver)
            
            # 保存到文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info("✅ 会话保存成功")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 保存会话失败: {e}")
            return False
    
    def load_session(self, driver: webdriver.Chrome, filepath: Optional[str] = None) -> bool:
        """
        加载浏览器会话
        
        Args:
            driver: WebDriver实例
            filepath: 会话文件路径，如果为None则使用默认路径
            
        Returns:
            是否加载成功
        """
        if filepath is None:
            filepath = self.default_session_file
        
        try:
            if not Path(filepath).exists():
                self.logger.warning(f"会话文件不存在: {filepath}")
                return False
            
            self.logger.info(f"📂 加载会话从: {filepath}")
            
            # 读取会话数据
            with open(filepath, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # 检查会话是否过期
            if self._is_session_expired(session_data):
                self.logger.warning("会话已过期")
                return False
            
            # 应用会话数据
            success = self._apply_session_data(driver, session_data)
            
            if success:
                self.logger.info("✅ 会话加载成功")
            else:
                self.logger.warning("⚠️ 会话加载失败")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ 加载会话失败: {e}")
            return False
    
    def _collect_session_data(self, driver: webdriver.Chrome) -> Dict[str, Any]:
        """
        收集会话数据
        
        Args:
            driver: WebDriver实例
            
        Returns:
            会话数据字典
        """
        session_data = {
            'timestamp': datetime.now().isoformat(),
            'current_url': driver.current_url,
            'cookies': [],
            'local_storage': {},
            'session_storage': {},
            'user_agent': driver.execute_script("return navigator.userAgent;"),
            'window_size': driver.get_window_size()
        }
        
        try:
            # 保存Cookies
            session_data['cookies'] = driver.get_cookies()
            self.logger.debug(f"保存了 {len(session_data['cookies'])} 个Cookie")
            
            # 保存LocalStorage
            local_storage = driver.execute_script(
                "var items = {}; "
                "for (var i = 0; i < localStorage.length; i++) { "
                "    var key = localStorage.key(i); "
                "    items[key] = localStorage.getItem(key); "
                "} "
                "return items;"
            )
            session_data['local_storage'] = local_storage
            self.logger.debug(f"保存了 {len(local_storage)} 个LocalStorage项")
            
            # 保存SessionStorage
            session_storage = driver.execute_script(
                "var items = {}; "
                "for (var i = 0; i < sessionStorage.length; i++) { "
                "    var key = sessionStorage.key(i); "
                "    items[key] = sessionStorage.getItem(key); "
                "} "
                "return items;"
            )
            session_data['session_storage'] = session_storage
            self.logger.debug(f"保存了 {len(session_storage)} 个SessionStorage项")
            
        except Exception as e:
            self.logger.warning(f"收集会话数据时出错: {e}")
        
        return session_data
    
    def _apply_session_data(self, driver: webdriver.Chrome, session_data: Dict[str, Any]) -> bool:
        """
        应用会话数据
        
        Args:
            driver: WebDriver实例
            session_data: 会话数据
            
        Returns:
            是否应用成功
        """
        try:
            # 导航到原始URL
            original_url = session_data.get('current_url')
            if original_url:
                # 先访问域名根路径，确保可以设置Cookie
                from urllib.parse import urlparse
                parsed_url = urlparse(original_url)
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                driver.get(base_url)
            
            # 恢复Cookies
            cookies = session_data.get('cookies', [])
            for cookie in cookies:
                try:
                    # 移除可能导致问题的字段
                    cookie_copy = cookie.copy()
                    cookie_copy.pop('sameSite', None)
                    cookie_copy.pop('httpOnly', None)
                    driver.add_cookie(cookie_copy)
                except Exception as e:
                    self.logger.debug(f"添加Cookie失败: {e}")
            
            self.logger.debug(f"恢复了 {len(cookies)} 个Cookie")
            
            # 恢复LocalStorage
            local_storage = session_data.get('local_storage', {})
            for key, value in local_storage.items():
                try:
                    driver.execute_script(
                        f"localStorage.setItem(arguments[0], arguments[1]);",
                        key, value
                    )
                except Exception as e:
                    self.logger.debug(f"恢复LocalStorage失败 {key}: {e}")
            
            # 恢复SessionStorage
            session_storage = session_data.get('session_storage', {})
            for key, value in session_storage.items():
                try:
                    driver.execute_script(
                        f"sessionStorage.setItem(arguments[0], arguments[1]);",
                        key, value
                    )
                except Exception as e:
                    self.logger.debug(f"恢复SessionStorage失败 {key}: {e}")
            
            # 最后导航到原始URL
            if original_url:
                driver.get(original_url)
            
            return True
            
        except Exception as e:
            self.logger.error(f"应用会话数据失败: {e}")
            return False
    
    def _is_session_expired(self, session_data: Dict[str, Any]) -> bool:
        """
        检查会话是否过期
        
        Args:
            session_data: 会话数据
            
        Returns:
            是否过期
        """
        try:
            timestamp_str = session_data.get('timestamp')
            if not timestamp_str:
                return True
            
            session_time = datetime.fromisoformat(timestamp_str)
            timeout_seconds = self.mode_config.get('session_timeout', 3600)  # 默认1小时
            
            expiry_time = session_time + timedelta(seconds=timeout_seconds)
            is_expired = datetime.now() > expiry_time
            
            if is_expired:
                self.logger.info(f"会话已过期: {session_time} -> {expiry_time}")
            
            return is_expired
            
        except Exception as e:
            self.logger.warning(f"检查会话过期时出错: {e}")
            return True
    
    def is_session_valid(self, driver: webdriver.Chrome) -> bool:
        """
        检查当前会话是否有效（是否已登录）
        
        Args:
            driver: WebDriver实例
            
        Returns:
            会话是否有效
        """
        try:
            # 使用登录检测器的逻辑
            success_indicators = self.login_config.get('success_indicators', [])
            
            for selector in success_indicators:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    if element and element.is_displayed():
                        self.logger.debug(f"找到登录指示器: {selector}")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.warning(f"检查会话有效性失败: {e}")
            return False
    
    def get_session_info(self, filepath: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        获取会话信息
        
        Args:
            filepath: 会话文件路径
            
        Returns:
            会话信息字典，如果文件不存在则返回None
        """
        if filepath is None:
            filepath = self.default_session_file
        
        try:
            if not Path(filepath).exists():
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # 返回基本信息
            return {
                'filepath': filepath,
                'timestamp': session_data.get('timestamp'),
                'current_url': session_data.get('current_url'),
                'cookies_count': len(session_data.get('cookies', [])),
                'local_storage_count': len(session_data.get('local_storage', {})),
                'session_storage_count': len(session_data.get('session_storage', {})),
                'is_expired': self._is_session_expired(session_data)
            }
            
        except Exception as e:
            self.logger.error(f"获取会话信息失败: {e}")
            return None
    
    def delete_session(self, filepath: Optional[str] = None) -> bool:
        """
        删除会话文件
        
        Args:
            filepath: 会话文件路径
            
        Returns:
            是否删除成功
        """
        if filepath is None:
            filepath = self.default_session_file
        
        try:
            if Path(filepath).exists():
                Path(filepath).unlink()
                self.logger.info(f"🗑️ 会话文件已删除: {filepath}")
                return True
            else:
                self.logger.warning(f"会话文件不存在: {filepath}")
                return False
                
        except Exception as e:
            self.logger.error(f"删除会话文件失败: {e}")
            return False
    
    def list_sessions(self, directory: str = "data") -> List[Dict[str, Any]]:
        """
        列出所有会话文件
        
        Args:
            directory: 搜索目录
            
        Returns:
            会话文件信息列表
        """
        sessions = []
        
        try:
            data_dir = Path(directory)
            if not data_dir.exists():
                return sessions
            
            # 查找所有.json文件
            for session_file in data_dir.glob("*session*.json"):
                session_info = self.get_session_info(str(session_file))
                if session_info:
                    sessions.append(session_info)
            
            # 按时间排序
            sessions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
        except Exception as e:
            self.logger.error(f"列出会话文件失败: {e}")
        
        return sessions