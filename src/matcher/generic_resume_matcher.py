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
        
        # 匹配参数配置 - 提高阈值降低匹配率，确保质量
        self.default_search_k = config.get('default_search_k', 80)  # 增加搜索范围
        self.min_score_threshold = config.get('min_score_threshold', 0.45)  # 提高最低阈值到0.45，确保匹配质量
        self.max_results = config.get('max_results', 30)  # 增加最大结果数
        
        # 动态权重配置 - 从配置文件读取
        self.matching_weights = self._load_matching_weights(config)
        
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
    
    def _load_matching_weights(self, config: Dict) -> Dict[str, float]:
        """从配置文件加载匹配权重 - 支持高级匹配配置"""
        # 优化的默认权重 - 针对20年经验资深人士
        default_weights = {
            'semantic_similarity': 0.40,  # 语义相似度权重
            'skills_match': 0.45,         # 技能匹配权重（最重要）
            'experience_match': 0.05,     # 经验权重（20年经验基本都满足）
            'industry_match': 0.02,       # 行业权重（IT跨行业）
            'salary_match': 0.08          # 薪资权重（重要但不是决定性）
        }
        
        # 优先读取高级匹配配置
        if config and 'resume_matching_advanced' in config:
            advanced_config = config['resume_matching_advanced']
            
            # 读取高级权重配置
            if 'matching_weights' in advanced_config:
                advanced_weights = advanced_config['matching_weights']
                default_weights.update(advanced_weights)
                self.logger.info(f"🚀 使用高级匹配权重配置: {default_weights}")
            
            # 读取高级阈值配置
            if 'match_thresholds' in advanced_config:
                thresholds = advanced_config['match_thresholds']
                if 'poor' in thresholds:
                    self.min_score_threshold = thresholds['poor']
                    self.logger.info(f"🎯 使用高级匹配阈值: {self.min_score_threshold}")
            
            # 读取高级搜索范围配置
            if 'default_search_k' in advanced_config:
                self.default_search_k = advanced_config['default_search_k']
                self.logger.info(f"🔍 使用高级搜索范围: {self.default_search_k}")
            
            # 读取高级最大结果配置
            if 'max_results' in advanced_config:
                self.max_results = advanced_config['max_results']
                self.logger.info(f"📊 使用高级最大结果数: {self.max_results}")
        
        # 回退到标准配置读取
        elif config and 'modules' in config and 'resume_matching' in config['modules']:
            resume_matching_config = config['modules']['resume_matching']
            
            if 'algorithms' in resume_matching_config:
                algorithms = resume_matching_config['algorithms']
                
                # 解析算法权重配置
                for algo in algorithms:
                    if algo.get('enabled', False):
                        algo_name = algo.get('name', '')
                        weight = algo.get('weight', 0.0)
                        
                        # 映射配置文件中的算法名称到内部权重键
                        if algo_name == 'semantic_matching':
                            default_weights['semantic_similarity'] = weight
                        elif algo_name == 'skill_matching':
                            default_weights['skills_match'] = weight
                        elif algo_name == 'keyword_matching':
                            # keyword_matching 可以映射到 semantic_similarity 或单独处理
                            # 这里我们将其合并到 semantic_similarity 中
                            default_weights['semantic_similarity'] += weight * 0.5
                            default_weights['skills_match'] += weight * 0.5
                
                self.logger.info(f"从标准配置文件加载匹配权重: {default_weights}")
        
        # 也支持直接的 weights 配置（向后兼容）
        if config and 'weights' in config:
            default_weights.update(config['weights'])
            self.logger.info(f"使用直接权重配置: {default_weights}")
        
        # 确保权重总和为1.0
        total_weight = sum(default_weights.values())
        if total_weight > 0:
            normalized_weights = {k: v/total_weight for k, v in default_weights.items()}
            self.logger.info(f"标准化后的匹配权重: {normalized_weights}")
            return normalized_weights
        
        return default_weights
    
    async def find_matching_jobs(self,
                                resume_profile: GenericResumeProfile,
                                filters: Dict[str, Any] = None,
                                top_k: int = 20) -> ResumeMatchingResult:
        """为任意用户查找匹配的职位"""
        start_time = time.time()
        
        try:
            self.logger.info(f"🔍 开始为 {resume_profile.name} 查找匹配职位，目标数量: {top_k}")
            self.logger.info(f"📊 简历基本信息: 经验{resume_profile.total_experience_years}年, 技能数量{len(resume_profile.get_all_skills())}")
            
            # 1. 构建个性化查询
            query = self._build_personalized_query(resume_profile)
            self.logger.debug(f"🔤 构建查询: {query[:100]}...")
            
            # 2. 执行语义搜索
            search_k = min(self.default_search_k, top_k * 3)
            self.logger.info(f"🔍 执行语义搜索，搜索范围: {search_k}")
            search_results = await self._execute_semantic_search(
                query, filters, k=search_k
            )
            
            self.logger.info(f"📄 语义搜索返回 {len(search_results)} 个候选文档")
            
            # 3. 按职位ID分组文档
            jobs_by_id = self._group_results_by_job(search_results)
            self.logger.info(f"📋 分组后得到 {len(jobs_by_id)} 个候选职位")
            
            # 4. 计算匹配分数
            matching_jobs = []
            failed_matches = 0
            below_threshold = 0
            
            for job_id, job_docs in jobs_by_id.items():
                try:
                    match_result = await self._calculate_match_score(
                        resume_profile, job_docs, job_id
                    )
                    
                    if match_result:
                        if match_result.overall_score >= self.min_score_threshold:
                            matching_jobs.append(match_result)
                            self.logger.debug(f"✅ 职位 {job_id} 匹配成功，分数: {match_result.overall_score:.3f}")
                        else:
                            below_threshold += 1
                            self.logger.debug(f"⚠️ 职位 {job_id} 分数过低: {match_result.overall_score:.3f} < {self.min_score_threshold}")
                    else:
                        failed_matches += 1
                        
                except Exception as e:
                    failed_matches += 1
                    self.logger.warning(f"❌ 计算职位 {job_id} 匹配度失败: {str(e)}")
                    continue
            
            # 记录匹配统计
            self.logger.info(f"📊 匹配统计: 成功{len(matching_jobs)}, 低分{below_threshold}, 失败{failed_matches}")
            
            # 5. 排序和筛选结果
            matching_jobs.sort(key=lambda x: x.overall_score, reverse=True)
            top_matches = matching_jobs[:top_k]
            
            if top_matches:
                best_score = top_matches[0].overall_score
                worst_score = top_matches[-1].overall_score
                self.logger.info(f"🏆 最终结果分数范围: {worst_score:.3f} - {best_score:.3f}")
            
            # 6. 生成匹配摘要和洞察
            processing_time = time.time() - start_time
            summary = self._generate_matching_summary(top_matches, processing_time)
            insights = self._generate_career_insights(top_matches, resume_profile)
            
            # 7. 创建完整结果
            result = ResumeMatchingResult(
                matching_summary=summary,
                matches=top_matches,
                career_insights=insights,
                resume_profile=resume_profile,
                query_metadata={
                    'query': query,
                    'filters': filters,
                    'search_results_count': len(search_results),
                    'candidate_jobs_count': len(jobs_by_id),
                    'successful_matches': len(matching_jobs),
                    'failed_matches': failed_matches,
                    'below_threshold': below_threshold,
                    'processing_time': processing_time
                }
            )
            
            # 更新性能统计
            self._update_performance_stats(processing_time, len(top_matches))
            
            self.logger.info(f"✅ 匹配完成，返回 {len(top_matches)} 个职位，耗时 {processing_time:.2f}秒")
            
            # 记录匹配率警告
            if len(jobs_by_id) > 0:
                match_rate = len(matching_jobs) / len(jobs_by_id)
                if match_rate < 0.2:
                    self.logger.warning(f"⚠️ 匹配率过低: {match_rate:.1%} ({len(matching_jobs)}/{len(jobs_by_id)})")
                else:
                    self.logger.info(f"📈 匹配率: {match_rate:.1%} ({len(matching_jobs)}/{len(jobs_by_id)})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"💥 职位匹配失败: {str(e)}")
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
        """执行语义搜索 - 支持时间感知搜索"""
        try:
            # 检查是否启用时间感知搜索
            time_aware_config = self.config.get('time_aware_search', {})
            enable_time_aware = time_aware_config.get('enable_time_boost', True)
            search_strategy = time_aware_config.get('search_strategy', 'hybrid')
            
            if enable_time_aware and hasattr(self.vector_manager, 'time_aware_similarity_search'):
                # 使用时间感知搜索
                self.logger.info(f"🕒 使用时间感知搜索，策略: {search_strategy}")
                search_results = self.vector_manager.time_aware_similarity_search(
                    query=query,
                    k=k,
                    filters=filters,
                    strategy=search_strategy
                )
            else:
                # 使用传统搜索
                self.logger.debug("使用传统向量搜索")
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
        """按职位ID分组搜索结果，过滤已删除职位"""
        jobs_by_id = defaultdict(list)
        
        for doc, score in search_results:
            job_id = doc.metadata.get('job_id')
            if job_id:
                # 检查职位是否已被删除
                if self._is_job_available(job_id):
                    doc.metadata['search_score'] = score
                    jobs_by_id[job_id].append(doc)
                else:
                    self.logger.debug(f"跳过已删除职位: {job_id}")
        
        return dict(jobs_by_id)
    
    async def _calculate_match_score(self,
                                   resume_profile: GenericResumeProfile,
                                   job_docs: List[Document],
                                   job_id: str) -> Optional[JobMatchResult]:
        """计算匹配分数"""
        try:
            # 提取职位元数据
            job_metadata = self._extract_job_metadata(job_docs, job_id)
            job_title = job_metadata.get('job_title', 'Unknown Position')
            
            self.logger.debug(f"🔢 开始计算职位 {job_id} ({job_title}) 的匹配分数")
            
            # 计算各维度分数
            semantic_score = self._calculate_semantic_similarity(resume_profile, job_docs)
            skills_score = self._calculate_skills_match(resume_profile, job_docs, job_metadata)
            experience_score = self._calculate_experience_match(resume_profile, job_metadata)
            industry_score = self._calculate_industry_match(resume_profile, job_metadata)
            salary_score = self._calculate_salary_match(resume_profile, job_metadata)
            
            # 记录各维度分数
            self.logger.debug(f"📊 {job_id} 各维度分数: 语义{semantic_score:.3f}, 技能{skills_score:.3f}, "
                            f"经验{experience_score:.3f}, 行业{industry_score:.3f}, 薪资{salary_score:.3f}")
            
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
            
            self.logger.debug(f"🎯 {job_id} 加权总分: {overall_score:.3f} "
                            f"(权重: 语义{self.matching_weights['semantic_similarity']}, "
                            f"技能{self.matching_weights['skills_match']}, "
                            f"经验{self.matching_weights['experience_match']}, "
                            f"行业{self.matching_weights['industry_match']}, "
                            f"薪资{self.matching_weights['salary_match']})")
            
            # 生成匹配分析
            match_analysis = self._generate_match_analysis(
                resume_profile, job_docs, job_metadata, dimension_scores
            )
            
            # 创建匹配结果
            match_result = JobMatchResult(
                job_id=job_metadata.get('job_id', 'unknown'),
                job_title=job_title,
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
            self.logger.error(f"💥 计算职位 {job_id} 匹配度失败: {str(e)}")
            return None
    
    def _calculate_semantic_similarity(self,
                                     resume_profile: GenericResumeProfile,
                                     job_docs: List[Document]) -> float:
        """
        计算语义相似度 - 优化版本
        使用向量搜索分数替代TF-IDF，提供更准确的中文语义匹配
        """
        try:
            # 优先使用向量搜索分数
            vector_score = self._get_vector_similarity_score(job_docs)
            if vector_score > 0:
                self.logger.debug(f"使用向量搜索分数: {vector_score:.3f}")
                return vector_score
            
            # 回退策略：基于文档质量和类型的评分
            fallback_score = self._calculate_fallback_similarity(job_docs)
            self.logger.debug(f"使用回退策略分数: {fallback_score:.3f}")
            return fallback_score
            
        except Exception as e:
            self.logger.error(f"计算语义相似度失败: {str(e)}")
            return 0.0
    
    def _get_vector_similarity_score(self, job_docs: List[Document]) -> float:
        """获取向量搜索相似度分数"""
        try:
            search_scores = []
            for doc in job_docs:
                if 'search_score' in doc.metadata:
                    score = doc.metadata['search_score']
                    # 验证分数有效性
                    if isinstance(score, (int, float)) and 0 <= score <= 1:
                        search_scores.append(score)
            
            if not search_scores:
                return 0.0
            
            # 单个文档直接返回分数
            if len(search_scores) == 1:
                return search_scores[0]
            
            # 多个文档使用加权平均，高分获得更多权重
            weights = [score ** 1.2 for score in search_scores]
            total_weight = sum(weights)
            
            if total_weight > 0:
                weighted_avg = sum(s * w for s, w in zip(search_scores, weights)) / total_weight
                return min(1.0, max(0.0, weighted_avg))
            
            # 简单平均作为备选
            return sum(search_scores) / len(search_scores)
            
        except Exception as e:
            self.logger.error(f"获取向量相似度分数失败: {str(e)}")
            return 0.0
    
    def _calculate_fallback_similarity(self, job_docs: List[Document]) -> float:
        """回退相似度计算策略"""
        try:
            # 基于文档类型和内容长度的启发式评分
            type_scores = {
                'overview': 0.8,
                'skills': 0.85,
                'responsibility': 0.7,
                'requirement': 0.75,
                'basic_requirements': 0.6,
                'company_info': 0.4
            }
            
            total_weight = 0
            weighted_score = 0
            
            for doc in job_docs:
                doc_type = doc.metadata.get('type', 'unknown')
                base_score = type_scores.get(doc_type, 0.5)
                
                # 根据内容长度调整分数
                content_length = len(doc.page_content) if doc.page_content else 0
                if content_length > 500:
                    length_bonus = 0.1
                elif content_length > 200:
                    length_bonus = 0.05
                else:
                    length_bonus = 0.0
                
                final_score = min(1.0, base_score + length_bonus)
                weight = 1.0
                
                total_weight += weight
                weighted_score += final_score * weight
            
            if total_weight > 0:
                return weighted_score / total_weight
            
            return 0.5  # 默认中等分数
            
        except Exception as e:
            self.logger.error(f"回退相似度计算失败: {str(e)}")
            return 0.5
    
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
        """计算薪资匹配度 - 优化版本，更宽松的匹配条件"""
        try:
            job_salary_range = job_metadata.get('salary_range')
            
            # 如果任一方没有薪资信息，给予中等分数
            if not job_salary_range or not resume_profile.expected_salary_range:
                self.logger.debug("薪资信息缺失，返回默认分数 0.8")
                return 0.8
            
            resume_min = resume_profile.expected_salary_range.get('min', 0)
            resume_max = resume_profile.expected_salary_range.get('max', 0)
            
            if resume_min == 0 and resume_max == 0:
                self.logger.debug("简历期望薪资为0，返回默认分数 0.8")
                return 0.8
            
            job_min = job_salary_range.get('min', 0)
            job_max = job_salary_range.get('max', float('inf'))
            
            self.logger.debug(f"薪资匹配计算: 简历期望 {resume_min}-{resume_max}, 职位提供 {job_min}-{job_max}")
            
            # 1. 检查是否有重叠
            overlap_min = max(resume_min, job_min)
            overlap_max = min(resume_max, job_max)
            
            if overlap_max >= overlap_min:
                # 有重叠，计算重叠度
                overlap_size = overlap_max - overlap_min
                resume_range_size = resume_max - resume_min
                job_range_size = job_max - job_min if job_max != float('inf') else resume_range_size
                
                if resume_range_size > 0 and job_range_size > 0:
                    overlap_ratio = overlap_size / min(resume_range_size, job_range_size)
                    score = min(1.0, overlap_ratio)
                    self.logger.debug(f"薪资有重叠，重叠度: {overlap_ratio:.3f}, 分数: {score:.3f}")
                    return score
            
            # 2. 没有重叠，但检查是否在合理范围内
            resume_mid = (resume_min + resume_max) / 2
            job_mid = (job_min + job_max) / 2 if job_max != float('inf') else job_min * 1.5
            
            # 计算薪资差距比例
            if job_mid > 0:
                gap_ratio = abs(resume_mid - job_mid) / job_mid
                
                # 根据差距给分
                if gap_ratio <= 0.2:  # 差距在20%以内
                    score = 0.8
                elif gap_ratio <= 0.4:  # 差距在40%以内
                    score = 0.6
                elif gap_ratio <= 0.6:  # 差距在60%以内
                    score = 0.4
                else:  # 差距超过60%
                    score = 0.2
                
                self.logger.debug(f"薪资无重叠，差距比例: {gap_ratio:.3f}, 分数: {score:.3f}")
                return score
            
            # 3. 特殊情况：如果简历期望明显低于职位提供，给高分
            if resume_max <= job_min * 1.2:  # 简历最高期望不超过职位最低的120%
                self.logger.debug("简历期望薪资合理偏低，给予高分 0.9")
                return 0.9
            
            # 4. 默认情况
            self.logger.debug("薪资匹配默认情况，返回 0.5")
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
        
        # 扩展的技能关键词 - 包含占彬简历的核心技能
        common_skills = [
            # 编程语言
            'python', 'java', 'javascript', 'typescript', 'c#', 'c++', 'golang', 'go',
            
            # Web前端技术
            'react', 'vue', 'angular', 'node.js', 'html', 'css', 'bootstrap',
            'jquery', 'webpack', 'npm', 'yarn', 'sass', 'less',
            
            # 后端框架
            'spring', 'django', 'flask', '.net', 'asp.net',
            
            # 数据库技术
            'mysql', 'postgresql', 'mongodb', 'redis', 'azure sql', 'cosmos db',
            'sql server', 'oracle', 'sqlite', 'cassandra', 'elasticsearch',
            
            # 云平台技术 (重点扩展Azure)
            'azure', 'microsoft azure', 'aws', 'gcp', 'google cloud',
            'azure data factory', 'azure functions', 'azure storage',
            'azure data lake storage', 'azure data lake storage gen2',
            'azure synapse', 'azure databricks', 'azure devops',
            'azure app service', 'azure kubernetes service', 'aks',
            
            # 大数据和数据工程技能 (占彬的核心领域)
            'databricks', 'delta lake', 'spark', 'pyspark', 'spark sql',
            'hadoop', 'hdfs', 'hive', 'kafka', 'airflow', 'nifi',
            'ssis', 'informatica', 'talend', 'pentaho',
            'etl', 'elt', 'data pipeline', 'data integration',
            'oltp', 'olap', 'data warehouse', 'data mart',
            'data lineage', 'data governance', 'data quality',
            'metadata management', 'data catalog',
            
            # AI/ML技能 (占彬的专长)
            'machine learning', 'deep learning', 'ai', 'artificial intelligence',
            'tensorflow', 'pytorch', 'scikit-learn', 'keras', 'xgboost',
            'computer vision', 'opencv', 'yolo', 'resnet', 'cnn', 'rnn', 'lstm',
            'attention mechanism', 'transformer', 'bert', 'gpt',
            'numpy', 'pandas', 'matplotlib', 'seaborn', 'plotly',
            'jupyter', 'anaconda', 'mlflow', 'kubeflow',
            'langchain', 'llamaindex', 'openai api', 'azure openai',
            'rag', 'retrieval augmented generation', 'prompt engineering',
            
            # 数据科学和分析
            'data science', 'data analysis', 'data visualization',
            'tableau', 'power bi', 'qlik', 'looker', 'grafana',
            'r', 'stata', 'spss', 'sas',
            
            # DevOps和基础设施
            'docker', 'kubernetes', 'jenkins', 'gitlab ci', 'github actions',
            'terraform', 'ansible', 'chef', 'puppet',
            'linux', 'ubuntu', 'centos', 'windows server',
            'nginx', 'apache', 'iis',
            
            # 项目管理和方法论
            'agile', 'scrum', 'kanban', 'waterfall', 'devops',
            'ci/cd', 'continuous integration', 'continuous deployment',
            'git', 'github', 'gitlab', 'bitbucket', 'svn',
            
            # 架构和设计模式
            'microservices', 'api', 'rest', 'graphql', 'soap',
            'event driven', 'message queue', 'rabbitmq', 'activemq',
            'design patterns', 'solid principles', 'clean architecture',
            
            # 制药和医疗行业特定技能
            'pharmaceutical', 'clinical data', 'regulatory compliance',
            'gxp', 'fda', 'ich', 'clinical trials', 'pharmacovigilance',
            
            # 中文技能关键词 (占彬简历中的中文技能)
            '数据工程', '数据架构', '数据治理', '数据质量', '数据血缘',
            '元数据管理', '机器学习', '深度学习', '计算机视觉',
            '人工智能', '数据科学', '大数据', '云计算',
            '敏捷开发', '项目管理', '技术管理', '架构设计',
            '湖仓一体', '实时处理', '批处理', '流处理'
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
        """判断技能是否匹配 - 增强版本支持中英文映射和智能匹配"""
        job_skill_lower = job_skill.lower().strip()
        
        # 1. 精确匹配
        if job_skill_lower in resume_skills:
            return True
        
        # 2. 中英文技能映射
        skill_mappings = self._get_skill_mappings()
        
        # 检查job_skill是否有对应的中文或英文映射
        for cn_skill, en_skills in skill_mappings.items():
            if job_skill_lower in [s.lower() for s in en_skills]:
                # job_skill是英文，检查简历中是否有对应中文
                if cn_skill in [s.lower() for s in resume_skills]:
                    return True
            elif job_skill_lower == cn_skill.lower():
                # job_skill是中文，检查简历中是否有对应英文
                for en_skill in en_skills:
                    if en_skill.lower() in resume_skills:
                        return True
        
        # 3. 技能变体匹配
        skill_variants = self._get_skill_variants()
        for base_skill, variants in skill_variants.items():
            if job_skill_lower == base_skill.lower() or job_skill_lower in [v.lower() for v in variants]:
                # 检查简历中是否有任何变体
                all_variants = [base_skill] + variants
                for variant in all_variants:
                    if variant.lower() in resume_skills:
                        return True
        
        # 4. 部分匹配 (更智能的匹配)
        for resume_skill in resume_skills:
            # 避免过短的匹配
            if len(job_skill_lower) >= 3 and len(resume_skill) >= 3:
                if job_skill_lower in resume_skill or resume_skill in job_skill_lower:
                    return True
                
                # 检查是否是复合技能的一部分
                if self._is_compound_skill_match(job_skill_lower, resume_skill):
                    return True
        
        return False
    
    def _get_skill_mappings(self) -> Dict[str, List[str]]:
        """获取中英文技能映射"""
        return {
            # 占彬简历中的核心技能映射
            '数据工程师': ['data engineer', 'data engineering', 'data architect', 'data architecture'],
            'ai/ml架构师': ['ai architect', 'ml architect', 'ai/ml architect', 'machine learning architect', 'ai', 'artificial intelligence'],
            '技术管理者': ['technical lead', 'tech lead', 'technical manager', 'engineering manager'],
            '数据平台架构师': ['data platform architect', 'data architect', 'platform architect', 'data architecture'],
            '端到端ai系统开发': ['end-to-end ai development', 'ai system development', 'ai pipeline', 'ai'],
            '企业分布式系统开发': ['distributed systems', 'enterprise systems', 'distributed computing'],
            'web互联网架构构建': ['web architecture', 'internet architecture', 'web system design'],
            '技术领导': ['technical leadership', 'tech leadership', 'engineering leadership'],
            '敏捷实践': ['agile practices', 'agile methodology', 'agile development', 'agile'],
            '企业级系统架构设计': ['enterprise architecture', 'system architecture', 'solution architecture', 'data architecture'],
            '项目风险管理': ['project risk management', 'risk management', 'project management'],
            '技术债务控制': ['technical debt management', 'code quality', 'technical debt'],
            
            # 数据工程技能
            '数据血缘追踪': ['data lineage', 'data lineage tracking', 'lineage management'],
            '元数据管理': ['metadata management', 'data catalog', 'metadata governance'],
            '数据治理': ['data governance', 'data management', 'data stewardship'],
            '数据质量校验': ['data quality', 'data validation', 'data quality assurance'],
            'ssis': ['ssis', 'sql server integration services', 'etl', 'data integration'],
            'informatica': ['informatica', 'etl', 'data integration'],
            'databricks': ['databricks', 'delta lake', 'lakehouse'],
            
            # AI/ML技能
            '机器学习': ['machine learning', 'ml', 'ai'],
            '深度学习': ['deep learning', 'dl', 'ai'],
            '计算机视觉': ['computer vision', 'cv'],
            '人体关键点检测': ['human pose estimation', 'keypoint detection', 'pose detection'],
            '注意力机制': ['attention mechanism', 'attention', 'self-attention'],
            '推理加速': ['inference acceleration', 'model optimization', 'inference optimization'],
            '内存优化': ['memory optimization', 'memory management'],
            '批量预测': ['batch prediction', 'batch inference'],
            '模型部署': ['model deployment', 'model serving', 'ml deployment'],
            'rag架构': ['rag', 'retrieval augmented generation', 'rag architecture'],
            '提示工程': ['prompt engineering', 'prompt design', 'prompt optimization'],
            
            # 管理技能
            '技术团队管理': ['technical team management', 'engineering team lead', 'team leadership'],
            '敏捷开发实践者': ['agile practitioner', 'agile coach', 'scrum practitioner', 'agile'],
            '架构设计': ['architecture design', 'system design', 'solution design', 'data architecture'],
            '风险控制': ['risk management', 'risk control', 'risk mitigation'],
            '自动化部署': ['automated deployment', 'deployment automation', 'ci/cd'],
            '版本管理': ['version control', 'source control', 'git management'],
            '团队建设': ['team building', 'team development', 'team management'],
            '项目管理': ['project management', 'program management'],
            'scrum方法论': ['scrum', 'agile', 'scrum master'],
            
            # 云平台和数据平台
            '湖仓一体': ['lakehouse', 'data lakehouse', 'lakehouse architecture', 'delta lake'],
            '实时处理': ['real-time processing', 'stream processing', 'real-time analytics'],
            '批处理': ['batch processing', 'batch analytics'],
            '流处理': ['stream processing', 'streaming', 'real-time streaming'],
            
            # 制药行业经验
            'zoetis': ['pharmaceutical', 'pharma', 'healthcare'],
            'pwc': ['consulting', 'pharmaceutical']
        }
    
    def _get_skill_variants(self) -> Dict[str, List[str]]:
        """获取技能变体映射"""
        return {
            'azure': ['microsoft azure', 'azure cloud', 'azure platform'],
            'databricks': ['databricks platform', 'databricks workspace', 'databricks runtime'],
            'azure data factory': ['adf', 'data factory', 'azure adf'],
            'azure functions': ['azure function', 'function app', 'serverless functions'],
            'machine learning': ['ml', 'ai/ml', 'artificial intelligence'],
            'deep learning': ['dl', 'neural networks', 'deep neural networks'],
            'computer vision': ['cv', 'image processing', 'visual recognition'],
            'data engineering': ['data engineer', 'big data engineering'],
            'data architecture': ['data architect', 'data platform architecture'],
            'etl': ['extract transform load', 'data integration', 'data pipeline'],
            'oltp': ['online transaction processing', 'transactional database'],
            'olap': ['online analytical processing', 'analytical database'],
            'ci/cd': ['continuous integration', 'continuous deployment', 'devops pipeline'],
            'scrum master': ['scrum', 'agile coach', 'agile facilitator'],
            'pytorch': ['torch', 'pytorch framework'],
            'tensorflow': ['tf', 'tensorflow framework'],
            'kubernetes': ['k8s', 'container orchestration'],
            'docker': ['containerization', 'container technology'],
            'rest api': ['rest', 'restful api', 'web api'],
            'microservices': ['micro services', 'service oriented architecture', 'soa']
        }
    
    def _is_compound_skill_match(self, job_skill: str, resume_skill: str) -> bool:
        """检查复合技能匹配"""
        # 处理复合技能，如 "azure data factory" 匹配 "data factory"
        job_words = set(job_skill.split())
        resume_words = set(resume_skill.split())
        
        # 如果有足够的词汇重叠，认为匹配
        if len(job_words) > 1 and len(resume_words) > 1:
            overlap = job_words.intersection(resume_words)
            # 至少有2个词匹配，且匹配率超过50%
            if len(overlap) >= 2 and len(overlap) / min(len(job_words), len(resume_words)) >= 0.5:
                return True
        
        return False
    
    def _calculate_skill_bonus(self, resume_skills: List[str], job_skills: List[str]) -> float:
        """计算技能加分 - 扩展占彬的高价值技能"""
        bonus = 0.0
        
        # 扩展的高价值技能加分 - 重点包含占彬的核心技能
        high_value_skills = [
            # AI/ML核心技能
            'ai', 'machine learning', 'deep learning', 'computer vision',
            'pytorch', 'tensorflow', 'rag', 'langchain', 'llamaindex',
            'prompt engineering', 'attention mechanism',
            
            # 数据工程和架构 (占彬的核心优势)
            'databricks', 'delta lake', 'data architecture', 'data governance',
            'data lineage', 'metadata management', 'lakehouse',
            'azure data factory', 'pyspark', 'etl', 'data pipeline',
            
            # 云平台技能
            'azure', 'aws', 'kubernetes', 'azure databricks',
            'azure functions', 'azure synapse', 'azure data lake storage',
            
            # 架构和管理技能
            'solution architecture', 'enterprise architecture', 'scrum master',
            'technical leadership', 'data platform architect',
            
            # 中文高价值技能
            '数据架构', '数据治理', '湖仓一体', 'ai/ml架构师',
            '数据平台架构师', '技术管理者', '数据工程师'
        ]
        
        for skill in resume_skills:
            skill_lower = skill.lower()
            if skill_lower in high_value_skills and skill_lower not in job_skills:
                # 根据技能重要性给不同加分
                if skill_lower in ['databricks', 'data architecture', '数据架构', 'azure data factory']:
                    bonus += 0.08  # 占彬的最核心技能，更高加分
                elif skill_lower in ['ai', 'machine learning', 'azure', 'rag']:
                    bonus += 0.06  # 重要技能
                else:
                    bonus += 0.04  # 一般高价值技能
        
        return min(0.25, bonus)  # 提高最大加分到25%
    
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
    
    def _is_job_available(self, job_id: str) -> bool:
        """检查职位是否可用（未删除）"""
        try:
            from ..database.operations import DatabaseManager
            
            # 从配置中获取数据库路径
            db_path = self.config.get('database_path', 'data/jobs.db')
            db_manager = DatabaseManager(db_path)
            
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 1 FROM jobs
                    WHERE job_id = ? AND (is_deleted = 0 OR is_deleted IS NULL)
                """, (job_id,))
                return cursor.fetchone() is not None
        except Exception as e:
            self.logger.warning(f"检查职位可用性失败: {e}")
            return True  # 出错时默认可用，避免误删