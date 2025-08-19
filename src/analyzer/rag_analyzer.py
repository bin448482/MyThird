"""
RAG智能分析器

整合所有RAG组件，提供统一的职位信息智能分析接口。
"""

from typing import Dict, List, Any, Optional
import logging
import asyncio
from datetime import datetime
import json

from ..rag.job_processor import LangChainJobProcessor, JobStructure
from ..rag.vector_manager import ChromaDBManager
from ..rag.rag_chain import JobRAGSystem
from ..rag.document_creator import DocumentCreator
from ..rag.semantic_search import SemanticSearchEngine

logger = logging.getLogger(__name__)


class RAGAnalyzer:
    """RAG智能分析器"""
    
    def __init__(self, config: Dict = None):
        """
        初始化RAG分析器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        
        # 初始化各个组件
        self._init_components()
        
        # 分析统计
        self.stats = {
            'processed_jobs': 0,
            'created_documents': 0,
            'analysis_sessions': 0,
            'start_time': datetime.now().isoformat()
        }
        
        logger.info("RAG智能分析器初始化完成")
    
    def _init_components(self):
        """初始化RAG组件"""
        
        # 1. 初始化职位处理器
        processor_config = self.config.get('job_processor', {})
        self.job_processor = LangChainJobProcessor(
            llm_model=processor_config.get('llm_model', 'gpt-3.5-turbo'),
            config=processor_config
        )
        
        # 2. 初始化向量存储管理器
        vector_config = self.config.get('vectorstore', {})
        self.vector_manager = ChromaDBManager(config=vector_config)
        
        # 3. 初始化RAG问答系统
        rag_config = self.config.get('rag_chain', {})
        self.rag_system = JobRAGSystem(
            vectorstore_manager=self.vector_manager,
            config=rag_config
        )
        
        # 4. 初始化文档创建器
        doc_config = self.config.get('document_creator', {})
        self.document_creator = DocumentCreator(config=doc_config)
        
        # 5. 初始化语义搜索引擎
        search_config = self.config.get('semantic_search', {})
        self.search_engine = SemanticSearchEngine(
            vector_manager=self.vector_manager,
            config=search_config
        )
        
        logger.info("所有RAG组件初始化完成")
    
    async def analyze_job(self, job_data: Dict, job_id: str = None, 
                         source_url: str = None) -> Dict[str, Any]:
        """
        分析单个职位
        
        Args:
            job_data: 职位数据
            job_id: 职位ID
            source_url: 来源URL
            
        Returns:
            Dict: 分析结果
        """
        try:
            analysis_start = datetime.now()
            
            # 1. 结构化提取职位信息
            logger.info(f"开始分析职位: {job_data.get('title', 'Unknown')}")
            job_structure = await self.job_processor.process_job_data(job_data)
            
            # 2. 创建文档
            documents = self.document_creator.create_job_documents(
                job_structure=job_structure,
                job_id=job_id,
                source_url=source_url
            )
            
            # 3. 存储到向量数据库
            doc_ids = self.vector_manager.add_job_documents(
                documents=documents,
                job_id=job_id
            )
            
            # 4. 计算分析时间
            analysis_time = (datetime.now() - analysis_start).total_seconds()
            
            # 5. 更新统计信息
            self.stats['processed_jobs'] += 1
            self.stats['created_documents'] += len(documents)
            
            # 6. 构建分析结果
            analysis_result = {
                'job_id': job_id,
                'job_structure': job_structure.dict(),
                'document_count': len(documents),
                'document_ids': doc_ids,
                'analysis_time': analysis_time,
                'success': True,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"职位分析完成: {job_structure.job_title}, 耗时: {analysis_time:.2f}秒")
            return analysis_result
            
        except Exception as e:
            logger.error(f"职位分析失败: {e}")
            return {
                'job_id': job_id,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def batch_analyze_jobs(self, jobs_data: List[Dict], 
                               batch_size: int = 5) -> List[Dict[str, Any]]:
        """
        批量分析职位
        
        Args:
            jobs_data: 职位数据列表
            batch_size: 批处理大小
            
        Returns:
            List[Dict]: 分析结果列表
        """
        results = []
        total_jobs = len(jobs_data)
        
        logger.info(f"开始批量分析 {total_jobs} 个职位，批处理大小: {batch_size}")
        
        # 分批处理
        for i in range(0, total_jobs, batch_size):
            batch = jobs_data[i:i + batch_size]
            batch_tasks = []
            
            for j, job_data in enumerate(batch):
                job_id = job_data.get('job_id', f"job_{i+j}")
                source_url = job_data.get('url')
                
                task = self.analyze_job(
                    job_data=job_data,
                    job_id=job_id,
                    source_url=source_url
                )
                batch_tasks.append(task)
            
            # 并发执行当前批次
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # 处理结果
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"批处理中的任务失败: {result}")
                    results.append({
                        'success': False,
                        'error': str(result),
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    results.append(result)
            
            logger.info(f"完成批次 {i//batch_size + 1}/{(total_jobs-1)//batch_size + 1}")
        
        # 统计结果
        successful = sum(1 for r in results if r.get('success', False))
        failed = len(results) - successful
        
        logger.info(f"批量分析完成: 成功 {successful}, 失败 {failed}")
        
        return results
    
    async def query_jobs(self, question: str, filters: Dict = None, 
                        k: int = 5) -> Dict[str, Any]:
        """
        查询职位信息
        
        Args:
            question: 查询问题
            filters: 过滤条件
            k: 返回结果数量
            
        Returns:
            Dict: 查询结果
        """
        try:
            self.stats['analysis_sessions'] += 1
            
            result = await self.rag_system.ask_question(
                question=question,
                filters=filters,
                k=k
            )
            
            logger.info(f"查询完成: {question[:50]}...")
            return result
            
        except Exception as e:
            logger.error(f"查询失败: {e}")
            return {
                'answer': f"查询处理失败: {str(e)}",
                'success': False,
                'error': str(e)
            }
    
    def search_jobs(self, query: str, strategy: str = 'similarity', 
                   k: int = 10, filters: Dict = None) -> List[Dict[str, Any]]:
        """
        搜索职位
        
        Args:
            query: 搜索查询
            strategy: 搜索策略
            k: 返回结果数量
            filters: 过滤条件
            
        Returns:
            List[Dict]: 搜索结果
        """
        try:
            results = self.search_engine.search(
                query=query,
                strategy=strategy,
                k=k,
                filters=filters
            )
            
            logger.info(f"搜索完成: {query[:50]}..., 返回 {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []
    
    async def find_matching_jobs(self, user_profile: str, filters: Dict = None, 
                               k: int = 10) -> List[Dict[str, Any]]:
        """
        查找匹配职位
        
        Args:
            user_profile: 用户画像
            filters: 过滤条件
            k: 返回结果数量
            
        Returns:
            List[Dict]: 匹配职位列表
        """
        try:
            matching_jobs = await self.rag_system.find_matching_jobs(
                user_profile=user_profile,
                filters=filters,
                k=k
            )
            
            logger.info(f"职位匹配完成，找到 {len(matching_jobs)} 个匹配职位")
            return matching_jobs
            
        except Exception as e:
            logger.error(f"职位匹配失败: {e}")
            return []
    
    async def analyze_market_trends(self, query: str = "职位市场分析", 
                                  filters: Dict = None) -> Dict[str, Any]:
        """
        分析市场趋势
        
        Args:
            query: 分析查询
            filters: 过滤条件
            
        Returns:
            Dict: 市场分析结果
        """
        try:
            market_analysis = await self.rag_system.analyze_job_market(
                query=query,
                filters=filters
            )
            
            logger.info("市场趋势分析完成")
            return market_analysis
            
        except Exception as e:
            logger.error(f"市场趋势分析失败: {e}")
            return {'error': str(e)}
    
    def get_job_recommendations(self, user_criteria: Dict[str, Any], 
                              k: int = 10) -> List[Dict[str, Any]]:
        """
        获取职位推荐
        
        Args:
            user_criteria: 用户标准
            k: 推荐数量
            
        Returns:
            List[Dict]: 推荐职位列表
        """
        try:
            recommendations = self.search_engine.search_by_job_criteria(
                criteria=user_criteria,
                k=k
            )
            
            logger.info(f"生成 {len(recommendations)} 个职位推荐")
            return recommendations
            
        except Exception as e:
            logger.error(f"职位推荐失败: {e}")
            return []
    
    def find_similar_positions(self, reference_job: Dict[str, Any], 
                             k: int = 10) -> List[Dict[str, Any]]:
        """
        查找相似职位
        
        Args:
            reference_job: 参考职位
            k: 返回数量
            
        Returns:
            List[Dict]: 相似职位列表
        """
        try:
            similar_jobs = self.search_engine.find_similar_positions(
                reference_job=reference_job,
                k=k
            )
            
            logger.info(f"找到 {len(similar_jobs)} 个相似职位")
            return similar_jobs
            
        except Exception as e:
            logger.error(f"查找相似职位失败: {e}")
            return []
    
    def get_analytics_dashboard(self) -> Dict[str, Any]:
        """
        获取分析仪表板数据
        
        Returns:
            Dict: 仪表板数据
        """
        try:
            # 获取向量数据库统计
            vector_stats = self.vector_manager.get_collection_stats()
            
            # 计算运行时间
            start_time = datetime.fromisoformat(self.stats['start_time'])
            runtime = (datetime.now() - start_time).total_seconds()
            
            dashboard_data = {
                'system_stats': {
                    'runtime_seconds': runtime,
                    'processed_jobs': self.stats['processed_jobs'],
                    'created_documents': self.stats['created_documents'],
                    'analysis_sessions': self.stats['analysis_sessions']
                },
                'vector_store_stats': vector_stats,
                'performance_metrics': {
                    'avg_documents_per_job': (
                        self.stats['created_documents'] / max(self.stats['processed_jobs'], 1)
                    ),
                    'jobs_per_hour': (
                        self.stats['processed_jobs'] / max(runtime / 3600, 0.01)
                    )
                },
                'timestamp': datetime.now().isoformat()
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"获取仪表板数据失败: {e}")
            return {'error': str(e)}
    
    def export_analysis_results(self, output_path: str, 
                              format: str = 'json') -> bool:
        """
        导出分析结果
        
        Args:
            output_path: 输出路径
            format: 导出格式
            
        Returns:
            bool: 导出是否成功
        """
        try:
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'system_stats': self.stats,
                'vector_store_stats': self.vector_manager.get_collection_stats(),
                'config': self.config
            }
            
            if format.lower() == 'json':
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
            else:
                raise ValueError(f"不支持的导出格式: {format}")
            
            logger.info(f"分析结果已导出到: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出分析结果失败: {e}")
            return False
    
    def cleanup(self):
        """清理资源"""
        try:
            # 关闭向量数据库连接
            self.vector_manager.close()
            
            logger.info("RAG分析器资源清理完成")
            
        except Exception as e:
            logger.error(f"资源清理失败: {e}")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.cleanup()


# 便捷函数
async def analyze_single_job(job_data: Dict, config: Dict = None) -> Dict[str, Any]:
    """
    分析单个职位的便捷函数
    
    Args:
        job_data: 职位数据
        config: 配置
        
    Returns:
        Dict: 分析结果
    """
    async with RAGAnalyzer(config) as analyzer:
        return await analyzer.analyze_job(job_data)


async def batch_analyze(jobs_data: List[Dict], config: Dict = None) -> List[Dict[str, Any]]:
    """
    批量分析的便捷函数
    
    Args:
        jobs_data: 职位数据列表
        config: 配置
        
    Returns:
        List[Dict]: 分析结果列表
    """
    async with RAGAnalyzer(config) as analyzer:
        return await analyzer.batch_analyze_jobs(jobs_data)