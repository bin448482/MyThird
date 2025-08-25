#!/usr/bin/env python3
"""
通用简历数据模型
支持任意用户和动态技能配置的灵活简历系统
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from enum import Enum
import json


class MatchLevel(Enum):
    """匹配等级枚举"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class RecommendationPriority(Enum):
    """推荐优先级枚举"""
    HIGH = "高优先级"
    MEDIUM = "中优先级"
    LOW = "低优先级"
    NOT_RECOMMENDED = "不推荐"


@dataclass
class WorkExperience:
    """工作经验数据模型"""
    company: str
    position: str
    start_date: str
    end_date: Optional[str]
    duration_years: float
    responsibilities: List[str] = field(default_factory=list)
    achievements: List[str] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)
    industry: str = ""


@dataclass
class Education:
    """教育背景数据模型"""
    degree: str
    major: str
    university: str
    graduation_year: str
    gpa: Optional[float] = None
    honors: List[str] = field(default_factory=list)


@dataclass
class Project:
    """项目经验数据模型"""
    name: str
    description: str
    technologies: List[str]
    duration: str
    achievements: List[str] = field(default_factory=list)
    role: str = ""
    url: Optional[str] = None


@dataclass
class SkillCategory:
    """技能分类数据模型"""
    category_name: str
    skills: List[str]
    proficiency_level: str = "intermediate"  # beginner, intermediate, advanced, expert
    years_experience: Optional[int] = None


