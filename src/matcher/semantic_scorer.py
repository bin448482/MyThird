"""
语义评分算法

基于向量相似度和语义理解的评分算法，提供多种评分策略。
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
import numpy as np
from datetime import datetime
import re
from collections import Counter

logger = logging.getLogger(__name__)


class SemanticScorer:
    """语义评分器"""
    
    def __init__(self, config: Dict = None):
        """
        初始化语义评分器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        
        # 评分权重配置
        self.scoring_weights = self.config.get('scoring_weights', {
            'vector_similarity': 0.4,
            'keyword_match': 0.3,
            'semantic_context': 0.2,
            'document_quality': 0.1
        })
        
        # 技能权重映射
        self.skill_weights = self.config.get('skill_weights', {
            'programming': 1.0,
            'framework': 0.9,
            'database': 0.8,
            'tool': 0.7,
            'soft_skill': 0.6
        })
        
        # 技能分类
        self.skill_categories = self._init_skill_categories()
        
        logger.info("语义评分器初始化完成")
    
    def _init_skill_categories(self) -> Dict[str, List[str]]:
        """初始化技能分类"""
        
        return {
            'programming': [
                'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust',
                'php', 'ruby', 'swift', 'kotlin', 'scala', 'r', 'matlab'
            ],
            'framework': [
                'react', 'vue', 'angular', 'django', 'flask', 'spring', 'express',
                'laravel', 'rails', 'asp.net', 'tensorflow', 'pytorch', 'keras'
            ],
            'database': [
                'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
                'oracle', 'sql server', 'sqlite', 'cassandra', 'dynamodb'
            ],
            'tool': [
                'git', 'docker', 'kubernetes', 'jenkins', 'aws', 'azure', 'gcp',
                'linux', 'nginx', 'apache', 'webpack', 'babel'
            ],
            'soft_skill': [
                '沟通', '团队合作', '领导力', '项目管理', '问题解决', '创新思维',
                '学习能力', '责任心', '抗压能力', '时间管理'
            ]
        }
    
    def calculate_comprehensive_score(self, resume_data: Dict[str, Any], 
                                    job_documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算综合评分
        
        Args:
            resume_data: 简历数据
            job_documents: 职位文档列表
            
        Returns:
            Dict: 评分结果
        """
        try:
            # 1. 向量相似度评分
            vector_score = self._calculate_vector_similarity_score(job_documents)
            
            # 2. 关键词匹配评分
            keyword_score = self._calculate_keyword_match_score(resume_data, job_documents)
            
            # 3. 语义上下文评分
            context_score = self._calculate_semantic_context_score(resume_data, job_documents)
            
            # 4. 文档质量评分
            quality_score = self._calculate_document_quality_score(job_documents)
            
            # 5. 计算综合分数
            comprehensive_score = (
                vector_score * self.scoring_weights['vector_similarity'] +
                keyword_score * self.scoring_weights['keyword_match'] +
                context_score * self.scoring_weights['semantic_context'] +
                quality_score * self.scoring_weights['document_quality']
            )
            
            return {
                'comprehensive_score': round(comprehensive_score, 3),
                'component_scores': {
                    'vector_similarity': round(vector_score, 3),
                    'keyword_match': round(keyword_score, 3),
                    'semantic_context': round(context_score, 3),
                    'document_quality': round(quality_score, 3)
                },
                'scoring_details': self._generate_scoring_details(
                    resume_data, job_documents, {
                        'vector': vector_score,
                        'keyword': keyword_score,
                        'context': context_score,
                        'quality': quality_score
                    }
                ),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"综合评分计算失败: {e}")
            return {
                'comprehensive_score': 0.0,
                'error': str(e)
            }
    
    def _calculate_vector_similarity_score(self, job_documents: List[Dict[str, Any]]) -> float:
        """计算向量相似度评分"""
        
        similarity_scores = []
        
        for doc in job_documents:
            score = doc.get('similarity_score', 0.0)
            if score > 0:
                similarity_scores.append(score)
        
        if not similarity_scores:
            return 0.0
        
        # 使用加权平均，给高分更多权重
        weights = [score ** 2 for score in similarity_scores]
        weighted_avg = sum(s * w for s, w in zip(similarity_scores, weights)) / sum(weights)
        
        return min(weighted_avg, 1.0)
    
    def _calculate_keyword_match_score(self, resume_data: Dict[str, Any], 
                                     job_documents: List[Dict[str, Any]]) -> float:
        """计算关键词匹配评分"""
        
        # 提取简历关键词
        resume_keywords = self._extract_resume_keywords(resume_data)
        
        # 提取职位关键词
        job_keywords = self._extract_job_keywords(job_documents)
        
        if not resume_keywords or not job_keywords:
            return 0.0
        
        # 计算匹配度
        matched_keywords = set(resume_keywords).intersection(set(job_keywords))
        
        # 基础匹配分数
        basic_match_score = len(matched_keywords) / len(job_keywords)
        
        # 加权匹配分数（考虑关键词重要性）
        weighted_score = self._calculate_weighted_keyword_score(
            matched_keywords, job_keywords
        )
        
        # 综合分数
        final_score = (basic_match_score * 0.6 + weighted_score * 0.4)
        
        return min(final_score, 1.0)
    
    def _extract_resume_keywords(self, resume_data: Dict[str, Any]) -> List[str]:
        """提取简历关键词"""
        
        keywords = []
        
        # 技能关键词
        skills = resume_data.get('skills', [])
        if isinstance(skills, list):
            keywords.extend([skill.lower().strip() for skill in skills])
        elif isinstance(skills, str):
            keywords.extend([skill.lower().strip() for skill in skills.split(',')])
        
        # 工作经历关键词
        work_experience = resume_data.get('work_experience', [])
        if isinstance(work_experience, list):
            for exp in work_experience:
                if isinstance(exp, str):
                    keywords.extend(self._extract_keywords_from_text(exp))
        elif isinstance(work_experience, str):
            keywords.extend(self._extract_keywords_from_text(work_experience))
        
        # 项目经历关键词
        projects = resume_data.get('projects', [])
        if isinstance(projects, list):
            for project in projects:
                if isinstance(project, str):
                    keywords.extend(self._extract_keywords_from_text(project))
                elif isinstance(project, dict):
                    description = project.get('description', '')
                    keywords.extend(self._extract_keywords_from_text(description))
        
        return list(set(keywords))  # 去重
    
    def _extract_job_keywords(self, job_documents: List[Dict[str, Any]]) -> List[str]:
        """提取职位关键词"""
        
        keywords = []
        
        for doc in job_documents:
            metadata = doc.get('metadata', {})
            content = doc.get('content', '')
            
            # 从元数据提取技能
            skills = metadata.get('skills', [])
            if skills:
                keywords.extend([skill.lower().strip() for skill in skills])
            
            # 从内容提取关键词
            if content:
                keywords.extend(self._extract_keywords_from_text(content))
        
        return list(set(keywords))  # 去重
    
    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        
        if not text:
            return []
        
        # 转换为小写
        text = text.lower()
        
        # 移除标点符号和特殊字符
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
        
        # 分词
        words = text.split()
        
        # 过滤关键词
        keywords = []
        for word in words:
            # 过滤长度
            if len(word) < 2 or len(word) > 20:
                continue
            
            # 检查是否为技术关键词
            if self._is_technical_keyword(word):
                keywords.append(word)
        
        return keywords
    
    def _is_technical_keyword(self, word: str) -> bool:
        """判断是否为技术关键词"""
        
        # 检查是否在技能分类中
        for category, skills in self.skill_categories.items():
            if word in skills:
                return True
        
        # 检查常见技术词汇模式
        tech_patterns = [
            r'.*ing$',  # programming, testing, etc.
            r'.*er$',   # developer, designer, etc.
            r'.*js$',   # vue.js, react.js, etc.
            r'.*sql$',  # mysql, postgresql, etc.
            r'.*db$',   # mongodb, etc.
        ]
        
        for pattern in tech_patterns:
            if re.match(pattern, word):
                return True
        
        return False
    
    def _calculate_weighted_keyword_score(self, matched_keywords: set, 
                                        job_keywords: List[str]) -> float:
        """计算加权关键词分数"""
        
        if not matched_keywords or not job_keywords:
            return 0.0
        
        total_weight = 0.0
        matched_weight = 0.0
        
        for keyword in job_keywords:
            weight = self._get_keyword_weight(keyword)
            total_weight += weight
            
            if keyword in matched_keywords:
                matched_weight += weight
        
        return matched_weight / total_weight if total_weight > 0 else 0.0
    
    def _get_keyword_weight(self, keyword: str) -> float:
        """获取关键词权重"""
        
        # 根据技能分类确定权重
        for category, skills in self.skill_categories.items():
            if keyword in skills:
                return self.skill_weights.get(category, 0.5)
        
        # 默认权重
        return 0.5
    
    def _calculate_semantic_context_score(self, resume_data: Dict[str, Any], 
                                        job_documents: List[Dict[str, Any]]) -> float:
        """计算语义上下文评分"""
        
        # 分析职位类型匹配
        job_type_score = self._analyze_job_type_match(resume_data, job_documents)
        
        # 分析行业匹配
        industry_score = self._analyze_industry_match(resume_data, job_documents)
        
        # 分析经验层次匹配
        experience_level_score = self._analyze_experience_level_match(resume_data, job_documents)
        
        # 综合上下文分数
        context_score = (job_type_score * 0.4 + industry_score * 0.3 + experience_level_score * 0.3)
        
        return min(context_score, 1.0)
    
    def _analyze_job_type_match(self, resume_data: Dict[str, Any], 
                              job_documents: List[Dict[str, Any]]) -> float:
        """分析职位类型匹配度"""
        
        # 从简历中提取期望职位类型
        desired_position = resume_data.get('desired_position', '').lower()
        
        # 从职位文档中提取职位标题
        job_titles = []
        for doc in job_documents:
            metadata = doc.get('metadata', {})
            job_title = metadata.get('job_title', '').lower()
            if job_title:
                job_titles.append(job_title)
        
        if not desired_position or not job_titles:
            return 0.5  # 无法判断，给中等分数
        
        # 计算职位类型相似度
        max_similarity = 0.0
        for job_title in job_titles:
            similarity = self._calculate_text_similarity(desired_position, job_title)
            max_similarity = max(max_similarity, similarity)
        
        return max_similarity
    
    def _analyze_industry_match(self, resume_data: Dict[str, Any], 
                              job_documents: List[Dict[str, Any]]) -> float:
        """分析行业匹配度"""
        
        # 简化的行业匹配分析
        # 这里可以根据实际需求扩展更复杂的行业分析逻辑
        
        return 0.7  # 默认给中等偏上分数
    
    def _analyze_experience_level_match(self, resume_data: Dict[str, Any], 
                                      job_documents: List[Dict[str, Any]]) -> float:
        """分析经验层次匹配度"""
        
        resume_years = resume_data.get('experience_years', 0)
        
        # 从职位文档中提取经验要求
        job_experience_requirements = []
        for doc in job_documents:
            metadata = doc.get('metadata', {})
            experience = metadata.get('experience', '')
            if experience:
                job_experience_requirements.append(experience)
        
        if not job_experience_requirements:
            return 0.7  # 无经验要求，给中等偏上分数
        
        # 分析经验匹配度
        match_scores = []
        for req in job_experience_requirements:
            required_years = self._extract_years_from_requirement(req)
            if required_years is not None:
                if resume_years >= required_years:
                    match_scores.append(1.0)
                elif resume_years >= required_years * 0.8:
                    match_scores.append(0.8)
                elif resume_years >= required_years * 0.5:
                    match_scores.append(0.5)
                else:
                    match_scores.append(0.2)
        
        return max(match_scores) if match_scores else 0.5
    
    def _extract_years_from_requirement(self, requirement: str) -> Optional[int]:
        """从经验要求中提取年限"""
        
        import re
        
        patterns = [
            r'(\d+)\s*年',
            r'(\d+)\s*-\s*\d+\s*年',
            r'(\d+)\+\s*年'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, requirement)
            if match:
                return int(match.group(1))
        
        return None
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（简化版）"""
        
        if not text1 or not text2:
            return 0.0
        
        # 分词
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # 计算Jaccard相似度
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _calculate_document_quality_score(self, job_documents: List[Dict[str, Any]]) -> float:
        """计算文档质量评分"""
        
        if not job_documents:
            return 0.0
        
        quality_scores = []
        
        for doc in job_documents:
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            
            # 内容长度评分
            content_length = len(content)
            length_score = min(content_length / 100, 1.0)  # 标准化到0-1
            
            # 元数据完整性评分
            required_fields = ['job_title', 'company', 'type']
            present_fields = sum(1 for field in required_fields if metadata.get(field))
            metadata_score = present_fields / len(required_fields)
            
            # 文档类型权重
            doc_type = metadata.get('type', '')
            type_weights = {
                'overview': 1.0,
                'skills': 0.9,
                'responsibility': 0.8,
                'requirement': 0.8,
                'basic_requirements': 0.6
            }
            type_weight = type_weights.get(doc_type, 0.5)
            
            # 综合质量分数
            doc_quality = (length_score * 0.4 + metadata_score * 0.4 + type_weight * 0.2)
            quality_scores.append(doc_quality)
        
        # 返回平均质量分数
        return sum(quality_scores) / len(quality_scores)
    
    def _generate_scoring_details(self, resume_data: Dict[str, Any], 
                                job_documents: List[Dict[str, Any]], 
                                scores: Dict[str, float]) -> Dict[str, Any]:
        """生成评分详情"""
        
        details = {
            'total_documents': len(job_documents),
            'document_types': {},
            'keyword_analysis': {},
            'similarity_distribution': [],
            'quality_metrics': {}
        }
        
        # 文档类型统计
        for doc in job_documents:
            doc_type = doc.get('metadata', {}).get('type', 'unknown')
            details['document_types'][doc_type] = details['document_types'].get(doc_type, 0) + 1
        
        # 相似度分布
        similarities = [doc.get('similarity_score', 0.0) for doc in job_documents]
        details['similarity_distribution'] = {
            'min': min(similarities) if similarities else 0.0,
            'max': max(similarities) if similarities else 0.0,
            'avg': sum(similarities) / len(similarities) if similarities else 0.0
        }
        
        # 关键词分析
        resume_keywords = self._extract_resume_keywords(resume_data)
        job_keywords = self._extract_job_keywords(job_documents)
        matched_keywords = set(resume_keywords).intersection(set(job_keywords))
        
        details['keyword_analysis'] = {
            'resume_keywords_count': len(resume_keywords),
            'job_keywords_count': len(job_keywords),
            'matched_keywords_count': len(matched_keywords),
            'match_ratio': len(matched_keywords) / len(job_keywords) if job_keywords else 0.0
        }
        
        return details
    
    def compare_candidates(self, candidates_scores: List[Dict[str, Any]]) -> Dict[str, Any]:
        """比较多个候选人的评分"""
        
        if not candidates_scores:
            return {}
        
        comparison = {
            'candidate_count': len(candidates_scores),
            'score_statistics': {},
            'ranking': [],
            'score_distribution': {
                'excellent': 0,  # >= 0.8
                'good': 0,       # >= 0.6
                'fair': 0,       # >= 0.4
                'poor': 0        # < 0.4
            }
        }
        
        # 收集所有分数
        all_scores = [candidate.get('comprehensive_score', 0.0) for candidate in candidates_scores]
        
        # 统计信息
        comparison['score_statistics'] = {
            'min': min(all_scores),
            'max': max(all_scores),
            'avg': sum(all_scores) / len(all_scores),
            'median': sorted(all_scores)[len(all_scores) // 2]
        }
        
        # 排名
        sorted_candidates = sorted(
            enumerate(candidates_scores),
            key=lambda x: x[1].get('comprehensive_score', 0.0),
            reverse=True
        )
        
        for rank, (original_index, candidate) in enumerate(sorted_candidates, 1):
            score = candidate.get('comprehensive_score', 0.0)
            
            # 分数分布统计
            if score >= 0.8:
                comparison['score_distribution']['excellent'] += 1
            elif score >= 0.6:
                comparison['score_distribution']['good'] += 1
            elif score >= 0.4:
                comparison['score_distribution']['fair'] += 1
            else:
                comparison['score_distribution']['poor'] += 1
            
            # 排名信息
            comparison['ranking'].append({
                'rank': rank,
                'original_index': original_index,
                'score': score,
                'candidate_id': candidate.get('candidate_id', f'candidate_{original_index}')
            })
        
        return comparison