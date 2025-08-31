"""
浏览器管理器

负责WebDriver的创建、配置和管理
"""

import logging
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from ..core.exceptions import WebDriverError


class BrowserManager:
    """浏览器管理器"""
    
    def __init__(self, config: dict):
        """
        初始化浏览器管理器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.selenium_config = config.get('selenium', {})
        self.mode_config = config.get('mode', {})
        self.driver: Optional[webdriver.Chrome] = None
        self.logger = logging.getLogger(__name__)
    
    def create_driver(self) -> webdriver.Chrome:
        """
        创建WebDriver实例
        
        Returns:
            Chrome WebDriver实例
            
        Raises:
            WebDriverError: WebDriver创建失败
        """
        try:
            self.logger.info("🔧 创建Chrome WebDriver...")
            
            # Chrome选项配置
            chrome_options = self._get_chrome_options()
            
            # 自动下载并设置ChromeDriver
            service = Service(ChromeDriverManager().install())
            
            # 创建WebDriver实例
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 设置超时和等待时间
            self._configure_timeouts()
            
            # 执行反检测脚本
            self._apply_anti_detection()
            
            self.logger.info("✅ WebDriver创建成功")
            return self.driver
            
        except Exception as e:
            self.logger.error(f"❌ WebDriver创建失败: {e}")
            raise WebDriverError(f"WebDriver创建失败: {e}")
    
    def _get_chrome_options(self) -> Options:
        """获取Chrome选项配置"""
        chrome_options = Options()
        
        # 基础选项
        if self.selenium_config.get('headless', False):
            chrome_options.add_argument('--headless')
        
        # 增强反爬虫设置
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        # chrome_options.add_argument('--disable-images')  # 注释掉：登录需要显示二维码图片
        # chrome_options.add_argument('--disable-javascript')  # 注释掉：现代网站需要JavaScript
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        chrome_options.add_argument('--disable-features=TranslateUI')
        chrome_options.add_argument('--disable-ipc-flooding-protection')
        
        # 实验性选项
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 设置首选项
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,  # 禁用通知
                # "images": 2,  # 注释掉：登录需要显示二维码图片
                "plugins": 2,  # 禁用插件
                "popups": 2,  # 禁用弹窗
                "geolocation": 2,  # 禁用地理位置
                "media_stream": 2,  # 禁用媒体流
            },
            "profile.managed_default_content_settings": {
                # "images": 2  # 注释掉：登录需要显示二维码图片
            }
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # 窗口大小
        window_size = self.selenium_config.get('window_size', '1920,1080')
        chrome_options.add_argument(f'--window-size={window_size}')
        
        # 用户代理
        user_agent = self._get_user_agent()
        chrome_options.add_argument(f'--user-agent={user_agent}')
        
        # 禁用日志输出
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_argument('--silent')
        
        # 开发模式特殊配置
        if self.mode_config.get('development', False):
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-running-insecure-content')
        
        return chrome_options
    
    def _get_user_agent(self) -> str:
        """获取用户代理字符串"""
        import random
        
        # 随机选择一个真实的用户代理
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        return random.choice(user_agents)
    
    def _configure_timeouts(self) -> None:
        """配置超时时间"""
        if not self.driver:
            return
        
        page_load_timeout = self.selenium_config.get('page_load_timeout', 30)
        element_wait_timeout = self.selenium_config.get('element_wait_timeout', 10)
        implicit_wait = self.selenium_config.get('implicit_wait', 5)
        
        self.driver.implicitly_wait(implicit_wait)
        self.driver.set_page_load_timeout(page_load_timeout)
        
        self.logger.debug(f"超时配置: 页面加载={page_load_timeout}s, 元素等待={element_wait_timeout}s, 隐式等待={implicit_wait}s")
    
    def _apply_anti_detection(self) -> None:
        """应用反检测脚本"""
        if not self.driver:
            return
        
        try:
            # 隐藏webdriver属性
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            
            # 修改plugins长度和内容
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'plugins', {
                    get: () => {
                        return [
                            {name: 'Chrome PDF Plugin', description: 'Portable Document Format'},
                            {name: 'Chrome PDF Viewer', description: 'PDF Viewer'},
                            {name: 'Native Client', description: 'Native Client'},
                            {name: 'Chromium PDF Plugin', description: 'Portable Document Format'},
                            {name: 'Microsoft Edge PDF Plugin', description: 'PDF Plugin'}
                        ];
                    }
                });
            """)
            
            # 修改languages
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en-US', 'en']})"
            )
            
            # 修改platform
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'platform', {get: () => 'Win32'})"
            )
            
            # 修改hardwareConcurrency
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8})"
            )
            
            # 修改deviceMemory
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'deviceMemory', {get: () => 8})"
            )
            
            # 隐藏自动化相关属性
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({
                        query: () => Promise.resolve({state: 'granted'})
                    })
                });
            """)
            
            # 修改chrome对象
            self.driver.execute_script("""
                if (!window.chrome) {
                    window.chrome = {};
                }
                if (!window.chrome.runtime) {
                    window.chrome.runtime = {};
                }
                if (!window.chrome.runtime.onConnect) {
                    window.chrome.runtime.onConnect = undefined;
                }
                if (!window.chrome.runtime.onMessage) {
                    window.chrome.runtime.onMessage = undefined;
                }
            """)
            
            # 移除selenium相关痕迹
            self.driver.execute_script("""
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_JSON;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Object;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Proxy;
            """)
            
            self.logger.debug("增强反检测脚本已应用")
            
        except Exception as e:
            self.logger.warning(f"应用反检测脚本失败: {e}")
    
    def get_driver(self) -> Optional[webdriver.Chrome]:
        """
        获取当前WebDriver实例
        
        Returns:
            WebDriver实例，如果未创建则返回None
        """
        return self.driver
    
    def is_driver_alive(self) -> bool:
        """
        检查WebDriver是否仍然活跃
        
        Returns:
            WebDriver是否活跃
        """
        if not self.driver:
            return False
        
        try:
            # 尝试获取当前URL来检查driver是否活跃
            _ = self.driver.current_url
            return True
        except Exception:
            return False
    
    def restart_driver(self) -> webdriver.Chrome:
        """
        重启WebDriver
        
        Returns:
            新的WebDriver实例
        """
        self.logger.info("🔄 重启WebDriver...")
        
        # 关闭现有driver
        self.quit_driver()
        
        # 创建新的driver
        return self.create_driver()
    
    def quit_driver(self) -> None:
        """关闭WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("🧹 WebDriver已关闭")
            except Exception as e:
                self.logger.warning(f"关闭WebDriver时出错: {e}")
            finally:
                self.driver = None
    
    def create_wait(self, timeout: Optional[int] = None) -> WebDriverWait:
        """
        创建WebDriverWait实例
        
        Args:
            timeout: 超时时间，如果为None则使用配置中的默认值
            
        Returns:
            WebDriverWait实例
            
        Raises:
            ValueError: WebDriver未创建
        """
        if not self.driver:
            raise ValueError("WebDriver未创建，请先调用create_driver()")
        
        if timeout is None:
            timeout = self.selenium_config.get('element_wait_timeout', 10)
        
        return WebDriverWait(self.driver, timeout)
    
    def __enter__(self):
        """上下文管理器入口"""
        self.create_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.quit_driver()