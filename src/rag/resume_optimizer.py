"""
简历优化器

基于RAG技术的智能简历优化器，分析职位要求并提供个性化的简历优化建议
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from .rag_system_coordinator import RAGSystemCoordinator
from .llm_factory import create_llm
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)


class ResumeOptimizer:
    """简历优化器"""
    
    def __init__(self, rag_coordinator: RAGSystemCoordinator, llm_config: Dict = None):
        """
        初始化简历优化器
        
        Args:
            rag_coordinator: RAG系统协调器
            llm_config: LLM配置
        """
        self.rag_coordinator = rag_coordinator
        self.llm_config = llm_config or {}
        
        # 初始化LLM
        provider = self.llm_config.get('provider', 'zhipu')
        self.llm = create_llm(
            provider=provider,
            model=self.llm_config.get('model', 'glm-4-flash'),
            temperature=self.llm_config.get('temperature', 0.3),
            max_tokens=self.llm_config.get('max_tokens', 2000),
            **{k: v for k, v in self.llm_config.items() if k not in ['provider', 'model', 'temperature', 'max_tokens']}
        )
        
        # 构建优化链
        self.gap_analysis_chain = self._build_gap_analysis_chain()
        self.skill_suggestion_chain = self._build_skill_suggestion_chain()
        self.content_optimization_chain = self._build_content_optimization_chain()
        self.cover_letter_chain = self._build_cover_letter_chain()
        
        logger.info(f"简历优化器初始化完成，使用LLM提供商: {provider}")
    
    def _build_gap_analysis_chain(self):
        """构建差距分析链"""
        prompt_template = """
你是专业的职业规划顾问。请分析候选人简历与目标职位之间的差距。

候选人简历信息：
{resume_info}

目标职位信息：
{job_info}

请从以下维度分析差距并提供建议：

1. 技能差距分析
2. 经验差距分析
3. 教育背景匹配度
4. 项目经验相关性
5. 软技能评估

请严格按照以下JSON格式输出：

{{
    "skill_gaps": [
        {{
            "missing_skill": "缺失的技能",
            "importance": "高/中/低",
            "suggestion": "学习建议"
        }}
    ],
    "experience_gaps": [
        {{
            "gap_area": "差距领域",
            "current_level": "当前水平",
            "required_level": "要求水平",
            "improvement_suggestion": "提升建议"
        }}
    ],
    "education_match": {{
        "match_score": 0.8,
        "analysis": "教育背景匹配分析"
    }},
    "project_relevance": {{
        "relevance_score": 0.7,
        "relevant_projects": ["相关项目1", "相关项目2"],
        "suggestions": ["项目优化建议1", "项目优化建议2"]
    }},
    "soft_skills": {{
        "strengths": ["优势软技能1", "优势软技能2"],
        "areas_for_improvement": ["需要提升的软技能1", "需要提升的软技能2"]
    }},
    "overall_match_score": 0.75,
    "priority_improvements": ["最优先改进项1", "最优先改进项2", "最优先改进项3"]
}}

JSON输出：
"""
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["resume_info", "job_info"]
        )
        
        return prompt | self.llm | StrOutputParser()
    
    def _build_skill_suggestion_chain(self):
        """构建技能建议链"""
        prompt_template = """
你是技术专家和职业导师。基于市场趋势和职位要求，为候选人提供技能提升建议。

候选人当前技能：
{current_skills}

目标职位技能要求：
{required_skills}

市场热门技能趋势：
{market_trends}

请提供详细的技能提升路径和学习建议：

请严格按照以下JSON格式输出：

{{
    "immediate_skills": [
        {{
            "skill": "技能名称",
            "priority": "高/中/低",
            "learning_path": "学习路径",
            "estimated_time": "预计学习时间",
            "resources": ["学习资源1", "学习资源2"]
        }}
    ],
    "long_term_skills": [
        {{
            "skill": "技能名称",
            "market_demand": "市场需求度",
            "career_impact": "职业发展影响",
            "learning_strategy": "学习策略"
        }}
    ],
    "skill_combinations": [
        {{
            "combination": ["技能1", "技能2", "技能3"],
            "synergy_benefit": "协同效应",
            "career_opportunities": "职业机会"
        }}
    ],
    "certification_recommendations": [
        {{
            "certification": "认证名称",
            "value": "认证价值",
            "difficulty": "难度等级",
            "timeline": "获取时间"
        }}
    ]
}}

JSON输出：
"""
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["current_skills", "required_skills", "market_trends"]
        )
        
        return prompt | self.llm | StrOutputParser()
    
    def _build_content_optimization_chain(self):
        """构建内容优化链"""
        prompt_template = """
