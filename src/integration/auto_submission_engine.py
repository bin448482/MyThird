"""
自动投递引擎 (AutoSubmissionEngine)
执行智能投递操作
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)

class SubmissionStatus(Enum):
    """投递状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ALREADY_APPLIED = "already_applied"

class SubmissionMethod(Enum):
    """投递方式"""
    DIRECT_APPLY = "direct_apply"
    EMAIL_SUBMIT = "email_submit"
    PLATFORM_APPLY = "platform_apply"
    MANUAL_REVIEW = "manual_review"

@dataclass
class SubmissionTask:
    """投递任务"""
    task_id: str
    job_id: str
    job_title: str
    company: str
    job_url: str
    submission_priority: str
    final_score: float
    decision_reasoning: List[str]
    estimated_success_rate: float
    status: SubmissionStatus = SubmissionStatus.PENDING
    submission_method: Optional[SubmissionMethod] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SubmissionResult:
    """投递结果"""
    total_attempts: int
    successful_submissions: int
    failed_submissions: int
    skipped_submissions: int
    already_applied_count: int
    submission_details: List[Dict[str, Any]]
    execution_time: float
    success_rate: float
    daily_submission_count: int
    remaining_daily_quota: int
    success: bool = True
    error_message: Optional[str] = None

class AutoSubmissionEngine:
    """自动投递引擎 - 执行智能投递操作"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.submission_config = config.get('auto_submission', {})
        
        # 投递配置
        self.max_submissions_per_day = self.submission_config.get('max_submissions_per_day', 50)
        self.submission_delay = self.submission_config.get('submission_delay', 5)
        self.max_concurrent_submissions = self.submission_config.get('max_concurrent_submissions', 3)
        self.enable_smart_delay = self.submission_config.get('enable_smart_delay', True)
        self.dry_run_mode = self.submission_config.get('dry_run_mode', False)
        
        # 浏览器和会话管理
        self.browser_manager = None
        self.session_manager = None
        self.login_manager = None
        
        # 投递统计
        self.submission_stats = {
            'total_attempts': 0,
            'successful_submissions': 0,
            'failed_submissions': 0,
            'skipped_submissions': 0,
            'already_applied_count': 0,
            'daily_submission_count': 0,
            'last_reset_date': datetime.now().date(),
            'average_submission_time': 0,
            'success_rate_by_priority': {},
            'company_submission_counts': {},
            'platform_success_rates': {}
        }
        
        # 投递历史
        self.submission_history = []
        self.applied_jobs = set()  # 已申请的职位ID
        
        # 并发控制
        self.submission_semaphore = asyncio.Semaphore(self.max_concurrent_submissions)
        
        # 智能延迟参数
        self.base_delay = self.submission_delay
        self.delay_variance = 0.3  # 延迟变化范围
        self.adaptive_delay = self.base_delay
    
    async def initialize(self):
        """初始化投递引擎"""
        try:
            # 导入浏览器管理模块
            from ..auth.browser_manager import BrowserManager
            from ..auth.session_manager import SessionManager
            from ..auth.login_manager import LoginManager
            
            # 初始化管理器
            self.browser_manager = BrowserManager(self.config)
            self.session_manager = SessionManager(self.config)
            self.login_manager = LoginManager(self.config)
            
            if not self.dry_run_mode:
                # 启动浏览器
                await self.browser_manager.start_browser()
                logger.info("浏览器已启动")
                
                # 等待用户登录
                await self._wait_for_user_login()
                logger.info("用户登录完成")
            else:
                logger.info("运行在干运行模式，不会实际投递")
            
            # 重置每日计数器
            self._reset_daily_counter_if_needed()
            
            logger.info("自动投递引擎初始化完成")
            
        except Exception as e:
            logger.error(f"投递引擎初始化失败: {e}")
            raise
    
    async def submit_applications(self, decision_result: Dict, submission_config: Dict[str, Any] = None) -> SubmissionResult:
        """批量提交简历申请"""
        start_time = datetime.now()
        
        try:
            # 更新配置
            if submission_config:
                self._update_submission_config(submission_config)
            
            # 解析决策结果
            decisions = decision_result.get('decisions', [])
            submission_candidates = [d for d in decisions if d.get('should_submit', False)]
            
            if not submission_candidates:
                return SubmissionResult(
                    total_attempts=0,
                    successful_submissions=0,
                    failed_submissions=0,
                    skipped_submissions=0,
                    already_applied_count=0,
                    submission_details=[],
                    execution_time=0,
                    success_rate=0,
                    daily_submission_count=self.submission_stats['daily_submission_count'],
                    remaining_daily_quota=self._get_remaining_daily_quota(),
                    success=True
                )
            
            logger.info(f"开始处理 {len(submission_candidates)} 个投递候选")
            
            # 创建投递任务
            submission_tasks = self._create_submission_tasks(submission_candidates)
            
            # 应用每日限制
            filtered_tasks = self._apply_daily_limits(submission_tasks)
            
            # 按优先级排序
            sorted_tasks = self._sort_tasks_by_priority(filtered_tasks)
            
            # 执行投递
            submission_details = await self._execute_submissions(sorted_tasks)
            
            # 计算结果
            execution_time = (datetime.now() - start_time).total_seconds()
            result = self._calculate_submission_result(submission_details, execution_time)
            
            # 更新统计信息
            self._update_submission_stats(submission_details)
            
            logger.info(f"投递完成: 成功 {result.successful_submissions}, 失败 {result.failed_submissions}, 跳过 {result.skipped_submissions}")
            
            return result
            
        except Exception as e:
            logger.error(f"批量投递失败: {e}")
            execution_time = (datetime.now() - start_time).total_seconds()
            return SubmissionResult(
                total_attempts=0,
                successful_submissions=0,
                failed_submissions=0,
                skipped_submissions=0,
                already_applied_count=0,
                submission_details=[],
                execution_time=execution_time,
                success_rate=0,
                daily_submission_count=self.submission_stats['daily_submission_count'],
                remaining_daily_quota=self._get_remaining_daily_quota(),
                success=False,
                error_message=str(e)
            )
    
    async def _execute_submissions(self, tasks: List[SubmissionTask]) -> List[Dict[str, Any]]:
        """执行投递任务"""
        submission_details = []
        
        # 并发执行投递任务
        semaphore_tasks = []
        for task in tasks:
            semaphore_task = self._submit_single_application_with_semaphore(task)
            semaphore_tasks.append(semaphore_task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*semaphore_tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"投递任务异常: {result}")
                submission_details.append({
                    'task_id': tasks[i].task_id,
                    'job_id': tasks[i].job_id,
                    'status': SubmissionStatus.FAILED.value,
                    'error_message': str(result)
                })
            else:
                submission_details.append(result)
        
        return submission_details
    
    async def _submit_single_application_with_semaphore(self, task: SubmissionTask) -> Dict[str, Any]:
        """带信号量的单个申请提交"""
        async with self.submission_semaphore:
            return await self._submit_single_application(task)
    
    async def _submit_single_application(self, task: SubmissionTask) -> Dict[str, Any]:
        """提交单个申请"""
        task.started_at = datetime.now()
        task.status = SubmissionStatus.IN_PROGRESS
        
        logger.info(f"开始投递: {task.job_title} @ {task.company}")
        
        try:
            # 检查是否已经申请过
            if await self._check_already_applied(task):
                task.status = SubmissionStatus.ALREADY_APPLIED
                task.completed_at = datetime.now()
                return self._create_submission_detail(task, "已经申请过此职位")
            
            # 干运行模式
            if self.dry_run_mode:
                await asyncio.sleep(1)  # 模拟处理时间
                task.status = SubmissionStatus.SUCCESS
                task.completed_at = datetime.now()
                return self._create_submission_detail(task, "干运行模式 - 模拟成功")
            
            # 导航到职位页面
            success = await self._navigate_to_job_page(task)
            if not success:
                task.status = SubmissionStatus.FAILED
                task.error_message = "无法导航到职位页面"
                task.completed_at = datetime.now()
                return self._create_submission_detail(task, task.error_message)
            
            # 检测投递方式
            submission_method = await self._detect_submission_method(task)
            task.submission_method = submission_method
            
            # 执行投递操作
            success = await self._perform_submission(task)
            
            if success:
                task.status = SubmissionStatus.SUCCESS
                self.applied_jobs.add(task.job_id)
                self.submission_stats['daily_submission_count'] += 1
                
                # 智能延迟
                if self.enable_smart_delay:
                    delay = self._calculate_smart_delay()
                    await asyncio.sleep(delay)
                else:
                    await asyncio.sleep(self.submission_delay)
                
                task.completed_at = datetime.now()
                return self._create_submission_detail(task, "投递成功")
            else:
                task.status = SubmissionStatus.FAILED
                task.error_message = "投递操作失败"
                task.completed_at = datetime.now()
                return self._create_submission_detail(task, task.error_message)
                
        except Exception as e:
            logger.error(f"投递失败 {task.job_title}: {e}")
            task.status = SubmissionStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now()
            return self._create_submission_detail(task, str(e))
    
    async def _navigate_to_job_page(self, task: SubmissionTask) -> bool:
        """导航到职位页面"""
        try:
            if not self.browser_manager:
                return False
            
            await self.browser_manager.navigate_to_url(task.job_url)
            
            # 等待页面加载
            await asyncio.sleep(2)
            
            # 检查页面是否正确加载
            page_title = await self.browser_manager.get_page_title()
            if not page_title or "404" in page_title or "错误" in page_title:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"导航到职位页面失败: {e}")
            return False
    
    async def _detect_submission_method(self, task: SubmissionTask) -> SubmissionMethod:
        """检测投递方式"""
        try:
            if not self.browser_manager:
                return SubmissionMethod.MANUAL_REVIEW
            
            # 检查页面元素来判断投递方式
            page_content = await self.browser_manager.get_page_content()
            
            if "立即申请" in page_content or "投递简历" in page_content:
                return SubmissionMethod.DIRECT_APPLY
            elif "发送邮件" in page_content or "邮箱" in page_content:
                return SubmissionMethod.EMAIL_SUBMIT
            elif "平台申请" in page_content:
                return SubmissionMethod.PLATFORM_APPLY
            else:
                return SubmissionMethod.MANUAL_REVIEW
                
        except Exception as e:
            logger.error(f"检测投递方式失败: {e}")
            return SubmissionMethod.MANUAL_REVIEW
    
    async def _perform_submission(self, task: SubmissionTask) -> bool:
        """执行投递操作"""
        try:
            if task.submission_method == SubmissionMethod.DIRECT_APPLY:
                return await self._direct_apply(task)
            elif task.submission_method == SubmissionMethod.EMAIL_SUBMIT:
                return await self._email_submit(task)
            elif task.submission_method == SubmissionMethod.PLATFORM_APPLY:
                return await self._platform_apply(task)
            else:
                # 手动审核模式，标记为跳过
                task.status = SubmissionStatus.SKIPPED
                return False
                
        except Exception as e:
            logger.error(f"执行投递操作失败: {e}")
            return False
    
    async def _direct_apply(self, task: SubmissionTask) -> bool:
        """直接申请"""
        try:
            if not self.browser_manager:
                return False
            
            # 查找申请按钮
            apply_button_selectors = [
                "button:contains('立即申请')",
                "button:contains('投递简历')",
                "a:contains('申请职位')",
                ".apply-btn",
                "#apply-button"
            ]
            
            for selector in apply_button_selectors:
                if await self.browser_manager.click_element(selector):
                    # 等待申请流程
                    await asyncio.sleep(3)
                    
                    # 检查是否需要填写额外信息
                    if await self._handle_application_form():
                        return True
                    
                    # 检查申请是否成功
                    if await self._verify_application_success():
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"直接申请失败: {e}")
            return False
    
    async def _email_submit(self, task: SubmissionTask) -> bool:
        """邮件投递"""
        try:
            # 这里可以集成邮件发送功能
            # 暂时返回False，表示需要手动处理
            logger.info(f"邮件投递模式: {task.job_title}")
            return False
            
        except Exception as e:
            logger.error(f"邮件投递失败: {e}")
            return False
    
    async def _platform_apply(self, task: SubmissionTask) -> bool:
        """平台申请"""
        try:
            # 根据不同平台实现不同的申请逻辑
            return await self._direct_apply(task)  # 暂时使用直接申请逻辑
            
        except Exception as e:
            logger.error(f"平台申请失败: {e}")
            return False
    
    async def _handle_application_form(self) -> bool:
        """处理申请表单"""
        try:
            if not self.browser_manager:
                return False
            
            # 检查是否有表单需要填写
            form_elements = await self.browser_manager.find_elements("form")
            if not form_elements:
                return True
            
            # 填写常见的表单字段
            await self._fill_common_form_fields()
            
            # 提交表单
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:contains('提交')",
                "button:contains('确认申请')"
            ]
            
            for selector in submit_selectors:
                if await self.browser_manager.click_element(selector):
                    await asyncio.sleep(2)
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"处理申请表单失败: {e}")
            return False
    
    async def _fill_common_form_fields(self):
        """填写常见表单字段"""
        try:
            # 这里可以根据简历信息自动填写表单
            # 暂时跳过，实际使用时需要根据具体表单结构实现
            pass
            
        except Exception as e:
            logger.error(f"填写表单字段失败: {e}")
    
    async def _verify_application_success(self) -> bool:
        """验证申请是否成功"""
        try:
            if not self.browser_manager:
                return False
            
            # 等待页面响应
            await asyncio.sleep(3)
            
            # 检查成功指示器
            success_indicators = [
                "申请成功",
                "投递成功",
                "简历已投递",
                "申请已提交",
                "success",
                "submitted"
            ]
            
            page_content = await self.browser_manager.get_page_content()
            for indicator in success_indicators:
                if indicator in page_content:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"验证申请成功失败: {e}")
            return False
    
    async def _check_already_applied(self, task: SubmissionTask) -> bool:
        """检查是否已经申请过"""
        # 检查本地记录
        if task.job_id in self.applied_jobs:
            return True
        
        # 检查页面是否显示已申请
        try:
            if not self.browser_manager:
                return False
            
            page_content = await self.browser_manager.get_page_content()
            already_applied_indicators = [
                "已申请",
                "已投递",
                "已提交申请",
                "applied",
                "submitted"
            ]
            
            for indicator in already_applied_indicators:
                if indicator in page_content:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"检查已申请状态失败: {e}")
            return False
    
    async def _wait_for_user_login(self):
        """等待用户登录"""
        if not self.login_manager:
            logger.warning("登录管理器未初始化")
            return
        
        # 这里可以实现自动登录或等待用户手动登录
        # 暂时等待一段时间让用户手动登录
        logger.info("请在浏览器中完成登录...")
        await asyncio.sleep(30)  # 等待30秒让用户登录
    
    def _create_submission_tasks(self, candidates: List[Dict]) -> List[SubmissionTask]:
        """创建投递任务"""
        tasks = []
        
        for i, candidate in enumerate(candidates):
            task = SubmissionTask(
                task_id=f"submission_{int(datetime.now().timestamp())}_{i}",
                job_id=candidate.get('job_id', ''),
                job_title=candidate.get('job_title', ''),
                company=candidate.get('company', ''),
                job_url=candidate.get('job_url', ''),
                submission_priority=candidate.get('submission_priority', 'medium'),
                final_score=candidate.get('final_score', 0),
                decision_reasoning=candidate.get('decision_reasoning', []),
                estimated_success_rate=candidate.get('estimated_success_rate', 0.5)
            )
            tasks.append(task)
        
        return tasks
    
    def _apply_daily_limits(self, tasks: List[SubmissionTask]) -> List[SubmissionTask]:
        """应用每日限制"""
        remaining_quota = self._get_remaining_daily_quota()
        
        if len(tasks) <= remaining_quota:
            return tasks
        
        # 按优先级和分数排序，保留前N个
        sorted_tasks = sorted(
            tasks,
            key=lambda x: (self._get_priority_value(x.submission_priority), x.final_score),
            reverse=True
        )
        
        selected_tasks = sorted_tasks[:remaining_quota]
        skipped_count = len(tasks) - len(selected_tasks)
        
        if skipped_count > 0:
            logger.info(f"由于每日限制，跳过 {skipped_count} 个投递任务")
        
        return selected_tasks
    
    def _sort_tasks_by_priority(self, tasks: List[SubmissionTask]) -> List[SubmissionTask]:
        """按优先级排序任务"""
        return sorted(
            tasks,
            key=lambda x: (self._get_priority_value(x.submission_priority), x.final_score),
            reverse=True
        )
    
    def _get_priority_value(self, priority: str) -> int:
        """获取优先级数值"""
        priority_values = {
            'urgent': 4,
            'high': 3,
            'medium': 2,
            'low': 1
        }
        return priority_values.get(priority.lower(), 1)
    
    def _calculate_smart_delay(self) -> float:
        """计算智能延迟"""
        # 基础延迟加上随机变化
        variance = random.uniform(-self.delay_variance, self.delay_variance)
        delay = self.adaptive_delay * (1 + variance)
        
        # 根据成功率调整延迟
        recent_success_rate = self._get_recent_success_rate()
        if recent_success_rate < 0.5:
            # 成功率低，增加延迟
            delay *= 1.5
        elif recent_success_rate > 0.8:
            # 成功率高，可以稍微减少延迟
            delay *= 0.8
        
        return max(1.0, delay)  # 最小1秒延迟
    
    def _get_recent_success_rate(self) -> float:
        """获取最近的成功率"""
        if len(self.submission_history) < 5:
            return 0.5
        
        recent_submissions = self.submission_history[-10:]  # 最近10次
        successful = sum(1 for s in recent_submissions if s.get('status') == SubmissionStatus.SUCCESS.value)
        return successful / len(recent_submissions)
    
    def _create_submission_detail(self, task: SubmissionTask, message: str) -> Dict[str, Any]:
        """创建投递详情"""
        execution_time = 0
        if task.started_at and task.completed_at:
            execution_time = (task.completed_at - task.started_at).total_seconds()
        
        return {
            'task_id': task.task_id,
            'job_id': task.job_id,
            'job_title': task.job_title,
            'company': task.company,
            'status': task.status.value,
            'submission_method': task.submission_method.value if task.submission_method else None,
            'submission_priority': task.submission_priority,
            'final_score': task.final_score,
            'estimated_success_rate': task.estimated_success_rate,
            'execution_time': execution_time,
            'message': message,
            'error_message': task.error_message,
            'retry_count': task.retry_count,
            'submitted_at': task.completed_at.isoformat() if task.completed_at else None
        }
    
    def _calculate_submission_result(self, submission_details: List[Dict], execution_time: float) -> SubmissionResult:
        """计算投递结果"""
        total_attempts = len(submission_details)
        successful_submissions = len([d for d in submission_details if d['status'] == SubmissionStatus.SUCCESS.value])
        failed_submissions = len([d for d in submission_details if d['status'] == SubmissionStatus.FAILED.value])
        skipped_submissions = len([d for d in submission_details if d['status'] == SubmissionStatus.SKIPPED.value])
        already_applied_count = len([d for d in submission_details if d['status'] == SubmissionStatus.ALREADY_APPLIED.value])
        
        success_rate = successful_submissions / total_attempts if total_attempts > 0 else 0
        
        return SubmissionResult(
            total_attempts=total_attempts,
            successful_submissions=successful_submissions,
            failed_submissions=failed_submissions,
            skipped_submissions=skipped_submissions,
            already_applied_count=already_applied_count,
            submission_details=submission_details,
            execution_time=execution_time,
            success_rate=success_rate,
            daily_submission_count=self.submission_stats['daily_submission_count'],
            remaining_daily_quota=self._get_remaining_daily_quota(),
            success=True
        )
    
    def _update_submission_stats(self, submission_details: List[Dict]):
        """更新投递统计"""
        for detail in submission_details:
            status = detail['status']
            priority = detail['submission_priority']
            company = detail['company']
            
            # 更新总体统计
            self.submission_stats['total_attempts'] += 1
            
            if status == SubmissionStatus.SUCCESS.value:
                self.submission_stats['successful_submissions'] += 1
            elif status == SubmissionStatus.FAILED.value:
                self.submission_stats['failed_submissions'] += 1
            elif status == SubmissionStatus.SKIPPED.value:
                self.submission_stats['skipped_submissions'] += 1
            elif status == SubmissionStatus.ALREADY_APPLIED.value:
                self.submission_stats['already_applied_count'] += 1
            
            # 更新优先级成功率统计
            if priority not in self.submission_stats['success_rate_by_priority']:
                self.submission_stats['success_rate_by_priority'][priority] = {'total': 0, 'success': 0}
            
            self.submission_stats['success_rate_by_priority'][priority]['total'] += 1
            if status == SubmissionStatus.SUCCESS.value:
                self.submission_stats['success_rate_by_priority'][priority]['success'] += 1
            
            # 更新公司投递统计
            if company not in self.submission_stats['company_submission_counts']:
                self.submission_stats['company_submission_counts'][company] = 0
            self.submission_stats['company_submission_counts'][company] += 1
            
            # 添加到历史记录
            self.submission_history.append(detail)
        
        # 保留最近1000条记录
        if len(self.submission_history) > 1000:
            self.submission_history = self.submission_history[-1000:]
        
        # 计算平均投递时间
        execution_times = [d.get('execution_time', 0) for d in submission_details if d.get('execution_time')]
        if execution_times:
            avg_time = sum(execution_times) / len(execution_times)
            self.submission_stats['average_submission_time'] = avg_time
    
    def _reset_daily_counter_if_needed(self):
        """如果需要，重置每日计数器"""
        current_date = datetime.now().date()
        if current_date != self.submission_stats['last_reset_date']:
            self.submission_stats['daily_submission_count'] = 0
            self.submission_stats['last_reset_date'] = current_date
            logger.info("每日投递计数器已重置")
    
    def _get_remaining_daily_quota(self) -> int:
        """获取剩余每日配额"""
        return max(0, self.max_submissions_per_day - self.submission_stats['daily_submission_count'])
    
    def _update_submission_config(self, new_config: Dict[str, Any]):
        """更新投递配置"""
        for key, value in new_config.items():
            if hasattr(self, key):
                setattr(self, key, value)
                logger.info(f"更新投递配置: {key} = {value}")
    
    def get_submission_stats(self) -> Dict[str, Any]:
        """获取投递统计信息"""
        # 计算成功率
        total_attempts = self.submission_stats['total_attempts']
        successful = self.submission_stats['successful_submissions']
        overall_success_rate = successful / total_attempts if total_attempts > 0 else 0
        
        # 计算优先级成功率
        priority_success_rates = {}
        for priority, stats in self.submission_stats['success_rate_by_priority'].items():
            rate = stats['success'] / stats['total'] if stats['total'] > 0 else 0
            priority_success_rates[priority] = rate
        
        return {
            'overall_stats': {
                'total_attempts': self.submission_stats['total_attempts'],
                'successful_submissions': self.submission_stats['successful_submissions'],
                'failed_submissions': self.submission_stats['failed_submissions'],
                'skipped_submissions': self.submission_stats['skipped_submissions'],
                'already_applied_count': self.submission_stats['already_applied_count'],
                'overall_success_rate': overall_success_rate,
                'daily_submission_count': self.submission_stats['daily_submission_count'],
                'remaining_daily_quota': self._get_remaining_daily_quota(),
                'average_submission_time': self.submission_stats['average_submission_time']
            },
            'priority_success_rates': priority_success_rates,
            'company_submission_counts': self.submission_stats['company_submission_counts'],
            'recent_submissions': self.submission_history[-10:] if self.submission_history else [],
            'config': {
                'max_submissions_per_day': self.max_submissions_per_day,
                'submission_delay': self.submission_delay,
                'max_concurrent_submissions': self.max_concurrent_submissions,
                'dry_run_mode': self.dry_run_mode
            }
        }
    
    async def cleanup(self):
        """清理资源"""
        try:
            if self.browser_manager and not self.dry_run_mode:
                await self.browser_manager.close_browser()
                logger.info("浏览器已关闭")
        except Exception as e:
            logger.error(f"清理资源失败: {e}")