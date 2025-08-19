# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

这是一个基于Python的智能简历投递系统，集成了LangChain RAG技术进行职位信息智能分析。系统支持智联招聘、前程无忧、Boss直聘等主流招聘网站，使用Selenium进行网页自动化，采用人工登录后自动化操作的方式。核心特色是基于LangChain的RAG（检索增强生成）引擎，能够对职位信息进行深度结构化分析、向量化存储和智能匹配，大幅提升简历投递的精准度和效率。

## Technology Stack

- **核心语言**: Python 3.8+
- **网页自动化**: Selenium WebDriver
- **AI分析**: LangChain + OpenAI/本地LLM
- **RAG引擎**: LangChain RAG + ChromaDB向量数据库
- **向量嵌入**: sentence-transformers (多语言支持)
- **文档处理**: LangChain TextSplitter + Document Loaders
- **数据库**: SQLite (结构化数据) + ChromaDB (向量数据)
- **配置管理**: YAML/JSON
- **命令行界面**: Click/argparse
- **日志**: Python logging
- **测试**: pytest

## Getting Started

When setting up this project:

1. Initialize version control: `git init`
2. Install Python dependencies: `pip install -r requirements.txt`
3. Configure settings in `config/config.yaml`
4. Run the tool: `python src/main.py --website zhilian`

## Development Commands

```bash
# 安装依赖
pip install -r requirements.txt

# 运行工具
python src/main.py --website zhilian

# 运行测试
pytest tests/

# 生成需求文件
pip freeze > requirements.txt
```

## Architecture

### 系统架构图

```mermaid
graph TB
    CLI[命令行界面] --> Core[核心控制器]
    Config[配置管理] --> Core
    
    Core --> Crawler[爬虫引擎]
    Core --> RAGAnalyzer[RAG智能分析器]
    Core --> Matcher[智能匹配引擎]
    Core --> Submitter[投递引擎]
    
    Crawler --> WebDriver[Selenium WebDriver]
    Crawler --> AntiBot[防反爬机制]
    Submitter --> WebDriver
    
    RAGAnalyzer --> JobProcessor[LangChain职位处理器]
    JobProcessor --> TextSplitter[智能文本分割器]
    JobProcessor --> StructureExtractor[结构化提取链]
    JobProcessor --> DocumentCreator[文档创建器]
    
    RAGAnalyzer --> VectorStore[ChromaDB向量存储]
    VectorStore --> Embeddings[多语言嵌入模型]
    VectorStore --> Retriever[压缩检索器]
    
    RAGAnalyzer --> RAGChain[检索问答链]
    RAGChain --> LLM[大语言模型]
    RAGChain --> QAPrompts[问答提示词模板]
    
    Matcher --> Resume[简历数据]
    Matcher --> VectorStore
    Matcher --> SemanticSearch[语义相似度搜索]
    
    Core --> Database[SQLite数据库]
    Core --> VectorStore
    Core --> Logger[日志系统]
    
    Adapters[网站适配器] --> Crawler
    Adapters --> Submitter
    
    HumanLogin[人工登录] --> WebDriver
    
    subgraph "RAG核心组件"
        JobProcessor
        VectorStore
        RAGChain
        SemanticSearch
    end
```

### 模块架构

#### 1. 核心控制器 (Core Controller)
- **职责**: 协调各个模块，控制整体流程
- **主要功能**: 初始化组件、控制爬取流程、异常处理、状态管理

#### 2. 网站适配器 (Website Adapters)
- **职责**: 为不同招聘网站提供统一接口
- **设计模式**: 策略模式 + 工厂模式
- **支持网站**: 智联招聘、前程无忧、Boss直聘

#### 3. 爬虫引擎 (Crawler Engine)
- **职责**: 基于Selenium执行网页自动化操作，包含会话管理
- **主要功能**: 启动浏览器、等待人工登录、检测登录状态、页面导航、数据提取