你是专业的简历写作专家。请为候选人优化简历内容，使其更好地匹配目标职位。

原始简历内容：
{original_resume}

目标职位要求：
{job_requirements}

优化重点：
{optimization_focus}

请提供详细的简历优化建议：

请严格按照以下JSON格式输出：

{{
    "summary_optimization": {{
        "original": "原始个人简介",
        "optimized": "优化后的个人简介",
        "improvements": ["改进点1", "改进点2"]
    }},
    "experience_optimization": [
        {{
            "position": "职位名称",
            "original_description": "原始描述",
            "optimized_description": "优化后描述",
            "key_improvements": ["关键改进1", "关键改进2"]
        }}
    ],
    "skills_presentation": {{
        "technical_skills": {{
            "original": ["原始技能列表"],
            "optimized": ["优化后技能列表"],
            "grouping_strategy": "技能分组策略"
        }},
        "soft_skills": {{
            "recommended": ["推荐的软技能"],
            "presentation_tips": ["展示技巧1", "展示技巧2"]
        }}
    }},
    "project_highlights": [
        {{
            "project": "项目名称",
            "relevance_score": 0.9,
            "optimization_suggestions": ["优化建议1", "优化建议2"],
            "impact_metrics": ["影响指标1", "影响指标2"]
        }}
    ],
    "keyword_optimization": {{
        "missing_keywords": ["缺失关键词1", "缺失关键词2"],
        "keyword_placement": ["关键词放置建议1", "关键词放置建议2"],
        "ats_optimization": ["ATS优化建议1", "ATS优化建议2"]
    }},
    "formatting_suggestions": [
        "格式建议1",
        "格式建议2",
        "格式建议3"
    ]
}}

JSON输出：
"""
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["original_resume", "job_requirements", "optimization_focus"]
        )
        
        return prompt | self.llm | StrOutputParser()
    
    def _build_cover_letter_chain(self):
        """构建求职信生成链"""
        prompt_template = """
你是专业的求职信写作专家。请为候选人生成一份个性化的求职信。

候选人信息：
{candidate_info}

目标职位信息：
{job_info}

公司信息：
{company_info}

求职信要求：
- 长度适中（300-500字）
- 突出匹配度
- 体现个人特色
- 专业且有吸引力

请生成一份完整的求职信：

