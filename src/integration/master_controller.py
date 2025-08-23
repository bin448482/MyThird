"""
统一主控制器 (MasterController)
协调整个端到端流程的执行
"""

import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from ..extraction.content_extractor import ContentExtractor
from ..rag.rag_system_coordinator import RAGSystemCoordinator
from ..matcher.generic_resume_matcher import GenericResumeJobMatcher
from .data_bridge import DataBridge
from .job_scheduler import JobScheduler
from .decision_engine import DecisionEngine
from .auto_submission_engine import AutoSubmissionEngine

logger = logging.getLogger(__name__)

@dataclass
class PipelineConfig:
    """流水线配置"""
    search_keywords: List[str]
    search_locations: List[str] = None
    max_jobs_per_keyword: int = 40  # 总40个职位
    max_pages: int = 2              # 测试2页
    resume_profile: Dict[str, Any] = None
    decision_criteria: Dict[str, Any] = None
    submission_config: Dict[str, Any] = None

@dataclass
class ExecutionReport:
    """执行报告"""
    pipeline_id: str
    start_time: datetime
    end_time: datetime
    total_execution_time: float
    extraction_result: Dict[str, Any]
    rag_result: Dict[str, Any]
    matching_result: Dict[str, Any]
    decision_result: Dict[str, Any]
    submission_result: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None

class PipelineError(Exception):
    """流水线执行错误"""
    pass

