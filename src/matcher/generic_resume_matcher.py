#!/usr/bin/env python3
"""
通用简历职位匹配引擎
支持任意用户的灵活匹配系统
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from langchain.schema import Document

from ..rag.semantic_search import SemanticSearchEngine
from ..rag.vector_manager import ChromaDBManager
from ..utils.logger import get_logger
from .generic_resume_models import (
    GenericResumeProfile, DynamicSkillWeights, MatchLevel, RecommendationPriority,
    create_default_skill_weights, JobMatchResult, ResumeMatchingResult,
    MatchingSummary, CareerInsights, MatchAnalysis
)


class GenericResumeJobMatcher:
    """通用简历职位匹配引擎"""
    
    def __init__(self, 
                 vector_manager: ChromaDBManager,
                 config: Dict = None):
        self.vector_manager = vector_manager
        self.config = config or {}
        self.logger = get_logger(__name__)
        
        # 初始化组件
        self.search_engine = SemanticSearchEngine(vector_manager, config)
        
        # 匹配参数配置
        self.default_search_k = config.get('default_search_k', 60)
        self.min_score_threshold = config.get('min_score_threshold', 0.3)
        self.max_results = config.get('max_results', 20)
        
        # 动态权重配置
        self.matching_weights = config.get('weights', {
            'semantic_similarity': 0.35,
            'skills_match': 0.30,
            'experience_match': 0.20,
            'industry_match': 0.10,
            'salary_match': 0.05
        })
        
        # 初始化技能权重系统
        self.skill_weights = create_default_skill_weights()
        if config:
            self.skill_weights.update_from_config(config)
        
        # 性能监控
        self.performance_stats = {
            'total_matches': 0,
            'average_processing_time': 0.0,
            'cache_hits': 0
        }
    
    async def find_matching_jobs(self, 
                                resume_profile: GenericResumeProfile,
                                filters: Dict[str, Any] = None,
                                top_k: int = 20) -> ResumeMatchingResult:
        """为任意用户查找匹配的职位"""
        start_time = time.time()
        
        try:
            self.logger.info(f"开始为 {resume_profile.name} 查找匹配职位，目标数量: {top_k}")
            
            # 1. 构建个性化查询
            query = self._build_personalized_query(resume_profile)
            self.logger.debug(f"构建查询: {query[:100]}...")
            
            # 2. 执行语义搜索
            search_results = await self._execute_semantic_search(
                query, filters, k=min(self.default_search_k, top_k * 3)
            )
            
            self.logger.info(f"语义搜索返回 {len(search_results)} 个候选文档")
            
            # 3. 按职位ID分组文档
            jobs_by_id = self._group_results_by_job(search_results)
            self.logger.info(f"分组后得到 {len(jobs_by_id)} 个候选职位")
            
            # 4. 计算匹配分数
            matching_jobs = []
            for job_id, job_docs in jobs_by_id.items():
                try:
                    match_result = await self._calculate_match_score(
                        resume_profile, job_docs, job_id
                    )
                    
                    if match_result and match_result.overall_score >= self.min_score_threshold:
                        matching_jobs.append(match_result)
                        
                except Exception as e:
                    self.logger.warning(f"计算职位 {job_id} 匹配度失败: {str(e)}")
                    continue
            
            # 5. 排序和筛选结果
            matching_jobs.sort(key=lambda x: x.overall_score, reverse=True)
            top_matches = matching_jobs[:top_k]
            
            # 6. 生成匹配摘要和洞察
            processing_time = time.time() - start_time
            summary = self._generate_matching_summary(top_matches, processing_time)
            insights = self._generate_career_insights(top_matches, resume_profile)
            
            # 7. 创建完整结果
            result = ResumeMatchingResult(
                matching_summary=summary,
                matches=top_matches,
                career_insights=insights,
                resume_profile=resume_profile,  # 这里可能需要转换
                query_metadata={
                    'query': query,
                    'filters': filters,
                    'search_results_count': len(search_results),
                    'candidate_jobs_count': len(jobs_by_id),
                    'processing_time': processing_time
                }
            )
            
            # 更新性能统计
            self._update_performance_stats(processing_time, len(top_matches))
            
            self.logger.info(f"匹配完成，返回 {len(top_matches)} 个职位，耗时 {processing_time:.2f}秒")
            
            return result
            
        except Exception as e:
            self.logger.error(f"职位匹配失败: {str(e)}")
            raise
    
    def _build_personalized_query(self, resume_profile: GenericResumeProfile) -> str:
        """构建个性化查询"""
        query_parts = []
        
        # 1. 当前职位和经验
        if resume_profile.current_position:
            query_parts.append(f"{resume_profile.current_position} {resume_profile.total_experience_years}年经验")
        
        # 2. 核心技能（从各个分类中选择）
        all_skills = resume_profile.get_all_skills()
        if all_skills:
            # 根据权重排序技能，选择前8个
            weighted_skills = []
            for skill in all_skills[:15]:  # 限制技能数量避免查询过长
                weight = self.skill_weights.get_skill_weight(skill)
                weighted_skills.append((skill, weight))
            
            weighted_skills.sort(key=lambda x: x[1], reverse=True)
            top_skills = [skill for skill, _ in weighted_skills[:8]]
            query_parts.append("核心技能: " + " ".join(top_skills))
        
        # 3. 期望职位
        if resume_profile.preferred_positions:
            preferred_text = " ".join(resume_profile.preferred_positions[:3])
            query_parts.append(f"目标职位: {preferred_text}")
        
        # 4. 行业经验
        if resume_profile.industry_experience:
            industries = list(resume_profile.industry_experience.keys())[:2]
            query_parts.append(f"行业经验: {' '.join(industries)}")
        
        # 5. 软技能和管理经验
        if resume_profile.soft_skills:
            soft_skills_text = " ".join(resume_profile.soft_skills[:3])
            query_parts.append(f"软技能: {soft_skills_text}")
        
        query = " ".join(query_parts)
        return query
    
    async def _execute_semantic_search(self,
                                     query: str,
                                     filters: Dict[str, Any] = None,
                                     k: int = 60) -> List[Tuple[Document, float]]:
        """执行语义搜索"""
        try:
            # 直接调用向量管理器的搜索方法，返回 (Document, float) 元组
            search_results = self.vector_manager.similarity_search_with_score(
                query=query,
                k=k,
                filters=filters
            )
            
            return search_results
            
        except Exception as e:
            self.logger.error(f"语义搜索失败: {str(e)}")
            return []
    
    def _group_results_by_job(self, search_results: List[Tuple[Document, float]]) -> Dict[str, List[Document]]:
        """按职位ID分组搜索结果"""
        jobs_by_id = defaultdict(list)
        
        for doc, score in search_results:
            job_id = doc.metadata.get('job_id')
            if job_id:
                doc.metadata['search_score'] = score
                jobs_by_id[job_id].append(doc)
        
        return dict(jobs_by_id)
    
    async def _calculate_match_score(self, 
                                   resume_profile: GenericResumeProfile,
                                   job_docs: List[Document],
                                   job_id: str) -> Optional[JobMatchResult]:
        """计算匹配分数"""
        try:
            # 提取职位元数据
            job_metadata = self._extract_job_metadata(job_docs, job_id)
            
            # 计算各维度分数
            semantic_score = self._calculate_semantic_similarity(resume_profile, job_docs)
            skills_score = self._calculate_skills_match(resume_profile, job_docs, job_metadata)
            experience_score = self._calculate_experience_match(resume_profile, job_metadata)
            industry_score = self._calculate_industry_match(resume_profile, job_metadata)
            salary_score = self._calculate_salary_match(resume_profile, job_metadata)
            
            # 计算加权总分
            dimension_scores = {
                'semantic_similarity': semantic_score,
                'skills_match': skills_score,
                'experience_match': experience_score,
                'industry_match': industry_score,
                'salary_match': salary_score
            }
            
            overall_score = (
                semantic_score * self.matching_weights['semantic_similarity'] +
                skills_score * self.matching_weights['skills_match'] +
                experience_score * self.matching_weights['experience_match'] +
                industry_score * self.matching_weights['industry_match'] +
                salary_score * self.matching_weights['salary_match']
            )
            
            # 生成匹配分析
            match_analysis = self._generate_match_analysis(
                resume_profile, job_docs, job_metadata, dimension_scores
            )
            
            # 创建匹配结果
            match_result = JobMatchResult(
                job_id=job_metadata.get('job_id', 'unknown'),
                job_title=job_metadata.get('job_title', 'Unknown Position'),
                company=job_metadata.get('company', 'Unknown Company'),
                location=job_metadata.get('location'),
                salary_range=job_metadata.get('salary_range'),
                overall_score=overall_score,
                dimension_scores=dimension_scores,
                match_level=self._get_match_level_from_score(overall_score),
                match_analysis=match_analysis,
                recommendation_priority=self._get_recommendation_priority_from_score(overall_score),
                confidence_level=self._calculate_confidence_level(dimension_scores),
                processing_time=time.time()
            )
            
            return match_result
            
        except Exception as e:
            self.logger.error(f"计算职位 {job_id} 匹配度失败: {str(e)}")
            return None
    
    def _calculate_semantic_similarity(self, 
                                     resume_profile: GenericResumeProfile,
                                     job_docs: List[Document]) -> float:
        """计算语义相似度"""
        try:
            # 构建简历文本
            resume_text = self._build_resume_text(resume_profile)
            
            # 构建职位文本
            job_text = " ".join([doc.page_content for doc in job_docs])
            
            # 使用简单的文本相似度计算（可以替换为更复杂的算法）
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            
            texts = [resume_text, job_text]
            vectorizer = TfidfVectorizer(max_features=1000, stop_words='english', ngram_range=(1, 2))
            tfidf_matrix = vectorizer.fit_transform(texts)
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            similarity_score = similarity_matrix[0, 1]
            return max(0.0, min(1.0, similarity_score))
            
        except Exception as e:
            self.logger.error(f"计算语义相似度失败: {str(e)}")
            return 0.0
    
    def _calculate_skills_match(self, 
                              resume_profile: GenericResumeProfile,
                              job_docs: List[Document],
                              job_metadata: Dict[str, Any]) -> float:
        """计算技能匹配度"""
        try:
            # 获取简历技能
            resume_skills = [skill.lower() for skill in resume_profile.get_all_skills()]
            
            # 获取职位技能要求
            job_skills = self._extract_job_skills(job_docs, job_metadata)
            
            if not job_skills:
                return 0.5
            
            # 计算加权匹配
            matched_skills = []
            total_job_skill_weight = 0
            matched_skill_weight = 0
            
            for job_skill in job_skills:
                skill_weight = self.skill_weights.get_skill_weight(job_skill)
                total_job_skill_weight += skill_weight
                
                if self._is_skill_matched(job_skill, resume_skills):
                    matched_skills.append(job_skill)
                    matched_skill_weight += skill_weight
            
            # 计算匹配率
            if total_job_skill_weight > 0:
                match_rate = matched_skill_weight / total_job_skill_weight
            else:
                match_rate = 0.0
            
            # 考虑高价值技能加分
            bonus_score = self._calculate_skill_bonus(resume_skills, job_skills)
            
            final_score = min(1.0, match_rate + bonus_score)
            
            return final_score
            
        except Exception as e:
            self.logger.error(f"计算技能匹配度失败: {str(e)}")
            return 0.0
    
    def _calculate_experience_match(self, 
                                  resume_profile: GenericResumeProfile,
                                  job_metadata: Dict[str, Any]) -> float:
        """计算经验匹配度"""
        try:
            required_years = self._extract_required_experience(job_metadata)
            resume_years = resume_profile.total_experience_years
            
            if required_years is None:
                return 0.9
            
            if resume_years >= required_years:
                if resume_years <= required_years * 2:
                    return 1.0
                else:
                    # 经验过多可能被认为overqualified
                    return 0.95
            else:
                return min(1.0, resume_years / required_years)
            
        except Exception as e:
            self.logger.error(f"计算经验匹配度失败: {str(e)}")
            return 0.0
    
    def _calculate_industry_match(self, 
                                resume_profile: GenericResumeProfile,
                                job_metadata: Dict[str, Any]) -> float:
        """计算行业匹配度"""
        try:
            job_industry = job_metadata.get('industry', '').lower()
            
            if not job_industry:
                return 0.7
            
            # 检查直接行业匹配
            for resume_industry, weight in resume_profile.industry_experience.items():
                if resume_industry.lower() in job_industry or job_industry in resume_industry.lower():
                    return weight
            
            # 检查相关行业匹配
            return self._calculate_industry_similarity(job_industry, list(resume_profile.industry_experience.keys()))
            
        except Exception as e:
            self.logger.error(f"计算行业匹配度失败: {str(e)}")
            return 0.0
    
    def _calculate_salary_match(self, 
                              resume_profile: GenericResumeProfile,
                              job_metadata: Dict[str, Any]) -> float:
        """计算薪资匹配度"""
        try:
            job_salary_range = job_metadata.get('salary_range')
            
            if not job_salary_range or not resume_profile.expected_salary_range:
                return 0.8
            
            resume_min = resume_profile.expected_salary_range.get('min', 0)
            resume_max = resume_profile.expected_salary_range.get('max', 0)
            
            if resume_min == 0 and resume_max == 0:
                return 0.8
            
            job_min = job_salary_range.get('min', 0)
            job_max = job_salary_range.get('max', float('inf'))
            
            # 计算薪资范围重叠度
            overlap_min = max(resume_min, job_min)
            overlap_max = min(resume_max, job_max)
            
            if overlap_max >= overlap_min:
                overlap_size = overlap_max - overlap_min
                resume_range_size = resume_max - resume_min
                job_range_size = job_max - job_min if job_max != float('inf') else resume_range_size
                
                if resume_range_size > 0 and job_range_size > 0:
                    overlap_ratio = overlap_size / min(resume_range_size, job_range_size)
                    return min(1.0, overlap_ratio)
            
            return 0.5
            
        except Exception as e:
            self.logger.error(f"计算薪资匹配度失败: {str(e)}")
            return 0.0
    
    def _build_resume_text(self, resume_profile: GenericResumeProfile) -> str:
        """构建简历文本"""
        text_parts = []
        
        # 基本信息
        if resume_profile.current_position:
            text_parts.append(f"{resume_profile.current_position} {resume_profile.total_experience_years}年经验")
        
        # 技能
        all_skills = resume_profile.get_all_skills()
        if all_skills:
            text_parts.append(" ".join(all_skills))
        
        # 工作经历
        for work_exp in resume_profile.work_history:
            text_parts.append(f"{work_exp.company} {work_exp.position} {work_exp.industry}")
            text_parts.extend(work_exp.responsibilities)
            text_parts.extend(work_exp.achievements)
            text_parts.extend(work_exp.technologies)
        
        # 项目经验
        for project in resume_profile.projects:
            text_parts.append(f"{project.name} {project.description}")
            text_parts.extend(project.technologies)
        
        # 职业目标
        text_parts.extend(resume_profile.career_objectives)
        text_parts.extend(resume_profile.preferred_positions)
        
        return " ".join(text_parts)
    
    def _extract_job_metadata(self, job_docs: List[Document], job_id: str) -> Dict[str, Any]:
        """提取职位元数据"""
        metadata = {'job_id': job_id}
        
        for doc in job_docs:
            doc_metadata = doc.metadata
            
            for key in ['job_title', 'company', 'location', 'industry']:
                if key in doc_metadata:
                    metadata[key] = doc_metadata[key]
            
            if 'salary_min' in doc_metadata and 'salary_max' in doc_metadata:
                metadata['salary_range'] = {
                    'min': doc_metadata['salary_min'],
                    'max': doc_metadata['salary_max']
                }
            
            if 'skills' in doc_metadata:
                if 'skills' not in metadata:
                    metadata['skills'] = []
                metadata['skills'].extend(doc_metadata['skills'])
            
            if 'required_experience_years' in doc_metadata:
                metadata['required_experience_years'] = doc_metadata['required_experience_years']
        
        if 'skills' in metadata:
            metadata['skills'] = list(set(metadata['skills']))
        
        metadata['description'] = " ".join([doc.page_content for doc in job_docs])
        
        return metadata
    
    def _extract_job_skills(self, job_docs: List[Document], job_metadata: Dict[str, Any]) -> List[str]:
        """提取职位技能要求"""
        skills = []
        
        # 从元数据中获取技能
        if 'skills' in job_metadata and isinstance(job_metadata['skills'], list):
            skills.extend(job_metadata['skills'])
        
        # 从文档内容中提取技能（简化版本）
        job_text = " ".join([doc.page_content for doc in job_docs]).lower()
        
        # 常见技能关键词
        common_skills = [
            'python', 'java', 'javascript', 'react', 'vue', 'angular', 'node.js',
            'spring', 'django', 'flask', 'mysql', 'postgresql', 'mongodb', 'redis',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'machine learning',
            'deep learning', 'ai', 'data science', 'big data', 'spark', 'hadoop',
            'tensorflow', 'pytorch', 'git', 'linux', 'agile', 'scrum', 'devops',
            'c#', 'c++', 'golang', 'typescript', 'html', 'css', 'bootstrap',
            'jquery', 'webpack', 'npm', 'yarn', 'sass', 'less'
        ]
        
        # 只添加在职位文本中找到的技能关键词
        for skill in common_skills:
            if skill.lower() in job_text:
                skills.append(skill)
        
        # 去重并过滤空值
        unique_skills = []
        for skill in skills:
            if skill and skill.strip() and skill not in unique_skills:
                unique_skills.append(skill.lower().strip())
        
        return unique_skills
    
    def _is_skill_matched(self, job_skill: str, resume_skills: List[str]) -> bool:
        """判断技能是否匹配"""
        job_skill_lower = job_skill.lower()
        
        if job_skill_lower in resume_skills:
            return True
        
        # 部分匹配
        for resume_skill in resume_skills:
            if job_skill_lower in resume_skill or resume_skill in job_skill_lower:
                return True
        
        return False
    
    def _calculate_skill_bonus(self, resume_skills: List[str], job_skills: List[str]) -> float:
        """计算技能加分"""
        bonus = 0.0
        
        # 高价值技能加分
        high_value_skills = ['ai', 'machine learning', 'deep learning', 'kubernetes', 'aws', 'azure']
        
        for skill in resume_skills:
            if skill in high_value_skills and skill not in job_skills:
                bonus += 0.05
        
        return min(0.2, bonus)
    
    def _extract_required_experience(self, job_metadata: Dict[str, Any]) -> Optional[int]:
        """提取职位经验要求"""
        if 'required_experience_years' in job_metadata:
            return job_metadata['required_experience_years']
        
        # 从职位描述中提取（简化版本）
        job_description = job_metadata.get('description', '').lower()
        
        import re
        patterns = [
            r'(\d+)\+?\s*years?\s*of?\s*experience',
            r'(\d+)\+?\s*年.*经验',
            r'experience.*(\d+)\+?\s*years?',
            r'minimum.*(\d+)\s*years?'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, job_description)
            if matches:
                return int(matches[0])
        
        return None
    
    def _calculate_industry_similarity(self, job_industry: str, resume_industries: List[str]) -> float:
        """计算行业相似度"""
        # 简化的行业相关性
        industry_relations = {
            '科技': ['互联网', 'ai', '软件', '技术'],
            '制药': ['医疗', '生物', '健康'],
            '金融': ['银行', '保险', '投资'],
            '咨询': ['管理', '战略', '顾问']
        }
        
        max_similarity = 0.0
        
        for resume_industry in resume_industries:
            if job_industry.lower() in resume_industry.lower() or resume_industry.lower() in job_industry.lower():
                max_similarity = max(max_similarity, 0.8)
            
            for category, related_terms in industry_relations.items():
                if any(term in job_industry.lower() for term in related_terms):
                    if any(term in resume_industry.lower() for term in related_terms):
                        max_similarity = max(max_similarity, 0.6)
        
        return max_similarity
    
    def _calculate_confidence_level(self, dimension_scores: Dict[str, float]) -> float:
        """计算置信度"""
        import numpy as np
        scores = list(dimension_scores.values())
        mean_score = np.mean(scores)
        variance = np.var(scores)
        
        confidence = max(0.5, 1.0 - variance)
        return confidence
    
    def _get_match_level_from_score(self, score: float) -> MatchLevel:
        """根据分数获取匹配等级"""
        if score >= 0.85:
            return MatchLevel.EXCELLENT
        elif score >= 0.70:
            return MatchLevel.GOOD
        elif score >= 0.50:
            return MatchLevel.FAIR
        else:
            return MatchLevel.POOR
    
    def _get_recommendation_priority_from_score(self, score: float) -> RecommendationPriority:
        """根据分数获取推荐优先级"""
        if score >= 0.85:
            return RecommendationPriority.HIGH
        elif score >= 0.70:
            return RecommendationPriority.MEDIUM
        elif score >= 0.50:
            return RecommendationPriority.LOW
        else:
            return RecommendationPriority.NOT_RECOMMENDED
    
    def _generate_match_analysis(self, 
                               resume_profile: GenericResumeProfile,
                               job_docs: List[Document],
                               job_metadata: Dict[str, Any],
                               dimension_scores: Dict[str, float]) -> MatchAnalysis:
        """生成匹配分析"""
        analysis = MatchAnalysis()
        
        # 分析优势
        if dimension_scores['skills_match'] >= 0.8:
            analysis.strengths.append("技能匹配度极高")
        elif dimension_scores['skills_match'] >= 0.6:
            analysis.strengths.append("技能匹配度良好")
        
        if dimension_scores['experience_match'] >= 0.9:
            analysis.strengths.append("经验完全符合要求")
        elif dimension_scores['experience_match'] >= 0.7:
            analysis.strengths.append("经验基本符合要求")
        
        if dimension_scores['salary_match'] >= 0.8:
            analysis.strengths.append("薪资期望合理")
        
        # 分析劣势
        if dimension_scores['skills_match'] < 0.5:
            analysis.weaknesses.append("部分关键技能需要提升")
        
        if dimension_scores['industry_match'] < 0.6:
            analysis.weaknesses.append("行业转换需要适应")
        
        if dimension_scores['semantic_similarity'] < 0.5:
            analysis.weaknesses.append("职位描述匹配度有待提高")
        
        # 生成建议
        if dimension_scores['skills_match'] < 0.7:
            analysis.recommendations.append("重点突出相关技能和项目经验")
        
        if dimension_scores['industry_match'] < 0.6:
            analysis.recommendations.append("准备行业转换说明和学习计划")
        
        # 提取匹配和缺失的技能
        resume_skills = [skill.lower().strip() for skill in resume_profile.get_all_skills() if skill and skill.strip()]
        job_skills = self._extract_job_skills(job_docs, job_metadata)
        
        # 确保job_skills是有效的技能列表，过滤掉单个字符和无效技能
        valid_job_skills = [skill for skill in job_skills if skill and len(skill.strip()) > 1 and skill.strip().isalpha()]
        
        for job_skill in valid_job_skills:
            if self._is_skill_matched(job_skill, resume_skills):
                analysis.matched_skills.append(job_skill)
            else:
                analysis.missing_skills.append(job_skill)
        
        # 计算各项指标
        analysis.skill_gap_score = 1.0 - dimension_scores['skills_match']
        analysis.experience_alignment = dimension_scores['experience_match']
        analysis.industry_fit = dimension_scores['industry_match']
        
        return analysis
    
    def _generate_matching_summary(self, 
                                 matches: List[JobMatchResult],
                                 processing_time: float) -> MatchingSummary:
        """生成匹配结果摘要"""
        summary = MatchingSummary()
        
        summary.total_matches = len(matches)
        summary.processing_time = processing_time
        
        if matches:
            summary.average_score = sum(match.overall_score for match in matches) / len(matches)
            
            for match in matches:
                if match.recommendation_priority == RecommendationPriority.HIGH:
                    summary.high_priority += 1
                elif match.recommendation_priority == RecommendationPriority.MEDIUM:
                    summary.medium_priority += 1
                elif match.recommendation_priority == RecommendationPriority.LOW:
                    summary.low_priority += 1
        
        return summary
    
    def _generate_career_insights(self, 
                                matches: List[JobMatchResult],
                                resume_profile: GenericResumeProfile) -> CareerInsights:
        """生成职业洞察分析"""
        insights = CareerInsights()
        
        if not matches:
            return insights
        
        # 分析热门职位
        position_counts = defaultdict(int)
        for match in matches:
            position_counts[match.job_title] += 1
        
        insights.top_matching_positions = [
            pos for pos, count in sorted(position_counts.items(),
                                       key=lambda x: x[1], reverse=True)[:5]
        ]
        
        # 技能差距分析
        all_missing_skills = []
        high_demand_skills = defaultdict(int)
        
        for match in matches:
            all_missing_skills.extend(match.match_analysis.missing_skills)
            
            if match.overall_score >= 0.7:
                for skill in match.match_analysis.missing_skills:
                    high_demand_skills[skill] += 1
        
        insights.skill_gap_analysis = {
            'high_demand_missing': [
                skill for skill, count in sorted(high_demand_skills.items(),
                                                key=lambda x: x[1], reverse=True)[:5]
            ],
            'emerging_skills': ['AI/ML', 'Cloud Native', 'DevOps', 'Microservices', 'Data Science']
        }
        
        # 薪资分析
        salary_ranges = []
        for match in matches:
            if match.salary_range:
                salary_ranges.append(match.salary_range)
        
        if salary_ranges:
            min_salaries = [sr['min'] for sr in salary_ranges if 'min' in sr]
            max_salaries = [sr['max'] for sr in salary_ranges if 'max' in sr]
            
            if min_salaries and max_salaries:
                market_min = min(min_salaries)
                market_max = max(max_salaries)
                
                insights.salary_analysis = {
                    'market_range': {'min': market_min, 'max': market_max},
                    'your_range': resume_profile.expected_salary_range,
                    'market_position': self._analyze_salary_position(
                        resume_profile.expected_salary_range, market_min, market_max
                    )
                }
        
        # 市场趋势
        insights.market_trends = [
            "AI/ML技能需求持续增长",
            "云平台技能成为标配",
            "全栈开发能力受欢迎",
            "软技能越来越重要"
        ]
        
        # 职业建议
        insights.career_recommendations = self._generate_career_recommendations(
            matches, resume_profile
        )
        
        return insights
    
    def _analyze_salary_position(self,
                               expected_range: Dict[str, int],
                               market_min: int,
                               market_max: int) -> str:
        """分析薪资市场定位"""
        if not expected_range or expected_range.get('min', 0) == 0:
            return "未设定期望薪资"
        
        expected_mid = (expected_range['min'] + expected_range['max']) / 2
        market_mid = (market_min + market_max) / 2
        
        if expected_mid >= market_mid * 1.2:
            return "高于市场水平"
        elif expected_mid >= market_mid * 0.8:
            return "符合市场水平"
        else:
            return "低于市场水平"
    
    def _generate_career_recommendations(self,
                                       matches: List[JobMatchResult],
                                       resume_profile: GenericResumeProfile) -> List[str]:
        """生成职业建议"""
        recommendations = []
        
        high_score_matches = [m for m in matches if m.overall_score >= 0.8]
        
        if len(high_score_matches) >= 5:
            recommendations.append("您的背景非常符合市场需求，可以积极申请高匹配度职位")
        elif len(high_score_matches) >= 2:
            recommendations.append("有几个高匹配度职位，建议重点关注和准备")
        else:
            recommendations.append("建议提升关键技能以增加匹配度")
        
        # 基于技能差距的建议
        common_missing_skills = defaultdict(int)
        for match in matches[:10]:
            for skill in match.match_analysis.missing_skills:
                common_missing_skills[skill] += 1
        
        if common_missing_skills:
            top_missing = max(common_missing_skills.items(), key=lambda x: x[1])
            recommendations.append(f"建议重点学习 {top_missing[0]} 技能")
        
        # 基于行业经验的建议
        avg_industry_score = sum(m.dimension_scores.get('industry_match', 0) for m in matches) / len(matches)
        if avg_industry_score < 0.6:
            recommendations.append("考虑准备行业转换的说明和学习计划")
        
        return recommendations
    
    def _update_performance_stats(self, processing_time: float, results_count: int):
        """更新性能统计"""
        self.performance_stats['total_matches'] += results_count
        
        current_avg = self.performance_stats['average_processing_time']
        total_operations = self.performance_stats.get('total_operations', 0) + 1
        
        new_avg = (current_avg * (total_operations - 1) + processing_time) / total_operations
        self.performance_stats['average_processing_time'] = new_avg
        self.performance_stats['total_operations'] = total_operations
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        return self.performance_stats.copy()
    
    def reset_performance_stats(self):
        """重置性能统计"""
        self.performance_stats = {
            'total_matches': 0,
            'average_processing_time': 0.0,
            'cache_hits': 0,
            'total_operations': 0
        }