#### 4. RAG智能分析器 (RAG Analyzer)
- **职责**: 基于LangChain RAG技术进行职位信息深度分析
- **核心组件**:
  - **LangChain职位处理器**: 使用LLM进行结构化提取
  - **智能文本分割器**: 语义级别的文本分割
  - **向量嵌入引擎**: 多语言职位信息向量化
  - **ChromaDB存储**: 高效的向量数据库存储
- **主要功能**:
  - 职位描述智能结构化（职责、要求、技能分离）
  - 语义级技能标签提取和分类
  - 薪资范围智能解析
  - 职位信息向量化存储
  - 基于语义的相似职位检索

#### 5. 智能匹配引擎 (Smart Matching Engine)
- **职责**: 基于RAG技术进行简历与职位的智能匹配
- **核心技术**:
  - **语义相似度匹配**: 基于向量嵌入的深度语义理解
  - **RAG检索增强**: 利用历史匹配数据优化匹配算法
  - **多维度评分**: 综合技能、经验、薪资等多个维度
- **匹配维度**:
  - 技能语义匹配(50%): 基于向量相似度的技能匹配
  - 工作经验匹配(30%): 经验年限和项目经历匹配
  - 薪资范围匹配(20%): 期望薪资与职位薪资的匹配度
- **增强功能**:
  - 职位推荐: 基于用户画像推荐相似职位
  - 匹配解释: 提供详细的匹配原因分析
  - 学习优化: 根据投递反馈持续优化匹配算法

#### 6. 投递引擎 (Submission Engine)
- **职责**: 执行简历投递操作
- **主要功能**: 定位投递按钮、模拟点击投递、状态确认

### 项目目录结构

```
resume_auto_submitter/
├── src/
│   ├── main.py                 # 主入口
│   ├── core/
│   │   ├── controller.py       # 核心控制器
│   │   ├── config.py          # 配置管理
│   │   └── exceptions.py      # 自定义异常
│   ├── adapters/
│   │   ├── base.py            # 基础适配器
│   │   ├── zhilian.py         # 智联招聘适配器
│   │   ├── qiancheng.py       # 前程无忧适配器
│   │   └── boss.py            # Boss直聘适配器
│   ├── crawler/
│   │   ├── engine.py          # 爬虫引擎
│   │   ├── anti_bot.py        # 防反爬机制
│   │   └── selenium_utils.py   # Selenium工具函数
│   ├── rag/                   # RAG智能分析模块
│   │   ├── __init__.py
│   │   ├── job_processor.py   # LangChain职位处理器
│   │   ├── vector_manager.py  # ChromaDB向量存储管理
│   │   ├── rag_chain.py       # RAG检索问答链
│   │   ├── document_creator.py # 文档创建器
│   │   └── semantic_search.py # 语义搜索引擎
│   ├── analyzer/
│   │   ├── rag_analyzer.py    # RAG智能分析器
│   │   ├── prompts.py         # LangChain提示词模板
│   │   └── llm_client.py      # LLM客户端
│   ├── matcher/
│   │   ├── smart_matching.py  # 智能匹配引擎
│   │   ├── semantic_scorer.py # 语义评分算法
│   │   └── recommendation.py  # 职位推荐引擎
│   ├── submitter/
│   │   └── submission_engine.py # 投递引擎
│   ├── database/
│   │   ├── models.py          # 数据模型
│   │   ├── operations.py      # 数据库操作
│   │   └── vector_ops.py      # 向量数据库操作
│   ├── cli/
│   │   ├── commands.py        # 命令行命令
│   │   └── utils.py           # CLI工具函数
│   └── utils/
│       ├── logger.py          # 日志工具
## 🚀 LangChain RAG智能分析系统

### RAG系统架构设计

基于LangChain的RAG（检索增强生成）系统是本项目的核心智能引擎，负责职位信息的深度分析、向量化存储和智能匹配。

```mermaid
graph TD
    A[职位JSON数据] --> B[LangChain文档加载器]
    B --> C[LLM语义分割器]
    C --> D[结构化提取链]
    D --> E[向量嵌入]
    E --> F[ChromaDB存储]
    
    G[用户查询] --> H[检索链]
    H --> I[重排序]
    I --> J[生成回答]
    
    F --> H
    
    subgraph "LangChain组件"
        K[TextSplitter]
        L[LLMChain]
        M[VectorStore]
        N[RetrievalQA]
    end
