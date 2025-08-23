"""
数据传递接口 (DataBridge)
标准化模块间数据格式，实现数据验证和转换
"""

import hashlib
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from cachetools import TTLCache

logger = logging.getLogger(__name__)

@dataclass
class PipelineData:
    """流水线数据容器"""
    pipeline_id: str
    resume_profile: Dict[str, Any]
    config: Dict[str, Any]
    start_time: float
    extraction_result: Optional[Dict] = None
    rag_result: Optional[Dict] = None
    matching_result: Optional[Dict] = None
    decision_result: Optional[Dict] = None
    submission_result: Optional[Dict] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class JobData:
    """标准化职位数据结构"""
    job_id: str
    title: str
    company: str
    location: str
    description: str
    requirements: str
    salary: str
    url: str
    source: str
    extracted_at: str
    additional_info: Dict[str, Any] = field(default_factory=dict)

class DataValidationError(Exception):
    """数据验证错误"""
    pass

class DataTransformationError(Exception):
    """数据转换错误"""
    pass

class DataBridge:
    """数据传递桥接器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.bridge_config = config.get('data_bridge', {})
        self.validation_enabled = self.bridge_config.get('validation_enabled', True)
        self.transformation_cache_enabled = self.bridge_config.get('transformation_cache', True)
        self.data_retention_days = self.bridge_config.get('data_retention_days', 30)
        
        # 初始化缓存
        if self.transformation_cache_enabled:
            cache_ttl = self.bridge_config.get('cache_ttl', 3600)  # 1小时
            self.transformation_cache = TTLCache(maxsize=1000, ttl=cache_ttl)
        else:
            self.transformation_cache = {}
        
        # 数据统计
        self.transformation_stats = {
            'total_transformations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'validation_errors': 0,
            'transformation_errors': 0
        }
    
    def transform_extraction_to_rag(self, extraction_result: Dict) -> Dict:
        """转换职位提取结果为RAG输入格式"""
        if self.validation_enabled and not self._validate_extraction_result(extraction_result):
            raise DataValidationError("Invalid extraction result format")
        
        # 检查缓存
        cache_key = self._generate_cache_key('extraction_to_rag', extraction_result)
        if self.transformation_cache_enabled and cache_key in self.transformation_cache:
            self.transformation_stats['cache_hits'] += 1
            return self.transformation_cache[cache_key]
        
        self.transformation_stats['cache_misses'] += 1
        
        try:
            jobs = extraction_result.get('jobs', [])
            transformed_jobs = []
            
            for job in jobs:
                transformed_job = self._standardize_job_data(job)
                transformed_jobs.append(transformed_job)
            
            result = {
                'jobs': transformed_jobs,
                'total_count': len(transformed_jobs),
                'transformation_time': datetime.now().isoformat(),
                'source_stats': {
                    'original_count': len(jobs),
                    'transformed_count': len(transformed_jobs),
                    'success_rate': len(transformed_jobs) / len(jobs) if jobs else 0
                }
            }
            
            # 缓存结果
            if self.transformation_cache_enabled:
                self.transformation_cache[cache_key] = result
            
            self.transformation_stats['total_transformations'] += 1
            return result
            
        except Exception as e:
            self.transformation_stats['transformation_errors'] += 1
            logger.error(f"数据转换失败: {e}")
            raise DataTransformationError(f"Failed to transform extraction to RAG: {e}")
    
    def transform_rag_to_matching(self, rag_result: Dict) -> Dict:
        """转换RAG结果为匹配输入格式"""
        if self.validation_enabled and not self._validate_rag_result(rag_result):
            raise DataValidationError("Invalid RAG result format")
        
        # 检查缓存
        cache_key = self._generate_cache_key('rag_to_matching', rag_result)
        if self.transformation_cache_enabled and cache_key in self.transformation_cache:
            self.transformation_stats['cache_hits'] += 1
            return self.transformation_cache[cache_key]
        
        self.transformation_stats['cache_misses'] += 1
        
        try:
            result = {
                'processed_jobs_count': rag_result.get('processed_count', 0),
                'vector_db_ready': rag_result.get('success', False),
                'processing_quality': rag_result.get('success_rate', 0),
                'ready_for_matching': True,
                'vector_db_stats': rag_result.get('vector_db_stats', {}),
                'transformation_time': datetime.now().isoformat()
            }
            
            # 缓存结果
            if self.transformation_cache_enabled:
                self.transformation_cache[cache_key] = result
            
            self.transformation_stats['total_transformations'] += 1
            return result
            
        except Exception as e:
            self.transformation_stats['transformation_errors'] += 1
            logger.error(f"RAG到匹配数据转换失败: {e}")
            raise DataTransformationError(f"Failed to transform RAG to matching: {e}")
    
    def transform_matching_to_decision(self, matching_result: Dict) -> Dict:
        """转换匹配结果为决策输入格式"""
        if self.validation_enabled and not self._validate_matching_result(matching_result):
            raise DataValidationError("Invalid matching result format")
        
        try:
            matches = matching_result.get('matches', [])
            decision_candidates = []
            
            for match in matches:
                candidate = {
                    'job_id': match.get('job_id'),
                    'job_title': match.get('job_title'),
                    'company': match.get('company'),
                    'location': match.get('location'),
                    'overall_score': match.get('overall_score', 0),
                    'match_level': match.get('match_level', 'unknown'),
                    'recommendation_priority': match.get('recommendation_priority', 'low'),
                    'job_url': match.get('job_url', ''),
                    'salary_range': match.get('salary_range', {}),
                    'detailed_scores': match.get('detailed_scores', {}),
                    'match_reasons': match.get('match_reasons', [])
                }
                decision_candidates.append(candidate)
            
            result = {
                'total_candidates': len(decision_candidates),
                'candidates': decision_candidates,
                'matching_summary': {
                    'total_matches': matching_result.get('total_matches', 0),
                    'high_priority': matching_result.get('high_priority', 0),
                    'medium_priority': matching_result.get('medium_priority', 0),
                    'low_priority': matching_result.get('low_priority', 0)
                },
                'transformation_time': datetime.now().isoformat()
            }
            
            self.transformation_stats['total_transformations'] += 1
            return result
            
        except Exception as e:
            self.transformation_stats['transformation_errors'] += 1
            logger.error(f"匹配到决策数据转换失败: {e}")
            raise DataTransformationError(f"Failed to transform matching to decision: {e}")
    
    def transform_decision_to_submission(self, decision_result: Dict) -> Dict:
        """转换决策结果为投递输入格式"""
        if self.validation_enabled and not self._validate_decision_result(decision_result):
            raise DataValidationError("Invalid decision result format")
        
        try:
            decisions = decision_result.get('decisions', [])
            submission_tasks = []
            
            for decision in decisions:
                if decision.get('should_submit', False):
                    task = {
                        'job_id': decision.get('job_id'),
                        'job_title': decision.get('job_title'),
                        'company': decision.get('company'),
                        'job_url': decision.get('job_url'),
                        'submission_priority': decision.get('submission_priority', 'medium'),
                        'final_score': decision.get('final_score', 0),
                        'decision_reasoning': decision.get('decision_reasoning', ''),
                        'estimated_success_rate': decision.get('estimated_success_rate', 0.5)
                    }
                    submission_tasks.append(task)
            
            # 按优先级排序
            priority_order = {'high': 3, 'medium': 2, 'low': 1}
            submission_tasks.sort(
                key=lambda x: (priority_order.get(x['submission_priority'], 0), x['final_score']),
                reverse=True
            )
            
            result = {
                'total_submission_tasks': len(submission_tasks),
                'submission_tasks': submission_tasks,
                'priority_distribution': self._calculate_priority_distribution(submission_tasks),
                'transformation_time': datetime.now().isoformat()
            }
            
            self.transformation_stats['total_transformations'] += 1
            return result
            
        except Exception as e:
            self.transformation_stats['transformation_errors'] += 1
            logger.error(f"决策到投递数据转换失败: {e}")
            raise DataTransformationError(f"Failed to transform decision to submission: {e}")
    
    def _standardize_job_data(self, job: Dict) -> Dict:
        """标准化职位数据"""
        return {
            'job_id': job.get('id') or self._generate_job_id(job),
            'title': job.get('title', '').strip(),
            'company': job.get('company', '').strip(),
            'location': job.get('location', '').strip(),
            'description': job.get('description', '').strip(),
            'requirements': job.get('requirements', '').strip(),
            'salary': job.get('salary', '').strip(),
            'url': job.get('url', '').strip(),
            'source': job.get('source', 'extraction'),
            'extracted_at': job.get('extracted_at') or datetime.now().isoformat(),
            'additional_info': job.get('additional_info', {})
        }
    
    def _generate_job_id(self, job: Dict) -> str:
        """生成职位ID"""
        content = f"{job.get('title', '')}{job.get('company', '')}{job.get('url', '')}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _generate_cache_key(self, operation: str, data: Dict) -> str:
        """生成缓存键"""
        data_str = str(sorted(data.items()))
        content = f"{operation}_{data_str}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _validate_extraction_result(self, result: Dict) -> bool:
        """验证提取结果格式"""
        try:
            if not isinstance(result, dict):
                return False
            
            if 'success' not in result:
                return False
            
            if result.get('success') and 'jobs' not in result:
                return False
            
            jobs = result.get('jobs', [])
            if not isinstance(jobs, list):
                return False
            
            # 验证职位数据格式
            for job in jobs[:5]:  # 只验证前5个
                if not self._validate_job_data(job):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"提取结果验证失败: {e}")
            self.transformation_stats['validation_errors'] += 1
            return False
    
    def _validate_rag_result(self, result: Dict) -> bool:
        """验证RAG结果格式"""
        try:
            if not isinstance(result, dict):
                return False
            
            required_fields = ['success', 'processed_count']
            for field in required_fields:
                if field not in result:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"RAG结果验证失败: {e}")
            self.transformation_stats['validation_errors'] += 1
            return False
    
    def _validate_matching_result(self, result: Dict) -> bool:
        """验证匹配结果格式"""
        try:
            if not isinstance(result, dict):
                return False
            
            if 'success' not in result or not result.get('success'):
                return False
            
            if 'matches' not in result:
                return False
            
            matches = result.get('matches', [])
            if not isinstance(matches, list):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"匹配结果验证失败: {e}")
            self.transformation_stats['validation_errors'] += 1
            return False
    
    def _validate_decision_result(self, result: Dict) -> bool:
        """验证决策结果格式"""
        try:
            if not isinstance(result, dict):
                return False
            
            if 'decisions' not in result:
                return False
            
            decisions = result.get('decisions', [])
            if not isinstance(decisions, list):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"决策结果验证失败: {e}")
            self.transformation_stats['validation_errors'] += 1
            return False
    
    def _validate_job_data(self, job: Dict) -> bool:
        """验证单个职位数据"""
        required_fields = ['title', 'company']
        for field in required_fields:
            if field not in job or not job[field]:
                return False
        return True
    
    def _calculate_priority_distribution(self, tasks: List[Dict]) -> Dict[str, int]:
        """计算优先级分布"""
        distribution = {'high': 0, 'medium': 0, 'low': 0}
        for task in tasks:
            priority = task.get('submission_priority', 'medium')
            if priority in distribution:
                distribution[priority] += 1
        return distribution
    
    def get_transformation_stats(self) -> Dict[str, Any]:
        """获取转换统计信息"""
        return {
            'stats': self.transformation_stats.copy(),
            'cache_hit_rate': (
                self.transformation_stats['cache_hits'] / 
                max(self.transformation_stats['cache_hits'] + self.transformation_stats['cache_misses'], 1)
            ),
            'error_rate': (
                (self.transformation_stats['validation_errors'] + self.transformation_stats['transformation_errors']) /
                max(self.transformation_stats['total_transformations'], 1)
            ),
            'cache_size': len(self.transformation_cache) if self.transformation_cache_enabled else 0
        }
    
    def clear_cache(self):
        """清空缓存"""
        if self.transformation_cache_enabled:
            self.transformation_cache.clear()
            logger.info("数据转换缓存已清空")
    
    def validate_pipeline_data(self, pipeline_data: PipelineData) -> bool:
        """验证完整的流水线数据"""
        try:
            # 验证基本字段
            if not pipeline_data.pipeline_id:
                return False
            
            if not pipeline_data.resume_profile:
                return False
            
            # 验证各阶段结果
            if pipeline_data.extraction_result and not self._validate_extraction_result(pipeline_data.extraction_result):
                return False
            
            if pipeline_data.rag_result and not self._validate_rag_result(pipeline_data.rag_result):
                return False
            
            if pipeline_data.matching_result and not self._validate_matching_result(pipeline_data.matching_result):
                return False
            
            if pipeline_data.decision_result and not self._validate_decision_result(pipeline_data.decision_result):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"流水线数据验证失败: {e}")
            return False