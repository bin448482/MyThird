"""
反爬虫系统

基于现有的BehaviorSimulator，为投递功能提供专门的反爬虫策略
"""

import logging
import random
import time
from typing import Dict, Any, Optional
from selenium.webdriver.common.by import By

from ..utils.behavior_simulator import BehaviorSimulator


class AntiCrawlerSystem:
    """反爬虫系统 - 基于BehaviorSimulator的封装"""
    
    def __init__(self, driver, config: Dict[str, Any], data_manager=None):
        """
        初始化反爬虫系统
        
        Args:
            driver: WebDriver实例
            config: 配置字典
            data_manager: 数据管理器实例，用于获取真实的投递统计
        """
        self.driver = driver
        self.config = config
        self.data_manager = data_manager
        self.logger = logging.getLogger(__name__)
        
        # 初始化行为模拟器
        self.behavior_simulator = BehaviorSimulator(driver, config)
        
        # 投递专用配置
        self.submission_config = config.get('submission_engine', {})
        self.delay_range = self.submission_config.get('submission_delay_range', [3.0, 8.0])
        self.max_daily_submissions = self.submission_config.get('max_daily_submissions', 50)
        
        # 统计信息
        self.stats = {
            'total_delays': 0,
            'total_delay_time': 0.0,
            'daily_submission_count': self._get_actual_daily_count(),
            'last_reset_date': time.strftime('%Y-%m-%d')
        }
    
    def get_random_delay(self, base_delay: float = None) -> float:
        """
        获取随机延迟时间
        
        Args:
            base_delay: 基础延迟时间，None则使用配置的范围
            
        Returns:
            延迟时间（秒）
        """
        if base_delay is not None:
            # 在基础延迟的基础上增加随机变化
            variance = base_delay * 0.3  # 30%的变化范围
            delay = random.uniform(base_delay - variance, base_delay + variance)
        else:
            # 使用配置的延迟范围
            delay = random.uniform(self.delay_range[0], self.delay_range[1])
        
        # 确保延迟不小于1秒
        delay = max(1.0, delay)
        
        self.stats['total_delays'] += 1
        self.stats['total_delay_time'] += delay
        
        self.logger.debug(f"生成随机延迟: {delay:.2f}秒")
        return delay
    
    def apply_delay(self, base_delay: float = None):
        """
        应用随机延迟
        
        Args:
            base_delay: 基础延迟时间
        """
        delay = self.get_random_delay(base_delay)
        self.logger.info(f"应用投递延迟: {delay:.2f}秒")
        time.sleep(delay)
    
    def simulate_job_page_reading(self, min_time: float = 15.0, max_time: float = 45.0):
        """
        模拟阅读职位页面
        
        Args:
            min_time: 最小阅读时间（秒）
            max_time: 最大阅读时间（秒）
        """
        reading_time = random.uniform(min_time, max_time)
        self.logger.info(f"模拟阅读职位页面: {reading_time:.1f}秒")
        
        # 使用BehaviorSimulator的页面探索功能
        self.behavior_simulator.simulate_page_exploration(reading_time)
        
        # 额外的阅读行为
        self._simulate_detailed_reading()
    
    def _simulate_detailed_reading(self):
        """模拟详细阅读行为"""
        try:
            # 随机滚动查看职位详情
            scroll_actions = random.randint(2, 5)
            for _ in range(scroll_actions):
                direction = random.choice(['down', 'up'])
                self.behavior_simulator.simulate_scroll(direction)
                
                # 阅读停顿
                self.behavior_simulator.simulate_reading_pause(random.randint(50, 200))
            
            self.logger.debug("详细阅读模拟完成")
            
        except Exception as e:
            self.logger.warning(f"详细阅读模拟失败: {e}")
    
    def safe_navigate_to_job(self, job_url: str) -> bool:
        """
        安全导航到职位页面（简化版本）
        
        Args:
            job_url: 职位URL
            
        Returns:
            是否导航成功
        """
        try:
            self.logger.info(f"安全导航到职位页面: {job_url}")
            
            # 检查URL有效性
            if not job_url or not job_url.startswith(('http://', 'https://')):
                self.logger.error(f"无效的URL: {job_url}")
                return False
            
            # 直接导航，不使用复杂的行为模拟
            self.driver.get(job_url)
            
            # 等待页面加载
            time.sleep(3)
            
            # 验证页面是否正确加载
            current_url = self.driver.current_url
            if self._is_valid_job_page(current_url):
                self.logger.info("职位页面导航成功")
                return True
            else:
                self.logger.warning(f"页面加载异常，当前URL: {current_url}")
                return False
                
        except Exception as e:
            self.logger.error(f"安全导航失败: {e}")
            return False
    
    def _is_valid_job_page(self, current_url: str) -> bool:
        """
        验证是否为有效的职位页面
        
        Args:
            current_url: 当前页面URL
            
        Returns:
            是否为有效职位页面
        """
        try:
            # 检查URL是否包含职位页面特征
            job_page_indicators = [
                'jobs.51job.com',
                'zhaopin.com/jobs',
                'liepin.com/job',
                'boss.zhipin.com/job'
            ]
            
            if any(indicator in current_url for indicator in job_page_indicators):
                # 进一步检查页面内容
                try:
                    # 检查页面标题
                    title = self.driver.title
                    if title and len(title) > 5:
                        return True
                    
                    # 检查是否有职位相关元素
                    job_elements = self.driver.find_elements(By.CSS_SELECTOR,
                        ".job-title, .job-name, .position-title, h1")
                    if job_elements:
                        return True
                        
                except:
                    pass
            
            # 检查是否被重定向到错误页面
            error_indicators = [
                '404', 'not found', 'error', 'expired',
                '页面不存在', '职位已下线', '招聘已结束'
            ]
            
            page_text = self.driver.page_source.lower()
            if any(indicator in page_text for indicator in error_indicators):
                return False
            
            return True
            
        except Exception as e:
            self.logger.warning(f"页面验证失败: {e}")
            return True  # 默认认为有效，避免误判
    
    def safe_click_button(self, element) -> bool:
        """
        安全点击按钮
        
        Args:
            element: 按钮元素
            
        Returns:
            是否点击成功
        """
        try:
            # 使用BehaviorSimulator的自然点击
            success = self.behavior_simulator.natural_click(element)
            
            if success:
                self.logger.info("按钮点击成功")
                # 点击后等待
                self.behavior_simulator.random_delay(1.0, 3.0)
            else:
                self.logger.warning("按钮点击失败")
            
            return success
            
        except Exception as e:
            self.logger.error(f"安全点击失败: {e}")
            return False
    
    def get_batch_delay(self, batch_size: int, completed_count: int) -> float:
        """
        获取批次间延迟
        
        Args:
            batch_size: 批次大小
            completed_count: 已完成数量
            
        Returns:
            延迟时间（秒）
        """
        # 每完成一个批次，增加延迟
        if completed_count > 0 and completed_count % batch_size == 0:
            # 批次间延迟：2-5分钟
            batch_delay = random.uniform(120, 300)
            self.logger.info(f"批次间延迟: {batch_delay/60:.1f}分钟")
            return batch_delay
        
        return 0.0
    
    def apply_batch_delay(self, batch_size: int, completed_count: int):
        """
        应用批次间延迟
        
        Args:
            batch_size: 批次大小
            completed_count: 已完成数量
        """
        delay = self.get_batch_delay(batch_size, completed_count)
        if delay > 0:
            self.logger.info(f"应用批次延迟: {delay/60:.1f}分钟")
            time.sleep(delay)
    
    def check_daily_limit(self) -> bool:
        """
        检查是否达到每日限制
        
        Returns:
            是否可以继续投递
        """
        # 检查日期是否变更
        current_date = time.strftime('%Y-%m-%d')
        if current_date != self.stats['last_reset_date']:
            self.stats['last_reset_date'] = current_date
            self.logger.info("日期已变更，重新获取投递计数")
        
        # 从数据库获取真实的今日投递数量
        actual_count = self._get_actual_daily_count()
        self.stats['daily_submission_count'] = actual_count
        
        # 检查是否达到限制
        if actual_count >= self.max_daily_submissions:
            self.logger.warning(f"已达到每日投递限制: {self.max_daily_submissions} (实际已投递: {actual_count})")
            return False
        
        return True
    
    def increment_daily_count(self):
        """增加每日投递计数"""
        # 从数据库获取真实的今日投递数量
        actual_count = self._get_actual_daily_count()
        self.stats['daily_submission_count'] = actual_count
        remaining = self.max_daily_submissions - actual_count
        self.logger.info(f"今日已投递: {actual_count}, 剩余: {remaining}")
    
    def _get_actual_daily_count(self) -> int:
        """
        从数据库获取真实的今日投递数量
        
        Returns:
            今日实际投递数量
        """
        try:
            if self.data_manager:
                return self.data_manager.get_daily_submission_count()
            else:
                self.logger.warning("数据管理器未设置，无法获取真实投递数量")
                return 0
        except Exception as e:
            self.logger.error(f"获取真实投递数量失败: {e}")
            return 0
    
    def get_remaining_daily_quota(self) -> int:
        """获取剩余每日配额"""
        if not self.check_daily_limit():
            return 0
        actual_count = self._get_actual_daily_count()
        return max(0, self.max_daily_submissions - actual_count)
    
    def simulate_pre_application_behavior(self):
        """模拟申请前的行为"""
        try:
            self.logger.info("模拟申请前行为")
            
            # 1. 页面滚动查看
            self.behavior_simulator.simulate_scroll('down', random.randint(200, 500))
            self.behavior_simulator.random_delay(1.0, 2.0)
            
            # 2. 向上滚动查看公司信息
            self.behavior_simulator.simulate_scroll('up', random.randint(100, 300))
            self.behavior_simulator.random_delay(0.5, 1.5)
            
            # 3. 再次向下滚动到申请按钮
            self.behavior_simulator.simulate_scroll('down', random.randint(300, 600))
            self.behavior_simulator.random_delay(1.0, 2.0)
            
            self.logger.debug("申请前行为模拟完成")
            
        except Exception as e:
            self.logger.warning(f"申请前行为模拟失败: {e}")
    
    def simulate_post_application_behavior(self):
        """模拟申请后的行为"""
        try:
            self.logger.info("模拟申请后行为")
            
            # 1. 等待页面响应
            self.behavior_simulator.random_delay(2.0, 4.0)
            
            # 2. 轻微滚动查看结果
            if random.random() < 0.7:
                self.behavior_simulator.simulate_scroll('down', random.randint(100, 300))
                self.behavior_simulator.random_delay(1.0, 2.0)
            
            # 3. 停留一段时间
            self.behavior_simulator.random_delay(2.0, 5.0)
            
            self.logger.debug("申请后行为模拟完成")
            
        except Exception as e:
            self.logger.warning(f"申请后行为模拟失败: {e}")
    
    def check_detection_risk(self) -> Dict[str, Any]:
        """
        检查被检测的风险
        
        Returns:
            风险评估结果
        """
        risk_factors = {
            'high_frequency': False,
            'daily_limit_reached': False,
            'consistent_timing': False,
            'risk_level': 'low'
        }
        
        try:
            # 检查操作频率
            if self.stats['total_delays'] > 0:
                avg_delay = self.stats['total_delay_time'] / self.stats['total_delays']
                if avg_delay < 2.0:
                    risk_factors['high_frequency'] = True
            
            # 检查每日限制
            if self.stats['daily_submission_count'] >= self.max_daily_submissions * 0.8:
                risk_factors['daily_limit_reached'] = True
            
            # 计算总体风险等级
            risk_count = sum(1 for v in risk_factors.values() if v is True)
            
            if risk_count >= 2:
                risk_factors['risk_level'] = 'high'
            elif risk_count == 1:
                risk_factors['risk_level'] = 'medium'
            else:
                risk_factors['risk_level'] = 'low'
            
            return risk_factors
            
        except Exception as e:
            self.logger.error(f"风险检查失败: {e}")
            return risk_factors
    
    def apply_risk_mitigation(self, risk_assessment: Dict[str, Any]):
        """
        应用风险缓解措施
        
        Args:
            risk_assessment: 风险评估结果
        """
        try:
            risk_level = risk_assessment.get('risk_level', 'low')
            
            if risk_level == 'high':
                # 高风险：长时间延迟
                delay = random.uniform(300, 600)  # 5-10分钟
                self.logger.warning(f"检测到高风险，应用长延迟: {delay/60:.1f}分钟")
                time.sleep(delay)
                
                # 执行更多人类行为模拟
                self.behavior_simulator.simulate_page_exploration(random.uniform(10, 20))
                
            elif risk_level == 'medium':
                # 中等风险：中等延迟
                delay = random.uniform(60, 180)  # 1-3分钟
                self.logger.info(f"检测到中等风险，应用中等延迟: {delay/60:.1f}分钟")
                time.sleep(delay)
                
                # 执行人类行为模拟
                self.behavior_simulator.simulate_page_exploration(random.uniform(5, 10))
            
        except Exception as e:
            self.logger.error(f"风险缓解失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        stats = self.stats.copy()
        
        # 计算平均延迟
        if stats['total_delays'] > 0:
            stats['average_delay'] = stats['total_delay_time'] / stats['total_delays']
        else:
            stats['average_delay'] = 0.0
        
        # 添加剩余配额
        stats['remaining_daily_quota'] = self.get_remaining_daily_quota()
        
        return stats
    
    def reset_daily_stats(self):
        """重置每日统计"""
        self.stats['daily_submission_count'] = 0
        self.stats['last_reset_date'] = time.strftime('%Y-%m-%d')
        self.logger.info("每日统计已重置")