class MasterController:
    """统一主控制器 - 协调整个端到端流程"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pipeline_id = f"pipeline_{int(time.time())}"
        
        # 初始化所有子模块
        self.job_extractor = ContentExtractor(config)
        self.rag_coordinator = RAGSystemCoordinator(config)
        
        # 初始化向量管理器（从RAG协调器获取）
        vector_manager = self.rag_coordinator.vector_manager
        self.resume_matcher = GenericResumeJobMatcher(vector_manager, config)
        
        self.decision_engine = DecisionEngine(config)
        self.auto_submitter = AutoSubmissionEngine(config)
        self.data_bridge = DataBridge(config)
        self.job_scheduler = JobScheduler(config)
        
        # 执行状态
        self.current_stage = "initialized"
        self.execution_stats = {
            'total_jobs_processed': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'stage_timings': {}
        }
    
    async def run_full_pipeline(self, pipeline_config: PipelineConfig) -> ExecutionReport:
        """执行完整的端到端流水线"""
        start_time = datetime.now()
        logger.info(f"开始执行流水线 {self.pipeline_id}")
        
        try:
            # 阶段1: 职位提取
            logger.info("开始阶段1: 职位提取")
            self.current_stage = "job_extraction"
            extraction_result = await self._execute_job_extraction(pipeline_config)
            
            # 打印提取的内容进行调试
            logger.info(f"=== 职位提取结果调试 ===")
            logger.info(f"提取成功: {extraction_result.get('success', False)}")
            logger.info(f"提取数量: {extraction_result.get('total_extracted', 0)}")
            logger.info(f"关键词处理数量: {extraction_result.get('keywords_processed', 0)}")
            
            if extraction_result.get('jobs'):
                logger.info(f"前5条职位详情:")
                for i, job in enumerate(extraction_result['jobs'][:5]):
                    logger.info(f"职位 {i+1}: {job}")
            else:
                logger.warning("没有提取到任何职位数据")
            
            if not extraction_result['success']:
                raise PipelineError(f"职位提取失败: {extraction_result.get('error', 'Unknown error')}")
            
            # 暂时注释掉其他阶段，专注调试第一阶段
            # 阶段2: RAG处理 - 从数据库读取未处理的职位
            logger.info("开始阶段2: RAG处理")
            self.current_stage = "rag_processing"
            rag_result = await self._execute_rag_processing_from_database()
            
            if not rag_result['success']:
                raise PipelineError(f"RAG处理失败: {rag_result.get('error', 'Unknown error')}")
            
            # 阶段3: 简历匹配并保存结果到数据库
            logger.info("开始阶段3: 简历匹配")
            self.current_stage = "resume_matching"
            matching_result = await self._execute_resume_matching_with_database_save(pipeline_config.resume_profile)
            
            if not matching_result['success']:
                raise PipelineError(f"简历匹配失败: {matching_result.get('error', 'Unknown error')}")
            
            # # 阶段4: 智能决策
            # logger.info("开始阶段4: 智能决策")
            # self.current_stage = "intelligent_decision"
            # decision_result = await self._execute_intelligent_decision(matching_result, pipeline_config.decision_criteria)
            
            # if not decision_result['success']:
            #     raise PipelineError(f"智能决策失败: {decision_result.get('error', 'Unknown error')}")
            
            # # 阶段5: 自动投递
            # logger.info("开始阶段5: 自动投递")
            # self.current_stage = "auto_submission"
            # submission_result = await self._execute_auto_submission(decision_result, pipeline_config.submission_config)
            
            # 创建模拟的其他阶段结果用于测试
            decision_result = {'success': True, 'recommended_submissions': 0}
            submission_result = {'success': True, 'successful_submissions': 0}
            
            # 生成执行报告
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # 使用实际的extraction_result，如果没有则创建空的
            extraction_result = getattr(self, '_last_extraction_result', {'success': True, 'total_extracted': 0})
            
            report = ExecutionReport(
                pipeline_id=self.pipeline_id,
                start_time=start_time,
                end_time=end_time,
                total_execution_time=execution_time,
                extraction_result=extraction_result,
                rag_result=rag_result,
                matching_result=matching_result,
                decision_result=decision_result,
                submission_result=submission_result,
                success=True
            )
            
            logger.info(f"流水线 {self.pipeline_id} 执行完成，耗时 {execution_time:.2f} 秒")
            return report
            
        except Exception as e:
            logger.error(f"流水线执行失败: {e}")
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            return ExecutionReport(
                pipeline_id=self.pipeline_id,
                start_time=start_time,
                end_time=end_time,
                total_execution_time=execution_time,
                extraction_result=getattr(self, '_last_extraction_result', {}),
                rag_result=getattr(self, '_last_rag_result', {}),
                matching_result=getattr(self, '_last_matching_result', {}),
                decision_result=getattr(self, '_last_decision_result', {}),
                submission_result=getattr(self, '_last_submission_result', {}),
                success=False,
                error_message=str(e)
            )
    
    async def _execute_job_extraction(self, pipeline_config: PipelineConfig) -> Dict[str, Any]:
        """执行职位提取阶段（异步接口，内部调用同步方法）"""
        return self._execute_job_extraction_sync(pipeline_config)
    
    def _execute_job_extraction_sync(self, pipeline_config: PipelineConfig) -> Dict[str, Any]:
        """执行职位提取阶段（同步方法）"""
        stage_start = time.time()
        
        try:
            combined_results = []
            
            # 顺序执行每个关键词的提取任务（避免Selenium并发问题）
            for i, keyword in enumerate(pipeline_config.search_keywords, 1):
                logger.info(f"开始处理关键词 {i}/{len(pipeline_config.search_keywords)}: '{keyword}'")
                
                try:
                    # 同步调用ContentExtractor
                    keyword_results = self.job_extractor.extract_from_keyword(
                        keyword=keyword,
                        max_results=pipeline_config.max_jobs_per_keyword,
                        save_results=True,
                        extract_details=True,
                        max_pages=pipeline_config.max_pages
                    )
                    
                    logger.info(f"关键词 '{keyword}' 提取完成: {len(keyword_results)} 个职位")
                    combined_results.extend(keyword_results)
                    
                    # 关键词之间添加短暂间隔，避免过于频繁的请求
                    if i < len(pipeline_config.search_keywords):
                        logger.info(f"等待 10 秒后处理下一个关键词...")
                        time.sleep(10)
                        
                except Exception as e:
                    logger.error(f"处理关键词 '{keyword}' 失败: {e}")
                    # 继续处理下一个关键词，不中断整个流程
                    continue
            
            stage_time = time.time() - stage_start
            self.execution_stats['stage_timings']['extraction'] = stage_time
            
            result = {
                'success': True,
                'total_extracted': len(combined_results),
                'jobs': combined_results,
                'extraction_time': stage_time,
                'keywords_processed': len(pipeline_config.search_keywords)
            }
            
            self._last_extraction_result = result
            return result
            
        except Exception as e:
            logger.error(f"职位提取失败: {e}")
            result = {'success': False, 'error': str(e)}
            self._last_extraction_result = result
            return result
    
    def _extract_jobs_for_keyword_sync(self, keyword: str, max_results: int, max_pages: int) -> List[Dict]:
        """为单个关键词提取职位（同步方法）"""
        logger.info(f"开始为关键词 '{keyword}' 提取职位，最大结果数: {max_results}, 最大页数: {max_pages}")
        
        try:
            # 调用真实的ContentExtractor（同步方法）
            extracted_jobs = self.job_extractor.extract_from_keyword(
                keyword=keyword,
                max_results=max_results,
                save_results=True,
                extract_details=True,  # 提取详情
                max_pages=max_pages
            )
            
            logger.info(f"ContentExtractor 为关键词 '{keyword}' 提取了 {len(extracted_jobs)} 个职位")
            
            # 打印前5条提取的职位详情
            for i, job in enumerate(extracted_jobs[:5]):
                logger.info(f"提取职位 {i+1}: 标题={job.get('title', 'N/A')}, 公司={job.get('company', 'N/A')}, 地点={job.get('location', 'N/A')}")
            
            return extracted_jobs
            
        except Exception as e:
            logger.error(f"ContentExtractor 提取职位失败: {e}")
            # 如果真实提取失败，返回空列表而不是模拟数据
            logger.warning("提取失败，返回空结果")
            return []
    
    def _merge_extraction_results(self, results: List) -> List[Dict]:
        """合并提取结果"""
        combined = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"提取任务失败: {result}")
                continue
            if isinstance(result, list):
                combined.extend(result)
        return combined
    
    async def _execute_rag_processing_from_database(self) -> Dict[str, Any]:
        """执行RAG处理阶段 - 从数据库读取未处理的职位"""
        stage_start = time.time()
        
        try:
            # 初始化RAG系统（如果尚未初始化）
            if not self.rag_coordinator.is_initialized:
                logger.info("初始化RAG系统...")
                init_success = self.rag_coordinator.initialize_system()
                if not init_success:
                    logger.warning("RAG系统初始化失败，但继续处理...")
            
            # 直接从数据库读取未处理的职位进行RAG处理
            rag_result = await self.rag_coordinator.import_database_jobs(
                batch_size=50,
                force_reprocess=False
            )
            
            stage_time = time.time() - stage_start
            self.execution_stats['stage_timings']['rag_processing'] = stage_time
            
            result = {
                'success': True,
                'processed_count': rag_result.get('total_imported', 0),
                'processing_time': stage_time,
                'success_rate': rag_result.get('success_rate', 0),
                'vector_db_stats': rag_result.get('vector_db_stats', {})
            }
            
            self._last_rag_result = result
            return result
            
        except Exception as e:
            logger.error(f"RAG处理失败: {e}")
            result = {'success': False, 'error': str(e)}
            self._last_rag_result = result
            return result
    
    async def _execute_rag_processing(self, extraction_result: Dict[str, Any]) -> Dict[str, Any]:
        """执行RAG处理阶段（保留原方法用于兼容性）"""
        stage_start = time.time()
        
        try:
            # 初始化RAG系统（如果尚未初始化）
            if not self.rag_coordinator.is_initialized:
                logger.info("初始化RAG系统...")
                init_success = self.rag_coordinator.initialize_system()
                if not init_success:
                    logger.warning("RAG系统初始化失败，但继续处理...")
            
            # 将提取的职位数据转换为RAG输入格式
            rag_input = self.data_bridge.transform_extraction_to_rag(extraction_result)
            
            # 批量处理职位数据
            rag_result = await self.rag_coordinator.import_database_jobs(
                batch_size=50,
                force_reprocess=False
            )
            
            stage_time = time.time() - stage_start
            self.execution_stats['stage_timings']['rag_processing'] = stage_time
            
            result = {
                'success': True,
                'processed_count': rag_result.get('total_imported', 0),
                'processing_time': stage_time,
                'success_rate': rag_result.get('success_rate', 0),
                'vector_db_stats': rag_result.get('vector_db_stats', {})
            }
            
            self._last_rag_result = result
            return result
            
        except Exception as e:
            logger.error(f"RAG处理失败: {e}")
            result = {'success': False, 'error': str(e)}
            self._last_rag_result = result
            return result
    
    async def _execute_resume_matching_with_database_save(self, resume_profile: Dict[str, Any]) -> Dict[str, Any]:
        """执行简历匹配阶段并保存结果到数据库"""
        stage_start = time.time()
        
        try:
            # 将字典转换为GenericResumeProfile对象
            from ..matcher.generic_resume_models import GenericResumeProfile
            if isinstance(resume_profile, dict):
                # 转换简化格式到完整格式
                resume_profile_obj = self._convert_simple_resume_profile(resume_profile)
            else:
                resume_profile_obj = resume_profile
            
            # 执行简历匹配
            matching_result = await self.resume_matcher.find_matching_jobs(
                resume_profile=resume_profile_obj,
                top_k=50
            )
            
            # 保存匹配结果到数据库
            saved_count = await self._save_matching_results_to_database(matching_result, resume_profile_obj)
            
            stage_time = time.time() - stage_start
            self.execution_stats['stage_timings']['matching'] = stage_time
            
            result = {
                'success': True,
                'total_matches': matching_result.matching_summary.total_matches,
                'high_priority': matching_result.matching_summary.high_priority,
                'medium_priority': matching_result.matching_summary.medium_priority,
                'low_priority': matching_result.matching_summary.low_priority,
                'matches': matching_result.matches,
                'saved_to_database': saved_count,
                'processing_time': stage_time
            }
            
            self._last_matching_result = result
            return result
            
        except Exception as e:
            logger.error(f"简历匹配失败: {e}")
            result = {'success': False, 'error': str(e)}
            self._last_matching_result = result
            return result
    
    async def _execute_resume_matching(self, rag_result: Dict[str, Any], resume_profile: Dict[str, Any]) -> Dict[str, Any]:
        """执行简历匹配阶段（保留原方法用于兼容性）"""
        stage_start = time.time()
        
        try:
            # 将字典转换为GenericResumeProfile对象
            from ..matcher.generic_resume_models import GenericResumeProfile
            if isinstance(resume_profile, dict):
                # 转换简化格式到完整格式
                resume_profile_obj = self._convert_simple_resume_profile(resume_profile)
            else:
                resume_profile_obj = resume_profile
            
            # 执行简历匹配
            matching_result = await self.resume_matcher.find_matching_jobs(
                resume_profile=resume_profile_obj,
                top_k=50
            )
            
            stage_time = time.time() - stage_start
            self.execution_stats['stage_timings']['matching'] = stage_time
            
            result = {
                'success': True,
                'total_matches': matching_result.matching_summary.total_matches,
                'high_priority': matching_result.matching_summary.high_priority,
                'medium_priority': matching_result.matching_summary.medium_priority,
                'low_priority': matching_result.matching_summary.low_priority,
                'matches': matching_result.matches,
                'processing_time': stage_time
            }
            
            self._last_matching_result = result
            return result
            
        except Exception as e:
            logger.error(f"简历匹配失败: {e}")
            result = {'success': False, 'error': str(e)}
            self._last_matching_result = result
            return result
    
    async def _save_matching_results_to_database(self, matching_result, resume_profile) -> int:
        """保存匹配结果到数据库"""
        try:
            from ..database.operations import DatabaseManager
            
            # 获取数据库管理器
            db_manager = DatabaseManager(self.config.get('database_path', 'data/jobs.db'))
            
            # 准备匹配结果数据
            match_records = []
            resume_profile_id = getattr(resume_profile, 'profile_id', 'default')
            
            for match in matching_result.matches:
                # 获取优先级，如果没有则根据分数计算
                priority_level = getattr(match, 'priority_level', None)
                if not priority_level:
                    if match.overall_score >= 0.8:
                        priority_level = 'high'
                    elif match.overall_score >= 0.6:
                        priority_level = 'medium'
                    else:
                        priority_level = 'low'
                
                match_data = {
                    'job_id': match.job_id,
                    'resume_profile_id': resume_profile_id,
                    'match_score': match.overall_score,
                    'priority_level': priority_level,
                    'semantic_score': getattr(match, 'semantic_score', None),
                    'skill_match_score': getattr(match.dimension_scores, 'skills_match', None) if hasattr(match, 'dimension_scores') else None,
                    'experience_match_score': getattr(match.dimension_scores, 'experience_match', None) if hasattr(match, 'dimension_scores') else None,
                    'location_match_score': getattr(match.dimension_scores, 'location_match', None) if hasattr(match, 'dimension_scores') else None,
                    'salary_match_score': getattr(match.dimension_scores, 'salary_match', None) if hasattr(match, 'dimension_scores') else None,
                    'match_details': str(getattr(match, 'match_analysis', {})),
                    'match_reasons': ', '.join(getattr(match.match_analysis, 'strengths', []) if hasattr(match, 'match_analysis') else [])
                }
                match_records.append(match_data)
            
            # 批量保存到数据库
            saved_count = db_manager.batch_save_resume_matches(match_records)
            
            logger.info(f"保存匹配结果到数据库: {saved_count}/{len(match_records)} 成功")
            return saved_count
            
        except Exception as e:
            logger.error(f"保存匹配结果到数据库失败: {e}")
            return 0
    
    def _convert_simple_resume_profile(self, simple_profile: Dict[str, Any]):
        """将简化的简历格式转换为GenericResumeProfile对象"""
        from ..matcher.generic_resume_models import GenericResumeProfile, SkillCategory
        
        # 如果已经是完整格式，直接使用from_dict
        if 'skill_categories' in simple_profile:
            return GenericResumeProfile.from_dict(simple_profile)
        
        # 创建基本的简历对象（简化格式）
        profile = GenericResumeProfile(
            name=simple_profile.get('name', ''),
            total_experience_years=simple_profile.get('experience_years', 0),
            current_position=simple_profile.get('current_position', '')
        )
        
        # 处理技能 - 如果是简单列表，转换为技能分类
        skills = simple_profile.get('skills', [])
        if skills:
            # 创建一个通用技能分类
            skill_category = SkillCategory(
                category_name='core_skills',
                skills=skills,
                proficiency_level='intermediate'
            )
            profile.skill_categories.append(skill_category)
        
        # 处理教育背景
        education = simple_profile.get('education', '')
        if education:
            from ..matcher.generic_resume_models import Education
            edu = Education(
                degree=education,
                major='',
                university='',
                graduation_year=''
            )
            profile.education.append(edu)
        
        return profile
    
    async def _execute_intelligent_decision(self, matching_result: Dict[str, Any], decision_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """执行智能决策阶段"""
        stage_start = time.time()
        
        try:
            # 制定投递决策
            decision_result = await self.decision_engine.make_submission_decisions(
                matching_result=matching_result,
                decision_criteria=decision_criteria or {}
            )
            
            stage_time = time.time() - stage_start
            self.execution_stats['stage_timings']['decision'] = stage_time
            
            result = {
                'success': True,
                'total_evaluated': decision_result.get('total_evaluated', 0),
                'recommended_submissions': decision_result.get('recommended_submissions', 0),
                'decisions': decision_result.get('decisions', []),
                'processing_time': stage_time
            }
            
            self._last_decision_result = result
            return result
            
        except Exception as e:
            logger.error(f"智能决策失败: {e}")
            result = {'success': False, 'error': str(e)}
            self._last_decision_result = result
            return result
    
    async def _execute_auto_submission(self, decision_result: Dict[str, Any], submission_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行自动投递阶段"""
        stage_start = time.time()
        
        try:
            # 执行自动投递
            submission_result = await self.auto_submitter.submit_applications(
                decision_result=decision_result,
                submission_config=submission_config or {}
            )
            
            stage_time = time.time() - stage_start
            self.execution_stats['stage_timings']['submission'] = stage_time
            
            result = {
                'success': True,
                'total_attempts': submission_result.get('total_attempts', 0),
                'successful_submissions': submission_result.get('successful_submissions', 0),
                'failed_submissions': submission_result.get('failed_submissions', 0),
                'submission_details': submission_result.get('submission_details', []),
                'processing_time': stage_time
            }
            
            self._last_submission_result = result
            return result
            
        except Exception as e:
            logger.error(f"自动投递失败: {e}")
            result = {'success': False, 'error': str(e)}
            self._last_submission_result = result
            return result
    
    def get_current_status(self) -> Dict[str, Any]:
        """获取当前执行状态"""
        return {
            'pipeline_id': self.pipeline_id,
            'current_stage': self.current_stage,
            'execution_stats': self.execution_stats,
            'stage_timings': self.execution_stats.get('stage_timings', {})
        }
    
    def generate_execution_summary(self, report: ExecutionReport) -> Dict[str, Any]:
        """生成执行摘要"""
        return {
            'pipeline_id': report.pipeline_id,
            'execution_time': report.total_execution_time,
            'success': report.success,
            'error_message': report.error_message,
            'stage_results': {
                'extraction': {
                    'jobs_extracted': report.extraction_result.get('total_extracted', 0),
                    'success': report.extraction_result.get('success', False)
                },
                'rag_processing': {
                    'jobs_processed': report.rag_result.get('processed_count', 0),
                    'success': report.rag_result.get('success', False)
                },
                'matching': {
                    'matches_found': report.matching_result.get('total_matches', 0),
                    'success': report.matching_result.get('success', False)
                },
                'decision': {
                    'recommended_submissions': report.decision_result.get('recommended_submissions', 0),
                    'success': report.decision_result.get('success', False)
                },
                'submission': {
                    'successful_submissions': report.submission_result.get('successful_submissions', 0),
                    'success': report.submission_result.get('success', False)
                }
            },
            'recommendations': self._generate_optimization_recommendations(report)
        }
    
    def _generate_optimization_recommendations(self, report: ExecutionReport) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 基于执行时间的建议
        if report.total_execution_time > 1800:  # 30分钟
            recommendations.append("考虑增加并发处理数量以提高整体执行效率")
        
        # 基于各阶段性能的建议
        if report.rag_result.get('processing_time', 0) > 600:  # 10分钟
            recommendations.append("RAG处理时间较长，建议优化批处理大小或增加缓存")
        
        if report.matching_result.get('total_matches', 0) < 10:
            recommendations.append("匹配结果较少，建议调整匹配阈值或扩大搜索范围")
        
        if report.submission_result.get('successful_submissions', 0) == 0:
            recommendations.append("投递成功率为0，建议检查投递配置和网络连接")
        
        return recommendations
    
    def reset_rag_processing_status(self, job_ids: List[str] = None) -> int:
        """
        重置RAG处理状态，支持重新处理
        
        Args:
            job_ids: 要重置的职位ID列表，None表示重置所有
            
        Returns:
            重置的记录数
        """
        try:
            from ..database.operations import DatabaseManager
            db_manager = DatabaseManager(self.config.get('database_path', 'data/jobs.db'))
            
            reset_count = db_manager.reset_rag_processing_status(job_ids)
            logger.info(f"重置RAG处理状态: {reset_count} 个职位")
            return reset_count
            
        except Exception as e:
            logger.error(f"重置RAG处理状态失败: {e}")
            return 0
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """
        获取处理统计信息
        
        Returns:
            统计信息字典
        """
        try:
            from ..database.operations import DatabaseManager
            db_manager = DatabaseManager(self.config.get('database_path', 'data/jobs.db'))
            
            # 获取RAG处理统计
            rag_stats = db_manager.get_rag_processing_stats()
            
            # 获取匹配结果统计
            match_stats = db_manager.get_match_statistics()
            
            # 获取基本统计
            basic_stats = db_manager.get_statistics()
            
            return {
                'basic_stats': basic_stats,
                'rag_processing': rag_stats,
                'matching_results': match_stats,
                'pipeline_id': self.pipeline_id,
                'current_stage': self.current_stage
            }
            
        except Exception as e:
            logger.error(f"获取处理统计失败: {e}")
            return {}
    
    async def run_stage_only(self, stage: str, pipeline_config: PipelineConfig) -> Dict[str, Any]:
        """
        只运行指定阶段
        
        Args:
            stage: 阶段名称 ('rag_processing', 'resume_matching', 'decision', 'submission')
            pipeline_config: 流水线配置
            
        Returns:
            阶段执行结果
        """
        logger.info(f"开始执行单独阶段: {stage}")
        
        try:
            if stage == 'rag_processing':
                return await self._execute_rag_processing_from_database()
            elif stage == 'resume_matching':
                return await self._execute_resume_matching_with_database_save(pipeline_config.resume_profile)
            elif stage == 'decision':
                # 需要先获取匹配结果
                logger.warning("决策阶段需要匹配结果，建议先运行匹配阶段")
                return {'success': False, 'error': '需要先运行匹配阶段'}
            elif stage == 'submission':
                # 需要先获取决策结果
                logger.warning("投递阶段需要决策结果，建议先运行决策阶段")
                return {'success': False, 'error': '需要先运行决策阶段'}
            else:
                return {'success': False, 'error': f'未知阶段: {stage}'}
                
        except Exception as e:
            logger.error(f"执行阶段 {stage} 失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def validate_pipeline_readiness(self) -> Dict[str, Any]:
        """
        验证流水线准备状态
        
        Returns:
            验证结果
        """
        try:
            from ..database.operations import DatabaseManager
            db_manager = DatabaseManager(self.config.get('database_path', 'data/jobs.db'))
            
            # 检查数据库中的数据状态
            stats = db_manager.get_statistics()
            rag_stats = db_manager.get_rag_processing_stats()
            
            readiness = {
                'database_ready': stats.get('total', 0) > 0,
                'jobs_available': stats.get('total', 0),
                'rag_ready': rag_stats.get('processed', 0) > 0,
                'rag_processed_count': rag_stats.get('processed', 0),
                'unprocessed_count': rag_stats.get('unprocessed', 0),
                'recommendations': []
            }
            
            # 生成建议
            if not readiness['database_ready']:
                readiness['recommendations'].append("需要先运行职位提取阶段，数据库中没有职位数据")
            
            if readiness['jobs_available'] > 0 and rag_stats.get('unprocessed', 0) > 0:
                readiness['recommendations'].append(f"有 {rag_stats.get('unprocessed', 0)} 个职位需要RAG处理")
            
            if rag_stats.get('processed', 0) > 0:
                readiness['recommendations'].append(f"可以开始简历匹配，已有 {rag_stats.get('processed', 0)} 个职位完成RAG处理")
            
            return readiness
            
        except Exception as e:
            logger.error(f"验证流水线准备状态失败: {e}")
            return {'database_ready': False, 'error': str(e)}