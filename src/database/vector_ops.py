"""
向量数据库操作模块

提供向量数据库的高级操作接口，包括数据管理、查询优化和性能监控。
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime, timedelta
import json
import sqlite3
import os
from pathlib import Path

from ..rag.vector_manager import ChromaDBManager

logger = logging.getLogger(__name__)


class VectorDatabaseOperations:
    """向量数据库操作类"""
    
    def __init__(self, vector_manager: ChromaDBManager, config: Dict = None):
        """
        初始化向量数据库操作
        
        Args:
            vector_manager: 向量存储管理器
            config: 配置字典
        """
        self.vector_manager = vector_manager
        self.config = config or {}
        
        # 初始化SQLite数据库用于元数据管理
        self.metadata_db_path = self.config.get('metadata_db_path', 'data/vector_metadata.db')
        self._init_metadata_db()
        
        # 操作统计
        self.operation_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'last_operation_time': None
        }
        
        logger.info("向量数据库操作模块初始化完成")
    
    def _init_metadata_db(self):
        """初始化元数据数据库"""
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.metadata_db_path), exist_ok=True)
        
        with sqlite3.connect(self.metadata_db_path) as conn:
            cursor = conn.cursor()
            
            # 创建向量文档元数据表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vector_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id TEXT UNIQUE NOT NULL,
                    job_id TEXT,
                    doc_type TEXT,
                    content_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata_json TEXT,
                    vector_id TEXT,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # 创建操作日志表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS operation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT NOT NULL,
                    operation_details TEXT,
                    success BOOLEAN,
                    error_message TEXT,
                    execution_time REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建性能监控表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    metric_value REAL,
                    metric_unit TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def add_job_with_metadata(self, job_data: Dict[str, Any], 
                            documents: List[Dict[str, Any]], 
                            job_id: str) -> Dict[str, Any]:
        """
        添加职位及其元数据
        
        Args:
            job_data: 职位数据
            documents: 文档列表
            job_id: 职位ID
            
        Returns:
            Dict: 操作结果
        """
        operation_start = datetime.now()
        
        try:
            self.operation_stats['total_operations'] += 1
            
            # 1. 添加文档到向量数据库
            doc_ids = self.vector_manager.add_job_documents(documents, job_id)
            
            # 2. 记录元数据到SQLite
            self._record_document_metadata(documents, doc_ids, job_id)
            
            # 3. 记录操作日志
            execution_time = (datetime.now() - operation_start).total_seconds()
            self._log_operation(
                operation_type='add_job',
                operation_details=f'Added job {job_id} with {len(documents)} documents',
                success=True,
                execution_time=execution_time
            )
            
            self.operation_stats['successful_operations'] += 1
            self.operation_stats['last_operation_time'] = datetime.now().isoformat()
            
            return {
                'success': True,
                'job_id': job_id,
                'document_count': len(documents),
                'document_ids': doc_ids,
                'execution_time': execution_time
            }
            
        except Exception as e:
            execution_time = (datetime.now() - operation_start).total_seconds()
            
            self._log_operation(
                operation_type='add_job',
                operation_details=f'Failed to add job {job_id}',
                success=False,
                error_message=str(e),
                execution_time=execution_time
            )
            
            self.operation_stats['failed_operations'] += 1
            
            logger.error(f"添加职位失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'execution_time': execution_time
            }
    
    def _record_document_metadata(self, documents: List[Dict[str, Any]], 
                                doc_ids: List[str], job_id: str):
        """记录文档元数据"""
        
        with sqlite3.connect(self.metadata_db_path) as conn:
            cursor = conn.cursor()
            
            for i, (doc, doc_id) in enumerate(zip(documents, doc_ids)):
                metadata = doc.get('metadata', {})
                content = doc.get('page_content', '')
                
                # 计算内容哈希
                import hashlib
                content_hash = hashlib.md5(content.encode()).hexdigest()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO vector_documents 
                    (doc_id, job_id, doc_type, content_hash, metadata_json, vector_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    metadata.get('doc_id', f'{job_id}_doc_{i}'),
                    job_id,
                    metadata.get('type', 'unknown'),
                    content_hash,
                    json.dumps(metadata),
                    doc_id
                ))
            
            conn.commit()
    
    def update_job_documents(self, job_id: str, 
                           new_documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        更新职位文档
        
        Args:
            job_id: 职位ID
            new_documents: 新文档列表
            
        Returns:
            Dict: 操作结果
        """
        operation_start = datetime.now()
        
        try:
            # 1. 删除旧文档
            delete_result = self.delete_job_documents(job_id)
            
            if not delete_result['success']:
                raise Exception(f"删除旧文档失败: {delete_result.get('error')}")
            
            # 2. 添加新文档
            doc_ids = self.vector_manager.add_job_documents(new_documents, job_id)
            
            # 3. 更新元数据
            self._record_document_metadata(new_documents, doc_ids, job_id)
            
            execution_time = (datetime.now() - operation_start).total_seconds()
            
            self._log_operation(
                operation_type='update_job',
                operation_details=f'Updated job {job_id} with {len(new_documents)} documents',
                success=True,
                execution_time=execution_time
            )
            
            return {
                'success': True,
                'job_id': job_id,
                'updated_documents': len(new_documents),
                'document_ids': doc_ids,
                'execution_time': execution_time
            }
            
        except Exception as e:
            execution_time = (datetime.now() - operation_start).total_seconds()
            
            self._log_operation(
                operation_type='update_job',
                operation_details=f'Failed to update job {job_id}',
                success=False,
                error_message=str(e),
                execution_time=execution_time
            )
            
            logger.error(f"更新职位文档失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'execution_time': execution_time
            }
    
    def delete_job_documents(self, job_id: str) -> Dict[str, Any]:
        """
        删除职位文档
        
        Args:
            job_id: 职位ID
            
        Returns:
            Dict: 操作结果
        """
        operation_start = datetime.now()
        
        try:
            # 1. 从向量数据库删除
            success = self.vector_manager.delete_documents(job_id)
            
            if not success:
                raise Exception("从向量数据库删除文档失败")
            
            # 2. 更新元数据状态
            with sqlite3.connect(self.metadata_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE vector_documents 
                    SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                    WHERE job_id = ?
                ''', (job_id,))
                deleted_count = cursor.rowcount
                conn.commit()
            
            execution_time = (datetime.now() - operation_start).total_seconds()
            
            self._log_operation(
                operation_type='delete_job',
                operation_details=f'Deleted job {job_id} documents',
                success=True,
                execution_time=execution_time
            )
            
            return {
                'success': True,
                'job_id': job_id,
                'deleted_documents': deleted_count,
                'execution_time': execution_time
            }
            
        except Exception as e:
            execution_time = (datetime.now() - operation_start).total_seconds()
            
            self._log_operation(
                operation_type='delete_job',
                operation_details=f'Failed to delete job {job_id}',
                success=False,
                error_message=str(e),
                execution_time=execution_time
            )
            
            logger.error(f"删除职位文档失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'execution_time': execution_time
            }
    
    def get_job_documents_metadata(self, job_id: str) -> List[Dict[str, Any]]:
        """
        获取职位文档元数据
        
        Args:
            job_id: 职位ID
            
        Returns:
            List[Dict]: 文档元数据列表
        """
        try:
            with sqlite3.connect(self.metadata_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT doc_id, doc_type, content_hash, created_at, 
                           updated_at, metadata_json, vector_id, is_active
                    FROM vector_documents 
                    WHERE job_id = ? AND is_active = TRUE
                    ORDER BY created_at
                ''', (job_id,))
                
                results = []
                for row in cursor.fetchall():
                    metadata = {
                        'doc_id': row[0],
                        'doc_type': row[1],
                        'content_hash': row[2],
                        'created_at': row[3],
                        'updated_at': row[4],
                        'vector_id': row[6],
                        'is_active': bool(row[7])
                    }
                    
                    # 解析JSON元数据
                    try:
                        metadata['original_metadata'] = json.loads(row[5])
                    except:
                        metadata['original_metadata'] = {}
                    
                    results.append(metadata)
                
                return results
                
        except Exception as e:
            logger.error(f"获取职位文档元数据失败: {e}")
            return []
    
    def search_with_metadata_filter(self, query: str, 
                                  metadata_filters: Dict[str, Any] = None,
                                  k: int = 10) -> List[Dict[str, Any]]:
        """
        带元数据过滤的搜索
        
        Args:
            query: 搜索查询
            metadata_filters: 元数据过滤条件
            k: 返回结果数量
            
        Returns:
            List[Dict]: 搜索结果
        """
        try:
            # 构建ChromaDB过滤条件
            chroma_filters = {}
            
            if metadata_filters:
                # 转换元数据过滤条件为ChromaDB格式
                for key, value in metadata_filters.items():
                    if isinstance(value, list):
                        chroma_filters[key] = {"$in": value}
                    else:
                        chroma_filters[key] = value
            
            # 执行搜索
            results = self.vector_manager.similarity_search_with_score(
                query=query,
                k=k,
                filters=chroma_filters
            )
            
            # 增强结果信息
            enhanced_results = []
            for doc, score in results:
                metadata = doc.metadata
                job_id = metadata.get('job_id')
                
                # 获取额外的元数据信息
                doc_metadata = self.get_job_documents_metadata(job_id) if job_id else []
                
                enhanced_result = {
                    'content': doc.page_content,
                    'metadata': metadata,
                    'similarity_score': float(score),
                    'enhanced_metadata': doc_metadata,
                    'timestamp': datetime.now().isoformat()
                }
                
                enhanced_results.append(enhanced_result)
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"带元数据过滤的搜索失败: {e}")
            return []
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """
        获取数据库统计信息
        
        Returns:
            Dict: 统计信息
        """
        try:
            stats = {
                'vector_store_stats': self.vector_manager.get_collection_stats(),
                'metadata_stats': {},
                'operation_stats': self.operation_stats.copy(),
                'performance_metrics': {},
                'timestamp': datetime.now().isoformat()
            }
            
            # 获取元数据统计
            with sqlite3.connect(self.metadata_db_path) as conn:
                cursor = conn.cursor()
                
                # 文档统计
                cursor.execute('SELECT COUNT(*) FROM vector_documents WHERE is_active = TRUE')
                stats['metadata_stats']['active_documents'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM vector_documents WHERE is_active = FALSE')
                stats['metadata_stats']['inactive_documents'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(DISTINCT job_id) FROM vector_documents WHERE is_active = TRUE')
                stats['metadata_stats']['unique_jobs'] = cursor.fetchone()[0]
                
                # 文档类型分布
                cursor.execute('''
                    SELECT doc_type, COUNT(*) 
                    FROM vector_documents 
                    WHERE is_active = TRUE 
                    GROUP BY doc_type
                ''')
                stats['metadata_stats']['document_type_distribution'] = dict(cursor.fetchall())
                
                # 操作统计
                cursor.execute('''
                    SELECT operation_type, COUNT(*), AVG(execution_time)
                    FROM operation_logs 
                    WHERE timestamp > datetime('now', '-7 days')
                    GROUP BY operation_type
                ''')
                recent_operations = {}
                for op_type, count, avg_time in cursor.fetchall():
                    recent_operations[op_type] = {
                        'count': count,
                        'avg_execution_time': round(avg_time, 3) if avg_time else 0
                    }
                stats['operation_stats']['recent_operations'] = recent_operations
            
            return stats
            
        except Exception as e:
            logger.error(f"获取数据库统计信息失败: {e}")
            return {'error': str(e)}
    
    def optimize_database(self) -> Dict[str, Any]:
        """
        优化数据库性能
        
        Returns:
            Dict: 优化结果
        """
        optimization_start = datetime.now()
        
        try:
            optimization_results = {
                'actions_performed': [],
                'performance_improvements': {},
                'recommendations': []
            }
            
            # 1. 清理无效文档
            cleanup_result = self._cleanup_inactive_documents()
            optimization_results['actions_performed'].append('cleanup_inactive_documents')
            optimization_results['performance_improvements']['cleaned_documents'] = cleanup_result
            
            # 2. 重建索引
            index_result = self._rebuild_metadata_indexes()
            optimization_results['actions_performed'].append('rebuild_indexes')
            optimization_results['performance_improvements']['index_rebuild'] = index_result
            
            # 3. 分析查询性能
            query_analysis = self._analyze_query_performance()
            optimization_results['performance_improvements']['query_analysis'] = query_analysis
            
            # 4. 生成优化建议
            recommendations = self._generate_optimization_recommendations()
            optimization_results['recommendations'] = recommendations
            
            execution_time = (datetime.now() - optimization_start).total_seconds()
            
            self._log_operation(
                operation_type='optimize_database',
                operation_details='Database optimization completed',
                success=True,
                execution_time=execution_time
            )
            
            optimization_results['execution_time'] = execution_time
            optimization_results['success'] = True
            
            return optimization_results
            
        except Exception as e:
            execution_time = (datetime.now() - optimization_start).total_seconds()
            
            self._log_operation(
                operation_type='optimize_database',
                operation_details='Database optimization failed',
                success=False,
                error_message=str(e),
                execution_time=execution_time
            )
            
            logger.error(f"数据库优化失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'execution_time': execution_time
            }
    
    def _cleanup_inactive_documents(self) -> int:
        """清理无效文档"""
        
        with sqlite3.connect(self.metadata_db_path) as conn:
            cursor = conn.cursor()
            
            # 删除超过30天的无效文档记录
            cursor.execute('''
                DELETE FROM vector_documents 
                WHERE is_active = FALSE 
                AND updated_at < datetime('now', '-30 days')
            ''')
            
            cleaned_count = cursor.rowcount
            conn.commit()
            
            return cleaned_count
    
    def _rebuild_metadata_indexes(self) -> bool:
        """重建元数据索引"""
        
        try:
            with sqlite3.connect(self.metadata_db_path) as conn:
                cursor = conn.cursor()
                
                # 创建索引
                indexes = [
                    'CREATE INDEX IF NOT EXISTS idx_job_id ON vector_documents(job_id)',
                    'CREATE INDEX IF NOT EXISTS idx_doc_type ON vector_documents(doc_type)',
                    'CREATE INDEX IF NOT EXISTS idx_created_at ON vector_documents(created_at)',
                    'CREATE INDEX IF NOT EXISTS idx_is_active ON vector_documents(is_active)',
                    'CREATE INDEX IF NOT EXISTS idx_operation_type ON operation_logs(operation_type)',
                    'CREATE INDEX IF NOT EXISTS idx_timestamp ON operation_logs(timestamp)'
                ]
                
                for index_sql in indexes:
                    cursor.execute(index_sql)
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"重建索引失败: {e}")
            return False
    
    def _analyze_query_performance(self) -> Dict[str, Any]:
        """分析查询性能"""
        
        try:
            with sqlite3.connect(self.metadata_db_path) as conn:
                cursor = conn.cursor()
                
                # 分析最近的操作性能
                cursor.execute('''
                    SELECT operation_type, 
                           COUNT(*) as count,
                           AVG(execution_time) as avg_time,
                           MIN(execution_time) as min_time,
                           MAX(execution_time) as max_time
                    FROM operation_logs 
                    WHERE timestamp > datetime('now', '-7 days')
                    AND success = TRUE
                    GROUP BY operation_type
                ''')
                
                performance_data = {}
                for row in cursor.fetchall():
                    op_type, count, avg_time, min_time, max_time = row
                    performance_data[op_type] = {
                        'count': count,
                        'avg_execution_time': round(avg_time, 3),
                        'min_execution_time': round(min_time, 3),
                        'max_execution_time': round(max_time, 3)
                    }
                
                return performance_data
                
        except Exception as e:
            logger.error(f"查询性能分析失败: {e}")
            return {}
    
    def _generate_optimization_recommendations(self) -> List[str]:
        """生成优化建议"""
        
        recommendations = []
        
        try:
            stats = self.get_database_statistics()
            
            # 基于统计信息生成建议
            metadata_stats = stats.get('metadata_stats', {})
            
            # 检查文档数量
            active_docs = metadata_stats.get('active_documents', 0)
            if active_docs > 10000:
                recommendations.append("考虑对大量文档进行分片存储以提高查询性能")
            
            # 检查无效文档比例
            inactive_docs = metadata_stats.get('inactive_documents', 0)
            if inactive_docs > active_docs * 0.2:
                recommendations.append("定期清理无效文档以节省存储空间")
            
            # 检查操作性能
            operation_stats = stats.get('operation_stats', {})
            recent_ops = operation_stats.get('recent_operations', {})
            
            for op_type, op_data in recent_ops.items():
                avg_time = op_data.get('avg_execution_time', 0)
                if avg_time > 5.0:  # 超过5秒
                    recommendations.append(f"优化{op_type}操作的性能，当前平均耗时{avg_time:.2f}秒")
            
            if not recommendations:
                recommendations.append("数据库性能良好，无需特殊优化")
            
        except Exception as e:
            logger.error(f"生成优化建议失败: {e}")
            recommendations.append("无法生成优化建议，请检查系统状态")
        
        return recommendations
    
    def _log_operation(self, operation_type: str, operation_details: str = None,
                      success: bool = True, error_message: str = None,
                      execution_time: float = None):
        """记录操作日志"""
        
        try:
            with sqlite3.connect(self.metadata_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO operation_logs 
                    (operation_type, operation_details, success, error_message, execution_time)
                    VALUES (?, ?, ?, ?, ?)
                ''', (operation_type, operation_details, success, error_message, execution_time))
                conn.commit()
                
        except Exception as e:
            logger.error(f"记录操作日志失败: {e}")
    
    def export_metadata(self, output_path: str) -> bool:
        """
        导出元数据
        
        Args:
            output_path: 输出路径
            
        Returns:
            bool: 导出是否成功
        """
        try:
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'database_stats': self.get_database_statistics(),
                'documents_metadata': [],
                'operation_logs': []
            }
            
            # 导出文档元数据
            with sqlite3.connect(self.metadata_db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM vector_documents WHERE is_active = TRUE
                ''')
                
                columns = [description[0] for description in cursor.description]
                for row in cursor.fetchall():
                    doc_data = dict(zip(columns, row))
                    # 解析JSON字段
                    if doc_data.get('metadata_json'):
                        try:
                            doc_data['metadata'] = json.loads(doc_data['metadata_json'])
                            del doc_data['metadata_json']
                        except:
                            pass
                    export_data['documents_metadata'].append(doc_data)
                
                # 导出最近的操作日志
                cursor.execute('''
                    SELECT * FROM operation_logs 
                    WHERE timestamp > datetime('now', '-30 days')
                    ORDER BY timestamp DESC
                    LIMIT 1000
                ''')
                
                columns = [description[0] for description in cursor.description]
                for row in cursor.fetchall():
                    log_data = dict(zip(columns, row))
                    export_data['operation_logs'].append(log_data)
            
            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"元数据已导出到: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出元数据失败: {e}")
            return False
    
    def cleanup_resources(self):
        """清理资源"""
        try:
            # 关闭向量数据库连接
            self.vector_manager.close()
            
            logger.info("向量数据库操作资源清理完成")
            
        except Exception as e:
            logger.error(f"资源清理失败: {e}")