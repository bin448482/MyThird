"""
会话保活器
负责在长时间延迟期间保持浏览器会话活跃
"""

import time
import logging
import threading
from typing import Optional, Callable
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import WebDriverException


class SessionKeeper:
    """会话保活器"""
    
    def __init__(self, driver: WebDriver, check_interval: int = 30):
        """
        初始化会话保活器
        
        Args:
            driver: WebDriver实例
            check_interval: 检查间隔（秒）
        """
        self.driver = driver
        self.check_interval = check_interval
        self.logger = logging.getLogger(__name__)
        self._stop_event = threading.Event()
        self._keep_alive_thread: Optional[threading.Thread] = None
        self._is_running = False
    
    def start_keep_alive(self) -> bool:
        """
        启动会话保活
        
        Returns:
            是否启动成功
        """
        if self._is_running:
            self.logger.warning("会话保活已在运行中")
            return True
        
        try:
            self.logger.info(f"🔄 启动会话保活，检查间隔: {self.check_interval}秒")
            self._stop_event.clear()
            self._keep_alive_thread = threading.Thread(target=self._keep_alive_loop, daemon=True)
            self._keep_alive_thread.start()
            self._is_running = True
            return True
            
        except Exception as e:
            self.logger.error(f"启动会话保活失败: {e}")
            return False
    
    def stop_keep_alive(self):
        """停止会话保活"""
        if not self._is_running:
            return
        
        self.logger.info("🛑 停止会话保活")
        self._stop_event.set()
        
        if self._keep_alive_thread and self._keep_alive_thread.is_alive():
            self._keep_alive_thread.join(timeout=5)
        
        self._is_running = False
    
    def _keep_alive_loop(self):
        """会话保活循环"""
        while not self._stop_event.is_set():
            try:
                # 执行轻量级操作保持会话
                if self._ping_session():
                    self.logger.debug("✅ 会话保活检查成功")
                else:
                    self.logger.warning("⚠️ 会话保活检查失败")
                    break
                
                # 等待下次检查
                self._stop_event.wait(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"会话保活循环异常: {e}")
                break
        
        self._is_running = False
        self.logger.info("会话保活循环已停止")
    
    def _ping_session(self) -> bool:
        """
        ping会话以保持活跃
        
        Returns:
            会话是否仍然有效
        """
        try:
            # 执行轻量级JavaScript检查
            result = self.driver.execute_script("return document.readyState;")
            
            # 检查当前URL是否可访问
            current_url = self.driver.current_url
            
            return result == "complete" and current_url is not None
            
        except WebDriverException as e:
            self.logger.warning(f"会话ping失败: {e}")
            return False
        except Exception as e:
            self.logger.error(f"会话ping异常: {e}")
            return False
    
    def keep_alive_during_delay(self, delay_minutes: float) -> bool:
        """
        在延迟期间保持会话活跃
        
        Args:
            delay_minutes: 延迟时间（分钟）
            
        Returns:
            会话是否保持有效
        """
        total_seconds = delay_minutes * 60
        self.logger.info(f"🕐 开始 {delay_minutes:.1f} 分钟延迟，期间保持会话活跃")
        
        start_time = time.time()
        last_check_time = start_time
        
        while time.time() - start_time < total_seconds:
            current_time = time.time()
            
            # 每隔检查间隔执行一次保活检查
            if current_time - last_check_time >= self.check_interval:
                if not self._ping_session():
                    elapsed = (current_time - start_time) / 60
                    self.logger.error(f"❌ 会话在延迟 {elapsed:.1f}/{delay_minutes:.1f} 分钟后失效")
                    return False
                
                elapsed = (current_time - start_time) / 60
                remaining = delay_minutes - elapsed
                self.logger.debug(f"🔄 会话保活检查 {elapsed:.1f}/{delay_minutes:.1f} 分钟，剩余 {remaining:.1f} 分钟")
                last_check_time = current_time
            
            # 短暂休眠避免CPU占用过高
            time.sleep(1)
        
        self.logger.info(f"✅ {delay_minutes:.1f} 分钟延迟完成，会话保持有效")
        return True
    
    def is_session_alive(self) -> bool:
        """
        检查会话是否仍然活跃
        
        Returns:
            会话是否活跃
        """
        return self._ping_session()
    
    def __enter__(self):
        """上下文管理器入口"""
        self.start_keep_alive()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop_keep_alive()