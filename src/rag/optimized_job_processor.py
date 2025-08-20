"""
优化的职位处理器 - 混合处理模式

基于数据库记录的优化处理器，直接映射基本字段，只对复杂字段使用LLM处理
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
from .job_processor import JobStructure

logger = logging.getLogger(__name__)


class OptimizedJobProcessor:
    """优化的职位处理器 - 混合处理模式"""
    
    def __init__(self, llm_config: Dict = None, config: Dict = None):
        """
        初始化优化职位处理器
        
        Args:
            llm_config: LLM配置字典
            config: 其他配置字典
        """
        self.config = config or {}
        self.llm_config = llm_config or {}
        
        # 初始化LLM
        provider = self.llm_config.get('provider', 'zhipu')
        self.llm = create_llm(
            provider=provider,
            model=self.llm_config.get('model', 'glm-4-flash'),
            temperature=self.llm_config.get('temperature', 0.1),
            max_tokens=self.llm_config.get('max_tokens', 1500),
            **{k: v for k, v in self.llm_config.items() if k not in ['provider', 'model', 'temperature', 'max_tokens']}
        )
        
        # 构建智能提取链
        self.smart_extraction_chain = self._build_smart_extraction_chain()
        
        # 初始化语义分割器
        self.semantic_splitter = self._build_semantic_splitter()
        
        logger.info(f"优化职位处理器初始化完成，使用提供商: {provider}")
    
    def _build_smart_extraction_chain(self):
        """构建智能提取链 - 只处理复杂字段"""
        
        prompt_template = """
你是专业的HR数据分析师。请分析以下职位信息，提取岗位职责、人员要求、技能要求和薪资信息。

薪资信息：{salary_text}
职位描述：{description_text}
职位要求：{requirements_text}

请严格按照以下JSON格式输出，不要包含任何其他内容：

{{
    "responsibilities": ["职责1", "职责2", "职责3"],
    "requirements": ["要求1", "要求2", "要求3"],
    "skills": ["技能1", "技能2", "技能3"],
    "salary_min": 最低薪资数字或null,
    "salary_max": 最高薪资数字或null
}}

提取要求：
1. 从职位描述中提取岗位职责到responsibilities数组
2. 从职位要求中提取人员要求到requirements数组
3. 识别所有技术技能、工具、编程语言等到skills数组
4. 从薪资文本中提取数字范围：
   - "10k-15k" → salary_min: 10000, salary_max: 15000
   - "面议" → salary_min: null, salary_max: null
   - "15000以上" → salary_min: 15000, salary_max: null
   - "8000-12000元/月" → salary_min: 8000, salary_max: 12000
   - "8千-1.5万·13薪" → salary_min: 8000, salary_max: 15000
5. 每个数组包含3-8个具体明确的条目
6. 只输出JSON，不要其他解释文字

JSON输出：
"""
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["salary_text", "description_text", "requirements_text"]
        )
        
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
    
    async def process_database_job(self, db_record: Dict) -> JobStructure:
        """
        处理数据库职位记录 - 混合处理模式
        
        Args:
            db_record: 数据库记录（包含jobs和job_details的合并数据）
            
        Returns:
            JobStructure: 结构化的职位信息
        """
        try:
            # 1. 直接映射基本字段（无需LLM处理）
            job_data = {
                'job_title': db_record.get('title', ''),
                'company': db_record.get('company', ''),
                'location': db_record.get('location', ''),
                'education': db_record.get('education', '不限'),
                'experience': db_record.get('experience', '不限'),
                'company_size': db_record.get('company_scale', ''),
            }
            
            # 2. 使用LLM处理需要智能解析的复杂字段
            llm_result = await self.smart_extraction_chain.ainvoke({
                "salary_text": db_record.get('salary', ''),
                "description_text": db_record.get('description', ''),
                "requirements_text": db_record.get('requirements', '')
            })
            
            # 3. 解析LLM结果并合并
            extracted_data = self._parse_llm_result(llm_result)
            job_data.update(extracted_data)
            
            # 4. 创建JobStructure对象
            job_structure = JobStructure(**job_data)
            
            logger.info(f"成功处理职位: {job_structure.job_title} - {job_structure.company}")
            return job_structure
            
        except Exception as e:
            logger.error(f"处理职位失败，使用备用方案: {e}")
            return self._fallback_extraction_from_db(db_record)
    
    def _parse_llm_result(self, llm_result: str) -> Dict:
        """解析LLM返回的结果"""
        try:
            # 清理结果字符串
            cleaned_result = llm_result.strip()
            
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
            
            # 解析JSON
            parsed = json.loads(cleaned_result)
            
            # 验证和清理字段
            result = {
                'responsibilities': parsed.get('responsibilities', []),
                'requirements': parsed.get('requirements', []),
                'skills': parsed.get('skills', []),
                'salary_min': parsed.get('salary_min'),
                'salary_max': parsed.get('salary_max')
            }
            
            # 确保列表字段都是列表
            for key in ['responsibilities', 'requirements', 'skills']:
                if not isinstance(result[key], list):
                    result[key] = []
            
            # 确保薪资字段是数字或None
            for key in ['salary_min', 'salary_max']:
                if result[key] is not None:
                    try:
                        result[key] = int(result[key])
                    except (ValueError, TypeError):
                        result[key] = None
            
            return result
            
        except Exception as e:
            logger.error(f"LLM结果解析失败: {e}")
            return {
                'responsibilities': [],
                'requirements': [],
                'skills': [],
                'salary_min': None,
                'salary_max': None
            }
    
    def _fallback_extraction_from_db(self, db_record: Dict) -> JobStructure:
        """从数据库记录的备用提取方案"""
        return JobStructure(
            job_title=db_record.get('title', '未知职位'),
            company=db_record.get('company', '未知公司'),
            location=db_record.get('location'),
            education=db_record.get('education', '不限'),
            experience=db_record.get('experience', '不限'),
            company_size=db_record.get('company_scale'),
            responsibilities=[],
            requirements=[],
            skills=[],
            salary_min=None,
            salary_max=None
        )
    
    def create_documents(self, job_structure: JobStructure, job_id: str = None, job_url: str = None) -> List[Document]:
        """
        创建LangChain文档对象
        
        Args:
            job_structure: 结构化职位信息
            job_id: 职位ID
            job_url: 职位URL
            
        Returns:
            List[Document]: 文档列表
        """
        documents = []
        
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
            "company_size": job_structure.company_size,
            "job_url": job_url
        }
        
        # 1. 职位概览文档
        overview_content = f"""职位：{job_structure.job_title}
