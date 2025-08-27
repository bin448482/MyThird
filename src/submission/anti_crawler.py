"""
反爬虫系统

基于现有的BehaviorSimulator，为投递功能提供专门的反爬虫策略
增强版：支持会话保活和智能重连
"""

import logging
import random
import time
from typing import Dict, Any, Optional
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

from ..utils.behavior_simulator import BehaviorSimulator
from ..auth.session_keeper import SessionKeeper
from ..auth.session_recovery import SessionRecovery


class AntiCrawlerSystem:
    """反爬虫系统 - 基于BehaviorSimulator的封装，增强版支持会话保活"""
    
    def __init__(self, driver, config: Dict[str, Any], data_manager=None,
                 browser_manager=None, login_manager=None):
        """
        初始化反爬虫系统
        
        Args:
            driver: WebDriver实例
            config: 配置字典
            data_manager: 数据管理器实例，用于获取真实的投递统计
            browser_manager: 浏览器管理器实例
            login_manager: 登录管理器实例
        """
        self.driver = driver
        self.config = config
        self.data_manager = data_manager
        self.browser_manager = browser_manager
        self.login_manager = login_manager
        self.logger = logging.getLogger(__name__)
        
        # 初始化行为模拟器
        self.behavior_simulator = BehaviorSimulator(driver, config)
        
        # 初始化会话保活器
        self.session_keeper = SessionKeeper(driver, check_interval=30)
        
        # 初始化会话恢复器（如果提供了必要的管理器）
        self.session_recovery = None
        if browser_manager and login_manager:
            self.session_recovery = SessionRecovery(browser_manager, login_manager, config)
        
        # 投递专用配置
        self.submission_config = config.get('submission_engine', {})
        self.delay_range = self.submission_config.get('submission_delay_range', [2.0, 5.0])
        self.max_daily_submissions = self.submission_config.get('max_daily_submissions', 50)
        
        # 会话保活配置
        self.session_config = config.get('session_management', {})
        self.enable_session_keepalive = self.session_config.get('enable_keepalive', True)
        self.keepalive_threshold = self.session_config.get('keepalive_threshold_minutes', 2.0)
        
        # 统计信息
        self.stats = {
            'total_delays': 0,
            'total_delay_time': 0.0,
            'daily_submission_count': self._get_actual_daily_count(),
            'last_reset_date': time.strftime('%Y-%m-%d'),
            'session_recoveries': 0,
            'keepalive_activations': 0
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
        安全导航到职位页面（增强版，支持会话恢复）
        
        Args:
            job_url: 职位URL
            
        Returns:
            是否导航成功
        """
        def _navigate_operation():
            self.logger.info(f"安全导航到职位页面: {job_url}")
            
            # 检查URL有效性
            if not job_url or not job_url.startswith(('http://', 'https://')):
                self.logger.error(f"无效的URL: {job_url}")
                return False
            
            # 直接导航，不使用复杂的行为模拟
            self.driver.get(job_url)
            
            # 等待页面加载
            time.sleep(1)
            
            # 验证页面是否正确加载
            current_url = self.driver.current_url
            if self._is_valid_job_page(current_url):
                self.logger.info("职位页面导航成功")
                return True
            else:
                self.logger.warning(f"页面加载异常，当前URL: {current_url}")
                return False
        
        # 如果有会话恢复器，使用带恢复的导航
        if self.session_recovery:
            try:
                return self.session_recovery.with_session_recovery(
                    _navigate_operation,
                    f"导航到职位页面: {job_url}"
                )
            except Exception as e:
                self.logger.error(f"会话恢复导航失败: {e}")
                return False
        else:
            # 传统导航方式
            try:
                return _navigate_operation()
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
    
    def get_batch_delay(self, batch_size: int, completed_count: int,
                       success_count: int = None) -> float:
        """
        获取智能批次间延迟（基于成功率动态调整）
        
        Args:
            batch_size: 批次大小
            completed_count: 已完成数量
            success_count: 成功数量
            
        Returns:
            延迟时间（秒）
        """
        # 每完成一个批次，增加延迟
        if completed_count > 0 and completed_count % batch_size == 0:
            # 基础延迟：2-5分钟
            base_delay = random.uniform(120, 300)
            
            # 如果提供了成功率信息，动态调整
            if success_count is not None:
                success_rate = success_count / completed_count if completed_count > 0 else 0
                delay_multiplier = self._calculate_delay_multiplier(success_rate)
                batch_delay = base_delay * delay_multiplier
                
                self.logger.info(f"智能批次延迟: {batch_delay/60:.1f}分钟 "
                               f"(成功率: {success_rate:.1%}, 调整系数: {delay_multiplier:.2f})")
            else:
                batch_delay = base_delay
                self.logger.info(f"批次间延迟: {batch_delay/60:.1f}分钟")
            
            return batch_delay
        
        return 0.0
    
    def _calculate_delay_multiplier(self, success_rate: float) -> float:
        """
        根据成功率计算延迟调整系数
        
        Args:
            success_rate: 成功率 (0.0-1.0)
            
        Returns:
            延迟调整系数
        """
        if success_rate >= 0.8:
            # 成功率高，减少延迟
            return random.uniform(0.5, 0.7)
        elif success_rate >= 0.5:
            # 成功率中等，正常延迟
            return random.uniform(0.8, 1.2)
        else:
            # 成功率低，增加延迟
            return random.uniform(1.5, 2.0)
    
    def apply_batch_delay(self, batch_size: int, completed_count: int,
                         success_count: int = None):
        """
        应用智能批次间延迟（带会话保活）
        
        Args:
            batch_size: 批次大小
            completed_count: 已完成数量
            success_count: 成功数量
        """
        delay = self.get_batch_delay(batch_size, completed_count, success_count)
        if delay > 0:
            delay_minutes = delay / 60
            
            # 如果延迟时间超过阈值且启用了会话保活
            if (self.enable_session_keepalive and
                delay_minutes >= self.keepalive_threshold):
                
                self.logger.info(f"启用会话保活的批次延迟: {delay_minutes:.1f}分钟")
                self.stats['keepalive_activations'] += 1
                
                # 使用会话保活器
                if self.session_keeper.keep_alive_during_delay(delay_minutes):
                    self.logger.info("✅ 批次延迟完成，会话保持有效")
                else:
                    self.logger.warning("⚠️ 批次延迟期间会话失效，尝试恢复...")
                    if self.session_recovery:
                        if self.session_recovery.handle_session_timeout("批次延迟"):
                            self.stats['session_recoveries'] += 1
                        else:
                            raise WebDriverException("会话恢复失败，无法继续批次处理")
            else:
                # 传统延迟方式
                self.logger.info(f"应用批次延迟: {delay_minutes:.1f}分钟")
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