#!/usr/bin/env python3
"""
简历处理系统异常定义
集中管理所有简历处理相关的异常类
"""


class ResumeProcessingError(Exception):
    """简历处理基础异常"""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or 'RESUME_PROCESSING_ERROR'
        self.details = details or {}
    
    def __str__(self):
        if self.details:
            return f"{self.message} (错误代码: {self.error_code}, 详情: {self.details})"
        return f"{self.message} (错误代码: {self.error_code})"


class UnsupportedFormatError(ResumeProcessingError):
    """不支持的文档格式"""
    
    def __init__(self, format_type: str, supported_formats: list = None):
        message = f"不支持的文档格式: {format_type}"
        if supported_formats:
            message += f"，支持的格式: {supported_formats}"
        
        super().__init__(
            message=message,
            error_code='UNSUPPORTED_FORMAT',
            details={'format': format_type, 'supported_formats': supported_formats}
        )


class DocumentParseError(ResumeProcessingError):
    """文档解析错误"""
    
    def __init__(self, file_path: str, reason: str):
        message = f"文档解析失败: {file_path} - {reason}"
        super().__init__(
            message=message,
            error_code='DOCUMENT_PARSE_ERROR',
            details={'file_path': file_path, 'reason': reason}
        )


class RAGExtractionError(ResumeProcessingError):
    """RAG信息提取错误"""
    
    def __init__(self, extraction_type: str, reason: str):
        message = f"RAG信息提取失败 ({extraction_type}): {reason}"
        super().__init__(
            message=message,
            error_code='RAG_EXTRACTION_ERROR',
            details={'extraction_type': extraction_type, 'reason': reason}
        )


class DataValidationError(ResumeProcessingError):
    """数据验证错误"""
    
    def __init__(self, validation_type: str, issues: list):
        message = f"数据验证失败 ({validation_type}): {len(issues)} 个问题"
        super().__init__(
            message=message,
            error_code='DATA_VALIDATION_ERROR',
            details={'validation_type': validation_type, 'issues': issues}
        )


class LLMCallError(ResumeProcessingError):
    """LLM调用错误"""
    
    def __init__(self, provider: str, reason: str, retry_count: int = 0):
        message = f"LLM调用失败 ({provider}): {reason}"
        if retry_count > 0:
            message += f" (已重试 {retry_count} 次)"
        
        super().__init__(
            message=message,
            error_code='LLM_CALL_ERROR',
            details={'provider': provider, 'reason': reason, 'retry_count': retry_count}
        )


class ConfigurationError(ResumeProcessingError):
    """配置错误"""
    
    def __init__(self, config_key: str, reason: str):
        message = f"配置错误 ({config_key}): {reason}"
        super().__init__(
            message=message,
            error_code='CONFIGURATION_ERROR',
            details={'config_key': config_key, 'reason': reason}
        )


class FileOperationError(ResumeProcessingError):
    """文件操作错误"""
    
    def __init__(self, operation: str, file_path: str, reason: str):
        message = f"文件操作失败 ({operation}): {file_path} - {reason}"
        super().__init__(
            message=message,
            error_code='FILE_OPERATION_ERROR',
            details={'operation': operation, 'file_path': file_path, 'reason': reason}
        )


class BatchProcessingError(ResumeProcessingError):
    """批量处理错误"""
    
    def __init__(self, total_files: int, failed_files: int, errors: list):
        message = f"批量处理部分失败: {failed_files}/{total_files} 个文件处理失败"
        super().__init__(
            message=message,
            error_code='BATCH_PROCESSING_ERROR',
            details={
                'total_files': total_files,
                'failed_files': failed_files,
                'success_files': total_files - failed_files,
                'errors': errors
            }
        )


class TimeoutError(ResumeProcessingError):
    """超时错误"""
    
    def __init__(self, operation: str, timeout_seconds: int):
        message = f"操作超时 ({operation}): 超过 {timeout_seconds} 秒"
        super().__init__(
            message=message,
            error_code='TIMEOUT_ERROR',
            details={'operation': operation, 'timeout_seconds': timeout_seconds}
        )


class ResourceExhaustionError(ResumeProcessingError):
    """资源耗尽错误"""
    
    def __init__(self, resource_type: str, current_usage: str, limit: str):
        message = f"资源耗尽 ({resource_type}): 当前使用 {current_usage}，限制 {limit}"
        super().__init__(
            message=message,
            error_code='RESOURCE_EXHAUSTION_ERROR',
            details={
                'resource_type': resource_type,
                'current_usage': current_usage,
                'limit': limit
            }
        )


class QualityAssuranceError(ResumeProcessingError):
    """质量保证错误"""
    
    def __init__(self, quality_check: str, score: float, threshold: float):
        message = f"质量检查失败 ({quality_check}): 得分 {score:.3f} 低于阈值 {threshold:.3f}"
        super().__init__(
            message=message,
            error_code='QUALITY_ASSURANCE_ERROR',
            details={
                'quality_check': quality_check,
                'score': score,
                'threshold': threshold
            }
        )


