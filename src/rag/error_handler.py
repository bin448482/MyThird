#!/usr/bin/env python3
"""
RAG系统增强错误处理器

提供全面的错误处理、恢复机制、重试策略和错误报告功能
"""

import asyncio
import logging
import traceback
import time
import json
from typing import Dict, List, Any, Optional, Callable, Union, Type
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
import sqlite3
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"           # 轻微错误，不影响主要功能
    MEDIUM = "medium"     # 中等错误，影响部分功能
    HIGH = "high"         # 严重错误，影响核心功能
    CRITICAL = "critical" # 致命错误，系统无法继续运行

class ErrorCategory(Enum):
    """错误类别"""
    DATABASE = "database"           # 数据库相关错误
    NETWORK = "network"            # 网络连接错误
    API = "api"                    # API调用错误
    VALIDATION = "validation"      # 数据验证错误
    PROCESSING = "processing"      # 数据处理错误
    RESOURCE = "resource"          # 资源相关错误（内存、磁盘等）
    CONFIGURATION = "configuration" # 配置错误
    SYSTEM = "system"              # 系统级错误
    UNKNOWN = "unknown"            # 未知错误

@dataclass
class ErrorInfo:
    """错误信息数据类"""
    error_id: str
    timestamp: datetime
    severity: ErrorSeverity
    category: ErrorCategory
    error_type: str
    error_message: str
    stack_trace: str
    context: Dict[str, Any]
    operation: str
    retry_count: int = 0
    resolved: bool = False
    resolution_method: Optional[str] = None
    resolution_timestamp: Optional[datetime] = None

class RetryStrategy:
    """重试策略"""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, 
                 max_delay: float = 60.0, exponential_base: float = 2.0,
                 jitter: bool = True):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """计算重试延迟时间"""
        if attempt <= 0:
            return 0
        
        # 指数退避
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)
        
        # 添加抖动以避免雷群效应
        if self.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)
        
        return delay
    
    def should_retry(self, attempt: int, error: Exception) -> bool:
        """判断是否应该重试"""
        if attempt >= self.max_attempts:
            return False
        
        # 根据错误类型判断是否可重试
        non_retryable_errors = (
            ValueError,           # 数据验证错误
            TypeError,           # 类型错误
            KeyError,            # 键错误
            AttributeError,      # 属性错误
        )
        
        if isinstance(error, non_retryable_errors):
            return False
        
        # 网络和临时性错误可以重试
        retryable_errors = (
            requests.exceptions.RequestException,
            sqlite3.OperationalError,
            ConnectionError,
            TimeoutError,
            OSError,
        )
        
        return isinstance(error, retryable_errors)

class ErrorRecoveryStrategy:
    """错误恢复策略"""
    
    @staticmethod
    def database_recovery(error: Exception, context: Dict[str, Any]) -> Optional[Any]:
        """数据库错误恢复"""
        if isinstance(error, sqlite3.OperationalError):
            error_msg = str(error).lower()
            
            if "database is locked" in error_msg:
                # 数据库锁定，等待后重试
                time.sleep(1)
                return "retry_after_delay"
            
            elif "no such table" in error_msg:
                # 表不存在，尝试创建表
                return "create_missing_table"
            
            elif "disk i/o error" in error_msg:
                # 磁盘I/O错误，切换到备用存储
                return "switch_to_backup_storage"
        
        return None
    
    @staticmethod
    def network_recovery(error: Exception, context: Dict[str, Any]) -> Optional[Any]:
        """网络错误恢复"""
        if isinstance(error, requests.exceptions.RequestException):
            if isinstance(error, requests.exceptions.Timeout):
                # 超时错误，增加超时时间重试
                return "increase_timeout_and_retry"
            
            elif isinstance(error, requests.exceptions.ConnectionError):
                # 连接错误，检查网络状态
                return "check_network_and_retry"
            
            elif hasattr(error, 'response') and error.response is not None:
                status_code = error.response.status_code
                
                if status_code == 429:  # 速率限制
                    return "rate_limit_backoff"
                elif status_code >= 500:  # 服务器错误
                    return "server_error_retry"
                elif status_code == 401:  # 认证错误
                    return "refresh_authentication"
        
        return None
    
    @staticmethod
    def api_recovery(error: Exception, context: Dict[str, Any]) -> Optional[Any]:
        """API错误恢复"""
        error_msg = str(error).lower()
        
        if "api key" in error_msg or "unauthorized" in error_msg:
            return "check_api_credentials"
        
        elif "quota" in error_msg or "limit" in error_msg:
            return "switch_to_backup_api"
        
        elif "invalid format" in error_msg or "json" in error_msg:
            return "use_fallback_processing"
        
        return None
    
    @staticmethod
    def resource_recovery(error: Exception, context: Dict[str, Any]) -> Optional[Any]:
        """资源错误恢复"""
        if isinstance(error, MemoryError):
            return "reduce_batch_size_and_gc"
        
        elif isinstance(error, OSError):
            error_msg = str(error).lower()
            
            if "no space left" in error_msg:
                return "cleanup_temp_files"
            
            elif "too many open files" in error_msg:
                return "close_unused_connections"
        
        return None

