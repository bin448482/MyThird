"""
错误处理和恢复机制
提供完善的错误处理、恢复和重试功能
"""

import asyncio
import logging
import traceback
import pickle
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """错误类别"""
    NETWORK = "network"
    DATABASE = "database"
    VALIDATION = "validation"
    PROCESSING = "processing"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    UNKNOWN = "unknown"

class RecoveryStrategy(Enum):
    """恢复策略"""
    RETRY = "retry"
    SKIP = "skip"
    FALLBACK = "fallback"
    RESTART = "restart"
    MANUAL = "manual"
    ABORT = "abort"

@dataclass
class ErrorInfo:
    """错误信息"""
    error_id: str
    error_type: str
    error_message: str
    error_details: str
    severity: ErrorSeverity
    category: ErrorCategory
    occurred_at: datetime
    context: Dict[str, Any]
    stack_trace: str
    recovery_strategy: Optional[RecoveryStrategy] = None
    retry_count: int = 0
    max_retries: int = 3
    resolved: bool = False
    resolution_time: Optional[datetime] = None

@dataclass
class CheckpointData:
    """检查点数据"""
    checkpoint_id: str
    pipeline_id: str
    stage: str
    data: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RecoveryResult:
    """恢复结果"""
    success: bool
    strategy_used: RecoveryStrategy
    recovery_time: float
    error_resolved: bool
    checkpoint_restored: bool
    message: str
    new_error: Optional[ErrorInfo] = None

class PipelineError(Exception):
    """流水线错误基类"""
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.UNKNOWN, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM, context: Dict = None):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.context = context or {}

class NetworkError(PipelineError):
    """网络错误"""
    def __init__(self, message: str, context: Dict = None):
        super().__init__(message, ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, context)

class DatabaseError(PipelineError):
    """数据库错误"""
    def __init__(self, message: str, context: Dict = None):
        super().__init__(message, ErrorCategory.DATABASE, ErrorSeverity.HIGH, context)

class ValidationError(PipelineError):
    """验证错误"""
    def __init__(self, message: str, context: Dict = None):
        super().__init__(message, ErrorCategory.VALIDATION, ErrorSeverity.LOW, context)

class ProcessingError(PipelineError):
    """处理错误"""
    def __init__(self, message: str, context: Dict = None):
        super().__init__(message, ErrorCategory.PROCESSING, ErrorSeverity.MEDIUM, context)

