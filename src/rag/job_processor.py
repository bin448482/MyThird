"""
LangChain职位处理器

基于LangChain的职位数据处理器，负责职位信息的结构化提取和文档创建。
"""

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import json
import logging
from .llm_factory import create_llm

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
    
    def __init__(self, llm_config: Dict = None, config: Dict = None):
        """
        初始化职位处理器
        
        Args:
            llm_config: LLM配置字典，包含provider、api_key等
            config: 其他配置字典
        """
        self.config = config or {}
        self.llm_config = llm_config or {}
        
        # 获取LLM提供商和配置
        provider = self.llm_config.get('provider', 'zhipu')
        
        # 初始化LLM
        self.llm = create_llm(
            provider=provider,
            model=self.llm_config.get('model', 'glm-4-flash' if provider == 'zhipu' else 'gpt-3.5-turbo'),
            temperature=self.llm_config.get('temperature', 0.1),
            max_tokens=self.llm_config.get('max_tokens', 2000),
            **{k: v for k, v in self.llm_config.items() if k not in ['provider', 'model', 'temperature', 'max_tokens']}
        )
        
        # 构建结构化提取链
        self.extraction_chain = self._build_extraction_chain()
        
        # 初始化语义分割器
        self.semantic_splitter = self._build_semantic_splitter()
        
        logger.info(f"LangChain职位处理器初始化完成，使用提供商: {provider}")
    
    def _build_extraction_chain(self):
        """构建结构化提取链"""
        
        prompt_template = """
你是专业的HR数据分析师。请分析以下职位描述，将其结构化提取为JSON格式。

职位文本：
{job_text}

请严格按照以下JSON格式输出，不要包含任何其他内容：

{{
    "job_title": "从职位标题中提取的职位名称",
    "company": "从职位信息中提取的公司名称",
    "responsibilities": ["职责1", "职责2", "职责3"],
    "requirements": ["要求1", "要求2", "要求3"],
    "skills": ["技能1", "技能2", "技能3"],
    "education": "学历要求",
    "experience": "经验要求",
    "salary_min": 最低薪资数字或null,
    "salary_max": 最高薪资数字或null,
    "location": "工作地点或null",
    "company_size": "公司规模或null"
}}

提取要求：
1. 职位名称提取：
   - 如果文本中包含"【职位名称_职位招聘_公司名称】"格式，提取其中的职位名称
   - 如果包含"上海AI工程师"等格式，提取"AI工程师"作为职位名称
   - 优先从页面标题或明显的职位标识中提取
2. 从岗位职责部分提取responsibilities
3. 从人员要求部分提取requirements
4. 识别所有技术技能关键词
5. 提取学历和工作经验要求
6. 如果有薪资信息，提取数字部分
7. 只输出JSON，不要其他解释文字

JSON输出：
"""
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["job_text"]
        )
        
        # 使用新的LangChain API
        return prompt | self.llm | StrOutputParser()
    
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
            llm_result = await self.extraction_chain.ainvoke({"job_text": job_text})
            
            # 解析LLM返回的JSON
            parsed_result = self._parse_llm_result(llm_result)
            
            # 创建JobStructure对象
            job_structure = JobStructure(**parsed_result)
            
            logger.info(f"成功提取职位信息: {job_structure.job_title}")
            return job_structure
            
        except Exception as e:
            logger.error(f"LLM提取失败，使用备用方案: {e}")
            return self._fallback_extraction(job_json)
    
    def _parse_llm_result(self, llm_result: str) -> Dict:
        """
        解析LLM返回的结果
        
        Args:
            llm_result: LLM返回的字符串
            
        Returns:
            Dict: 解析后的字典
        """
        try:
            # 清理结果字符串
            cleaned_result = llm_result.strip()
            
            # 如果结果包含```json标记，提取JSON部分
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
            
            # 尝试解析JSON
            parsed = json.loads(cleaned_result)
            
            # 验证必需字段
            required_fields = ["job_title", "company", "responsibilities", "requirements", "skills", "education", "experience"]
            for field in required_fields:
                if field not in parsed:
                    parsed[field] = [] if field in ["responsibilities", "requirements", "skills"] else "不限"
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 原始结果: {llm_result[:200]}...")
            raise ValueError(f"无法解析LLM返回的JSON: {e}")
        except Exception as e:
            logger.error(f"结果解析失败: {e}")
            raise ValueError(f"结果解析错误: {e}")
    
    def _extract_job_text(self, job_json: Dict) -> str:
        """从JSON中提取职位文本"""
        text_parts = []
        
        # 优先添加page_title，因为它包含职位名称
        if 'page_title' in job_json and job_json['page_title']:
            text_parts.append(f"页面标题: {job_json['page_title']}")
        
        # 添加主要内容字段
        main_fields = ['description', 'requirements', 'content', 'detail']
        for field in main_fields:
            if field in job_json and job_json[field]:
                text_parts.append(f"{field}: {job_json[field]}")
        
        # 如果还没有足够内容，添加其他有用字段
        if len(text_parts) < 2:
            other_fields = ['url', 'company_info', 'benefits']
            for field in other_fields:
                if field in job_json and job_json[field] and len(str(job_json[field])) > 10:
                    text_parts.append(f"{field}: {job_json[field]}")
        
        # 如果仍然没有内容，合并所有文本字段
        if not text_parts:
            for key, value in job_json.items():
                if isinstance(value, str) and len(value) > 20:
                    text_parts.append(f"{key}: {value}")
        
        return '\n\n'.join(text_parts) if text_parts else str(job_json)
    
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