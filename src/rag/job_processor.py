"""
LangChain职位处理器

基于LangChain的职位数据处理器，负责职位信息的结构化提取和文档创建。
"""

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)


class JobStructure(BaseModel):
    """职位结构化数据模型"""
    job_title: str = Field(description="职位名称")
    company: str = Field(description="公司名称")
    responsibilities: List[str] = Field(description="岗位职责列表")
    requirements: List[str] = Field(description="人员要求列表")
    skills: List[str] = Field(description="技能要求列表")
    education: str = Field(description="学历要求")
    experience: str = Field(description="经验要求")
    salary_min: Optional[int] = Field(description="最低薪资", default=None)
    salary_max: Optional[int] = Field(description="最高薪资", default=None)
    location: Optional[str] = Field(description="工作地点", default=None)
    company_size: Optional[str] = Field(description="公司规模", default=None)


class LangChainJobProcessor:
    """基于LangChain的职位数据处理器"""
    
    def __init__(self, llm_model: str = "gpt-3.5-turbo", config: Dict = None):
        """
        初始化职位处理器
        
        Args:
            llm_model: LLM模型名称
            config: 配置字典
        """
        self.config = config or {}
        
        # 初始化LLM
        self.llm = OpenAI(
            model_name=llm_model,
            temperature=self.config.get('temperature', 0.1),
            max_tokens=self.config.get('max_tokens', 2000)
        )
        
        # 初始化输出解析器
        self.output_parser = PydanticOutputParser(pydantic_object=JobStructure)
        
        # 构建结构化提取链
        self.extraction_chain = self._build_extraction_chain()
        
        # 初始化语义分割器
        self.semantic_splitter = self._build_semantic_splitter()
        
        logger.info(f"LangChain职位处理器初始化完成，使用模型: {llm_model}")
    
    def _build_extraction_chain(self) -> LLMChain:
        """构建结构化提取链"""
        
        prompt_template = """
你是专业的HR数据分析师。请分析以下职位描述，将其结构化提取。

职位文本：
{job_text}

提取要求：
1. 准确分离岗位职责和人员要求
2. 提取所有技能关键词
3. 识别学历和经验要求
4. 提取薪资范围和工作地点
5. 确保信息完整且不重复

{format_instructions}

结构化输出：
"""
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["job_text"],
            partial_variables={"format_instructions": self.output_parser.get_format_instructions()}
        )
        
        return LLMChain(
            llm=self.llm,
            prompt=prompt,
            output_parser=self.output_parser
        )
    
    def _build_semantic_splitter(self) -> RecursiveCharacterTextSplitter:
        """构建语义分割器"""
        
        separators = self.config.get('separators', [
            "\n岗位职责：", "\n人员要求：", "\n任职要求：", 
            "\n工作职责：", "\n职位要求：", "\n招聘要求：",
            "\n\n",  # 段落分割
            "\n",    # 行分割
            "。",    # 句子分割
        ])
        
        return RecursiveCharacterTextSplitter(
            separators=separators,
            chunk_size=self.config.get('chunk_size', 500),
            chunk_overlap=self.config.get('chunk_overlap', 50),
            length_function=len,
            is_separator_regex=False,
        )
    
    async def process_job_data(self, job_json: Dict) -> JobStructure:
        """
        处理职位数据
        
        Args:
            job_json: 职位JSON数据
            
        Returns:
            JobStructure: 结构化的职位信息
        """
        try:
            # 提取原始文本
            job_text = self._extract_job_text(job_json)
            
            # 使用LLM结构化提取
            result = await self.extraction_chain.arun(job_text=job_text)
            
            logger.info(f"成功提取职位信息: {result.job_title}")
            return result
            
        except Exception as e:
            logger.error(f"LLM提取失败，使用备用方案: {e}")
            return self._fallback_extraction(job_json)
    
    def _extract_job_text(self, job_json: Dict) -> str:
        """从JSON中提取职位文本"""
        text_fields = ['description', 'requirements', 'content', 'detail']
        
        for field in text_fields:
            if field in job_json and job_json[field]:
                return str(job_json[field])
        
        # 如果没有找到标准字段，尝试合并所有文本字段
        text_parts = []
        for key, value in job_json.items():
            if isinstance(value, str) and len(value) > 20:
                text_parts.append(value)
        
        return '\n'.join(text_parts) if text_parts else str(job_json)
    
    def _fallback_extraction(self, job_json: Dict) -> JobStructure:
        """备用提取方案"""
        return JobStructure(
            job_title=job_json.get('title', '未知职位'),
            company=job_json.get('company', '未知公司'),
            responsibilities=[],
            requirements=[],
            skills=[],
            education='不限',
            experience='不限',
            location=job_json.get('location'),
            salary_min=job_json.get('salary_min'),
            salary_max=job_json.get('salary_max')
        )
    
    def create_documents(self, job_structure: JobStructure) -> List[Document]:
        """
        创建LangChain文档对象
        
        Args:
            job_structure: 结构化职位信息
            
        Returns:
            List[Document]: 文档列表
        """
        documents = []
        
        # 职位概览文档
        overview_doc = Document(
            page_content=f"职位：{job_structure.job_title}，公司：{job_structure.company}",
            metadata={
                "type": "overview",
                "job_title": job_structure.job_title,
                "company": job_structure.company,
                "location": job_structure.location,
                "salary_min": job_structure.salary_min,
                "salary_max": job_structure.salary_max
            }
        )
        documents.append(overview_doc)
        
        # 职责文档
        for i, responsibility in enumerate(job_structure.responsibilities):
            resp_doc = Document(
                page_content=responsibility,
                metadata={
                    "type": "responsibility",
                    "index": i,
                    "job_title": job_structure.job_title,
                    "company": job_structure.company
                }
            )
            documents.append(resp_doc)
        
        # 要求文档
        for i, requirement in enumerate(job_structure.requirements):
            req_doc = Document(
                page_content=requirement,
                metadata={
                    "type": "requirement", 
                    "index": i,
                    "job_title": job_structure.job_title,
                    "company": job_structure.company
                }
            )
            documents.append(req_doc)
        
        # 技能文档
        if job_structure.skills:
            skills_doc = Document(
                page_content=f"技能要求：{', '.join(job_structure.skills)}",
                metadata={
                    "type": "skills",
                    "skills": job_structure.skills,
                    "job_title": job_structure.job_title,
                    "company": job_structure.company
                }
            )
            documents.append(skills_doc)
        
        # 基本要求文档
        basic_req_content = f"学历要求：{job_structure.education}，经验要求：{job_structure.experience}"
        basic_req_doc = Document(
            page_content=basic_req_content,
            metadata={
                "type": "basic_requirements",
                "education": job_structure.education,
                "experience": job_structure.experience,
                "job_title": job_structure.job_title,
                "company": job_structure.company
            }
        )
        documents.append(basic_req_doc)
        
        logger.info(f"为职位 {job_structure.job_title} 创建了 {len(documents)} 个文档")
        return documents
    
    def split_text_semantically(self, text: str) -> List[str]:
        """
        语义分割文本
        
        Args:
            text: 待分割的文本
            
        Returns:
            List[str]: 分割后的文本块
        """
        return self.semantic_splitter.split_text(text)