```

### 核心组件实现

#### 1. LangChain职位处理器 (JobProcessor)

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List, Dict

class JobStructure(BaseModel):
    """职位结构化数据模型"""
    job_title: str = Field(description="职位名称")
    company: str = Field(description="公司名称")
    responsibilities: List[str] = Field(description="岗位职责列表")
    requirements: List[str] = Field(description="人员要求列表")
    skills: List[str] = Field(description="技能要求列表")
    education: str = Field(description="学历要求")
    experience: str = Field(description="经验要求")

class LangChainJobProcessor:
    """基于LangChain的职位数据处理器"""
    
    def __init__(self, llm_model="gpt-3.5-turbo"):
        self.llm = OpenAI(model_name=llm_model, temperature=0.1)
        self.output_parser = PydanticOutputParser(pydantic_object=JobStructure)
        self.extraction_chain = self._build_extraction_chain()
        self.semantic_splitter = self._build_semantic_splitter()
    
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
4. 确保信息完整且不重复

{format_instructions}

结构化输出：
"""
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["job_text"],
            partial_variables={"format_instructions": self.output_parser.get_format_instructions()}
        )
        
        return LLMChain(llm=self.llm, prompt=prompt, output_parser=self.output_parser)
```

#### 2. ChromaDB向量存储管理器

```python
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor

class ChromaDBManager:
    """ChromaDB向量存储管理器"""
    
    def __init__(self, persist_directory="./chroma_db"):
        # 初始化中文嵌入模型
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # 初始化ChromaDB
        self.vectorstore = Chroma(
            persist_directory=persist_directory,
            embedding_function=self.embeddings,
            collection_name="job_positions"
        )
        
        # 初始化压缩检索器
        self.compressor = LLMChainExtractor.from_llm(OpenAI(temperature=0))
        self.compression_retriever = ContextualCompressionRetriever(
            base_compressor=self.compressor,
            base_retriever=self.vectorstore.as_retriever(search_kwargs={"k": 10})
        )
    
    def add_job_documents(self, documents: List[Document]) -> List[str]:
        """添加职位文档到向量数据库"""
        doc_ids = self.vectorstore.add_documents(documents)
        self.vectorstore.persist()
        return doc_ids
    
    def search_similar_jobs(self, query: str, k: int = 5) -> List[Document]:
        """搜索相似职位"""
        compressed_docs = self.compression_retriever.get_relevant_documents(query)
        return compressed_docs[:k]
```

#### 3. RAG检索问答链

```python
from langchain.chains import RetrievalQA
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate

class JobRAGSystem:
    """职位信息RAG系统"""
    
    def __init__(self, vectorstore_manager: ChromaDBManager):
        self.vectorstore_manager = vectorstore_manager
        self.llm = OpenAI(temperature=0.2)
        
        # 构建检索QA链
        self.retrieval_qa = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=vectorstore_manager.vectorstore.as_retriever(search_kwargs={"k": 5}),
            return_source_documents=True,
            chain_type_kwargs={"prompt": self._build_qa_prompt()}
        )
    
    def _build_qa_prompt(self) -> PromptTemplate:
        """构建问答Prompt"""
        template = """
你是专业的职位匹配顾问。基于以下职位信息回答用户问题。

职位信息：
{context}

用户问题：{question}

回答要求：
1. 基于提供的职位信息回答
2. 如果信息不足，明确说明
3. 提供具体的职位匹配建议
4. 回答要专业且有帮助

回答：
"""
        
        return PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )
    
    async def ask_question(self, question: str, filters: Dict = None) -> Dict:
        """问答接口"""
        relevant_docs = self.vectorstore_manager.hybrid_search(question, filters)
        
        result = await self.retrieval_qa.arun(
            query=question,
            source_documents=relevant_docs
        )
        
        return {
            "answer": result["result"],
            "source_documents": [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata
                }
                for doc in result["source_documents"]
            ]
        }
```