求职信内容：
"""
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["candidate_info", "job_info", "company_info"]
        )
        
        return prompt | self.llm | StrOutputParser()
    
    async def analyze_resume_gaps(self, resume: Dict, target_jobs: List[str]) -> Dict[str, Any]:
        """
        分析简历与目标职位的差距
        
        Args:
            resume: 简历信息
            target_jobs: 目标职位ID列表
            
        Returns:
            差距分析结果
        """
        try:
            gap_analyses = []
            
            for job_id in target_jobs:
                # 获取职位详细信息
                job_data = self.rag_coordinator.db_reader.get_job_with_details(job_id)
                if not job_data:
                    logger.warning(f"未找到职位信息: {job_id}")
                    continue
                
                # 构建职位信息摘要
                job_info = self._format_job_info(job_data)
                resume_info = self._format_resume_info(resume)
                
                # 执行差距分析
                analysis_result = await self.gap_analysis_chain.ainvoke({
                    "resume_info": resume_info,
                    "job_info": job_info
                })
                
                # 解析结果
                parsed_analysis = self._parse_json_result(analysis_result)
                parsed_analysis['job_id'] = job_id
                parsed_analysis['job_title'] = job_data.get('title', '未知职位')
                parsed_analysis['company'] = job_data.get('company', '未知公司')
                
                gap_analyses.append(parsed_analysis)
            
            # 汇总分析结果
            summary = self._summarize_gap_analyses(gap_analyses)
            
            return {
                'individual_analyses': gap_analyses,
                'summary': summary,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"简历差距分析失败: {e}")
            return {'error': str(e)}
    
    async def suggest_skill_improvements(self, resume: Dict, market_data: Dict = None) -> List[Dict]:
        """
        建议技能提升方向
        
        Args:
            resume: 简历信息
            market_data: 市场数据
            
        Returns:
            技能提升建议列表
        """
        try:
            # 获取相关职位的技能要求
            relevant_jobs = await self._find_relevant_jobs(resume)
            required_skills = self._extract_required_skills(relevant_jobs)
            
            current_skills = resume.get('skills', [])
            market_trends = market_data.get('trending_skills', []) if market_data else []
            
            # 生成技能建议
            suggestion_result = await self.skill_suggestion_chain.ainvoke({
                "current_skills": ', '.join(current_skills),
                "required_skills": ', '.join(required_skills),
                "market_trends": ', '.join(market_trends)
            })
            
            # 解析结果
            parsed_suggestions = self._parse_json_result(suggestion_result)
            
            return {
                'skill_suggestions': parsed_suggestions,
                'analysis_basis': {
                    'current_skills_count': len(current_skills),
                    'required_skills_count': len(required_skills),
                    'relevant_jobs_count': len(relevant_jobs)
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"技能建议生成失败: {e}")
            return {'error': str(e)}
    
    async def optimize_resume_content(self, resume: Dict, target_job_id: str, focus_areas: List[str] = None) -> Dict:
        """
        优化简历内容
        
        Args:
            resume: 简历信息
            target_job_id: 目标职位ID
            focus_areas: 优化重点领域
            
        Returns:
            简历优化建议
        """
        try:
            # 获取目标职位信息
            job_data = self.rag_coordinator.db_reader.get_job_with_details(target_job_id)
            if not job_data:
                return {'error': f'未找到职位信息: {target_job_id}'}
            
            # 格式化输入
            original_resume = self._format_resume_for_optimization(resume)
            job_requirements = self._format_job_requirements(job_data)
            optimization_focus = ', '.join(focus_areas) if focus_areas else '全面优化'
            
            # 执行内容优化
            optimization_result = await self.content_optimization_chain.ainvoke({
                "original_resume": original_resume,
                "job_requirements": job_requirements,
                "optimization_focus": optimization_focus
            })
            
            # 解析结果
            parsed_optimization = self._parse_json_result(optimization_result)
            
            return {
                'optimization_suggestions': parsed_optimization,
                'target_job': {
                    'job_id': target_job_id,
                    'title': job_data.get('title'),
                    'company': job_data.get('company')
                },
                'focus_areas': focus_areas or ['全面优化'],
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"简历内容优化失败: {e}")
            return {'error': str(e)}
    
    async def generate_cover_letter(self, resume: Dict, job_id: str) -> str:
        """
        生成求职信
        
        Args:
            resume: 简历信息
            job_id: 职位ID
            
        Returns:
            生成的求职信
        """
        try:
            # 获取职位信息
            job_data = self.rag_coordinator.db_reader.get_job_with_details(job_id)
            if not job_data:
                return f'错误：未找到职位信息 {job_id}'
            
            # 格式化信息
            candidate_info = self._format_candidate_info(resume)
            job_info = self._format_job_info_for_cover_letter(job_data)
            company_info = self._format_company_info(job_data)
            
            # 生成求职信
            cover_letter = await self.cover_letter_chain.ainvoke({
                "candidate_info": candidate_info,
                "job_info": job_info,
                "company_info": company_info
            })
            
            return cover_letter.strip()
            
        except Exception as e:
            logger.error(f"求职信生成失败: {e}")
            return f'求职信生成失败: {e}'
    
    def _format_job_info(self, job_data: Dict) -> str:
        """格式化职位信息"""
        info_parts = [
            f"职位：{job_data.get('title', '未知')}",
            f"公司：{job_data.get('company', '未知')}",
            f"地点：{job_data.get('location', '未知')}",
            f"薪资：{job_data.get('salary', '面议')}",
            f"经验要求：{job_data.get('experience', '不限')}",
            f"学历要求：{job_data.get('education', '不限')}"
        ]
        
        if job_data.get('description'):
            info_parts.append(f"职位描述：{job_data['description'][:500]}...")
        
        if job_data.get('requirements'):
            info_parts.append(f"职位要求：{job_data['requirements'][:500]}...")
        
        return '\n'.join(info_parts)
    
    def _format_resume_info(self, resume: Dict) -> str:
        """格式化简历信息"""
        info_parts = [
            f"姓名：{resume.get('name', '未提供')}",
            f"当前职位：{resume.get('current_position', '未提供')}",
            f"工作经验：{resume.get('years_of_experience', '未提供')}年",
            f"教育背景：{resume.get('education', '未提供')}",
            f"技能：{', '.join(resume.get('skills', []))}"
        ]
        
        if resume.get('summary'):
            info_parts.append(f"个人简介：{resume['summary']}")
        
        if resume.get('experience'):
            info_parts.append("工作经历：")
            for exp in resume['experience'][:3]:  # 只取前3个经历
                info_parts.append(f"- {exp.get('position', '')} at {exp.get('company', '')} ({exp.get('duration', '')})")
        
        return '\n'.join(info_parts)
    
    def _parse_json_result(self, result: str) -> Dict:
        """解析JSON结果"""
        try:
            # 清理结果字符串
            cleaned_result = result.strip()
            
            # 提取JSON部分
            if "```json" in cleaned_result:
                start = cleaned_result.find("```json") + 7
                end = cleaned_result.find("```", start)
                if end != -1:
                    cleaned_result = cleaned_result[start:end].strip()
            elif "```" in cleaned_result:
                start = cleaned_result.find("```") + 3
                end = cleaned_result.find("```", start)
                if end != -1:
                    cleaned_result = cleaned_result[start:end].strip()
            
            return json.loads(cleaned_result)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return {'error': f'结果解析失败: {e}', 'raw_result': result}
    
    async def _find_relevant_jobs(self, resume: Dict) -> List[Dict]:
        """查找相关职位"""
        try:
            # 基于简历技能和职位搜索相关职位
            skills = resume.get('skills', [])
            if not skills:
                return []
            
            # 使用向量搜索找到相关职位
            query = f"技能要求：{', '.join(skills[:5])}"  # 只用前5个技能
            similar_docs = self.rag_coordinator.vector_manager.search_similar_jobs(query, k=10)
            
            # 提取职位ID并获取详细信息
            job_ids = list(set([doc.metadata.get('job_id') for doc in similar_docs if doc.metadata.get('job_id')]))
            
            relevant_jobs = []
            for job_id in job_ids[:5]:  # 限制为5个相关职位
                job_data = self.rag_coordinator.db_reader.get_job_with_details(job_id)
                if job_data:
                    relevant_jobs.append(job_data)
            
            return relevant_jobs
            
        except Exception as e:
            logger.error(f"查找相关职位失败: {e}")
            return []
    
    def _extract_required_skills(self, jobs: List[Dict]) -> List[str]:
        """从职位列表中提取技能要求"""
        all_skills = set()
        
        for job in jobs:
            # 从描述中提取技能关键词
            description = job.get('description', '')
            requirements = job.get('requirements', '')
            
            # 简单的技能关键词提取
            skill_keywords = [
                'Python', 'Java', 'JavaScript', 'React', 'Vue', 'Angular', 'Node.js',
                'SQL', 'MySQL', 'PostgreSQL', 'MongoDB', 'Redis',
                'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP',
                'Git', 'Linux', 'HTML', 'CSS', 'TypeScript'
            ]
            
            text = f"{description} {requirements}".lower()
            for skill in skill_keywords:
                if skill.lower() in text:
                    all_skills.add(skill)
        
        return list(all_skills)
    
    def _summarize_gap_analyses(self, analyses: List[Dict]) -> Dict:
        """汇总差距分析结果"""
        if not analyses:
            return {}
        
        # 统计常见差距
        common_skill_gaps = {}
        common_experience_gaps = {}
        overall_scores = []
        
        for analysis in analyses:
            if 'error' in analysis:
                continue
            
            # 统计技能差距
            for gap in analysis.get('skill_gaps', []):
                skill = gap.get('missing_skill', '')
                if skill:
                    common_skill_gaps[skill] = common_skill_gaps.get(skill, 0) + 1
            
            # 统计经验差距
            for gap in analysis.get('experience_gaps', []):
                area = gap.get('gap_area', '')
                if area:
                    common_experience_gaps[area] = common_experience_gaps.get(area, 0) + 1
            
            # 收集总体评分
            score = analysis.get('overall_match_score', 0)
            if score > 0:
                overall_scores.append(score)
        
        # 计算平均匹配度
        avg_match_score = sum(overall_scores) / len(overall_scores) if overall_scores else 0
        
        return {
            'average_match_score': round(avg_match_score, 2),
            'most_common_skill_gaps': sorted(common_skill_gaps.items(), key=lambda x: x[1], reverse=True)[:5],
            'most_common_experience_gaps': sorted(common_experience_gaps.items(), key=lambda x: x[1], reverse=True)[:5],
            'total_jobs_analyzed': len([a for a in analyses if 'error' not in a])
        }
    
    def _format_resume_for_optimization(self, resume: Dict) -> str:
        """为优化格式化简历"""
        return self._format_resume_info(resume)
    
    def _format_job_requirements(self, job_data: Dict) -> str:
        """格式化职位要求"""
        return self._format_job_info(job_data)
    
    def _format_candidate_info(self, resume: Dict) -> str:
        """格式化候选人信息"""
        return self._format_resume_info(resume)
    
    def _format_job_info_for_cover_letter(self, job_data: Dict) -> str:
        """为求职信格式化职位信息"""
        return f"{job_data.get('title', '未知职位')} - {job_data.get('company', '未知公司')}"
    
    def _format_company_info(self, job_data: Dict) -> str:
        """格式化公司信息"""
        info_parts = [
            f"公司名称：{job_data.get('company', '未知公司')}",
            f"行业：{job_data.get('industry', '未知行业')}",
            f"规模：{job_data.get('company_scale', '未知规模')}"
        ]
        return '\n'.join(info_parts)