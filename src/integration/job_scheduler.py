"""
作业调度器 (JobScheduler)
管理任务队列和执行顺序，控制并发执行
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import json

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"

class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5

@dataclass
class PipelineTask:
    """流水线任务"""
    task_id: str
    task_type: str
    data: Dict[str, Any]
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[int] = None
    dependencies: List[str] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TaskBatch:
    """任务批次"""
    batch_id: str
    tasks: List[PipelineTask]
    batch_priority: TaskPriority = TaskPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.now)
    max_concurrent: int = 5
    timeout: Optional[int] = None

class TaskExecutionError(Exception):
    """任务执行错误"""
    pass

class JobScheduler:
    """作业调度器 - 管理任务队列和执行顺序"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.scheduler_config = config.get('job_scheduler', {})
        
        # 队列配置
        self.queue_size = self.scheduler_config.get('queue_size', 1000)
        self.max_concurrent = self.scheduler_config.get('max_concurrent_tasks', 10)
        self.batch_size = self.scheduler_config.get('batch_size', 50)
        self.priority_levels = self.scheduler_config.get('priority_levels', 5)
        
        # 任务队列 - 按优先级分组
        self.task_queues = {
            priority: asyncio.Queue(maxsize=self.queue_size)
            for priority in TaskPriority
        }
        
        # 任务管理
        self.running_tasks = {}
        self.completed_tasks = {}
        self.failed_tasks = {}
        self.task_history = []
        
        # 并发控制
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        self.worker_pool = []
        self.is_running = False
        
        # 统计信息
        self.stats = {
            'total_tasks_scheduled': 0,
            'total_tasks_completed': 0,
            'total_tasks_failed': 0,
            'total_execution_time': 0,
            'average_task_time': 0,
            'queue_sizes': defaultdict(int),
            'worker_utilization': 0
        }
        
        # 任务执行器映射
        self.task_executors = {}
    
    async def start(self):
        """启动调度器"""
        if self.is_running:
            logger.warning("调度器已经在运行")
            return
        
        self.is_running = True
        logger.info(f"启动作业调度器，最大并发数: {self.max_concurrent}")
        
        # 启动工作线程
        for i in range(self.max_concurrent):
            worker = asyncio.create_task(self._worker(f"worker_{i}"))
            self.worker_pool.append(worker)
        
        # 启动监控任务
        monitor_task = asyncio.create_task(self._monitor_tasks())
        self.worker_pool.append(monitor_task)
    
    async def stop(self):
        """停止调度器"""
        if not self.is_running:
            return
        
        logger.info("停止作业调度器")
        self.is_running = False
        
        # 取消所有工作线程
        for worker in self.worker_pool:
            worker.cancel()
        
        # 等待所有任务完成
        await asyncio.gather(*self.worker_pool, return_exceptions=True)
        self.worker_pool.clear()
    
    async def schedule_task(self, task: PipelineTask) -> str:
        """调度单个任务"""
        if not self.is_running:
            await self.start()
        
        # 验证任务
        if not self._validate_task(task):
            raise ValueError(f"Invalid task: {task.task_id}")
        
        # 检查依赖
        if not await self._check_dependencies(task):
            raise ValueError(f"Task dependencies not met: {task.task_id}")
        
        # 添加到相应优先级队列
        await self.task_queues[task.priority].put(task)
        
        # 更新统计
        self.stats['total_tasks_scheduled'] += 1
        self.stats['queue_sizes'][task.priority.name] += 1
        
        logger.info(f"任务已调度: {task.task_id}, 优先级: {task.priority.name}")
        return task.task_id
    
    async def schedule_task_batch(self, batch: TaskBatch) -> List[str]:
        """调度任务批次"""
        task_ids = []
        
        for task in batch.tasks:
            # 设置批次优先级
            if task.priority == TaskPriority.MEDIUM:
                task.priority = batch.batch_priority
            
            # 添加批次元数据
            task.metadata['batch_id'] = batch.batch_id
            task.metadata['batch_size'] = len(batch.tasks)
            
            task_id = await self.schedule_task(task)
            task_ids.append(task_id)
        
        logger.info(f"批次任务已调度: {batch.batch_id}, 任务数: {len(task_ids)}")
        return task_ids
    
    async def schedule_pipeline_tasks(self, pipeline_config: Dict[str, Any]) -> Dict[str, List[str]]:
        """调度流水线任务"""
        pipeline_id = pipeline_config.get('pipeline_id', f"pipeline_{int(time.time())}")
        
        # 创建各阶段任务
        stage_tasks = {
            'extraction': self._create_extraction_tasks(pipeline_config),
            'rag_processing': self._create_rag_tasks(pipeline_config),
            'matching': self._create_matching_tasks(pipeline_config),
            'decision': self._create_decision_tasks(pipeline_config),
            'submission': self._create_submission_tasks(pipeline_config)
        }
        
        # 设置任务依赖关系
        self._setup_task_dependencies(stage_tasks)
        
        # 调度所有任务
        scheduled_task_ids = {}
        for stage, tasks in stage_tasks.items():
            task_ids = []
            for task in tasks:
                task.metadata['pipeline_id'] = pipeline_id
                task.metadata['stage'] = stage
                task_id = await self.schedule_task(task)
                task_ids.append(task_id)
            scheduled_task_ids[stage] = task_ids
        
        logger.info(f"流水线任务已调度: {pipeline_id}")
        return scheduled_task_ids
    
    def register_task_executor(self, task_type: str, executor: Callable):
        """注册任务执行器"""
        self.task_executors[task_type] = executor
        logger.info(f"注册任务执行器: {task_type}")
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        # 检查运行中的任务
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            return self._task_to_dict(task)
        
        # 检查已完成的任务
        if task_id in self.completed_tasks:
            task = self.completed_tasks[task_id]
            return self._task_to_dict(task)
        
        # 检查失败的任务
        if task_id in self.failed_tasks:
            task = self.failed_tasks[task_id]
            return self._task_to_dict(task)
        
        # 检查队列中的任务
        for priority_queue in self.task_queues.values():
            # 注意：这里无法直接检查队列中的任务，需要其他方式
            pass
        
        return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.status = TaskStatus.CANCELLED
            logger.info(f"任务已取消: {task_id}")
            return True
        
        return False
    
    async def retry_failed_task(self, task_id: str) -> bool:
        """重试失败的任务"""
        if task_id not in self.failed_tasks:
            return False
        
        task = self.failed_tasks[task_id]
        if task.retry_count >= task.max_retries:
            logger.warning(f"任务重试次数已达上限: {task_id}")
            return False
        
        # 重置任务状态
        task.status = TaskStatus.RETRYING
        task.retry_count += 1
        task.error_message = None
        
        # 重新调度
        await self.schedule_task(task)
        
        # 从失败列表中移除
        del self.failed_tasks[task_id]
        
        logger.info(f"任务重试: {task_id}, 重试次数: {task.retry_count}")
        return True
    
    async def _worker(self, worker_name: str):
        """工作线程"""
        logger.info(f"启动工作线程: {worker_name}")
        
        while self.is_running:
            try:
                # 按优先级获取任务
                task = await self._get_next_task()
                if not task:
                    await asyncio.sleep(0.1)
                    continue
                
                # 执行任务
                async with self.semaphore:
                    await self._execute_task(task, worker_name)
                
            except asyncio.CancelledError:
                logger.info(f"工作线程被取消: {worker_name}")
                break
            except Exception as e:
                logger.error(f"工作线程错误 {worker_name}: {e}")
                await asyncio.sleep(1)
    
    async def _get_next_task(self) -> Optional[PipelineTask]:
        """按优先级获取下一个任务"""
        # 按优先级从高到低检查队列
        for priority in sorted(TaskPriority, key=lambda x: x.value, reverse=True):
            queue = self.task_queues[priority]
            if not queue.empty():
                try:
                    task = await asyncio.wait_for(queue.get(), timeout=0.1)
                    self.stats['queue_sizes'][priority.name] -= 1
                    return task
                except asyncio.TimeoutError:
                    continue
        
        return None
    
    async def _execute_task(self, task: PipelineTask, worker_name: str):
        """执行单个任务"""
        task.started_at = datetime.now()
        task.status = TaskStatus.RUNNING
        self.running_tasks[task.task_id] = task
        
        logger.info(f"开始执行任务: {task.task_id} (工作线程: {worker_name})")
        
        try:
            # 检查任务执行器
            if task.task_type not in self.task_executors:
                raise TaskExecutionError(f"No executor found for task type: {task.task_type}")
            
            executor = self.task_executors[task.task_type]
            
            # 执行任务（带超时）
            if task.timeout:
                result = await asyncio.wait_for(
                    executor(task.data),
                    timeout=task.timeout
                )
            else:
                result = await executor(task.data)
            
            # 任务完成
            task.completed_at = datetime.now()
            task.status = TaskStatus.COMPLETED
            task.result = result
            
            # 移动到完成列表
            del self.running_tasks[task.task_id]
            self.completed_tasks[task.task_id] = task
            
            # 更新统计
            execution_time = (task.completed_at - task.started_at).total_seconds()
            self.stats['total_tasks_completed'] += 1
            self.stats['total_execution_time'] += execution_time
            self.stats['average_task_time'] = (
                self.stats['total_execution_time'] / self.stats['total_tasks_completed']
            )
            
            logger.info(f"任务执行完成: {task.task_id}, 耗时: {execution_time:.2f}秒")
            
        except asyncio.TimeoutError:
            task.status = TaskStatus.FAILED
            task.error_message = f"Task timeout after {task.timeout} seconds"
            self._handle_task_failure(task)
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            self._handle_task_failure(task)
            logger.error(f"任务执行失败: {task.task_id}, 错误: {e}")
    
    def _handle_task_failure(self, task: PipelineTask):
        """处理任务失败"""
        # 移动到失败列表
        if task.task_id in self.running_tasks:
            del self.running_tasks[task.task_id]
        self.failed_tasks[task.task_id] = task
        
        # 更新统计
        self.stats['total_tasks_failed'] += 1
        
        # 检查是否需要重试
        if task.retry_count < task.max_retries:
            logger.info(f"任务将自动重试: {task.task_id}")
            # 这里可以添加自动重试逻辑
    
    async def _monitor_tasks(self):
        """监控任务执行"""
        while self.is_running:
            try:
                # 更新工作线程利用率
                active_workers = len(self.running_tasks)
                self.stats['worker_utilization'] = active_workers / self.max_concurrent
                
                # 检查超时任务
                await self._check_timeout_tasks()
                
                # 清理历史记录
                await self._cleanup_history()
                
                await asyncio.sleep(10)  # 每10秒监控一次
                
            except Exception as e:
                logger.error(f"任务监控错误: {e}")
                await asyncio.sleep(5)
    
    async def _check_timeout_tasks(self):
        """检查超时任务"""
        current_time = datetime.now()
        timeout_tasks = []
        
        for task_id, task in self.running_tasks.items():
            if task.timeout and task.started_at:
                elapsed = (current_time - task.started_at).total_seconds()
                if elapsed > task.timeout:
                    timeout_tasks.append(task_id)
        
        for task_id in timeout_tasks:
            task = self.running_tasks[task_id]
            task.status = TaskStatus.FAILED
            task.error_message = f"Task timeout after {task.timeout} seconds"
            self._handle_task_failure(task)
    
    async def _cleanup_history(self):
        """清理历史记录"""
        # 保留最近1000个已完成的任务
        if len(self.completed_tasks) > 1000:
            # 按完成时间排序，保留最新的
            sorted_tasks = sorted(
                self.completed_tasks.items(),
                key=lambda x: x[1].completed_at or datetime.min,
                reverse=True
            )
            
            # 保留前1000个
            self.completed_tasks = dict(sorted_tasks[:1000])
        
        # 保留最近100个失败的任务
        if len(self.failed_tasks) > 100:
            sorted_failed = sorted(
                self.failed_tasks.items(),
                key=lambda x: x[1].started_at or datetime.min,
                reverse=True
            )
            self.failed_tasks = dict(sorted_failed[:100])
    
    def _create_extraction_tasks(self, config: Dict[str, Any]) -> List[PipelineTask]:
        """创建提取任务"""
        tasks = []
        keywords = config.get('search_keywords', [])
        
        for i, keyword in enumerate(keywords):
            task = PipelineTask(
                task_id=f"extraction_{keyword}_{int(time.time())}_{i}",
                task_type="job_extraction",
                data={
                    'keyword': keyword,
                    'max_results': config.get('max_jobs_per_keyword', 50),
                    'max_pages': config.get('max_pages', 5)
                },
                priority=TaskPriority.HIGH,
                timeout=300  # 5分钟超时
            )
            tasks.append(task)
        
        return tasks
    
    def _create_rag_tasks(self, config: Dict[str, Any]) -> List[PipelineTask]:
        """创建RAG处理任务"""
        task = PipelineTask(
            task_id=f"rag_processing_{int(time.time())}",
            task_type="rag_processing",
            data={
                'batch_size': config.get('rag_batch_size', 50),
                'force_reprocess': config.get('force_reprocess', False)
            },
            priority=TaskPriority.HIGH,
            timeout=600,  # 10分钟超时
            dependencies=[]  # 将在setup_dependencies中设置
        )
        return [task]
    
    def _create_matching_tasks(self, config: Dict[str, Any]) -> List[PipelineTask]:
        """创建匹配任务"""
        task = PipelineTask(
            task_id=f"matching_{int(time.time())}",
            task_type="resume_matching",
            data={
                'resume_profile': config.get('resume_profile', {}),
                'top_k': config.get('top_k_matches', 50)
            },
            priority=TaskPriority.MEDIUM,
            timeout=300  # 5分钟超时
        )
        return [task]
    
    def _create_decision_tasks(self, config: Dict[str, Any]) -> List[PipelineTask]:
        """创建决策任务"""
        task = PipelineTask(
            task_id=f"decision_{int(time.time())}",
            task_type="intelligent_decision",
            data={
                'decision_criteria': config.get('decision_criteria', {})
            },
            priority=TaskPriority.MEDIUM,
            timeout=180  # 3分钟超时
        )
        return [task]
    
    def _create_submission_tasks(self, config: Dict[str, Any]) -> List[PipelineTask]:
        """创建投递任务"""
        task = PipelineTask(
            task_id=f"submission_{int(time.time())}",
            task_type="auto_submission",
            data={
                'submission_config': config.get('submission_config', {})
            },
            priority=TaskPriority.LOW,
            timeout=1800  # 30分钟超时
        )
        return [task]
    
    def _setup_task_dependencies(self, stage_tasks: Dict[str, List[PipelineTask]]):
        """设置任务依赖关系"""
        # RAG任务依赖所有提取任务
        rag_tasks = stage_tasks['rag_processing']
        extraction_task_ids = [task.task_id for task in stage_tasks['extraction']]
        for rag_task in rag_tasks:
            rag_task.dependencies.extend(extraction_task_ids)
        
        # 匹配任务依赖RAG任务
        matching_tasks = stage_tasks['matching']
        rag_task_ids = [task.task_id for task in rag_tasks]
        for matching_task in matching_tasks:
            matching_task.dependencies.extend(rag_task_ids)
        
        # 决策任务依赖匹配任务
        decision_tasks = stage_tasks['decision']
        matching_task_ids = [task.task_id for task in matching_tasks]
        for decision_task in decision_tasks:
            decision_task.dependencies.extend(matching_task_ids)
        
        # 投递任务依赖决策任务
        submission_tasks = stage_tasks['submission']
        decision_task_ids = [task.task_id for task in decision_tasks]
        for submission_task in submission_tasks:
            submission_task.dependencies.extend(decision_task_ids)
    
    def _validate_task(self, task: PipelineTask) -> bool:
        """验证任务"""
        if not task.task_id or not task.task_type:
            return False
        
        if not isinstance(task.data, dict):
            return False
        
        return True
    
    async def _check_dependencies(self, task: PipelineTask) -> bool:
        """检查任务依赖"""
        for dep_task_id in task.dependencies:
            if dep_task_id not in self.completed_tasks:
                return False
        return True
    
    def _task_to_dict(self, task: PipelineTask) -> Dict[str, Any]:
        """将任务转换为字典"""
        return {
            'task_id': task.task_id,
            'task_type': task.task_type,
            'status': task.status.value,
            'priority': task.priority.name,
            'created_at': task.created_at.isoformat() if task.created_at else None,
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'retry_count': task.retry_count,
            'max_retries': task.max_retries,
            'error_message': task.error_message,
            'dependencies': task.dependencies,
            'metadata': task.metadata
        }
    
    def get_scheduler_stats(self) -> Dict[str, Any]:
        """获取调度器统计信息"""
        return {
            'stats': self.stats.copy(),
            'queue_status': {
                priority.name: queue.qsize()
                for priority, queue in self.task_queues.items()
            },
            'running_tasks_count': len(self.running_tasks),
            'completed_tasks_count': len(self.completed_tasks),
            'failed_tasks_count': len(self.failed_tasks),
            'is_running': self.is_running,
            'max_concurrent': self.max_concurrent
        }