@dataclass
class GenericResumeProfile:
    """通用简历数据模型 - 支持任意用户"""
    
    # 基本信息
    name: str
    phone: str = ""
    email: str = ""
    location: str = ""
    
    # 职业信息
    total_experience_years: int = 0
    current_position: str = ""
    current_company: str = ""
    
    # 技能信息 - 使用灵活的分类系统
    skill_categories: List[SkillCategory] = field(default_factory=list)
    
    # 工作经验
    work_history: List[WorkExperience] = field(default_factory=list)
    
    # 教育背景
    education: List[Education] = field(default_factory=list)
    
    # 项目经验
    projects: List[Project] = field(default_factory=list)
    
    # 认证
    certifications: List[str] = field(default_factory=list)
    
    # 语言能力
    languages: List[Dict[str, str]] = field(default_factory=list)
    
    # 行业经验权重 - 动态配置
    industry_experience: Dict[str, float] = field(default_factory=dict)
    
    # 职业目标
    preferred_positions: List[str] = field(default_factory=list)
    expected_salary_range: Dict[str, int] = field(default_factory=lambda: {"min": 0, "max": 0})
    career_objectives: List[str] = field(default_factory=list)
    
    # 个人特质和软技能
    soft_skills: List[str] = field(default_factory=list)
    personality_traits: List[str] = field(default_factory=list)
    
    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "1.0"
    profile_type: str = "generic"  # 用于区分不同类型的简历
    
    def get_all_skills(self) -> List[str]:
        """获取所有技能列表"""
        all_skills = []
        for category in self.skill_categories:
            all_skills.extend(category.skills)
        return all_skills
    
    def get_skills_by_category(self, category_name: str) -> List[str]:
        """根据分类获取技能"""
        for category in self.skill_categories:
            if category.category_name.lower() == category_name.lower():
                return category.skills
        return []
    
    def add_skill_category(self, category_name: str, skills: List[str], 
                          proficiency_level: str = "intermediate"):
        """添加技能分类"""
        category = SkillCategory(
            category_name=category_name,
            skills=skills,
            proficiency_level=proficiency_level
        )
        self.skill_categories.append(category)
    
    def update_skill_category(self, category_name: str, skills: List[str]):
        """更新技能分类"""
        for category in self.skill_categories:
            if category.category_name.lower() == category_name.lower():
                category.skills = skills
                return True
        return False
    
    def add_work_experience(self, experience: WorkExperience):
        """添加工作经验"""
        self.work_history.append(experience)
        self.updated_at = datetime.now().isoformat()
    
    def get_experience_by_industry(self, industry: str) -> List[WorkExperience]:
        """根据行业获取工作经验"""
        return [exp for exp in self.work_history if exp.industry.lower() == industry.lower()]
    
    def calculate_industry_experience_years(self) -> Dict[str, float]:
        """计算各行业工作年限"""
        industry_years = {}
        for exp in self.work_history:
            if exp.industry:
                industry_years[exp.industry] = industry_years.get(exp.industry, 0) + exp.duration_years
        return industry_years
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'location': self.location,
            'total_experience_years': self.total_experience_years,
            'current_position': self.current_position,
            'current_company': self.current_company,
            'skill_categories': [
                {
                    'category_name': cat.category_name,
                    'skills': cat.skills,
                    'proficiency_level': cat.proficiency_level,
                    'years_experience': cat.years_experience
                }
                for cat in self.skill_categories
            ],
            'work_history': [
                {
                    'company': exp.company,
                    'position': exp.position,
                    'start_date': exp.start_date,
                    'end_date': exp.end_date,
                    'duration_years': exp.duration_years,
                    'responsibilities': exp.responsibilities,
                    'achievements': exp.achievements,
                    'technologies': exp.technologies,
                    'industry': exp.industry
                }
                for exp in self.work_history
            ],
            'education': [
                {
                    'degree': edu.degree,
                    'major': edu.major,
                    'university': edu.university,
                    'graduation_year': edu.graduation_year,
                    'gpa': edu.gpa,
                    'honors': edu.honors
                }
                for edu in self.education
            ],
            'projects': [
                {
                    'name': proj.name,
                    'description': proj.description,
                    'technologies': proj.technologies,
                    'duration': proj.duration,
                    'achievements': proj.achievements,
                    'role': proj.role,
                    'url': proj.url
                }
                for proj in self.projects
            ],
            'certifications': self.certifications,
            'languages': self.languages,
            'industry_experience': self.industry_experience,
            'preferred_positions': self.preferred_positions,
            'expected_salary_range': self.expected_salary_range,
            'career_objectives': self.career_objectives,
            'soft_skills': self.soft_skills,
            'personality_traits': self.personality_traits,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'version': self.version,
            'profile_type': self.profile_type
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GenericResumeProfile':
        """从字典创建简历对象"""
        profile = cls(
            name=data.get('name', ''),
            phone=data.get('phone', ''),
            email=data.get('email', ''),
            location=data.get('location', ''),
            total_experience_years=data.get('total_experience_years', 0),
            current_position=data.get('current_position', ''),
            current_company=data.get('current_company', ''),
            certifications=data.get('certifications', []),
            languages=data.get('languages', []),
            industry_experience=data.get('industry_experience', {}),
            preferred_positions=data.get('preferred_positions', []),
            expected_salary_range=data.get('expected_salary_range', {"min": 0, "max": 0}),
            career_objectives=data.get('career_objectives', []),
            soft_skills=data.get('soft_skills', []),
            personality_traits=data.get('personality_traits', []),
            created_at=data.get('created_at', datetime.now().isoformat()),
            updated_at=data.get('updated_at', datetime.now().isoformat()),
            version=data.get('version', '1.0'),
            profile_type=data.get('profile_type', 'generic')
        )
        
        # 处理技能分类
        for cat_data in data.get('skill_categories', []):
            category = SkillCategory(
                category_name=cat_data['category_name'],
                skills=cat_data['skills'],
                proficiency_level=cat_data.get('proficiency_level', 'intermediate'),
                years_experience=cat_data.get('years_experience')
            )
            profile.skill_categories.append(category)
        
        # 处理工作经验
        for exp_data in data.get('work_history', []):
            experience = WorkExperience(
                company=exp_data['company'],
                position=exp_data['position'],
                start_date=exp_data['start_date'],
                end_date=exp_data.get('end_date'),
                duration_years=exp_data['duration_years'],
                responsibilities=exp_data.get('responsibilities', []),
                achievements=exp_data.get('achievements', []),
                technologies=exp_data.get('technologies', []),
                industry=exp_data.get('industry', '')
            )
            profile.work_history.append(experience)
        
        # 处理教育背景
        for edu_data in data.get('education', []):
            education = Education(
                degree=edu_data['degree'],
                major=edu_data['major'],
                university=edu_data['university'],
                graduation_year=edu_data['graduation_year'],
                gpa=edu_data.get('gpa'),
                honors=edu_data.get('honors', [])
            )
            profile.education.append(education)
        
        # 处理项目经验
        for proj_data in data.get('projects', []):
            project = Project(
                name=proj_data['name'],
                description=proj_data['description'],
                technologies=proj_data['technologies'],
                duration=proj_data['duration'],
                achievements=proj_data.get('achievements', []),
                role=proj_data.get('role', ''),
                url=proj_data.get('url')
            )
            profile.projects.append(project)
        
        return profile