#### 4. 完整的RAG处理流程

```python
class JobRAGPipeline:
    """完整的职位RAG处理流程"""
    
    def __init__(self):
        self.processor = LangChainJobProcessor()
        self.vectorstore_manager = ChromaDBManager()
        self.rag_system = JobRAGSystem(self.vectorstore_manager)
    
    async def process_and_store_job(self, job_json: Dict) -> str:
        """处理并存储职位信息"""
        
        # 1. 结构化提取
        job_structure = await self.processor.process_job_data(job_json)
        
        # 2. 创建文档
        documents = self.processor.create_documents(job_structure)
        
        # 3. 存储到向量数据库
        doc_ids = self.vectorstore_manager.add_job_documents(documents)
        
        return job_structure.job_title
    
    async def query_jobs(self, question: str) -> Dict:
        """查询职位信息"""
        return await self.rag_system.ask_question(question)
    
    async def match_jobs(self, user_profile: str) -> List[Dict]:
        """职位匹配"""
        return await self.rag_system.find_matching_jobs(user_profile)
```

### RAG系统优势

#### 1. 智能文本处理
- **语义分割**: 基于职位内容结构的智能分割
- **结构化提取**: LLM驱动的精确信息提取
- **多语言支持**: 支持中英文混合职位描述

#### 2. 向量化存储
- **高效检索**: ChromaDB提供毫秒级向量检索
- **语义理解**: 基于语义相似度的职位匹配
- **持久化存储**: 支持数据持久化和增量更新

#### 3. 智能问答
- **上下文理解**: 基于检索到的职位信息回答问题
- **匹配解释**: 提供详细的匹配原因分析
- **个性化推荐**: 根据用户画像推荐合适职位

#### 4. 可扩展架构
- **模块化设计**: 各组件可独立升级和替换
- **多模型支持**: 支持不同的LLM和嵌入模型
- **灵活配置**: 通过配置文件调整RAG参数

│       └── helpers.py         # 辅助函数
├── config/
│   ├── config.yaml            # 主配置文件
│   ├── config.example.yaml    # 配置示例
│   └── prompts/
│       ├── job_analysis.txt   # 职位分析提示词
│       ├── matching.txt       # 匹配分析提示词
│       ├── rag_extraction.txt # RAG结构化提取提示词
│       └── qa_template.txt    # 问答模板提示词
├── data/                      # 数据库文件
├── chroma_db/                 # ChromaDB向量数据库
├── logs/                      # 日志文件
├── tests/                     # 测试文件
├── docs/                      # 文档
├── requirements.txt
└── README.md
```

### RAG增强的数据库设计

#### 职位信息表 (jobs) - 扩展版
```sql
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(100) UNIQUE NOT NULL,  -- 职位唯一标识
    title VARCHAR(200) NOT NULL,          -- 职位标题
    company VARCHAR(200) NOT NULL,        -- 公司名称
    url VARCHAR(500) NOT NULL,            -- 职位详情页URL
    application_status VARCHAR(50) DEFAULT 'pending',  -- 投递状态
    match_score FLOAT,                     -- 传统匹配度评分
    semantic_score FLOAT,                  -- RAG语义匹配度评分
    vector_id VARCHAR(100),                -- ChromaDB向量ID
    structured_data TEXT,                  -- JSON格式的结构化数据
    website VARCHAR(50) NOT NULL,         -- 来源网站
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    submitted_at TIMESTAMP,               -- 投递时间
    rag_processed BOOLEAN DEFAULT FALSE   -- 是否已进行RAG处理
);
```

#### 向量匹配记录表 (vector_matches)
```sql
CREATE TABLE vector_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(100) NOT NULL,
    user_query TEXT NOT NULL,
    similarity_score FLOAT NOT NULL,
    matched_content TEXT,
    match_type VARCHAR(50),  -- 'skill', 'responsibility', 'requirement'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);