公司：{job_structure.company}
地点：{job_structure.location or '不限'}
薪资：{self._format_salary(job_structure.salary_min, job_structure.salary_max)}
学历：{job_structure.education}
经验：{job_structure.experience}
公司规模：{job_structure.company_size or '未知'}"""
        
        overview_doc = Document(
            page_content=overview_content,
            metadata={**base_metadata, "type": "overview"}
        )
        documents.append(overview_doc)
        
        # 2. 职责文档
        if job_structure.responsibilities:
            for i, responsibility in enumerate(job_structure.responsibilities):
                resp_doc = Document(
                    page_content=f"岗位职责：{responsibility}",
                    metadata={**base_metadata, "type": "responsibility", "index": i}
                )
                documents.append(resp_doc)
        
        # 3. 要求文档
        if job_structure.requirements:
            for i, requirement in enumerate(job_structure.requirements):
                req_doc = Document(
                    page_content=f"人员要求：{requirement}",
                    metadata={**base_metadata, "type": "requirement", "index": i}
                )
                documents.append(req_doc)
        
        # 4. 技能文档
        if job_structure.skills:
            skills_content = f"技能要求：{', '.join(job_structure.skills)}"
            skills_doc = Document(
                page_content=skills_content,
                metadata={**base_metadata, "type": "skills", "skills": job_structure.skills}
            )
            documents.append(skills_doc)
        
        # 5. 基本要求文档
        basic_req_content = f"基本要求 - 学历：{job_structure.education}，经验：{job_structure.experience}"
        basic_req_doc = Document(
            page_content=basic_req_content,
            metadata={**base_metadata, "type": "basic_requirements"}
        )
        documents.append(basic_req_doc)
        
        logger.info(f"为职位 {job_structure.job_title} 创建了 {len(documents)} 个文档")
        return documents
    
    def _format_salary(self, salary_min: Optional[int], salary_max: Optional[int]) -> str:
        """格式化薪资显示"""
        if salary_min and salary_max:
            return f"{salary_min}-{salary_max}元"
        elif salary_min:
            return f"{salary_min}元以上"
        elif salary_max:
            return f"{salary_max}元以下"
        else:
            return "面议"
    
    def split_text_semantically(self, text: str) -> List[str]:
        """
        语义分割文本
        
        Args:
            text: 待分割的文本
            
        Returns:
            List[str]: 分割后的文本块
        """
        return self.semantic_splitter.split_text(text)
    
    def validate_job_structure(self, job_structure: JobStructure) -> bool:
        """
        验证职位结构完整性
        
        Args:
            job_structure: 职位结构
            
        Returns:
            是否有效
        """
        # 检查必需字段
        if not job_structure.job_title or not job_structure.company:
            return False
        
        # 检查是否有有效的内容
        has_content = (
            len(job_structure.responsibilities) > 0 or
            len(job_structure.requirements) > 0 or
            len(job_structure.skills) > 0
        )
        
        return has_content
    
    def get_processing_stats(self, job_structure: JobStructure) -> Dict:
        """
        获取处理统计信息
        
        Args:
            job_structure: 职位结构
            
        Returns:
            处理统计信息
        """
        return {
            'job_title': job_structure.job_title,
            'company': job_structure.company,
            'responsibilities_count': len(job_structure.responsibilities),
            'requirements_count': len(job_structure.requirements),
            'skills_count': len(job_structure.skills),
            'has_salary': job_structure.salary_min is not None or job_structure.salary_max is not None,
            'has_location': job_structure.location is not None,
            'processing_mode': 'hybrid'  # 混合处理模式
        }