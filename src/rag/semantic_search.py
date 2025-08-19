"""
语义搜索引擎

基于向量相似度的语义搜索，支持多种搜索策略和结果排序。
"""

from langchain.schema import Document
from typing import List, Dict, Any, Optional, Tuple
import logging
import numpy as np
from datetime import datetime
import json

from .vector_manager import ChromaDBManager

logger = logging.getLogger(__name__)


class SemanticSearchEngine:
    """语义搜索引擎"""
    
    def __init__(self, vector_manager: ChromaDBManager, config: Dict = None):
        """
        初始化语义搜索引擎
        
        Args:
            vector_manager: 向量存储管理器
            config: 配置字典
        """
        self.vector_manager = vector_manager
        self.config = config or {}
        
        # 搜索配置
        self.default_k = self.config.get('default_k', 10)
        self.score_threshold = self.config.get('score_threshold', 0.7)
        self.max_results = self.config.get('max_results', 50)
        
        # 搜索策略配置
        self.search_strategies = {
            'similarity': self._similarity_search,
            'hybrid': self._hybrid_search,
            'filtered': self._filtered_search,
            'multi_query': self._multi_query_search
        }
        
        logger.info("语义搜索引擎初始化完成")
    
    def search(self, query: str, strategy: str = 'similarity', 
               k: int = None, filters: Dict = None, **kwargs) -> List[Dict[str, Any]]:
        """
        执行语义搜索
        
        Args:
            query: 搜索查询
            strategy: 搜索策略
            k: 返回结果数量
            filters: 过滤条件
            **kwargs: 其他参数
            
        Returns:
            List[Dict]: 搜索结果
        """
        k = k or self.default_k
        
        if strategy not in self.search_strategies:
            logger.warning(f"未知搜索策略: {strategy}，使用默认策略")
            strategy = 'similarity'
        
        try:
            # 执行搜索
            search_func = self.search_strategies[strategy]
            results = search_func(query, k, filters, **kwargs)
            
            # 后处理结果
            processed_results = self._post_process_results(results, query)
            
            logger.info(f"搜索完成，返回 {len(processed_results)} 个结果")
            return processed_results
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []
    
    def _similarity_search(self, query: str, k: int, filters: Dict = None, 
                          **kwargs) -> List[Tuple[Document, float]]:
        """相似度搜索"""
        
        return self.vector_manager.similarity_search_with_score(
            query=query, k=k, filters=filters
        )
    
    def _hybrid_search(self, query: str, k: int, filters: Dict = None, 
                      **kwargs) -> List[Tuple[Document, float]]:
        """混合搜索：结合向量搜索和关键词匹配"""
        
        # 先进行向量搜索
        vector_results = self.vector_manager.similarity_search_with_score(
            query=query, k=k*2, filters=filters  # 获取更多结果用于重排序
        )
        
        # 关键词匹配评分
        query_words = set(query.lower().split())
        
        enhanced_results = []
        for doc, vector_score in vector_results:
            # 计算关键词匹配分数
            content_words = set(doc.page_content.lower().split())
            keyword_score = len(query_words.intersection(content_words)) / len(query_words)
            
            # 组合分数
            combined_score = vector_score * 0.7 + keyword_score * 0.3
            enhanced_results.append((doc, combined_score))
        
        # 按组合分数排序
        enhanced_results.sort(key=lambda x: x[1], reverse=True)
        
        return enhanced_results[:k]
    
    def _filtered_search(self, query: str, k: int, filters: Dict = None, 
                        **kwargs) -> List[Tuple[Document, float]]:
        """过滤搜索：基于元数据的精确过滤"""
        
        # 构建过滤条件
        search_filters = filters or {}
        
        # 添加分数阈值过滤
        results = self.vector_manager.similarity_search_with_score(
            query=query, k=k*3, filters=search_filters
        )
        
        # 过滤低分结果
        filtered_results = [
            (doc, score) for doc, score in results 
            if score >= self.score_threshold
        ]
        
        return filtered_results[:k]
    
    def _multi_query_search(self, query: str, k: int, filters: Dict = None, 
                           **kwargs) -> List[Tuple[Document, float]]:
        """多查询搜索：生成多个相关查询并合并结果"""
        
        # 生成相关查询
        related_queries = self._generate_related_queries(query)
        
        all_results = {}  # doc_id -> (doc, max_score)
        
        # 对每个查询执行搜索
        for q in [query] + related_queries:
            results = self.vector_manager.similarity_search_with_score(
                query=q, k=k, filters=filters
            )
            
            for doc, score in results:
                doc_id = doc.metadata.get('doc_id', id(doc))
                if doc_id not in all_results or score > all_results[doc_id][1]:
                    all_results[doc_id] = (doc, score)
        
        # 按分数排序
        sorted_results = sorted(all_results.values(), key=lambda x: x[1], reverse=True)
        
        return sorted_results[:k]
    
    def _generate_related_queries(self, query: str) -> List[str]:
        """生成相关查询"""
        related_queries = []
        
        # 简单的查询扩展策略
        words = query.split()
        
        # 添加同义词查询（简化版）
        synonyms = {
            '开发': ['编程', '程序员', '工程师'],
            'Python': ['python', 'py'],
            '经验': ['年限', '工作经验'],
            '要求': ['需要', '条件']
        }
        
        for word in words:
            if word in synonyms:
                for synonym in synonyms[word]:
                    new_query = query.replace(word, synonym)
                    if new_query != query:
                        related_queries.append(new_query)
        
        return related_queries[:3]  # 最多3个相关查询
    
    def _post_process_results(self, results: List[Tuple[Document, float]], 
                            query: str) -> List[Dict[str, Any]]:
        """后处理搜索结果"""
        
        processed_results = []
        
        for doc, score in results:
            # 构建结果字典
            result = {
                'content': doc.page_content,
                'metadata': doc.metadata,
                'similarity_score': float(score),
                'relevance_rank': len(processed_results) + 1,
                'search_query': query,
                'timestamp': datetime.now().isoformat()
            }
            
            # 添加额外的相关性指标
            result.update(self._calculate_relevance_metrics(doc, query, score))
            
            processed_results.append(result)
        
        return processed_results
    
    def _calculate_relevance_metrics(self, doc: Document, query: str, 
                                   similarity_score: float) -> Dict[str, Any]:
        """计算相关性指标"""
        
        metrics = {}
        
        # 内容长度指标
        content_length = len(doc.page_content)
        metrics['content_length'] = content_length
        metrics['content_length_score'] = min(content_length / 200, 1.0)  # 标准化到0-1
        
        # 关键词密度
        query_words = query.lower().split()
        content_words = doc.page_content.lower().split()
        
        keyword_matches = sum(1 for word in query_words if word in content_words)
        metrics['keyword_matches'] = keyword_matches
        metrics['keyword_density'] = keyword_matches / len(query_words) if query_words else 0
        
        # 文档类型权重
        doc_type = doc.metadata.get('type', 'unknown')
        type_weights = {
            'overview': 1.0,
            'skills': 0.9,
            'responsibility': 0.8,
            'requirement': 0.8,
            'basic_requirements': 0.6
        }
        metrics['type_weight'] = type_weights.get(doc_type, 0.5)
        
        # 综合相关性分数
        metrics['relevance_score'] = (
            similarity_score * 0.5 +
            metrics['keyword_density'] * 0.3 +
            metrics['type_weight'] * 0.2
        )
        
        return metrics
    
    def search_by_job_criteria(self, criteria: Dict[str, Any], 
                              k: int = None) -> List[Dict[str, Any]]:
        """
        基于职位标准搜索
        
        Args:
            criteria: 搜索标准
            k: 返回结果数量
            
        Returns:
            List[Dict]: 搜索结果
        """
        k = k or self.default_k
        
        # 构建查询文本
        query_parts = []
        filters = {}
        
        # 处理技能要求
        if 'skills' in criteria:
            skills = criteria['skills']
            if isinstance(skills, list):
                query_parts.append(f"技能要求: {', '.join(skills)}")
            else:
                query_parts.append(f"技能要求: {skills}")
        
        # 处理经验要求
        if 'experience' in criteria:
            query_parts.append(f"经验要求: {criteria['experience']}")
        
        # 处理地点要求
        if 'location' in criteria:
            filters['location'] = criteria['location']
            query_parts.append(f"工作地点: {criteria['location']}")
        
        # 处理薪资要求
        if 'salary_min' in criteria or 'salary_max' in criteria:
            salary_min = criteria.get('salary_min', 0)
            salary_max = criteria.get('salary_max', 999999)
            query_parts.append(f"薪资范围: {salary_min}-{salary_max}")
        
        # 构建最终查询
        query = '; '.join(query_parts) if query_parts else "职位信息"
        
        return self.search(query=query, strategy='filtered', k=k, filters=filters)
    
    def find_similar_positions(self, reference_job: Dict[str, Any], 
                             k: int = None) -> List[Dict[str, Any]]:
        """
        查找相似职位
        
        Args:
            reference_job: 参考职位信息
            k: 返回结果数量
            
        Returns:
            List[Dict]: 相似职位列表
        """
        k = k or self.default_k
        
        # 构建参考职位的查询文本
        query_parts = []
        
        if 'job_title' in reference_job:
            query_parts.append(reference_job['job_title'])
        
        if 'skills' in reference_job:
            skills = reference_job['skills']
            if isinstance(skills, list):
                query_parts.extend(skills[:5])  # 最多5个技能
            else:
                query_parts.append(str(skills))
        
        if 'responsibilities' in reference_job:
            responsibilities = reference_job['responsibilities']
            if isinstance(responsibilities, list):
                query_parts.extend(responsibilities[:3])  # 最多3个职责
        
        query = ' '.join(query_parts)
        
        # 排除参考职位本身
        filters = {}
        if 'job_id' in reference_job:
            # 注意：这里需要根据实际的ChromaDB过滤语法调整
            filters = {'job_id': {'$ne': reference_job['job_id']}}
        
        return self.search(query=query, strategy='similarity', k=k, filters=filters)
    
    def get_search_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """
        获取搜索建议
        
        Args:
            partial_query: 部分查询文本
            limit: 建议数量限制
            
        Returns:
            List[str]: 搜索建议列表
        """
        try:
            # 基于现有文档内容生成建议
            # 这里实现一个简化版本
            
            suggestions = []
            
            # 常见搜索模式
            common_patterns = [
                f"{partial_query} 开发工程师",
                f"{partial_query} 技能要求",
                f"{partial_query} 工作经验",
                f"{partial_query} 岗位职责",
                f"{partial_query} 薪资待遇"
            ]
            
            # 过滤和排序建议
            for pattern in common_patterns:
                if pattern.strip() and len(pattern) > len(partial_query):
                    suggestions.append(pattern)
            
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(f"生成搜索建议失败: {e}")
            return []
    
    def analyze_search_patterns(self, search_history: List[str]) -> Dict[str, Any]:
        """
        分析搜索模式
        
        Args:
            search_history: 搜索历史
            
        Returns:
            Dict: 搜索模式分析结果
        """
        if not search_history:
            return {}
        
        analysis = {
            'total_searches': len(search_history),
            'unique_queries': len(set(search_history)),
            'most_common_terms': {},
            'search_patterns': []
        }
        
        # 统计词频
        all_words = []
        for query in search_history:
            words = query.lower().split()
            all_words.extend(words)
        
        # 计算词频
        from collections import Counter
        word_counts = Counter(all_words)
        analysis['most_common_terms'] = dict(word_counts.most_common(10))
        
        # 识别搜索模式
        patterns = []
        for query in set(search_history):
            if '工程师' in query:
                patterns.append('职位搜索')
            elif any(skill in query.lower() for skill in ['python', 'java', 'javascript']):
                patterns.append('技能搜索')
            elif '经验' in query or '年' in query:
                patterns.append('经验搜索')
        
        analysis['search_patterns'] = list(set(patterns))
        
        return analysis