```

### 数据库设计

#### 职位信息表 (jobs)
```sql
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(100) UNIQUE NOT NULL,  -- 职位唯一标识
    title VARCHAR(200) NOT NULL,          -- 职位标题
    company VARCHAR(200) NOT NULL,        -- 公司名称
    url VARCHAR(500) NOT NULL,            -- 职位详情页URL
    application_status VARCHAR(50) DEFAULT 'pending',  -- 投递状态
    match_score FLOAT,                     -- 匹配度评分
    website VARCHAR(50) NOT NULL,         -- 来源网站
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    submitted_at TIMESTAMP                 -- 投递时间
);
```

### RAG增强的核心流程

1. **启动浏览器**: 打开指定招聘网站
2. **人工登录**: 等待用户手动完成登录
3. **自动爬取**: 获取职位列表，逐个分析
4. **RAG智能分析**:
   - 使用LangChain进行职位信息结构化提取
   - 创建语义文档并向量化存储到ChromaDB
   - 建立职位知识库，支持语义检索
5. **智能匹配评分**:
   - 基于向量相似度进行语义匹配
   - 结合RAG检索增强匹配精度
   - 生成详细的匹配分析报告
6. **自动投递**: 根据智能匹配度决定是否投递
7. **知识库更新**: 将职位信息和匹配结果存储到向量数据库
8. **记录保存**: 将结构化数据保存到SQLite，向量数据保存到ChromaDB

### RAG增强的配置示例

```yaml
# 基础配置
app:
  name: "Smart Resume Auto Submitter"
  version: "2.0.0"
  description: "基于LangChain RAG的智能简历投递系统"

# 网站配置
websites:
  zhilian:
    enabled: true
    base_url: "https://www.zhaopin.com"
    submit_button_selector: ".btn-apply"

# RAG系统配置
rag:
  # LLM配置
  llm:
    provider: "openai"  # openai, claude, local
    model: "gpt-3.5-turbo"
    temperature: 0.1
    max_tokens: 2000
    
  # 向量数据库配置
  vectorstore:
    provider: "chromadb"
    persist_directory: "./chroma_db"
    collection_name: "job_positions"
    
  # 嵌入模型配置
  embeddings:
    model_name: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    device: "cpu"
    normalize_embeddings: true
    
  # 文本分割配置
  text_splitter:
    chunk_size: 500
    chunk_overlap: 50
    separators: ["\n岗位职责：", "\n人员要求：", "\n任职要求：", "\n\n", "\n", "。"]
    
  # 检索配置
  retrieval:
    search_type: "similarity"
    k: 5
    score_threshold: 0.7
    use_compression: true

# 智能匹配算法配置
matching:
  # 传统权重配置
  traditional_weights:
    skills: 0.5
    experience: 0.3
    salary: 0.2
    
  # RAG增强权重配置
  rag_weights:
    semantic_similarity: 0.6  # 语义相似度
    traditional_score: 0.4    # 传统评分
    
  # 匹配阈值
  thresholds:
    auto_submit: 0.85         # RAG增强后提高阈值
    manual_review: 0.7
    skip: 0.4

# 简历配置
resume:
  skills: ["Python", "Java", "React", "Node.js", "LangChain", "RAG"]
  experience_years: 3
  expected_salary_min: 15000
  expected_salary_max: 25000
  preferred_locations: ["上海"]
  
  # 简历向量化配置
  profile_description: |
    具有3年Python开发经验，熟悉机器学习和LLM应用开发，
    有RAG系统构建经验，擅长使用LangChain进行AI应用开发。

