#!/usr/bin/env python3
"""
批量重新匹配脚本
用于修复低匹配率问题，重新匹配所有未匹配的职位
参考 test_optimized_matching.py 的优化配置
"""

import asyncio
import sys
import os
import time
import json
import sqlite3
import yaml
from typing import List, Dict, Any
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(__file__))

from src.database.operations import DatabaseManager
from src.rag.vector_manager import ChromaDBManager
from src.matcher.generic_resume_matcher import GenericResumeJobMatcher
from src.matcher.generic_resume_models import GenericResumeProfile, SkillCategory, WorkExperience
from src.utils.logger import get_logger


def load_integration_config(config_path: str = "config/integration_config.yaml") -> dict:
    """加载集成配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"⚠️ 无法加载配置文件 {config_path}: {e}")
        return {}


class BatchRematcher:
    """批量重新匹配器"""
    
    def __init__(self, db_path: str = 'data/jobs.db'):
        self.db_path = db_path
        self.logger = get_logger(__name__)
        
        # 加载集成配置
        self.integration_config = load_integration_config()
        
        # 初始化向量管理器
        self.vector_manager = self._init_vector_manager()
        
        # 初始化数据库管理器
        self.db_manager = DatabaseManager(db_path)
        
        # 加载优化配置并初始化匹配器
        config = self._load_optimized_config()
        self.matcher = GenericResumeJobMatcher(self.vector_manager, config)
        
        # 统计信息
        self.stats = {
            'total_jobs': 0,
            'unmatched_jobs': 0,
            'processed_jobs': 0,
            'new_matches': 0,
            'failed_jobs': 0,
            'start_time': None,
            'end_time': None
        }
    
    def _init_vector_manager(self) -> ChromaDBManager:
        """初始化向量管理器 - 参考 test_optimized_matching.py"""
        try:
            # 从集成配置中提取向量数据库配置
            rag_config = self.integration_config.get('rag_system', {})
            vector_db_config = rag_config.get('vector_db', {})
            llm_config = rag_config.get('llm', {})
            
            # 构建向量管理器配置
            vector_manager_config = {
                'persist_directory': vector_db_config.get('persist_directory', './chroma_db'),
                'collection_name': vector_db_config.get('collection_name', 'job_positions'),
                'embeddings': {
                    'model_name': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                    'device': 'cpu',
                    'normalize_embeddings': True
                },
                'llm': {
                    'provider': llm_config.get('provider', 'zhipu'),
                    'model': llm_config.get('model', 'glm-4-flash'),
                    'api_key': llm_config.get('api_key', ''),
                    'temperature': llm_config.get('temperature', 0.1),
                    'max_tokens': llm_config.get('max_tokens', 1500)
                }
            }
            
            self.logger.info(f"📁 向量数据库目录: {vector_manager_config['persist_directory']}")
            self.logger.info(f"📚 集合名称: {vector_manager_config['collection_name']}")
            
            return ChromaDBManager(vector_manager_config)
            
        except Exception as e:
            self.logger.error(f"向量管理器初始化失败: {e}")
            self.logger.info("这可能是由于Hugging Face连接问题导致的")
            self.logger.info("建议解决方案:")
            self.logger.info("1. 检查网络连接")
            self.logger.info("2. 使用VPN或代理")
            self.logger.info("3. 预先下载模型到本地")
            raise
    
    def _load_optimized_config(self) -> Dict[str, Any]:
        """加载优化配置 - 参考 test_optimized_matching.py"""
        # 从集成配置中提取匹配算法配置
        resume_matching_config = self.integration_config.get('modules', {}).get('resume_matching', {})
        
        # 优先使用高级匹配配置
        advanced_matching_config = self.integration_config.get('resume_matching_advanced', {})
        
        if advanced_matching_config:
            self.logger.info("🚀 使用高级匹配配置")
            # 使用高级配置的权重和阈值
            config = {
                'min_score_threshold': advanced_matching_config.get('match_thresholds', {}).get('poor', 0.25),
                'default_search_k': 80,
                'max_results': resume_matching_config.get('max_matches_per_resume', 30),
                'weights': advanced_matching_config.get('matching_weights', {
                    'semantic_similarity': 0.40,
                    'skills_match': 0.35,
                    'experience_match': 0.15,
                    'industry_match': 0.08,
                    'salary_match': 0.02
                })
            }
            self.logger.info(f"📊 高级配置权重: {config['weights']}")
        else:
            self.logger.info("📋 使用标准优化配置")
            # 构建优化的匹配器配置
            config = {
                'min_score_threshold': 0.25,  # 降低阈值从0.3到0.25
                'default_search_k': 80,       # 增加搜索范围
                'max_results': resume_matching_config.get('max_matches_per_resume', 30),
                'weights': {
                    'semantic_similarity': 0.40,  # 提高语义相似度权重
                    'skills_match': 0.35,         # 提高技能匹配权重
                    'experience_match': 0.15,     # 降低经验权重
                    'industry_match': 0.08,       # 降低行业权重
                    'salary_match': 0.02          # 大幅降低薪资权重
                }
            }
        
        self.logger.info(f"📋 使用配置: 阈值={config['min_score_threshold']}, 最大结果={config['max_results']}")
        return config
    
    async def run_batch_rematch(self, limit: int = None) -> Dict[str, Any]:
        """运行批量重新匹配"""
        self.stats['start_time'] = datetime.now()
        
        try:
            self.logger.info("🚀 开始批量重新匹配任务")
            
            # 1. 分析当前状态
            await self._analyze_current_state()
            
            # 2. 获取未匹配的职位
            unmatched_jobs = await self._get_unmatched_jobs(limit)
            
            if not unmatched_jobs:
                self.logger.info("✅ 没有找到需要重新匹配的职位")
                return self._generate_report()
            
            self.logger.info(f"📋 找到 {len(unmatched_jobs)} 个未匹配职位")
            
            # 3. 创建简历档案
            resume_profile = await self._create_resume_profile()
            
            # 4. 批量匹配
            await self._batch_match_jobs(unmatched_jobs, resume_profile)
            
            # 5. 生成报告
            self.stats['end_time'] = datetime.now()
            report = self._generate_report()
            
            self.logger.info("✅ 批量重新匹配完成")
            self.logger.info(f"📊 处理结果: 新增匹配 {self.stats['new_matches']}, "
                           f"失败 {self.stats['failed_jobs']}, "
                           f"耗时 {(self.stats['end_time'] - self.stats['start_time']).total_seconds():.1f}秒")
            
            return report
            
        except Exception as e:
            self.logger.error(f"💥 批量重新匹配失败: {str(e)}")
            raise
    
    async def _analyze_current_state(self):
        """分析当前匹配状态"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 总职位数
            cursor.execute("SELECT COUNT(*) FROM jobs WHERE rag_processed = 1")
            self.stats['total_jobs'] = cursor.fetchone()[0]
            
            # 已匹配职位数
            cursor.execute("SELECT COUNT(DISTINCT job_id) FROM resume_matches")
            matched_jobs = cursor.fetchone()[0]
            
            # 未匹配职位数
            self.stats['unmatched_jobs'] = self.stats['total_jobs'] - matched_jobs
            
            # 当前匹配率
            current_match_rate = matched_jobs / self.stats['total_jobs'] if self.stats['total_jobs'] > 0 else 0
            
            conn.close()
            
            self.logger.info(f"📊 当前状态分析:")
            self.logger.info(f"   总职位数: {self.stats['total_jobs']}")
            self.logger.info(f"   已匹配: {matched_jobs}")
            self.logger.info(f"   未匹配: {self.stats['unmatched_jobs']}")
            self.logger.info(f"   匹配率: {current_match_rate:.1%}")
            
        except Exception as e:
            self.logger.error(f"分析当前状态失败: {str(e)}")
            raise
    
    async def _get_unmatched_jobs(self, limit: int = None) -> List[str]:
        """获取未匹配的职位ID列表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = """
                SELECT job_id FROM jobs 
                WHERE rag_processed = 1 
                AND job_id NOT IN (SELECT DISTINCT job_id FROM resume_matches)
                ORDER BY created_at DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query)
            unmatched_jobs = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            return unmatched_jobs
            
        except Exception as e:
            self.logger.error(f"获取未匹配职位失败: {str(e)}")
            return []
    
    async def _create_resume_profile(self) -> GenericResumeProfile:
        """创建简历档案 - 参考 test_optimized_matching.py"""
        try:
            # 尝试从文件加载
            resume_file = 'testdata/resume.json'
            if os.path.exists(resume_file):
                with open(resume_file, 'r', encoding='utf-8') as f:
                    resume_data = json.load(f)
                profile = GenericResumeProfile.from_dict(resume_data)
                self.logger.info(f"✅ 从 {resume_file} 加载简历档案: {profile.name}")
                return profile
        except Exception as e:
            self.logger.warning(f"从文件加载简历失败: {e}")
        
        # 创建默认档案 - 与 test_optimized_matching.py 保持一致
        self.logger.info("使用默认简历档案")
        return GenericResumeProfile(
            name="占彬 (Zhan Bin)",
            total_experience_years=20,
            current_position="数据平台架构师",
            skill_categories=[
                SkillCategory(
                    category_name="programming_languages",
                    skills=["Python", "Java", "C#", "JavaScript", "Go"],
                    proficiency_level="expert"
                ),
                SkillCategory(
                    category_name="ai_ml_skills",
                    skills=["机器学习", "深度学习", "AI", "PyTorch", "TensorFlow"],
                    proficiency_level="advanced"
                ),
                SkillCategory(
                    category_name="data_engineering_skills",
                    skills=["Databricks", "Spark", "数据架构", "数据治理", "项目管理"],
                    proficiency_level="advanced"
                )
            ],
            work_history=[
                WorkExperience(
                    company="Zoetis",
                    position="数据平台架构师",
                    industry="制药/医疗",
                    duration_years=0.8,
                    technologies=["Databricks", "Azure", "Python"]
                )
            ],
            expected_salary_range={"min": 300000, "max": 500000},
            industry_experience={"制药/医疗": 6.4, "IT/互联网": 5.8}
        )
    
    async def _batch_match_jobs(self, job_ids: List[str], resume_profile: GenericResumeProfile):
        """批量匹配职位"""
        batch_size = 10  # 减少批次大小，提高稳定性
        
        for i in range(0, len(job_ids), batch_size):
            batch = job_ids[i:i + batch_size]
            batch_num = i//batch_size + 1
            total_batches = (len(job_ids) + batch_size - 1)//batch_size
            
            self.logger.info(f"🔄 处理批次 {batch_num}/{total_batches}, 职位数: {len(batch)}")
            self.logger.info(f"📊 当前进度: {i + len(batch)}/{len(job_ids)} ({((i + len(batch))/len(job_ids)*100):.1f}%)")
            
            await self._process_job_batch(batch, resume_profile)
            
            # 短暂休息避免过载
            await asyncio.sleep(2)  # 增加休息时间
    
    async def _process_job_batch(self, job_ids: List[str], resume_profile: GenericResumeProfile):
        """处理一批职位"""
        for job_id in job_ids:
            try:
                self.stats['processed_jobs'] += 1
                
                # 构建职位过滤器
                filters = {"job_id": job_id}
                
                # 执行匹配
                result = await self.matcher.find_matching_jobs(
                    resume_profile,
                    filters=filters,
                    top_k=1
                )
                
                # 保存匹配结果
                if result.matches:
                    await self._save_match_result(result.matches[0])
                    self.stats['new_matches'] += 1
                    self.logger.info(f"✅ 职位 {job_id} 匹配成功，分数: {result.matches[0].overall_score:.3f}")
                else:
                    # 记录查询元数据以便调试
                    metadata = result.query_metadata
                    self.logger.debug(f"⚠️ 职位 {job_id} 未产生匹配结果")
                    self.logger.debug(f"   搜索结果数: {metadata.get('search_results_count', 0)}")
                    self.logger.debug(f"   候选职位数: {metadata.get('candidate_jobs_count', 0)}")
                    self.logger.debug(f"   成功匹配数: {metadata.get('successful_matches', 0)}")
                    self.logger.debug(f"   低分数量: {metadata.get('below_threshold', 0)}")
                
            except Exception as e:
                self.stats['failed_jobs'] += 1
                self.logger.warning(f"❌ 处理职位 {job_id} 失败: {str(e)}")
                # 添加更详细的错误信息
                import traceback
                self.logger.debug(f"错误详情: {traceback.format_exc()}")
    
    async def _save_match_result(self, match_result):
        """保存匹配结果到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO resume_matches 
                (job_id, resume_profile_id, match_score, priority_level, 
                 semantic_score, skill_match_score, experience_match_score, 
                 location_match_score, salary_match_score, match_details, 
                 match_reasons, created_at, processed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 0)
            """, (
                match_result.job_id,
                'default',
                match_result.overall_score,
                match_result.match_level.value if hasattr(match_result.match_level, 'value') else str(match_result.match_level),
                match_result.dimension_scores.get('semantic_similarity', 0),
                match_result.dimension_scores.get('skills_match', 0),
                match_result.dimension_scores.get('experience_match', 0),
                match_result.dimension_scores.get('industry_match', 0),
                match_result.dimension_scores.get('salary_match', 0),
                json.dumps(match_result.dimension_scores),
                f"批量重新匹配: {match_result.job_title} at {match_result.company}"
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"保存匹配结果失败: {str(e)}")
    
    def _generate_report(self) -> Dict[str, Any]:
        """生成处理报告"""
        processing_time = 0
        if self.stats['start_time'] and self.stats['end_time']:
            processing_time = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        # 计算新的匹配率
        new_total_matches = self.stats['total_jobs'] - self.stats['unmatched_jobs'] + self.stats['new_matches']
        new_match_rate = new_total_matches / self.stats['total_jobs'] if self.stats['total_jobs'] > 0 else 0
        
        old_match_rate = (self.stats['total_jobs'] - self.stats['unmatched_jobs']) / self.stats['total_jobs'] if self.stats['total_jobs'] > 0 else 0
        
        return {
            "summary": {
                "total_jobs": self.stats['total_jobs'],
                "originally_unmatched": self.stats['unmatched_jobs'],
                "processed_jobs": self.stats['processed_jobs'],
                "new_matches": self.stats['new_matches'],
                "failed_jobs": self.stats['failed_jobs'],
                "processing_time_seconds": processing_time
            },
            "match_rate_improvement": {
                "before": f"{old_match_rate:.1%}",
                "after": f"{new_match_rate:.1%}",
                "improvement": f"{(new_match_rate - old_match_rate):.1%}"
            },
            "performance": {
                "success_rate": f"{(self.stats['new_matches'] / self.stats['processed_jobs'] * 100):.1f}%" if self.stats['processed_jobs'] > 0 else "0%",
                "jobs_per_second": f"{(self.stats['processed_jobs'] / processing_time):.1f}" if processing_time > 0 else "N/A"
            },
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if self.stats['processed_jobs'] > 0:
            success_rate = self.stats['new_matches'] / self.stats['processed_jobs']
            
            if success_rate < 0.2:
                recommendations.append("匹配成功率很低，建议进一步降低阈值到0.20或检查向量数据库质量")
            elif success_rate < 0.4:
                recommendations.append("匹配成功率偏低，建议检查匹配算法权重配置")
            elif success_rate > 0.6:
                recommendations.append("匹配成功率良好，系统运行正常")
            
            if self.stats['failed_jobs'] > self.stats['processed_jobs'] * 0.1:
                recommendations.append("失败率较高，建议检查数据质量和错误处理逻辑")
        
        if self.stats['new_matches'] > 0:
            recommendations.append("建议定期运行批量重新匹配以保持匹配率")
        else:
            recommendations.append("未产生新匹配，建议检查向量数据库是否正确索引了职位数据")
        
        # 添加基于配置的建议
        recommendations.append("如需进一步提高匹配率，可考虑:")
        recommendations.append("1. 降低匹配阈值到0.18-0.20")
        recommendations.append("2. 调整权重配置，提高语义相似度权重")
        recommendations.append("3. 检查向量数据库数据质量和完整性")
        recommendations.append("4. 运行 python debug_matching_failure.py 进行详细诊断")
        
        return recommendations


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='批量重新匹配职位')
    parser.add_argument('--limit', type=int, help='限制处理的职位数量')
    parser.add_argument('--db-path', default='data/jobs.db', help='数据库路径')
    parser.add_argument('--report-file', help='保存报告到文件')
    
    args = parser.parse_args()
    
    # 创建重新匹配器
    rematcher = BatchRematcher(args.db_path)
    
    # 运行批量重新匹配
    report = await rematcher.run_batch_rematch(args.limit)
    
    # 打印报告
    print("\n" + "="*60)
    print("📊 批量重新匹配报告")
    print("="*60)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    
    # 保存报告到文件
    if args.report_file:
        with open(args.report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n📄 报告已保存到: {args.report_file}")


if __name__ == "__main__":
    asyncio.run(main())