"""
职位状态检测器
基于现有架构设计，提供高效的页面状态检测功能
"""

import logging
import time
from typing import Dict, Any, Optional
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from .models import JobStatusResult, SubmissionStatus


class JobStatusDetector:
    """职位状态检测器 - 遵循现有组件设计模式"""
    
    def __init__(self, driver, config: Dict[str, Any]):
        """
        初始化状态检测器
        
        Args:
            driver: Selenium WebDriver实例
            config: 配置字典
        """
        self.driver = driver
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 从配置中获取检测规则
        self.detection_config = config.get('job_status_detection', {})
        self.timeout = self.detection_config.get('timeout', 5)
        
        # 状态检测规则
        self._init_detection_rules()
    
    def _init_detection_rules(self):
        """初始化检测规则"""
        
        # 页面文本检测规则
        self.text_patterns = {
            SubmissionStatus.JOB_SUSPENDED: [
                "很抱歉，你选择的职位目前已经暂停招聘",
                "该职位已暂停招聘",
                "职位暂停招聘"
            ],
            SubmissionStatus.JOB_EXPIRED: [
                "该职位已过期",
                "职位已过期",
                "招聘已结束"
            ],
            SubmissionStatus.LOGIN_REQUIRED: [
                "请先登录",
                "需要登录后查看",
                "登录后投递"
            ]
        }
        
        # 按钮状态检测规则
        self.button_selectors = [
            "#app_ck",                    # 主要申请按钮
            "a.but_sq",                   # 通用申请按钮
            ".apply-btn",                 # 其他申请按钮
            "[onclick*='delivery']"       # 投递相关按钮
        ]
        
        # 已申请状态检测规则
        self.applied_indicators = {
            'text_patterns': ["已申请", "已投递", "已发送"],
            'class_patterns': ["off", "disabled", "applied"]
        }
    
    def detect_job_status(self) -> JobStatusResult:
        """
        检测职位状态 - 一次性获取所有信息避免重复DOM查找
        
        Returns:
            JobStatusResult: 检测结果
        """
        start_time = time.time()
        
        try:
            # 一次性获取页面信息
            page_info = self._get_page_info_once()
            
            # 基于获取的信息进行状态检测
            status_result = self._analyze_page_status(page_info)
            
            # 设置检测耗时
            status_result.detection_time = time.time() - start_time
            
            self.logger.debug(f"状态检测完成: {status_result.status.value} - {status_result.reason}")
            return status_result
            
        except Exception as e:
            self.logger.error(f"状态检测失败: {e}")
            return JobStatusResult(
                status=SubmissionStatus.PAGE_ERROR,
                reason=f"检测异常: {str(e)}",
                detection_time=time.time() - start_time
            )
    
    def _get_page_info_once(self) -> Dict[str, Any]:
        """
        一次性获取页面所有需要的信息
        避免重复DOM查找，提高性能
        """
        page_info = {
            'page_source': None,
            'page_title': None,
            'apply_button': None,
            'button_text': None,
            'button_class': None,
            'button_onclick': None,
            'error_occurred': False,
            'error_message': None
        }
        
        try:
            # 1. 获取页面源码（包含所有文本信息）
            page_info['page_source'] = self.driver.page_source
            
            # 2. 获取页面标题
            page_info['page_title'] = self.driver.title
            
            # 3. 查找申请按钮（尝试多个选择器，找到第一个就停止）
            for selector in self.button_selectors:
                try:
                    button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if button:
                        page_info['apply_button'] = button
                        page_info['button_text'] = button.text.strip()
                        page_info['button_class'] = button.get_attribute('class') or ''
                        page_info['button_onclick'] = button.get_attribute('onclick') or ''
                        break
                except NoSuchElementException:
                    continue
                except Exception as e:
                    self.logger.debug(f"查找按钮时出错 {selector}: {e}")
                    continue
            
            return page_info
            
        except Exception as e:
            page_info['error_occurred'] = True
            page_info['error_message'] = str(e)
            return page_info
    
    def _analyze_page_status(self, page_info: Dict[str, Any]) -> JobStatusResult:
        """
        基于一次性获取的页面信息分析状态
        
        Args:
            page_info: _get_page_info_once() 返回的页面信息
            
        Returns:
            JobStatusResult: 分析结果
        """
        
        # 如果获取页面信息时出错
        if page_info['error_occurred']:
            return JobStatusResult(
                status=SubmissionStatus.PAGE_ERROR,
                reason="页面信息获取失败",
                page_content_snippet=page_info.get('error_message')
            )
        
        page_source = page_info['page_source']
        button_text = page_info['button_text']
        button_class = page_info['button_class']
        page_title = page_info['page_title']
        
        # 1. 检测职位暂停（优先级最高）
        if page_source:
            for status, patterns in self.text_patterns.items():
                for pattern in patterns:
                    if pattern in page_source:
                        return JobStatusResult(
                            status=status,
                            reason=f"页面显示: {pattern}",
                            page_content_snippet=pattern,
                            page_title=page_title
                        )
        
        # 2. 检测已申请状态
        if button_text and button_class:
            # 检查按钮文本
            for pattern in self.applied_indicators['text_patterns']:
                if pattern in button_text:
                    return JobStatusResult(
                        status=SubmissionStatus.ALREADY_APPLIED,
                        reason="按钮显示已申请状态",
                        button_text=button_text,
                        button_class=button_class,
                        page_title=page_title
                    )
            
            # 检查按钮样式类
            for pattern in self.applied_indicators['class_patterns']:
                if pattern in button_class:
                    return JobStatusResult(
                        status=SubmissionStatus.ALREADY_APPLIED,
                        reason="按钮样式显示已申请状态",
                        button_text=button_text,
                        button_class=button_class,
                        page_title=page_title
                    )
        
        # 3. 检测可用申请按钮
        if button_text and any(keyword in button_text for keyword in ["申请", "投递", "应聘"]):
            if not any(pattern in button_class for pattern in self.applied_indicators['class_patterns']):
                return JobStatusResult(
                    status=SubmissionStatus.PENDING,  # 可以投递
                    reason="找到可用申请按钮",
                    button_text=button_text,
                    button_class=button_class,
                    page_title=page_title
                )
        
        # 4. 未找到申请按钮
        if not page_info['apply_button']:
            return JobStatusResult(
                status=SubmissionStatus.BUTTON_NOT_FOUND,
                reason="未找到申请按钮",
                page_title=page_title
            )
        
        # 5. 其他情况
        return JobStatusResult(
            status=SubmissionStatus.FAILED,
            reason="无法确定页面状态",
            button_text=button_text,
            button_class=button_class,
            page_title=page_title
        )
    
    def get_button_info_from_status(self, status_result: JobStatusResult) -> Optional[Dict[str, Any]]:
        """
        从状态检测结果中提取按钮信息，供后续投递使用
        
        Args:
            status_result: 状态检测结果
            
        Returns:
            按钮信息字典，如果没有可用按钮则返回None
        """
        if status_result.status == SubmissionStatus.PENDING and status_result.button_text:
            # 如果状态是可投递，返回按钮信息
            return {
                'text': status_result.button_text,
                'class': status_result.button_class,
                'available': True
            }
        
        return None
    
    def is_job_available_for_submission(self, status_result: JobStatusResult) -> bool:
        """
        判断职位是否可以投递
        
        Args:
            status_result: 状态检测结果
            
        Returns:
            是否可以投递
        """
        return status_result.status == SubmissionStatus.PENDING
    
    def should_delete_job(self, status_result: JobStatusResult) -> bool:
        """
        判断是否应该删除职位记录
        
        Args:
            status_result: 状态检测结果
            
        Returns:
            是否应该删除
        """
        return status_result.status == SubmissionStatus.JOB_SUSPENDED
    
    def should_mark_as_applied(self, status_result: JobStatusResult) -> bool:
        """
        判断是否应该标记为已申请
        
        Args:
            status_result: 状态检测结果
            
        Returns:
            是否应该标记为已申请
        """
        return status_result.status == SubmissionStatus.ALREADY_APPLIED