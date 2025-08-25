"""
集成系统测试用例
测试端到端流水线的完整功能
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
import yaml

from src.integration.master_controller import MasterController, PipelineConfig
from src.integration.data_bridge import DataBridge
from src.integration.job_scheduler import JobScheduler
from src.integration.decision_engine import DecisionEngine
from src.integration.submission_integration import SubmissionIntegration
from src.integration.error_handler import ErrorHandler
from src.integration.monitoring import PipelineMonitor


class TestIntegrationSystem:
    """集成系统测试"""
    
    @pytest.fixture
    def test_config(self):
        """测试配置"""
        return {
            'integration_system': {
                'master_controller': {
                    'max_concurrent_jobs': 5,
                    'checkpoint_interval': 10,
                    'error_retry_attempts': 2
                },
                'job_scheduler': {
                    'queue_size': 100,
                    'batch_size': 10,
                    'max_concurrent_tasks': 3
                },
                'data_bridge': {
                    'validation_enabled': True,
                    'transformation_cache': True
                },
                'decision_engine': {
                    'submission_threshold': 0.7,
                    'max_daily_submissions': 10
                },
                'auto_submission': {
                    'dry_run_mode': True,
                    'max_submissions_per_day': 10
                }
            },
            'monitoring': {
                'metrics_collection': True,
                'alert_thresholds': {
                    'error_rate': 0.2,
                    'memory_usage': 0.9
                }
            },
            'error_handling': {
                'global_error_handler': True,
                'retry_strategy': {
                    'max_attempts': 2,
                    'backoff_factor': 1.5
                }
            }
        }
    
    @pytest.fixture
    def test_resume_profile(self):
        """测试简历档案"""
        return {
            'name': '张三',
            'skills': ['Python', '机器学习', '数据分析'],
            'experience': '3年',
            'education': '本科',
            'location_preference': ['北京', '上海'],
            'salary_expectation': 25000
        }
    
    @pytest.fixture
    def test_pipeline_config(self, test_resume_profile):
        """测试流水线配置"""
        return PipelineConfig(
            search_keywords=['Python开发', '数据分析师'],
            search_locations=['北京', '上海'],
            max_jobs_per_keyword=5,
            max_pages=2,
            resume_profile=test_resume_profile,
            decision_criteria={
                'submission_threshold': 0.7,
                'max_daily_submissions': 5
            },
            submission_config={
                'dry_run_mode': True,
                'max_submissions_per_day': 5
            }
        )
    
    @pytest.fixture
    def temp_dir(self):
        """临时目录"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    async def master_controller(self, test_config, temp_dir):
        """主控制器实例"""
        # 修改配置中的路径
        test_config['checkpoint_dir'] = str(temp_dir / 'checkpoints')
        test_config['log_dir'] = str(temp_dir / 'logs')
        
        controller = MasterController(test_config)
        yield controller
        # 清理
        if hasattr(controller, 'cleanup'):
            await controller.cleanup()


class TestMasterController:
    """主控制器测试"""
    
    @pytest.mark.asyncio
    async def test_master_controller_initialization(self, test_config):
        """测试主控制器初始化"""
        controller = MasterController(test_config)
        
        assert controller.config == test_config
        assert controller.pipeline_id.startswith('pipeline_')
        assert controller.current_stage == "initialized"
        assert isinstance(controller.data_bridge, DataBridge)
        assert isinstance(controller.job_scheduler, JobScheduler)
    
    @pytest.mark.asyncio
    async def test_pipeline_execution_mock(self, master_controller, test_pipeline_config):
        """测试流水线执行（模拟）"""
        # 模拟各个阶段的执行
        with patch.object(master_controller, '_execute_job_extraction') as mock_extraction, \
             patch.object(master_controller, '_execute_rag_processing') as mock_rag, \
             patch.object(master_controller, '_execute_resume_matching') as mock_matching, \
             patch.object(master_controller, '_execute_intelligent_decision') as mock_decision, \
             patch.object(master_controller, '_execute_auto_submission') as mock_submission:
            
            # 设置模拟返回值
            mock_extraction.return_value = {
                'success': True,
                'total_extracted': 10,
                'jobs': [{'id': f'job_{i}', 'title': f'职位{i}'} for i in range(10)]
            }
            
            mock_rag.return_value = {
                'success': True,
                'processed_count': 10,
                'processing_time': 30.5
            }
            
            mock_matching.return_value = {
                'success': True,
                'total_matches': 5,
                'matches': [{'job_id': f'job_{i}', 'score': 0.8} for i in range(5)]
            }
            
            mock_decision.return_value = {
                'success': True,
                'recommended_submissions': 3,
                'decisions': [{'job_id': f'job_{i}', 'should_submit': True} for i in range(3)]
            }
            
            mock_submission.return_value = {
                'success': True,
                'successful_submissions': 3,
                'submission_details': []
            }
            
            # 执行流水线
            result = await master_controller.run_full_pipeline(test_pipeline_config)
            
            # 验证结果
            assert result.success is True
            assert result.extraction_result['success'] is True
            assert result.rag_result['success'] is True
            assert result.matching_result['success'] is True
            assert result.decision_result['success'] is True
            assert result.submission_result['success'] is True
            
            # 验证各阶段都被调用
            mock_extraction.assert_called_once()
            mock_rag.assert_called_once()
            mock_matching.assert_called_once()
            mock_decision.assert_called_once()
            mock_submission.assert_called_once()


