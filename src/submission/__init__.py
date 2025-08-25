"""
简历投递模块

提供自动化简历投递功能，包括：
- 数据库查询和状态管理
- 智能登录检测
- 按钮识别和点击
- 反爬虫策略
- 投递状态跟踪
"""

from .submission_engine import ResumeSubmissionEngine
from .data_manager import SubmissionDataManager
from .button_recognition import ButtonRecognitionEngine
from .anti_crawler import AntiCrawlerSystem
from .models import SubmissionResult, SubmissionReport, ButtonInfo

__all__ = [
    'ResumeSubmissionEngine',
    'SubmissionDataManager', 
    'ButtonRecognitionEngine',
    'AntiCrawlerSystem',
    'SubmissionResult',
    'SubmissionReport',
    'ButtonInfo'
]