@dataclass
class DynamicSkillWeights:
    """动态技能权重配置"""
    base_weights: Dict[str, float] = field(default_factory=dict)
    category_multipliers: Dict[str, float] = field(default_factory=lambda: {
        'core_skills': 1.0,
        'programming_languages': 0.9,
        'frameworks': 0.8,
        'tools': 0.7,
        'soft_skills': 0.6
    })
    proficiency_multipliers: Dict[str, float] = field(default_factory=lambda: {
        'expert': 1.2,
        'advanced': 1.0,
        'intermediate': 0.8,
        'beginner': 0.6
    })
    
    def get_skill_weight(self, skill: str, category: str = 'core_skills', 
                        proficiency: str = 'intermediate') -> float:
        """获取技能权重"""
        base_weight = self.base_weights.get(skill.lower(), 1.0)
        category_mult = self.category_multipliers.get(category, 1.0)
        proficiency_mult = self.proficiency_multipliers.get(proficiency, 1.0)
        
        return base_weight * category_mult * proficiency_mult
    
    def add_skill_weight(self, skill: str, weight: float):
        """添加技能权重"""
        self.base_weights[skill.lower()] = weight
    
    def update_from_config(self, config: Dict[str, Any]):
        """从配置更新权重"""
        if 'skills_weights' in config:
            self.base_weights.update({k.lower(): v for k, v in config['skills_weights'].items()})
        if 'category_multipliers' in config:
            self.category_multipliers.update(config['category_multipliers'])
        if 'proficiency_multipliers' in config:
            self.proficiency_multipliers.update(config['proficiency_multipliers'])


def create_resume_from_legacy_zhanbin(zhanbin_data: Dict[str, Any]) -> GenericResumeProfile:
    """从旧的占彬简历数据创建通用简历"""
    profile = GenericResumeProfile(
        name=zhanbin_data.get('name', '占彬'),
        phone=zhanbin_data.get('phone', ''),
        email=zhanbin_data.get('email', ''),
        location=zhanbin_data.get('location', ''),
        total_experience_years=zhanbin_data.get('total_experience_years', 20),
        current_position=zhanbin_data.get('current_position', ''),
        current_company=zhanbin_data.get('current_company', ''),
        certifications=zhanbin_data.get('certifications', []),
        industry_experience=zhanbin_data.get('industry_experience', {}),
        preferred_positions=zhanbin_data.get('preferred_positions', []),
        expected_salary_range=zhanbin_data.get('expected_salary_range', {"min": 0, "max": 0}),
        career_objectives=zhanbin_data.get('career_objectives', []),
        profile_type='zhanbin_legacy'
    )
    
    # 转换技能分类
    skill_mappings = [
        ('core_skills', 'core_skills'),
        ('programming_languages', 'programming_languages'),
        ('cloud_platforms', 'cloud_platforms'),
        ('ai_ml_skills', 'ai_ml_skills'),
        ('data_engineering_skills', 'data_engineering_skills'),
        ('management_skills', 'management_skills')
    ]
    
    for category_name, data_key in skill_mappings:
        if data_key in zhanbin_data:
            profile.add_skill_category(
                category_name=category_name,
                skills=zhanbin_data[data_key],
                proficiency_level='advanced'
            )
    
    # 转换工作经验
    for exp_data in zhanbin_data.get('work_history', []):
        experience = WorkExperience(
            company=exp_data['company'],
            position=exp_data['position'],
            start_date=exp_data['start_date'],
            end_date=exp_data.get('end_date'),
            duration_years=exp_data['duration_years'],
            responsibilities=exp_data.get('responsibilities', []),
            achievements=exp_data.get('achievements', []),
            technologies=exp_data.get('technologies', []),
            industry=exp_data.get('industry', '')
        )
        profile.add_work_experience(experience)
    
    return profile


