"""
用户行为模拟器

模拟真实用户的浏览行为，包括鼠标移动、滚动、点击等
"""

import time
import random
import logging
from typing import Optional, Tuple, List
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class BehaviorSimulator:
    """用户行为模拟器"""
    
    def __init__(self, driver: webdriver.Chrome, config: dict = None):
        """
        初始化行为模拟器
        
        Args:
            driver: WebDriver实例
            config: 配置字典
        """
        self.driver = driver
        self.config = config or {}
        self.anti_bot_config = self.config.get('anti_bot', {})
        self.logger = logging.getLogger(__name__)
        
        # 行为参数
        self.mouse_speed = self.anti_bot_config.get('mouse_speed', 'normal')  # slow, normal, fast
        self.scroll_speed = self.anti_bot_config.get('scroll_speed', 'normal')
        self.typing_speed = self.anti_bot_config.get('typing_speed', 'normal')
    
    def random_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
        """
        随机延迟
        
        Args:
            min_seconds: 最小延迟秒数
            max_seconds: 最大延迟秒数
        """
        if self.anti_bot_config.get('random_delay', True):
            delay = random.uniform(min_seconds, max_seconds)
            self.logger.debug(f"随机延迟 {delay:.2f} 秒 - COMMENTED FOR SPEED")
            # time.sleep(delay)
    
    def simulate_human_mouse_move(self, element, offset: Tuple[int, int] = (0, 0)) -> None:
        """
        模拟人类鼠标移动
        
        Args:
            element: 目标元素
            offset: 偏移量 (x, y)
        """
        if not self.anti_bot_config.get('mouse_simulation', True):
            return
        
        try:
            actions = ActionChains(self.driver)
            
            # 获取当前鼠标位置（模拟）
            current_x = random.randint(0, 1920)
            current_y = random.randint(0, 1080)
            
            # 获取目标位置
            target_x = element.location['x'] + element.size['width'] // 2 + offset[0]
            target_y = element.location['y'] + element.size['height'] // 2 + offset[1]
            
            # 计算移动路径（贝塞尔曲线模拟）
            steps = random.randint(5, 15)
            for i in range(steps):
                progress = i / steps
                # 添加一些随机性和曲线
                curve_offset_x = random.randint(-10, 10) * (1 - progress)
                curve_offset_y = random.randint(-10, 10) * (1 - progress)
                
                intermediate_x = current_x + (target_x - current_x) * progress + curve_offset_x
                intermediate_y = current_y + (target_y - current_y) * progress + curve_offset_y
                
                actions.move_by_offset(
                    intermediate_x - current_x, 
                    intermediate_y - current_y
                )
                current_x, current_y = intermediate_x, intermediate_y
                
                # 随机暂停
                if random.random() < 0.3:
                    actions.pause(random.uniform(0.01, 0.05))
            
            # 最终移动到目标
            actions.move_to_element_with_offset(element, offset[0], offset[1])
            actions.perform()
            
            # 短暂停留 - COMMENTED FOR SPEED
            # time.sleep(random.uniform(0.1, 0.3))
            
        except Exception as e:
            self.logger.warning(f"模拟鼠标移动失败: {e}")
    
    def simulate_scroll(self, direction: str = 'down', distance: int = None) -> None:
        """
        模拟滚动行为
        
        Args:
            direction: 滚动方向 ('up', 'down')
            distance: 滚动距离，None为随机
        """
        if not self.anti_bot_config.get('scroll_simulation', True):
            return
        
        try:
            if distance is None:
                distance = random.randint(200, 800)
            
            if direction == 'down':
                distance = abs(distance)
            else:
                distance = -abs(distance)
            
            # 分段滚动，模拟真实用户行为
            segments = random.randint(3, 8)
            segment_distance = distance // segments
            
            for i in range(segments):
                self.driver.execute_script(f"window.scrollBy(0, {segment_distance});")
                
                # 随机停顿
                pause_time = random.uniform(0.1, 0.5)
                # time.sleep(pause_time)  # COMMENTED FOR SPEED
                
                # 偶尔反向滚动一点（模拟用户调整）
                if random.random() < 0.2:
                    reverse_distance = random.randint(10, 50)
                    if direction == 'down':
                        reverse_distance = -reverse_distance
                    self.driver.execute_script(f"window.scrollBy(0, {reverse_distance});")
                    # time.sleep(random.uniform(0.1, 0.3))  # COMMENTED FOR SPEED
            
            self.logger.debug(f"模拟滚动: {direction} {distance}px")
            
        except Exception as e:
            self.logger.warning(f"模拟滚动失败: {e}")
    
    def simulate_reading_pause(self, content_length: int = 100) -> None:
        """
        模拟阅读停顿（优化版本）
        
        Args:
            content_length: 内容长度（字符数）
        """
        # 优化：大幅减少阅读时间
        base_time = 0.5  # 从2.0减少到0.5
        reading_time = base_time + (content_length / 500) * random.uniform(0.1, 0.3)  # 减少计算因子
        
        # 限制最大阅读时间
        reading_time = min(reading_time, 3.0)  # 从10.0减少到3.0
        
        self.logger.debug(f"模拟阅读停顿: {reading_time:.2f} 秒 - COMMENTED FOR SPEED")
        # time.sleep(reading_time)
    
    def natural_click(self, element, double_click: bool = False) -> bool:
        """
        自然点击元素
        
        Args:
            element: 要点击的元素
            double_click: 是否双击
            
        Returns:
            是否点击成功
        """
        try:
            # 先移动鼠标到元素
            self.simulate_human_mouse_move(element)
            
            # 短暂停顿 - COMMENTED FOR SPEED
            # time.sleep(random.uniform(0.1, 0.3))
            
            # 点击
            actions = ActionChains(self.driver)
            if double_click:
                actions.double_click(element)
            else:
                actions.click(element)
            actions.perform()
            
            # 点击后停顿 - COMMENTED FOR SPEED
            # time.sleep(random.uniform(0.2, 0.5))
            
            self.logger.debug(f"自然点击元素: {'双击' if double_click else '单击'}")
            return True
            
        except Exception as e:
            self.logger.warning(f"自然点击失败: {e}")
            return False
    
    def simulate_page_exploration(self, duration: float = 5.0) -> None:
        """
        模拟页面探索行为（优化版本）
        
        Args:
            duration: 探索持续时间（秒）
        """
        try:
            start_time = time.time()
            
            # 优化：减少动作复杂度，主要做滚动
            while time.time() - start_time < duration:
                action = random.choice(['scroll', 'pause'])  # 移除复杂的鼠标移动
                
                if action == 'scroll':
                    direction = random.choice(['up', 'down'])
                    self.simulate_scroll(direction, random.randint(100, 300))  # 减少滚动距离
                    
                elif action == 'pause':
                    # time.sleep(random.uniform(0.2, 0.8))  # 减少暂停时间 - COMMENTED FOR SPEED
                    pass

                # 优化：减少随机停顿时间 - COMMENTED FOR SPEED
                # time.sleep(random.uniform(0.2, 0.5))
            
            self.logger.debug(f"页面探索完成: {duration} 秒")
            
        except Exception as e:
            self.logger.warning(f"页面探索失败: {e}")
    
    def wait_for_page_load(self, timeout: int = 30) -> bool:
        """
        等待页面加载完成，并模拟用户等待行为
        
        Args:
            timeout: 超时时间
            
        Returns:
            是否加载成功
        """
        try:
            # 等待页面基本加载
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            # 模拟用户等待和观察
            observation_time = random.uniform(1.0, 3.0)
            # time.sleep(observation_time)  # COMMENTED FOR SPEED
            
            # 轻微滚动，模拟用户查看页面
            if random.random() < 0.7:
                self.simulate_scroll('down', random.randint(100, 300))
                # time.sleep(random.uniform(0.5, 1.0))  # COMMENTED FOR SPEED
                self.simulate_scroll('up', random.randint(50, 150))
            
            return True
            
        except TimeoutException:
            self.logger.warning("页面加载超时")
            return False
        except Exception as e:
            self.logger.warning(f"等待页面加载失败: {e}")
            return False
    
    def natural_navigate_to_url(self, url: str, from_link: bool = False) -> bool:
        """
        自然地导航到URL（优化版本）
        
        Args:
            url: 目标URL
            from_link: 是否来自链接点击
            
        Returns:
            是否导航成功
        """
        try:
            # 验证URL格式
            if not url or not isinstance(url, str):
                self.logger.error(f"无效的URL: {url}")
                return False
            
            if not url.startswith(('http://', 'https://')):
                self.logger.error(f"URL格式错误: {url}")
                return False
            
            if from_link:
                # 优化：减少等待时间
                self.random_delay(0.2, 0.8)
            else:
                # 优化：减少直接导航延迟
                self.random_delay(0.5, 1.0)
            
            # 记录当前URL以便回滚
            current_url = None
            try:
                current_url = self.driver.current_url
            except:
                pass
            
            # 导航到URL
            self.driver.get(url)
            
            # 等待页面加载并模拟用户行为
            if self.wait_for_page_load():
                # 验证导航是否成功
                try:
                    new_url = self.driver.current_url
                    # 检查是否被重定向到错误页面
                    if self._is_error_page(new_url):
                        self.logger.warning(f"导航到错误页面: {new_url}")
                        return False
                    
                    # 优化：减少页面探索概率和时间
                    if random.random() < 0.3:  # 从60%减少到30%
                        self.simulate_page_exploration(random.uniform(1.0, 2.0))  # 从2-5秒减少到1-2秒
                    return True
                except Exception as e:
                    self.logger.warning(f"导航后验证失败: {e}")
                    return False
            
            return False
            
        except Exception as e:
            self.logger.error(f"自然导航失败: {e}")
            # 尝试恢复到之前的页面
            if current_url:
                try:
                    self.driver.get(current_url)
                except:
                    pass
            return False
    
    def _is_error_page(self, url: str) -> bool:
        """
        检查是否为错误页面
        
        Args:
            url: 页面URL
            
        Returns:
            是否为错误页面
        """
        try:
            # 检查URL中的错误指示器
            error_indicators = ['404', 'error', 'notfound', 'expired']
            url_lower = url.lower()
            
            if any(indicator in url_lower for indicator in error_indicators):
                return True
            
            # 检查页面标题和内容
            try:
                title = self.driver.title.lower()
                if any(indicator in title for indicator in ['404', 'error', '页面不存在', '找不到']):
                    return True
                
                # 检查页面源码中的错误指示器
                page_source = self.driver.page_source.lower()
                error_texts = ['404', 'page not found', '页面不存在', '职位已下线', '招聘已结束']
                if any(text in page_source for text in error_texts):
                    return True
                    
            except:
                pass
            
            return False
            
        except Exception:
            return False
    
    def get_random_viewport_position(self) -> Tuple[int, int]:
        """
        获取随机的视口位置
        
        Returns:
            (x, y) 坐标
        """
        try:
            viewport_width = self.driver.execute_script("return window.innerWidth")
            viewport_height = self.driver.execute_script("return window.innerHeight")
            
            x = random.randint(50, viewport_width - 50)
            y = random.randint(50, viewport_height - 50)
            
            return x, y
            
        except:
            return random.randint(100, 1800), random.randint(100, 900)