class ErrorHandler:
    """错误处理器主类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.errors: List[ErrorInfo] = []
        self.error_stats: Dict[str, int] = {}
        
        # 重试策略配置
        retry_config = config.get('retry', {})
        self.default_retry_strategy = RetryStrategy(
            max_attempts=retry_config.get('max_attempts', 3),
            base_delay=retry_config.get('base_delay', 1.0),
            max_delay=retry_config.get('max_delay', 60.0),
            exponential_base=retry_config.get('exponential_base', 2.0),
            jitter=retry_config.get('jitter', True)
        )
        
        # 错误恢复策略
        self.recovery_strategies = {
            ErrorCategory.DATABASE: ErrorRecoveryStrategy.database_recovery,
            ErrorCategory.NETWORK: ErrorRecoveryStrategy.network_recovery,
            ErrorCategory.API: ErrorRecoveryStrategy.api_recovery,
            ErrorCategory.RESOURCE: ErrorRecoveryStrategy.resource_recovery,
        }
        
        # 错误报告配置
        self.enable_error_reporting = config.get('enable_error_reporting', True)
        self.error_report_file = config.get('error_report_file', './logs/error_report.json')
        
        # 确保日志目录存在
        Path(self.error_report_file).parent.mkdir(parents=True, exist_ok=True)
    
    def categorize_error(self, error: Exception, context: Dict[str, Any]) -> ErrorCategory:
        """错误分类"""
        error_type = type(error).__name__
        error_msg = str(error).lower()
        
        # 数据库错误
        if isinstance(error, (sqlite3.Error, sqlite3.OperationalError)):
            return ErrorCategory.DATABASE
        
        # 网络错误
        if isinstance(error, (requests.exceptions.RequestException, ConnectionError, TimeoutError)):
            return ErrorCategory.NETWORK
        
        # API错误
        if "api" in error_msg or "unauthorized" in error_msg or "quota" in error_msg:
            return ErrorCategory.API
        
        # 验证错误
        if isinstance(error, (ValueError, TypeError, KeyError)):
            return ErrorCategory.VALIDATION
        
        # 资源错误
        if isinstance(error, (MemoryError, OSError)):
            return ErrorCategory.RESOURCE
        
        # 配置错误
        if "config" in error_msg or "setting" in error_msg:
            return ErrorCategory.CONFIGURATION
        
        # 系统错误
        if isinstance(error, (SystemError, RuntimeError)):
            return ErrorCategory.SYSTEM
        
        return ErrorCategory.UNKNOWN
    
    def determine_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """确定错误严重程度"""
        # 致命错误
        if isinstance(error, (SystemExit, KeyboardInterrupt, MemoryError)):
            return ErrorSeverity.CRITICAL
        
        # 严重错误
        if category in [ErrorCategory.DATABASE, ErrorCategory.SYSTEM]:
            return ErrorSeverity.HIGH
        
        # 中等错误
        if category in [ErrorCategory.NETWORK, ErrorCategory.API, ErrorCategory.RESOURCE]:
            return ErrorSeverity.MEDIUM
        
        # 轻微错误
        return ErrorSeverity.LOW
    
    def record_error(self, error: Exception, operation: str, context: Dict[str, Any]) -> str:
        """记录错误"""
        error_id = f"ERR_{int(time.time() * 1000)}_{len(self.errors)}"
        category = self.categorize_error(error, context)
        severity = self.determine_severity(error, category)
        
        error_info = ErrorInfo(
            error_id=error_id,
            timestamp=datetime.now(),
            severity=severity,
            category=category,
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            context=context,
            operation=operation
        )
        
        self.errors.append(error_info)
        
        # 更新统计
        error_key = f"{category.value}_{error_info.error_type}"
        self.error_stats[error_key] = self.error_stats.get(error_key, 0) + 1
        
        # 记录日志
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }[severity]
        
        logger.log(log_level, f"错误记录 [{error_id}] {category.value}: {error}")
        
        # 保存错误报告
        if self.enable_error_reporting:
            self._save_error_report()
        
        return error_id
    
    def attempt_recovery(self, error: Exception, category: ErrorCategory, 
                        context: Dict[str, Any]) -> Optional[str]:
        """尝试错误恢复"""
        if category not in self.recovery_strategies:
            return None
        
        recovery_strategy = self.recovery_strategies[category]
        return recovery_strategy(error, context)
    
    def mark_error_resolved(self, error_id: str, resolution_method: str) -> bool:
        """标记错误已解决"""
        for error_info in self.errors:
            if error_info.error_id == error_id:
                error_info.resolved = True
                error_info.resolution_method = resolution_method
                error_info.resolution_timestamp = datetime.now()
                
                logger.info(f"错误 {error_id} 已解决，方法: {resolution_method}")
                return True
        
        return False
    
    def _save_error_report(self) -> None:
        """保存错误报告"""
        try:
            report_data = {
                'timestamp': datetime.now().isoformat(),
                'total_errors': len(self.errors),
                'error_stats': self.error_stats,
                'recent_errors': [
                    asdict(error) for error in self.errors[-10:]  # 最近10个错误
                ]
            }
            
            # 转换datetime对象为字符串
            def datetime_converter(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, (ErrorSeverity, ErrorCategory)):
                    return obj.value
                return obj
            
            with open(self.error_report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2, default=datetime_converter)
        
        except Exception as e:
            logger.error(f"保存错误报告失败: {e}")
    
    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        if not self.errors:
            return {'total_errors': 0}
        
        # 按严重程度统计
        severity_stats = {}
        for severity in ErrorSeverity:
            severity_stats[severity.value] = sum(
                1 for error in self.errors if error.severity == severity
            )
        
        # 按类别统计
        category_stats = {}
        for category in ErrorCategory:
            category_stats[category.value] = sum(
                1 for error in self.errors if error.category == category
            )
        
        # 解决率统计
        resolved_count = sum(1 for error in self.errors if error.resolved)
        resolution_rate = (resolved_count / len(self.errors)) * 100 if self.errors else 0
        
        return {
            'total_errors': len(self.errors),
            'resolved_errors': resolved_count,
            'resolution_rate': round(resolution_rate, 2),
            'severity_distribution': severity_stats,
            'category_distribution': category_stats,
            'error_stats': self.error_stats,
            'recent_errors': [
                {
                    'error_id': error.error_id,
                    'timestamp': error.timestamp.isoformat(),
                    'severity': error.severity.value,
                    'category': error.category.value,
                    'operation': error.operation,
                    'resolved': error.resolved
                }
                for error in self.errors[-5:]  # 最近5个错误
            ]
        }

def with_error_handling(operation_name: str, 
                       retry_strategy: Optional[RetryStrategy] = None,
                       enable_recovery: bool = True):
    """错误处理装饰器"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            error_handler = getattr(args[0], 'error_handler', None) if args else None
            if not error_handler:
                return await func(*args, **kwargs)
            
            strategy = retry_strategy or error_handler.default_retry_strategy
            attempt = 0
            last_error = None
            
            while attempt < strategy.max_attempts:
                try:
                    return await func(*args, **kwargs)
                
                except Exception as e:
                    last_error = e
                    attempt += 1
                    
                    # 记录错误
                    context = {
                        'function': func.__name__,
                        'args_count': len(args),
                        'kwargs_keys': list(kwargs.keys()),
                        'attempt': attempt
                    }
                    error_id = error_handler.record_error(e, operation_name, context)
                    
                    # 判断是否应该重试
                    if not strategy.should_retry(attempt, e):
                        logger.error(f"错误不可重试或达到最大重试次数: {e}")
                        break
                    
                    # 尝试错误恢复
                    if enable_recovery:
                        category = error_handler.categorize_error(e, context)
                        recovery_action = error_handler.attempt_recovery(e, category, context)
                        
                        if recovery_action:
                            logger.info(f"尝试错误恢复: {recovery_action}")
                            
                            # 根据恢复动作执行相应操作
                            if recovery_action == "retry_after_delay":
                                await asyncio.sleep(2)
                            elif recovery_action == "use_fallback_processing":
                                # 可以在这里实现备用处理逻辑
                                pass
                    
                    # 等待重试
                    if attempt < strategy.max_attempts:
                        delay = strategy.get_delay(attempt)
                        logger.info(f"第 {attempt} 次重试失败，{delay:.1f}秒后重试")
                        await asyncio.sleep(delay)
            
            # 所有重试都失败了
            logger.error(f"操作 {operation_name} 在 {attempt} 次尝试后仍然失败")
            raise last_error
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            error_handler = getattr(args[0], 'error_handler', None) if args else None
            if not error_handler:
                return func(*args, **kwargs)
            
            strategy = retry_strategy or error_handler.default_retry_strategy
            attempt = 0
            last_error = None
            
            while attempt < strategy.max_attempts:
                try:
                    return func(*args, **kwargs)
                
                except Exception as e:
                    last_error = e
                    attempt += 1
                    
                    # 记录错误
                    context = {
                        'function': func.__name__,
                        'args_count': len(args),
                        'kwargs_keys': list(kwargs.keys()),
                        'attempt': attempt
                    }
                    error_id = error_handler.record_error(e, operation_name, context)
                    
                    # 判断是否应该重试
                    if not strategy.should_retry(attempt, e):
                        logger.error(f"错误不可重试或达到最大重试次数: {e}")
                        break
                    
                    # 尝试错误恢复
                    if enable_recovery:
                        category = error_handler.categorize_error(e, context)
                        recovery_action = error_handler.attempt_recovery(e, category, context)
                        
                        if recovery_action:
                            logger.info(f"尝试错误恢复: {recovery_action}")
                            
                            # 根据恢复动作执行相应操作
                            if recovery_action == "retry_after_delay":
                                time.sleep(2)
                    
                    # 等待重试
                    if attempt < strategy.max_attempts:
                        delay = strategy.get_delay(attempt)
                        logger.info(f"第 {attempt} 次重试失败，{delay:.1f}秒后重试")
                        time.sleep(delay)
            
            # 所有重试都失败了
            logger.error(f"操作 {operation_name} 在 {attempt} 次尝试后仍然失败")
            raise last_error
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# 工厂函数
def create_error_handler(config: Optional[Dict[str, Any]] = None) -> ErrorHandler:
    """创建错误处理器实例"""
    default_config = {
        'retry': {
            'max_attempts': 3,
            'base_delay': 1.0,
            'max_delay': 60.0,
            'exponential_base': 2.0,
            'jitter': True
        },
        'enable_error_reporting': True,
        'error_report_file': './logs/error_report.json'
    }
    
    if config:
        # 深度合并配置
        def deep_merge(base, override):
            result = base.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        default_config = deep_merge(default_config, config)
    
    return ErrorHandler(default_config)