def create_default_skill_weights() -> DynamicSkillWeights:
    """创建默认技能权重配置"""
    weights = DynamicSkillWeights()
    
    # 扩展的技能权重配置 - 重点提升占彬的核心技能权重
    default_skills = {
        # 编程语言
        'python': 1.8,  # 占彬的核心技能，提升权重
        'java': 1.5,
        'javascript': 1.4,
        'typescript': 1.4,
        'c#': 1.6,  # 占彬有经验
        'go': 1.5,
        'golang': 1.5,
        
        # Web技术
        'react': 1.3,
        'vue': 1.3,
        'angular': 1.3,
        'node.js': 1.4,
        'spring': 1.3,
        'django': 1.3,
        'flask': 1.2,
        
        # 数据库技术
        'mysql': 1.4,
        'postgresql': 1.4,
        'mongodb': 1.2,
        'redis': 1.3,
        'azure sql': 1.6,  # 占彬的Azure专长
        'cosmos db': 1.6,  # 占彬的Azure专长
        'sql server': 1.5,
        
        # 云平台技术 (占彬的专长领域)
        'azure': 1.9,  # 占彬是Azure专家，最高权重
        'microsoft azure': 1.9,
        'azure data factory': 2.0,  # 占彬的核心技能
        'azure functions': 1.8,
        'azure storage': 1.7,
        'azure data lake storage': 1.9,
        'azure data lake storage gen2': 1.9,
        'azure databricks': 2.0,  # 占彬的核心技能
        'azure synapse': 1.8,
        'azure devops': 1.7,
        'azure app service': 1.6,
        'aws': 1.5,
        'gcp': 1.4,
        'google cloud': 1.4,
        
        # 大数据和数据工程 (占彬的核心领域)
        'databricks': 2.0,  # 占彬的最核心技能
        'delta lake': 1.9,  # 占彬的核心技能
        'spark': 1.8,
        'pyspark': 1.9,  # 占彬的核心技能
        'spark sql': 1.8,
        'hadoop': 1.5,
        'hdfs': 1.5,
        'hive': 1.5,
        'kafka': 1.6,
        'ssis': 1.8,  # 占彬有丰富经验
        'informatica': 1.8,  # 占彬有丰富经验
        'etl': 1.8,  # 占彬的核心技能
        'elt': 1.7,
        'data pipeline': 1.9,  # 占彬的核心技能
        'data integration': 1.8,
        'oltp': 1.7,  # 占彬简历中的技能
        'olap': 1.7,  # 占彬简历中的技能
        'data warehouse': 1.8,
        'data lineage': 1.8,  # 占彬的专长
        'data governance': 1.9,  # 占彬的专长
        'data quality': 1.8,  # 占彬的专长
        'metadata management': 1.8,  # 占彬的专长
        
        # AI/ML技能 (占彬的专长)
        'machine learning': 1.9,  # 占彬的核心技能
        'deep learning': 1.8,  # 占彬的核心技能
        'ai': 1.9,
        'artificial intelligence': 1.9,
        'computer vision': 1.8,  # 占彬的专长
        'tensorflow': 1.7,
        'pytorch': 1.8,  # 占彬的核心技能
        'yolo': 1.7,  # 占彬简历中的技能
        'resnet': 1.7,  # 占彬简历中的技能
        'attention mechanism': 1.7,  # 占彬简历中的技能
        'opencv': 1.6,
        'scikit-learn': 1.5,
        'pandas': 1.6,  # 占彬的核心技能
        'numpy': 1.6,  # 占彬的核心技能
        'matplotlib': 1.4,
        'langchain': 1.8,  # 占彬简历中的技能
        'llamaindex': 1.8,  # 占彬简历中的技能
        'openai api': 1.7,
        'azure openai': 1.8,  # 占彬的Azure专长
        'rag': 1.9,  # 占彬的核心技能
        'retrieval augmented generation': 1.9,
        'prompt engineering': 1.7,  # 占彬简历中的技能
        
        # 数据科学
        'data science': 1.8,  # 占彬的核心领域
        'data analysis': 1.7,
        'data visualization': 1.6,
        'big data': 1.7,
        
        # DevOps和基础设施
        'docker': 1.5,
        'kubernetes': 1.6,
        'jenkins': 1.4,
        'ci/cd': 1.6,  # 占彬有经验
        'continuous integration': 1.6,
        'continuous deployment': 1.6,
        'devops': 1.6,  # 占彬的管理技能
        'git': 1.3,
        'linux': 1.4,
        
        # 项目管理和方法论 (占彬的管理经验)
        'agile': 1.7,  # 占彬的核心技能
        'scrum': 1.8,  # 占彬是Scrum Master
        'scrum master': 1.9,  # 占彬的职位
        'project management': 1.8,  # 占彬的管理技能
        'technical lead': 1.8,  # 占彬的角色
        'team management': 1.8,  # 占彬的管理技能
        
        # 架构技能 (占彬的核心优势)
        'data architecture': 2.0,  # 占彬的核心职位
        'solution architecture': 1.9,  # 占彬的经验
        'system architecture': 1.8,
        'microservices': 1.6,
        'api': 1.5,
        'rest': 1.5,
        
        # 制药行业技能 (占彬的行业经验)
        'pharmaceutical': 1.7,  # 占彬的行业经验
        'clinical data': 1.6,
        'regulatory compliance': 1.6,
        
        # 中文技能关键词 (占彬简历中的中文技能)
        '数据工程': 1.9,
        '数据架构': 2.0,
        '数据治理': 1.9,
        '数据质量': 1.8,
        '数据血缘': 1.8,
        '元数据管理': 1.8,
        '机器学习': 1.9,
        '深度学习': 1.8,
        '计算机视觉': 1.8,
        '人工智能': 1.9,
        '数据科学': 1.8,
        '大数据': 1.7,
        '云计算': 1.8,
        '敏捷开发': 1.7,
        '项目管理': 1.8,
        '技术管理': 1.8,
        '架构设计': 1.9,
        '湖仓一体': 1.9,  # 占彬的核心架构经验
        '实时处理': 1.7,
        '批处理': 1.7,
        '流处理': 1.7
    }
    
    for skill, weight in default_skills.items():
        weights.add_skill_weight(skill, weight)
    
    return weights


