"""
数据库职位数据读取器

从SQLite数据库读取职位数据，为RAG系统提供数据源
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Iterator
from pathlib import Path

from ..database.operations import DatabaseManager
from ..core.exceptions import DatabaseError


class DatabaseJobReader:
    """数据库职位数据读取器"""
    
    def __init__(self, db_path: str, config: Dict = None):
        """
        初始化数据库职位读取器
        
        Args:
            db_path: 数据库文件路径
            config: 配置字典
        """
        self.db_path = Path(db_path)
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # 初始化数据库管理器
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # 验证数据库文件存在
        if not self.db_path.exists():
            raise DatabaseError(f"数据库文件不存在: {self.db_path}")
        
        self.logger.info(f"数据库职位读取器初始化完成: {self.db_path}")
    
    def read_all_jobs(self) -> List[Dict]:
        """
        读取所有职位数据（包含详细信息）
        
        Returns:
            职位数据列表
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        j.id, j.job_id, j.title, j.company, j.url, j.job_fingerprint,
                        j.application_status, j.match_score, j.semantic_score, j.vector_id,
                        j.structured_data, j.website, j.created_at, j.submitted_at,
                        j.rag_processed, j.rag_processed_at, j.vector_doc_count,
                        jd.salary, jd.location, jd.experience, jd.education,
                        jd.description, jd.requirements, jd.benefits, jd.publish_time,
                        jd.company_scale, jd.industry, jd.keyword, jd.extracted_at
                    FROM jobs j
                    LEFT JOIN job_details jd ON j.job_id = jd.job_id
                    ORDER BY j.created_at DESC
                """)
                
                jobs = []
                for row in cursor.fetchall():
                    jobs.append(dict(row))
                
                self.logger.info(f"读取所有职位数据: {len(jobs)} 个")
                return jobs
                
        except Exception as e:
            self.logger.error(f"读取所有职位数据失败: {e}")
            raise DatabaseError(f"读取职位数据失败: {e}")
    
    def read_jobs_by_batch(self, batch_size: int = 100) -> Iterator[List[Dict]]:
        """
        批量读取职位数据
        
        Args:
            batch_size: 批次大小
            
        Yields:
            职位数据批次
        """
        try:
            offset = 0
            
            while True:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        SELECT 
                            j.id, j.job_id, j.title, j.company, j.url, j.job_fingerprint,
                            j.application_status, j.match_score, j.semantic_score, j.vector_id,
                            j.structured_data, j.website, j.created_at, j.submitted_at,
                            j.rag_processed, j.rag_processed_at, j.vector_doc_count,
                            jd.salary, jd.location, jd.experience, jd.education,
                            jd.description, jd.requirements, jd.benefits, jd.publish_time,
                            jd.company_scale, jd.industry, jd.keyword, jd.extracted_at
                        FROM jobs j
                        LEFT JOIN job_details jd ON j.job_id = jd.job_id
                        ORDER BY j.created_at DESC
                        LIMIT ? OFFSET ?
                    """, (batch_size, offset))
                    
                    batch = []
                    for row in cursor.fetchall():
                        batch.append(dict(row))
                    
                    if not batch:
                        break
                    
                    self.logger.debug(f"读取批次数据: {len(batch)} 个职位 (offset: {offset})")
                    yield batch
                    
                    offset += batch_size
                    
                    # 如果批次大小小于请求大小，说明已经读完
                    if len(batch) < batch_size:
                        break
                        
        except Exception as e:
            self.logger.error(f"批量读取职位数据失败: {e}")
            raise DatabaseError(f"批量读取失败: {e}")
    
    def read_new_jobs(self, since: datetime) -> List[Dict]:
        """
        读取指定时间后的新职位
        
        Args:
            since: 起始时间
            
        Returns:
            新职位数据列表
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        j.id, j.job_id, j.title, j.company, j.url, j.job_fingerprint,
                        j.application_status, j.match_score, j.semantic_score, j.vector_id,
                        j.structured_data, j.website, j.created_at, j.submitted_at,
                        j.rag_processed, j.rag_processed_at, j.vector_doc_count,
                        jd.salary, jd.location, jd.experience, jd.education,
                        jd.description, jd.requirements, jd.benefits, jd.publish_time,
                        jd.company_scale, jd.industry, jd.keyword, jd.extracted_at
                    FROM jobs j
                    LEFT JOIN job_details jd ON j.job_id = jd.job_id
                    WHERE j.created_at > ?
                    ORDER BY j.created_at DESC
                """, (since.isoformat(),))
                
                jobs = []
                for row in cursor.fetchall():
                    jobs.append(dict(row))
                
                self.logger.info(f"读取新职位数据: {len(jobs)} 个 (since: {since})")
                return jobs
                
        except Exception as e:
            self.logger.error(f"读取新职位数据失败: {e}")
            raise DatabaseError(f"读取新职位失败: {e}")
    
    def get_job_with_details(self, job_id: str) -> Optional[Dict]:
        """
        获取包含详细信息的完整职位数据
        
        Args:
            job_id: 职位ID
            
        Returns:
            完整职位数据或None
        """
        try:
            return self.db_manager.get_job_with_details(job_id)
        except Exception as e:
            self.logger.error(f"获取职位详细信息失败: {e}")
            return None
    
    def get_jobs_for_rag_processing(self, limit: int = None) -> List[Dict]:
        """
        获取需要RAG处理的职位数据（未处理的职位）
        
        Args:
            limit: 限制数量
            
        Returns:
            需要处理的职位数据列表
        """
        try:
            limit = limit or self.config.get('batch_size', 100)
            return self.db_manager.get_unprocessed_jobs(limit)
        except Exception as e:
            self.logger.error(f"获取待处理职位失败: {e}")
            return []
    
    def get_unprocessed_jobs(self, batch_size: int = 100) -> Iterator[List[Dict]]:
        """
        批量获取未进行RAG处理的职位
        
        Args:
            batch_size: 批次大小
            
        Yields:
            未处理职位数据批次
        """
        try:
            offset = 0
            
            while True:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        SELECT 
                            j.id, j.job_id, j.title, j.company, j.url, j.job_fingerprint,
                            j.application_status, j.match_score, j.semantic_score, j.vector_id,
                            j.structured_data, j.website, j.created_at, j.submitted_at,
                            j.rag_processed, j.rag_processed_at, j.vector_doc_count,
                            jd.salary, jd.location, jd.experience, jd.education,
                            jd.description, jd.requirements, jd.benefits, jd.publish_time,
                            jd.company_scale, jd.industry, jd.keyword, jd.extracted_at
                        FROM jobs j
                        LEFT JOIN job_details jd ON j.job_id = jd.job_id
                        WHERE j.rag_processed = 0 OR j.rag_processed IS NULL
                        ORDER BY j.created_at DESC
                        LIMIT ? OFFSET ?
                    """, (batch_size, offset))
                    
                    batch = []
                    for row in cursor.fetchall():
                        batch.append(dict(row))
                    
                    if not batch:
                        break
                    
                    self.logger.debug(f"读取未处理职位批次: {len(batch)} 个 (offset: {offset})")
                    yield batch
                    
                    offset += batch_size
                    
                    # 如果批次大小小于请求大小，说明已经读完
                    if len(batch) < batch_size:
                        break
                        
        except Exception as e:
            self.logger.error(f"批量获取未处理职位失败: {e}")
            raise DatabaseError(f"批量获取未处理职位失败: {e}")
    
    def mark_job_as_processed(self, job_id: str, doc_count: int = 0, vector_id: str = None, semantic_score: float = None, structured_data: str = None) -> bool:
        """
        标记职位为已RAG处理
        
        Args:
            job_id: 职位ID
            doc_count: 生成的向量文档数量
            vector_id: 向量ID
            semantic_score: 语义评分
            structured_data: 结构化数据JSON字符串
            
        Returns:
            是否标记成功
        """
        try:
            return self.db_manager.mark_job_as_processed(job_id, doc_count, vector_id, semantic_score, structured_data)
        except Exception as e:
            self.logger.error(f"标记职位处理状态失败: {e}")
            return False
    
    def get_rag_processing_stats(self) -> Dict[str, Any]:
        """
        获取RAG处理统计信息
        
        Returns:
            统计信息字典
        """
        try:
            return self.db_manager.get_rag_processing_stats()
        except Exception as e:
            self.logger.error(f"获取RAG处理统计失败: {e}")
            return {}
    
    def reset_rag_processing_status(self, job_ids: List[str] = None) -> int:
        """
        重置RAG处理状态（用于重新处理）
        
        Args:
            job_ids: 要重置的职位ID列表，None表示重置所有
            
        Returns:
            重置的记录数
        """
        try:
            return self.db_manager.reset_rag_processing_status(job_ids)
        except Exception as e:
            self.logger.error(f"重置RAG处理状态失败: {e}")
            return 0
    
    def get_jobs_by_criteria(self, 
                           website: str = None,
                           status: str = None,
                           rag_processed: bool = None,
                           limit: int = 100) -> List[Dict]:
        """
        根据条件获取职位数据
        
        Args:
            website: 网站筛选
            status: 状态筛选
            rag_processed: RAG处理状态筛选
            limit: 限制数量
            
        Returns:
            符合条件的职位数据列表
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 构建查询条件
                conditions = []
                params = []
                
                if website:
                    conditions.append("j.website = ?")
                    params.append(website)
                
                if status:
                    conditions.append("j.application_status = ?")
                    params.append(status)
                
                if rag_processed is not None:
                    conditions.append("j.rag_processed = ?")
                    params.append(1 if rag_processed else 0)
                
                where_clause = ""
                if conditions:
                    where_clause = "WHERE " + " AND ".join(conditions)
                
                params.append(limit)
                
                cursor.execute(f"""
                    SELECT 
                        j.id, j.job_id, j.title, j.company, j.url, j.job_fingerprint,
                        j.application_status, j.match_score, j.semantic_score, j.vector_id,
                        j.structured_data, j.website, j.created_at, j.submitted_at,
                        j.rag_processed, j.rag_processed_at, j.vector_doc_count,
                        jd.salary, jd.location, jd.experience, jd.education,
                        jd.description, jd.requirements, jd.benefits, jd.publish_time,
                        jd.company_scale, jd.industry, jd.keyword, jd.extracted_at
                    FROM jobs j
                    LEFT JOIN job_details jd ON j.job_id = jd.job_id
                    {where_clause}
                    ORDER BY j.created_at DESC
                    LIMIT ?
                """, params)
                
                jobs = []
                for row in cursor.fetchall():
                    jobs.append(dict(row))
                
                self.logger.info(f"根据条件获取职位: {len(jobs)} 个")
                return jobs
                
        except Exception as e:
            self.logger.error(f"根据条件获取职位失败: {e}")
            return []
    
    def validate_job_data(self, job_data: Dict) -> bool:
        """
        验证职位数据完整性
        
        Args:
            job_data: 职位数据
            
        Returns:
            是否有效
        """
        required_fields = ['job_id', 'title', 'company']
        
        for field in required_fields:
            if not job_data.get(field):
                self.logger.warning(f"职位数据缺少必需字段: {field}")
                return False
        
        # 检查RAG处理所需的关键字段
        rag_fields = ['description', 'requirements']
        has_rag_data = any(job_data.get(field) for field in rag_fields)
        
        if not has_rag_data:
            self.logger.warning(f"职位 {job_data['job_id']} 缺少RAG处理所需的描述或要求信息")
            return False
        
        return True
    
    def get_data_quality_report(self) -> Dict[str, Any]:
        """
        获取数据质量报告
        
        Returns:
            数据质量报告
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 基本统计
                cursor.execute("SELECT COUNT(*) as total FROM jobs")
                total_jobs = cursor.fetchone()['total']
                
                cursor.execute("SELECT COUNT(*) as with_details FROM jobs j INNER JOIN job_details jd ON j.job_id = jd.job_id")
                jobs_with_details = cursor.fetchone()['with_details']
                
                # 数据完整性检查
                cursor.execute("SELECT COUNT(*) as with_description FROM job_details WHERE description IS NOT NULL AND description != ''")
                with_description = cursor.fetchone()['with_description']
                
                cursor.execute("SELECT COUNT(*) as with_requirements FROM job_details WHERE requirements IS NOT NULL AND requirements != ''")
                with_requirements = cursor.fetchone()['with_requirements']
                
                # RAG处理状态
                cursor.execute("SELECT COUNT(*) as processed FROM jobs WHERE rag_processed = 1")
                rag_processed = cursor.fetchone()['processed']
                
                # 计算质量指标
                detail_coverage = (jobs_with_details / total_jobs * 100) if total_jobs > 0 else 0
                description_coverage = (with_description / total_jobs * 100) if total_jobs > 0 else 0
                requirements_coverage = (with_requirements / total_jobs * 100) if total_jobs > 0 else 0
                rag_coverage = (rag_processed / total_jobs * 100) if total_jobs > 0 else 0
                
                return {
                    'total_jobs': total_jobs,
                    'jobs_with_details': jobs_with_details,
                    'detail_coverage': round(detail_coverage, 1),
                    'description_coverage': round(description_coverage, 1),
                    'requirements_coverage': round(requirements_coverage, 1),
                    'rag_processed': rag_processed,
                    'rag_coverage': round(rag_coverage, 1),
                    'data_quality_score': round((detail_coverage + description_coverage + requirements_coverage) / 3, 1)
                }
                
        except Exception as e:
            self.logger.error(f"获取数据质量报告失败: {e}")
            return {}