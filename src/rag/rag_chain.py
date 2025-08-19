"""
RAG检索问答链

基于LangChain的检索增强生成系统，负责职位信息的智能问答和匹配分析。
"""

from langchain.chains import RetrievalQA
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI
from langchain.schema import Document
from typing import Dict, List, Optional, Any
import logging
import json
from datetime import datetime

from .vector_manager import ChromaDBManager

logger = logging.getLogger(__name__)


class JobRAGSystem:
    """职位信息RAG系统"""
    
    def __init__(self, vectorstore_manager: ChromaDBManager, config: Dict = None):
        """
        初始化RAG系统
        
        Args:
            vectorstore_manager: 向量存储管理器
            config: 配置字典
        """
        self.vectorstore_manager = vectorstore_manager
        self.config = config or {}
        
        # 初始化LLM
        llm_config = self.config.get('llm', {})
        self.llm = OpenAI(
            model_name=llm_config.get('model', 'gpt-3.5-turbo'),
            temperature=llm_config.get('temperature', 0.2),
            max_tokens=llm_config.get('max_tokens', 2000)
        )
        
        # 构建问答链
        self.qa_chain = self._build_qa_chain()
        
        # 构建检索QA链
        self.retrieval_qa = self._build_retrieval_qa()
        
        logger.info("JobRAG系统初始化完成")
    
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
5. 如果涉及多个职位，请分别说明

