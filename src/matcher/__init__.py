#!/usr/bin/env python3
"""
简历职位匹配模块
提供智能简历职位匹配功能
"""

from .generic_resume_models import (
    GenericResumeProfile,
    JobMatchResult,
    MatchAnalysis,
    ResumeMatchingResult,
    MatchingSummary,
    CareerInsights,
    WorkExperience,
    MatchLevel,
    RecommendationPriority,
    get_match_level_from_score,
    get_recommendation_priority_from_score,
    DEFAULT_MATCHING_WEIGHTS,
    create_default_skill_weights,
    MATCH_THRESHOLDS
)

from .generic_resume_vectorizer import GenericResumeVectorizer
from .multi_dimensional_scorer import MultiDimensionalScorer
from .generic_resume_matcher import GenericResumeJobMatcher

__all__ = [
    # 数据模型
    'GenericResumeProfile',
    'JobMatchResult',
    'MatchAnalysis',
    'ResumeMatchingResult',
    'MatchingSummary',
    'CareerInsights',
    'WorkExperience',
    'MatchLevel',
    'RecommendationPriority',
    
    # 核心组件
    'GenericResumeVectorizer',
    'MultiDimensionalScorer',
    'GenericResumeJobMatcher',
    
    # 工具函数
    'get_match_level_from_score',
    'get_recommendation_priority_from_score',
    
    # 配置常量
    'DEFAULT_MATCHING_WEIGHTS',
    'create_default_skill_weights',
    'MATCH_THRESHOLDS'
]