# 提示词模板配置
prompts:
  job_extraction: "config/prompts/rag_extraction.txt"
  matching_analysis: "config/prompts/matching.txt"
  qa_template: "config/prompts/qa_template.txt"
```

## RAG增强的AI提示词模板

### RAG结构化提取提示词 (config/prompts/rag_extraction.txt)
```
你是专业的HR数据分析师。请分析以下职位描述，将其结构化提取。

职位文本：
{job_text}

提取要求：
1. 准确分离岗位职责和人员要求
2. 提取所有技能关键词
3. 识别学历和经验要求
4. 确保信息完整且不重复

{format_instructions}

结构化输出：
```

### RAG问答模板提示词 (config/prompts/qa_template.txt)
```
你是专业的职位匹配顾问。基于以下职位信息回答用户问题。

职位信息：
{context}

用户问题：{question}

回答要求：
1. 基于提供的职位信息回答
2. 如果信息不足，明确说明
3. 提供具体的职位匹配建议
4. 回答要专业且有帮助

回答：
```

### 智能匹配分析提示词 (config/prompts/matching.txt)
```
你是一个专业的简历匹配分析师。请基于RAG检索到的职位信息分析候选人匹配度。

候选人信息：
{resume_info}

检索到的相关职位信息：
{retrieved_context}

职位要求：
{job_requirements}

请从以下维度分析匹配度（0-1分）：
1. 语义相似度匹配（权重60%）：基于向量相似度的深度语义理解
2. 技能匹配度（权重25%）：具体技能要求的匹配
3. 经验匹配度（权重15%）：工作经验和项目经历匹配

输出格式：
{
  "semantic_match": 0.85,
  "skills_match": 0.8,
  "experience_match": 0.7,
  "overall_score": 0.82,
  "match_reasons": ["匹配原因1", "匹配原因2"],
  "improvement_suggestions": ["改进建议1", "改进建议2"],
  "analysis": "详细分析说明"
}
```

### 职位推荐提示词 (config/prompts/recommendation.txt)
```
你是专业的职位推荐专家。基于用户画像和RAG检索结果，推荐最适合的职位。

用户画像：
{user_profile}

检索到的职位信息：
{retrieved_jobs}

推荐要求：
1. 根据语义相似度排序
2. 考虑用户的技能匹配度
3. 分析职业发展潜力
4. 提供推荐理由

输出格式：
{
  "recommended_jobs": [
    {
      "job_title": "职位名称",
      "company": "公司名称",
      "match_score": 0.9,
      "recommendation_reason": "推荐理由",
      "growth_potential": "发展潜力分析"
    }
  ],
  "summary": "推荐总结"
}
```

## 重构后的模块化架构

### 登录功能分离

系统已重构为模块化架构，将登录功能和内容提取功能完全分离：

```
┌─────────────────┐    ┌─────────────────┐
│   登录模块      │    │   内容提取模块   │
│                 │    │                 │
│ ├─ LoginManager │    │ ├─ ContentExtractor
│ ├─ SessionManager│    │ ├─ PageParser   │
│ └─ BrowserManager│    │ └─ DataStorage  │
└─────────────────┘    └─────────────────┘
```

### 最新更新：分页功能增强 (2025-01-18)

#### 🚀 分页功能概述

内容提取模块新增完整的分页功能，支持自动导航多页内容，大幅提升数据采集覆盖范围：

- **默认配置**: 自动读取前10页内容
- **智能导航**: 自动检测和点击下一页按钮
- **多页合并**: 自动合并所有页面的提取结果
- **页码标记**: 每个结果都标记来源页码
- **错误恢复**: 单页失败不影响整体提取流程

#### 📄 分页配置

```yaml
# 搜索策略配置 (config/config.yaml)
search:
  strategy:
    max_pages: 10              # 默认最大页数
    enable_pagination: true    # 是否启用分页
    page_delay: 2              # 页面间延迟时间（秒）
    page_delay_max: 5          # 页面间最大延迟时间（秒）
```

#### 🔧 核心分页方法

**PageParser 新增方法：**

1. **`has_next_page(driver)`** - 检测下一页按钮
   - 支持多种选择器：`.btn_next`, `.next-page`, `.page-next`, `.pager-next`等
   - 智能判断按钮是否可用（非禁用状态）

2. **`navigate_to_next_page(driver)`** - 导航到下一页
   - 模拟人类点击行为（悬停、滚动等）
   - 验证页面跳转是否成功
   - 支持AJAX加载的页面

3. **`get_current_page_info(driver)`** - 获取页面信息
   - 从URL参数和页面元素中提取页码
   - 返回当前页码和页面状态

**ContentExtractor 增强方法：**

1. **`extract_from_search_url()`** - 支持多页提取
   - 新增 `max_pages` 参数
   - 实现页面循环逻辑
   - 为每个结果添加 `page_number` 字段

2. **`extract_from_keyword()`** - 关键词多页搜索
   - 支持 `max_pages` 参数传递

3. **`extract_multiple_keywords()`** - 批量多页提取
   - 新增 `max_pages_per_keyword` 参数

#### 💡 使用示例

```python
# 使用默认配置（10页）
results = extractor.extract_from_keyword("AI工程师")

# 自定义页数
results = extractor.extract_from_keyword("AI工程师", max_pages=5)

# 批量提取多个关键词，每个最多3页
results = extractor.extract_multiple_keywords(
    ["AI工程师", "数据工程师"],
    max_pages_per_keyword=3
)

# 检查结果中的页码信息
for job in results:
    print(f"职位: {job['title']} - 来源: 第{job['page_number']}页")
```

#### 🧪 测试验证

创建了专门的测试脚本验证分页功能：

```bash
# 运行分页功能测试
python simple_pagination_test.py

# 测试结果示例：
# 📊 测试结果: 3/3 通过
# 🎉 所有分页功能测试通过！
#
# 📝 分页功能特性:
#   ✅ 配置文件支持分页参数
#   ✅ PageParser 具备分页导航能力
#   ✅ ContentExtractor 支持多页提取
#   ✅ 多种下一页按钮选择器
```

#### 🎯 技术特性

1. **智能分页检测** - 自动识别多种下一页按钮样式
2. **人性化延迟** - 页面间2-5秒随机延迟，避免反爬检测
3. **灵活配置** - 可通过配置文件或参数控制分页行为
4. **结果追踪** - 每个职位都标记来源页码
5. **错误恢复** - 单页失败不影响整体提取
6. **资源优化** - 达到限制时自动停止，避免无效请求

#### 📈 性能提升

- **数据覆盖范围**: 从单页提升到多页（默认10页）
- **采集效率**: 自动化分页导航，无需人工干预
- **数据完整性**: 支持页码标记，便于数据溯源
- **稳定性**: 智能错误恢复，提高采集成功率

### 新增模块配置

```yaml
# 运行模式配置
mode:
  development: true           # 开发模式
  skip_login: false          # 跳过登录检查
  use_saved_session: true    # 使用保存的会话
  session_file: "data/session.json"
  session_timeout: 3600      # 会话超时时间（秒）
  auto_save_session: true    # 自动保存会话
  close_on_complete: false   # 完成后是否关闭浏览器

# 模块配置
modules:
  login:
    enabled: true
    auto_save_session: true
  extraction:
    enabled: true
    max_concurrent: 1
    retry_attempts: 3
  browser:
    reuse_session: true
    close_on_complete: false
```

### 使用方式

#### 1. 独立登录测试
```bash
# 基本登录测试
python test_login.py

# 登录并保存会话
python test_login.py --save-session

# 检查登录状态
python test_login.py --check-status
```

#### 2. 独立内容提取测试
```bash
# 基于关键词提取
python test_extraction.py --keyword "AI工程师"