class ErrorHandler:
    """错误处理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.error_config = config.get('error_handling', {})
        
        # 错误处理配置
        self.global_error_handler = self.error_config.get('global_error_handler', True)
        self.max_retry_attempts = self.error_config.get('retry_strategy', {}).get('max_attempts', 3)
        self.backoff_factor = self.error_config.get('retry_strategy', {}).get('backoff_factor', 2)
        self.max_delay = self.error_config.get('retry_strategy', {}).get('max_delay', 60)
        
        # 检查点配置
        self.enable_checkpoint = self.error_config.get('recovery', {}).get('enable_checkpoint', True)
        self.checkpoint_interval = self.error_config.get('recovery', {}).get('checkpoint_interval', 100)
        self.auto_recovery = self.error_config.get('recovery', {}).get('auto_recovery', True)
        
        # 存储路径
        self.checkpoint_dir = Path("checkpoints")
        self.error_log_dir = Path("logs/errors")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.error_log_dir.mkdir(parents=True, exist_ok=True)
        
        # 错误记录
        self.error_history = []
        self.active_errors = {}
        self.checkpoints = {}
        
        # 恢复策略映射
        self.recovery_strategies = {
            ErrorCategory.NETWORK: RecoveryStrategy.RETRY,
            ErrorCategory.DATABASE: RecoveryStrategy.RETRY,
            ErrorCategory.VALIDATION: RecoveryStrategy.SKIP,
            ErrorCategory.PROCESSING: RecoveryStrategy.RETRY,
            ErrorCategory.AUTHENTICATION: RecoveryStrategy.MANUAL,
            ErrorCategory.PERMISSION: RecoveryStrategy.MANUAL,
            ErrorCategory.TIMEOUT: RecoveryStrategy.RETRY,
            ErrorCategory.RESOURCE: RecoveryStrategy.FALLBACK,
            ErrorCategory.UNKNOWN: RecoveryStrategy.MANUAL
        }
        
        # 错误处理器映射
        self.error_handlers = {}
        self._register_default_handlers()
        
        # 统计信息
        self.stats = {
            'total_errors': 0,
            'errors_by_category': {cat.value: 0 for cat in ErrorCategory},
            'errors_by_severity': {sev.value: 0 for sev in ErrorSeverity},
            'recovery_success_rate': 0,
            'average_recovery_time': 0,
            'checkpoints_created': 0,
            'checkpoints_restored': 0
        }
    
    async def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> RecoveryResult:
        """处理错误"""
        try:
            # 创建错误信息
            error_info = self._create_error_info(error, context or {})
            
            # 记录错误
            await self._log_error(error_info)
            
            # 更新统计
            self._update_error_stats(error_info)
            
            # 确定恢复策略
            recovery_strategy = self._determine_recovery_strategy(error_info)
            error_info.recovery_strategy = recovery_strategy
            
            # 执行恢复
            recovery_result = await self._execute_recovery(error_info)
            
            # 记录恢复结果
            if recovery_result.success:
                error_info.resolved = True
                error_info.resolution_time = datetime.now()
                logger.info(f"错误恢复成功: {error_info.error_id}")
            else:
                logger.error(f"错误恢复失败: {error_info.error_id}")
            
            return recovery_result
            
        except Exception as e:
            logger.error(f"错误处理器本身发生错误: {e}")
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.ABORT,
                recovery_time=0,
                error_resolved=False,
                checkpoint_restored=False,
                message=f"错误处理器失败: {str(e)}"
            )
    
    async def create_checkpoint(self, pipeline_id: str, stage: str, data: Dict[str, Any], 
                              metadata: Dict[str, Any] = None) -> str:
        """创建检查点"""
        if not self.enable_checkpoint:
            return ""
        
        try:
            checkpoint_id = self._generate_checkpoint_id(pipeline_id, stage)
            
            checkpoint = CheckpointData(
                checkpoint_id=checkpoint_id,
                pipeline_id=pipeline_id,
                stage=stage,
                data=data,
                created_at=datetime.now(),
                metadata=metadata or {}
            )
            
            # 保存检查点
            await self._save_checkpoint(checkpoint)
            
            # 缓存检查点
            self.checkpoints[checkpoint_id] = checkpoint
            
            # 更新统计
            self.stats['checkpoints_created'] += 1
            
            logger.info(f"检查点已创建: {checkpoint_id}")
            return checkpoint_id
            
        except Exception as e:
            logger.error(f"创建检查点失败: {e}")
            return ""
    
    async def restore_checkpoint(self, checkpoint_id: str) -> Optional[CheckpointData]:
        """恢复检查点"""
        try:
            # 先从缓存查找
            if checkpoint_id in self.checkpoints:
                checkpoint = self.checkpoints[checkpoint_id]
                self.stats['checkpoints_restored'] += 1
                logger.info(f"从缓存恢复检查点: {checkpoint_id}")
                return checkpoint
            
            # 从文件加载
            checkpoint = await self._load_checkpoint(checkpoint_id)
            if checkpoint:
                self.checkpoints[checkpoint_id] = checkpoint
                self.stats['checkpoints_restored'] += 1
                logger.info(f"从文件恢复检查点: {checkpoint_id}")
                return checkpoint
            
            logger.warning(f"检查点不存在: {checkpoint_id}")
            return None
            
        except Exception as e:
            logger.error(f"恢复检查点失败: {e}")
            return None
    
    async def retry_with_backoff(self, func: Callable, *args, max_retries: int = None, 
                               backoff_factor: float = None, **kwargs) -> Any:
        """带退避的重试机制"""
        max_retries = max_retries or self.max_retry_attempts
        backoff_factor = backoff_factor or self.backoff_factor
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
                    
            except Exception as e:
                last_exception = e
                
                if attempt == max_retries:
                    logger.error(f"重试失败，已达最大重试次数 {max_retries}: {e}")
                    break
                
                # 计算退避延迟
                delay = min(backoff_factor ** attempt, self.max_delay)
                logger.warning(f"第 {attempt + 1} 次重试失败，{delay} 秒后重试: {e}")
                await asyncio.sleep(delay)
        
        # 所有重试都失败了
        raise last_exception
    
    def _create_error_info(self, error: Exception, context: Dict[str, Any]) -> ErrorInfo:
        """创建错误信息"""
        error_id = self._generate_error_id(error, context)
        
        # 确定错误类别和严重程度
        if isinstance(error, PipelineError):
            category = error.category
            severity = error.severity
            context.update(error.context)
        else:
            category = self._classify_error(error)
            severity = self._assess_severity(error, category)
        
        return ErrorInfo(
            error_id=error_id,
            error_type=type(error).__name__,
            error_message=str(error),
            error_details=repr(error),
            severity=severity,
            category=category,
            occurred_at=datetime.now(),
            context=context,
            stack_trace=traceback.format_exc()
        )
    
    def _classify_error(self, error: Exception) -> ErrorCategory:
        """分类错误"""
        error_type = type(error).__name__.lower()
        error_message = str(error).lower()
        
        if 'network' in error_message or 'connection' in error_message:
            return ErrorCategory.NETWORK
        elif 'database' in error_message or 'sql' in error_message:
            return ErrorCategory.DATABASE
        elif 'validation' in error_message or 'invalid' in error_message:
            return ErrorCategory.VALIDATION
        elif 'timeout' in error_message:
            return ErrorCategory.TIMEOUT
        elif 'permission' in error_message or 'access' in error_message:
            return ErrorCategory.PERMISSION
        elif 'auth' in error_message:
            return ErrorCategory.AUTHENTICATION
        elif 'memory' in error_message or 'resource' in error_message:
            return ErrorCategory.RESOURCE
        else:
            return ErrorCategory.UNKNOWN
    
    def _assess_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """评估错误严重程度"""
        # 基于错误类别的默认严重程度
        severity_map = {
            ErrorCategory.NETWORK: ErrorSeverity.MEDIUM,
            ErrorCategory.DATABASE: ErrorSeverity.HIGH,
            ErrorCategory.VALIDATION: ErrorSeverity.LOW,
            ErrorCategory.PROCESSING: ErrorSeverity.MEDIUM,
            ErrorCategory.AUTHENTICATION: ErrorSeverity.HIGH,
            ErrorCategory.PERMISSION: ErrorSeverity.HIGH,
            ErrorCategory.TIMEOUT: ErrorSeverity.MEDIUM,
            ErrorCategory.RESOURCE: ErrorSeverity.HIGH,
            ErrorCategory.UNKNOWN: ErrorSeverity.MEDIUM
        }
        
        base_severity = severity_map.get(category, ErrorSeverity.MEDIUM)
        
        # 基于错误消息调整严重程度
        error_message = str(error).lower()
        if 'critical' in error_message or 'fatal' in error_message:
            return ErrorSeverity.CRITICAL
        elif 'warning' in error_message:
            return ErrorSeverity.LOW
        
        return base_severity
    
    def _determine_recovery_strategy(self, error_info: ErrorInfo) -> RecoveryStrategy:
        """确定恢复策略"""
        # 检查是否有自定义处理器
        if error_info.error_type in self.error_handlers:
            return RecoveryStrategy.FALLBACK
        
        # 基于错误类别确定策略
        strategy = self.recovery_strategies.get(error_info.category, RecoveryStrategy.MANUAL)
        
        # 基于重试次数调整策略
        if error_info.retry_count >= error_info.max_retries:
            if strategy == RecoveryStrategy.RETRY:
                return RecoveryStrategy.SKIP
        
        # 基于严重程度调整策略
        if error_info.severity == ErrorSeverity.CRITICAL:
            return RecoveryStrategy.ABORT
        elif error_info.severity == ErrorSeverity.LOW:
            return RecoveryStrategy.SKIP
        
        return strategy
    
    async def _execute_recovery(self, error_info: ErrorInfo) -> RecoveryResult:
        """执行恢复策略"""
        start_time = datetime.now()
        strategy = error_info.recovery_strategy
        
        try:
            if strategy == RecoveryStrategy.RETRY:
                return await self._retry_recovery(error_info)
            elif strategy == RecoveryStrategy.SKIP:
                return await self._skip_recovery(error_info)
            elif strategy == RecoveryStrategy.FALLBACK:
                return await self._fallback_recovery(error_info)
            elif strategy == RecoveryStrategy.RESTART:
                return await self._restart_recovery(error_info)
            elif strategy == RecoveryStrategy.MANUAL:
                return await self._manual_recovery(error_info)
            elif strategy == RecoveryStrategy.ABORT:
                return await self._abort_recovery(error_info)
            else:
                return RecoveryResult(
                    success=False,
                    strategy_used=strategy,
                    recovery_time=0,
                    error_resolved=False,
                    checkpoint_restored=False,
                    message=f"未知的恢复策略: {strategy}"
                )
                
        except Exception as e:
            recovery_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"恢复策略执行失败: {e}")
            return RecoveryResult(
                success=False,
                strategy_used=strategy,
                recovery_time=recovery_time,
                error_resolved=False,
                checkpoint_restored=False,
                message=f"恢复策略执行失败: {str(e)}"
            )
    
    async def _retry_recovery(self, error_info: ErrorInfo) -> RecoveryResult:
        """重试恢复"""
        start_time = datetime.now()
        
        # 增加重试计数
        error_info.retry_count += 1
        
        # 计算延迟
        delay = min(self.backoff_factor ** (error_info.retry_count - 1), self.max_delay)
        await asyncio.sleep(delay)
        
        recovery_time = (datetime.now() - start_time).total_seconds()
        
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.RETRY,
            recovery_time=recovery_time,
            error_resolved=False,  # 需要重新执行才能确定
            checkpoint_restored=False,
            message=f"准备第 {error_info.retry_count} 次重试"
        )
    
    async def _skip_recovery(self, error_info: ErrorInfo) -> RecoveryResult:
        """跳过恢复"""
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.SKIP,
            recovery_time=0,
            error_resolved=True,
            checkpoint_restored=False,
            message="跳过错误，继续执行"
        )
    
    async def _fallback_recovery(self, error_info: ErrorInfo) -> RecoveryResult:
        """回退恢复"""
        start_time = datetime.now()
        
        # 尝试使用自定义处理器
        if error_info.error_type in self.error_handlers:
            try:
                handler = self.error_handlers[error_info.error_type]
                await handler(error_info)
                
                recovery_time = (datetime.now() - start_time).total_seconds()
                return RecoveryResult(
                    success=True,
                    strategy_used=RecoveryStrategy.FALLBACK,
                    recovery_time=recovery_time,
                    error_resolved=True,
                    checkpoint_restored=False,
                    message="使用自定义处理器恢复"
                )
            except Exception as e:
                logger.error(f"自定义处理器失败: {e}")
        
        # 尝试恢复到最近的检查点
        pipeline_id = error_info.context.get('pipeline_id')
        if pipeline_id:
            checkpoint = await self.find_latest_checkpoint(pipeline_id)
            if checkpoint:
                recovery_time = (datetime.now() - start_time).total_seconds()
                return RecoveryResult(
                    success=True,
                    strategy_used=RecoveryStrategy.FALLBACK,
                    recovery_time=recovery_time,
                    error_resolved=False,
                    checkpoint_restored=True,
                    message=f"恢复到检查点: {checkpoint.checkpoint_id}"
                )
        
        recovery_time = (datetime.now() - start_time).total_seconds()
        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.FALLBACK,
            recovery_time=recovery_time,
            error_resolved=False,
            checkpoint_restored=False,
            message="回退恢复失败"
        )
    
    async def _restart_recovery(self, error_info: ErrorInfo) -> RecoveryResult:
        """重启恢复"""
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.RESTART,
            recovery_time=0,
            error_resolved=False,
            checkpoint_restored=False,
            message="需要重启流水线"
        )
    
    async def _manual_recovery(self, error_info: ErrorInfo) -> RecoveryResult:
        """手动恢复"""
        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.MANUAL,
            recovery_time=0,
            error_resolved=False,
            checkpoint_restored=False,
            message="需要手动干预"
        )
    
    async def _abort_recovery(self, error_info: ErrorInfo) -> RecoveryResult:
        """中止恢复"""
        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.ABORT,
            recovery_time=0,
            error_resolved=False,
            checkpoint_restored=False,
            message="严重错误，中止执行"
        )
    
    async def find_latest_checkpoint(self, pipeline_id: str, stage: str = None) -> Optional[CheckpointData]:
        """查找最新的检查点"""
        try:
            matching_checkpoints = []
            
            # 搜索缓存中的检查点
            for checkpoint in self.checkpoints.values():
                if checkpoint.pipeline_id == pipeline_id:
                    if stage is None or checkpoint.stage == stage:
                        matching_checkpoints.append(checkpoint)
            
            # 搜索文件中的检查点
            checkpoint_files = list(self.checkpoint_dir.glob(f"{pipeline_id}_*.pkl"))
            for file_path in checkpoint_files:
                try:
                    checkpoint = await self._load_checkpoint_from_file(file_path)
                    if checkpoint and (stage is None or checkpoint.stage == stage):
                        matching_checkpoints.append(checkpoint)
                except Exception as e:
                    logger.warning(f"加载检查点文件失败 {file_path}: {e}")
            
            # 返回最新的检查点
            if matching_checkpoints:
                latest = max(matching_checkpoints, key=lambda x: x.created_at)
                return latest
            
            return None
            
        except Exception as e:
            logger.error(f"查找最新检查点失败: {e}")
            return None
    
    def _register_default_handlers(self):
        """注册默认错误处理器"""
        self.error_handlers['NetworkError'] = self._handle_network_error
        self.error_handlers['DatabaseError'] = self._handle_database_error
        self.error_handlers['ValidationError'] = self._handle_validation_error
        self.error_handlers['ProcessingError'] = self._handle_processing_error
    
    async def _handle_network_error(self, error_info: ErrorInfo):
        """处理网络错误"""
        logger.info(f"处理网络错误: {error_info.error_message}")
        # 可以在这里实现网络重连逻辑
    
    async def _handle_database_error(self, error_info: ErrorInfo):
        """处理数据库错误"""
        logger.info(f"处理数据库错误: {error_info.error_message}")
        # 可以在这里实现数据库重连逻辑
    
    async def _handle_validation_error(self, error_info: ErrorInfo):
        """处理验证错误"""
        logger.info(f"处理验证错误: {error_info.error_message}")
        # 可以在这里实现数据清理逻辑
    
    async def _handle_processing_error(self, error_info: ErrorInfo):
        """处理处理错误"""
        logger.info(f"处理处理错误: {error_info.error_message}")
        # 可以在这里实现数据重处理逻辑
    
    async def _save_checkpoint(self, checkpoint: CheckpointData):
        """保存检查点"""
        file_path = self.checkpoint_dir / f"{checkpoint.checkpoint_id}.pkl"
        
        try:
            with open(file_path, 'wb') as f:
                pickle.dump(checkpoint, f)
            logger.debug(f"检查点已保存: {file_path}")
        except Exception as e:
            logger.error(f"保存检查点失败: {e}")
            raise
    
    async def _load_checkpoint(self, checkpoint_id: str) -> Optional[CheckpointData]:
        """加载检查点"""
        file_path = self.checkpoint_dir / f"{checkpoint_id}.pkl"
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'rb') as f:
                checkpoint = pickle.load(f)
            return checkpoint
        except Exception as e:
            logger.error(f"加载检查点失败: {e}")
            return None
    
    async def _load_checkpoint_from_file(self, file_path: Path) -> Optional[CheckpointData]:
        """从文件加载检查点"""
        try:
            with open(file_path, 'rb') as f:
                checkpoint = pickle.load(f)
            return checkpoint
        except Exception as e:
            logger.error(f"从文件加载检查点失败 {file_path}: {e}")
            return None
    
    async def _log_error(self, error_info: ErrorInfo):
        """记录错误"""
        # 添加到历史记录
        self.error_history.append(error_info)
        self.active_errors[error_info.error_id] = error_info
        
        # 保留最近1000个错误
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-1000:]
        
        # 写入错误日志文件
        error_log_file = self.error_log_dir / f"error_{datetime.now().strftime('%Y%m%d')}.json"
        
        try:
            error_data = {
                'error_id': error_info.error_id,
                'error_type': error_info.error_type,
                'error_message': error_info.error_message,
                'severity': error_info.severity.value,
                'category': error_info.category.value,
                'occurred_at': error_info.occurred_at.isoformat(),
                'context': error_info.context,
                'stack_trace': error_info.stack_trace
            }
            
            with open(error_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(error_data, ensure_ascii=False) + '\n')
                
        except Exception as e:
            logger.error(f"写入错误日志失败: {e}")
    
    def _update_error_stats(self, error_info: ErrorInfo):
        """更新错误统计"""
        self.stats['total_errors'] += 1
        self.stats['errors_by_category'][error_info.category.value] += 1
        self.stats['errors_by_severity'][error_info.severity.value] += 1
    
    def _generate_error_id(self, error: Exception, context: Dict[str, Any]) -> str:
        """生成错误ID"""
        content = f"{type(error).__name__}_{str(error)}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _generate_checkpoint_id(self, pipeline_id: str, stage: str) -> str:
        """生成检查点ID"""
        content = f"{pipeline_id}_{stage}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def register_error_handler(self, error_type: Union[type, str], handler: Callable):
        """注册错误处理器"""
        key = error_type.__name__ if isinstance(error_type, type) else str(error_type)
        self.error_handlers[key] = handler
        logger.info(f"注册错误处理器: {key}")
    
    def set_recovery_strategy(self, category: ErrorCategory, strategy: RecoveryStrategy):
        """设置恢复策略"""
        self.recovery_strategies[category] = strategy
        logger.info(f"设置恢复策略: {category.value} -> {strategy.value}")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        # 计算恢复成功率
        resolved_errors = len([e for e in self.error_history if e.resolved])
        total_errors = len(self.error_history)
        recovery_success_rate = resolved_errors / total_errors if total_errors > 0 else 0
        
        # 计算平均恢复时间
        recovery_times = []
        for error in self.error_history:
            if error.resolved and error.resolution_time:
                recovery_time = (error.resolution_time - error.occurred_at).total_seconds()
                recovery_times.append(recovery_time)
        
        avg_recovery_time = sum(recovery_times) / len(recovery_times) if recovery_times else 0
        
        return {
            'total_errors': self.stats['total_errors'],
            'errors_by_category': self.stats['errors_by_category'],
            'errors_by_severity': self.stats['errors_by_severity'],
            'recovery_success_rate': recovery_success_rate,
            'average_recovery_time': avg_recovery_time,
            'checkpoints_created': self.stats['checkpoints_created'],
            'checkpoints_restored': self.stats['checkpoints_restored'],
            'active_errors_count': len(self.active_errors),
            'recent_errors': [
                {
                    'error_id': e.error_id,
                    'error_type': e.error_type,
                    'severity': e.severity.value,
                    'category': e.category.value,
                    'occurred_at': e.occurred_at.isoformat(),
                    'resolved': e.resolved
                }
                for e in self.error_history[-10:]
            ]
        }


class CheckpointManager:
    """检查点管理器"""
    
    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler
        self.checkpoint_counter = 0
    
    async def create_pipeline_checkpoint(self, pipeline_id: str, stage: str,
                                       extraction_result: Dict = None,
                                       rag_result: Dict = None,
                                       matching_result: Dict = None,
                                       decision_result: Dict = None) -> str:
        """创建流水线检查点"""
        data = {
            'extraction_result': extraction_result,
            'rag_result': rag_result,
            'matching_result': matching_result,
            'decision_result': decision_result,
            'checkpoint_counter': self.checkpoint_counter
        }
        
        metadata = {
            'stage': stage,
            'checkpoint_type': 'pipeline',
            'created_by': 'CheckpointManager'
        }
        
        checkpoint_id = await self.error_handler.create_checkpoint(
            pipeline_id, stage, data, metadata
        )
        
        if checkpoint_id:
            self.checkpoint_counter += 1
        
        return checkpoint_id
    
    async def restore_pipeline_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """恢复流水线检查点"""
        checkpoint = await self.error_handler.restore_checkpoint(checkpoint_id)
        if checkpoint:
            return checkpoint.data
        return None


# 装饰器函数
def with_error_handling(error_handler: ErrorHandler, context: Dict[str, Any] = None):
    """错误处理装饰器"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                recovery_result = await error_handler.handle_error(e, context or {})
                if not recovery_result.success:
                    raise
                return None
        
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 对于同步函数，只记录错误，不执行恢复
                logger.error(f"同步函数错误: {e}")
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def with_retry(max_retries: int = 3, backoff_factor: float = 2, max_delay: float = 60):
    """重试装饰器"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        break
                    
                    delay = min(backoff_factor ** attempt, max_delay)
                    logger.warning(f"第 {attempt + 1} 次重试失败，{delay} 秒后重试: {e}")
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        break
                    
                    delay = min(backoff_factor ** attempt, max_delay)
                    logger.warning(f"第 {attempt + 1} 次重试失败，{delay} 秒后重试: {e}")
                    import time
                    time.sleep(delay)
            
            raise last_exception
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator