#!/usr/bin/env python3
"""
测试优化后的匹配算法
验证薪资匹配逻辑和整体匹配率改进效果
"""

import asyncio
import sys
import os
import json
import yaml
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(__file__))

from src.matcher.generic_resume_matcher import GenericResumeJobMatcher
from src.matcher.generic_resume_models import GenericResumeProfile
from src.rag.vector_manager import ChromaDBManager
from src.utils.logger import get_logger


def load_integration_config(config_path: str = "config/integration_config.yaml") -> dict:
    """加载集成配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"⚠️ 无法加载配置文件 {config_path}: {e}")
        return {}


async def test_qc_job_matching():
    """测试qc_167002415职位的匹配情况"""
    logger = get_logger(__name__)
    
    try:
        logger.info("🧪 开始测试优化后的匹配算法")
        
        # 1. 加载集成配置
        integration_config = load_integration_config()
        
        # 2. 从集成配置中提取向量数据库配置
        rag_config = integration_config.get('rag_system', {})
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
        
        try:
            vector_manager = ChromaDBManager(vector_manager_config)
        except Exception as e:
            logger.warning(f"向量管理器初始化失败: {e}")
            logger.info("这可能是由于Hugging Face连接问题导致的")
            logger.info("建议解决方案:")
            logger.info("1. 检查网络连接")
            logger.info("2. 使用VPN或代理")
            logger.info("3. 预先下载模型到本地")
            return False
        
        # 3. 从集成配置中提取匹配算法配置
        resume_matching_config = integration_config.get('modules', {}).get('resume_matching', {})
        
        # 优先使用高级匹配配置
        advanced_matching_config = integration_config.get('resume_matching_advanced', {})
        
        if advanced_matching_config:
            logger.info("🚀 使用高级匹配配置")
            # 使用高级配置的权重和阈值
            matcher_config = {
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
            logger.info(f"📊 高级配置权重: {matcher_config['weights']}")
        else:
            logger.info("📋 使用标准匹配配置")
            # 构建标准匹配器配置
            matcher_config = {
                'min_score_threshold': resume_matching_config.get('matching_threshold', 0.25),
                'default_search_k': 80,
                'max_results': resume_matching_config.get('max_matches_per_resume', 30),
                'weights': {
                    'semantic_similarity': 0.40,
                    'skills_match': 0.35,
                    'experience_match': 0.15,
                    'industry_match': 0.08,
                    'salary_match': 0.02
                }
            }
        
        logger.info(f"📋 使用配置: 阈值={matcher_config['min_score_threshold']}, 最大结果={matcher_config['max_results']}")
        
        matcher = GenericResumeJobMatcher(vector_manager, matcher_config)
        
        # 4. 创建简历档案
        resume_profile = await create_test_resume_profile()
        
        # 5. 测试特定职位匹配
        logger.info("🎯 测试职位 qc_167002415 的匹配情况")
        
        # 构建职位过滤器
        filters = {"job_id": "qc_167002415"}
        
        result = await matcher.find_matching_jobs(
            resume_profile, 
            filters=filters, 
            top_k=1
        )
        
        # 6. 分析结果
        if result.matches:
            match = result.matches[0]
            logger.info("✅ 职位匹配成功！")
            logger.info(f"   职位: {match.job_title}")
            logger.info(f"   公司: {match.company}")
            logger.info(f"   综合分数: {match.overall_score:.3f}")
            logger.info(f"   匹配等级: {match.match_level}")
            
            # 详细分数分析
            logger.info("📊 各维度分数:")
            for dimension, score in match.dimension_scores.items():
                logger.info(f"   {dimension}: {score:.3f}")
            
            # 薪资匹配分析
            if match.salary_range:
                logger.info(f"   职位薪资: {match.salary_range}")
                logger.info(f"   期望薪资: {resume_profile.expected_salary_range}")
            
            return True
        else:
            logger.warning("❌ 职位未匹配成功")
            logger.info("📋 查询元数据:")
            for key, value in result.query_metadata.items():
                logger.info(f"   {key}: {value}")
            return False
            
    except Exception as e:
        logger.error(f"💥 测试失败: {str(e)}")
        return False


async def test_batch_matching_improvement():
    """测试批量匹配改进效果"""
    logger = get_logger(__name__)
    
    try:
        logger.info("📈 测试批量匹配改进效果")
        
        # 1. 加载集成配置
        integration_config = load_integration_config()
        
        # 2. 从集成配置中提取向量数据库配置
        rag_config = integration_config.get('rag_system', {})
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
        
        try:
            vector_manager = ChromaDBManager(vector_manager_config)
        except Exception as e:
            logger.warning(f"向量管理器初始化失败: {e}")
            logger.info("这可能是由于Hugging Face连接问题导致的")
            return {}
        
        # 3. 从集成配置中提取匹配算法配置
        resume_matching_config = integration_config.get('modules', {}).get('resume_matching', {})
        
        # 旧配置（原始）
        old_config = {
            'min_score_threshold': 0.3,
            'weights': {
                'semantic_similarity': 0.35,
                'skills_match': 0.30,
                'experience_match': 0.20,
                'industry_match': 0.10,
                'salary_match': 0.05
            }
        }
        
        # 新配置（优化后）
        new_config = {
            'min_score_threshold': 0.25,
            'weights': {
                'semantic_similarity': 0.40,
                'skills_match': 0.35,
                'experience_match': 0.15,
                'industry_match': 0.08,
                'salary_match': 0.02
            }
        }
        
        # 4. 创建简历档案
        resume_profile = await create_test_resume_profile()
        
        # 5. 测试样本职位
        test_jobs = ["qc_167002415"]  # 可以添加更多测试职位
        
        results = {}
        
        for config_name, config in [("旧配置", old_config), ("新配置", new_config)]:
            logger.info(f"🔄 测试 {config_name}")
            
            matcher = GenericResumeJobMatcher(vector_manager, config)
            matched_count = 0
            total_score = 0
            
            for job_id in test_jobs:
                try:
                    filters = {"job_id": job_id}
                    result = await matcher.find_matching_jobs(
                        resume_profile, 
                        filters=filters, 
                        top_k=1
                    )
                    
                    if result.matches:
                        matched_count += 1
                        total_score += result.matches[0].overall_score
                        logger.info(f"   ✅ {job_id}: {result.matches[0].overall_score:.3f}")
                    else:
                        logger.info(f"   ❌ {job_id}: 未匹配")
                        
                except Exception as e:
                    logger.warning(f"   ⚠️ {job_id}: 测试失败 - {str(e)}")
            
            match_rate = matched_count / len(test_jobs) if test_jobs else 0
            avg_score = total_score / matched_count if matched_count > 0 else 0
            
            results[config_name] = {
                'matched_count': matched_count,
                'total_jobs': len(test_jobs),
                'match_rate': match_rate,
                'avg_score': avg_score
            }
            
            logger.info(f"   📊 {config_name}结果: 匹配率 {match_rate:.1%}, 平均分 {avg_score:.3f}")
        
        # 6. 对比分析
        logger.info("📊 对比分析:")
        old_result = results["旧配置"]
        new_result = results["新配置"]
        
        match_rate_improvement = new_result['match_rate'] - old_result['match_rate']
        score_improvement = new_result['avg_score'] - old_result['avg_score']
        
        logger.info(f"   匹配率改进: {match_rate_improvement:+.1%}")
        logger.info(f"   平均分改进: {score_improvement:+.3f}")
        
        # 7. 使用高级匹配配置进行额外测试
        advanced_matching_config = integration_config.get('resume_matching_advanced', {})
        if advanced_matching_config:
            logger.info("🚀 测试高级匹配配置")
            
            # 使用高级配置的权重和阈值
            advanced_config = {
                'min_score_threshold': advanced_matching_config.get('match_thresholds', {}).get('poor', 0.25),
                'max_results': resume_matching_config.get('max_matches_per_resume', 30),
                'weights': advanced_matching_config.get('matching_weights', {
                    'semantic_similarity': 0.40,
                    'skills_match': 0.35,
                    'experience_match': 0.15,
                    'industry_match': 0.08,
                    'salary_match': 0.02
                })
            }
            
            logger.info(f"   高级配置阈值: {advanced_config['min_score_threshold']}")
            
            advanced_matcher = GenericResumeJobMatcher(vector_manager, advanced_config)
            advanced_matched_count = 0
            advanced_total_score = 0
            
            for job_id in test_jobs:
                try:
                    filters = {"job_id": job_id}
                    result = await advanced_matcher.find_matching_jobs(
                        resume_profile,
                        filters=filters,
                        top_k=1
                    )
                    
                    if result.matches:
                        advanced_matched_count += 1
                        advanced_total_score += result.matches[0].overall_score
                        logger.info(f"   ✅ 高级配置 {job_id}: {result.matches[0].overall_score:.3f}")
                    else:
                        logger.info(f"   ❌ 高级配置 {job_id}: 未匹配")
                        
                except Exception as e:
                    logger.warning(f"   ⚠️ 高级配置 {job_id}: 测试失败 - {str(e)}")
            
            advanced_match_rate = advanced_matched_count / len(test_jobs) if test_jobs else 0
            advanced_avg_score = advanced_total_score / advanced_matched_count if advanced_matched_count > 0 else 0
            
            results["高级配置"] = {
                'matched_count': advanced_matched_count,
                'total_jobs': len(test_jobs),
                'match_rate': advanced_match_rate,
                'avg_score': advanced_avg_score
            }
            
            logger.info(f"   📊 高级配置结果: 匹配率 {advanced_match_rate:.1%}, 平均分 {advanced_avg_score:.3f}")
        
        return results
        
    except Exception as e:
        logger.error(f"💥 批量测试失败: {str(e)}")
        return {}


async def create_test_resume_profile() -> GenericResumeProfile:
    """创建测试用简历档案"""
    try:
        # 尝试从文件加载
        resume_file = 'testdata/resume.json'
        if os.path.exists(resume_file):
            with open(resume_file, 'r', encoding='utf-8') as f:
                resume_data = json.load(f)
            return GenericResumeProfile.from_dict(resume_data)
    except Exception:
        pass
    
    # 创建默认档案
    from src.matcher.generic_resume_models import SkillCategory, WorkExperience
    
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


async def main():
    """主函数"""
    logger = get_logger(__name__)
    
    print("="*60)
    print("🧪 匹配算法优化测试")
    print("="*60)
    
    # 1. 测试特定职位匹配
    print("\n1️⃣ 测试 qc_167002415 职位匹配")
    print("-" * 40)
    qc_success = await test_qc_job_matching()
    
    # 2. 测试批量匹配改进
    print("\n2️⃣ 测试批量匹配改进效果")
    print("-" * 40)
    batch_results = await test_batch_matching_improvement()
    
    # 3. 生成总结报告
    print("\n📋 测试总结")
    print("-" * 40)
    
    if qc_success:
        print("✅ qc_167002415 职位现在可以成功匹配")
    else:
        print("❌ qc_167002415 职位仍然无法匹配，需要进一步优化")
    
    if batch_results:
        old_result = batch_results.get("旧配置", {})
        new_result = batch_results.get("新配置", {})
        
        if new_result.get('match_rate', 0) > old_result.get('match_rate', 0):
            print("✅ 批量匹配率有所提高")
        else:
            print("⚠️ 批量匹配率未显著提高")
    
    print("\n🎯 优化建议:")
    print("1. 如果匹配率仍然偏低，可以进一步降低阈值到0.2")
    print("2. 可以调整技能匹配逻辑，增加模糊匹配")
    print("3. 考虑增加语义相似度的权重")
    print("4. 运行批量重新匹配脚本: python batch_rematch_jobs.py")


if __name__ == "__main__":
    asyncio.run(main())