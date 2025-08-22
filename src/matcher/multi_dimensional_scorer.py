#!/usr/bin/env python3
"""
多维度评分系统
基于语义相似度、技能匹配、经验匹配、行业匹配、薪资匹配等多个维度进行评分
"""

import re
import math
from typing import List, Dict, Any, Optional, Tuple
from langchain.schema import Document
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from ..utils.logger import get_logger
from .generic_resume_models import (
    GenericResumeProfile, JobMatchResult, MatchAnalysis,
    create_default_skill_weights, DEFAULT_MATCHING_WEIGHTS,
    get_match_level_from_score, get_recommendation_priority_from_score
)


class MultiDimensionalScorer:
    """多维度评分系统"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.logger = get_logger(__name__)
        
        # 评分权重配置
        self.weights = DEFAULT_MATCHING_WEIGHTS.copy()
        if config and 'weights' in config:
            self.weights.update(config['weights'])
        
        # 技能权重配置
        self.skill_weights = create_default_skill_weights()
        if config:
            self.skill_weights.update_from_config(config)
        
        # 技能同义词映射
        self.skill_synonyms = {
            'machine learning': ['机器学习', 'ML', 'ml'],
            'artificial intelligence': ['人工智能', 'AI', 'ai'],
            'deep learning': ['深度学习', 'DL', 'dl'],
            'python': ['Python', 'python'],
            'azure': ['Azure', 'azure', 'Microsoft Azure'],
            'aws': ['AWS', 'aws', 'Amazon Web Services'],
            'databricks': ['Databricks', 'databricks'],
            'tensorflow': ['TensorFlow', 'tensorflow', 'tf'],
            'pytorch': ['PyTorch', 'pytorch', 'torch'],
            'langchain': ['LangChain', 'langchain'],
            'rag': ['RAG', 'rag', 'Retrieval Augmented Generation'],
            'sql': ['SQL', 'sql', 'MySQL', 'PostgreSQL', 'SQL Server'],
            'docker': ['Docker', 'docker', '容器化'],
            'kubernetes': ['Kubernetes', 'kubernetes', 'k8s', 'K8s'],
            'scrum': ['Scrum', 'scrum', '敏捷开发', 'Agile'],
            'etl': ['ETL', 'etl', 'Extract Transform Load'],
            'data warehouse': ['数据仓库', 'data warehouse', 'DW'],
            'big data': ['大数据', 'big data', 'BigData'],
            'spark': ['Spark', 'spark', 'Apache Spark'],
            'hadoop': ['Hadoop', 'hadoop', 'Apache Hadoop']
        }
        
        # 初始化TF-IDF向量化器
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
    
    def calculate_comprehensive_score(self,
                                    resume_profile: GenericResumeProfile,
                                    job_documents: List[Document],
                                    job_metadata: Dict[str, Any]) -> JobMatchResult:
        """计算综合匹配分数"""
        try:
            # 1. 语义相似度评分
            semantic_score = self._calculate_semantic_similarity(resume_profile, job_documents)
            
            # 2. 技能匹配评分
            skills_score = self._calculate_skills_match(resume_profile, job_documents, job_metadata)
            
            # 3. 经验匹配评分
            experience_score = self._calculate_experience_match(resume_profile, job_metadata)
            
            # 4. 行业匹配评分
            industry_score = self._calculate_industry_match(resume_profile, job_metadata)
            
            # 5. 薪资匹配评分
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
                semantic_score * self.weights['semantic_similarity'] +
                skills_score * self.weights['skills_match'] +
                experience_score * self.weights['experience_match'] +
                industry_score * self.weights['industry_match'] +
                salary_score * self.weights['salary_match']
            )
            
            # 生成匹配分析
            match_analysis = self._generate_match_analysis(
                resume_profile, job_documents, job_metadata, dimension_scores
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
                match_level=get_match_level_from_score(overall_score),
                match_analysis=match_analysis,
                recommendation_priority=get_recommendation_priority_from_score(overall_score),
                confidence_level=self._calculate_confidence_level(dimension_scores)
            )
            
            return match_result
            
        except Exception as e:
            self.logger.error(f"计算综合评分失败: {str(e)}")
            raise
    
    def _calculate_semantic_similarity(self,
                                     resume_profile: GenericResumeProfile,
                                     job_documents: List[Document]) -> float:
        """计算语义相似度"""
        try:
            # 构建简历文本
            resume_text = self._build_resume_text(resume_profile)
            
            # 构建职位文本
            job_text = " ".join([doc.page_content for doc in job_documents])
            
            # 使用TF-IDF计算相似度
            texts = [resume_text, job_text]
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            # 返回相似度分数
            similarity_score = similarity_matrix[0, 1]
            
            # 归一化到0-1范围
            return max(0.0, min(1.0, similarity_score))
            
        except Exception as e:
            self.logger.error(f"计算语义相似度失败: {str(e)}")
            return 0.0
    
    def _calculate_skills_match(self,
                              resume_profile: GenericResumeProfile,
                              job_documents: List[Document],
                              job_metadata: Dict[str, Any]) -> float:
        """计算技能匹配度"""
        try:
            # 获取简历技能
            resume_skills = self._extract_resume_skills(resume_profile)
            
            # 获取职位技能要求
            job_skills = self._extract_job_skills(job_documents, job_metadata)
            
            if not job_skills:
                return 0.5  # 如果没有明确的技能要求，给中等分数
            
            # 计算技能匹配
            matched_skills = []
            total_job_skill_weight = 0
            matched_skill_weight = 0
            
            for job_skill in job_skills:
                skill_weight = self.skill_weights.get_skill_weight(job_skill)
                total_job_skill_weight += skill_weight
                
                if self._is_skill_matched(job_skill, resume_skills):
                    matched_skills.append(job_skill)
                    matched_skill_weight += skill_weight
            
            # 计算加权匹配率
            if total_job_skill_weight > 0:
                weighted_match_rate = matched_skill_weight / total_job_skill_weight
            else:
                weighted_match_rate = 0.0
            
            # 考虑简历中的高价值技能加分
            bonus_score = self._calculate_skill_bonus(resume_skills, job_skills)
            
            final_score = min(1.0, weighted_match_rate + bonus_score)
            
            self.logger.debug(f"技能匹配: {len(matched_skills)}/{len(job_skills)}, 加权分数: {final_score:.3f}")
            
            return final_score
            
        except Exception as e:
            self.logger.error(f"计算技能匹配度失败: {str(e)}")
            return 0.0
    
    def _calculate_experience_match(self,
                                  resume_profile: GenericResumeProfile,
                                  job_metadata: Dict[str, Any]) -> float:
        """计算经验匹配度"""
        try:
            # 获取职位经验要求
            required_years = self._extract_required_experience(job_metadata)
            
            # 获取简历经验年限
            resume_years = resume_profile.total_experience_years
            
            if required_years is None:
                return 0.9  # 没有明确要求时给高分
            
            if resume_years >= required_years:
                # 经验超出要求，给高分，但避免过度匹配惩罚
                if resume_years <= required_years * 2:
                    return 1.0  # 完美匹配
                else:
                    # 经验过多可能被认为overqualified，稍微降分
                    return 0.95
            else:
                # 经验不足，按比例计算
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
                return 0.7  # 没有行业信息时给中等分数
            
            # 检查直接行业匹配
            for resume_industry, weight in resume_profile.industry_experience.items():
                if resume_industry.lower() in job_industry or job_industry in resume_industry.lower():
                    return weight
            
            # 检查相关行业匹配
            industry_similarity = self._calculate_industry_similarity(
                job_industry, list(resume_profile.industry_experience.keys())
            )
            
            return industry_similarity
            
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
                return 0.8  # 没有薪资信息时给较高分数
            
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
                # 有重叠
                overlap_size = overlap_max - overlap_min
                resume_range_size = resume_max - resume_min
                job_range_size = job_max - job_min if job_max != float('inf') else resume_range_size
                
                # 计算重叠比例
                overlap_ratio = overlap_size / min(resume_range_size, job_range_size)
                return min(1.0, overlap_ratio)
            else:
                # 没有重叠，计算距离惩罚
                if resume_min > job_max:
                    # 期望薪资过高
                    gap = resume_min - job_max
                    penalty = gap / resume_min
                    return max(0.0, 1.0 - penalty)
                else:
                    # 期望薪资过低（不太可能）
                    return 0.9
            
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
    
    def _extract_resume_skills(self, resume_profile: GenericResumeProfile) -> List[str]:
        """提取简历技能"""
        all_skills = resume_profile.get_all_skills()
        
        # 去重并转换为小写
        return list(set([skill.lower() for skill in all_skills]))
    
    def _extract_job_skills(self, job_documents: List[Document], job_metadata: Dict[str, Any]) -> List[str]:
        """提取职位技能要求"""
        skills = []
        
        # 从元数据中提取
        if 'skills' in job_metadata:
            skills.extend(job_metadata['skills'])
        
        # 从文档内容中提取
        job_text = " ".join([doc.page_content for doc in job_documents])
        
        # 使用正则表达式匹配常见技能
        skill_patterns = [
            r'\b(python|java|javascript|c\#|c\+\+|sql|r|scala|go|rust)\b',
            r'\b(azure|aws|gcp|docker|kubernetes|spark|hadoop|kafka)\b',
            r'\b(tensorflow|pytorch|scikit-learn|pandas|numpy)\b',
            r'\b(machine learning|deep learning|ai|artificial intelligence)\b',
            r'\b(data science|data engineering|data analysis|big data)\b',
            r'\b(scrum|agile|devops|ci/cd|git|jenkins)\b'
        ]
        
        for pattern in skill_patterns:
            matches = re.findall(pattern, job_text.lower())
            skills.extend(matches)
        
        # 去重
        return list(set([skill.lower() for skill in skills if skill]))
    
    
    def _is_skill_matched(self, job_skill: str, resume_skills: List[str]) -> bool:
        """判断技能是否匹配"""
        job_skill_lower = job_skill.lower()
        
        # 直接匹配
        if job_skill_lower in resume_skills:
            return True
        
        # 同义词匹配
        for canonical_skill, synonyms in self.skill_synonyms.items():
            job_synonyms = [s.lower() for s in synonyms]
            resume_synonyms = [s.lower() for s in synonyms]
            
            if job_skill_lower in job_synonyms:
                for resume_skill in resume_skills:
                    if resume_skill in resume_synonyms:
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
        high_value_skills = ['rag', 'langchain', 'ai/ml', 'azure', 'databricks']
        
        for skill in resume_skills:
            if skill in high_value_skills and skill not in job_skills:
                bonus += 0.05  # 每个高价值技能加5%
        
        return min(0.2, bonus)  # 最多加20%
    
    def _extract_required_experience(self, job_metadata: Dict[str, Any]) -> Optional[int]:
        """提取职位经验要求"""
        # 从元数据中提取
        if 'required_experience_years' in job_metadata:
            return job_metadata['required_experience_years']
        
        # 从职位描述中提取
        job_description = job_metadata.get('description', '')
        
        # 使用正则表达式匹配经验要求
        patterns = [
            r'(\d+)\+?\s*years?\s*of?\s*experience',
            r'(\d+)\+?\s*年.*经验',
            r'experience.*(\d+)\+?\s*years?',
            r'minimum.*(\d+)\s*years?'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, job_description.lower())
            if matches:
                return int(matches[0])
        
        return None
    
    def _calculate_industry_similarity(self, job_industry: str, resume_industries: List[str]) -> float:
        """计算行业相似度"""
        # 行业相关性映射
        industry_relations = {
            '科技': ['互联网', 'ai', '软件', '技术'],
            '制药': ['医疗', '生物', '健康'],
            '金融': ['银行', '保险', '投资'],
            '咨询': ['管理', '战略', '顾问']
        }
        
        max_similarity = 0.0
        
        for resume_industry in resume_industries:
            # 直接匹配
            if job_industry.lower() in resume_industry.lower() or resume_industry.lower() in job_industry.lower():
                max_similarity = max(max_similarity, 0.8)
            
            # 相关性匹配
            for category, related_terms in industry_relations.items():
                if any(term in job_industry.lower() for term in related_terms):
                    if any(term in resume_industry.lower() for term in related_terms):
                        max_similarity = max(max_similarity, 0.6)
        
        return max_similarity
    
    def _calculate_confidence_level(self, dimension_scores: Dict[str, float]) -> float:
        """计算置信度"""
        # 基于各维度分数的方差计算置信度
        scores = list(dimension_scores.values())
        mean_score = np.mean(scores)
        variance = np.var(scores)
        
        # 方差越小，置信度越高
        confidence = max(0.5, 1.0 - variance)
        
        return confidence
    
    def _generate_match_analysis(self,
                               resume_profile: GenericResumeProfile,
                               job_documents: List[Document],
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
        resume_skills = self._extract_resume_skills(resume_profile)
        job_skills = self._extract_job_skills(job_documents, job_metadata)
        
        for job_skill in job_skills:
            if self._is_skill_matched(job_skill, resume_skills):
                analysis.matched_skills.append(job_skill)
            else:
                analysis.missing_skills.append(job_skill)
        
        # 计算各项指标
        analysis.skill_gap_score = 1.0 - dimension_scores['skills_match']
        analysis.experience_alignment = dimension_scores['experience_match']
        analysis.industry_fit = dimension_scores['industry_match']
        
        return analysis