"""
ChromaDB向量存储管理器

负责职位信息的向量化存储、检索和管理。
"""

try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain.vectorstores import Chroma

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain.embeddings import HuggingFaceEmbeddings

from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain.schema import Document
from typing import List, Dict, Optional, Any
from .llm_factory import create_llm
import logging
import os
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class ChromaDBManager:
    """ChromaDB向量存储管理器"""
    
    def __init__(self, config: Dict = None):
        """
        初始化ChromaDB管理器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        
        # 配置参数
        self.persist_directory = self.config.get('persist_directory', './chroma_db')
        self.collection_name = self.config.get('collection_name', 'job_positions')
        
        # 确保目录存在
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # 初始化嵌入模型
        self.embeddings = self._init_embeddings()
        
        # 初始化ChromaDB
        self.vectorstore = self._init_vectorstore()
        
        # 初始化压缩检索器
        self.compression_retriever = self._init_compression_retriever()
        
        logger.info(f"ChromaDB管理器初始化完成，存储路径: {self.persist_directory}")
    
    def _init_embeddings(self) -> HuggingFaceEmbeddings:
        """初始化嵌入模型"""
        embeddings_config = self.config.get('embeddings', {})
        
        model_name = embeddings_config.get(
            'model_name', 
            'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
        )
        
        return HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={
                'device': embeddings_config.get('device', 'cpu')
            },
            encode_kwargs={
                'normalize_embeddings': embeddings_config.get('normalize_embeddings', True)
            }
        )
    
    def _init_vectorstore(self) -> Chroma:
        """初始化ChromaDB向量存储"""
        return Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings,
            collection_name=self.collection_name
        )
    
    def _init_compression_retriever(self) -> Optional[ContextualCompressionRetriever]:
        """初始化压缩检索器"""
        try:
            # 初始化LLM压缩器
            llm_config = self.config.get('llm', {})
            
            # 获取LLM提供商和配置
            provider = llm_config.get('provider', 'zhipu')
            
            # 检查必要的配置
            if provider == 'zhipu' and not llm_config.get('api_key'):
                logger.warning("未配置智谱GLM API密钥，跳过压缩检索器初始化")
                return None
            elif provider == 'openai' and not llm_config.get('api_key'):
                logger.warning("未配置OpenAI API密钥，跳过压缩检索器初始化")
                return None
            elif provider == 'claude' and not llm_config.get('api_key'):
                logger.warning("未配置Claude API密钥，跳过压缩检索器初始化")
                return None
            
            # 创建LLM实例
            llm = create_llm(
                provider=provider,
                model=llm_config.get('model', 'glm-4-flash' if provider == 'zhipu' else 'gpt-3.5-turbo'),
                temperature=llm_config.get('temperature', 0),
                max_tokens=llm_config.get('max_tokens', 1024),
                **{k: v for k, v in llm_config.items() if k not in ['provider', 'model', 'temperature', 'max_tokens']}
            )
            
            compressor = LLMChainExtractor.from_llm(llm)
            
            # 创建压缩检索器
            retrieval_config = self.config.get('retrieval', {})
            return ContextualCompressionRetriever(
                base_compressor=compressor,
                base_retriever=self.vectorstore.as_retriever(
                    search_kwargs={"k": retrieval_config.get('k', 10)}
                )
            )
        except Exception as e:
            logger.warning(f"压缩检索器初始化失败: {e}，将使用基础检索器")
            return None
    
    def add_job_documents(self, documents: List[Document], job_id: str = None) -> List[str]:
        """
        添加职位文档到向量数据库
        
        Args:
            documents: 文档列表
            job_id: 职位ID
            
        Returns:
            List[str]: 文档ID列表
        """
        try:
            # 为文档添加时间戳和job_id，并过滤复杂元数据
            timestamp = datetime.now().isoformat()
            for doc in documents:
                # 过滤复杂元数据（将列表转换为字符串）
                filtered_metadata = self._filter_complex_metadata(doc.metadata)
                filtered_metadata.update({
                    'created_at': timestamp,
                    'job_id': job_id
                })
                doc.metadata = filtered_metadata
            
            # 批量添加文档
            doc_ids = self.vectorstore.add_documents(documents)
            
            # 新版本的langchain-chroma不需要手动persist，自动持久化
            # self.vectorstore.persist()  # 已移除此方法
            
            logger.info(f"成功添加 {len(documents)} 个文档到向量数据库")
            return doc_ids
            
        except Exception as e:
            logger.error(f"添加文档到向量数据库失败: {e}")
            raise
    
    def _filter_complex_metadata(self, metadata: Dict) -> Dict:
        """
        过滤复杂元数据，将不支持的类型转换为字符串
        
        Args:
            metadata: 原始元数据
            
        Returns:
            过滤后的元数据
        """
        filtered = {}
        for key, value in metadata.items():
            if value is None:
                filtered[key] = None
            elif isinstance(value, (str, int, float, bool)):
                filtered[key] = value
            elif isinstance(value, list):
                # 将列表转换为逗号分隔的字符串
                filtered[key] = ', '.join(str(item) for item in value)
            elif isinstance(value, dict):
                # 将字典转换为JSON字符串
                import json
                filtered[key] = json.dumps(value, ensure_ascii=False)
            else:
                # 其他类型转换为字符串
                filtered[key] = str(value)
        
        return filtered
    
    async def add_job_documents_async(self, documents: List[Document], job_id: str = None) -> List[str]:
        """
        异步添加职位文档到向量数据库
        
        Args:
            documents: 文档列表
            job_id: 职位ID
            
        Returns:
            List[str]: 文档ID列表
        """
        import asyncio
        
        # 在线程池中执行同步操作
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.add_job_documents, documents, job_id)
    
    def search_similar_jobs(self, query: str, k: int = 5, filters: Dict = None) -> List[Document]:
        """
        搜索相似职位
        
        Args:
            query: 查询文本
            k: 返回结果数量
            filters: 过滤条件
            
        Returns:
            List[Document]: 相似文档列表
        """
        try:
            if self.compression_retriever and not filters:
                # 使用压缩检索器
                compressed_docs = self.compression_retriever.get_relevant_documents(query)
                return compressed_docs[:k]
            else:
                # 使用基础检索器
                search_kwargs = {"k": k}
                if filters:
                    search_kwargs["filter"] = filters
                
                docs = self.vectorstore.similarity_search(query, **search_kwargs)
                return docs
                
        except Exception as e:
            logger.error(f"搜索相似职位失败: {e}")
            return []
    
    def similarity_search_with_score(self, query: str, k: int = 5, filters: Dict = None) -> List[tuple]:
        """
        带相似度分数的搜索
        
        Args:
            query: 查询文本
            k: 返回结果数量
            filters: 过滤条件
            
        Returns:
            List[tuple]: (Document, score) 元组列表
        """
        try:
            search_kwargs = {"k": k}
            if filters:
                search_kwargs["filter"] = filters
            
            results = self.vectorstore.similarity_search_with_score(query, **search_kwargs)
            return results
            
        except Exception as e:
            logger.error(f"带分数搜索失败: {e}")
            return []
    
    def hybrid_search(self, query: str, filters: Dict = None, k: int = 20) -> List[Document]:
        """
        混合检索：向量检索 + 元数据过滤
        
        Args:
            query: 查询文本
            filters: 过滤条件
            k: 返回结果数量
            
        Returns:
            List[Document]: 检索结果
        """
        try:
            # 构建搜索参数
            search_kwargs = {"k": k}
            if filters:
                search_kwargs["filter"] = filters
            
            # 执行检索
            docs = self.vectorstore.similarity_search(query, **search_kwargs)
            
            logger.info(f"混合检索返回 {len(docs)} 个结果")
            return docs
            
        except Exception as e:
            logger.error(f"混合检索失败: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        获取集合统计信息
        
        Returns:
            Dict: 统计信息
        """
        try:
            collection = self.vectorstore._collection
            count = collection.count()
            
            return {
                'document_count': count,
                'collection_name': self.collection_name,
                'persist_directory': self.persist_directory
            }
            
        except Exception as e:
            logger.error(f"获取集合统计信息失败: {e}")
            return {}
    
    def delete_documents(self, job_id: str) -> bool:
        """
        删除指定职位的所有文档
        
        Args:
            job_id: 职位ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            # ChromaDB删除文档的方法
            collection = self.vectorstore._collection
            
            # 根据job_id过滤并删除
            collection.delete(where={"job_id": job_id})
            
            # 新版本自动持久化
            # self.vectorstore.persist()  # 已移除此方法
            
            logger.info(f"成功删除职位 {job_id} 的所有文档")
            return True
            
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False
    
    def update_document_metadata(self, doc_id: str, metadata: Dict) -> bool:
        """
        更新文档元数据
        
        Args:
            doc_id: 文档ID
            metadata: 新的元数据
            
        Returns:
            bool: 更新是否成功
        """
        try:
            # ChromaDB更新元数据的方法
            collection = self.vectorstore._collection
            
            collection.update(
                ids=[doc_id],
                metadatas=[metadata]
            )
            
            # 新版本自动持久化
            # self.vectorstore.persist()  # 已移除此方法
            
            logger.info(f"成功更新文档 {doc_id} 的元数据")
            return True
            
        except Exception as e:
            logger.error(f"更新文档元数据失败: {e}")
            return False
    
    def backup_collection(self, backup_path: str) -> bool:
        """
        备份集合数据
        
        Args:
            backup_path: 备份路径
            
        Returns:
            bool: 备份是否成功
        """
        try:
            import shutil
            
            # 创建备份目录
            os.makedirs(backup_path, exist_ok=True)
            
            # 复制数据库文件
            shutil.copytree(
                self.persist_directory, 
                os.path.join(backup_path, 'chroma_db'),
                dirs_exist_ok=True
            )
            
            # 保存配置信息
            config_backup = {
                'collection_name': self.collection_name,
                'backup_time': datetime.now().isoformat(),
                'stats': self.get_collection_stats()
            }
            
            with open(os.path.join(backup_path, 'backup_info.json'), 'w', encoding='utf-8') as f:
                json.dump(config_backup, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功备份集合到: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"备份集合失败: {e}")
            return False
    
    def close(self):
        """关闭连接并清理资源"""
        try:
            # 新版本自动持久化，无需手动调用persist
            # self.vectorstore.persist()  # 已移除此方法
            
            # 清理向量存储引用，帮助释放文件句柄
            if hasattr(self, 'vectorstore'):
                self.vectorstore = None
            if hasattr(self, 'compression_retriever'):
                self.compression_retriever = None
                
            logger.info("ChromaDB连接已关闭")
        except Exception as e:
            logger.error(f"关闭ChromaDB连接时出错: {e}")