"""
数据库操作模块

提供数据库的CRUD操作和统计功能
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from contextlib import contextmanager

from .models import DatabaseSchema, JobRecord, ApplicationStatus
from ..core.exceptions import DatabaseError


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(__name__)
        
        # 确保数据库目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            raise DatabaseError(f"数据库操作失败: {e}")
        finally:
            if conn:
                conn.close()
    
    def init_database(self):
        """初始化数据库，创建表和索引"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 创建表
                for table_sql in DatabaseSchema.get_all_tables():
                    cursor.execute(table_sql)
                
                # 创建索引
                for index_sql in DatabaseSchema.get_all_indexes():
                    cursor.execute(index_sql)
                
                conn.commit()
                self.logger.info("数据库初始化完成")
                
        except Exception as e:
            raise DatabaseError(f"数据库初始化失败: {e}")
    
    def job_exists(self, job_id: str) -> bool:
        """
        检查职位是否已存在
        
        Args:
            job_id: 职位ID
            
        Returns:
            是否存在
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM jobs WHERE job_id = ?", (job_id,))
                return cursor.fetchone() is not None
        except Exception as e:
            self.logger.error(f"检查职位存在性失败: {e}")
            return False
    
    def save_job(self, job_data: Dict[str, Any]) -> bool:
        """
        保存职位信息
        
        Args:
            job_data: 职位数据字典
            
        Returns:
            是否保存成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查状态是否有效
                status = job_data.get('application_status', ApplicationStatus.PENDING)
                if not ApplicationStatus.is_valid_status(status):
                    raise DatabaseError(f"无效的投递状态: {status}")
                
                # 准备数据
                now = datetime.now().isoformat()
                submitted_at = job_data.get('submitted_at')
                if submitted_at and isinstance(submitted_at, (int, float)):
                    submitted_at = datetime.fromtimestamp(submitted_at).isoformat()
                
                # 插入或更新
                sql = """
                INSERT OR REPLACE INTO jobs
                (job_id, title, company, url, job_fingerprint, application_status, match_score, website, created_at, submitted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                cursor.execute(sql, (
                    job_data['job_id'],
                    job_data['title'],
                    job_data['company'],
                    job_data['url'],
                    job_data.get('job_fingerprint'),
                    status,
                    job_data.get('match_score'),
                    job_data.get('website', ''),
                    now,
                    submitted_at
                ))
                
                conn.commit()
                self.logger.debug(f"保存职位成功: {job_data['job_id']}")
                return True
                
        except Exception as e:
            self.logger.error(f"保存职位失败: {e}")
            return False
    
    def get_job(self, job_id: str) -> Optional[JobRecord]:
        """
        获取职位信息
        
        Args:
            job_id: 职位ID
            
        Returns:
            职位记录或None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
                row = cursor.fetchone()
                
                if row:
                    return JobRecord.from_dict(dict(row))
                return None
                
        except Exception as e:
            self.logger.error(f"获取职位失败: {e}")
            return None
    
    def get_jobs_by_status(self, status: str, limit: int = 100) -> List[JobRecord]:
        """
        根据状态获取职位列表
        
        Args:
            status: 投递状态
            limit: 限制数量
            
        Returns:
            职位记录列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM jobs WHERE application_status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, limit)
                )
                
                jobs = []
                for row in cursor.fetchall():
                    jobs.append(JobRecord.from_dict(dict(row)))
                
                return jobs
                
        except Exception as e:
            self.logger.error(f"获取职位列表失败: {e}")
            return []
    
    def update_job_status(self, job_id: str, status: str, submitted_at: Optional[datetime] = None) -> bool:
        """
        更新职位状态
        
        Args:
            job_id: 职位ID
            status: 新状态
            submitted_at: 投递时间
            
        Returns:
            是否更新成功
        """
        try:
            if not ApplicationStatus.is_valid_status(status):
                raise DatabaseError(f"无效的投递状态: {status}")
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if submitted_at:
                    cursor.execute(
                        "UPDATE jobs SET application_status = ?, submitted_at = ? WHERE job_id = ?",
                        (status, submitted_at.isoformat(), job_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE jobs SET application_status = ? WHERE job_id = ?",
                        (status, job_id)
                    )
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            self.logger.error(f"更新职位状态失败: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计数据字典
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 总数统计
                cursor.execute("SELECT COUNT(*) as total FROM jobs")
                total = cursor.fetchone()['total']
                
                # 按状态统计
                cursor.execute("""
                    SELECT application_status, COUNT(*) as count 
                    FROM jobs 
                    GROUP BY application_status
                """)
                status_counts = {row['application_status']: row['count'] for row in cursor.fetchall()}
                
                # 平均匹配度
                cursor.execute("SELECT AVG(match_score) as avg_score FROM jobs WHERE match_score IS NOT NULL")
                avg_score = cursor.fetchone()['avg_score'] or 0
                
                # 按网站统计
                cursor.execute("""
                    SELECT website, COUNT(*) as count 
                    FROM jobs 
                    GROUP BY website
                """)
                website_counts = {row['website']: row['count'] for row in cursor.fetchall()}
                
                # 今日统计
                today = datetime.now().date().isoformat()
                cursor.execute(
                    "SELECT COUNT(*) as today_count FROM jobs WHERE DATE(created_at) = ?",
                    (today,)
                )
                today_count = cursor.fetchone()['today_count']
                
                return {
                    'total': total,
                    'submitted': status_counts.get(ApplicationStatus.SUBMITTED, 0),
                    'failed': status_counts.get(ApplicationStatus.FAILED, 0),
                    'skipped': status_counts.get(ApplicationStatus.SKIPPED, 0),
                    'pending': status_counts.get(ApplicationStatus.PENDING, 0),
                    'avg_match_score': round(avg_score, 2),
                    'status_counts': status_counts,
                    'website_counts': website_counts,
                    'today_count': today_count
                }
                
        except Exception as e:
            self.logger.error(f"获取统计信息失败: {e}")
            return {}
    
    def get_rag_processing_stats(self) -> Dict[str, int]:
        """
        获取RAG处理统计信息
        
        Returns:
            RAG处理统计数据
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 总数统计
                cursor.execute("SELECT COUNT(*) as total FROM jobs")
                total = cursor.fetchone()['total']
                
                # 已处理数量
                cursor.execute("SELECT COUNT(*) as processed FROM jobs WHERE rag_processed = 1")
                processed = cursor.fetchone()['processed']
                
                # 未处理数量
                unprocessed = total - processed
                
                # 平均向量文档数量
                cursor.execute("SELECT AVG(vector_doc_count) as avg_docs FROM jobs WHERE rag_processed = 1")
                avg_docs = cursor.fetchone()['avg_docs'] or 0
                
                # 平均语义评分
                cursor.execute("SELECT AVG(semantic_score) as avg_semantic FROM jobs WHERE semantic_score IS NOT NULL")
                avg_semantic = cursor.fetchone()['avg_semantic'] or 0
                
                return {
                    'total': total,
                    'processed': processed,
                    'unprocessed': unprocessed,
                    'processing_rate': (processed / total * 100) if total > 0 else 0,
                    'avg_vector_docs': round(avg_docs, 1),
                    'avg_semantic_score': round(avg_semantic, 3)
                }
                
        except Exception as e:
            self.logger.error(f"获取RAG处理统计失败: {e}")
            return {
                'total': 0,
                'processed': 0,
                'unprocessed': 0,
                'processing_rate': 0,
                'avg_vector_docs': 0,
                'avg_semantic_score': 0
            }
    
    def mark_job_as_processed(self, job_id: str, doc_count: int = 0, vector_id: str = None, semantic_score: float = None) -> bool:
        """
        标记职位为已RAG处理
        
        Args:
            job_id: 职位ID
            doc_count: 生成的向量文档数量
            vector_id: 向量ID
            semantic_score: 语义评分
            
        Returns:
            是否更新成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                now = datetime.now().isoformat()
                cursor.execute("""
                    UPDATE jobs
                    SET rag_processed = 1,
                        rag_processed_at = ?,
                        vector_doc_count = ?,
                        vector_id = ?,
                        semantic_score = ?
                    WHERE job_id = ?
                """, (now, doc_count, vector_id, semantic_score, job_id))
                
                conn.commit()
                success = cursor.rowcount > 0
                
                if success:
                    self.logger.debug(f"标记职位RAG处理完成: {job_id}")
                
                return success
                
        except Exception as e:
            self.logger.error(f"标记职位RAG处理状态失败: {e}")
            return False
    
    def get_unprocessed_jobs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取未进行RAG处理的职位（包含详细信息）
        
        Args:
            limit: 限制数量
            
        Returns:
            未处理的职位列表（包含详细信息）
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 联合查询jobs和job_details表
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
                    LIMIT ?
                """, (limit,))
                
                jobs = []
                for row in cursor.fetchall():
                    jobs.append(dict(row))
                
                return jobs
                
        except Exception as e:
            self.logger.error(f"获取未处理职位失败: {e}")
            return []
    
    def get_job_with_details(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        获取包含详细信息的完整职位数据
        
        Args:
            job_id: 职位ID
            
        Returns:
            完整职位数据或None
        """
        try:
            with self.get_connection() as conn:
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
                    WHERE j.job_id = ?
                """, (job_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            self.logger.error(f"获取职位详细信息失败: {e}")
            return None
    
    def reset_rag_processing_status(self, job_ids: List[str] = None) -> int:
        """
        重置RAG处理状态（用于重新处理）
        
        Args:
            job_ids: 要重置的职位ID列表，None表示重置所有
            
        Returns:
            重置的记录数
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if job_ids:
                    placeholders = ','.join('?' * len(job_ids))
                    cursor.execute(f"""
                        UPDATE jobs
                        SET rag_processed = 0,
                            rag_processed_at = NULL,
                            vector_doc_count = 0,
                            vector_id = NULL,
                            semantic_score = NULL,
                            structured_data = NULL
                        WHERE job_id IN ({placeholders})
                    """, job_ids)
                else:
                    cursor.execute("""
                        UPDATE jobs
                        SET rag_processed = 0,
                            rag_processed_at = NULL,
                            vector_doc_count = 0,
                            vector_id = NULL,
                            semantic_score = NULL,
                            structured_data = NULL
                    """)
                
                reset_count = cursor.rowcount
                conn.commit()
                
                self.logger.info(f"重置了 {reset_count} 个职位的RAG处理状态")
                return reset_count
                
        except Exception as e:
            self.logger.error(f"重置RAG处理状态失败: {e}")
            return 0
    
    def cleanup_old_records(self, days: int = 30) -> int:
        """
        清理旧记录
        
        Args:
            days: 保留天数
            
        Returns:
            删除的记录数
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 删除指定天数前的记录
                cursor.execute("""
                    DELETE FROM jobs 
                    WHERE created_at < datetime('now', '-{} days')
                """.format(days))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                self.logger.info(f"清理了 {deleted_count} 条旧记录")
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"清理旧记录失败: {e}")
            return 0
    
    def export_data(self, output_file: str, status_filter: Optional[str] = None) -> bool:
        """
        导出数据到CSV文件
        
        Args:
            output_file: 输出文件路径
            status_filter: 状态过滤器
            
        Returns:
            是否导出成功
        """
        try:
            import csv
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if status_filter:
                    cursor.execute(
                        "SELECT * FROM jobs WHERE application_status = ? ORDER BY created_at",
                        (status_filter,)
                    )
                else:
                    cursor.execute("SELECT * FROM jobs ORDER BY created_at")
                
                with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                    if cursor.description:
                        fieldnames = [desc[0] for desc in cursor.description]
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writeheader()
                        
                        for row in cursor.fetchall():
                            writer.writerow(dict(row))
                
                self.logger.info(f"数据导出成功: {output_file}")
                return True
                
        except Exception as e:
            self.logger.error(f"数据导出失败: {e}")
            return False
    
    def fingerprint_exists(self, fingerprint: str) -> bool:
        """
        检查职位指纹是否已存在
        
        Args:
            fingerprint: 职位指纹
            
        Returns:
            是否存在
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM jobs WHERE job_fingerprint = ?", (fingerprint,))
                return cursor.fetchone() is not None
        except Exception as e:
            self.logger.error(f"检查职位指纹存在性失败: {e}")
            return False
    
    def get_job_by_fingerprint(self, fingerprint: str) -> Optional[Dict[str, Any]]:
        """
        根据指纹获取职位信息
        
        Args:
            fingerprint: 职位指纹
            
        Returns:
            职位信息字典或None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM jobs WHERE job_fingerprint = ?", (fingerprint,))
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            self.logger.error(f"根据指纹获取职位失败: {e}")
            return None
    
    def batch_check_fingerprints(self, fingerprints: List[str]) -> Dict[str, bool]:
        """
        批量检查职位指纹是否存在
        
        Args:
            fingerprints: 指纹列表
            
        Returns:
            指纹存在性字典 {fingerprint: exists}
        """
        try:
            if not fingerprints:
                return {}
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 构建IN查询
                placeholders = ','.join('?' * len(fingerprints))
                sql = f"SELECT job_fingerprint FROM jobs WHERE job_fingerprint IN ({placeholders})"
                
                cursor.execute(sql, fingerprints)
                existing_fingerprints = {row[0] for row in cursor.fetchall()}
                
                # 构建结果字典
                return {fp: fp in existing_fingerprints for fp in fingerprints}
                
        except Exception as e:
            self.logger.error(f"批量检查指纹失败: {e}")
            return {fp: False for fp in fingerprints}
    
    def get_duplicate_jobs_count(self) -> int:
        """
        获取重复职位数量（基于指纹）
        
        Returns:
            重复职位数量
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) - COUNT(DISTINCT job_fingerprint) as duplicates
                    FROM jobs
                    WHERE job_fingerprint IS NOT NULL
                """)
                result = cursor.fetchone()
                return result[0] if result else 0
                
        except Exception as e:
            self.logger.error(f"获取重复职位数量失败: {e}")
            return 0
    
    def cleanup_duplicate_jobs(self) -> int:
        """
        清理重复职位（保留最新的）
        
        Returns:
            删除的记录数
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 删除重复职位，保留每个指纹的最新记录
                cursor.execute("""
                    DELETE FROM jobs
                    WHERE id NOT IN (
                        SELECT MAX(id)
                        FROM jobs
                        WHERE job_fingerprint IS NOT NULL
                        GROUP BY job_fingerprint
                    ) AND job_fingerprint IS NOT NULL
                """)
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                self.logger.info(f"清理了 {deleted_count} 条重复职位记录")
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"清理重复职位失败: {e}")
            return 0
    
    def save_resume_match(self, match_data: Dict[str, Any]) -> bool:
        """
        保存简历匹配结果（智能处理已投递职位）
        
        逻辑：
        - 对于已投递的职位（processed=1）：跳过，不更新
        - 对于未投递的职位：正常插入或更新
        
        Args:
            match_data: 匹配结果数据
            
        Returns:
            是否保存成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                job_id = match_data['job_id']
                resume_profile_id = match_data.get('resume_profile_id', 'default')
                now = datetime.now().isoformat()
                
                # 检查是否已存在相同job_id和resume_profile_id的记录，以及是否已投递
                cursor.execute("""
                    SELECT id, processed FROM resume_matches
                    WHERE job_id = ? AND resume_profile_id = ?
                """, (job_id, resume_profile_id))
                
                existing_record = cursor.fetchone()
                
                # 如果记录已存在且已投递，跳过处理
                if existing_record and existing_record['processed'] == 1:
                    self.logger.debug(f"跳过已投递职位的匹配记录更新: {job_id}")
                    return True  # 返回True表示操作"成功"（虽然是跳过）
                
                if existing_record:
                    # 更新现有记录（仅未投递的）
                    sql = """
                    UPDATE resume_matches SET
                        match_score = ?, priority_level = ?, semantic_score = ?,
                        skill_match_score = ?, experience_match_score = ?,
                        location_match_score = ?, salary_match_score = ?,
                        match_details = ?, match_reasons = ?, created_at = ?, processed = 0
                    WHERE job_id = ? AND resume_profile_id = ? AND (processed = 0 OR processed IS NULL)
                    """
                    
                    cursor.execute(sql, (
                        match_data['match_score'],
                        match_data['priority_level'],
                        match_data.get('semantic_score'),
                        match_data.get('skill_match_score'),
                        match_data.get('experience_match_score'),
                        match_data.get('location_match_score'),
                        match_data.get('salary_match_score'),
                        match_data.get('match_details'),
                        match_data.get('match_reasons'),
                        now,
                        job_id,
                        resume_profile_id
                    ))
                    
                    if cursor.rowcount > 0:
                        self.logger.debug(f"更新简历匹配结果成功: {job_id}")
                    else:
                        self.logger.debug(f"匹配记录已投递，跳过更新: {job_id}")
                else:
                    # 插入新记录
                    sql = """
                    INSERT INTO resume_matches
                    (job_id, resume_profile_id, match_score, priority_level, semantic_score,
                     skill_match_score, experience_match_score, location_match_score,
                     salary_match_score, match_details, match_reasons, created_at, processed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """
                    
                    cursor.execute(sql, (
                        job_id,
                        resume_profile_id,
                        match_data['match_score'],
                        match_data['priority_level'],
                        match_data.get('semantic_score'),
                        match_data.get('skill_match_score'),
                        match_data.get('experience_match_score'),
                        match_data.get('location_match_score'),
                        match_data.get('salary_match_score'),
                        match_data.get('match_details'),
                        match_data.get('match_reasons'),
                        now
                    ))
                    
                    self.logger.debug(f"插入简历匹配结果成功: {job_id}")
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"保存简历匹配结果失败: {e}")
            return False
    
    def batch_save_resume_matches(self, matches: List[Dict[str, Any]]) -> int:
        """
        批量保存简历匹配结果（智能处理已投递职位）
        
        逻辑：
        - 对于未投递的职位：删除旧匹配记录，插入新记录
        - 对于已投递的职位（processed=1）：跳过，不删除不添加
        
        Args:
            matches: 匹配结果列表
            
        Returns:
            成功保存的数量
        """
        success_count = 0
        skipped_count = 0
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                
                # 收集所有job_id和resume_profile_id
                job_profile_pairs = [(match['job_id'], match.get('resume_profile_id', 'default')) for match in matches]
                
                # 检查哪些匹配记录已经被处理过（已投递）
                processed_jobs = set()
                if job_profile_pairs:
                    # 逐个查询已处理的匹配记录（SQLite不支持元组IN查询）
                    for job_id, profile_id in job_profile_pairs:
                        cursor.execute("""
                            SELECT job_id, resume_profile_id FROM resume_matches
                            WHERE job_id = ? AND resume_profile_id = ? AND processed = 1
                        """, (job_id, profile_id))
                        
                        result = cursor.fetchone()
                        if result:
                            processed_jobs.add((result['job_id'], result['resume_profile_id']))
                    
                    if processed_jobs:
                        self.logger.info(f"发现 {len(processed_jobs)} 个已投递的职位，将跳过处理")
                
                # 分离需要处理和需要跳过的匹配记录
                matches_to_process = []
                for match_data in matches:
                    job_id = match_data['job_id']
                    profile_id = match_data.get('resume_profile_id', 'default')
                    
                    if (job_id, profile_id) in processed_jobs:
                        skipped_count += 1
                        self.logger.debug(f"跳过已投递职位的匹配记录: {job_id}")
                    else:
                        matches_to_process.append(match_data)
                
                # 对于未投递的职位，删除旧记录
                if matches_to_process:
                    unprocessed_pairs = [(match['job_id'], match.get('resume_profile_id', 'default'))
                                       for match in matches_to_process]
                    
                    delete_sql = """
                        DELETE FROM resume_matches
                        WHERE job_id = ? AND resume_profile_id = ? AND (processed = 0 OR processed IS NULL)
                    """
                    deleted_count = 0
                    for job_id, profile_id in unprocessed_pairs:
                        cursor.execute(delete_sql, (job_id, profile_id))
                        deleted_count += cursor.rowcount
                    
                    if deleted_count > 0:
                        self.logger.info(f"删除了 {deleted_count} 条未投递职位的旧匹配记录")
                
                # 插入新记录（仅未投递的职位）
                if matches_to_process:
                    insert_sql = """
                    INSERT INTO resume_matches
                    (job_id, resume_profile_id, match_score, priority_level, semantic_score,
                     skill_match_score, experience_match_score, location_match_score,
                     salary_match_score, match_details, match_reasons, created_at, processed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """
                    
                    for match_data in matches_to_process:
                        try:
                            cursor.execute(insert_sql, (
                                match_data['job_id'],
                                match_data.get('resume_profile_id', 'default'),
                                match_data['match_score'],
                                match_data['priority_level'],
                                match_data.get('semantic_score'),
                                match_data.get('skill_match_score'),
                                match_data.get('experience_match_score'),
                                match_data.get('location_match_score'),
                                match_data.get('salary_match_score'),
                                match_data.get('match_details'),
                                match_data.get('match_reasons'),
                                now
                            ))
                            success_count += 1
                        except Exception as e:
                            self.logger.warning(f"保存单个匹配结果失败: {e}")
                            continue
                
                conn.commit()
                self.logger.info(f"批量保存简历匹配结果: {success_count} 新增, {skipped_count} 跳过 (已投递)")
                
        except Exception as e:
            self.logger.error(f"批量保存简历匹配结果失败: {e}")
        
        return success_count
    
    def get_resume_matches(self, job_id: str = None, resume_profile_id: str = None,
                          priority_level: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取简历匹配结果
        
        Args:
            job_id: 职位ID筛选
            resume_profile_id: 简历档案ID筛选
            priority_level: 优先级筛选
            limit: 限制数量
            
        Returns:
            匹配结果列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                conditions = []
                params = []
                
                if job_id:
                    conditions.append("job_id = ?")
                    params.append(job_id)
                
                if resume_profile_id:
                    conditions.append("resume_profile_id = ?")
                    params.append(resume_profile_id)
                
                if priority_level:
                    conditions.append("priority_level = ?")
                    params.append(priority_level)
                
                where_clause = ""
                if conditions:
                    where_clause = "WHERE " + " AND ".join(conditions)
                
                params.append(limit)
                
                cursor.execute(f"""
                    SELECT * FROM resume_matches
                    {where_clause}
                    ORDER BY match_score DESC, created_at DESC
                    LIMIT ?
                """, params)
                
                matches = []
                for row in cursor.fetchall():
                    matches.append(dict(row))
                
                return matches
                
        except Exception as e:
            self.logger.error(f"获取简历匹配结果失败: {e}")
            return []
    
    def get_unprocessed_matches(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取未处理的匹配结果
        
        Args:
            limit: 限制数量
            
        Returns:
            未处理的匹配结果列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM resume_matches
                    WHERE processed = 0 OR processed IS NULL
                    ORDER BY match_score DESC, created_at DESC
                    LIMIT ?
                """, (limit,))
                
                matches = []
                for row in cursor.fetchall():
                    matches.append(dict(row))
                
                return matches
                
        except Exception as e:
            self.logger.error(f"获取未处理匹配结果失败: {e}")
            return []
    
    def mark_match_as_processed(self, match_id: int) -> bool:
        """
        标记匹配结果为已处理
        
        Args:
            match_id: 匹配结果ID
            
        Returns:
            是否标记成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                now = datetime.now().isoformat()
                cursor.execute("""
                    UPDATE resume_matches
                    SET processed = 1, processed_at = ?
                    WHERE id = ?
                """, (now, match_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            self.logger.error(f"标记匹配结果处理状态失败: {e}")
            return False
    
    def get_match_statistics(self) -> Dict[str, Any]:
        """
        获取匹配结果统计信息
        
        Returns:
            统计信息字典
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 总数统计
                cursor.execute("SELECT COUNT(*) as total FROM resume_matches")
                total = cursor.fetchone()['total']
                
                # 按优先级统计
                cursor.execute("""
                    SELECT priority_level, COUNT(*) as count
                    FROM resume_matches
                    GROUP BY priority_level
                """)
                priority_counts = {row['priority_level']: row['count'] for row in cursor.fetchall()}
                
                # 平均匹配分数
                cursor.execute("SELECT AVG(match_score) as avg_score FROM resume_matches")
                avg_score = cursor.fetchone()['avg_score'] or 0
                
                # 处理状态统计
                cursor.execute("SELECT COUNT(*) as processed FROM resume_matches WHERE processed = 1")
                processed = cursor.fetchone()['processed']
                
                return {
                    'total_matches': total,
                    'processed_matches': processed,
                    'unprocessed_matches': total - processed,
                    'avg_match_score': round(avg_score, 3),
                    'priority_counts': priority_counts,
                    'processing_rate': (processed / total * 100) if total > 0 else 0
                }
                
        except Exception as e:
            self.logger.error(f"获取匹配统计信息失败: {e}")
            return {}