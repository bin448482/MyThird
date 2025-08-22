#!/usr/bin/env python3
"""
通用简历向量化模块
支持任意用户的灵活向量化系统
"""

import asyncio
from typing import List, Dict, Any, Optional
from langchain.schema import Document
from datetime import datetime

from ..rag.vector_manager import ChromaDBManager
from ..utils.logger import get_logger
from .generic_resume_models import GenericResumeProfile, WorkExperience, Project


class GenericResumeVectorizer:
    """通用简历向量化处理器"""
    
    def __init__(self, vector_manager: ChromaDBManager, config: Dict = None):
        self.vector_manager = vector_manager
        self.config = config or {}
        self.logger = get_logger(__name__)
        self.resume_collection = "resume_profiles"
        
        # 文档类型权重
        self.document_weights = config.get('document_weights', {
            'personal_overview': 1.0,
            'skills_overview': 1.0,
            'experience_overview': 0.9,
            'education_overview': 0.7,
            'projects_overview': 0.8,
            'career_objectives': 0.7,
            'work_experience': 0.8,
            'project_detail': 0.7
        })
    
    async def vectorize_and_store(self, resume_profile: GenericResumeProfile) -> List[str]:
        """向量化并存储简历"""
        try:
            self.logger.info(f"开始向量化简历: {resume_profile.name}")
            
            # 创建简历文档
            documents = self._create_resume_documents(resume_profile)
            
            self.logger.info(f"创建了 {len(documents)} 个简历文档")
            
            # 存储到向量数据库
            doc_ids = await self.vector_manager.add_job_documents_async(
                documents, job_id=f"resume_{resume_profile.name.lower().replace(' ', '_')}"
            )
            
            self.logger.info(f"成功存储简历向量，文档ID: {doc_ids}")
            return doc_ids
            
        except Exception as e:
            self.logger.error(f"简历向量化失败: {str(e)}")
            raise
    
    def _create_resume_documents(self, profile: GenericResumeProfile) -> List[Document]:
        """创建简历文档"""
        documents = []
        
        # 1. 个人概览文档
        personal_doc = self._create_personal_overview_document(profile)
        documents.append(personal_doc)
        
        # 2. 技能概览文档
        skills_doc = self._create_skills_overview_document(profile)
        documents.append(skills_doc)
        
        # 3. 工作经验概览文档
        experience_doc = self._create_experience_overview_document(profile)
        documents.append(experience_doc)
        
        # 4. 教育背景文档
        if profile.education:
            education_doc = self._create_education_overview_document(profile)
            documents.append(education_doc)
        
        # 5. 项目经验概览文档
        if profile.projects:
            projects_doc = self._create_projects_overview_document(profile)
            documents.append(projects_doc)
        
        # 6. 职业目标文档
        career_doc = self._create_career_objectives_document(profile)
        documents.append(career_doc)
        
        # 7. 详细工作经历文档（每个工作经历一个文档）
        for i, work_exp in enumerate(profile.work_history):
            work_doc = self._create_work_experience_document(work_exp, profile, i)
            documents.append(work_doc)
        
        # 8. 详细项目文档（每个项目一个文档）
        for i, project in enumerate(profile.projects):
            project_doc = self._create_project_detail_document(project, profile, i)
            documents.append(project_doc)
        
        return documents
    
    def _create_personal_overview_document(self, profile: GenericResumeProfile) -> Document:
        """创建个人概览文档"""
        content_parts = [
            f"姓名: {profile.name}",
            f"当前职位: {profile.current_position}",
            f"当前公司: {profile.current_company}",
            f"工作经验: {profile.total_experience_years}年",
            f"所在地: {profile.location}",
            ""
        ]
        
        # 添加认证信息
        if profile.certifications:
            content_parts.append("认证:")
            content_parts.append(", ".join(profile.certifications))
            content_parts.append("")
        
        # 添加语言能力
        if profile.languages:
            content_parts.append("语言能力:")
            for lang in profile.languages:
                content_parts.append(f"• {lang.get('language', '')}: {lang.get('level', '')}")
            content_parts.append("")
        
        # 添加软技能
        if profile.soft_skills:
            content_parts.append("软技能:")
            content_parts.append(", ".join(profile.soft_skills))
            content_parts.append("")
        
        content = "\n".join(content_parts)
        
        metadata = {
            "document_type": "personal_overview",
            "resume_id": f"resume_{profile.name.lower().replace(' ', '_')}",
            "person_name": profile.name,
            "current_position": profile.current_position,
            "current_company": profile.current_company,
            "experience_years": profile.total_experience_years,
            "location": profile.location,
            "certifications": profile.certifications,
            "languages": [lang.get('language', '') for lang in profile.languages],
            "soft_skills": profile.soft_skills,
            "weight": self.document_weights.get('personal_overview', 1.0),
            "created_at": datetime.now().isoformat()
        }
        
        return Document(page_content=content, metadata=metadata)
    
    def _create_skills_overview_document(self, profile: GenericResumeProfile) -> Document:
        """创建技能概览文档"""
        content_parts = [
            f"{profile.name} - 技能概览",
            f"总工作经验: {profile.total_experience_years}年",
            ""
        ]
        
        # 按分类组织技能
        all_skills = []
        for category in profile.skill_categories:
            content_parts.append(f"{category.category_name}:")
            skills_text = ", ".join(category.skills)
            content_parts.append(skills_text)
            
            if category.proficiency_level:
                content_parts.append(f"熟练程度: {category.proficiency_level}")
            
            if category.years_experience:
                content_parts.append(f"相关经验: {category.years_experience}年")
            
            content_parts.append("")
            all_skills.extend(category.skills)
        
        content = "\n".join(content_parts)
        
        # 构建技能分类元数据
        skill_categories_meta = {}
        for category in profile.skill_categories:
            skill_categories_meta[category.category_name] = {
                'skills': category.skills,
                'proficiency_level': category.proficiency_level,
                'years_experience': category.years_experience
            }
        
        metadata = {
            "document_type": "skills_overview",
            "resume_id": f"resume_{profile.name.lower().replace(' ', '_')}",
            "person_name": profile.name,
            "all_skills": all_skills,
            "skill_categories": skill_categories_meta,
            "total_skills_count": len(all_skills),
            "weight": self.document_weights.get('skills_overview', 1.0),
            "created_at": datetime.now().isoformat()
        }
        
        return Document(page_content=content, metadata=metadata)
    
    def _create_experience_overview_document(self, profile: GenericResumeProfile) -> Document:
        """创建工作经验概览文档"""
        content_parts = [
            f"{profile.name} - 工作经验概览",
            f"总工作经验: {profile.total_experience_years}年",
            f"当前公司: {profile.current_company}",
            f"当前职位: {profile.current_position}",
            "",
            "工作经历摘要:"
        ]
        
        companies = []
        positions = []
        industries = []
        all_technologies = []
        
        for work_exp in profile.work_history:
            content_parts.append(f"• {work_exp.company} - {work_exp.position} ({work_exp.duration_years}年)")
            content_parts.append(f"  行业: {work_exp.industry}")
            
            if work_exp.technologies:
                tech_text = ", ".join(work_exp.technologies[:5])
                content_parts.append(f"  主要技术: {tech_text}")
            
            # 添加主要成就
            if work_exp.achievements:
                content_parts.append(f"  主要成就: {work_exp.achievements[0]}")
            
            content_parts.append("")
            
            companies.append(work_exp.company)
            positions.append(work_exp.position)
            industries.append(work_exp.industry)
            all_technologies.extend(work_exp.technologies)
        
        content = "\n".join(content_parts)
        
        metadata = {
            "document_type": "experience_overview",
            "resume_id": f"resume_{profile.name.lower().replace(' ', '_')}",
            "person_name": profile.name,
            "total_experience_years": profile.total_experience_years,
            "companies": companies,
            "positions": positions,
            "industries": list(set(industries)),
            "technologies": list(set(all_technologies)),
            "current_company": profile.current_company,
            "current_position": profile.current_position,
            "weight": self.document_weights.get('experience_overview', 0.9),
            "created_at": datetime.now().isoformat()
        }
        
        return Document(page_content=content, metadata=metadata)
    
    def _create_education_overview_document(self, profile: GenericResumeProfile) -> Document:
        """创建教育背景文档"""
        content_parts = [
            f"{profile.name} - 教育背景",
            ""
        ]
        
        degrees = []
        majors = []
        universities = []
        
        for edu in profile.education:
            content_parts.append(f"• {edu.degree} - {edu.major}")
            content_parts.append(f"  学校: {edu.university}")
            content_parts.append(f"  毕业年份: {edu.graduation_year}")
            
            if edu.gpa:
                content_parts.append(f"  GPA: {edu.gpa}")
            
            if edu.honors:
                content_parts.append(f"  荣誉: {', '.join(edu.honors)}")
            
            content_parts.append("")
            
            degrees.append(edu.degree)
            majors.append(edu.major)
            universities.append(edu.university)
        
        content = "\n".join(content_parts)
        
        metadata = {
            "document_type": "education_overview",
            "resume_id": f"resume_{profile.name.lower().replace(' ', '_')}",
            "person_name": profile.name,
            "degrees": degrees,
            "majors": majors,
            "universities": universities,
            "education_count": len(profile.education),
            "weight": self.document_weights.get('education_overview', 0.7),
            "created_at": datetime.now().isoformat()
        }
        
        return Document(page_content=content, metadata=metadata)
    
    def _create_projects_overview_document(self, profile: GenericResumeProfile) -> Document:
        """创建项目经验概览文档"""
        content_parts = [
            f"{profile.name} - 项目经验概览",
            f"项目数量: {len(profile.projects)}",
            ""
        ]
        
        all_project_technologies = []
        project_names = []
        
        for project in profile.projects:
            content_parts.append(f"• {project.name}")
            content_parts.append(f"  描述: {project.description}")
            content_parts.append(f"  持续时间: {project.duration}")
            
            if project.role:
                content_parts.append(f"  角色: {project.role}")
            
            if project.technologies:
                tech_text = ", ".join(project.technologies)
                content_parts.append(f"  技术栈: {tech_text}")
                all_project_technologies.extend(project.technologies)
            
            if project.achievements:
                content_parts.append(f"  主要成果: {project.achievements[0]}")
            
            content_parts.append("")
            project_names.append(project.name)
        
        content = "\n".join(content_parts)
        
        metadata = {
            "document_type": "projects_overview",
            "resume_id": f"resume_{profile.name.lower().replace(' ', '_')}",
            "person_name": profile.name,
            "project_names": project_names,
            "project_technologies": list(set(all_project_technologies)),
            "projects_count": len(profile.projects),
            "weight": self.document_weights.get('projects_overview', 0.8),
            "created_at": datetime.now().isoformat()
        }
        
        return Document(page_content=content, metadata=metadata)
    
    def _create_career_objectives_document(self, profile: GenericResumeProfile) -> Document:
        """创建职业目标文档"""
        content_parts = [
            f"{profile.name} - 职业发展目标",
            ""
        ]
        
        if profile.preferred_positions:
            content_parts.append("期望职位:")
            content_parts.append(", ".join(profile.preferred_positions))
            content_parts.append("")
        
        if profile.expected_salary_range and profile.expected_salary_range.get('min', 0) > 0:
            salary_min = profile.expected_salary_range['min']
            salary_max = profile.expected_salary_range['max']
            content_parts.append("薪资期望:")
            content_parts.append(f"{salary_min:,} - {salary_max:,} 元/年")
            content_parts.append("")
        
        if profile.career_objectives:
            content_parts.append("职业目标:")
            for objective in profile.career_objectives:
                content_parts.append(f"• {objective}")
            content_parts.append("")
        
        if profile.personality_traits:
            content_parts.append("个人特质:")
            content_parts.append(", ".join(profile.personality_traits))
        
        content = "\n".join(content_parts)
        
        metadata = {
            "document_type": "career_objectives",
            "resume_id": f"resume_{profile.name.lower().replace(' ', '_')}",
            "person_name": profile.name,
            "preferred_positions": profile.preferred_positions,
            "salary_min": profile.expected_salary_range.get('min', 0),
            "salary_max": profile.expected_salary_range.get('max', 0),
            "career_objectives": profile.career_objectives,
            "personality_traits": profile.personality_traits,
            "weight": self.document_weights.get('career_objectives', 0.7),
            "created_at": datetime.now().isoformat()
        }
        
        return Document(page_content=content, metadata=metadata)
    
    def _create_work_experience_document(self, work_exp: WorkExperience, 
                                       profile: GenericResumeProfile, 
                                       index: int) -> Document:
        """创建单个工作经历文档"""
        content_parts = [
            f"{profile.name} - {work_exp.company} 工作经历",
            f"职位: {work_exp.position}",
            f"时间: {work_exp.start_date} - {work_exp.end_date or '至今'}",
            f"工作时长: {work_exp.duration_years}年",
            f"行业: {work_exp.industry}",
            ""
        ]
        
        if work_exp.responsibilities:
            content_parts.append("主要职责:")
            for responsibility in work_exp.responsibilities:
                content_parts.append(f"• {responsibility}")
            content_parts.append("")
        
        if work_exp.achievements:
            content_parts.append("主要成就:")
            for achievement in work_exp.achievements:
                content_parts.append(f"• {achievement}")
            content_parts.append("")
        
        if work_exp.technologies:
            content_parts.append("使用技术:")
            content_parts.append(", ".join(work_exp.technologies))
        
        content = "\n".join(content_parts)
        
        metadata = {
            "document_type": "work_experience",
            "resume_id": f"resume_{profile.name.lower().replace(' ', '_')}",
            "person_name": profile.name,
            "company": work_exp.company,
            "position": work_exp.position,
            "industry": work_exp.industry,
            "duration_years": work_exp.duration_years,
            "technologies": work_exp.technologies,
            "start_date": work_exp.start_date,
            "end_date": work_exp.end_date,
            "experience_index": index,
            "weight": self.document_weights.get('work_experience', 0.8),
            "created_at": datetime.now().isoformat()
        }
        
        return Document(page_content=content, metadata=metadata)
    
    def _create_project_detail_document(self, project: Project, 
                                      profile: GenericResumeProfile, 
                                      index: int) -> Document:
        """创建单个项目详情文档"""
        content_parts = [
            f"{profile.name} - 项目: {project.name}",
            f"项目描述: {project.description}",
            f"持续时间: {project.duration}",
        ]
        
        if project.role:
            content_parts.append(f"担任角色: {project.role}")
        
        if project.url:
            content_parts.append(f"项目链接: {project.url}")
        
        content_parts.append("")
        
        if project.technologies:
            content_parts.append("技术栈:")
            content_parts.append(", ".join(project.technologies))
            content_parts.append("")
        
        if project.achievements:
            content_parts.append("项目成果:")
            for achievement in project.achievements:
                content_parts.append(f"• {achievement}")
        
        content = "\n".join(content_parts)
        
        metadata = {
            "document_type": "project_detail",
            "resume_id": f"resume_{profile.name.lower().replace(' ', '_')}",
            "person_name": profile.name,
            "project_name": project.name,
            "project_description": project.description,
            "project_duration": project.duration,
            "project_role": project.role,
            "project_technologies": project.technologies,
            "project_url": project.url,
            "project_index": index,
            "weight": self.document_weights.get('project_detail', 0.7),
            "created_at": datetime.now().isoformat()
        }
        
        return Document(page_content=content, metadata=metadata)
    
    def update_resume_profile(self, resume_profile: GenericResumeProfile) -> bool:
        """更新简历档案"""
        try:
            # 先删除旧的简历文档
            resume_id = f"resume_{resume_profile.name.lower().replace(' ', '_')}"
            self.vector_manager.delete_documents(resume_id)
            
            # 重新向量化和存储
            asyncio.run(self.vectorize_and_store(resume_profile))
            
            self.logger.info(f"成功更新简历档案: {resume_profile.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"更新简历档案失败: {str(e)}")
            return False
    
    def validate_resume_vectorization(self, resume_profile: GenericResumeProfile) -> Dict[str, Any]:
        """验证简历向量化结果"""
        try:
            documents = self._create_resume_documents(resume_profile)
            
            validation_result = {
                "total_documents": len(documents),
                "document_types": [doc.metadata.get("document_type") for doc in documents],
                "total_content_length": sum(len(doc.page_content) for doc in documents),
                "metadata_completeness": all(
                    doc.metadata.get("resume_id") and 
                    doc.metadata.get("person_name") and
                    doc.metadata.get("document_type")
                    for doc in documents
                ),
                "skills_coverage": len(resume_profile.get_all_skills()),
                "experience_coverage": len(resume_profile.work_history),
                "projects_coverage": len(resume_profile.projects),
                "validation_passed": True
            }
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"简历向量化验证失败: {str(e)}")
            return {
                "validation_passed": False,
                "error": str(e)
            }