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
                (job_id, title, company, url, application_status, match_score, website, created_at, submitted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                cursor.execute(sql, (
                    job_data['job_id'],
                    job_data['title'],
                    job_data['company'],
                    job_data['url'],
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