# 异常处理工具函数
def handle_exception(exception: Exception, context: str = None) -> ResumeProcessingError:
    """
    将通用异常转换为简历处理异常
    
    Args:
        exception: 原始异常
        context: 异常上下文
        
    Returns:
        ResumeProcessingError: 转换后的异常
    """
    if isinstance(exception, ResumeProcessingError):
        return exception
    
    message = str(exception)
    if context:
        message = f"{context}: {message}"
    
    # 根据异常类型进行特殊处理
    if isinstance(exception, FileNotFoundError):
        return FileOperationError('read', str(exception.filename), '文件不存在')
    elif isinstance(exception, PermissionError):
        return FileOperationError('access', str(exception.filename), '权限不足')
    elif isinstance(exception, TimeoutError):
        return TimeoutError(context or 'unknown', 0)
    elif isinstance(exception, MemoryError):
        return ResourceExhaustionError('memory', 'unknown', 'system_limit')
    else:
        return ResumeProcessingError(
            message=message,
            error_code='UNKNOWN_ERROR',
            details={'original_exception': type(exception).__name__}
        )


def log_exception(logger, exception: Exception, context: str = None):
    """
    记录异常日志
    
    Args:
        logger: 日志记录器
        exception: 异常对象
        context: 异常上下文
    """
    if isinstance(exception, ResumeProcessingError):
        logger.error(f"简历处理异常: {exception}")
        if exception.details:
            logger.debug(f"异常详情: {exception.details}")
    else:
        processed_exception = handle_exception(exception, context)
        logger.error(f"未处理异常转换: {processed_exception}")
    
    # 记录异常堆栈
    import traceback
    logger.debug(f"异常堆栈:\n{traceback.format_exc()}")


# 异常恢复策略
class ExceptionRecoveryStrategy:
    """异常恢复策略"""
    
    @staticmethod
    def should_retry(exception: Exception, retry_count: int, max_retries: int) -> bool:
        """
        判断是否应该重试
        
        Args:
            exception: 异常对象
            retry_count: 当前重试次数
            max_retries: 最大重试次数
            
        Returns:
            bool: 是否应该重试
        """
        if retry_count >= max_retries:
            return False
        
        # 可重试的异常类型
        retryable_exceptions = [
            LLMCallError,
            TimeoutError,
            FileOperationError
        ]
        
        # 不可重试的异常类型
        non_retryable_exceptions = [
            UnsupportedFormatError,
            ConfigurationError,
            DataValidationError
        ]
        
        if isinstance(exception, tuple(non_retryable_exceptions)):
            return False
        
        if isinstance(exception, tuple(retryable_exceptions)):
            return True
        
        # 默认不重试未知异常
        return False
    
    @staticmethod
    def get_retry_delay(retry_count: int, base_delay: float = 1.0) -> float:
        """
        获取重试延迟时间（指数退避）
        
        Args:
            retry_count: 重试次数
            base_delay: 基础延迟时间
            
        Returns:
            float: 延迟时间（秒）
        """
        return base_delay * (2 ** retry_count)
    
    @staticmethod
    def get_fallback_action(exception: Exception) -> str:
        """
        获取异常的回退操作建议
        
        Args:
            exception: 异常对象
            
        Returns:
            str: 回退操作建议
        """
        if isinstance(exception, UnsupportedFormatError):
            return "尝试转换文档格式或使用支持的格式"
        elif isinstance(exception, DocumentParseError):
            return "检查文档完整性或尝试其他解析方法"
        elif isinstance(exception, RAGExtractionError):
            return "使用备用提取方法或人工处理"
        elif isinstance(exception, LLMCallError):
            return "检查API配置或切换到备用LLM提供商"
        elif isinstance(exception, DataValidationError):
            return "启用数据修复功能或人工校验"
        else:
            return "联系技术支持或查看详细日志"


# 异常统计
class ExceptionStatistics:
    """异常统计"""
    
    def __init__(self):
        self.exception_counts = {}
        self.total_exceptions = 0
    
    def record_exception(self, exception: Exception):
        """记录异常"""
        exception_type = type(exception).__name__
        self.exception_counts[exception_type] = self.exception_counts.get(exception_type, 0) + 1
        self.total_exceptions += 1
    
    def get_statistics(self) -> dict:
        """获取异常统计"""
        return {
            'total_exceptions': self.total_exceptions,
            'exception_counts': self.exception_counts.copy(),
            'most_common_exception': max(self.exception_counts.items(), key=lambda x: x[1])[0] if self.exception_counts else None
        }
    
    def reset(self):
        """重置统计"""
        self.exception_counts.clear()
        self.total_exceptions = 0