class TestDataBridge:
    """数据传递接口测试"""
    
    @pytest.mark.asyncio
    async def test_data_bridge_initialization(self, test_config):
        """测试数据桥接器初始化"""
        bridge = DataBridge(test_config)
        
        assert bridge.config == test_config
        assert bridge.validation_enabled is True
        assert bridge.transformation_cache_enabled is True
    
    def test_extraction_to_rag_transformation(self, test_config):
        """测试提取到RAG的数据转换"""
        bridge = DataBridge(test_config)
        
        extraction_result = {
            'success': True,
            'jobs': [
                {
                    'id': 'job_1',
                    'title': 'Python开发工程师',
                    'company': '科技公司A',
                    'location': '北京',
                    'description': '负责Python开发工作',
                    'requirements': '3年以上Python经验',
                    'salary': '20-30K',
                    'url': 'https://example.com/job1'
                }
            ]
        }
        
        rag_input = bridge.transform_extraction_to_rag(extraction_result)
        
        assert 'jobs' in rag_input
        assert 'total_count' in rag_input
        assert rag_input['total_count'] == 1
        assert len(rag_input['jobs']) == 1
        
        job = rag_input['jobs'][0]
        assert job['job_id'] == 'job_1'
        assert job['title'] == 'Python开发工程师'
        assert job['company'] == '科技公司A'
    
    def test_rag_to_matching_transformation(self, test_config):
        """测试RAG到匹配的数据转换"""
        bridge = DataBridge(test_config)
        
        rag_result = {
            'success': True,
            'processed_count': 10,
            'processing_time': 30.5,
            'success_rate': 0.9
        }
        
        matching_input = bridge.transform_rag_to_matching(rag_result)
        
        assert matching_input['processed_jobs_count'] == 10
        assert matching_input['vector_db_ready'] is True
        assert matching_input['processing_quality'] == 0.9
        assert matching_input['ready_for_matching'] is True


class TestJobScheduler:
    """作业调度器测试"""
    
    @pytest.mark.asyncio
    async def test_job_scheduler_initialization(self, test_config):
        """测试作业调度器初始化"""
        scheduler = JobScheduler(test_config)
        
        assert scheduler.config == test_config
        assert scheduler.max_concurrent == 3
        assert scheduler.batch_size == 10
        assert not scheduler.is_running
    
    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self, test_config):
        """测试调度器启动和停止"""
        scheduler = JobScheduler(test_config)
        
        # 启动调度器
        await scheduler.start()
        assert scheduler.is_running is True
        assert len(scheduler.worker_pool) > 0
        
        # 停止调度器
        await scheduler.stop()
        assert scheduler.is_running is False
        assert len(scheduler.worker_pool) == 0


class TestDecisionEngine:
    """智能决策引擎测试"""
    
    @pytest.mark.asyncio
    async def test_decision_engine_initialization(self, test_config):
        """测试决策引擎初始化"""
        engine = DecisionEngine(test_config)
        
        assert engine.config == test_config
        assert engine.learning_enabled is True
    
    @pytest.mark.asyncio
    async def test_make_submission_decisions(self, test_config):
        """测试制定投递决策"""
        engine = DecisionEngine(test_config)
        
        matching_result = {
            'success': True,
            'matches': [
                {
                    'job_id': 'job_1',
                    'job_title': 'Python开发工程师',
                    'company': '科技公司A',
                    'location': '北京',
                    'overall_score': 0.85,
                    'job_url': 'https://example.com/job1'
                },
                {
                    'job_id': 'job_2',
                    'job_title': '数据分析师',
                    'company': '科技公司B',
                    'location': '上海',
                    'overall_score': 0.65,
                    'job_url': 'https://example.com/job2'
                }
            ]
        }
        
        decision_criteria = {
            'submission_threshold': 0.7,
            'max_daily_submissions': 5
        }
        
        result = await engine.make_submission_decisions(matching_result, decision_criteria)
        
        assert result.success is True
        assert result.total_evaluated == 2
        assert result.recommended_submissions >= 1  # 至少一个分数超过阈值
        assert len(result.decisions) == 2
        
        # 检查高分职位被推荐
        high_score_decision = next(d for d in result.decisions if d.job_id == 'job_1')
        assert high_score_decision.should_submit is True
        assert high_score_decision.final_score >= 0.7


