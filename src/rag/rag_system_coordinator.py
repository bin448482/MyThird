"""
RAG系统协调器

统一管理RAG系统各组件，协调数据流和处理流程，提供统一的API接口
集成性能优化和错误处理功能
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Iterator
from pathlib import Path

from .database_job_reader import DatabaseJobReader
from .optimized_job_processor import OptimizedJobProcessor
from .vector_manager import ChromaDBManager
from .document_creator import DocumentCreator
from .performance_optimizer import create_performance_optimizer, performance_monitor
from .error_handler import create_error_handler, with_error_handling
from ..core.exceptions import RAGSystemError

logger = logging.getLogger(__name__)


class RAGSystemCoordinator:
    """RAG系统协调器"""
    
    def __init__(self, config: Dict):
        """
        初始化RAG系统协调器
        
        Args:
            config: 系统配置字典
        """
        self.config = config
        self.rag_config = config.get('rag_system', {})
        
        # 初始化性能优化器和错误处理器
        self._initialize_optimization_components()
        
        # 初始化各个组件
        self._initialize_components()
        
        # 系统状态
        self.is_initialized = False
        self.processing_stats = {
            'total_processed': 0,
            'total_errors': 0,
            'last_processing_time': None,
            'processing_rate': 0.0
        }
        
        logger.info("RAG系统协调器初始化完成")
    
    def _initialize_optimization_components(self):
        """初始化性能优化和错误处理组件"""
        try:
            # 性能优化器配置
            perf_config = self.rag_config.get('performance_optimization', {})
            self.performance_optimizer = create_performance_optimizer(perf_config)
            
            # 错误处理器配置
            error_config = self.rag_config.get('error_handling', {})
            self.error_handler = create_error_handler(error_config)
            
            logger.info("性能优化和错误处理组件初始化完成")
            
        except Exception as e:
            logger.error(f"优化组件初始化失败: {e}")
            # 创建默认组件以确保系统可以运行
            self.performance_optimizer = create_performance_optimizer()
            self.error_handler = create_error_handler()
    
    def _initialize_components(self):
        """初始化系统组件"""
        try:
            # 数据库读取器
            db_config = self.rag_config.get('database', {})
            db_path = db_config.get('path', './data/jobs.db')
            self.db_reader = DatabaseJobReader(db_path, db_config)
            
            # 职位处理器
            llm_config = self.rag_config.get('llm', {})
            processing_config = self.rag_config.get('processing', {})
            self.job_processor = OptimizedJobProcessor(llm_config, processing_config)
            
            # 向量管理器 - 需要传递LLM配置用于压缩检索器
            vector_config = self.rag_config.get('vector_db', {})
            vector_config['llm'] = self.rag_config.get('llm', {})  # 添加LLM配置
            self.vector_manager = ChromaDBManager(vector_config)
            
            # 文档创建器
            doc_config = self.rag_config.get('documents', {})
            self.document_creator = DocumentCreator(doc_config)
            
            logger.info("RAG系统组件初始化完成")
            
        except Exception as e:
            logger.error(f"RAG系统组件初始化失败: {e}")
            raise RAGSystemError(f"组件初始化失败: {e}")
    
    @with_error_handling("system_initialization", enable_recovery=True)
    @performance_monitor("system_initialization")
    def initialize_system(self) -> bool:
        """
        初始化RAG系统
        
        Returns:
            是否初始化成功
        """
        try:
            # 检查数据库连接
            stats = self.db_reader.get_rag_processing_stats()
            logger.info(f"数据库连接正常，总职位数: {stats.get('total', 0)}")
            
            # 检查向量数据库状态
            vector_stats = self.vector_manager.get_collection_stats()
            logger.info(f"向量数据库状态: {vector_stats}")
            
            self.is_initialized = True
            logger.info("RAG系统初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"RAG系统初始化失败: {e}")
            self.is_initialized = False
            return False
    
    @with_error_handling("batch_import", enable_recovery=True)
    @performance_monitor("batch_import")
    async def import_database_jobs(self,
                                 batch_size: int = 50,
                                 force_reprocess: bool = False,
                                 max_jobs: int = None) -> Dict[str, Any]:
        """
        从数据库导入职位数据到向量数据库（优化版本）
        
        Args:
            batch_size: 批处理大小
            force_reprocess: 是否强制重新处理
            max_jobs: 最大处理职位数量
            
        Returns:
            处理结果统计
        """
        if not self.is_initialized:
            raise RAGSystemError("系统未初始化，请先调用initialize_system()")
        
        logger.info(f"开始导入数据库职位数据 (batch_size: {batch_size}, force_reprocess: {force_reprocess})")
        
        start_time = datetime.now()
        total_imported = 0
        total_skipped = 0
        total_errors = 0
        
        try:
            # 获取处理统计
            initial_stats = self.db_reader.get_rag_processing_stats()
            logger.info(f"初始统计: 总计 {initial_stats['total']} 个职位，已处理 {initial_stats['processed']} 个")
            
            # 选择数据源
            if force_reprocess:
                data_iterator = self.db_reader.read_jobs_by_batch(batch_size)
                logger.info("使用强制重处理模式")
            else:
                data_iterator = self.db_reader.get_unprocessed_jobs(batch_size)
                logger.info("使用增量处理模式")
            
            # 收集所有待处理的职位
            all_jobs = []
            processed_count = 0
            for batch in data_iterator:
                if not batch:
                    break
                
                # 检查是否达到最大处理数量
                if max_jobs and processed_count >= max_jobs:
                    logger.info(f"达到最大处理数量限制: {max_jobs}")
                    break
                
                all_jobs.extend(batch)
                processed_count += len(batch)
                
                # 如果是迭代器模式且没有更多数据，退出
                if not force_reprocess and len(batch) < batch_size:
                    break
            
            if not all_jobs:
                logger.info("没有需要处理的职位")
                return {
                    'total_imported': 0,
                    'total_skipped': 0,
                    'total_errors': 0,
                    'processing_time': 0,
                    'processing_rate': 0,
                    'success_rate': 1.0,
                    'initial_stats': initial_stats,
                    'final_stats': initial_stats
                }
            
            # 使用性能优化器进行批量处理
            def create_cache_key(job_data):
                return f"job_{job_data.get('job_id', 'unknown')}"
            
            results = await self.performance_optimizer.process_items_optimized(
                items=all_jobs,
                process_func=self._process_single_job_optimized,
                use_cache=True,
                cache_key_func=create_cache_key,
                force_reprocess=force_reprocess
            )
            
            # 统计结果
            for result in results:
                if result is None:
                    total_errors += 1
                elif result == 'skipped':
                    total_skipped += 1
                elif result == 'imported':
                    total_imported += 1
                else:
                    total_errors += 1
            
            # 计算处理时间和速率
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            processing_rate = total_imported / processing_time if processing_time > 0 else 0
            
            # 更新系统统计
            self.processing_stats.update({
                'total_processed': self.processing_stats['total_processed'] + total_imported,
                'total_errors': self.processing_stats['total_errors'] + total_errors,
                'last_processing_time': end_time,
                'processing_rate': processing_rate
            })
            
            # 获取最终统计
            final_stats = self.db_reader.get_rag_processing_stats()
            
            result = {
                'total_imported': total_imported,
                'total_skipped': total_skipped,
                'total_errors': total_errors,
                'processing_time': processing_time,
                'processing_rate': processing_rate,
                'success_rate': (total_imported / (total_imported + total_errors)) if (total_imported + total_errors) > 0 else 0,
                'initial_stats': initial_stats,
                'final_stats': final_stats,
                'performance_report': self.performance_optimizer.get_performance_report()
            }
            
            logger.info(f"数据导入完成: 导入 {total_imported}, 跳过 {total_skipped}, 错误 {total_errors}, 用时 {processing_time:.1f}s")
            return result
            
        except Exception as e:
            logger.error(f"数据导入失败: {e}")
            raise RAGSystemError(f"数据导入失败: {e}")
    
    async def _process_job_batch(self, batch: List[Dict], force_reprocess: bool = False) -> Dict[str, int]:
        """
        处理职位批次
        
        Args:
            batch: 职位数据批次
            force_reprocess: 是否强制重处理
            
        Returns:
            批次处理结果
        """
        imported = 0
        skipped = 0
        errors = 0
        
        for job_data in batch:
            try:
                # 检查是否需要跳过
                if not force_reprocess and job_data.get('rag_processed'):
                    skipped += 1
                    continue
                
                # 处理单个职位
                success = await self.process_single_job(job_data)
                if success:
                    imported += 1
                else:
                    errors += 1
                    
            except Exception as e:
                logger.error(f"处理职位失败 {job_data.get('job_id', 'unknown')}: {e}")
                errors += 1
        
        return {
            'imported': imported,
            'skipped': skipped,
            'errors': errors
        }
    
    @with_error_handling("single_job_processing", enable_recovery=True)
    async def process_single_job(self, job_data: Dict) -> bool:
        """
        处理单个职位数据
        
        Args:
            job_data: 职位数据
            
        Returns:
            是否处理成功
        """
        try:
            job_id = job_data.get('job_id')
            if not job_id:
                logger.warning("职位数据缺少job_id")
                return False
            
            # 1. 结构化处理
            job_structure = await self.job_processor.process_database_job(job_data)
            
            # 2. 验证处理结果
            if not self.job_processor.validate_job_structure(job_structure):
                logger.warning(f"职位结构验证失败: {job_id}")
                # 仍然标记为已处理，避免重复处理
                self.db_reader.mark_job_as_processed(job_id, 0)
                return False
            
            # 3. 创建文档
            documents = self.job_processor.create_documents(
                job_structure,
                job_id=job_id,
                job_url=job_data.get('url')
            )
            
            # 4. 向量化存储
            doc_ids = await self.vector_manager.add_job_documents_async(documents, job_id)
            
            # 5. 计算语义评分（基于文档数量和内容质量）
            semantic_score = self._calculate_semantic_score(job_structure, documents)
            
            # 6. 准备结构化数据JSON
            import json
            structured_data_dict = {
                'job_title': job_structure.job_title,
                'company': job_structure.company,
                'responsibilities': job_structure.responsibilities,
                'requirements': job_structure.requirements,
                'skills': job_structure.skills,
                'education': job_structure.education,
                'experience': job_structure.experience,
                'salary_min': job_structure.salary_min,
                'salary_max': job_structure.salary_max,
                'location': job_structure.location,
                'company_size': job_structure.company_size
            }
            structured_data_json = json.dumps(structured_data_dict, ensure_ascii=False)
            
            # 7. 更新处理状态
            vector_id = doc_ids[0] if doc_ids else None
            self.db_reader.mark_job_as_processed(
                job_id,
                doc_count=len(documents),
                vector_id=vector_id,
                semantic_score=semantic_score,
                structured_data=structured_data_json
            )
            
            logger.debug(f"成功处理职位: {job_id} - {job_structure.job_title}")
            return True
            
        except Exception as e:
            logger.error(f"处理职位失败: {e}")
            return False
    
    async def _process_single_job_optimized(self, job_data: Dict, force_reprocess: bool = False) -> str:
        """
        优化的单个职位处理方法（用于批量处理）
        
        Args:
            job_data: 职位数据
            force_reprocess: 是否强制重新处理
            
        Returns:
            处理结果状态: 'imported', 'skipped', 'error'
        """
        try:
            # 检查是否需要跳过
            if not force_reprocess and job_data.get('rag_processed'):
                return 'skipped'
            
            # 处理职位
            success = await self.process_single_job(job_data)
            return 'imported' if success else 'error'
            
        except Exception as e:
            logger.error(f"优化处理职位失败 {job_data.get('job_id', 'unknown')}: {e}")
            return 'error'
    
    def _calculate_semantic_score(self, job_structure, documents: List) -> float:
        """
        计算语义评分
        
        Args:
            job_structure: 职位结构
            documents: 文档列表
            
        Returns:
            语义评分 (0-1)
        """
        score = 0.0
        
        # 基于内容完整性评分
        if job_structure.responsibilities:
            score += 0.3
        if job_structure.requirements:
            score += 0.3
        if job_structure.skills:
            score += 0.2
        if job_structure.salary_min or job_structure.salary_max:
            score += 0.1
        if job_structure.location:
            score += 0.1
        
        # 基于文档数量评分
        doc_count_score = min(len(documents) / 5.0, 1.0)  # 最多5个文档为满分
        score = (score + doc_count_score) / 2
        
        return round(score, 3)
    
    def get_processing_progress(self) -> Dict[str, Any]:
        """
        获取RAG处理进度
        
        Returns:
            处理进度信息
        """
        try:
            db_stats = self.db_reader.get_rag_processing_stats()
            vector_stats = self.vector_manager.get_collection_stats()
            
            return {
                'database_stats': db_stats,
                'vector_stats': vector_stats,
                'system_stats': self.processing_stats,
                'is_initialized': self.is_initialized,
                'progress_percentage': (db_stats.get('processed', 0) / db_stats.get('total', 1)) * 100
            }
            
        except Exception as e:
            logger.error(f"获取处理进度失败: {e}")
            return {}
    
    def resume_processing(self, batch_size: int = 50) -> Dict[str, int]:
        """
        恢复中断的RAG处理
        
        Args:
            batch_size: 批处理大小
            
        Returns:
            恢复处理结果
        """
        logger.info("恢复中断的RAG处理")
        return asyncio.run(self.import_database_jobs(batch_size=batch_size, force_reprocess=False))
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        获取增强的系统状态信息
        
        Returns:
            系统状态信息
        """
        try:
            # 基础状态信息
            status = {
                'is_initialized': self.is_initialized,
                'components': {
                    'db_reader': self.db_reader is not None,
                    'job_processor': self.job_processor is not None,
                    'vector_manager': self.vector_manager is not None,
                    'document_creator': self.document_creator is not None,
                    'performance_optimizer': self.performance_optimizer is not None,
                    'error_handler': self.error_handler is not None
                },
                'processing_stats': self.processing_stats,
                'config': {
                    'batch_size': self.rag_config.get('processing', {}).get('batch_size', 50),
                    'vector_db_path': self.rag_config.get('vector_db', {}).get('persist_directory', './chroma_db'),
                    'llm_provider': self.rag_config.get('llm', {}).get('provider', 'zhipu')
                }
            }
            
            # 添加性能报告
            if hasattr(self, 'performance_optimizer') and self.performance_optimizer:
                status['performance_report'] = self.performance_optimizer.get_performance_report()
            
            # 添加错误摘要
            if hasattr(self, 'error_handler') and self.error_handler:
                status['error_summary'] = self.error_handler.get_error_summary()
            
            return status
            
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {'error': str(e)}
    
    def reset_processing_status(self, job_ids: List[str] = None) -> int:
        """
        重置处理状态
        
        Args:
            job_ids: 要重置的职位ID列表
            
        Returns:
            重置的记录数
        """
        try:
            reset_count = self.db_reader.reset_rag_processing_status(job_ids)
            logger.info(f"重置了 {reset_count} 个职位的处理状态")
            return reset_count
            
        except Exception as e:
            logger.error(f"重置处理状态失败: {e}")
            return 0
    
    def cleanup_system(self):
        """清理系统资源"""
        try:
            # 清理向量管理器
            if hasattr(self.vector_manager, 'cleanup'):
                self.vector_manager.cleanup()
            
            # 清理性能优化器
            if hasattr(self, 'performance_optimizer') and self.performance_optimizer:
                self.performance_optimizer.cleanup()
            
            # 重置性能指标
            if hasattr(self, 'performance_optimizer') and self.performance_optimizer:
                self.performance_optimizer.reset_performance_metrics()
            
            logger.info("RAG系统资源清理完成")
            
        except Exception as e:
            logger.error(f"系统资源清理失败: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        获取性能指标
        
        Returns:
            性能指标信息
        """
        try:
            if hasattr(self, 'performance_optimizer') and self.performance_optimizer:
                return self.performance_optimizer.get_performance_report()
            else:
                return {'error': '性能优化器未初始化'}
        except Exception as e:
            logger.error(f"获取性能指标失败: {e}")
            return {'error': str(e)}
    
    def get_error_report(self) -> Dict[str, Any]:
        """
        获取错误报告
        
        Returns:
            错误报告信息
        """
        try:
            if hasattr(self, 'error_handler') and self.error_handler:
                return self.error_handler.get_error_summary()
            else:
                return {'error': '错误处理器未初始化'}
        except Exception as e:
            logger.error(f"获取错误报告失败: {e}")
            return {'error': str(e)}
    
    def optimize_system_performance(self) -> Dict[str, Any]:
        """
        优化系统性能
        
        Returns:
            优化结果
        """
        try:
            optimization_results = {
                'timestamp': datetime.now().isoformat(),
                'actions_taken': []
            }
            
            # 内存优化
            if hasattr(self, 'performance_optimizer') and self.performance_optimizer:
                memory_manager = self.performance_optimizer.memory_manager
                memory_optimization = memory_manager.optimize_memory_usage()
                optimization_results['actions_taken'].append({
                    'action': 'memory_optimization',
                    'results': memory_optimization
                })
            
            # 缓存清理
            if hasattr(self, 'performance_optimizer') and self.performance_optimizer:
                cache_stats_before = self.performance_optimizer.cache_manager.get_stats()
                self.performance_optimizer.cache_manager.clear()
                cache_stats_after = self.performance_optimizer.cache_manager.get_stats()
                
                optimization_results['actions_taken'].append({
                    'action': 'cache_cleanup',
                    'before': cache_stats_before,
                    'after': cache_stats_after
                })
            
            logger.info("系统性能优化完成")
            return optimization_results
            
        except Exception as e:
            logger.error(f"系统性能优化失败: {e}")
            return {'error': str(e)}