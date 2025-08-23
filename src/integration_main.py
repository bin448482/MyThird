"""
智能简历投递系统 - 集成主入口
提供完整的端到端集成功能
"""

import asyncio
import logging
import argparse
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from src.integration.master_controller import MasterController, PipelineConfig
from src.integration.monitoring import PipelineMonitor
from src.integration.error_handler import ErrorHandler
from src.utils.logger import setup_logger

# 设置日志
logger = logging.getLogger(__name__)

class IntegratedResumeSystem:
    """集成简历投递系统"""
    
    def __init__(self, config_path: str = "config/integration_config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # 初始化组件
        self.master_controller = MasterController(self.config)
        self.monitor = PipelineMonitor(self.config)
        self.error_handler = ErrorHandler(self.config)
        
        # 系统状态
        self.is_running = False
        self.current_pipeline = None
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"配置文件加载成功: {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"配置文件加载失败: {e}")
            # 返回默认配置
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'integration_system': {
                'master_controller': {
                    'max_concurrent_jobs': 10,
                    'checkpoint_interval': 100,
                    'error_retry_attempts': 3
                },
                'auto_submission': {
                    'dry_run_mode': True,
                    'max_submissions_per_day': 50
                }
            },
            'monitoring': {
                'metrics_collection': True,
                'alert_thresholds': {
                    'error_rate': 0.1,
                    'memory_usage': 0.8
                }
            },
            'error_handling': {
                'global_error_handler': True,
                'retry_strategy': {
                    'max_attempts': 3,
                    'backoff_factor': 2
                }
            }
        }
    
    async def start_system(self):
        """启动系统"""
        if self.is_running:
            logger.warning("系统已经在运行")
            return
        
        try:
            logger.info("启动智能简历投递系统...")
            
            # 启动监控
            await self.monitor.start_monitoring()
            
            self.is_running = True
            logger.info("系统启动成功")
            
        except Exception as e:
            logger.error(f"系统启动失败: {e}")
            await self.error_handler.handle_error(e, {'component': 'system_startup'})
            raise
    
    async def stop_system(self):
        """停止系统"""
        if not self.is_running:
            return
        
        try:
            logger.info("停止智能简历投递系统...")
            
            # 停止监控
            await self.monitor.stop_monitoring()
            
            # 清理资源
            if hasattr(self.master_controller, 'cleanup'):
                await self.master_controller.cleanup()
            
            self.is_running = False
            logger.info("系统已停止")
            
        except Exception as e:
            logger.error(f"系统停止时发生错误: {e}")
    
    async def run_pipeline(self, 
                          search_keywords: list,
                          resume_profile: Dict[str, Any],
                          search_locations: list = None,
                          max_jobs_per_keyword: int = 50,
                          max_pages: int = 5,
                          decision_criteria: Dict[str, Any] = None,
                          submission_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """运行完整流水线"""
        
        if not self.is_running:
            await self.start_system()
        
        # 创建流水线配置
        pipeline_config = PipelineConfig(
            search_keywords=search_keywords,
            search_locations=search_locations or ['北京', '上海', '深圳'],
            max_jobs_per_keyword=max_jobs_per_keyword,
            max_pages=max_pages,
            resume_profile=resume_profile,
            decision_criteria=decision_criteria or {},
            submission_config=submission_config or {}
        )
        
        try:
            logger.info(f"开始执行流水线，关键词: {search_keywords}")
            
            # 记录流水线开始
            start_time = datetime.now()
            
            # 执行流水线
            result = await self.master_controller.run_full_pipeline(pipeline_config)
            
            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 记录到监控器
            self.monitor.record_pipeline_execution(
                success=result.success,
                execution_time=execution_time
            )
            
            # 生成报告
            report = self.monitor.generate_report()
            
            logger.info(f"流水线执行完成，耗时: {execution_time:.2f}秒")
            
            return {
                'pipeline_result': result,
                'performance_report': report,
                'execution_time': execution_time,
                'monitoring_stats': self.monitor.get_monitoring_status()
            }
            
        except Exception as e:
            logger.error(f"流水线执行失败: {e}")
            
            # 错误处理
            recovery_result = await self.error_handler.handle_error(
                e, 
                {
                    'pipeline_id': getattr(result, 'pipeline_id', 'unknown'),
                    'stage': 'pipeline_execution',
                    'search_keywords': search_keywords
                }
            )
            
            # 记录失败
            execution_time = (datetime.now() - start_time).total_seconds()
            self.monitor.record_pipeline_execution(
                success=False,
                execution_time=execution_time
            )
            
            return {
                'pipeline_result': None,
                'error': str(e),
                'recovery_result': recovery_result,
                'execution_time': execution_time
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            'is_running': self.is_running,
            'current_pipeline': self.current_pipeline,
            'monitoring_status': self.monitor.get_monitoring_status() if self.is_running else None,
            'error_stats': self.error_handler.get_error_stats(),
            'config_loaded': self.config_path.exists()
        }
    
    async def run_health_check(self) -> Dict[str, Any]:
        """运行健康检查"""
        health_status = {
            'overall_health': 'healthy',
            'components': {},
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # 检查配置
            health_status['components']['config'] = {
                'status': 'healthy' if self.config else 'unhealthy',
                'details': f'Config loaded from {self.config_path}'
            }
            
            # 检查监控器
            if self.is_running:
                monitor_status = self.monitor.get_monitoring_status()
                health_status['components']['monitor'] = {
                    'status': 'healthy' if monitor_status['is_monitoring'] else 'unhealthy',
                    'details': f"Monitoring: {monitor_status['is_monitoring']}"
                }
            else:
                health_status['components']['monitor'] = {
                    'status': 'stopped',
                    'details': 'System not running'
                }
            
            # 检查错误处理器
            error_stats = self.error_handler.get_error_stats()
            error_rate = error_stats.get('error_rate', 0)
            health_status['components']['error_handler'] = {
                'status': 'healthy' if error_rate < 0.1 else 'warning',
                'details': f"Error rate: {error_rate:.2%}"
            }
            
            # 确定整体健康状态
            component_statuses = [comp['status'] for comp in health_status['components'].values()]
            if 'unhealthy' in component_statuses:
                health_status['overall_health'] = 'unhealthy'
            elif 'warning' in component_statuses:
                health_status['overall_health'] = 'warning'
            
        except Exception as e:
            health_status['overall_health'] = 'unhealthy'
            health_status['error'] = str(e)
        
        return health_status


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='智能简历投递系统')
    parser.add_argument('--config', '-c', default='config/integration_config.yaml',
                       help='配置文件路径')
    parser.add_argument('--keywords', '-k', nargs='+', required=True,
                       help='搜索关键词')
    parser.add_argument('--locations', '-l', nargs='+', 
                       default=['北京', '上海', '深圳'],
                       help='搜索地点')
    parser.add_argument('--max-jobs', '-j', type=int, default=50,
                       help='每个关键词最大职位数')
    parser.add_argument('--max-pages', '-p', type=int, default=5,
                       help='最大搜索页数')
    parser.add_argument('--dry-run', action='store_true',
                       help='干运行模式（不实际投递）')
    parser.add_argument('--health-check', action='store_true',
                       help='运行健康检查')
    parser.add_argument('--resume-file', '-r', 
                       help='简历文件路径（JSON格式）')
    
    args = parser.parse_args()
    
    # 创建系统实例
    system = IntegratedResumeSystem(args.config)
    
    # 设置日志
    setup_logger(system.config)
    
    try:
        if args.health_check:
            # 运行健康检查
            health_status = await system.run_health_check()
            print("=== 系统健康检查 ===")
            print(f"整体状态: {health_status['overall_health']}")
            for component, status in health_status['components'].items():
                print(f"{component}: {status['status']} - {status['details']}")
            return
        
        # 加载简历档案
        resume_profile = {}
        if args.resume_file:
            try:
                import json
                with open(args.resume_file, 'r', encoding='utf-8') as f:
                    resume_profile = json.load(f)
                logger.info(f"简历档案加载成功: {args.resume_file}")
            except Exception as e:
                logger.error(f"简历档案加载失败: {e}")
                resume_profile = {
                    'name': '默认用户',
                    'skills': ['Python', '数据分析'],
                    'experience': '3年',
                    'location_preference': args.locations
                }
        else:
            # 使用默认简历档案
            resume_profile = {
                'name': '求职者',
                'skills': ['Python', '机器学习', '数据分析'],
                'experience': '3年',
                'education': '本科',
                'location_preference': args.locations,
                'salary_expectation': 25000
            }
        
        # 配置投递参数
        submission_config = {
            'dry_run_mode': args.dry_run,
            'max_submissions_per_day': 20
        }
        
        # 启动系统
        await system.start_system()
        
        print("=== 智能简历投递系统 ===")
        print(f"搜索关键词: {args.keywords}")
        print(f"搜索地点: {args.locations}")
        print(f"干运行模式: {args.dry_run}")
        print("开始执行流水线...")
        
        # 运行流水线
        result = await system.run_pipeline(
            search_keywords=args.keywords,
            resume_profile=resume_profile,
            search_locations=args.locations,
            max_jobs_per_keyword=args.max_jobs,
            max_pages=args.max_pages,
            submission_config=submission_config
        )
        
        # 显示结果
        print("\n=== 执行结果 ===")
        if result.get('pipeline_result'):
            pipeline_result = result['pipeline_result']
            print(f"执行状态: {'成功' if pipeline_result.success else '失败'}")
            print(f"执行时间: {result['execution_time']:.2f}秒")
            
            if pipeline_result.success:
                print(f"提取职位: {pipeline_result.extraction_result.get('total_extracted', 0)}")
                print(f"RAG处理: {pipeline_result.rag_result.get('processed_count', 0)}")
                print(f"匹配结果: {pipeline_result.matching_result.get('total_matches', 0)}")
                print(f"推荐投递: {pipeline_result.decision_result.get('recommended_submissions', 0)}")
                print(f"成功投递: {pipeline_result.submission_result.get('successful_submissions', 0)}")
        else:
            print(f"执行失败: {result.get('error', '未知错误')}")
        
        # 显示监控统计
        monitoring_stats = result.get('monitoring_stats', {})
        if monitoring_stats:
            print(f"\n=== 监控统计 ===")
            pipeline_stats = monitoring_stats.get('pipeline_stats', {})
            print(f"总执行次数: {pipeline_stats.get('total_pipelines_executed', 0)}")
            print(f"成功次数: {pipeline_stats.get('successful_pipelines', 0)}")
            print(f"失败次数: {pipeline_stats.get('failed_pipelines', 0)}")
            print(f"平均执行时间: {pipeline_stats.get('average_execution_time', 0):.2f}秒")
        
    except KeyboardInterrupt:
        logger.info("用户中断执行")
    except Exception as e:
        logger.error(f"系统执行错误: {e}")
    finally:
        # 停止系统
        await system.stop_system()
        print("\n系统已停止")


if __name__ == '__main__':
    asyncio.run(main())