class TestAutoSubmissionEngine:
    """自动投递引擎测试"""
    
    @pytest.mark.asyncio
    async def test_submission_integration_initialization(self, test_config):
        """测试投递集成模块初始化"""
        engine = AutoSubmissionEngine(test_config)
        
        assert engine.config == test_config
        assert engine.dry_run_mode is True
        assert engine.max_submissions_per_day == 10
    
    @pytest.mark.asyncio
    async def test_submit_applications_dry_run(self, test_config):
        """测试自动投递（干运行模式）"""
        engine = AutoSubmissionEngine(test_config)
        
        decision_result = {
            'decisions': [
                {
                    'job_id': 'job_1',
                    'job_title': 'Python开发工程师',
                    'company': '科技公司A',
                    'job_url': 'https://example.com/job1',
                    'should_submit': True,
                    'submission_priority': 'high',
                    'final_score': 0.85
                }
            ]
        }
        
        result = await engine.submit_applications(decision_result)
        
        assert result.success is True
        assert result.total_attempts >= 1
        # 在干运行模式下，应该模拟成功
        assert result.successful_submissions >= 0


class TestErrorHandler:
    """错误处理器测试"""
    
    @pytest.mark.asyncio
    async def test_error_handler_initialization(self, test_config, temp_dir):
        """测试错误处理器初始化"""
        test_config['checkpoint_dir'] = str(temp_dir / 'checkpoints')
        test_config['error_log_dir'] = str(temp_dir / 'logs')
        
        handler = ErrorHandler(test_config)
        
        assert handler.config == test_config
        assert handler.global_error_handler is True
        assert handler.max_retry_attempts == 2
    
    @pytest.mark.asyncio
    async def test_handle_error(self, test_config, temp_dir):
        """测试错误处理"""
        test_config['checkpoint_dir'] = str(temp_dir / 'checkpoints')
        test_config['error_log_dir'] = str(temp_dir / 'logs')
        
        handler = ErrorHandler(test_config)
        
        # 创建一个测试错误
        test_error = ValueError("测试错误")
        context = {'pipeline_id': 'test_pipeline', 'stage': 'test_stage'}
        
        result = await handler.handle_error(test_error, context)
        
        assert result is not None
        assert hasattr(result, 'success')
        assert hasattr(result, 'strategy_used')
    
    @pytest.mark.asyncio
    async def test_checkpoint_creation_and_restoration(self, test_config, temp_dir):
        """测试检查点创建和恢复"""
        test_config['checkpoint_dir'] = str(temp_dir / 'checkpoints')
        test_config['error_log_dir'] = str(temp_dir / 'logs')
        
        handler = ErrorHandler(test_config)
        
        # 创建检查点
        test_data = {'stage': 'test', 'data': {'key': 'value'}}
        checkpoint_id = await handler.create_checkpoint('test_pipeline', 'test_stage', test_data)
        
        assert checkpoint_id != ""
        
        # 恢复检查点
        restored_checkpoint = await handler.restore_checkpoint(checkpoint_id)
        
        assert restored_checkpoint is not None
        assert restored_checkpoint.pipeline_id == 'test_pipeline'
        assert restored_checkpoint.stage == 'test_stage'
        assert restored_checkpoint.data == test_data


class TestPipelineMonitor:
    """流水线监控器测试"""
    
    @pytest.mark.asyncio
    async def test_pipeline_monitor_initialization(self, test_config):
        """测试流水线监控器初始化"""
        monitor = PipelineMonitor(test_config)
        
        assert monitor.config == test_config
        assert not monitor.is_monitoring
        assert monitor.pipeline_stats['total_pipelines_executed'] == 0
    
    @pytest.mark.asyncio
    async def test_monitor_start_stop(self, test_config):
        """测试监控器启动和停止"""
        monitor = PipelineMonitor(test_config)
        
        # 启动监控
        await monitor.start_monitoring()
        assert monitor.is_monitoring is True
        
        # 停止监控
        await monitor.stop_monitoring()
        assert monitor.is_monitoring is False
    
    def test_record_pipeline_execution(self, test_config):
        """测试记录流水线执行"""
        monitor = PipelineMonitor(test_config)
        
        # 记录成功执行
        monitor.record_pipeline_execution(success=True, execution_time=120.5)
        
        assert monitor.pipeline_stats['total_pipelines_executed'] == 1
        assert monitor.pipeline_stats['successful_pipelines'] == 1
        assert monitor.pipeline_stats['failed_pipelines'] == 0
        assert monitor.pipeline_stats['average_execution_time'] == 120.5
        
        # 记录失败执行
        monitor.record_pipeline_execution(success=False, execution_time=60.0)
        
        assert monitor.pipeline_stats['total_pipelines_executed'] == 2
        assert monitor.pipeline_stats['successful_pipelines'] == 1
        assert monitor.pipeline_stats['failed_pipelines'] == 1


