#!/usr/bin/env python3
"""
测试技能匹配优化效果
验证占彬简历的技能匹配是否得到改善
"""

import json
import asyncio
from src.matcher.generic_resume_matcher import GenericResumeJobMatcher
from src.matcher.generic_resume_models import GenericResumeProfile
from src.rag.vector_manager import ChromaDBManager

def load_resume_data():
    """加载占彬的简历数据"""
    with open('testdata/resume.json', 'r', encoding='utf-8') as f:
        resume_data = json.load(f)
    return GenericResumeProfile.from_dict(resume_data)

def create_mock_job_docs():
    """创建模拟职位文档用于测试"""
    from langchain.schema import Document
    
    # 模拟一个数据架构师职位
    job_docs = [
        Document(
            page_content="""
            Senior Data Architect - Azure Platform
            
            We are seeking an experienced Data Architect to design and implement 
            data solutions using Azure cloud platform. The ideal candidate will have 
            expertise in Databricks, Azure Data Factory, and data governance.
            
            Key Requirements:
            - 8+ years of data engineering experience
            - Expert knowledge of Azure Data Factory, Databricks, Delta Lake
            - Experience with data governance, data lineage, and metadata management
            - Strong background in machine learning and AI/ML architecture
            - Experience with PySpark, ETL pipelines, and lakehouse architecture
            - Knowledge of data quality, OLTP/OLAP systems
            - Agile/Scrum methodology experience
            - Technical leadership and team management skills
            
            Preferred Skills:
            - Azure certifications (Solutions Architect Expert)
            - Experience with pharmaceutical or healthcare data
            - RAG architecture and LangChain experience
            - Computer vision and deep learning projects
            """,
            metadata={
                'job_id': 'test_job_001',
                'job_title': 'Senior Data Architect',
                'company': 'Tech Healthcare Corp',
                'location': 'Shanghai, China',
                'industry': 'Healthcare Technology',
                'required_experience_years': 8,
                'skills': [
                    'azure data factory', 'databricks', 'delta lake', 'data governance',
                    'machine learning', 'pyspark', 'etl', 'data architecture',
                    'azure', 'data lineage', 'metadata management', 'scrum'
                ]
            }
        )
    ]
    
    return job_docs

async def test_skill_matching():
    """测试技能匹配效果"""
    print("=== 测试技能匹配优化效果 ===\n")
    
    # 1. 加载简历数据
    print("1. 加载占彬的简历数据...")
    resume_profile = load_resume_data()
    print(f"   简历加载完成: {resume_profile.name}")
    print(f"   总技能数量: {len(resume_profile.get_all_skills())}")
    print(f"   核心技能: {resume_profile.get_all_skills()[:10]}")
    print()
    
    # 2. 创建模拟的向量管理器和匹配器
    print("2. 初始化匹配器...")
    config = {
        'persist_directory': './test_chroma_db',
        'collection_name': 'test_jobs'
    }
    
    # 注意：这里我们创建一个模拟的匹配器，不依赖真实的向量数据库
    class MockVectorManager:
        def similarity_search_with_score(self, query, k, filters=None):
            return []
    
    matcher = GenericResumeJobMatcher(MockVectorManager(), config)
    print("   匹配器初始化完成")
    print()
    
    # 3. 测试技能提取和匹配
    print("3. 测试技能提取和匹配...")
    job_docs = create_mock_job_docs()
    job_metadata = matcher._extract_job_metadata(job_docs, 'test_job_001')
    
    print(f"   职位标题: {job_metadata.get('job_title')}")
    print(f"   公司: {job_metadata.get('company')}")
    print()
    
    # 4. 提取职位技能
    print("4. 提取职位技能要求...")
    job_skills = matcher._extract_job_skills(job_docs, job_metadata)
    print(f"   提取到的职位技能数量: {len(job_skills)}")
    print(f"   职位技能: {job_skills}")
    print()
    
    # 5. 测试技能匹配
    print("5. 测试技能匹配效果...")
    resume_skills = [skill.lower() for skill in resume_profile.get_all_skills()]
    print(f"   简历技能数量: {len(resume_skills)}")
    
    matched_skills = []
    unmatched_skills = []
    
    for job_skill in job_skills:
        if matcher._is_skill_matched(job_skill, resume_skills):
            matched_skills.append(job_skill)
        else:
            unmatched_skills.append(job_skill)
    
    print(f"\n   匹配结果:")
    print(f"   ✅ 匹配的技能 ({len(matched_skills)}): {matched_skills}")
    print(f"   ❌ 未匹配的技能 ({len(unmatched_skills)}): {unmatched_skills}")
    print(f"   📊 匹配率: {len(matched_skills) / len(job_skills) * 100:.1f}%")
    print()
    
    # 6. 测试技能权重和加分
    print("6. 测试技能权重和加分...")
    
    # 计算加权匹配分数
    total_weight = 0
    matched_weight = 0
    
    for job_skill in job_skills:
        weight = matcher.skill_weights.get_skill_weight(job_skill)
        total_weight += weight
        if matcher._is_skill_matched(job_skill, resume_skills):
            matched_weight += weight
            print(f"   ✅ {job_skill}: 权重 {weight:.2f}")
        else:
            print(f"   ❌ {job_skill}: 权重 {weight:.2f}")
    
    base_match_rate = matched_weight / total_weight if total_weight > 0 else 0
    bonus_score = matcher._calculate_skill_bonus(resume_skills, job_skills)
    final_score = min(1.0, base_match_rate + bonus_score)
    
    print(f"\n   权重匹配结果:")
    print(f"   基础匹配率: {base_match_rate:.3f}")
    print(f"   技能加分: {bonus_score:.3f}")
    print(f"   最终技能分数: {final_score:.3f}")
    print()
    
    # 7. 显示优化效果
    print("7. 优化效果总结:")
    print(f"   🎯 针对占彬简历的优化:")
    print(f"      - 扩展了技能词典，包含 {len(matcher._get_skill_mappings())} 个中英文映射")
    print(f"      - 增加了 {len(matcher._get_skill_variants())} 个技能变体")
    print(f"      - 提升了核心技能权重 (Databricks: 2.0, Azure Data Factory: 2.0)")
    print(f"      - 增强了技能加分机制 (最高25%加分)")
    print()
    
    # 8. 测试中英文映射
    print("8. 测试中英文技能映射:")
    cn_skills_in_resume = ['数据工程师', 'ai/ml架构师', '数据治理', '机器学习']
    for cn_skill in cn_skills_in_resume:
        if cn_skill.lower() in resume_skills:
            mappings = matcher._get_skill_mappings().get(cn_skill, [])
            print(f"   🔄 '{cn_skill}' -> {mappings}")
    
    print("\n=== 测试完成 ===")
    
    return {
        'total_job_skills': len(job_skills),
        'matched_skills': len(matched_skills),
        'match_rate': len(matched_skills) / len(job_skills) if job_skills else 0,
        'weighted_score': final_score,
        'bonus_score': bonus_score
    }

if __name__ == "__main__":
    # 运行测试
    result = asyncio.run(test_skill_matching())
    
    print(f"\n📈 最终测试结果:")
    print(f"   匹配率: {result['match_rate']:.1%}")
    print(f"   加权分数: {result['weighted_score']:.3f}")
    print(f"   技能加分: {result['bonus_score']:.3f}")
    
    if result['match_rate'] >= 0.8:
        print("   🎉 优化效果显著！技能匹配率达到80%以上")
    elif result['match_rate'] >= 0.6:
        print("   ✅ 优化效果良好！技能匹配率达到60%以上")
    else:
        print("   ⚠️  仍需进一步优化")