"""
投递数据管理器

负责数据库查询、状态更新和投递记录管理
"""

import logging
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from contextlib import contextmanager

from .models import JobMatchRecord, SubmissionResult, SubmissionStatus, JobStatusResult
from .salary_filter import SalaryFilter, SalaryFilterResult
from ..database.operations import DatabaseManager
import json


class SubmissionDataManager:
    """投递数据管理器"""
    
    def __init__(self, db_path: str, config: Dict[str, Any] = None):
        """
        初始化数据管理器
        
        Args:
            db_path: 数据库文件路径
            config: 系统配置（用于薪资过滤）
        """
        self.db_path = db_path
        self.db_manager = DatabaseManager(db_path)
        self.logger = logging.getLogger(__name__)
        
        # 初始化薪资过滤器
        self.salary_filter = SalaryFilter(config or {}) if config else None
        
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
    
    def get_unprocessed_matches(self, limit: int = 50, priority_filter: Optional[str] = None, apply_salary_filter: bool = True) -> List[JobMatchRecord]:
        """
        获取未处理的匹配记录（支持薪资过滤）
        
        Args:
            limit: 限制数量（薪资过滤后的有效职位数量）
            priority_filter: 优先级过滤 ('high', 'medium', 'low')
            apply_salary_filter: 是否应用薪资过滤
            
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
                
                # 如果启用薪资过滤，直接在SQL中添加薪资条件，避免后续过滤遗漏
                if apply_salary_filter and self.salary_filter:
                    where_conditions.append("rm.salary_match_score > ?")
                    params.append(self.salary_filter.config.min_salary_match_score)
                    self.logger.debug(f"薪资过滤启用，SQL条件: salary_match_score > {self.salary_filter.config.min_salary_match_score}")
                
                where_clause = " AND ".join(where_conditions)
                query_limit = limit
                
                # 查询未处理的匹配记录，关联jobs表获取URL等信息，包含薪资匹配度
                # 过滤掉已删除的职位，按照与人工查询一致的排序：skill_match_score desc
                sql = f"""
                    SELECT
                        rm.id, rm.job_id, rm.match_score, rm.priority_level,
                        rm.processed, rm.created_at, rm.salary_match_score, rm.skill_match_score,
                        j.title, j.company, j.url
                    FROM resume_matches rm
                    JOIN jobs j ON rm.job_id = j.job_id
                    WHERE {where_clause} AND (j.is_deleted = 0 OR j.is_deleted IS NULL)
                    ORDER BY rm.skill_match_score DESC
                    LIMIT ?
                """
                
                params.append(query_limit)
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                records = []
                
                for row in rows:
                    row_dict = dict(row)
                    
                    # 如果在SQL中已经过滤了薪资，这里就不需要再次过滤
                    # 但仍然可以应用其他过滤逻辑（如分级阈值等）
                    if apply_salary_filter and self.salary_filter:
                        # 构建匹配数据用于高级薪资过滤（如分级阈值）
                        match_data = {
                            'job_id': row_dict['job_id'],
                            'job_title': row_dict.get('title', ''),
                            'salary_match_score': row_dict.get('salary_match_score', 0.0)
                        }
                        
                        salary_result, salary_info = self.salary_filter.evaluate_salary(match_data)
                        
                        # 由于SQL已经过滤了基本阈值，这里主要处理增强逻辑
                        if salary_result == SalaryFilterResult.REJECT:
                            # 这种情况应该很少发生，因为SQL已经过滤了
                            self.logger.debug(f"高级薪资过滤拒绝职位: {row_dict['job_id']} - {salary_info.get('reasoning', '')}")
                            continue
                    
                    # 创建JobMatchRecord
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
                    
                    # 达到限制数量就停止
                    if len(records) >= limit:
                        break
                
                filter_method = "SQL过滤" if apply_salary_filter and self.salary_filter else "无过滤"
                self.logger.info(f"获取到 {len(records)} 个未处理的匹配记录（{filter_method}）")
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
    
    def delete_suspended_job(self, match_id: int) -> bool:
        """
        删除暂停招聘的职位记录（软删除）
        
        Args:
            match_id: 匹配记录ID
            
        Returns:
            是否删除成功
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取job_id
                cursor.execute("SELECT job_id FROM resume_matches WHERE id = ?", (match_id,))
                result = cursor.fetchone()
                if not result:
                    self.logger.warning(f"未找到匹配记录: match_id={match_id}")
                    return False
                
                job_id = result['job_id']
                now = datetime.now().isoformat()
                
                # 标记职位为已删除（软删除）
                cursor.execute("""
                    UPDATE jobs
                    SET is_deleted = 1, deleted_at = ?
                    WHERE job_id = ?
                """, (now, job_id))
                
                job_updated = cursor.rowcount > 0
                
                # 删除匹配记录
                cursor.execute("DELETE FROM resume_matches WHERE id = ?", (match_id,))
                match_deleted = cursor.rowcount > 0
                
                conn.commit()
                
                if job_updated and match_deleted:
                    self.logger.info(f"删除暂停职位记录: match_id={match_id}, job_id={job_id} (软删除)")
                    return True
                elif match_deleted:
                    self.logger.info(f"删除匹配记录: match_id={match_id}, 但职位可能已被删除")
                    return True
                else:
                    self.logger.warning(f"未找到要删除的记录: match_id={match_id}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"删除暂停职位失败: {e}")
            return False

    def mark_as_processed(self, match_id: int, success: bool = True, status_info: str = None) -> bool:
        """
        标记职位为已处理
        
        Args:
            match_id: 匹配记录ID
            success: 是否成功处理
            status_info: 状态信息
            
        Returns:
            是否更新成功
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                now = datetime.now().isoformat()
                
                cursor.execute("""
                    UPDATE resume_matches
                    SET processed = 1, processed_at = ?
                    WHERE id = ?
                """, (now, match_id))
                
                updated_count = cursor.rowcount
                conn.commit()
                
                if updated_count > 0:
                    action = "成功处理" if success else "标记处理"
                    self.logger.info(f"{action}职位记录: match_id={match_id}")
                    return True
                else:
                    self.logger.warning(f"未找到要更新的记录: match_id={match_id}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"标记职位处理状态失败: {e}")
            return False

    def log_job_status_detection(self, job_record: JobMatchRecord, status_result: JobStatusResult, action: str):
        """
        记录职位状态检测结果到日志
        
        Args:
            job_record: 职位记录
            status_result: 状态检测结果
            action: 执行的动作
        """
        try:
            # 创建日志记录
            log_entry = {
                'timestamp': status_result.timestamp,
                'job_id': job_record.job_id,
                'job_title': job_record.job_title,
                'company': job_record.company,
                'job_url': job_record.job_url,
                'match_id': job_record.id,
                'action': action,
                'detection_result': status_result.to_dict()
            }
            
            # 写入投递日志表
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO submission_logs
                    (match_id, job_id, submission_status, message, error_details,
                     execution_time, attempts, button_info, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job_record.id,
                    job_record.job_id,
                    status_result.status.value,
                    status_result.reason,
                    status_result.page_content_snippet,
                    status_result.detection_time,
                    1,  # 检测尝试次数
                    json.dumps(status_result.to_dict(), ensure_ascii=False),
                    status_result.timestamp
                ))
                
                conn.commit()
            
            # 同时写入文件日志
            self._write_status_log_file(log_entry)
            
        except Exception as e:
            self.logger.error(f"记录状态检测日志失败: {e}")

    def _write_status_log_file(self, log_entry: Dict[str, Any]):
        """写入状态检测日志文件"""
        try:
            from pathlib import Path
            
            # 确保logs目录存在
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            
            # 按日期分文件
            log_file = logs_dir / f"job_status_{datetime.now().strftime('%Y%m%d')}.log"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
                
        except Exception as e:
            self.logger.error(f"写入状态日志文件失败: {e}")