"""
简历投递引擎

整合所有投递相关组件，提供完整的自动投递功能
"""

import logging
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional

from .models import (
    SubmissionResult, SubmissionReport, SubmissionStatus, 
    JobMatchRecord, SubmissionConfig, ButtonInfo
)
from .data_manager import SubmissionDataManager
from .button_recognition import ButtonRecognitionEngine
from .anti_crawler import AntiCrawlerSystem
from ..auth.browser_manager import BrowserManager
from ..auth.login_manager import LoginManager


class ResumeSubmissionEngine:
    """简历投递引擎 - 核心控制器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化投递引擎
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 初始化配置
        self.submission_config = SubmissionConfig.from_dict(
            config.get('submission_engine', {})
        )
        
        # 初始化组件
        self.data_manager = SubmissionDataManager(
            config.get('database_path', 'data/jobs.db')
        )
        
        # 浏览器和登录管理器（延迟初始化）
        self.browser_manager: Optional[BrowserManager] = None
        self.login_manager: Optional[LoginManager] = None
        self.button_engine: Optional[ButtonRecognitionEngine] = None
        self.anti_crawler: Optional[AntiCrawlerSystem] = None
        
        # 执行状态
        self.is_initialized = False
        self.current_report: Optional[SubmissionReport] = None
    
    async def initialize(self) -> bool:
        """
        初始化投递引擎
        
        Returns:
            是否初始化成功
        """
        try:
            self.logger.info("🚀 初始化投递引擎")
            
            # 1. 初始化浏览器管理器
            self.browser_manager = BrowserManager(self.config)
            
            # 2. 初始化登录管理器（共享同一个浏览器管理器）
            self.login_manager = LoginManager(self.config, self.browser_manager)
            
            # 3. 检查登录状态（这会创建浏览器实例）
            login_success = await self._ensure_login()
            if not login_success:
                self.logger.warning("登录检查失败，但继续执行")
            
            # 4. 获取已创建的driver实例
            driver = self.browser_manager.get_driver()
            if not driver:
                raise Exception("浏览器初始化失败")
            
            # 5. 初始化按钮识别引擎（使用已存在的driver）
            self.button_engine = ButtonRecognitionEngine(driver, self.config)
            
            # 6. 初始化反爬虫系统（使用已存在的driver和数据管理器）
            self.anti_crawler = AntiCrawlerSystem(driver, self.config, self.data_manager)
            
            self.is_initialized = True
            self.logger.info("✅ 投递引擎初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 投递引擎初始化失败: {e}")
            return False
    
    def initialize_sync(self) -> bool:
        """
        同步初始化投递引擎
        
        Returns:
            是否初始化成功
        """
        try:
            self.logger.info("🚀 同步初始化投递引擎")
            
            # 1. 初始化浏览器管理器
            self.browser_manager = BrowserManager(self.config)
            
            # 2. 初始化登录管理器（共享同一个浏览器管理器）
            self.login_manager = LoginManager(self.config, self.browser_manager)
            
            # 3. 检查登录状态（这会创建浏览器实例）
            login_success = self._ensure_login_sync()
            if not login_success:
                self.logger.warning("登录检查失败，但继续执行")
            
            # 4. 获取已创建的driver实例
            driver = self.browser_manager.get_driver()
            if not driver:
                raise Exception("浏览器初始化失败")
            
            # 5. 初始化按钮识别引擎（使用已存在的driver）
            self.button_engine = ButtonRecognitionEngine(driver, self.config)
            
            # 6. 初始化反爬虫系统（使用已存在的driver和数据管理器）
            self.anti_crawler = AntiCrawlerSystem(driver, self.config, self.data_manager)
            
            self.is_initialized = True
            self.logger.info("✅ 投递引擎同步初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 投递引擎同步初始化失败: {e}")
            return False

    async def _ensure_login(self) -> bool:
        """
        确保用户已登录
        
        Returns:
            是否登录成功
        """
        try:
            if not self.login_manager:
                return False
            
            # 检查当前登录状态
            status = self.login_manager.check_login_status()
            
            if status.get('is_logged_in', False):
                self.logger.info("✅ 用户已登录")
                return True
            
            # 尝试登录
            if self.submission_config.auto_login_enabled:
                self.logger.info("🔐 尝试自动登录")
                login_success = self.login_manager.start_login_session(
                    save_session=True,
                    test_keyword="test"
                )
                
                if login_success:
                    self.logger.info("✅ 自动登录成功")
                    return True
                else:
                    self.logger.warning("⚠️ 自动登录失败，需要手动登录")
            
            # 等待手动登录
            self.logger.info("⏳ 等待手动登录...")
            print("\n" + "="*60)
            print("🔐 请在浏览器中完成登录操作")
            print("="*60)
            print("程序将等待您完成登录，然后自动继续...")
            print("="*60 + "\n")
            
            # 等待登录完成
            timeout = self.submission_config.manual_login_timeout
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                status = self.login_manager.check_login_status()
                if status.get('is_logged_in', False):
                    self.logger.info("✅ 手动登录成功")
                    return True
                
                await asyncio.sleep(5)  # 每5秒检查一次
            
            self.logger.error("❌ 登录超时")
            return False
            
        except Exception as e:
            self.logger.error(f"登录检查失败: {e}")
            return False
    
    def _ensure_login_sync(self) -> bool:
        """
        确保用户已登录（同步版本）
        
        Returns:
            是否登录成功
        """
        try:
            if not self.login_manager:
                return False
            
            # 检查当前登录状态
            status = self.login_manager.check_login_status()
            
            if status.get('is_logged_in', False):
                self.logger.info("✅ 用户已登录")
                return True
            
            # 尝试登录
            if self.submission_config.auto_login_enabled:
                self.logger.info("🔐 尝试自动登录")
                login_success = self.login_manager.start_login_session(
                    save_session=True,
                    test_keyword="test"
                )
                
                if login_success:
                    self.logger.info("✅ 自动登录成功")
                    return True
                else:
                    self.logger.warning("⚠️ 自动登录失败，需要手动登录")
            
            # 等待手动登录（同步版本）
            self.logger.info("⏳ 等待手动登录...")
            print("\n" + "="*60)
            print("🔐 请在浏览器中完成登录操作")
            print("="*60)
            print("程序将等待您完成登录，然后自动继续...")
            print("="*60 + "\n")
            
            # 等待登录完成
            timeout = self.submission_config.manual_login_timeout
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                status = self.login_manager.check_login_status()
                if status.get('is_logged_in', False):
                    self.logger.info("✅ 手动登录成功")
                    return True
                
                time.sleep(5)  # 每5秒检查一次
            
            self.logger.error("❌ 登录超时")
            return False
            
        except Exception as e:
            self.logger.error(f"登录检查失败: {e}")
            return False

    def run_submission_batch_sync(self, batch_size: int = None) -> SubmissionReport:
        """
        执行批量投递（同步版本）
        
        Args:
            batch_size: 批次大小
            
        Returns:
            投递报告
        """
        if not self.is_initialized:
            self.initialize_sync()
        
        if batch_size is None:
            batch_size = self.submission_config.batch_size
        
        # 创建投递报告
        self.current_report = SubmissionReport()
        
        try:
            self.logger.info(f"🎯 开始批量投递（同步），批次大小: {batch_size}")
            
            # 1. 检查每日限制
            if not self.anti_crawler.check_daily_limit():
                self.logger.warning("已达到每日投递限制")
                self.current_report.finalize()
                return self.current_report
            
            # 2. 获取待投递的职位
            remaining_quota = self.anti_crawler.get_remaining_daily_quota()
            actual_batch_size = min(batch_size, remaining_quota)
            
            pending_jobs = self.data_manager.get_unprocessed_matches(
                limit=actual_batch_size
            )
            
            if not pending_jobs:
                self.logger.info("没有待投递的职位")
                self.current_report.finalize()
                return self.current_report
            
            self.logger.info(f"获取到 {len(pending_jobs)} 个待投递职位")
            
            # 3. 逐个处理职位
            for i, job_record in enumerate(pending_jobs):
                try:
                    # 检查是否需要批次延迟
                    self.anti_crawler.apply_batch_delay(10, i)
                    
                    # 投递单个职位（同步版本）
                    result = self.submit_single_job_sync(job_record)
                    self.current_report.add_result(result)
                    
                    # 更新数据库
                    self.data_manager.update_submission_result(result)
                    
                    # 如果成功，增加每日计数
                    if result.status == SubmissionStatus.SUCCESS:
                        self.anti_crawler.increment_daily_count()
                    
                    # 应用延迟
                    self.anti_crawler.apply_delay()
                    
                    # 风险检查和缓解
                    if i > 0 and i % 5 == 0:  # 每5个职位检查一次
                        risk_assessment = self.anti_crawler.check_detection_risk()
                        if risk_assessment['risk_level'] != 'low':
                            self.anti_crawler.apply_risk_mitigation(risk_assessment)
                    
                except Exception as e:
                    self.logger.error(f"处理职位 {job_record.job_id} 失败: {e}")
                    
                    # 创建失败结果
                    error_result = SubmissionResult(
                        job_id=job_record.job_id,
                        match_id=job_record.id,
                        job_title=job_record.job_title,
                        company=job_record.company,
                        job_url=job_record.job_url,
                        status=SubmissionStatus.FAILED,
                        message="处理异常",
                        error_details=str(e)
                    )
                    
                    self.current_report.add_result(error_result)
                    self.data_manager.update_submission_result(error_result)
                    continue
            
            # 4. 完成报告
            self.current_report.finalize()
            
            self.logger.info(f"✅ 批量投递完成: 成功 {self.current_report.successful_count}, "
                           f"失败 {self.current_report.failed_count}, "
                           f"跳过 {self.current_report.skipped_count}")
            
            return self.current_report
            
        except Exception as e:
            self.logger.error(f"批量投递失败: {e}")
            if self.current_report:
                self.current_report.finalize()
            return self.current_report or SubmissionReport()

    async def run_submission_batch(self, batch_size: int = None) -> SubmissionReport:
        """
        执行批量投递
        
        Args:
            batch_size: 批次大小
            
        Returns:
            投递报告
        """
        if not self.is_initialized:
            await self.initialize()
        
        if batch_size is None:
            batch_size = self.submission_config.batch_size
        
        # 创建投递报告
        self.current_report = SubmissionReport()
        
        try:
            self.logger.info(f"🎯 开始批量投递，批次大小: {batch_size}")
            
            # 1. 检查每日限制
            if not self.anti_crawler.check_daily_limit():
                self.logger.warning("已达到每日投递限制")
                self.current_report.finalize()
                return self.current_report
            
            # 2. 获取待投递的职位
            remaining_quota = self.anti_crawler.get_remaining_daily_quota()
            actual_batch_size = min(batch_size, remaining_quota)
            
            pending_jobs = self.data_manager.get_unprocessed_matches(
                limit=actual_batch_size
            )
            
            if not pending_jobs:
                self.logger.info("没有待投递的职位")
                self.current_report.finalize()
                return self.current_report
            
            self.logger.info(f"获取到 {len(pending_jobs)} 个待投递职位")
            
            # 3. 逐个处理职位
            for i, job_record in enumerate(pending_jobs):
                try:
                    # 检查是否需要批次延迟
                    self.anti_crawler.apply_batch_delay(10, i)
                    
                    # 投递单个职位
                    result = await self.submit_single_job(job_record)
                    self.current_report.add_result(result)
                    
                    # 更新数据库
                    self.data_manager.update_submission_result(result)
                    
                    # 如果成功，增加每日计数
                    if result.status == SubmissionStatus.SUCCESS:
                        self.anti_crawler.increment_daily_count()
                    
                    # 应用延迟
                    self.anti_crawler.apply_delay()
                    
                    # 风险检查和缓解
                    if i > 0 and i % 5 == 0:  # 每5个职位检查一次
                        risk_assessment = self.anti_crawler.check_detection_risk()
                        if risk_assessment['risk_level'] != 'low':
                            self.anti_crawler.apply_risk_mitigation(risk_assessment)
                    
                except Exception as e:
                    self.logger.error(f"处理职位 {job_record.job_id} 失败: {e}")
                    
                    # 创建失败结果
                    error_result = SubmissionResult(
                        job_id=job_record.job_id,
                        match_id=job_record.id,
                        job_title=job_record.job_title,
                        company=job_record.company,
                        job_url=job_record.job_url,
                        status=SubmissionStatus.FAILED,
                        message="处理异常",
                        error_details=str(e)
                    )
                    
                    self.current_report.add_result(error_result)
                    self.data_manager.update_submission_result(error_result)
                    continue
            
            # 4. 完成报告
            self.current_report.finalize()
            
            self.logger.info(f"✅ 批量投递完成: 成功 {self.current_report.successful_count}, "
                           f"失败 {self.current_report.failed_count}, "
                           f"跳过 {self.current_report.skipped_count}")
            
            return self.current_report
            
        except Exception as e:
            self.logger.error(f"批量投递失败: {e}")
            if self.current_report:
                self.current_report.finalize()
            return self.current_report or SubmissionReport()
    
    async def submit_single_job(self, job_record: JobMatchRecord) -> SubmissionResult:
        """
        投递单个职位
        
        Args:
            job_record: 职位匹配记录
            
        Returns:
            投递结果
        """
        start_time = time.time()
        
        # 创建基础结果对象
        result = SubmissionResult(
            job_id=job_record.job_id,
            match_id=job_record.id,
            job_title=job_record.job_title,
            company=job_record.company,
            job_url=job_record.job_url,
            status=SubmissionStatus.PENDING
        )
        
        try:
            self.logger.info(f"🎯 开始投递: {job_record.job_title} @ {job_record.company}")
            
            # 1. 检查是否已经投递过
            if self.data_manager.has_been_submitted(job_record.id):
                result.status = SubmissionStatus.ALREADY_APPLIED
                result.message = "已经投递过此职位"
                self.logger.info(f"⏭️ 跳过已投递职位: {job_record.job_title}")
                return result
            
            # 2. 导航到职位页面
            navigation_success = self.anti_crawler.safe_navigate_to_job(job_record.job_url)
            if not navigation_success:
                result.status = SubmissionStatus.FAILED
                result.message = "无法导航到职位页面"
                result.error_details = f"页面导航失败: {job_record.job_url}"
                self.logger.warning(f"❌ 导航失败: {job_record.job_title} - {job_record.job_url}")
                return result
            
            # 3. 模拟阅读职位页面
            self.anti_crawler.simulate_job_page_reading(
                min_time=3.0, max_time=5.0
            )
            
            # 4. 检查登录状态
            if not await self._check_login_status():
                result.status = SubmissionStatus.LOGIN_REQUIRED
                result.message = "需要登录"
                return result
            
            # 5. 查找申请按钮
            button_info = self.button_engine.find_application_button(job_record.job_url)
            if not button_info:
                result.status = SubmissionStatus.BUTTON_NOT_FOUND
                result.message = "未找到申请按钮"
                return result
            
            result.button_info = button_info
            
            # 6. 模拟申请前行为
            self.anti_crawler.simulate_pre_application_behavior()
            
            # 7. 点击申请按钮
            click_success = self.button_engine.click_button_safely(button_info)
            if not click_success:
                result.status = SubmissionStatus.FAILED
                result.message = "申请按钮点击失败"
                return result
            
            # 8. 处理申请表单（如果有）
            form_handled = self.button_engine.handle_application_form()
            
            # 9. 检查申请是否成功
            application_success = self.button_engine.check_application_success()
            
            if application_success:
                result.status = SubmissionStatus.SUCCESS
                result.message = "投递成功"
                self.logger.info(f"✅ 投递成功: {job_record.job_title}")
            else:
                result.status = SubmissionStatus.FAILED
                result.message = "投递可能失败，未检测到成功指示器"
                self.logger.warning(f"⚠️ 投递状态不明: {job_record.job_title}")
            
            # 10. 模拟申请后行为
            self.anti_crawler.simulate_post_application_behavior()
            
        except Exception as e:
            self.logger.error(f"❌ 投递失败 {job_record.job_title}: {e}")
            result.status = SubmissionStatus.FAILED
            result.message = "投递过程异常"
            result.error_details = str(e)
        
        finally:
            # 计算执行时间
            result.execution_time = time.time() - start_time
            result.attempts = self.data_manager.get_submission_attempts(job_record.id) + 1
        
        return result
    
    def submit_single_job_sync(self, job_record: JobMatchRecord) -> SubmissionResult:
        """
        投递单个职位（同步版本）
        
        Args:
            job_record: 职位匹配记录
            
        Returns:
            投递结果
        """
        start_time = time.time()
        
        # 创建基础结果对象
        result = SubmissionResult(
            job_id=job_record.job_id,
            match_id=job_record.id,
            job_title=job_record.job_title,
            company=job_record.company,
            job_url=job_record.job_url,
            status=SubmissionStatus.PENDING
        )
        
        try:
            self.logger.info(f"🎯 开始投递: {job_record.job_title} @ {job_record.company}")
            
            # 1. 检查是否已经投递过
            if self.data_manager.has_been_submitted(job_record.id):
                result.status = SubmissionStatus.ALREADY_APPLIED
                result.message = "已经投递过此职位"
                self.logger.info(f"⏭️ 跳过已投递职位: {job_record.job_title}")
                return result
            
            # 2. 导航到职位页面
            navigation_success = self.anti_crawler.safe_navigate_to_job(job_record.job_url)
            if not navigation_success:
                result.status = SubmissionStatus.FAILED
                result.message = "无法导航到职位页面"
                result.error_details = f"页面导航失败: {job_record.job_url}"
                self.logger.warning(f"❌ 导航失败: {job_record.job_title} - {job_record.job_url}")
                return result
            
            # 3. 模拟阅读职位页面
            self.anti_crawler.simulate_job_page_reading(
                min_time=2.0, max_time=5.0
            )
            
            # 4. 检查登录状态（同步版本）
            if not self._check_login_status_sync():
                result.status = SubmissionStatus.LOGIN_REQUIRED
                result.message = "需要登录"
                return result
            
            # 5. 查找申请按钮
            button_info = self.button_engine.find_application_button(job_record.job_url)
            if not button_info:
                result.status = SubmissionStatus.BUTTON_NOT_FOUND
                result.message = "未找到申请按钮"
                return result
            
            result.button_info = button_info
            
            # 6. 模拟申请前行为
            self.anti_crawler.simulate_pre_application_behavior()
            
            # 7. 点击申请按钮
            click_success = self.button_engine.click_button_safely(button_info)
            if not click_success:
                result.status = SubmissionStatus.FAILED
                result.message = "申请按钮点击失败"
                return result
            
            # 8. 处理申请表单（如果有）
            form_handled = self.button_engine.handle_application_form()
            
            # 9. 检查申请是否成功
            application_success = self.button_engine.check_application_success()
            
            if application_success:
                result.status = SubmissionStatus.SUCCESS
                result.message = "投递成功"
                self.logger.info(f"✅ 投递成功: {job_record.job_title}")
            else:
                result.status = SubmissionStatus.FAILED
                result.message = "投递可能失败，未检测到成功指示器"
                self.logger.warning(f"⚠️ 投递状态不明: {job_record.job_title}")
            
            # 10. 模拟申请后行为
            self.anti_crawler.simulate_post_application_behavior()
            
        except Exception as e:
            self.logger.error(f"❌ 投递失败 {job_record.job_title}: {e}")
            result.status = SubmissionStatus.FAILED
            result.message = "投递过程异常"
            result.error_details = str(e)
        
        finally:
            # 计算执行时间
            result.execution_time = time.time() - start_time
            result.attempts = self.data_manager.get_submission_attempts(job_record.id) + 1
        
        return result

    async def _check_login_status(self) -> bool:
        """
        检查登录状态
        
        Returns:
            是否已登录
        """
        try:
            if not self.login_manager:
                self.logger.warning("登录管理器未初始化")
                return False
            
            status = self.login_manager.check_login_status()
            is_logged_in = status.get('is_logged_in', False)
            
            if not is_logged_in:
                self.logger.warning("检测到未登录状态，尝试重新登录")
                # 尝试重新登录
                try:
                    login_success = self.login_manager.start_login_session(
                        save_session=True,
                        test_keyword="test"
                    )
                    if login_success:
                        self.logger.info("重新登录成功")
                        return True
                    else:
                        self.logger.warning("重新登录失败")
                        return False
                except Exception as login_e:
                    self.logger.error(f"重新登录异常: {login_e}")
                    return False
            
            return is_logged_in
            
        except Exception as e:
            self.logger.error(f"检查登录状态失败: {e}")
            return False
    
    def _check_login_status_sync(self) -> bool:
        """
        检查登录状态（同步版本）
        
        Returns:
            是否已登录
        """
        try:
            if not self.login_manager:
                self.logger.warning("登录管理器未初始化")
                return False
            
            status = self.login_manager.check_login_status()
            is_logged_in = status.get('is_logged_in', False)
            
            if not is_logged_in:
                self.logger.warning("检测到未登录状态，尝试重新登录")
                # 尝试重新登录
                try:
                    login_success = self.login_manager.start_login_session(
                        save_session=True,
                        test_keyword="test"
                    )
                    if login_success:
                        self.logger.info("重新登录成功")
                        return True
                    else:
                        self.logger.warning("重新登录失败")
                        return False
                except Exception as login_e:
                    self.logger.error(f"重新登录异常: {login_e}")
                    return False
            
            return is_logged_in
            
        except Exception as e:
            self.logger.error(f"检查登录状态失败: {e}")
            return False

    def get_submission_statistics(self) -> Dict[str, Any]:
        """
        获取投递统计信息
        
        Returns:
            统计信息字典
        """
        try:
            # 数据库统计
            db_stats = self.data_manager.get_submission_statistics()
            
            # 反爬虫统计
            anti_crawler_stats = self.anti_crawler.get_stats() if self.anti_crawler else {}
            
            # 当前报告统计
            current_report_stats = {}
            if self.current_report:
                current_report_stats = self.current_report.get_summary()
            
            return {
                'database_stats': db_stats,
                'anti_crawler_stats': anti_crawler_stats,
                'current_session': current_report_stats,
                'engine_status': {
                    'initialized': self.is_initialized,
                    'browser_alive': self.browser_manager.is_driver_alive() if self.browser_manager else False
                }
            }
            
        except Exception as e:
            self.logger.error(f"获取统计信息失败: {e}")
            return {}
    
    def get_failed_submissions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取失败的投递记录
        
        Args:
            limit: 限制数量
            
        Returns:
            失败记录列表
        """
        return self.data_manager.get_failed_submissions(limit)
    
    def reset_failed_submissions(self, match_ids: Optional[List[int]] = None) -> int:
        """
        重置失败的投递记录
        
        Args:
            match_ids: 要重置的匹配记录ID列表
            
        Returns:
            重置的记录数
        """
        return self.data_manager.reset_failed_submissions(match_ids)
    
    async def cleanup(self):
        """清理资源"""
        try:
            self.logger.info("🧹 清理投递引擎资源")
            
            if self.login_manager:
                self.login_manager.close()
            
            if self.browser_manager:
                self.browser_manager.quit_driver()
            
            self.is_initialized = False
            self.logger.info("✅ 资源清理完成")
            
        except Exception as e:
            self.logger.error(f"资源清理失败: {e}")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        asyncio.run(self.cleanup())