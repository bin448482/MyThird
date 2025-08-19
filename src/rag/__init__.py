"""
RAG智能分析模块

基于LangChain的RAG（检索增强生成）系统，负责职位信息的深度分析、向量化存储和智能匹配。

主要组件：
- JobProcessor: LangChain职位处理器
- VectorManager: ChromaDB向量存储管理
- RAGChain: RAG检索问答链
- DocumentCreator: 文档创建器
- SemanticSearch: 语义搜索引擎
"""

from .job_processor import LangChainJobProcessor, JobStructure
from .vector_manager import ChromaDBManager
from .rag_chain import JobRAGSystem
from .document_creator import DocumentCreator
from .semantic_search import SemanticSearchEngine

__all__ = [
    'LangChainJobProcessor',
    'JobStructure',
    'ChromaDBManager',
    'JobRAGSystem',
    'DocumentCreator',
    'SemanticSearchEngine'
]

__version__ = '1.0.0'