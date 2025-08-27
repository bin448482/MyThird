"""
投递模块数据模型

定义投递相关的数据结构和枚举类型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum


class SubmissionStatus(Enum):
    """投递状态枚举"""
    PENDING = "pending"           # 待投递
    IN_PROGRESS = "in_progress"   # 投递中
    SUCCESS = "success"           # 投递成功
    FAILED = "failed"             # 投递失败
    SKIPPED = "skipped"           # 已跳过
    ALREADY_APPLIED = "already_applied"  # 已申请过
    LOGIN_REQUIRED = "login_required"    # 需要登录
    BUTTON_NOT_FOUND = "button_not_found"  # 按钮未找到
    # 新增状态检测相关状态
    JOB_SUSPENDED = "job_suspended"      # 职位暂停招聘
    JOB_EXPIRED = "job_expired"          # 职位过期
    PAGE_ERROR = "page_error"            # 页面错误


class LoginStatus(Enum):
    """登录状态枚举"""
    LOGGED_IN = "logged_in"       # 已登录
    NOT_LOGGED_IN = "not_logged_in"  # 未登录
    LOGIN_EXPIRED = "login_expired"   # 登录过期
    UNKNOWN = "unknown"           # 未知状态


@dataclass
class ButtonInfo:
    """按钮信息"""
    selector: str                 # CSS选择器
    element_type: str            # 元素类型 (a, button, input等)
    text: str                    # 按钮文本
    onclick: Optional[str] = None  # onclick属性
    href: Optional[str] = None    # href属性
    position: Optional[Dict[str, int]] = None  # 位置信息
    confidence: float = 1.0       # 识别置信度


@dataclass
class SubmissionResult:
    """单次投递结果"""
    job_id: str
    match_id: int
    job_title: str
    company: str
    job_url: str
    status: SubmissionStatus
    message: str = ""
    error_details: Optional[str] = None
    execution_time: float = 0.0
    attempts: int = 1
    button_info: Optional[ButtonInfo] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'job_id': self.job_id,
            'match_id': self.match_id,
            'job_title': self.job_title,
            'company': self.company,
            'job_url': self.job_url,
            'status': self.status.value,
            'message': self.message,
            'error_details': self.error_details,
            'execution_time': self.execution_time,
            'attempts': self.attempts,
            'button_info': self.button_info.__dict__ if self.button_info else None,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class SubmissionReport:
    """批量投递报告"""
    total_processed: int = 0
    successful_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    already_applied_count: int = 0
    login_required_count: int = 0
    button_not_found_count: int = 0
    # 新增状态计数
    job_suspended_count: int = 0
    job_expired_count: int = 0
    page_error_count: int = 0
    
    results: List[SubmissionResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_execution_time: float = 0.0
    
    success_rate: float = 0.0
    average_execution_time: float = 0.0
    
    def add_result(self, result: SubmissionResult):
        """添加投递结果"""
        self.results.append(result)
        self.total_processed += 1
        
        if result.status == SubmissionStatus.SUCCESS:
            self.successful_count += 1
        elif result.status == SubmissionStatus.FAILED:
            self.failed_count += 1
        elif result.status == SubmissionStatus.SKIPPED:
            self.skipped_count += 1
        elif result.status == SubmissionStatus.ALREADY_APPLIED:
            self.already_applied_count += 1
        elif result.status == SubmissionStatus.LOGIN_REQUIRED:
            self.login_required_count += 1
        elif result.status == SubmissionStatus.BUTTON_NOT_FOUND:
            self.button_not_found_count += 1
        elif result.status == SubmissionStatus.JOB_SUSPENDED:
            self.job_suspended_count += 1
        elif result.status == SubmissionStatus.JOB_EXPIRED:
            self.job_expired_count += 1
        elif result.status == SubmissionStatus.PAGE_ERROR:
            self.page_error_count += 1
    
    def finalize(self):
        """完成报告统计"""
        self.end_time = datetime.now()
        if self.start_time:
            self.total_execution_time = (self.end_time - self.start_time).total_seconds()
        
        if self.total_processed > 0:
            self.success_rate = self.successful_count / self.total_processed
            total_time = sum(r.execution_time for r in self.results)
            self.average_execution_time = total_time / self.total_processed
    
    def get_summary(self) -> Dict[str, Any]:
        """获取摘要信息"""
        return {
            'total_processed': self.total_processed,
            'successful_count': self.successful_count,
            'failed_count': self.failed_count,
            'skipped_count': self.skipped_count,
            'already_applied_count': self.already_applied_count,
            'login_required_count': self.login_required_count,
            'button_not_found_count': self.button_not_found_count,
            'job_suspended_count': self.job_suspended_count,
            'job_expired_count': self.job_expired_count,
            'page_error_count': self.page_error_count,
            'success_rate': round(self.success_rate * 100, 2),
            'total_execution_time': round(self.total_execution_time, 2),
            'average_execution_time': round(self.average_execution_time, 2),
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None
        }


@dataclass
class JobMatchRecord:
    """职位匹配记录（基于现有数据库结构）"""
    id: int
    job_id: str
    job_title: str
    company: str
    job_url: str
    match_score: float
    priority_level: str
    processed: bool = False
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'JobMatchRecord':
        """从数据库行创建实例"""
        return cls(
            id=row['id'],
            job_id=row['job_id'],
            job_title=row.get('title', ''),
            company=row.get('company', ''),
            job_url=row.get('url', ''),
            match_score=row.get('match_score', 0.0),
            priority_level=row.get('priority_level', 'low'),
            processed=bool(row.get('processed', 0))
        )


@dataclass
class SubmissionConfig:
    """投递配置"""
    batch_size: int = 50  # 增加默认批次大小到50
    max_daily_submissions: int = 50
    submission_delay_range: List[float] = field(default_factory=lambda: [3.0, 8.0])
    max_retries: int = 3
    retry_delay: int = 10
    skip_on_error: bool = True
    
    # 登录配置
    auto_login_enabled: bool = True
    manual_login_timeout: int = 300
    session_check_interval: int = 60
    
    # 反爬虫配置
    random_delay: bool = True
    user_agent_rotation: bool = True
    mouse_simulation: bool = True
    scroll_simulation: bool = True
    
    # 按钮识别配置
    button_timeout: int = 10
    button_retry_attempts: int = 3
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'SubmissionConfig':
        """从字典创建配置"""
        return cls(**{k: v for k, v in config_dict.items() if hasattr(cls, k)})


@dataclass
class JobStatusResult:
    """职位状态检测结果"""
    status: SubmissionStatus
    reason: str
    page_content_snippet: Optional[str] = None
    button_text: Optional[str] = None
    button_class: Optional[str] = None
    page_title: Optional[str] = None
    detection_time: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'status': self.status.value,
            'reason': self.reason,
            'page_content_snippet': self.page_content_snippet,
            'button_text': self.button_text,
            'button_class': self.button_class,
            'page_title': self.page_title,
            'detection_time': self.detection_time,
            'timestamp': self.timestamp
        }