"""
RAG数据抽取和导入流水线

完整的数据处理流水线，从数据库读取职位数据，进行RAG处理，并导入到向量数据库
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
import json

from .rag_system_coordinator import RAGSystemCoordinator
from ..core.exceptions import RAGSystemError, DataStorageError

logger = logging.getLogger(__name__)


class RAGDataPipeline:
    """RAG数据处理流水线"""
    
    def __init__(self, config: Dict, progress_callback: Optional[Callable] = None):
        """
        初始化数据流水线
        
        Args:
            config: 系统配置
            progress_callback: 进度回调函数
        """
        self.config = config
        self.progress_callback = progress_callback
        
        # 初始化RAG系统协调器
        self.coordinator = RAGSystemCoordinator(config)
        
        # 流水线状态
        self.pipeline_stats = {
            'start_time': None,
            'end_time': None,
            'total_jobs': 0,
            'processed_jobs': 0,
            'failed_jobs': 0,
            'skipped_jobs': 0,
            'processing_rate': 0.0,
            'current_batch': 0,
            'total_batches': 0,
            'status': 'initialized'
        }
        
        logger.info("RAG数据流水线初始化完成")
    
    async def run_full_pipeline(self, 
                              batch_size: int = 50,
                              max_jobs: int = None,
                              force_reprocess: bool = False,
                              save_progress: bool = True) -> Dict[str, Any]:
        """
        运行完整的RAG数据流水线
        
        Args:
            batch_size: 批处理大小
            max_jobs: 最大处理职位数量
            force_reprocess: 是否强制重新处理
            save_progress: 是否保存进度
            
        Returns:
            处理结果统计
        """
        logger.info("🚀 开始运行RAG数据流水线")
        
        try:
            # 1. 初始化系统
            await self._initialize_pipeline()
            
            # 2. 预处理检查
            pre_check_result = await self._pre_processing_check()
            if not pre_check_result['can_proceed']:
                raise RAGSystemError(f"预处理检查失败: {pre_check_result['reason']}")
            
            # 3. 执行数据导入
            import_result = await self._execute_data_import(
                batch_size=batch_size,
                max_jobs=max_jobs,
                force_reprocess=force_reprocess
            )
            
            # 4. 后处理验证
            validation_result = await self._post_processing_validation()
            
            # 5. 保存处理结果
            if save_progress:
                await self._save_pipeline_results(import_result, validation_result)
            
            # 6. 生成最终报告
            final_report = self._generate_final_report(import_result, validation_result)
            
            logger.info("✅ RAG数据流水线执行完成")
            return final_report
            
        except Exception as e:
            logger.error(f"❌ RAG数据流水线执行失败: {e}")
            self.pipeline_stats['status'] = 'failed'
            self.pipeline_stats['error'] = str(e)
            raise RAGSystemError(f"流水线执行失败: {e}")
        
        finally:
            # 清理资源
            self._cleanup_pipeline()
    
    async def _initialize_pipeline(self):
        """初始化流水线"""
        logger.info("🔧 初始化RAG流水线...")
        
        self.pipeline_stats['start_time'] = datetime.now()
        self.pipeline_stats['status'] = 'initializing'
        
        # 初始化RAG系统
        if not self.coordinator.initialize_system():
            raise RAGSystemError("RAG系统初始化失败")
        
        # 获取初始统计
        initial_progress = self.coordinator.get_processing_progress()
        db_stats = initial_progress.get('database_stats', {})
        
        self.pipeline_stats.update({
            'total_jobs': db_stats.get('total', 0),
            'processed_jobs': db_stats.get('processed', 0),
            'status': 'initialized'
        })
        
        logger.info(f"✅ 流水线初始化完成，总职位数: {self.pipeline_stats['total_jobs']}")
        
        # 调用进度回调
        if self.progress_callback:
            self.progress_callback('initialized', self.pipeline_stats)
    
    async def _pre_processing_check(self) -> Dict[str, Any]:
        """预处理检查"""
        logger.info("🔍 执行预处理检查...")
        
        check_result = {
            'can_proceed': True,
            'reason': '',
            'warnings': [],
            'recommendations': []
        }
        
        try:
            # 检查数据库连接
            db_stats = self.coordinator.db_reader.get_rag_processing_stats()
            if db_stats.get('total', 0) == 0:
                check_result['can_proceed'] = False
                check_result['reason'] = '数据库中没有职位数据'
                return check_result
            
            # 检查向量数据库状态
            vector_stats = self.coordinator.vector_manager.get_collection_stats()
            if vector_stats.get('document_count', 0) > 10000:
                check_result['warnings'].append('向量数据库文档数量较多，建议定期清理')
            
            # 检查未处理职位数量
            unprocessed_count = db_stats.get('unprocessed', 0)
            if unprocessed_count == 0:
                check_result['warnings'].append('没有未处理的职位，可能不需要运行流水线')
            
            # 检查系统资源
            import psutil
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > 80:
                check_result['warnings'].append(f'系统内存使用率较高: {memory_percent}%')
                check_result['recommendations'].append('建议减小批处理大小')
            
            logger.info(f"✅ 预处理检查完成，可以继续: {check_result['can_proceed']}")
            return check_result
            
        except Exception as e:
            logger.error(f"预处理检查失败: {e}")
            check_result['can_proceed'] = False
            check_result['reason'] = f'预处理检查异常: {e}'
            return check_result
    
    async def _execute_data_import(self, 
                                 batch_size: int,
                                 max_jobs: int = None,
                                 force_reprocess: bool = False) -> Dict[str, Any]:
        """执行数据导入"""
        logger.info("📥 开始执行数据导入...")
        
        self.pipeline_stats['status'] = 'processing'
        
        # 使用协调器执行导入
        import_result = await self.coordinator.import_database_jobs(
            batch_size=batch_size,
            max_jobs=max_jobs,
            force_reprocess=force_reprocess
        )
        
        # 更新流水线统计
        self.pipeline_stats.update({
            'processed_jobs': import_result.get('total_imported', 0),
            'failed_jobs': import_result.get('total_errors', 0),
            'skipped_jobs': import_result.get('total_skipped', 0),
            'processing_rate': import_result.get('processing_rate', 0.0)
        })
        
        logger.info(f"✅ 数据导入完成，处理 {import_result.get('total_imported', 0)} 个职位")
        
        # 调用进度回调
        if self.progress_callback:
            self.progress_callback('processing_complete', self.pipeline_stats)
        
        return import_result
    
    async def _post_processing_validation(self) -> Dict[str, Any]:
        """后处理验证"""
        logger.info("✅ 执行后处理验证...")
        
        validation_result = {
            'database_consistency': True,
            'vector_store_integrity': True,
            'data_quality_score': 0.0,
            'issues': [],
            'recommendations': []
        }
        
        try:
            # 验证数据库一致性
            db_stats = self.coordinator.db_reader.get_rag_processing_stats()
            vector_stats = self.coordinator.vector_manager.get_collection_stats()
            
            # 检查处理状态一致性
            processed_count = db_stats.get('processed', 0)
            vector_count = vector_stats.get('document_count', 0)
            
            if processed_count > 0 and vector_count == 0:
                validation_result['vector_store_integrity'] = False
                validation_result['issues'].append('数据库显示已处理职位，但向量数据库为空')
            
            # 计算数据质量评分
            total_jobs = db_stats.get('total', 1)
            success_rate = processed_count / total_jobs
            error_rate = self.pipeline_stats['failed_jobs'] / max(total_jobs, 1)
            
            validation_result['data_quality_score'] = max(0, success_rate - error_rate * 0.5)
            
            # 生成建议
            if validation_result['data_quality_score'] < 0.8:
                validation_result['recommendations'].append('数据质量较低，建议检查处理逻辑')
            
            if error_rate > 0.1:
                validation_result['recommendations'].append('错误率较高，建议检查数据源质量')
            
            logger.info(f"✅ 后处理验证完成，数据质量评分: {validation_result['data_quality_score']:.2f}")
            return validation_result
            
        except Exception as e:
            logger.error(f"后处理验证失败: {e}")
            validation_result['issues'].append(f'验证过程异常: {e}')
            return validation_result
    
    async def _save_pipeline_results(self, import_result: Dict, validation_result: Dict):
        """保存流水线结果"""
        logger.info("💾 保存流水线结果...")
        
        try:
            # 创建结果目录
            results_dir = Path('./pipeline_results')
            results_dir.mkdir(exist_ok=True)
            
            # 生成结果文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            result_file = results_dir / f'rag_pipeline_result_{timestamp}.json'
            
            # 准备结果数据
            pipeline_result = {
                'pipeline_info': {
                    'timestamp': timestamp,
                    'config': self.config.get('rag_system', {}),
                    'pipeline_stats': self.pipeline_stats
                },
                'import_result': import_result,
                'validation_result': validation_result,
                'system_status': self.coordinator.get_system_status()
            }
            
            # 保存到文件
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(pipeline_result, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"✅ 流水线结果已保存到: {result_file}")
            
        except Exception as e:
            logger.error(f"保存流水线结果失败: {e}")
            raise DataStorageError(f"保存结果失败: {e}")
    
    def _generate_final_report(self, import_result: Dict, validation_result: Dict) -> Dict[str, Any]:
        """生成最终报告"""
        logger.info("📊 生成最终报告...")
        
        # 计算执行时间
        self.pipeline_stats['end_time'] = datetime.now()
        execution_time = (self.pipeline_stats['end_time'] - self.pipeline_stats['start_time']).total_seconds()
        
        # 生成报告
        final_report = {
            'execution_summary': {
                'status': 'completed',
                'execution_time': execution_time,
                'start_time': self.pipeline_stats['start_time'],
                'end_time': self.pipeline_stats['end_time']
            },
            'processing_statistics': {
                'total_jobs': self.pipeline_stats['total_jobs'],
                'processed_jobs': self.pipeline_stats['processed_jobs'],
                'failed_jobs': self.pipeline_stats['failed_jobs'],
                'skipped_jobs': self.pipeline_stats['skipped_jobs'],
                'success_rate': (self.pipeline_stats['processed_jobs'] / max(self.pipeline_stats['total_jobs'], 1)) * 100,
                'processing_rate': import_result.get('processing_rate', 0.0)
            },
            'data_quality': {
                'quality_score': validation_result.get('data_quality_score', 0.0),
                'database_consistency': validation_result.get('database_consistency', True),
                'vector_store_integrity': validation_result.get('vector_store_integrity', True)
            },
            'recommendations': validation_result.get('recommendations', []),
            'issues': validation_result.get('issues', []),
            'detailed_results': {
                'import_result': import_result,
                'validation_result': validation_result
            }
        }
        
        # 更新流水线状态
        self.pipeline_stats['status'] = 'completed'
        
        logger.info(f"✅ 最终报告生成完成，成功率: {final_report['processing_statistics']['success_rate']:.1f}%")
        return final_report
    
    def _cleanup_pipeline(self):
        """清理流水线资源"""
        try:
            self.coordinator.cleanup_system()
            logger.info("✅ 流水线资源清理完成")
        except Exception as e:
            logger.error(f"流水线资源清理失败: {e}")
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """获取流水线状态"""
        return {
            'pipeline_stats': self.pipeline_stats,
            'system_status': self.coordinator.get_system_status() if hasattr(self, 'coordinator') else {},
            'processing_progress': self.coordinator.get_processing_progress() if hasattr(self, 'coordinator') else {}
        }
    
    async def resume_pipeline(self, batch_size: int = 50) -> Dict[str, Any]:
        """恢复中断的流水线"""
        logger.info("🔄 恢复中断的RAG流水线...")
        
        return await self.run_full_pipeline(
            batch_size=batch_size,
            force_reprocess=False,
            save_progress=True
        )
    
    def estimate_processing_time(self, batch_size: int = 50) -> Dict[str, Any]:
        """估算处理时间"""
        try:
            # 获取未处理职位数量
            db_stats = self.coordinator.db_reader.get_rag_processing_stats()
            unprocessed_count = db_stats.get('unprocessed', 0)
            
            # 基于历史处理速率估算
            historical_rate = self.coordinator.processing_stats.get('processing_rate', 1.0)
            if historical_rate <= 0:
                historical_rate = 1.0  # 默认每秒1个职位
            
            estimated_seconds = unprocessed_count / historical_rate
            estimated_batches = (unprocessed_count + batch_size - 1) // batch_size
            
            return {
                'unprocessed_jobs': unprocessed_count,
                'estimated_time_seconds': estimated_seconds,
                'estimated_time_minutes': estimated_seconds / 60,
                'estimated_batches': estimated_batches,
                'batch_size': batch_size,
                'processing_rate': historical_rate
            }
            
        except Exception as e:
            logger.error(f"估算处理时间失败: {e}")
            return {'error': str(e)}


def create_progress_callback():
    """创建进度回调函数"""
    def progress_callback(stage: str, stats: Dict):
        timestamp = datetime.now().strftime('%H:%M:%S')
        if stage == 'initialized':
            print(f"[{timestamp}] 🔧 流水线初始化完成，总职位数: {stats.get('total_jobs', 0)}")
        elif stage == 'processing_complete':
            processed = stats.get('processed_jobs', 0)
            failed = stats.get('failed_jobs', 0)
            rate = stats.get('processing_rate', 0)
            print(f"[{timestamp}] ✅ 处理完成: 成功 {processed}, 失败 {failed}, 速率 {rate:.2f}/s")
        else:
            print(f"[{timestamp}] 📊 {stage}: {stats}")
    
    return progress_callback