# 匹配权重配置
DEFAULT_MATCHING_WEIGHTS = {
    'semantic_similarity': 0.35,  # 语义相似度
    'skills_match': 0.30,         # 技能匹配（重要）
    'experience_match': 0.20,     # 经验匹配
    'industry_match': 0.10,       # 行业匹配
    'salary_match': 0.05          # 薪资匹配
}

# 匹配阈值配置
MATCH_THRESHOLDS = {
    MatchLevel.EXCELLENT: 0.85,
    MatchLevel.GOOD: 0.70,
    MatchLevel.FAIR: 0.50,
    MatchLevel.POOR: 0.30
}


def get_match_level_from_score(score: float) -> MatchLevel:
    """根据分数获取匹配等级"""
    if score >= MATCH_THRESHOLDS[MatchLevel.EXCELLENT]:
        return MatchLevel.EXCELLENT
    elif score >= MATCH_THRESHOLDS[MatchLevel.GOOD]:
        return MatchLevel.GOOD
    elif score >= MATCH_THRESHOLDS[MatchLevel.FAIR]:
        return MatchLevel.FAIR
    else:
        return MatchLevel.POOR


def get_recommendation_priority_from_score(score: float) -> RecommendationPriority:
    """根据分数获取推荐优先级"""
    if score >= 0.85:
        return RecommendationPriority.HIGH
    elif score >= 0.70:
        return RecommendationPriority.MEDIUM
    elif score >= 0.50:
        return RecommendationPriority.LOW
    else:
        return RecommendationPriority.NOT_RECOMMENDED


@dataclass
class MatchAnalysis:
    """匹配分析结果"""
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    skill_gap_score: float = 0.0
    experience_alignment: float = 0.0
    industry_fit: float = 0.0


@dataclass
class JobMatchResult:
    """职位匹配结果模型"""
    
    job_id: str
    job_title: str
    company: str
    location: Optional[str] = None
    salary_range: Optional[Dict[str, int]] = None
    
    # 匹配评分
    overall_score: float = 0.0
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    match_level: MatchLevel = MatchLevel.POOR
    
    # 详细分析
    match_analysis: MatchAnalysis = field(default_factory=MatchAnalysis)
    recommendation_priority: RecommendationPriority = RecommendationPriority.NOT_RECOMMENDED
    
    # 元数据
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    confidence_level: float = 0.0
    processing_time: float = 0.0


@dataclass
class MatchingSummary:
    """匹配结果汇总"""
    total_matches: int = 0
    high_priority: int = 0
    medium_priority: int = 0
    low_priority: int = 0
    average_score: float = 0.0
    processing_time: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CareerInsights:
    """职业洞察分析"""
    top_matching_positions: List[str] = field(default_factory=list)
    skill_gap_analysis: Dict[str, List[str]] = field(default_factory=dict)
    salary_analysis: Dict[str, Any] = field(default_factory=dict)
    market_trends: List[str] = field(default_factory=list)
    career_recommendations: List[str] = field(default_factory=list)


@dataclass
class ResumeMatchingResult:
    """完整的简历匹配结果"""
    matching_summary: MatchingSummary
    matches: List[JobMatchResult]
    career_insights: CareerInsights
    resume_profile: Union[GenericResumeProfile, Any]  # 支持任意简历类型
    query_metadata: Dict[str, Any] = field(default_factory=dict)