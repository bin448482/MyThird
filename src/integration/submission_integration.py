"""
投递功能集成模块

将投递引擎集成到主控制器流水线中
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from ..submission.submission_engine import ResumeSubmissionEngine
from ..submission.models import SubmissionConfig


class SubmissionIntegration:
    """投递功能集成器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化集成器
        
        Args:
            config: 主配置字典
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.submission_engine: Optional[ResumeSubmissionEngine] = None
    
    def execute_submission_pipeline_sync(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行投递流水线（同步版本，用于Selenium）
        
        Args:
            config: 投递配置
            
        Returns:
            执行结果
        """
        stage_start = datetime.now()
        
        try:
            self.logger.info("🎯 开始执行投递流水线（同步）")
            
            # 1. 初始化投递引擎
            if not self.submission_engine:
                self.submission_engine = ResumeSubmissionEngine(self.config)
            
            # 同步初始化
            init_success = self.submission_engine.initialize_sync()
            if not init_success:
                return {
                    'success': False,
                    'error': '投递引擎初始化失败',
                    'stage': 'submission',
                    'execution_time': 0
                }
            
            # 2. 获取配置参数 - 从主配置文件中读取批次大小
            batch_size = config.get('batch_size', 10) if config else 10
            
            # 尝试从主配置的integration_system.job_scheduler中获取batch_size
            if 'integration_system' in self.config and 'job_scheduler' in self.config['integration_system']:
                batch_size = self.config['integration_system']['job_scheduler'].get('batch_size', batch_size)
            
            # 也可以从integration_system.auto_submission中获取
            if 'integration_system' in self.config and 'auto_submission' in self.config['integration_system']:
                batch_size = self.config['integration_system']['auto_submission'].get('batch_size', batch_size)
            
            # 3. 执行批量投递（同步）
            report = self.submission_engine.run_submission_batch_sync(batch_size)
            
            # 4. 计算执行时间
            stage_time = (datetime.now() - stage_start).total_seconds()
            
            # 5. 构建结果
            result = {
                'success': True,
                'stage': 'submission',
                'execution_time': stage_time,
                'total_processed': report.total_processed,
                'successful_submissions': report.successful_count,
                'failed_submissions': report.failed_count,
                'skipped_submissions': report.skipped_count,
                'already_applied_count': report.already_applied_count,
                'success_rate': report.success_rate,
                'submission_details': [result.to_dict() for result in report.results],
                'report_summary': report.get_summary()
            }
            
            self.logger.info(f"✅ 投递流水线完成: 成功 {report.successful_count}, "
                           f"失败 {report.failed_count}, 跳过 {report.skipped_count}")
            
            return result
            
        except Exception as e:
            stage_time = (datetime.now() - stage_start).total_seconds()
            self.logger.error(f"❌ 投递流水线失败: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'stage': 'submission',
                'execution_time': stage_time,
                'total_processed': 0,
                'successful_submissions': 0,
                'failed_submissions': 0,
                'skipped_submissions': 0
            }

    async def execute_submission_stage(self,
                                     submission_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行投递阶段
        
        Args:
            submission_config: 投递配置
            
        Returns:
            执行结果
        """
        stage_start = datetime.now()
        
        try:
            self.logger.info("🎯 开始执行投递阶段")
            
            # 1. 初始化投递引擎
            if not self.submission_engine:
                self.submission_engine = ResumeSubmissionEngine(self.config)
            
            init_success = await self.submission_engine.initialize()
            if not init_success:
                return {
                    'success': False,
                    'error': '投递引擎初始化失败',
                    'stage': 'submission',
                    'execution_time': 0
                }
            
            # 2. 获取配置参数 - 从主配置文件中读取批次大小
            batch_size = submission_config.get('batch_size', 10) if submission_config else 10
            
            # 尝试从主配置的integration_system.job_scheduler中获取batch_size
            if 'integration_system' in self.config and 'job_scheduler' in self.config['integration_system']:
                batch_size = self.config['integration_system']['job_scheduler'].get('batch_size', batch_size)
            
            # 也可以从integration_system.auto_submission中获取
            if 'integration_system' in self.config and 'auto_submission' in self.config['integration_system']:
                batch_size = self.config['integration_system']['auto_submission'].get('batch_size', batch_size)
            
            # 3. 执行批量投递
            report = await self.submission_engine.run_submission_batch(batch_size)
            
            # 4. 计算执行时间
            stage_time = (datetime.now() - stage_start).total_seconds()
            
            # 5. 构建结果
            result = {
                'success': True,
                'stage': 'submission',
                'execution_time': stage_time,
                'total_processed': report.total_processed,
                'successful_submissions': report.successful_count,
                'failed_submissions': report.failed_count,
                'skipped_submissions': report.skipped_count,
                'already_applied_count': report.already_applied_count,
                'success_rate': report.success_rate,
                'submission_details': [result.to_dict() for result in report.results],
                'report_summary': report.get_summary()
            }
            
            self.logger.info(f"✅ 投递阶段完成: 成功 {report.successful_count}, "
                           f"失败 {report.failed_count}, 跳过 {report.skipped_count}")
            
            return result
            
        except Exception as e:
            stage_time = (datetime.now() - stage_start).total_seconds()
            self.logger.error(f"❌ 投递阶段失败: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'stage': 'submission',
                'execution_time': stage_time,
                'total_processed': 0,
                'successful_submissions': 0,
                'failed_submissions': 0,
                'skipped_submissions': 0
            }
    
    def get_submission_statistics(self) -> Dict[str, Any]:
        """
        获取投递统计信息
        
        Returns:
            统计信息
        """
        if not self.submission_engine:
            return {'error': '投递引擎未初始化'}
        
        return self.submission_engine.get_submission_statistics()
    
    def get_failed_submissions(self, limit: int = 20) -> list:
        """
        获取失败的投递记录
        
        Args:
            limit: 限制数量
            
        Returns:
            失败记录列表
        """
        if not self.submission_engine:
            return []
        
        return self.submission_engine.get_failed_submissions(limit)
    
    def reset_failed_submissions(self, match_ids: Optional[list] = None) -> int:
        """
        重置失败的投递记录
        
        Args:
            match_ids: 要重置的匹配记录ID列表
            
        Returns:
            重置的记录数
        """
        if not self.submission_engine:
            return 0
        
        return self.submission_engine.reset_failed_submissions(match_ids)
    
    async def cleanup(self):
        """清理资源"""
        if self.submission_engine:
            await self.submission_engine.cleanup()
            self.submission_engine = None