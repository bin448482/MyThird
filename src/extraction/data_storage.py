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
        保存到SQLite数据库（使用CLAUDE.md中定义的表结构）
        
        Args:
            results: 结果数据
            keyword: 搜索关键词
            
        Returns:
            是否保存成功
        """
        try:
            # 确保数据库目录存在
            db_path = Path(self.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                # 创建表（如果不存在）
                self._create_tables(conn)
                
                # 插入数据
                cursor = conn.cursor()
                
                for result in results:
                    # 生成job_id（基于URL的哈希值）
                    job_url = result.get('url', '')
                    job_id = self._generate_job_id(job_url, result.get('title', ''), result.get('company', ''))
                    
                    # 插入职位数据（使用CLAUDE.md中定义的表结构）
                    cursor.execute("""
                        INSERT OR REPLACE INTO jobs (
                            job_id, title, company, url, application_status, 
                            match_score, website, created_at, submitted_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        job_id,
                        result.get('title', ''),
                        result.get('company', ''),
                        job_url,
                        'pending',  # 默认状态
                        None,  # 匹配度评分待后续计算
                        'qiancheng',  # 来源网站
                        datetime.now().isoformat(),
                        None  # 投递时间
                    ))
                
                conn.commit()
                self.logger.debug(f"数据库已保存 {len(results)} 条记录")
                return True
                
        except Exception as e:
            self.logger.error(f"保存到数据库失败: {e}")
            return False
    
    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """
        创建数据库表（基于CLAUDE.md中的定义）
        
        Args:
            conn: 数据库连接
        """
        cursor = conn.cursor()
        
        # 创建职位表（按照CLAUDE.md中的定义）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id VARCHAR(100) UNIQUE NOT NULL,
                title VARCHAR(200) NOT NULL,
                company VARCHAR(200) NOT NULL,
                url VARCHAR(500) NOT NULL,
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
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_job_id ON jobs(job_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_website ON jobs(website)")
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