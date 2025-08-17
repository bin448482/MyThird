"""
数据库模型定义

定义数据库表结构和数据模型
"""

import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class JobRecord:
    """职位记录数据模型"""
    job_id: str
    title: str
    company: str
    url: str
    application_status: str = 'pending'
    match_score: Optional[float] = None
    website: str = ''
    created_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'job_id': self.job_id,
            'title': self.title,
            'company': self.company,
            'url': self.url,
            'application_status': self.application_status,
            'match_score': self.match_score,
            'website': self.website,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobRecord':
        """从字典创建实例"""
        created_at = None
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'])
        
        submitted_at = None
        if data.get('submitted_at'):
            submitted_at = datetime.fromisoformat(data['submitted_at'])
        
        return cls(
            job_id=data['job_id'],
            title=data['title'],
            company=data['company'],
            url=data['url'],
            application_status=data.get('application_status', 'pending'),
            match_score=data.get('match_score'),
            website=data.get('website', ''),
            created_at=created_at,
            submitted_at=submitted_at
        )


class DatabaseSchema:
    """数据库表结构定义"""
    
    # 职位信息表
    JOBS_TABLE = """
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id VARCHAR(100) UNIQUE NOT NULL,
        title VARCHAR(200) NOT NULL,
        company VARCHAR(200) NOT NULL,
        url VARCHAR(500) NOT NULL,
        application_status VARCHAR(50) DEFAULT 'pending',
        match_score FLOAT,
        website VARCHAR(50) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        submitted_at TIMESTAMP
    )
    """
    
    # 日志表
    LOGS_TABLE = """
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level VARCHAR(20),
        message TEXT,
        module VARCHAR(100),
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    # 创建索引
    INDEXES = [
        "CREATE INDEX IF NOT EXISTS idx_jobs_job_id ON jobs(job_id)",
        "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(application_status)",
        "CREATE INDEX IF NOT EXISTS idx_jobs_website ON jobs(website)",
        "CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level)"
    ]
    
    @classmethod
    def get_all_tables(cls) -> list:
        """获取所有表的创建语句"""
        return [
            cls.JOBS_TABLE,
            cls.LOGS_TABLE
        ]
    
    @classmethod
    def get_all_indexes(cls) -> list:
        """获取所有索引的创建语句"""
        return cls.INDEXES


class ApplicationStatus:
    """投递状态常量"""
    PENDING = 'pending'          # 待处理
    SUBMITTED = 'submitted'      # 已投递
    FAILED = 'failed'           # 投递失败
    SKIPPED = 'skipped'         # 已跳过
    WOULD_SUBMIT = 'would_submit'  # 试运行模式下会投递
    
    @classmethod
    def get_all_statuses(cls) -> list:
        """获取所有状态"""
        return [
            cls.PENDING,
            cls.SUBMITTED,
            cls.FAILED,
            cls.SKIPPED,
            cls.WOULD_SUBMIT
        ]
    
    @classmethod
    def is_valid_status(cls, status: str) -> bool:
        """检查状态是否有效"""
        return status in cls.get_all_statuses()


class LogLevel:
    """日志级别常量"""
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'
    
    @classmethod
    def get_all_levels(cls) -> list:
        """获取所有日志级别"""
        return [
            cls.DEBUG,
            cls.INFO,
            cls.WARNING,
            cls.ERROR,
            cls.CRITICAL
        ]