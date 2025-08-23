"""
数据存储器

负责保存、管理和查询提取的职位数据
基于CLAUDE.md中定义的数据库表结构
"""

import json
import csv
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import hashlib

from ..core.exceptions import DataStorageError
from ..utils.fingerprint import generate_job_fingerprint, extract_job_key_info
from ..database.operations import DatabaseManager


class DataStorage:
    """数据存储器"""
    
    def __init__(self, config: dict):
        """
        初始化数据存储器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.database_config = config.get('database', {})
        self.search_config = config.get('search', {})
        self.logger = logging.getLogger(__name__)
        
        # 数据目录
        self.data_dir = Path("data")
        self.search_results_dir = self.data_dir / "search_results"
        self.job_details_dir = self.data_dir / "job_details"
        
        # 创建目录
        self._ensure_directories()
        
        # 数据库路径
        self.db_path = self.database_config.get('path', './data/jobs.db')
    
    def _ensure_directories(self) -> None:
        """确保数据目录存在"""
        try:
            self.data_dir.mkdir(exist_ok=True)
            self.search_results_dir.mkdir(exist_ok=True)
            self.job_details_dir.mkdir(exist_ok=True)
            self.logger.debug("数据目录已创建")
        except Exception as e:
            self.logger.error(f"创建数据目录失败: {e}")
    
    def save_search_results(self, 
                          results: List[Dict[str, Any]], 
                          keyword: str,
                          format: str = 'json') -> Optional[str]:
        """
        保存搜索结果
        
        Args:
            results: 搜索结果列表
            keyword: 搜索关键词
            format: 保存格式 ('json', 'csv', 'both')
            
        Returns:
            保存的文件路径，失败时返回None
        """
        if not results:
            self.logger.warning("搜索结果为空，跳过保存")
            return None
        
        try:
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_keyword = self._sanitize_filename(keyword)
            base_filename = f"search_{safe_keyword}_{timestamp}"
            
            saved_files = []
            
            # 保存为JSON格式
            if format in ['json', 'both']:
                json_file = self.search_results_dir / f"{base_filename}.json"
                if self._save_as_json(results, json_file, keyword):
                    saved_files.append(str(json_file))
            
            # 保存为CSV格式
            if format in ['csv', 'both']:
                csv_file = self.search_results_dir / f"{base_filename}.csv"
                if self._save_as_csv(results, csv_file):
                    saved_files.append(str(csv_file))
            
            # 保存到数据库
            if self.database_config.get('enabled', True):
                self._save_to_database(results, keyword)
            
            if saved_files:
                self.logger.info(f"💾 搜索结果已保存: {', '.join(saved_files)}")
                return saved_files[0]  # 返回第一个文件路径
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"❌ 保存搜索结果失败: {e}")
            raise DataStorageError(f"保存搜索结果失败: {e}")
    
    def _save_as_json(self, results: List[Dict], filepath: Path, keyword: str) -> bool:
        """
        保存为JSON格式
        
        Args:
            results: 结果数据
            filepath: 文件路径
            keyword: 搜索关键词
            
        Returns:
            是否保存成功
        """
        try:
            # 添加元数据
            data = {
                'metadata': {
                    'keyword': keyword,
                    'total_count': len(results),
                    'extracted_at': datetime.now().isoformat(),
                    'source': 'qiancheng_automation'
                },
                'results': results
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.debug(f"JSON文件已保存: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存JSON文件失败: {e}")
            return False
    
    def _save_as_csv(self, results: List[Dict], filepath: Path) -> bool:
        """
        保存为CSV格式
        
        Args:
            results: 结果数据
            filepath: 文件路径
            
        Returns:
            是否保存成功
        """
        try:
            if not results:
                return False
            
            # 获取所有字段名
            fieldnames = set()
            for result in results:
                fieldnames.update(result.keys())
            
            fieldnames = sorted(list(fieldnames))
            
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)
            
            self.logger.debug(f"CSV文件已保存: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存CSV文件失败: {e}")
            return False
    
    def _save_to_database(self, results: List[Dict], keyword: str) -> bool:
        """
        保存到SQLite数据库（使用指纹去重）
        
        Args:
            results: 结果数据
            keyword: 搜索关键词
            
        Returns:
            是否保存成功
        """
        try:
            # 使用DatabaseManager进行操作
            db_manager = DatabaseManager(self.db_path)
            db_manager.init_database()
            
            saved_count = 0
            skipped_count = 0
            
            for result in results:
                # 生成job_id和指纹
                job_url = result.get('url', '')
                job_id = self._generate_job_id(job_url, result.get('title', ''), result.get('company', ''))
                
                # 生成职位指纹
                job_fingerprint = generate_job_fingerprint(
                    result.get('title', ''),
                    result.get('company', ''),
                    result.get('salary', ''),
                    result.get('location', '')
                )
                
                # 检查指纹是否已存在
                if db_manager.fingerprint_exists(job_fingerprint):
                    skipped_count += 1
                    self.logger.debug(f"跳过重复职位: {result.get('title', '')} - {result.get('company', '')}")
                    continue
                
                # 准备职位数据
                job_data = {
                    'job_id': job_id,
                    'title': result.get('title', ''),
                    'company': result.get('company', ''),
                    'url': job_url,
                    'job_fingerprint': job_fingerprint,
                    'application_status': 'pending',
                    'match_score': None,
                    'website': result.get('source', 'qiancheng'),
                    'created_at': datetime.now().isoformat(),
                    'submitted_at': None
                }
                
                # 保存到数据库
                if db_manager.save_job(job_data):
                    saved_count += 1
                
                # 保存详细信息到扩展表
                self._save_job_details_with_fingerprint(result, job_id, job_fingerprint, keyword)
            
            self.logger.info(f"数据库保存完成: 新增 {saved_count} 条，跳过重复 {skipped_count} 条")
            return True
                
        except Exception as e:
            self.logger.error(f"保存到数据库失败: {e}")
            return False
    
    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """
        创建数据库表（基于CLAUDE.md中的定义，包含job_fingerprint字段）
        
        Args:
            conn: 数据库连接
        """
        cursor = conn.cursor()
        
        # 创建职位表（按照CLAUDE.md中的定义，包含指纹字段）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id VARCHAR(100) UNIQUE NOT NULL,
                title VARCHAR(200) NOT NULL,
                company VARCHAR(200) NOT NULL,
                url VARCHAR(500) NOT NULL,
                job_fingerprint VARCHAR(12) UNIQUE,
                application_status VARCHAR(50) DEFAULT 'pending',
                match_score FLOAT,
                website VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                submitted_at TIMESTAMP
            )
        """)
        
        # 创建扩展信息表（存储额外的职位信息）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id VARCHAR(100) NOT NULL,
                salary TEXT,
                location TEXT,
                experience TEXT,
                education TEXT,
                description TEXT,
                requirements TEXT,
                benefits TEXT,
                publish_time TEXT,
                company_scale TEXT,
                industry TEXT,
                keyword TEXT,
                extracted_at TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs (job_id)
            )
        """)
        
        # 创建搜索历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                results_count INTEGER,
                search_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                file_path TEXT
            )
        """)
        
        # 创建索引（包含指纹索引）
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_job_id ON jobs(job_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_website ON jobs(website)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_fingerprint ON jobs(job_fingerprint)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_details_job_id ON job_details(job_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_details_keyword ON job_details(keyword)")
        
        conn.commit()
    
    def _generate_job_id(self, url: str, title: str, company: str) -> str:
        """
        生成职位唯一标识
        
        Args:
            url: 职位URL
            title: 职位标题
            company: 公司名称
            
        Returns:
            职位ID
        """
        # 优先从URL中提取ID
        if url:
            import re
            match = re.search(r'/(\d+)\.html?', url)
            if match:
                return f"qc_{match.group(1)}"
            
            match = re.search(r'jobid[=:](\d+)', url, re.IGNORECASE)
            if match:
                return f"qc_{match.group(1)}"
        
        # 如果无法从URL提取，则基于标题和公司生成哈希
        content = f"{title}_{company}_{url}"
        hash_obj = hashlib.md5(content.encode('utf-8'))
        return f"qc_{hash_obj.hexdigest()[:12]}"
    
    def save_job_details(self, results: List[Dict[str, Any]], keyword: str) -> bool:
        """
        保存职位详细信息到扩展表
        
        Args:
            results: 职位详细信息列表
            keyword: 搜索关键词
            
        Returns:
            是否保存成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for result in results:
                    job_url = result.get('url', '')
                    job_id = self._generate_job_id(job_url, result.get('title', ''), result.get('company', ''))
                    
                    # 插入或更新职位详细信息
                    cursor.execute("""
                        INSERT OR REPLACE INTO job_details (
                            job_id, salary, location, experience, education,
                            description, requirements, benefits, publish_time,
                            company_scale, industry, keyword, extracted_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        job_id,
                        result.get('salary', ''),
                        result.get('location', ''),
                        result.get('experience', ''),
                        result.get('education', ''),
                        result.get('description', ''),
                        result.get('requirements', ''),
                        result.get('benefits', ''),
                        result.get('publish_time', ''),
                        result.get('company_scale', ''),
                        result.get('industry', ''),
                        keyword,
                        result.get('extracted_at', datetime.now().isoformat())
                    ))
                
                conn.commit()
                self.logger.debug(f"职位详细信息已保存 {len(results)} 条记录")
                return True
                
        except Exception as e:
            self.logger.error(f"保存职位详细信息失败: {e}")
            return False
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        清理文件名，移除非法字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            清理后的文件名
        """
        import re
        # 移除或替换非法字符
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 限制长度
        return sanitized[:50] if len(sanitized) > 50 else sanitized
    
    def load_search_results(self, filepath: str) -> Optional[Dict[str, Any]]:
        """
        加载搜索结果
        
        Args:
            filepath: 文件路径
            
        Returns:
            搜索结果数据
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.logger.info(f"📂 搜索结果已加载: {filepath}")
            return data
            
        except Exception as e:
            self.logger.error(f"❌ 加载搜索结果失败: {e}")
            return None
    
    def query_jobs(self, 
                   keyword: Optional[str] = None,
                   company: Optional[str] = None,
                   location: Optional[str] = None,
                   status: Optional[str] = None,
                   limit: int = 100) -> List[Dict[str, Any]]:
        """
        查询职位数据
        
        Args:
            keyword: 关键词过滤
            company: 公司名过滤
            location: 地点过滤
            status: 状态过滤
            limit: 结果数量限制
            
        Returns:
            职位数据列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row  # 返回字典格式
                cursor = conn.cursor()
                
                # 构建查询条件
                conditions = []
                params = []
                
                if keyword:
                    conditions.append("(j.title LIKE ? OR jd.keyword LIKE ?)")
                    params.extend([f"%{keyword}%", f"%{keyword}%"])
                
                if company:
                    conditions.append("j.company LIKE ?")
                    params.append(f"%{company}%")
                
                if location:
                    conditions.append("jd.location LIKE ?")
                    params.append(f"%{location}%")
                
                if status:
                    conditions.append("j.application_status = ?")
                    params.append(status)
                
                # 构建SQL查询（联合查询主表和详情表）
                sql = """
                    SELECT j.*, jd.salary, jd.location, jd.experience, jd.education,
                           jd.description, jd.requirements, jd.benefits, jd.publish_time,
                           jd.company_scale, jd.industry, jd.keyword
                    FROM jobs j
                    LEFT JOIN job_details jd ON j.job_id = jd.job_id
                """
                
                if conditions:
                    sql += " WHERE " + " AND ".join(conditions)
                sql += " ORDER BY j.created_at DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                # 转换为字典列表
                results = [dict(row) for row in rows]
                
                self.logger.info(f"📊 查询到 {len(results)} 条职位记录")
                return results
                
        except Exception as e:
            self.logger.error(f"❌ 查询职位数据失败: {e}")
            return []
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """
        获取搜索统计信息
        
        Returns:
            统计信息字典
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 总职位数
                cursor.execute("SELECT COUNT(*) FROM jobs")
                total_jobs = cursor.fetchone()[0]
                
                # 按网站统计
                cursor.execute("""
                    SELECT website, COUNT(*) as count 
                    FROM jobs 
                    GROUP BY website 
                    ORDER BY count DESC
                """)
                website_stats = cursor.fetchall()
                
                # 按状态统计
                cursor.execute("""
                    SELECT application_status, COUNT(*) as count 
                    FROM jobs 
                    GROUP BY application_status 
                    ORDER BY count DESC
                """)
                status_stats = cursor.fetchall()
                
                # 按公司统计（前10）
                cursor.execute("""
                    SELECT company, COUNT(*) as count 
                    FROM jobs 
                    WHERE company != '' 
                    GROUP BY company 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                company_stats = cursor.fetchall()
                
                # 按关键词统计（前10）
                cursor.execute("""
                    SELECT keyword, COUNT(*) as count 
                    FROM job_details 
                    WHERE keyword != '' 
                    GROUP BY keyword 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                keyword_stats = cursor.fetchall()
                
                return {
                    'total_jobs': total_jobs,
                    'website_stats': website_stats,
                    'status_stats': status_stats,
                    'company_stats': company_stats,
                    'keyword_stats': keyword_stats,
                    'generated_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"❌ 获取统计信息失败: {e}")
            return {}
    
    def update_job_status(self, job_id: str, status: str, submitted_at: Optional[str] = None) -> bool:
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
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if submitted_at:
                    cursor.execute("""
                        UPDATE jobs 
                        SET application_status = ?, submitted_at = ? 
                        WHERE job_id = ?
                    """, (status, submitted_at, job_id))
                else:
                    cursor.execute("""
                        UPDATE jobs 
                        SET application_status = ? 
                        WHERE job_id = ?
                    """, (status, job_id))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    self.logger.info(f"职位状态已更新: {job_id} -> {status}")
                    return True
                else:
                    self.logger.warning(f"未找到职位: {job_id}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"更新职位状态失败: {e}")
            return False
    
    def list_saved_files(self, directory: str = "search_results") -> List[Dict[str, Any]]:
        """
        列出保存的文件
        
        Args:
            directory: 目录名 ('search_results' 或 'job_details')
            
        Returns:
            文件信息列表
        """
        try:
            if directory == "search_results":
                target_dir = self.search_results_dir
            elif directory == "job_details":
                target_dir = self.job_details_dir
            else:
                target_dir = self.data_dir / directory
            
            if not target_dir.exists():
                return []
            
            files = []
            for file_path in target_dir.glob("*.json"):
                try:
                    stat = file_path.stat()
                    files.append({
                        'filename': file_path.name,
                        'filepath': str(file_path),
                        'size': stat.st_size,
                        'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'created_time': datetime.fromtimestamp(stat.st_ctime).isoformat()
                    })
                except Exception as e:
                    self.logger.warning(f"获取文件信息失败 {file_path}: {e}")
            
            # 按修改时间排序
            files.sort(key=lambda x: x['modified_time'], reverse=True)
            
            return files
            
        except Exception as e:
            self.logger.error(f"❌ 列出文件失败: {e}")
            return []
    
    def _save_job_details_with_fingerprint(self, result: Dict, job_id: str, job_fingerprint: str, keyword: str) -> bool:
        """
        保存职位详细信息（包含指纹）
        
        Args:
            result: 职位详细信息
            job_id: 职位ID
            job_fingerprint: 职位指纹
            keyword: 搜索关键词
            
        Returns:
            是否保存成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 先检查是否已存在，避免重复插入
                cursor.execute("SELECT id FROM job_details WHERE job_id = ?", (job_id,))
                existing_record = cursor.fetchone()
                
                if existing_record:
                    # 更新现有记录
                    cursor.execute("""
                        UPDATE job_details SET
                            salary = ?, location = ?, experience = ?, education = ?,
                            description = ?, requirements = ?, benefits = ?, publish_time = ?,
                            company_scale = ?, industry = ?, keyword = ?, extracted_at = ?
                        WHERE job_id = ?
                    """, (
                        result.get('salary', ''),
                        result.get('location', ''),
                        result.get('experience', ''),
                        result.get('education', ''),
                        result.get('description', ''),
                        result.get('requirements', ''),
                        result.get('benefits', ''),
                        result.get('publish_time', ''),
                        result.get('company_scale', ''),
                        result.get('industry', ''),
                        keyword,
                        result.get('extracted_at', datetime.now().isoformat()),
                        job_id
                    ))
                else:
                    # 插入新记录
                    cursor.execute("""
                        INSERT INTO job_details (
                            job_id, salary, location, experience, education,
                            description, requirements, benefits, publish_time,
                            company_scale, industry, keyword, extracted_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                    job_id,
                    result.get('salary', ''),
                    result.get('location', ''),
                    result.get('experience', ''),
                    result.get('education', ''),
                    result.get('description', ''),
                    result.get('requirements', ''),
                    result.get('benefits', ''),
                    result.get('publish_time', ''),
                    result.get('company_scale', ''),
                    result.get('industry', ''),
                    keyword,
                    result.get('extracted_at', datetime.now().isoformat())
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"保存职位详细信息失败: {e}")
            return False
    
    def save_job_detail(self, detail_data: Dict[str, Any], job_url: str) -> bool:
        """
        保存单个职位详情到数据库（替代JSON文件保存）
        
        Args:
            detail_data: 职位详情数据
            job_url: 职位URL
            
        Returns:
            是否保存成功
        """
        try:
            # 使用DatabaseManager
            db_manager = DatabaseManager(self.db_path)
            db_manager.init_database()
            
            # 生成job_id和指纹
            job_id = self._generate_job_id(
                job_url,
                detail_data.get('title', ''),
                detail_data.get('company', '')
            )
            
            # 从详情数据中提取基本信息生成指纹
            job_fingerprint = generate_job_fingerprint(
                detail_data.get('title', ''),
                detail_data.get('company', ''),
                detail_data.get('salary', ''),
                detail_data.get('location', '')
            )
            
            # 检查是否已存在
            if db_manager.fingerprint_exists(job_fingerprint):
                self.logger.debug(f"职位详情已存在，跳过保存: {detail_data.get('title', '')}")
                return True
            
            # 准备职位数据
            job_data = {
                'job_id': job_id,
                'title': detail_data.get('title', ''),
                'company': detail_data.get('company', ''),
                'url': job_url,
                'job_fingerprint': job_fingerprint,
                'application_status': 'pending',
                'match_score': None,
                'website': 'qiancheng',
                'created_at': datetime.now().isoformat(),
                'submitted_at': None
            }
            
            # 保存到数据库
            success = db_manager.save_job(job_data)
            
            if success:
                # 保存详细信息
                self._save_job_details_with_fingerprint(detail_data, job_id, job_fingerprint, "detail_extraction")
                self.logger.info(f"职位详情已保存到数据库: {detail_data.get('title', '')}")
            
            return success
                
        except Exception as e:
            self.logger.error(f"保存职位详情失败: {e}")
            return False
    
    def update_job_url(self, job_id: str, job_url: str) -> bool:
        """
        更新职位的URL
        
        Args:
            job_id: 职位ID
            job_url: 职位URL
            
        Returns:
            是否更新成功
        """
        try:
            db_manager = DatabaseManager(self.db_path)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE jobs
                    SET url = ?
                    WHERE job_id = ?
                """, (job_url, job_id))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    self.logger.debug(f"职位URL已更新: {job_id} -> {job_url}")
                    return True
                else:
                    self.logger.warning(f"未找到职位进行URL更新: {job_id}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"更新职位URL失败: {e}")
            return False
    
    def update_job_with_detail_url(self, title: str, company: str, detail_url: str) -> bool:
        """
        根据标题和公司名称更新职位的详情URL
        
        Args:
            title: 职位标题
            company: 公司名称
            detail_url: 详情页URL
            
        Returns:
            是否更新成功
        """
        try:
            db_manager = DatabaseManager(self.db_path)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 查找匹配的职位记录
                cursor.execute("""
                    SELECT job_id FROM jobs
                    WHERE title = ? AND company = ? AND (url = '' OR url IS NULL)
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (title, company))
                
                result = cursor.fetchone()
                if result:
                    job_id = result[0]
                    
                    # 更新URL
                    cursor.execute("""
                        UPDATE jobs
                        SET url = ?
                        WHERE job_id = ?
                    """, (detail_url, job_id))
                    
                    conn.commit()
                    
                    if cursor.rowcount > 0:
                        self.logger.info(f"职位URL已更新: {title} @ {company} -> {detail_url}")
                        return True
                
                self.logger.warning(f"未找到匹配的职位记录: {title} @ {company}")
                return False
                    
        except Exception as e:
            self.logger.error(f"更新职位详情URL失败: {e}")
            return False
    
    def check_job_fingerprint_exists(self, title: str, company: str, salary: str = "", location: str = "") -> bool:
        """
        检查职位指纹是否已存在
        
        Args:
            title: 职位标题
            company: 公司名称
            salary: 薪资信息
            location: 工作地点
            
        Returns:
            是否已存在
        """
        try:
            fingerprint = generate_job_fingerprint(title, company, salary, location)
            db_manager = DatabaseManager(self.db_path)
            return db_manager.fingerprint_exists(fingerprint)
        except Exception as e:
            self.logger.error(f"检查职位指纹失败: {e}")
            return False
    
    def get_deduplication_stats(self) -> Dict[str, Any]:
        """
        获取去重统计信息
        
        Returns:
            去重统计数据
        """
        try:
            db_manager = DatabaseManager(self.db_path)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 总职位数
                cursor.execute("SELECT COUNT(*) FROM jobs")
                total_jobs = cursor.fetchone()[0]
                
                # 有指纹的职位数
                cursor.execute("SELECT COUNT(*) FROM jobs WHERE job_fingerprint IS NOT NULL")
                jobs_with_fingerprint = cursor.fetchone()[0]
                
                # 唯一指纹数
                cursor.execute("SELECT COUNT(DISTINCT job_fingerprint) FROM jobs WHERE job_fingerprint IS NOT NULL")
                unique_fingerprints = cursor.fetchone()[0]
                
                # 重复职位数
                duplicate_count = db_manager.get_duplicate_jobs_count()
                
                return {
                    'total_jobs': total_jobs,
                    'jobs_with_fingerprint': jobs_with_fingerprint,
                    'unique_fingerprints': unique_fingerprints,
                    'duplicate_jobs': duplicate_count,
                    'deduplication_rate': (duplicate_count / max(total_jobs, 1)) * 100,
                    'generated_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"获取去重统计失败: {e}")
            return {}