回答：
"""
        
        return PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )
    
    def _build_qa_chain(self) -> Any:
        """构建问答链"""
        
        return load_qa_chain(
            llm=self.llm,
            chain_type="stuff",
            prompt=self._build_qa_prompt()
        )
    
    def _build_retrieval_qa(self) -> RetrievalQA:
        """构建检索QA链"""
        
        retrieval_config = self.config.get('retrieval', {})
        
        return RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vectorstore_manager.vectorstore.as_retriever(
                search_kwargs={"k": retrieval_config.get('k', 5)}
            ),
            return_source_documents=True,
            chain_type_kwargs={"prompt": self._build_qa_prompt()}
        )
    
    async def ask_question(self, question: str, filters: Dict = None, k: int = 5) -> Dict[str, Any]:
        """
        问答接口
        
        Args:
            question: 用户问题
            filters: 过滤条件
            k: 检索文档数量
            
        Returns:
            Dict: 问答结果
        """
        try:
            # 检索相关文档
            relevant_docs = self.vectorstore_manager.hybrid_search(
                query=question, 
                filters=filters, 
                k=k
            )
            
            if not relevant_docs:
                return {
                    "answer": "抱歉，没有找到相关的职位信息。请尝试调整搜索条件。",
                    "source_documents": [],
                    "confidence": 0.0
                }
            
            # 使用检索QA链生成回答
            result = await self.retrieval_qa.arun(
                query=question,
                source_documents=relevant_docs
            )
            
            # 计算置信度
            confidence = self._calculate_confidence(relevant_docs, question)
            
            return {
                "answer": result.get("result", result) if isinstance(result, dict) else result,
                "source_documents": [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "relevance_score": getattr(doc, 'relevance_score', None)
                    }
                    for doc in relevant_docs
                ],
                "confidence": confidence,
                "query": question,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"问答处理失败: {e}")
            return {
                "answer": f"处理问题时出现错误: {str(e)}",
                "source_documents": [],
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _calculate_confidence(self, documents: List[Document], question: str) -> float:
        """
        计算回答置信度
        
        Args:
            documents: 检索到的文档
            question: 用户问题
            
        Returns:
            float: 置信度分数 (0-1)
        """
        if not documents:
            return 0.0
        
        # 基于文档数量和相关性的简单置信度计算
        base_confidence = min(len(documents) / 5.0, 1.0)  # 文档数量因子
        
        # 检查关键词匹配
        question_lower = question.lower()
        keyword_matches = 0
        total_keywords = 0
        
        for doc in documents:
            content_lower = doc.page_content.lower()
            words = question_lower.split()
            total_keywords += len(words)
            
            for word in words:
                if len(word) > 2 and word in content_lower:
                    keyword_matches += 1
        
        keyword_confidence = keyword_matches / max(total_keywords, 1)
        
        # 综合置信度
        final_confidence = (base_confidence * 0.6 + keyword_confidence * 0.4)
        return min(final_confidence, 1.0)
    
    async def find_matching_jobs(self, user_profile: str, filters: Dict = None, k: int = 10) -> List[Dict[str, Any]]:
        """
        职位匹配
        
        Args:
            user_profile: 用户画像描述
            filters: 过滤条件
            k: 返回职位数量
            
        Returns:
            List[Dict]: 匹配的职位列表
        """
        try:
            query = f"寻找适合以下背景的职位：{user_profile}"
            
            # 检索匹配职位
            matching_docs = self.vectorstore_manager.search_similar_jobs(
                query=query, 
                k=k * 2,  # 获取更多文档用于分组
                filters=filters
            )
            
            if not matching_docs:
                return []
            
            # 按职位分组
            jobs_by_title = {}
            for doc in matching_docs:
                job_title = doc.metadata.get("job_title", "未知职位")
                company = doc.metadata.get("company", "未知公司")
                job_key = f"{job_title}@{company}"
                
                if job_key not in jobs_by_title:
                    jobs_by_title[job_key] = {
                        "job_title": job_title,
                        "company": company,
                        "documents": [],
                        "metadata": doc.metadata
                    }
                jobs_by_title[job_key]["documents"].append(doc)
            
            # 生成匹配报告
            matching_jobs = []
            for job_key, job_info in jobs_by_title.items():
                docs = job_info["documents"]
                
                # 计算匹配分数
                match_score = self._calculate_match_score(docs, user_profile)
                
                job_match = {
                    "job_title": job_info["job_title"],
                    "company": job_info["company"],
                    "match_score": match_score,
                    "responsibilities": [
                        d.page_content for d in docs 
                        if d.metadata.get("type") == "responsibility"
                    ],
                    "requirements": [
                        d.page_content for d in docs 
                        if d.metadata.get("type") == "requirement"
                    ],
                    "skills": [
                        skill for d in docs 
                        if d.metadata.get("type") == "skills"
                        for skill in d.metadata.get("skills", [])
                    ],
                    "location": job_info["metadata"].get("location"),
                    "salary_range": {
                        "min": job_info["metadata"].get("salary_min"),
                        "max": job_info["metadata"].get("salary_max")
                    },
                    "match_reasons": self._generate_match_reasons(docs, user_profile)
                }
                matching_jobs.append(job_match)
            
            # 按匹配度排序
            matching_jobs.sort(key=lambda x: x["match_score"], reverse=True)
            
            logger.info(f"为用户画像找到 {len(matching_jobs)} 个匹配职位")
            return matching_jobs[:k]
            
        except Exception as e:
            logger.error(f"职位匹配失败: {e}")
            return []
    
    def _calculate_match_score(self, documents: List[Document], user_profile: str) -> float:
        """
        计算匹配分数
        
        Args:
            documents: 职位文档列表
            user_profile: 用户画像
            
        Returns:
            float: 匹配分数 (0-1)
        """
        if not documents:
            return 0.0
        
        profile_lower = user_profile.lower()
        total_score = 0.0
        doc_count = len(documents)
        
        for doc in documents:
            content_lower = doc.page_content.lower()
            
            # 简单的关键词匹配评分
            words = profile_lower.split()
            matches = sum(1 for word in words if len(word) > 2 and word in content_lower)
            doc_score = matches / max(len(words), 1)
            
            # 根据文档类型调整权重
            doc_type = doc.metadata.get("type", "")
            if doc_type == "skills":
                doc_score *= 1.5  # 技能匹配更重要
            elif doc_type == "requirement":
                doc_score *= 1.2  # 要求匹配次重要
            
            total_score += doc_score
        
        # 平均分数
        avg_score = total_score / doc_count
        return min(avg_score, 1.0)
    
    def _generate_match_reasons(self, documents: List[Document], user_profile: str) -> List[str]:
        """
        生成匹配原因
        
        Args:
            documents: 职位文档列表
            user_profile: 用户画像
            
        Returns:
            List[str]: 匹配原因列表
        """
        reasons = []
        profile_lower = user_profile.lower()
        
        # 分析技能匹配
        skill_docs = [d for d in documents if d.metadata.get("type") == "skills"]
        for doc in skill_docs:
            skills = doc.metadata.get("skills", [])
            matched_skills = [
                skill for skill in skills 
                if skill.lower() in profile_lower
            ]
            if matched_skills:
                reasons.append(f"技能匹配: {', '.join(matched_skills)}")
        
        # 分析经验匹配
        basic_req_docs = [d for d in documents if d.metadata.get("type") == "basic_requirements"]
        for doc in basic_req_docs:
            experience = doc.metadata.get("experience", "")
            if experience and "年" in experience:
                reasons.append(f"经验要求匹配: {experience}")
        
        # 如果没有具体原因，添加通用原因
        if not reasons:
            reasons.append("职位描述与个人背景相关")
        
        return reasons[:3]  # 最多返回3个原因
    
    async def analyze_job_market(self, query: str, filters: Dict = None) -> Dict[str, Any]:
        """
        分析职位市场
        
        Args:
            query: 分析查询
            filters: 过滤条件
            
        Returns:
            Dict: 市场分析结果
        """
        try:
            # 检索相关职位
            docs = self.vectorstore_manager.hybrid_search(
                query=query,
                filters=filters,
                k=50  # 获取更多数据用于分析
            )
            
            if not docs:
                return {"error": "没有找到相关职位数据"}
            
            # 统计分析
            analysis = {
                "total_positions": len(docs),
                "companies": set(),
                "locations": set(),
                "skills": {},
                "salary_ranges": [],
                "experience_requirements": {},
                "education_requirements": {}
            }
            
            for doc in docs:
                metadata = doc.metadata
                
                # 公司统计
                if metadata.get("company"):
                    analysis["companies"].add(metadata["company"])
                
                # 地点统计
                if metadata.get("location"):
                    analysis["locations"].add(metadata["location"])
                
                # 技能统计
                skills = metadata.get("skills", [])
                for skill in skills:
                    analysis["skills"][skill] = analysis["skills"].get(skill, 0) + 1
                
                # 薪资统计
                salary_min = metadata.get("salary_min")
                salary_max = metadata.get("salary_max")
                if salary_min and salary_max:
                    analysis["salary_ranges"].append((salary_min, salary_max))
                
                # 经验要求统计
                experience = metadata.get("experience", "不限")
                analysis["experience_requirements"][experience] = \
                    analysis["experience_requirements"].get(experience, 0) + 1
                
                # 学历要求统计
                education = metadata.get("education", "不限")
                analysis["education_requirements"][education] = \
                    analysis["education_requirements"].get(education, 0) + 1
            
            # 转换集合为列表
            analysis["companies"] = list(analysis["companies"])
            analysis["locations"] = list(analysis["locations"])
            
            # 计算薪资统计
            if analysis["salary_ranges"]:
                salaries = analysis["salary_ranges"]
                avg_min = sum(s[0] for s in salaries) / len(salaries)
                avg_max = sum(s[1] for s in salaries) / len(salaries)
                analysis["average_salary"] = {
                    "min": round(avg_min),
                    "max": round(avg_max)
                }
            
            # 热门技能排序
            analysis["top_skills"] = sorted(
                analysis["skills"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            logger.info(f"完成职位市场分析，涵盖 {len(docs)} 个职位")
            return analysis
            
        except Exception as e:
            logger.error(f"职位市场分析失败: {e}")
            return {"error": str(e)}