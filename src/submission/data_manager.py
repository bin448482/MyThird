"""
投递数据管理器

负责数据库查询、状态更新和投递记录管理
"""

import logging
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from contextlib import contextmanager

from .models import JobMatchRecord, SubmissionResult, SubmissionStatus
from ..database.operations import DatabaseManager


class SubmissionDataManager:
    """投递数据管理器"""
    
    def __init__(self, db_path: str):
        """
        初始化数据管理器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.db_manager = DatabaseManager(db_path)
        self.logger = logging.getLogger(__name__)
        
        # 确保投递日志表存在
        self._ensure_submission_log_table()
    
    def _ensure_submission_log_table(self):
        """确保投递日志表存在"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 创建投递日志表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS submission_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        match_id INTEGER NOT NULL,
                        job_id VARCHAR(100) NOT NULL,
                        submission_status VARCHAR(20) NOT NULL,
                        message TEXT,
                        error_details TEXT,
                        execution_time FLOAT,
                        attempts INTEGER DEFAULT 1,
                        button_info TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (match_id) REFERENCES resume_matches (id)
                    )
                """)
                
                # 创建索引
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_submission_logs_match_id ON submission_logs(match_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_submission_logs_job_id ON submission_logs(job_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_submission_logs_status ON submission_logs(submission_status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_submission_logs_created_at ON submission_logs(created_at)")
                
                conn.commit()
                self.logger.debug("投递日志表已确保存在")
                
        except Exception as e:
            self.logger.error(f"确保投递日志表失败: {e}")
    
    def get_unprocessed_matches(self, limit: int = 50, priority_filter: Optional[str] = None) -> List[JobMatchRecord]:
        """
        获取未处理的匹配记录
        
        Args:
            limit: 限制数量
            priority_filter: 优先级过滤 ('high', 'medium', 'low')
            
        Returns:
            未处理的职位匹配记录列表
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 构建查询条件 - 只查询processed=0的记录
                where_conditions = ["rm.processed = 0"]
                params = []
                
                if priority_filter:
                    where_conditions.append("rm.priority_level = ?")
                    params.append(priority_filter)
                
                where_clause = " AND ".join(where_conditions)
                params.append(limit)
                
                # 查询未处理的匹配记录，关联jobs表获取URL等信息
                sql = f"""
                    SELECT 
                        rm.id, rm.job_id, rm.match_score, rm.priority_level,
                        rm.processed, rm.created_at,
                        j.title, j.company, j.url
                    FROM resume_matches rm
                    JOIN jobs j ON rm.job_id = j.job_id
                    WHERE {where_clause}
                    ORDER BY rm.match_score DESC, rm.created_at ASC
                    LIMIT ?
                """
                
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                records = []
                for row in rows:
                    row_dict = dict(row)
                    # 创建JobMatchRecord，使用现有字段
                    record = JobMatchRecord(
                        id=row_dict['id'],
                        job_id=row_dict['job_id'],
                        job_title=row_dict.get('title', ''),
                        company=row_dict.get('company', ''),
                        job_url=row_dict.get('url', ''),
                        match_score=row_dict.get('match_score', 0.0),
                        priority_level=row_dict.get('priority_level', 'low'),
                        processed=bool(row_dict.get('processed', 0))
                    )
                    records.append(record)
                
                self.logger.info(f"获取到 {len(records)} 个未处理的匹配记录")
                return records
                
        except Exception as e:
            self.logger.error(f"获取未处理匹配记录失败: {e}")
            return []
    
    def update_submission_result(self, result: SubmissionResult) -> bool:
        """
        更新投递结果
        
        Args:
            result: 投递结果
            
        Returns:
            是否更新成功
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                now = datetime.now().isoformat()
                
                # 如果投递成功，标记为已处理
                if result.status == SubmissionStatus.SUCCESS:
                    cursor.execute("""
                        UPDATE resume_matches 
                        SET processed = 1, processed_at = ?
                        WHERE id = ?
                    """, (now, result.match_id))
                
                # 插入投递日志
                cursor.execute("""
                    INSERT INTO submission_logs 
                    (match_id, job_id, submission_status, message, error_details, 
                     execution_time, attempts, button_info, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.match_id,
                    result.job_id,
                    result.status.value,
                    result.message,
                    result.error_details,
                    result.execution_time,
                    result.attempts,
                    str(result.button_info.__dict__) if result.button_info else None,
                    now
                ))
                
                conn.commit()
                
                self.logger.info(f"更新投递结果: {result.job_id} - {result.status.value}")
                return True
                
        except Exception as e:
            self.logger.error(f"更新投递结果失败: {e}")
            return False
    
    def get_submission_statistics(self, days: int = 1) -> Dict[str, Any]:
        """
        获取投递统计信息
        
        Args:
            days: 统计天数
            
        Returns:
            统计信息字典
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 总体统计
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_matches,
                        SUM(CASE WHEN processed = 1 THEN 1 ELSE 0 END) as processed_matches
                    FROM resume_matches
                """)
                
                overall_stats = dict(cursor.fetchone())
                
                # 从投递日志获取详细统计
                cursor.execute("""
                    SELECT 
                        submission_status,
                        COUNT(*) as count
                    FROM submission_logs 
                    WHERE created_at >= datetime('now', '-{} days')
                    GROUP BY submission_status
                """.format(days))
                
                recent_stats = {row['submission_status']: row['count'] for row in cursor.fetchall()}
                
                # 按优先级统计
                cursor.execute("""
                    SELECT 
                        rm.priority_level,
                        COUNT(*) as total,
                        SUM(CASE WHEN rm.processed = 1 THEN 1 ELSE 0 END) as processed
                    FROM resume_matches rm
                    GROUP BY rm.priority_level
                """)
                
                priority_stats = {}
                for row in cursor.fetchall():
                    priority = row['priority_level']
                    total = row['total']
                    processed = row['processed']
                    process_rate = (processed / total * 100) if total > 0 else 0
                    
                    priority_stats[priority] = {
                        'total': total,
                        'processed': processed,
                        'process_rate': round(process_rate, 2)
                    }
                
                # 平均执行时间
                cursor.execute("""
                    SELECT AVG(execution_time) as avg_execution_time
                    FROM submission_logs
                    WHERE execution_time > 0
                """)
                
                avg_time_result = cursor.fetchone()
                avg_execution_time = avg_time_result['avg_execution_time'] if avg_time_result else 0
                
                return {
                    'overall': overall_stats,
                    'recent_days': recent_stats,
                    'by_priority': priority_stats,
                    'avg_execution_time': round(avg_execution_time or 0, 2),
                    'statistics_period_days': days
                }
                
        except Exception as e:
            self.logger.error(f"获取投递统计失败: {e}")
            return {}
    
    def get_failed_submissions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取失败的投递记录
        
        Args:
            limit: 限制数量
            
        Returns:
            失败的投递记录列表
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        sl.match_id, sl.job_id, sl.submission_status,
                        sl.message, sl.error_details, sl.created_at,
                        j.title, j.company, j.url
                    FROM submission_logs sl
                    JOIN jobs j ON sl.job_id = j.job_id
                    WHERE sl.submission_status IN ('failed', 'button_not_found', 'login_required')
                    ORDER BY sl.created_at DESC
                    LIMIT ?
                """, (limit,))
                
                failed_records = []
                for row in cursor.fetchall():
                    failed_records.append(dict(row))
                
                return failed_records
                
        except Exception as e:
            self.logger.error(f"获取失败投递记录失败: {e}")
            return []
    
    def reset_failed_submissions(self, match_ids: Optional[List[int]] = None) -> int:
        """
        重置失败的投递记录，允许重新投递
        
        Args:
            match_ids: 要重置的匹配记录ID列表，None表示重置所有失败的
            
        Returns:
            重置的记录数
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                if match_ids:
                    # 重置指定的匹配记录
                    placeholders = ','.join('?' * len(match_ids))
                    cursor.execute(f"""
                        UPDATE resume_matches 
                        SET processed = 0, processed_at = NULL
                        WHERE id IN ({placeholders}) AND processed = 1
                    """, match_ids)
                else:
                    # 重置所有有失败日志但未标记为processed的记录
                    cursor.execute("""
                        UPDATE resume_matches 
                        SET processed = 0, processed_at = NULL
                        WHERE id IN (
                            SELECT DISTINCT match_id 
                            FROM submission_logs 
                            WHERE submission_status IN ('failed', 'button_not_found', 'login_required')
                        ) AND processed = 0
                    """)
                
                reset_count = cursor.rowcount
                conn.commit()
                
                self.logger.info(f"重置了 {reset_count} 个失败的投递记录")
                return reset_count
                
        except Exception as e:
            self.logger.error(f"重置失败投递记录失败: {e}")
            return 0
    
    def get_daily_submission_count(self, date: Optional[datetime] = None) -> int:
        """
        获取指定日期的投递数量
        
        Args:
            date: 指定日期，None表示今天
            
        Returns:
            投递数量
        """
        try:
            if date is None:
                date = datetime.now()
            
            date_str = date.date().isoformat()
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM submission_logs
                    WHERE DATE(created_at) = ? AND submission_status = 'success'
                """, (date_str,))
                
                result = cursor.fetchone()
                return result['count'] if result else 0
                
        except Exception as e:
            self.logger.error(f"获取每日投递数量失败: {e}")
            return 0
    
    def has_been_submitted(self, match_id: int) -> bool:
        """
        检查是否已经投递过
        
        Args:
            match_id: 匹配记录ID
            
        Returns:
            是否已投递过
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查是否有成功的投递记录
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM submission_logs
                    WHERE match_id = ? AND submission_status = 'success'
                """, (match_id,))
                
                result = cursor.fetchone()
                return result['count'] > 0 if result else False
                
        except Exception as e:
            self.logger.error(f"检查投递状态失败: {e}")
            return False
    
    def get_submission_attempts(self, match_id: int) -> int:
        """
        获取投递尝试次数
        
        Args:
            match_id: 匹配记录ID
            
        Returns:
            尝试次数
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM submission_logs
                    WHERE match_id = ?
                """, (match_id,))
                
                result = cursor.fetchone()
                return result['count'] if result else 0
                
        except Exception as e:
            self.logger.error(f"获取投递尝试次数失败: {e}")
            return 0
    
    def cleanup_old_logs(self, days: int = 30) -> int:
        """
        清理旧的投递日志
        
        Args:
            days: 保留天数
            
        Returns:
            删除的记录数
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM submission_logs 
                    WHERE created_at < datetime('now', '-{} days')
                """.format(days))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                self.logger.info(f"清理了 {deleted_count} 条旧的投递日志")
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"清理旧日志失败: {e}")
            return 0