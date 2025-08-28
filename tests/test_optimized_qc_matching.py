#!/usr/bin/env python3
"""
测试优化后的qc_167002415匹配效果
"""

import sys
import asyncio
sys.path.append('.')
from src.matcher.generic_resume_matcher import GenericResumeJobMatcher
from src.matcher.generic_resume_models import GenericResumeProfile
from src.rag.vector_manager import ChromaDBManager
from src.utils.logger import get_logger
import yaml
import json

async def test_optimized_matching():
    """测试优化后的匹配效果"""
    logger = get_logger(__name__)
    
    # 加载配置
    with open('config/integration_config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    rag_config = config.get('rag_system', {})
    vector_db_config = rag_config.get('vector_db', {})
    llm_config = rag_config.get('llm', {})

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

    vector_manager = ChromaDBManager(vector_manager_config)
    
    # 加载简历
    with open('testdata/resume.json', 'r', encoding='utf-8') as f:
        resume_data = json.load(f)
    resume_profile = GenericResumeProfile.from_dict(resume_data)
    
    print("="*80)
    print("🧪 测试优化后的qc_167002415匹配效果")
    print("="*80)
    
    # 测试配置对比
    configs = {
        "原始配置": {
            'min_score_threshold': 0.30,
            'weights': {
                'semantic_similarity': 0.40,
                'skills_match': 0.45,
                'experience_match': 0.05,
                'industry_match': 0.02,
                'salary_match': 0.08
            }
        },
        "优化配置": {
            'min_score_threshold': 0.25,
            'weights': {
                'semantic_similarity': 0.25,  # 降低语义权重
                'skills_match': 0.55,         # 提高技能权重
                'experience_match': 0.10,     # 提高经验权重
                'industry_match': 0.05,       # 提高行业权重
                'salary_match': 0.05          # 降低薪资权重
            }
        }
    }
    
    results = {}
    
    for config_name, matcher_config in configs.items():
        print(f"\n{'='*20} {config_name} {'='*20}")
        
        matcher = GenericResumeJobMatcher(vector_manager, matcher_config)
        
        # 执行匹配
        filters = {"job_id": "qc_167002415"}
        result = await matcher.find_matching_jobs(
            resume_profile, 
            filters=filters, 
            top_k=1
        )
        
        if result.matches:
            match = result.matches[0]
            results[config_name] = {
                'success': True,
                'score': match.overall_score,
                'level': match.match_level,
                'dimensions': match.dimension_scores
            }
            
            print(f"✅ 匹配成功！")
            print(f"   综合分数: {match.overall_score:.3f}")
            print(f"   匹配等级: {match.match_level}")
            print(f"   阈值: {matcher_config['min_score_threshold']}")
            
            print(f"\n📊 各维度分数:")
            for dimension, score in match.dimension_scores.items():
                weight = matcher_config['weights'].get(dimension, 0)
                contribution = score * weight
                print(f"   {dimension:20s}: {score:.3f} × {weight:.2f} = {contribution:.3f}")
                
        else:
            results[config_name] = {
                'success': False,
                'score': 0.0,
                'level': 'FAILED',
                'dimensions': {}
            }
            
            print(f"❌ 匹配失败")
            print(f"   阈值: {matcher_config['min_score_threshold']}")
            
            # 手动计算分数
            job_docs = vector_manager.similarity_search_with_score(
                query='qc_167002415',
                k=10,
                filters={'job_id': 'qc_167002415'}
            )
            
            if job_docs:
                docs_only = [doc for doc, score in job_docs]
                job_metadata = matcher._extract_job_metadata(docs_only, 'qc_167002415')
                
                semantic_score = matcher._calculate_semantic_similarity(resume_profile, docs_only)
                skills_score = matcher._calculate_skills_match(resume_profile, docs_only, job_metadata)
                experience_score = matcher._calculate_experience_match(resume_profile, job_metadata)
                industry_score = matcher._calculate_industry_match(resume_profile, job_metadata)
                salary_score = matcher._calculate_salary_match(resume_profile, job_metadata)
                
                total_score = (
                    semantic_score * matcher_config['weights']['semantic_similarity'] +
                    skills_score * matcher_config['weights']['skills_match'] +
                    experience_score * matcher_config['weights']['experience_match'] +
                    industry_score * matcher_config['weights']['industry_match'] +
                    salary_score * matcher_config['weights']['salary_match']
                )
                
                results[config_name]['score'] = total_score
                results[config_name]['dimensions'] = {
                    'semantic_similarity': semantic_score,
                    'skills_match': skills_score,
                    'experience_match': experience_score,
                    'industry_match': industry_score,
                    'salary_match': salary_score
                }
                
                print(f"   实际分数: {total_score:.3f}")
                print(f"   差距: {matcher_config['min_score_threshold'] - total_score:.3f}")
    
    # 对比分析
    print(f"\n{'='*30} 对比分析 {'='*30}")
    
    original = results.get("原始配置", {})
    optimized = results.get("优化配置", {})
    
    print(f"\n📈 分数对比:")
    print(f"   原始配置: {original.get('score', 0):.3f} ({'成功' if original.get('success') else '失败'})")
    print(f"   优化配置: {optimized.get('score', 0):.3f} ({'成功' if optimized.get('success') else '失败'})")
    
    if original.get('score', 0) > 0 and optimized.get('score', 0) > 0:
        improvement = optimized['score'] - original['score']
        improvement_pct = (improvement / original['score']) * 100
        print(f"   改进幅度: {improvement:+.3f} ({improvement_pct:+.1f}%)")
    
    print(f"\n📊 维度对比:")
    dimensions = ['semantic_similarity', 'skills_match', 'experience_match', 'industry_match', 'salary_match']
    
    for dim in dimensions:
        orig_score = original.get('dimensions', {}).get(dim, 0)
        opt_score = optimized.get('dimensions', {}).get(dim, 0)
        diff = opt_score - orig_score
        print(f"   {dim:20s}: {orig_score:.3f} → {opt_score:.3f} ({diff:+.3f})")
    
    # 结论和建议
    print(f"\n💡 结论和建议:")
    
    if optimized.get('success') and not original.get('success'):
        print("   ✅ 优化成功！职位现在可以匹配")
        print("   📋 建议将优化配置应用到生产环境")
    elif optimized.get('score', 0) > original.get('score', 0):
        print("   📈 分数有所提升，但仍需进一步优化")
        print("   🎯 建议继续调整权重或降低阈值")
    else:
        print("   ⚠️ 优化效果不明显，需要重新分析")
    
    # 具体优化建议
    if not optimized.get('success'):
        opt_score = optimized.get('score', 0)
        threshold = 0.25
        gap = threshold - opt_score
        
        print(f"\n🔧 进一步优化建议:")
        print(f"   当前分数: {opt_score:.3f}")
        print(f"   目标阈值: {threshold:.3f}")
        print(f"   差距: {gap:.3f}")
        
        if gap > 0:
            print(f"   建议1: 降低阈值到 {opt_score - 0.01:.2f}")
            print(f"   建议2: 进一步提高技能匹配权重到 0.65")
            print(f"   建议3: 增强职位标题和技能的语义映射")

if __name__ == "__main__":
    asyncio.run(test_optimized_matching())