"""
日志工具模块

配置和管理应用程序日志
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any


def setup_logger(config: Dict[str, Any]) -> logging.Logger:
    """
    设置日志配置
    
    Args:
        config: 配置字典
        
    Returns:
        配置好的logger实例
    """
    logging_config = config.get('logging', {})
    
    # 获取配置参数
    log_level = logging_config.get('level', 'INFO').upper()
    log_file = logging_config.get('file_path', './logs/app.log')
    console_output = logging_config.get('console_output', True)
    max_file_size = logging_config.get('max_file_size', '10MB')
    backup_count = logging_config.get('backup_count', 5)
    
    # 创建日志目录
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 配置根logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level))
    
    # 清除现有的handlers
    logger.handlers.clear()
    
    # 创建formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 文件handler（带轮转）
    if log_file:
        # 解析文件大小
        size_bytes = _parse_size(max_file_size)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=size_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, log_level))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # 控制台handler
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level))
        
        # 控制台使用简化的格式
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    return logger


def _parse_size(size_str: str) -> int:
    """
    解析文件大小字符串
    
    Args:
        size_str: 大小字符串，如 '10MB', '1GB'
        
    Returns:
        字节数
    """
    size_str = size_str.upper().strip()
    
    if size_str.endswith('KB'):
        return int(size_str[:-2]) * 1024
    elif size_str.endswith('MB'):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith('GB'):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    else:
        # 默认为字节
        return int(size_str)


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的logger
    
    Args:
        name: logger名称
        
    Returns:
        logger实例
    """
    return logging.getLogger(name)


class LoggerMixin:
    """日志混入类，为其他类提供日志功能"""
    
    @property
    def logger(self) -> logging.Logger:
        """获取当前类的logger"""
        return logging.getLogger(self.__class__.__module__ + '.' + self.__class__.__name__)