class TestEndToEndIntegration:
    """端到端集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_integration_mock(self, test_config, test_pipeline_config, temp_dir):
        """测试完整流水线集成（模拟）"""
        # 设置临时目录
        test_config['checkpoint_dir'] = str(temp_dir / 'checkpoints')
        test_config['log_dir'] = str(temp_dir / 'logs')
        
        # 创建主控制器
        controller = MasterController(test_config)
        
        # 创建监控器
        monitor = PipelineMonitor(test_config)
        await monitor.start_monitoring()
        
        try:
            # 模拟执行流水线
            with patch.object(controller, '_extract_jobs_for_keyword') as mock_extract:
                mock_extract.return_value = [
                    {
                        'id': 'job_1',
                        'title': 'Python开发工程师',
                        'company': '科技公司A',
                        'location': '北京',
                        'description': '负责Python开发',
                        'requirements': '3年经验',
                        'salary': '20-30K',
                        'url': 'https://example.com/job1'
                    }
                ]
                
                # 执行流水线
                result = await controller.run_full_pipeline(test_pipeline_config)
                
                # 验证结果
                assert result is not None
                assert hasattr(result, 'success')
                assert hasattr(result, 'pipeline_id')
                
                # 记录到监控器
                monitor.record_pipeline_execution(
                    success=result.success,
                    execution_time=result.total_execution_time
                )
                
                # 验证监控统计
                stats = monitor.get_monitoring_status()
                assert stats['pipeline_stats']['total_pipelines_executed'] >= 1
        
        finally:
            # 清理
            await monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_error_recovery_integration(self, test_config, temp_dir):
        """测试错误恢复集成"""
        test_config['checkpoint_dir'] = str(temp_dir / 'checkpoints')
        test_config['error_log_dir'] = str(temp_dir / 'logs')
        
        # 创建错误处理器
        error_handler = ErrorHandler(test_config)
        
        # 创建检查点
        test_data = {'stage': 'extraction', 'progress': 50}
        checkpoint_id = await error_handler.create_checkpoint(
            'test_pipeline', 'extraction', test_data
        )
        
        # 模拟错误
        test_error = ConnectionError("网络连接失败")
        context = {'pipeline_id': 'test_pipeline', 'stage': 'extraction'}
        
        # 处理错误
        recovery_result = await error_handler.handle_error(test_error, context)
        
        # 验证恢复结果
        assert recovery_result is not None
        assert hasattr(recovery_result, 'success')
        assert hasattr(recovery_result, 'strategy_used')


# 测试配置文件
@pytest.fixture
def integration_test_config():
    """集成测试配置"""
    return {
        'integration_system': {
            'master_controller': {
                'max_concurrent_jobs': 2,
                'checkpoint_interval': 5,
                'error_retry_attempts': 1
            },
            'job_scheduler': {
                'queue_size': 50,
                'batch_size': 5,
                'max_concurrent_tasks': 2
            },
            'data_bridge': {
                'validation_enabled': True,
                'transformation_cache': False  # 测试时禁用缓存
            },
            'decision_engine': {
                'submission_threshold': 0.6,
                'max_daily_submissions': 3
            },
            'auto_submission': {
                'dry_run_mode': True,
                'max_submissions_per_day': 3,
                'submission_delay': 0.1  # 加快测试速度
            }
        },
        'monitoring': {
            'metrics_collection': True,
            'collection_interval': 1,  # 加快收集频率
            'alert_thresholds': {
                'error_rate': 0.5,
                'memory_usage': 0.95
            }
        },
        'error_handling': {
            'global_error_handler': True,
            'retry_strategy': {
                'max_attempts': 1,
                'backoff_factor': 1.0,
                'max_delay': 1
            },
            'recovery': {
                'enable_checkpoint': True,
                'auto_recovery': True
            }
        }
    }


if __name__ == '__main__':
    # 运行测试
    pytest.main([__file__, '-v'])