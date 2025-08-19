"""
职位推荐引擎

基于用户画像和RAG检索结果，提供个性化的职位推荐。
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime
import json
import numpy as np
from collections import defaultdict, Counter

from ..rag.vector_manager import ChromaDBManager
from ..rag.semantic_search import SemanticSearchEngine
from .semantic_scorer import SemanticScorer

logger = logging.getLogger(__name__)


class JobRecommendationEngine:
    """职位推荐引擎"""
    
    def __init__(self, vector_manager: ChromaDBManager, config: Dict = None):
        """
        初始化职位推荐引擎
        
        Args:
            vector_manager: 向量存储管理器
            config: 配置字典
        """
        self.vector_manager = vector_manager
        self.config = config or {}
        
        # 初始化组件
        self.search_engine = SemanticSearchEngine(vector_manager, config.get('search', {}))
        self.semantic_scorer = SemanticScorer(config.get('scorer', {}))
        
        # 推荐策略配置
        self.recommendation_strategies = {
            'content_based': self._content_based_recommendation,
            'collaborative': self._collaborative_recommendation,
            'hybrid': self._hybrid_recommendation,
            'trending': self._trending_recommendation
        }
        
        # 推荐权重
        self.recommendation_weights = self.config.get('recommendation_weights', {
            'skill_match': 0.3,
            'experience_match': 0.2,
            'salary_match': 0.15,
            'location_match': 0.1,
            'company_preference': 0.1,
            'growth_potential': 0.15
        })
        
        # 多样性控制
        self.diversity_config = self.config.get('diversity', {
            'max_same_company': 3,
            'max_same_location': 5,
            'skill_diversity_weight': 0.2
        })
        
        logger.info("职位推荐引擎初始化完成")
    
    def recommend_jobs(self, user_profile: Dict[str, Any], 
                      strategy: str = 'hybrid', k: int = 20,
                      filters: Dict = None) -> List[Dict[str, Any]]:
        """
        推荐职位
        
        Args:
            user_profile: 用户画像
            strategy: 推荐策略
            k: 推荐数量
            filters: 过滤条件
            
        Returns:
            List[Dict]: 推荐职位列表
        """
        try:
            if strategy not in self.recommendation_strategies:
                logger.warning(f"未知推荐策略: {strategy}，使用默认策略")
                strategy = 'hybrid'
            
            # 执行推荐
            recommendation_func = self.recommendation_strategies[strategy]
            recommendations = recommendation_func(user_profile, k * 2, filters)  # 获取更多候选
            
            # 应用多样性控制
            diverse_recommendations = self._apply_diversity_control(recommendations, k)
            
            # 添加推荐解释
            final_recommendations = self._add_recommendation_explanations(
                diverse_recommendations, user_profile
            )
            
            logger.info(f"生成 {len(final_recommendations)} 个职位推荐")
            return final_recommendations
            
        except Exception as e:
            logger.error(f"职位推荐失败: {e}")
            return []
    
    def _content_based_recommendation(self, user_profile: Dict[str, Any], 
                                    k: int, filters: Dict = None) -> List[Dict[str, Any]]:
        """基于内容的推荐"""
        
        # 构建查询文本
        query_parts = []
        
        # 技能查询
        if 'skills' in user_profile:
            skills = user_profile['skills']
            if isinstance(skills, list):
                query_parts.append(' '.join(skills[:5]))  # 最多5个技能
            else:
                query_parts.append(str(skills))
        
        # 期望职位查询
        if 'desired_position' in user_profile:
            query_parts.append(user_profile['desired_position'])
        
        # 工作经验查询
        if 'experience_years' in user_profile:
            years = user_profile['experience_years']
            query_parts.append(f"{years}年经验")
        
        query = ' '.join(query_parts)
        
        # 执行搜索
        search_results = self.search_engine.search(
            query=query,
            strategy='hybrid',
            k=k,
            filters=filters
        )
        
        # 按职位分组并计算推荐分数
        recommendations = self._group_and_score_results(search_results, user_profile)
        
        return recommendations
    
    def _collaborative_recommendation(self, user_profile: Dict[str, Any], 
                                    k: int, filters: Dict = None) -> List[Dict[str, Any]]:
        """协同过滤推荐（简化版）"""
        
        # 由于缺乏用户行为数据，这里实现一个简化的协同过滤
        # 基于相似技能背景的用户喜欢的职位类型
        
        user_skills = set(skill.lower() for skill in user_profile.get('skills', []))
        
        # 搜索包含相似技能的职位
        recommendations = []
        
        for skill in list(user_skills)[:3]:  # 最多使用3个技能
            skill_results = self.search_engine.search(
                query=skill,
                strategy='similarity',
                k=k // 3,
                filters=filters
            )
            recommendations.extend(skill_results)
        
        # 去重并评分
        unique_recommendations = self._deduplicate_results(recommendations)
        scored_recommendations = self._group_and_score_results(unique_recommendations, user_profile)
        
        return scored_recommendations
    
    def _hybrid_recommendation(self, user_profile: Dict[str, Any], 
                             k: int, filters: Dict = None) -> List[Dict[str, Any]]:
        """混合推荐策略"""
        
        # 获取不同策略的推荐结果
        content_recs = self._content_based_recommendation(user_profile, k // 2, filters)
        collaborative_recs = self._collaborative_recommendation(user_profile, k // 2, filters)
        
        # 合并结果
        all_recommendations = content_recs + collaborative_recs
        
        # 去重
        unique_recommendations = self._deduplicate_results(all_recommendations)
        
        # 重新评分
        final_recommendations = self._rescore_hybrid_results(unique_recommendations, user_profile)
        
        return final_recommendations[:k]
    
    def _trending_recommendation(self, user_profile: Dict[str, Any], 
                               k: int, filters: Dict = None) -> List[Dict[str, Any]]:
        """热门趋势推荐"""
        
        # 基于最近添加的职位和热门技能进行推荐
        
        # 获取最近的职位
        recent_filters = filters.copy() if filters else {}
        # 这里可以添加时间过滤条件
        
        # 搜索热门技能相关职位
        trending_skills = ['python', 'ai', 'machine learning', 'react', 'cloud']
        
        recommendations = []
        for skill in trending_skills:
            skill_results = self.search_engine.search(
                query=skill,
                strategy='similarity',
                k=k // len(trending_skills),
                filters=recent_filters
            )
            recommendations.extend(skill_results)
        
        # 评分和排序
        scored_recommendations = self._group_and_score_results(recommendations, user_profile)
        
        return scored_recommendations
    
    def _group_and_score_results(self, search_results: List[Dict[str, Any]], 
                               user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """按职位分组并计算推荐分数"""
        
        # 按职位ID分组
        jobs_by_id = defaultdict(list)
        
        for result in search_results:
            metadata = result.get('metadata', {})
            job_id = metadata.get('job_id')
            
            if job_id:
                jobs_by_id[job_id].append(result)
        
        # 计算每个职位的推荐分数
        recommendations = []
        
        for job_id, job_docs in jobs_by_id.items():
            recommendation = self._calculate_recommendation_score(job_docs, user_profile)
            if recommendation:
                recommendations.append(recommendation)
        
        # 按推荐分数排序
        recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
        
        return recommendations
    
    def _calculate_recommendation_score(self, job_docs: List[Dict[str, Any]], 
                                      user_profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """计算单个职位的推荐分数"""
        
        try:
            if not job_docs:
                return None
            
            # 提取职位信息
            job_info = self._extract_job_info_from_docs(job_docs)
            
            # 计算各维度分数
            scores = {}
            
            # 1. 技能匹配分数
            scores['skill_match'] = self._calculate_skill_match_score(user_profile, job_info)
            
            # 2. 经验匹配分数
            scores['experience_match'] = self._calculate_experience_match_score(user_profile, job_info)
            
            # 3. 薪资匹配分数
            scores['salary_match'] = self._calculate_salary_match_score(user_profile, job_info)
            
            # 4. 地点匹配分数
            scores['location_match'] = self._calculate_location_match_score(user_profile, job_info)
            
            # 5. 公司偏好分数
            scores['company_preference'] = self._calculate_company_preference_score(user_profile, job_info)
            
            # 6. 成长潜力分数
            scores['growth_potential'] = self._calculate_growth_potential_score(user_profile, job_info)
            
            # 计算综合推荐分数
            recommendation_score = sum(
                scores[dimension] * self.recommendation_weights[dimension]
                for dimension in scores
            )
            
            return {
                'job_id': job_info['job_id'],
                'job_title': job_info['job_title'],
                'company': job_info['company'],
                'location': job_info.get('location'),
                'salary_range': job_info.get('salary_range'),
                'recommendation_score': round(recommendation_score, 3),
                'dimension_scores': {k: round(v, 3) for k, v in scores.items()},
                'job_info': job_info,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"计算推荐分数失败: {e}")
            return None
    
    def _extract_job_info_from_docs(self, job_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """从职位文档中提取信息"""
        
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
            for field in ['job_id', 'job_title', 'company', 'location', 'education', 'experience']:
                if not job_info[field] and metadata.get(field):
                    job_info[field] = metadata[field]
            
            # 薪资信息
            if metadata.get('salary_min'):
                job_info['salary_range']['min'] = metadata['salary_min']
            if metadata.get('salary_max'):
                job_info['salary_range']['max'] = metadata['salary_max']
            
            # 技能信息
            if metadata.get('skills'):
                job_info['skills'].extend(metadata['skills'])
            
            # 内容信息
            doc_type = metadata.get('type')
            content = doc.get('content', '')
            
            if doc_type == 'responsibility':
                job_info['responsibilities'].append(content)
            elif doc_type == 'requirement':
                job_info['requirements'].append(content)
        
        # 去重技能
        job_info['skills'] = list(set(job_info['skills']))
        
        return job_info
    
    def _calculate_skill_match_score(self, user_profile: Dict[str, Any], 
                                   job_info: Dict[str, Any]) -> float:
        """计算技能匹配分数"""
        
        user_skills = set(skill.lower() for skill in user_profile.get('skills', []))
        job_skills = set(skill.lower() for skill in job_info.get('skills', []))
        
        if not user_skills or not job_skills:
            return 0.5
        
        # 计算交集
        matched_skills = user_skills.intersection(job_skills)
        
        # 基础匹配分数
        basic_score = len(matched_skills) / len(job_skills)
        
        # 考虑用户技能覆盖度
        user_coverage = len(matched_skills) / len(user_skills)
        
        # 综合分数
        final_score = (basic_score * 0.7 + user_coverage * 0.3)
        
        return min(final_score, 1.0)
    
    def _calculate_experience_match_score(self, user_profile: Dict[str, Any], 
                                        job_info: Dict[str, Any]) -> float:
        """计算经验匹配分数"""
        
        user_years = user_profile.get('experience_years', 0)
        job_experience = job_info.get('experience', '')
        
        if not job_experience or job_experience == '不限':
            return 1.0
        
        # 提取职位要求的年限
        required_years = self._extract_years_from_text(job_experience)
        
        if required_years is None:
            return 0.8
        
        if user_years >= required_years:
            # 经验超出要求，但不要过度奖励
            excess_ratio = user_years / required_years
            if excess_ratio <= 1.5:
                return 1.0
            else:
                return max(0.8, 1.0 - (excess_ratio - 1.5) * 0.1)
        else:
            # 经验不足
            shortage_ratio = user_years / required_years
            return max(0.2, shortage_ratio)
    
    def _calculate_salary_match_score(self, user_profile: Dict[str, Any], 
                                    job_info: Dict[str, Any]) -> float:
        """计算薪资匹配分数"""
        
        expected_min = user_profile.get('expected_salary_min')
        expected_max = user_profile.get('expected_salary_max')
        
        job_salary = job_info.get('salary_range', {})
        job_min = job_salary.get('min')
        job_max = job_salary.get('max')
        
        # 如果任一方没有薪资信息
        if not (expected_min or expected_max) or not (job_min or job_max):
            return 0.7
        
        # 计算匹配度
        exp_min = expected_min or 0
        exp_max = expected_max or expected_min or 999999
        job_min = job_min or 0
        job_max = job_max or job_min or 999999
        
        # 检查重叠
        overlap_min = max(exp_min, job_min)
        overlap_max = min(exp_max, job_max)
        
        if overlap_min <= overlap_max:
            # 有重叠
            overlap_size = overlap_max - overlap_min
            total_range = max(exp_max - exp_min, job_max - job_min)
            return min(overlap_size / max(total_range, 1), 1.0)
        else:
            # 无重叠，计算距离
            gap = overlap_min - overlap_max
            avg_salary = (exp_min + exp_max + job_min + job_max) / 4
            penalty = gap / max(avg_salary, 1)
            return max(0.0, 1.0 - penalty)
    
    def _calculate_location_match_score(self, user_profile: Dict[str, Any], 
                                      job_info: Dict[str, Any]) -> float:
        """计算地点匹配分数"""
        
        preferred_locations = user_profile.get('preferred_locations', [])
        job_location = job_info.get('location', '')
        
        if not preferred_locations or not job_location:
            return 0.7  # 无偏好或无地点信息，给中等分数
        
        # 检查是否匹配
        job_location_lower = job_location.lower()
        
        for preferred in preferred_locations:
            if preferred.lower() in job_location_lower or job_location_lower in preferred.lower():
                return 1.0
        
        return 0.3  # 不匹配
    
    def _calculate_company_preference_score(self, user_profile: Dict[str, Any], 
                                          job_info: Dict[str, Any]) -> float:
        """计算公司偏好分数"""
        
        preferred_companies = user_profile.get('preferred_companies', [])
        avoided_companies = user_profile.get('avoided_companies', [])
        job_company = job_info.get('company', '')
        
        if not job_company:
            return 0.7
        
        job_company_lower = job_company.lower()
        
        # 检查偏好公司
        if preferred_companies:
            for preferred in preferred_companies:
                if preferred.lower() in job_company_lower:
                    return 1.0
        
        # 检查避免的公司
        if avoided_companies:
            for avoided in avoided_companies:
                if avoided.lower() in job_company_lower:
                    return 0.1
        
        return 0.7  # 默认分数
    
    def _calculate_growth_potential_score(self, user_profile: Dict[str, Any], 
                                        job_info: Dict[str, Any]) -> float:
        """计算成长潜力分数"""
        
        # 基于职位描述中的关键词判断成长潜力
        growth_keywords = [
            '发展', '成长', '晋升', '培训', '学习', '挑战', '创新',
            '领导', '管理', '项目', '团队', '技术栈', '新技术'
        ]
        
        # 检查职责和要求中的成长关键词
        all_content = []
        all_content.extend(job_info.get('responsibilities', []))
        all_content.extend(job_info.get('requirements', []))
        
        content_text = ' '.join(all_content).lower()
        
        growth_score = 0.0
        for keyword in growth_keywords:
            if keyword in content_text:
                growth_score += 0.1
        
        # 基于公司规模调整（如果有的话）
        # 这里可以根据实际需求添加更复杂的逻辑
        
        return min(growth_score, 1.0)
    
    def _extract_years_from_text(self, text: str) -> Optional[int]:
        """从文本中提取年限"""
        
        import re
        
        patterns = [
            r'(\d+)\s*年',
            r'(\d+)\s*-\s*\d+\s*年',
            r'(\d+)\+\s*年'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))
        
        return None
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重结果"""
        
        seen_job_ids = set()
        unique_results = []
        
        for result in results:
            job_id = result.get('metadata', {}).get('job_id')
            if job_id and job_id not in seen_job_ids:
                seen_job_ids.add(job_id)
                unique_results.append(result)
        
        return unique_results
    
    def _rescore_hybrid_results(self, recommendations: List[Dict[str, Any]], 
                              user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """重新评分混合推荐结果"""
        
        # 重新计算推荐分数，考虑多种策略的结果
        for rec in recommendations:
            # 这里可以添加更复杂的重评分逻辑
            # 例如考虑结果来源的多样性等
            pass
        
        # 按分数排序
        recommendations.sort(key=lambda x: x.get('recommendation_score', 0), reverse=True)
        
        return recommendations
    
    def _apply_diversity_control(self, recommendations: List[Dict[str, Any]], 
                               k: int) -> List[Dict[str, Any]]:
        """应用多样性控制"""
        
        if len(recommendations) <= k:
            return recommendations
        
        diverse_recs = []
        company_counts = Counter()
        location_counts = Counter()
        
        for rec in recommendations:
            company = rec.get('company', '')
            location = rec.get('location', '')
            
            # 检查多样性约束
            if (company_counts[company] >= self.diversity_config['max_same_company'] or
                location_counts[location] >= self.diversity_config['max_same_location']):
                continue
            
            diverse_recs.append(rec)
            company_counts[company] += 1
            location_counts[location] += 1
            
            if len(diverse_recs) >= k:
                break
        
        # 如果多样性控制后结果不足，补充剩余的高分结果
        if len(diverse_recs) < k:
            remaining_count = k - len(diverse_recs)
            added_job_ids = {rec['job_id'] for rec in diverse_recs}
            
            for rec in recommendations:
                if rec['job_id'] not in added_job_ids:
                    diverse_recs.append(rec)
                    remaining_count -= 1
                    if remaining_count <= 0:
                        break
        
        return diverse_recs
    
    def _add_recommendation_explanations(self, recommendations: List[Dict[str, Any]], 
                                       user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """添加推荐解释"""
        
        for rec in recommendations:
            explanation = self._generate_recommendation_explanation(rec, user_profile)
            rec['explanation'] = explanation
        
        return recommendations
    
    def _generate_recommendation_explanation(self, recommendation: Dict[str, Any], 
                                           user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """生成推荐解释"""
        
        explanation = {
            'main_reasons': [],
            'skill_matches': [],
            'potential_concerns': [],
            'growth_opportunities': []
        }
        
        dimension_scores = recommendation.get('dimension_scores', {})
        job_info = recommendation.get('job_info', {})
        
        # 主要推荐原因
        if dimension_scores.get('skill_match', 0) >= 0.8:
            explanation['main_reasons'].append("技能高度匹配")
        
        if dimension_scores.get('experience_match', 0) >= 0.8:
            explanation['main_reasons'].append("经验要求符合")
        
        if dimension_scores.get('salary_match', 0) >= 0.8:
            explanation['main_reasons'].append("薪资期望匹配")
        
        # 技能匹配详情
        user_skills = set(skill.lower() for skill in user_profile.get('skills', []))
        job_skills = set(skill.lower() for skill in job_info.get('skills', []))
        matched_skills = user_skills.intersection(job_skills)
        
        explanation['skill_matches'] = list(matched_skills)
        
        # 潜在关注点
        if dimension_scores.get('experience_match', 0) < 0.5:
            explanation['potential_concerns'].append("经验要求可能较高")
        
        if dimension_scores.get('salary_match', 0) < 0.5:
            explanation['potential_concerns'].append("薪资可能不完全匹配期望")
        
        # 成长机会
        if dimension_scores.get('growth_potential', 0) >= 0.7:
            explanation['growth_opportunities'].append("具有良好的成长发展空间")
        
        return explanation
    
    def get_recommendation_analytics(self, recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取推荐分析"""
        
        if not recommendations:
            return {}
        
        analytics = {
            'total_recommendations': len(recommendations),
            'score_distribution': {
                'excellent': 0,  # >= 0.8
                'good': 0,       # >= 0.6
                'fair': 0,       # >= 0.4
                'poor': 0        # < 0.4
            },
            'company_distribution': Counter(),
            'location_distribution': Counter(),
            'skill_frequency': Counter(),
            'average_scores': {}
        }
        
        all_scores = []
        dimension_totals = defaultdict(float)
        
        for rec in recommendations:
            score = rec.get('recommendation_score', 0)
            all_scores.append(score)
            
            # 分数分布
            if score >= 0.8:
                analytics['score_distribution']['excellent'] += 1
            elif score >= 0.6:
                analytics['score_distribution']['good'] += 1
            elif score >= 0.4:
                analytics['score_distribution']['fair'] += 1
            else:
                analytics['score_distribution']['poor'] += 1
            
            # 公司和地点分布
            company = rec.get('company', 'Unknown')
            location = rec.get('location', 'Unknown')
            analytics['company_distribution'][company] += 1
            analytics['location_distribution'][location] += 1
            
            # 技能频率
            job_info = rec.get('job_info', {})
            skills = job_info.get('skills', [])
            for skill in skills:
                analytics['skill_frequency'][skill.lower()] += 1
            
            # 维度分数累计
            dimension_scores = rec.get('dimension_scores', {})
            for dim, score in dimension_scores.items():
                dimension_totals[dim] += score
        
        # 计算平均分数
        count = len(recommendations)
        analytics['average_scores'] = {
            'overall': sum(all_scores) / count,
            **{dim: total / count for dim, total in dimension_totals.items()}
        }
        
        # 转换Counter为普通字典并排序
        analytics['company_distribution'] = dict(analytics['company_distribution'].most_common(10))
        analytics['location_distribution'] = dict(analytics['location_distribution'].most_common(10))
        analytics['skill_frequency'] = dict(analytics['skill_frequency'].most_common(20))
        
        return analytics