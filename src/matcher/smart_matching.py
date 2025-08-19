"""
智能匹配引擎

基于RAG技术进行简历与职位的智能匹配，提供多维度评分和详细分析。
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
import asyncio
from datetime import datetime
import json
import numpy as np

from ..rag.vector_manager import ChromaDBManager
from ..rag.semantic_search import SemanticSearchEngine
from .semantic_scorer import SemanticScorer

logger = logging.getLogger(__name__)


class SmartMatchingEngine:
    """智能匹配引擎"""
    
    def __init__(self, vector_manager: ChromaDBManager, config: Dict = None):
        """
        初始化智能匹配引擎
        
        Args:
            vector_manager: 向量存储管理器
            config: 配置字典
        """
        self.vector_manager = vector_manager
        self.config = config or {}
        
        # 初始化组件
        self.search_engine = SemanticSearchEngine(vector_manager, config.get('search', {}))
        self.semantic_scorer = SemanticScorer(config.get('scorer', {}))
        
        # 匹配权重配置
        self.weights = self.config.get('weights', {
            'semantic_similarity': 0.4,
            'skills_match': 0.3,
            'experience_match': 0.2,
            'salary_match': 0.1
        })
        
        # 匹配阈值
        self.thresholds = self.config.get('thresholds', {
            'excellent': 0.85,
            'good': 0.7,
            'fair': 0.5,
            'poor': 0.3
        })
        
        logger.info("智能匹配引擎初始化完成")
    
    async def match_resume_to_jobs(self, resume_data: Dict[str, Any], 
                                 filters: Dict = None, k: int = 20) -> List[Dict[str, Any]]:
        """
        简历与职位匹配
        
        Args:
            resume_data: 简历数据
            filters: 过滤条件
            k: 返回匹配职位数量
            
        Returns:
            List[Dict]: 匹配结果列表
        """
        try:
            # 1. 构建用户画像查询
            user_profile = self._build_user_profile(resume_data)
            
            # 2. 语义搜索相关职位
            search_results = self.search_engine.search(
                query=user_profile,
                strategy='hybrid',
                k=k * 2,  # 获取更多候选职位
                filters=filters
            )
            
            # 3. 按职位分组
            jobs_by_id = self._group_results_by_job(search_results)
            
            # 4. 计算匹配分数
            matching_jobs = []
            for job_id, job_docs in jobs_by_id.items():
                match_result = await self._calculate_job_match(resume_data, job_docs)
                if match_result:
                    matching_jobs.append(match_result)
            
            # 5. 排序和筛选
            matching_jobs.sort(key=lambda x: x['overall_score'], reverse=True)
            
            logger.info(f"简历匹配完成，找到 {len(matching_jobs)} 个匹配职位")
            return matching_jobs[:k]
            
        except Exception as e:
            logger.error(f"简历匹配失败: {e}")
            return []
    
    def _build_user_profile(self, resume_data: Dict[str, Any]) -> str:
        """构建用户画像查询文本"""
        
        profile_parts = []
        
        # 技能
        if 'skills' in resume_data:
            skills = resume_data['skills']
            if isinstance(skills, list):
                profile_parts.append(f"技能: {', '.join(skills)}")
            else:
                profile_parts.append(f"技能: {skills}")
        
        # 工作经验
        if 'experience_years' in resume_data:
            profile_parts.append(f"工作经验: {resume_data['experience_years']}年")
        
        # 期望职位
        if 'desired_position' in resume_data:
            profile_parts.append(f"期望职位: {resume_data['desired_position']}")
        
        # 教育背景
        if 'education' in resume_data:
            profile_parts.append(f"学历: {resume_data['education']}")
        
        # 工作经历描述
        if 'work_experience' in resume_data:
            work_exp = resume_data['work_experience']
            if isinstance(work_exp, list):
                profile_parts.extend(work_exp[:3])  # 最多3个工作经历
            else:
                profile_parts.append(str(work_exp))
        
        return '; '.join(profile_parts)
    
    def _group_results_by_job(self, search_results: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """按职位ID分组搜索结果"""
        
        jobs_by_id = {}
        
        for result in search_results:
            metadata = result.get('metadata', {})
            job_id = metadata.get('job_id')
            
            if not job_id:
                continue
            
            if job_id not in jobs_by_id:
                jobs_by_id[job_id] = []
            
            jobs_by_id[job_id].append(result)
        
        return jobs_by_id
    
    async def _calculate_job_match(self, resume_data: Dict[str, Any], 
                                 job_docs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """计算单个职位的匹配度"""
        
        try:
            if not job_docs:
                return None
            
            # 获取职位基本信息
            job_info = self._extract_job_info(job_docs)
            
            # 1. 语义相似度匹配
            semantic_score = self._calculate_semantic_match(resume_data, job_docs)
            
            # 2. 技能匹配度
            skills_score = self._calculate_skills_match(resume_data, job_info)
            
            # 3. 经验匹配度
            experience_score = self._calculate_experience_match(resume_data, job_info)
            
            # 4. 薪资匹配度
            salary_score = self._calculate_salary_match(resume_data, job_info)
            
            # 5. 计算综合分数
            overall_score = (
                semantic_score * self.weights['semantic_similarity'] +
                skills_score * self.weights['skills_match'] +
                experience_score * self.weights['experience_match'] +
                salary_score * self.weights['salary_match']
            )
            
            # 6. 生成匹配分析
            match_analysis = self._generate_match_analysis(
                resume_data, job_info, {
                    'semantic': semantic_score,
                    'skills': skills_score,
                    'experience': experience_score,
                    'salary': salary_score,
                    'overall': overall_score
                }
            )
            
            return {
                'job_id': job_info['job_id'],
                'job_title': job_info['job_title'],
                'company': job_info['company'],
                'location': job_info.get('location'),
                'salary_range': job_info.get('salary_range'),
                'overall_score': round(overall_score, 3),
                'dimension_scores': {
                    'semantic_similarity': round(semantic_score, 3),
                    'skills_match': round(skills_score, 3),
                    'experience_match': round(experience_score, 3),
                    'salary_match': round(salary_score, 3)
                },
                'match_level': self._get_match_level(overall_score),
                'match_analysis': match_analysis,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"计算职位匹配度失败: {e}")
            return None
    
    def _extract_job_info(self, job_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """从职位文档中提取基本信息"""
        
        job_info = {
            'job_id': None,
            'job_title': None,
            'company': None,
            'location': None,
            'salary_range': {},
            'skills': [],
            'responsibilities': [],
            'requirements': [],
            'education': None,
            'experience': None
        }
        
        for doc in job_docs:
            metadata = doc.get('metadata', {})
            
            # 基本信息
            if not job_info['job_id']:
                job_info['job_id'] = metadata.get('job_id')
            if not job_info['job_title']:
                job_info['job_title'] = metadata.get('job_title')
            if not job_info['company']:
                job_info['company'] = metadata.get('company')
            if not job_info['location']:
                job_info['location'] = metadata.get('location')
            
            # 薪资信息
            if metadata.get('salary_min'):
                job_info['salary_range']['min'] = metadata['salary_min']
            if metadata.get('salary_max'):
                job_info['salary_range']['max'] = metadata['salary_max']
            
            # 技能信息
            if metadata.get('skills'):
                job_info['skills'].extend(metadata['skills'])
            
            # 教育和经验要求
            if not job_info['education'] and metadata.get('education'):
                job_info['education'] = metadata['education']
            if not job_info['experience'] and metadata.get('experience'):
                job_info['experience'] = metadata['experience']
            
            # 职责和要求
            doc_type = metadata.get('type')
            content = doc.get('content', '')
            
            if doc_type == 'responsibility':
                job_info['responsibilities'].append(content)
            elif doc_type == 'requirement':
                job_info['requirements'].append(content)
        
        # 去重技能
        job_info['skills'] = list(set(job_info['skills']))
        
        return job_info
    
    def _calculate_semantic_match(self, resume_data: Dict[str, Any], 
                                job_docs: List[Dict[str, Any]]) -> float:
        """计算语义相似度匹配"""
        
        # 使用文档中的相似度分数
        similarity_scores = []
        
        for doc in job_docs:
            score = doc.get('similarity_score', 0.0)
            if score > 0:
                similarity_scores.append(score)
        
        if similarity_scores:
            # 使用最高分数作为语义匹配度
            return max(similarity_scores)
        
        return 0.0
    
    def _calculate_skills_match(self, resume_data: Dict[str, Any], 
                              job_info: Dict[str, Any]) -> float:
        """计算技能匹配度"""
        
        resume_skills = resume_data.get('skills', [])
        job_skills = job_info.get('skills', [])
        
        if not resume_skills or not job_skills:
            return 0.0
        
        # 转换为小写进行比较
        resume_skills_lower = [skill.lower() for skill in resume_skills]
        job_skills_lower = [skill.lower() for skill in job_skills]
        
        # 计算交集
        matched_skills = set(resume_skills_lower).intersection(set(job_skills_lower))
        
        # 计算匹配度
        match_ratio = len(matched_skills) / len(job_skills_lower)
        
        return min(match_ratio, 1.0)
    
    def _calculate_experience_match(self, resume_data: Dict[str, Any], 
                                  job_info: Dict[str, Any]) -> float:
        """计算经验匹配度"""
        
        resume_years = resume_data.get('experience_years', 0)
        job_experience = job_info.get('experience', '')
        
        if not job_experience or job_experience == '不限':
            return 1.0  # 无经验要求，完全匹配
        
        # 从职位经验要求中提取年限
        required_years = self._extract_years_from_text(job_experience)
        
        if required_years is None:
            return 0.8  # 无法解析经验要求，给中等分数
        
        if resume_years >= required_years:
            return 1.0  # 经验满足要求
        elif resume_years >= required_years * 0.8:
            return 0.8  # 经验接近要求
        elif resume_years >= required_years * 0.5:
            return 0.5  # 经验不足但有一定基础
        else:
            return 0.2  # 经验严重不足
    
    def _calculate_salary_match(self, resume_data: Dict[str, Any], 
                              job_info: Dict[str, Any]) -> float:
        """计算薪资匹配度"""
        
        expected_min = resume_data.get('expected_salary_min')
        expected_max = resume_data.get('expected_salary_max')
        
        job_salary = job_info.get('salary_range', {})
        job_min = job_salary.get('min')
        job_max = job_salary.get('max')
        
        # 如果任一方没有薪资信息，返回中等分数
        if not (expected_min or expected_max) or not (job_min or job_max):
            return 0.7
        
        # 计算期望薪资范围
        exp_min = expected_min or 0
        exp_max = expected_max or expected_min or 999999
        
        # 计算职位薪资范围
        job_min = job_min or 0
        job_max = job_max or job_min or 999999
        
        # 计算重叠度
        overlap_min = max(exp_min, job_min)
        overlap_max = min(exp_max, job_max)
        
        if overlap_min <= overlap_max:
            # 有重叠，计算重叠比例
            overlap_range = overlap_max - overlap_min
            exp_range = exp_max - exp_min
            job_range = job_max - job_min
            
            avg_range = (exp_range + job_range) / 2
            if avg_range > 0:
                return min(overlap_range / avg_range, 1.0)
            else:
                return 1.0
        else:
            # 无重叠，计算距离惩罚
            gap = overlap_min - overlap_max
            avg_salary = (exp_min + exp_max + job_min + job_max) / 4
            
            if avg_salary > 0:
                penalty = gap / avg_salary
                return max(0.0, 1.0 - penalty)
            else:
                return 0.0
    
    def _extract_years_from_text(self, text: str) -> Optional[int]:
        """从文本中提取年限数字"""
        
        import re
        
        # 匹配数字+年的模式
        patterns = [
            r'(\d+)\s*年',
            r'(\d+)\s*-\s*\d+\s*年',  # 取最小值
            r'(\d+)\+\s*年'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))
        
        return None
    
    def _get_match_level(self, score: float) -> str:
        """根据分数获取匹配等级"""
        
        if score >= self.thresholds['excellent']:
            return 'excellent'
        elif score >= self.thresholds['good']:
            return 'good'
        elif score >= self.thresholds['fair']:
            return 'fair'
        elif score >= self.thresholds['poor']:
            return 'poor'
        else:
            return 'very_poor'
    
    def _generate_match_analysis(self, resume_data: Dict[str, Any], 
                               job_info: Dict[str, Any], 
                               scores: Dict[str, float]) -> Dict[str, Any]:
        """生成匹配分析"""
        
        analysis = {
            'strengths': [],
            'weaknesses': [],
            'recommendations': [],
            'matched_skills': [],
            'missing_skills': []
        }
        
        # 技能分析
        resume_skills = set(skill.lower() for skill in resume_data.get('skills', []))
        job_skills = set(skill.lower() for skill in job_info.get('skills', []))
        
        matched_skills = resume_skills.intersection(job_skills)
        missing_skills = job_skills - resume_skills
        
        analysis['matched_skills'] = list(matched_skills)
        analysis['missing_skills'] = list(missing_skills)
        
        # 优势分析
        if scores['skills'] >= 0.8:
            analysis['strengths'].append("技能匹配度很高")
        if scores['experience'] >= 0.8:
            analysis['strengths'].append("工作经验符合要求")
        if scores['semantic'] >= 0.8:
            analysis['strengths'].append("整体背景与职位高度匹配")
        
        # 劣势分析
        if scores['skills'] < 0.5:
            analysis['weaknesses'].append("技能匹配度较低")
        if scores['experience'] < 0.5:
            analysis['weaknesses'].append("工作经验不足")
        if scores['salary'] < 0.5:
            analysis['weaknesses'].append("薪资期望与职位不匹配")
        
        # 建议
        if missing_skills:
            analysis['recommendations'].append(
                f"建议学习以下技能: {', '.join(list(missing_skills)[:3])}"
            )
        
        if scores['experience'] < 0.7:
            analysis['recommendations'].append("建议积累更多相关工作经验")
        
        return analysis
    
    async def batch_match_resumes(self, resumes_data: List[Dict[str, Any]], 
                                filters: Dict = None, k: int = 10) -> List[Dict[str, Any]]:
        """批量简历匹配"""
        
        results = []
        
        for i, resume_data in enumerate(resumes_data):
            try:
                matches = await self.match_resume_to_jobs(
                    resume_data=resume_data,
                    filters=filters,
                    k=k
                )
                
                results.append({
                    'resume_index': i,
                    'resume_id': resume_data.get('resume_id', f'resume_{i}'),
                    'matches': matches,
                    'match_count': len(matches),
                    'success': True
                })
                
            except Exception as e:
                logger.error(f"简历 {i} 匹配失败: {e}")
                results.append({
                    'resume_index': i,
                    'resume_id': resume_data.get('resume_id', f'resume_{i}'),
                    'matches': [],
                    'match_count': 0,
                    'success': False,
                    'error': str(e)
                })
        
        logger.info(f"批量匹配完成，处理了 {len(resumes_data)} 份简历")
        return results
    
    def get_matching_statistics(self, match_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取匹配统计信息"""
        
        if not match_results:
            return {}
        
        stats = {
            'total_matches': len(match_results),
            'score_distribution': {
                'excellent': 0,
                'good': 0,
                'fair': 0,
                'poor': 0,
                'very_poor': 0
            },
            'average_scores': {
                'overall': 0.0,
                'semantic': 0.0,
                'skills': 0.0,
                'experience': 0.0,
                'salary': 0.0
            },
            'top_companies': {},
            'top_skills': {}
        }
        
        total_scores = {
            'overall': 0.0,
            'semantic': 0.0,
            'skills': 0.0,
            'experience': 0.0,
            'salary': 0.0
        }
        
        for match in match_results:
            # 统计匹配等级
            match_level = match.get('match_level', 'very_poor')
            stats['score_distribution'][match_level] += 1
            
            # 累计分数
            total_scores['overall'] += match.get('overall_score', 0.0)
            
            dimension_scores = match.get('dimension_scores', {})
            for dim in ['semantic', 'skills', 'experience', 'salary']:
                key = f'{dim}_similarity' if dim == 'semantic' else f'{dim}_match'
                total_scores[dim] += dimension_scores.get(key, 0.0)
            
            # 统计公司
            company = match.get('company')
            if company:
                stats['top_companies'][company] = stats['top_companies'].get(company, 0) + 1
        
        # 计算平均分数
        count = len(match_results)
        for key in total_scores:
            stats['average_scores'][key] = round(total_scores[key] / count, 3)
        
        # 排序公司
        stats['top_companies'] = dict(
            sorted(stats['top_companies'].items(), key=lambda x: x[1], reverse=True)[:10]
        )
        
        return stats