# 跳过登录检查（开发模式）
python test_extraction.py --keyword "数据架构师" --skip-login

# 批量提取多个关键词
python test_extraction.py --multiple "AI工程师,数据架构师,Python工程师"
```

#### 3. 编程接口使用

**独立登录管理：**
```python
from src.auth.login_manager import LoginManager

with LoginManager(config) as login_manager:
    success = login_manager.start_login_session(save_session=True)
    if success:
        print("登录成功，会话已保存")
```

**独立内容提取：**
```python
from src.extraction.content_extractor import ContentExtractor

# 开发模式：跳过登录
config['mode']['skip_login'] = True

with ContentExtractor(config) as extractor:
    results = extractor.extract_from_keyword("AI工程师", max_results=30)
    print(f"提取到 {len(results)} 个职位")
```

**使用保存的会话：**
```python
# 配置使用保存的会话
config['mode']['use_saved_session'] = True
config['mode']['session_file'] = 'data/my_session.json'

with ContentExtractor(config) as extractor:
    results = extractor.extract_from_keyword("数据架构师")
```

### 重构优势

1. **独立开发**: 登录和内容提取可以独立开发和测试
2. **会话管理**: 支持会话保存和复用，提高效率
3. **开发友好**: 支持跳过登录的开发模式
4. **模块化配置**: 细粒度的配置控制
5. **易于维护**: 清晰的职责分离

### 迁移指南

从旧版本迁移：
```python
# 旧版本
automation = JobSearchAutomation()
automation.start_search_session(keyword="AI工程师")

# 新版本 - 分离式
# 1. 先登录
with LoginManager(config) as login_manager:
    login_manager.start_login_session(save_session=True)

# 2. 再提取内容
with ContentExtractor(config) as extractor:
    results = extractor.extract_from_keyword("AI工程师")
```

## Notes

### 核心特性
- 使用人工登录避免验证码和风控检测
- 通过随机延迟和行为模拟防止反爬
- 支持断点续传，避免重复处理
- 可配置匹配算法权重和阈值
- 简化投递流程，只需点击按钮即可
- 项目采用应用程序架构，直接运行main.py，无需安装包

### 模块化架构特性
- **登录功能分离**: 支持独立的登录模块，便于开发和调试
- **会话管理**: 支持会话保存和复用，提高使用效率
- **开发模式**: 支持跳过登录直接测试内容提取
- **分页功能**: 支持多页内容自动采集，大幅提升数据覆盖范围

### RAG智能分析特性 🚀
- **LangChain集成**: 基于LangChain构建完整的RAG处理流程
- **语义理解**: 使用多语言嵌入模型进行深度语义分析
- **向量存储**: ChromaDB提供高效的向量数据库存储和检索
- **智能分割**: 基于职位内容结构的语义级文本分割
- **结构化提取**: LLM驱动的精确职位信息结构化
- **语义匹配**: 基于向量相似度的深度语义匹配
- **智能问答**: 支持基于职位知识库的智能问答
- **个性化推荐**: 根据用户画像推荐最适合的职位
- **匹配解释**: 提供详细的匹配原因和改进建议
- **持续学习**: 根据投递反馈持续优化匹配算法

### 技术优势
- **双重数据库**: SQLite存储结构化数据，ChromaDB存储向量数据
- **多模型支持**: 支持OpenAI、Claude、本地LLM等多种模型
- **灵活配置**: 通过配置文件精确控制RAG系统参数
- **模块化设计**: RAG组件可独立开发、测试和部署
- **高性能检索**: 毫秒级向量检索，支持大规模职位数据
- **中英文支持**: 完整支持中英文混合职位描述的处理

### 使用场景
- **精准投递**: 基于语义理解的高精度职位匹配
- **职位分析**: 深度分析职位要求和市场趋势
- **技能评估**: 评估个人技能与市场需求的匹配度
- **职业规划**: 基于数据分析的职业发展建议
- **批量处理**: 高效处理大量职位信息的结构化分析