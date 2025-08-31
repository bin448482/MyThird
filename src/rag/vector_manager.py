"""
ChromaDB向量存储管理器

负责职位信息的向量化存储、检索和管理。
支持时间感知的向量搜索，解决新数据被老数据掩盖的问题。
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
from typing import List, Dict, Optional, Any, Tuple
from .llm_factory import create_llm
import logging
import os
import json
import numpy as np
from datetime import datetime, timedelta

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
        
        # 时间感知配置
        self.time_config = self.config.get('time_aware_search', {})
        self.fresh_data_boost = self.time_config.get('fresh_data_boost', 0.2)  # 新数据加分
        self.fresh_data_days = self.time_config.get('fresh_data_days', 7)      # 7天内算新数据
        self.time_decay_factor = self.time_config.get('time_decay_factor', 0.1) # 时间衰减因子
        self.enable_time_boost = self.time_config.get('enable_time_boost', True)
        
        logger.info(f"ChromaDB管理器初始化完成，存储路径: {self.persist_directory}")
        if self.enable_time_boost:
            logger.info(f"时间感知功能已启用: 新数据加分={self.fresh_data_boost}, "
                       f"新数据天数={self.fresh_data_days}, 时间衰减={self.time_decay_factor}")
    
    def _init_embeddings(self) -> HuggingFaceEmbeddings:
        """
        初始化嵌入模型 - 优化中文语义匹配
        支持多种中文优化的向量模型和本地模型加载
        """
        embeddings_config = self.config.get('embeddings', {})
        
        # 检查是否使用本地模型路径
        local_model_path = embeddings_config.get('local_model_path')
        model_name = embeddings_config.get('model_name')
        
        if local_model_path:
            # 使用本地模型路径
            if os.path.exists(local_model_path):
                model_name = local_model_path
                logger.info(f"使用本地向量模型: {local_model_path}")
            else:
                logger.warning(f"本地模型路径不存在: {local_model_path}，回退到在线模型")
                model_name = model_name or self._select_best_chinese_model(embeddings_config)
        elif not model_name:
            # 根据配置选择最佳中文模型
            chinese_optimized = embeddings_config.get('chinese_optimized', True)
            if chinese_optimized:
                # 优先选择中文优化模型
                model_name = self._select_best_chinese_model(embeddings_config)
            else:
                # 使用多语言模型
                model_name = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
        
        logger.info(f"使用向量模型: {model_name}")
        
        # 模型参数配置
        model_kwargs = {
            'device': embeddings_config.get('device', 'cpu'),
            'trust_remote_code': embeddings_config.get('trust_remote_code', True)
        }
        
        # 编码参数配置
        encode_kwargs = {
            'normalize_embeddings': embeddings_config.get('normalize_embeddings', True),
            'batch_size': embeddings_config.get('batch_size', 32)
            # 移除 show_progress_bar 参数，避免与 SentenceTransformer.encode() 冲突
        }
        
        # 支持离线模式
        cache_folder = embeddings_config.get('cache_folder', './models/embeddings')
        if embeddings_config.get('offline_mode', False):
            os.makedirs(cache_folder, exist_ok=True)
            logger.info(f"启用离线模式，模型缓存目录: {cache_folder}")
            # 直接在构造函数中传递 cache_folder，避免与 model_kwargs 中的参数冲突
            return HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs=model_kwargs,
                encode_kwargs=encode_kwargs,
                cache_folder=cache_folder
            )
        else:
            return HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs=model_kwargs,
                encode_kwargs=encode_kwargs
            )
    
    def _select_best_chinese_model(self, embeddings_config: Dict) -> str:
        """选择最佳中文语义模型"""
        
        # 中文优化模型优先级列表
        chinese_models = [
            # 专业中文模型（推荐）
            'shibing624/text2vec-base-chinese',
            'GanymedeNil/text2vec-large-chinese',
            'moka-ai/m3e-base',
            
            # 多语言模型（中文支持良好）
            'sentence-transformers/paraphrase-multilingual-mpnet-base-v2',
            'sentence-transformers/distiluse-base-multilingual-cased',
            'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
            
            # 备选模型
            'sentence-transformers/all-MiniLM-L6-v2'
        ]
        
        # 根据性能要求选择模型
        performance_level = embeddings_config.get('performance_level', 'balanced')
        
        if performance_level == 'high':
            # 高性能模型（更大，更准确）
            preferred_models = [
                'GanymedeNil/text2vec-large-chinese',
                'sentence-transformers/paraphrase-multilingual-mpnet-base-v2',
                'moka-ai/m3e-base'
            ]
        elif performance_level == 'fast':
            # 快速模型（更小，更快）
            preferred_models = [
                'shibing624/text2vec-base-chinese',
                'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                'sentence-transformers/all-MiniLM-L6-v2'
            ]
        else:
            # 平衡模型（默认）
            preferred_models = [
                'shibing624/text2vec-base-chinese',
                'moka-ai/m3e-base',
                'sentence-transformers/paraphrase-multilingual-mpnet-base-v2'
            ]
        
        # 返回首选模型
        selected_model = preferred_models[0]
        logger.info(f"选择中文优化模型: {selected_model} (性能级别: {performance_level})")
        
        return selected_model
    
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
    
    def time_aware_similarity_search(self,
                                   query: str,
                                   k: int = 5,
                                   filters: Dict = None,
                                   strategy: str = 'hybrid') -> List[Tuple[Document, float]]:
        """
        时间感知的相似度搜索
        
        Args:
            query: 查询文本
            k: 返回结果数量
            filters: 过滤条件
            strategy: 搜索策略 ('hybrid', 'fresh_first', 'balanced')
            
        Returns:
            List[Tuple[Document, float]]: 文档和调整后分数的元组列表
        """
        try:
            if not self.enable_time_boost:
                # 时间感知功能未启用，使用基础搜索
                return self.similarity_search_with_score(query=query, k=k, filters=filters)
            
            # 1. 执行基础向量搜索，获取更多候选结果
            # 移除200的硬限制，允许获取7天内的所有数据
            search_k = k * 3  # 获取3倍结果用于重排序，不限制上限
            base_results = self.similarity_search_with_score(
                query=query, k=search_k, filters=filters
            )
            
            if not base_results:
                logger.warning("基础向量搜索无结果")
                return []
            
            logger.debug(f"基础搜索返回 {len(base_results)} 个结果，开始时间感知重排序")
            
            # 2. 应用时间感知重排序
            if strategy == 'fresh_first':
                reranked_results = self._fresh_first_rerank(base_results)
            elif strategy == 'balanced':
                reranked_results = self._balanced_time_rerank(base_results)
            else:  # hybrid
                reranked_results = self._hybrid_time_rerank(base_results)
            
            # 3. 返回前k个结果
            final_results = reranked_results[:k]
            
            # 记录时间分布统计
            self._log_time_distribution(final_results)
            
            logger.debug(f"时间感知搜索完成，返回 {len(final_results)} 个结果")
            return final_results
            
        except Exception as e:
            logger.error(f"时间感知搜索失败: {e}")
            # 降级到基础搜索
            return self.similarity_search_with_score(query=query, k=k, filters=filters)
    
    def _hybrid_time_rerank(self, results: List[Tuple[Document, float]]) -> List[Tuple[Document, float]]:
        """混合时间重排序：平衡相似度和时间新旧"""
        reranked = []
        current_time = datetime.now()
        
        for doc, similarity_score in results:
            # 计算时间权重
            time_weight = self._calculate_time_weight(doc, current_time)
            
            # 混合分数：70%相似度 + 30%时间权重
            hybrid_score = similarity_score * 0.7 + time_weight * 0.3
            
            # 新数据额外加分
            if self._is_fresh_data(doc, current_time):
                hybrid_score += self.fresh_data_boost
                logger.debug(f"新数据加分: {doc.metadata.get('job_id', 'unknown')} "
                           f"原分数: {similarity_score:.3f} -> 混合分数: {hybrid_score:.3f}")
            
            reranked.append((doc, hybrid_score))
        
        # 按混合分数排序
        reranked.sort(key=lambda x: x[1], reverse=True)
        return reranked
    
    def _fresh_first_rerank(self, results: List[Tuple[Document, float]]) -> List[Tuple[Document, float]]:
        """新数据优先重排序：优先展示最新数据"""
        current_time = datetime.now()
        fresh_results = []
        old_results = []
        
        for doc, similarity_score in results:
            if self._is_fresh_data(doc, current_time):
                # 新数据：保持原有相似度分数并加分
                boosted_score = similarity_score + self.fresh_data_boost
                fresh_results.append((doc, boosted_score))
            else:
                # 老数据：应用时间衰减
                time_weight = self._calculate_time_weight(doc, current_time)
                decayed_score = similarity_score * (1 - self.time_decay_factor) + time_weight * self.time_decay_factor
                old_results.append((doc, decayed_score))
        
        # 分别排序
        fresh_results.sort(key=lambda x: x[1], reverse=True)
        old_results.sort(key=lambda x: x[1], reverse=True)
        
        # 新数据在前，老数据在后
        logger.debug(f"新数据优先排序: 新数据 {len(fresh_results)} 个，老数据 {len(old_results)} 个")
        return fresh_results + old_results
    
    def _balanced_time_rerank(self, results: List[Tuple[Document, float]]) -> List[Tuple[Document, float]]:
        """平衡时间重排序：确保新老数据都有机会"""
        current_time = datetime.now()
        reranked = []
        
        for doc, similarity_score in results:
            # 计算时间权重
            time_weight = self._calculate_time_weight(doc, current_time)
            
            # 平衡分数：50%相似度 + 50%时间权重
            balanced_score = similarity_score * 0.5 + time_weight * 0.5
            
            reranked.append((doc, balanced_score))
        
        # 按平衡分数排序
        reranked.sort(key=lambda x: x[1], reverse=True)
        return reranked
    
    def _calculate_time_weight(self, doc: Document, current_time: datetime) -> float:
        """计算时间权重"""
        try:
            created_at_str = doc.metadata.get('created_at')
            if not created_at_str:
                return 0.5  # 没有时间信息，给中等权重
            
            # 解析时间戳
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=current_time.tzinfo)
            
            # 计算时间差（天数）
            time_diff = (current_time - created_at).total_seconds() / (24 * 3600)
            
            # 时间权重计算：越新权重越高
            if time_diff <= 0:
                return 1.0  # 未来时间或当天，最高权重
            elif time_diff <= self.fresh_data_days:
                # 新数据：线性衰减
                return 1.0 - (time_diff / self.fresh_data_days) * 0.3  # 0.7-1.0
            elif time_diff <= 30:
                # 中等数据：缓慢衰减
                return 0.7 - ((time_diff - self.fresh_data_days) / (30 - self.fresh_data_days)) * 0.3  # 0.4-0.7
            else:
                # 老数据：指数衰减
                decay_factor = min(time_diff / 365, 2.0)  # 最多2年衰减
                return max(0.1, 0.4 * np.exp(-decay_factor * 0.5))  # 0.1-0.4
                
        except Exception as e:
            logger.warning(f"计算时间权重失败: {e}")
            return 0.5
    
    def _is_fresh_data(self, doc: Document, current_time: datetime) -> bool:
        """判断是否为新数据"""
        try:
            created_at_str = doc.metadata.get('created_at')
            if not created_at_str:
                return False
            
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=current_time.tzinfo)
            
            time_diff = (current_time - created_at).total_seconds() / (24 * 3600)
            return time_diff <= self.fresh_data_days
            
        except Exception as e:
            logger.warning(f"判断新数据失败: {e}")
            return False
    
    def _log_time_distribution(self, results: List[Tuple[Document, float]]):
        """记录时间分布统计"""
        if not results:
            return
        
        try:
            # 计算7天前的时间戳
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(days=7)
            cutoff_str = cutoff_time.isoformat()
            
            # 查询数据库中7天内的所有数据
            collection = self.vectorstore._collection
            
            # 获取所有文档的元数据
            all_data = collection.get(include=['metadatas'])
            
            within_7days_count = 0
            if all_data and all_data['metadatas']:
                for metadata in all_data['metadatas']:
                    try:
                        created_at_str = metadata.get('created_at')
                        if not created_at_str:
                            continue
                        
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        if created_at.tzinfo is None:
                            created_at = created_at.replace(tzinfo=current_time.tzinfo)
                        
                        # 如果是7天内的数据，计数
                        if created_at >= cutoff_time:
                            within_7days_count += 1
                            
                    except Exception:
                        continue
            
            logger.info(f"时间分布统计: 7天内全部数据 {within_7days_count}个")
            
        except Exception as e:
            logger.warning(f"统计7天内数据失败: {e}")
            # 降级到原来的方法，只统计搜索结果中的数据
            within_7days_count = 0
            current_time = datetime.now()
            
            for doc, _ in results:
                try:
                    created_at_str = doc.metadata.get('created_at')
                    if not created_at_str:
                        continue
                    
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=current_time.tzinfo)
                    
                    time_diff = (current_time - created_at).total_seconds() / (24 * 3600)
                    
                    if time_diff <= 7:
                        within_7days_count += 1
                        
                except Exception:
                    continue
            
            logger.info(f"时间分布统计: 7天内全部数据 {within_7days_count}个 (基于搜索结果)")
    
    def get_recent_documents(self, days: int = 7, k: int = 50) -> List[Document]:
        """获取最近的文档"""
        try:
            # 计算时间过滤条件
            cutoff_time = datetime.now() - timedelta(days=days)
            cutoff_str = cutoff_time.isoformat()
            
            # 使用时间过滤
            filters = {"created_at": {"$gte": cutoff_str}}
            
            # 执行搜索（使用通用查询）
            results = self.similarity_search("最新职位信息", k=k, filters=filters)
            
            logger.info(f"获取到 {len(results)} 个最近 {days} 天的文档")
            return results
            
        except Exception as e:
            logger.error(f"获取最近文档失败: {e}")
            return []

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