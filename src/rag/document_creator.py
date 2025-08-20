"""
文档创建器

负责将职位信息转换为LangChain文档对象，支持多种文档类型和元数据管理。
"""

from langchain.schema import Document
from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime
import hashlib

from .job_processor import JobStructure

logger = logging.getLogger(__name__)


class DocumentCreator:
    """文档创建器"""
    
    def __init__(self, config: Dict = None):
        """
        初始化文档创建器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.document_types = self.config.get('document_types', [
            'overview', 'responsibility', 'requirement', 'skills', 'basic_requirements'
        ])
        
        logger.info("文档创建器初始化完成")
    
    def create_job_documents(self, job_structure: JobStructure, job_id: str = None, 
                           source_url: str = None) -> List[Document]:
        """
        从职位结构创建文档
        
        Args:
            job_structure: 结构化职位信息
            job_id: 职位ID
            source_url: 来源URL
            
        Returns:
            List[Document]: 文档列表
        """
        documents = []
        timestamp = datetime.now().isoformat()
        
        # 生成文档ID前缀
        doc_id_prefix = self._generate_doc_id_prefix(job_structure, job_id)
        
        # 基础元数据
        base_metadata = {
            "job_id": job_id,
            "job_title": job_structure.job_title,
            "company": job_structure.company,
            "location": job_structure.location,
            "salary_min": job_structure.salary_min,
            "salary_max": job_structure.salary_max,
            "education": job_structure.education,
            "experience": job_structure.experience,
            "source_url": source_url,
            "created_at": timestamp,
            "doc_id_prefix": doc_id_prefix
        }
        
        # 1. 创建职位概览文档
        if 'overview' in self.document_types:
            overview_doc = self._create_overview_document(job_structure, base_metadata)
            documents.append(overview_doc)
        
        # 2. 创建职责文档
        if 'responsibility' in self.document_types:
            responsibility_docs = self._create_responsibility_documents(
                job_structure, base_metadata
            )
            documents.extend(responsibility_docs)
        
        # 3. 创建要求文档
        if 'requirement' in self.document_types:
            requirement_docs = self._create_requirement_documents(
                job_structure, base_metadata
            )
            documents.extend(requirement_docs)
        
        # 4. 创建技能文档
        if 'skills' in self.document_types and job_structure.skills:
            skills_doc = self._create_skills_document(job_structure, base_metadata)
            documents.append(skills_doc)
        
        # 5. 创建基本要求文档
        if 'basic_requirements' in self.document_types:
            basic_req_doc = self._create_basic_requirements_document(
                job_structure, base_metadata
            )
            documents.append(basic_req_doc)
        
        # 6. 创建综合文档（可选）
        if self.config.get('create_comprehensive_doc', False):
            comprehensive_doc = self._create_comprehensive_document(
                job_structure, base_metadata
            )
            documents.append(comprehensive_doc)
        
        logger.info(f"为职位 {job_structure.job_title} 创建了 {len(documents)} 个文档")
        return documents
    
    def _generate_doc_id_prefix(self, job_structure: JobStructure, job_id: str = None) -> str:
        """生成文档ID前缀"""
        if job_id:
            return job_id
        
        # 基于职位信息生成唯一ID
        content = f"{job_structure.job_title}_{job_structure.company}"
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    def _create_overview_document(self, job_structure: JobStructure, 
                                base_metadata: Dict) -> Document:
        """创建职位概览文档"""
        
        # 构建概览内容
        content_parts = [
            f"职位：{job_structure.job_title}",
            f"公司：{job_structure.company}"
        ]
        
        if job_structure.location:
            content_parts.append(f"地点：{job_structure.location}")
        
        if job_structure.salary_min and job_structure.salary_max:
            content_parts.append(f"薪资：{job_structure.salary_min}-{job_structure.salary_max}元")
        elif job_structure.salary_min:
            content_parts.append(f"薪资：{job_structure.salary_min}元起")
        
        content_parts.extend([
            f"学历要求：{job_structure.education}",
            f"经验要求：{job_structure.experience}"
        ])
        
        content = "，".join(content_parts)
        
        metadata = base_metadata.copy()
        metadata.update({
            "type": "overview",
            "doc_id": f"{base_metadata['doc_id_prefix']}_overview",
            "priority": 1  # 概览文档优先级最高
        })
        
        return Document(page_content=content, metadata=metadata)
    
    def _create_responsibility_documents(self, job_structure: JobStructure, 
                                       base_metadata: Dict) -> List[Document]:
        """创建职责文档"""
        documents = []
        
        for i, responsibility in enumerate(job_structure.responsibilities):
            if not responsibility.strip():
                continue
            
            metadata = base_metadata.copy()
            metadata.update({
                "type": "responsibility",
                "index": i,
                "doc_id": f"{base_metadata['doc_id_prefix']}_resp_{i}",
                "priority": 2
            })
            
            # 清理和格式化内容
            content = self._clean_content(responsibility)
            
            doc = Document(page_content=content, metadata=metadata)
            documents.append(doc)
        
        return documents
    
    def _create_requirement_documents(self, job_structure: JobStructure, 
                                    base_metadata: Dict) -> List[Document]:
        """创建要求文档"""
        documents = []
        
        for i, requirement in enumerate(job_structure.requirements):
            if not requirement.strip():
                continue
            
            metadata = base_metadata.copy()
            metadata.update({
                "type": "requirement",
                "index": i,
                "doc_id": f"{base_metadata['doc_id_prefix']}_req_{i}",
                "priority": 2
            })
            
            # 清理和格式化内容
            content = self._clean_content(requirement)
            
            doc = Document(page_content=content, metadata=metadata)
            documents.append(doc)
        
        return documents
    
    def _create_skills_document(self, job_structure: JobStructure, 
                              base_metadata: Dict) -> Document:
        """创建技能文档"""
        
        # 技能分类
        technical_skills = []
        soft_skills = []
        tools_skills = []
        
        for skill in job_structure.skills:
            skill_lower = skill.lower()
            if any(tech in skill_lower for tech in ['python', 'java', 'javascript', 'sql', 'html', 'css']):
                technical_skills.append(skill)
            elif any(tool in skill_lower for tool in ['git', 'docker', 'kubernetes', 'aws', 'azure']):
                tools_skills.append(skill)
            else:
                soft_skills.append(skill)
        
        # 构建内容
        content_parts = [f"技能要求：{', '.join(job_structure.skills)}"]
        
        if technical_skills:
            content_parts.append(f"技术技能：{', '.join(technical_skills)}")
        if tools_skills:
            content_parts.append(f"工具技能：{', '.join(tools_skills)}")
        if soft_skills:
            content_parts.append(f"软技能：{', '.join(soft_skills)}")
        
        content = "。".join(content_parts)
        
        metadata = base_metadata.copy()
        metadata.update({
            "type": "skills",
            "skills": ", ".join(job_structure.skills),  # 转换为字符串
            "technical_skills": ", ".join(technical_skills),  # 转换为字符串
            "soft_skills": ", ".join(soft_skills),  # 转换为字符串
            "tools_skills": ", ".join(tools_skills),  # 转换为字符串
            "doc_id": f"{base_metadata['doc_id_prefix']}_skills",
            "priority": 3
        })
        
        return Document(page_content=content, metadata=metadata)
    
    def _create_basic_requirements_document(self, job_structure: JobStructure, 
                                          base_metadata: Dict) -> Document:
        """创建基本要求文档"""
        
        content = f"学历要求：{job_structure.education}，经验要求：{job_structure.experience}"
        
        metadata = base_metadata.copy()
        metadata.update({
            "type": "basic_requirements",
            "doc_id": f"{base_metadata['doc_id_prefix']}_basic",
            "priority": 3
        })
        
        return Document(page_content=content, metadata=metadata)
    
    def _create_comprehensive_document(self, job_structure: JobStructure, 
                                     base_metadata: Dict) -> Document:
        """创建综合文档"""
        
        content_parts = [
            f"职位：{job_structure.job_title}",
            f"公司：{job_structure.company}"
        ]
        
        if job_structure.responsibilities:
            content_parts.append("岗位职责：" + "；".join(job_structure.responsibilities))
        
        if job_structure.requirements:
            content_parts.append("人员要求：" + "；".join(job_structure.requirements))
        
        if job_structure.skills:
            content_parts.append("技能要求：" + "、".join(job_structure.skills))
        
        content_parts.extend([
            f"学历要求：{job_structure.education}",
            f"经验要求：{job_structure.experience}"
        ])
        
        content = "。".join(content_parts)
        
        metadata = base_metadata.copy()
        metadata.update({
            "type": "comprehensive",
            "doc_id": f"{base_metadata['doc_id_prefix']}_comprehensive",
            "priority": 4
        })
        
        return Document(page_content=content, metadata=metadata)
    
    def _clean_content(self, content: str) -> str:
        """清理文档内容"""
        if not content:
            return ""
        
        # 移除多余的空白字符
        content = content.strip()
        
        # 移除HTML标签（如果有）
        import re
        content = re.sub(r'<[^>]+>', '', content)
        
        # 标准化换行符
        content = re.sub(r'\r\n|\r|\n', ' ', content)
        
        # 移除多余的空格
        content = re.sub(r'\s+', ' ', content)
        
        return content
    
    def create_custom_document(self, content: str, doc_type: str, 
                             metadata: Dict = None) -> Document:
        """
        创建自定义文档
        
        Args:
            content: 文档内容
            doc_type: 文档类型
            metadata: 元数据
            
        Returns:
            Document: 文档对象
        """
        base_metadata = {
            "type": doc_type,
            "created_at": datetime.now().isoformat(),
            "custom": True
        }
        
        if metadata:
            base_metadata.update(metadata)
        
        content = self._clean_content(content)
        
        return Document(page_content=content, metadata=base_metadata)
    
    def merge_documents(self, documents: List[Document], 
                       merge_type: str = "comprehensive") -> Document:
        """
        合并多个文档
        
        Args:
            documents: 文档列表
            merge_type: 合并类型
            
        Returns:
            Document: 合并后的文档
        """
        if not documents:
            return None
        
        # 合并内容
        contents = [doc.page_content for doc in documents if doc.page_content.strip()]
        merged_content = "。".join(contents)
        
        # 合并元数据
        merged_metadata = {
            "type": merge_type,
            "merged": True,
            "source_doc_count": len(documents),
            "created_at": datetime.now().isoformat()
        }
        
        # 提取公共元数据
        if documents:
            first_doc = documents[0]
            for key in ["job_id", "job_title", "company", "location"]:
                if key in first_doc.metadata:
                    merged_metadata[key] = first_doc.metadata[key]
        
        return Document(page_content=merged_content, metadata=merged_metadata)
    
    def validate_documents(self, documents: List[Document]) -> Dict[str, Any]:
        """
        验证文档质量
        
        Args:
            documents: 文档列表
            
        Returns:
            Dict: 验证结果
        """
        validation_result = {
            "total_documents": len(documents),
            "valid_documents": 0,
            "empty_documents": 0,
            "missing_metadata": 0,
            "issues": []
        }
        
        required_metadata = ["type", "job_title", "company"]
        
        for i, doc in enumerate(documents):
            # 检查内容
            if not doc.page_content or not doc.page_content.strip():
                validation_result["empty_documents"] += 1
                validation_result["issues"].append(f"文档 {i} 内容为空")
                continue
            
            # 检查元数据
            missing_fields = [
                field for field in required_metadata 
                if field not in doc.metadata
            ]
            
            if missing_fields:
                validation_result["missing_metadata"] += 1
                validation_result["issues"].append(
                    f"文档 {i} 缺少元数据字段: {missing_fields}"
                )
            else:
                validation_result["valid_documents"] += 1
        
        validation_result["quality_score"] = (
            validation_result["valid_documents"] / max(len(documents), 1)
        )
        
        return validation_result