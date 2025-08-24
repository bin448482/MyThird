#!/usr/bin/env python3
"""
RAG系统统一CLI接口

提供完整的RAG系统命令行接口，包括数据处理、简历优化、职位匹配等功能
"""

import sys
import asyncio
import argparse
import logging
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from src.rag.rag_system_coordinator import RAGSystemCoordinator
from src.rag.data_pipeline import RAGDataPipeline, create_progress_callback
from src.rag.resume_optimizer import ResumeOptimizer
from src.rag.vector_manager import ChromaDBManager
from src.rag.resume_document_parser import ResumeDocumentParser
from src.rag.resume_document_processor import ResumeDocumentProcessor
from src.rag.llm_factory import create_llm
from src.matcher import (
    GenericResumeJobMatcher
)
from src.matcher.generic_resume_models import (
    GenericResumeProfile
)
from src.matcher.generic_resume_matcher import GenericResumeJobMatcher
from src.matcher.generic_resume_vectorizer import GenericResumeVectorizer
from src.analysis_tools.agent import create_analysis_agent

def setup_logging(log_level: str = 'INFO', log_file: str = None):
    """设置日志配置"""
    handlers = [logging.StreamHandler()]
    
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

def load_config(config_file: str = None) -> dict:
    """加载配置文件"""
    if config_file and Path(config_file).exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            if config_file.endswith('.json'):
                return json.load(f)
            else:
                import yaml
                return yaml.safe_load(f)
    
    # 默认配置
    return {
        'rag_system': {
            'database': {
                'path': './data/jobs.db',
                'batch_size': 50
            },
            'llm': {
                'provider': 'zhipu',
                'model': 'glm-4-flash',
                'api_key': 'your-api-key-here',
                'temperature': 0.1,
                'max_tokens': 2000
            },
            'vector_db': {
                'persist_directory': './data/test_chroma_db',
                'collection_name': 'job_positions',
                'embeddings': {
                    'model_name': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                    'device': 'cpu',
                    'normalize_embeddings': True
                }
            },
            'documents': {
                'types': ['overview', 'responsibility', 'requirement', 'skills', 'basic_requirements'],
                'create_comprehensive_doc': False
            },
            'processing': {
                'skip_processed': True,
                'force_reprocess': False,
                'batch_size': 50,
                'max_retry_attempts': 3
            }
        }
    }

def load_resume(resume_file: str) -> dict:
    """加载简历文件"""
    if not Path(resume_file).exists():
        raise FileNotFoundError(f"简历文件不存在: {resume_file}")
    
    with open(resume_file, 'r', encoding='utf-8') as f:
        if resume_file.endswith('.json'):
            return json.load(f)
        else:
            import yaml
            return yaml.safe_load(f)

def create_default_zhanbin_profile() -> GenericResumeProfile:
    """创建默认的占彬简历档案（通用格式）"""
    from src.matcher.generic_resume_models import GenericResumeProfile, SkillCategory, WorkExperience
    
    profile = GenericResumeProfile(
        name="占彬",
        phone="",
        email="",
        location="中国",
        total_experience_years=20,
        current_position="高级技术专家",
        current_company="",
        profile_type="zhanbin_default"
    )
    
    # 添加技能分类
    profile.add_skill_category("core_skills", [
        "Python", "Java", "JavaScript", "React", "Vue.js", "Node.js",
        "Spring Boot", "Django", "Flask", "MySQL", "PostgreSQL", "MongoDB"
    ], "advanced")
    
    profile.add_skill_category("cloud_platforms", [
        "AWS", "Azure", "Google Cloud", "Docker", "Kubernetes", "Jenkins"
    ], "advanced")
    
    profile.add_skill_category("ai_ml_skills", [
        "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch",
        "Scikit-learn", "Pandas", "NumPy", "Data Science"
    ], "expert")
    
    profile.add_skill_category("data_engineering_skills", [
        "Apache Spark", "Hadoop", "Kafka", "Elasticsearch", "Redis",
        "ETL", "Data Pipeline", "Big Data"
    ], "advanced")
    
    profile.add_skill_category("management_skills", [
        "团队管理", "项目管理", "敏捷开发", "Scrum", "技术架构", "系统设计"
    ], "expert")
    
    # 设置行业经验
    profile.industry_experience = {
        "互联网": 0.8,
        "人工智能": 0.9,
        "金融科技": 0.7,
        "企业服务": 0.6
    }
    
    # 设置期望职位
    profile.preferred_positions = [
        "技术总监", "架构师", "AI工程师", "数据科学家", "技术专家"
    ]
    
    # 设置薪资期望
    profile.expected_salary_range = {"min": 500000, "max": 800000}
    
    # 设置职业目标
    profile.career_objectives = [
        "在人工智能和大数据领域发挥技术专长",
        "带领团队完成具有挑战性的技术项目",
        "推动企业数字化转型和技术创新"
    ]
    
    return profile

def load_resume_profile(resume_data: dict) -> GenericResumeProfile:
    """统一的简历加载函数"""
    try:
        # 直接使用通用格式加载
        if 'skill_categories' in resume_data:
            # 新的通用格式
            return GenericResumeProfile.from_dict(resume_data)
        else:
            # 旧格式数据，转换为通用格式
            # 创建基本的简历档案
            profile = GenericResumeProfile(
                name=resume_data.get('name', '未知用户'),
                phone=resume_data.get('phone', ''),
                email=resume_data.get('email', ''),
                location=resume_data.get('location', ''),
                total_experience_years=resume_data.get('total_experience_years', 0),
                current_position=resume_data.get('current_position', ''),
                current_company=resume_data.get('current_company', ''),
                certifications=resume_data.get('certifications', []),
                industry_experience=resume_data.get('industry_experience', {}),
                preferred_positions=resume_data.get('preferred_positions', []),
                expected_salary_range=resume_data.get('expected_salary_range', {"min": 0, "max": 0}),
                career_objectives=resume_data.get('career_objectives', []),
                profile_type='converted_from_legacy'
            )
            
            # 转换技能数据到技能分类
            skill_mappings = [
                ('core_skills', 'core_skills'),
                ('programming_languages', 'programming_languages'),
                ('cloud_platforms', 'cloud_platforms'),
                ('ai_ml_skills', 'ai_ml_skills'),
                ('data_engineering_skills', 'data_engineering_skills'),
                ('management_skills', 'management_skills')
            ]
            
            for category_name, data_key in skill_mappings:
                if data_key in resume_data and resume_data[data_key]:
                    profile.add_skill_category(
                        category_name=category_name,
                        skills=resume_data[data_key],
                        proficiency_level='advanced'
                    )
            
            # 转换工作经验
            for exp_data in resume_data.get('work_history', []):
                from src.matcher.generic_resume_models import WorkExperience
                experience = WorkExperience(
                    company=exp_data.get('company', ''),
                    position=exp_data.get('position', ''),
                    start_date=exp_data.get('start_date', ''),
                    end_date=exp_data.get('end_date'),
                    duration_years=exp_data.get('duration_years', 0),
                    responsibilities=exp_data.get('responsibilities', []),
                    achievements=exp_data.get('achievements', []),
                    technologies=exp_data.get('technologies', []),
                    industry=exp_data.get('industry', '')
                )
                profile.add_work_experience(experience)
            
            return profile
            
    except Exception as e:
        print(f"⚠️ 简历加载失败，使用默认档案: {e}")
        return create_default_zhanbin_profile()

async def pipeline_command(args):
    """数据流水线命令"""
    print("🚀 RAG数据流水线")
    print("=" * 40)
    
    try:
        config = load_config(args.config)
        
        # 覆盖命令行参数
        if args.batch_size:
            config['rag_system']['processing']['batch_size'] = args.batch_size
        if args.force_reprocess:
            config['rag_system']['processing']['force_reprocess'] = True
        
        # 创建进度回调
        progress_callback = create_progress_callback() if args.show_progress else None
        
        # 运行流水线
        pipeline = RAGDataPipeline(config, progress_callback)
        result = await pipeline.run_full_pipeline(
            batch_size=args.batch_size or 50,
            max_jobs=args.max_jobs,
            force_reprocess=args.force_reprocess,
            save_progress=not args.no_save
        )
        
        # 显示结果摘要
        print("\n📊 执行结果摘要:")
        exec_summary = result.get('execution_summary', {})
        proc_stats = result.get('processing_statistics', {})
        
        print(f"   状态: {exec_summary.get('status', 'unknown')}")
        print(f"   执行时间: {exec_summary.get('execution_time', 0):.1f} 秒")
        print(f"   处理职位: {proc_stats.get('processed_jobs', 0)}")
        print(f"   成功率: {proc_stats.get('success_rate', 0):.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ 流水线执行失败: {e}")
        return False

async def status_command(args):
    """系统状态命令"""
    print("📊 RAG系统状态")
    print("=" * 30)
    
    try:
        config = load_config(args.config)
        coordinator = RAGSystemCoordinator(config)
        
        if not coordinator.initialize_system():
            print("❌ 系统初始化失败")
            return False
        
        # 获取系统状态
        system_status = coordinator.get_system_status()
        progress = coordinator.get_processing_progress()
        
        # 显示组件状态
        print("组件状态:")
        components = system_status.get('components', {})
        for comp_name, comp_status in components.items():
            status_icon = "✅" if comp_status else "❌"
            print(f"  {comp_name}: {status_icon}")
        
        # 显示数据统计
        db_stats = progress.get('database_stats', {})
        print(f"\n数据库统计:")
        print(f"  总职位数: {db_stats.get('total', 0)}")
        print(f"  已处理: {db_stats.get('processed', 0)}")
        print(f"  未处理: {db_stats.get('unprocessed', 0)}")
        print(f"  处理率: {db_stats.get('processing_rate', 0):.1f}%")
        
        vector_stats = progress.get('vector_stats', {})
        print(f"\n向量数据库:")
        print(f"  文档数量: {vector_stats.get('document_count', 0)}")
        print(f"  集合名称: {vector_stats.get('collection_name', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 状态查询失败: {e}")
        return False

async def optimize_command(args):
    """简历优化命令"""
    print("📝 简历优化")
    print("=" * 20)
    
    try:
        # 加载配置和简历
        config = load_config(args.config)
        resume = load_resume(args.resume)
        
        # 初始化系统
        coordinator = RAGSystemCoordinator(config)
        if not coordinator.initialize_system():
            print("❌ 系统初始化失败")
            return False
        
        optimizer = ResumeOptimizer(coordinator, config['rag_system']['llm'])
        
        # 根据子命令执行不同操作
        if args.action == 'analyze':
            # 简历差距分析
            target_jobs = args.target_jobs.split(',') if args.target_jobs else []
            if not target_jobs:
                # 自动查找相关职位
                all_jobs = coordinator.db_reader.get_jobs_for_rag_processing(limit=5)
                target_jobs = [job['job_id'] for job in all_jobs[:3]]
            
            print(f"分析目标职位: {len(target_jobs)} 个")
            
            if not args.dry_run:
                result = await optimizer.analyze_resume_gaps(resume, target_jobs)
                
                if 'error' in result:
                    print(f"❌ 分析失败: {result['error']}")
                    return False
                
                # 显示分析结果
                summary = result.get('summary', {})
                print(f"\n📊 分析结果:")
                print(f"   平均匹配度: {summary.get('average_match_score', 0)}")
                print(f"   分析职位数: {summary.get('total_jobs_analyzed', 0)}")
                
                # 保存结果
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
                    print(f"   结果已保存到: {args.output}")
            else:
                print("🔍 干运行模式 - 跳过实际分析")
        
        elif args.action == 'optimize':
            # 简历内容优化
            target_job_id = args.target_job or coordinator.db_reader.get_jobs_for_rag_processing(limit=1)[0]['job_id']
            
            print(f"优化目标职位: {target_job_id}")
            
            if not args.dry_run:
                result = await optimizer.optimize_resume_content(
                    resume, 
                    target_job_id, 
                    args.focus_areas.split(',') if args.focus_areas else None
                )
                
                if 'error' in result:
                    print(f"❌ 优化失败: {result['error']}")
                    return False
                
                print("✅ 简历优化完成")
                
                # 保存结果
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
                    print(f"   结果已保存到: {args.output}")
            else:
                print("🔍 干运行模式 - 跳过实际优化")
        
        elif args.action == 'cover-letter':
            # 生成求职信
            target_job_id = args.target_job or coordinator.db_reader.get_jobs_for_rag_processing(limit=1)[0]['job_id']
            
            print(f"生成求职信，目标职位: {target_job_id}")
            
            if not args.dry_run:
                cover_letter = await optimizer.generate_cover_letter(resume, target_job_id)
                
                print("✅ 求职信生成完成")
                print(f"   长度: {len(cover_letter)} 字符")
                
                # 保存求职信
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        f.write(cover_letter)
                    print(f"   求职信已保存到: {args.output}")
                else:
                    print("\n" + "="*50)
                    print(cover_letter)
                    print("="*50)
            else:
                print("🔍 干运行模式 - 跳过实际生成")
        
        return True
        
    except Exception as e:
        print(f"❌ 简历优化失败: {e}")
        return False

async def search_command(args):
    """职位搜索命令"""
    print("🔍 职位搜索")
    print("=" * 20)
    
    try:
        config = load_config(args.config)
        coordinator = RAGSystemCoordinator(config)
        
        if not coordinator.initialize_system():
            print("❌ 系统初始化失败")
            return False
        
        # 执行搜索
        query = args.query
        k = args.limit or 10
        
        print(f"搜索查询: {query}")
        print(f"返回数量: {k}")
        
        # 使用向量搜索
        similar_docs = coordinator.vector_manager.search_similar_jobs(query, k=k)
        
        if not similar_docs:
            print("❌ 没有找到相关职位")
            return False
        
        print(f"\n📋 搜索结果 ({len(similar_docs)} 个):")
        
        for i, doc in enumerate(similar_docs, 1):
            metadata = doc.metadata
            print(f"\n{i}. {metadata.get('job_title', '未知职位')}")
            print(f"   公司: {metadata.get('company', '未知公司')}")
            print(f"   地点: {metadata.get('location', '未知地点')}")
            print(f"   类型: {metadata.get('type', '未知类型')}")
            print(f"   内容: {doc.page_content[:100]}...")
        
        # 保存搜索结果
        if args.output:
            results = []
            for doc in similar_docs:
                results.append({
                    'content': doc.page_content,
                    'metadata': doc.metadata
                })
            
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            print(f"\n💾 搜索结果已保存到: {args.output}")
        
        return True
        
    except Exception as e:
        print(f"❌ 搜索失败: {e}")
        return False

async def test_command(args):
    """向量数据库测试命令"""
    print("🧪 向量数据库测试")
    print("=" * 30)
    
    try:
        config = load_config(args.config)
        vector_config = config.get('rag_system', {}).get('vector_db', {})
        vector_manager = ChromaDBManager(vector_config)
        
        # 获取统计信息
        print("\n📊 数据库统计:")
        stats = vector_manager.get_collection_stats()
        print(f"   文档数量: {stats.get('document_count', 0)}")
        print(f"   集合名称: {stats.get('collection_name', 'unknown')}")
        print(f"   存储路径: {stats.get('persist_directory', 'unknown')}")
        
        if stats.get('document_count', 0) == 0:
            print("⚠️ 向量数据库为空")
            vector_manager.close()
            return True
        
        # 检查文档样本
        print("\n📄 文档样本:")
        collection = vector_manager.vectorstore._collection
        sample_data = collection.get(limit=args.sample_size or 3)
        
        if sample_data['ids']:
            for i, doc_id in enumerate(sample_data['ids']):
                content = sample_data['documents'][i]
                metadata = sample_data['metadatas'][i] if sample_data['metadatas'] else {}
                
                print(f"   文档 {i+1}:")
                print(f"     ID: {doc_id}")
                print(f"     长度: {len(content)} 字符")
                print(f"     预览: {content[:100]}...")
                print(f"     职位ID: {metadata.get('job_id', '未知')}")
                print(f"     类型: {metadata.get('document_type', '未知')}")
                print()
        
        # 测试搜索功能
        if args.test_search:
            print("🔍 搜索功能测试:")
            test_queries = args.queries.split(',') if args.queries else ["Python", "开发工程师", "前端"]
            
            for query in test_queries:
                results = vector_manager.search_similar_jobs(query.strip(), k=2)
                scored_results = vector_manager.similarity_search_with_score(query.strip(), k=2)
                
                print(f"   查询 '{query.strip()}': {len(results)} 个结果")
                if scored_results:
                    top_score = scored_results[0][1]
                    print(f"     最高相似度: {top_score:.3f}")
        
        # 检查元数据字段
        print("\n🏷️ 元数据字段:")
        if sample_data['metadatas']:
            all_fields = set()
            for metadata in sample_data['metadatas']:
                if metadata:
                    all_fields.update(metadata.keys())
            print(f"   字段: {list(all_fields)}")
        else:
            print("   ⚠️ 没有元数据")
        
        # 保存测试报告
        if args.output:
            test_report = {
                'timestamp': datetime.now().isoformat(),
                'stats': stats,
                'sample_documents': len(sample_data['ids']) if sample_data['ids'] else 0,
                'metadata_fields': list(all_fields) if sample_data['metadatas'] else []
            }
            
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(test_report, f, ensure_ascii=False, indent=2, default=str)
            print(f"\n💾 测试报告已保存到: {args.output}")
        
        vector_manager.close()
        print("\n✅ 向量数据库测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

async def clear_command(args):
    """清理向量数据库命令"""
    print("🗑️ 清理向量数据库")
    print("=" * 30)
    
    try:
        config = load_config(args.config)
        vector_config = config.get('rag_system', {}).get('vector_db', {})
        vector_manager = ChromaDBManager(vector_config)
        
        # 获取当前统计
        stats = vector_manager.get_collection_stats()
        doc_count = stats.get('document_count', 0)
        
        print(f"📊 当前文档数量: {doc_count}")
        
        if doc_count == 0:
            print("⚠️ 向量数据库已经是空的")
            vector_manager.close()
            return True
        
        # 确认删除
        if not args.force:
            confirm = input(f"确定要清空所有 {doc_count} 个文档吗？(y/N): ")
            if confirm.lower() != 'y':
                print("操作已取消")
                vector_manager.close()
                return True
        
        # 执行清理
        if args.job_id:
            # 删除特定职位的文档
            success = vector_manager.delete_documents(args.job_id)
            if success:
                print(f"✅ 成功删除职位 {args.job_id} 的文档")
            else:
                print(f"❌ 删除职位 {args.job_id} 的文档失败")
        else:
            # 清空所有文档
            collection = vector_manager.vectorstore._collection
            all_data = collection.get()
            
            if all_data['ids']:
                collection.delete(ids=all_data['ids'])
                print(f"✅ 成功清空 {len(all_data['ids'])} 个文档")
            else:
                print("📝 向量数据库已经是空的")
        
        # 验证清理结果
        new_stats = vector_manager.get_collection_stats()
        new_count = new_stats.get('document_count', 0)
        print(f"📊 清理后文档数量: {new_count}")
        
        vector_manager.close()
        return True
        
    except Exception as e:
        print(f"❌ 清理失败: {e}")
        return False

async def match_command(args):
    """简历职位匹配命令"""
    print("🎯 简历职位匹配")
    print("=" * 30)
    
    try:
        # 加载配置
        config = load_config(args.config)
        
        # 加载简历匹配配置
        resume_config_path = args.resume_config or 'config/resume_matching_config.yaml'
        resume_config = load_config(resume_config_path) if Path(resume_config_path).exists() else {}
        
        # 合并配置
        if resume_config:
            config.update(resume_config)
        
        # 初始化系统
        coordinator = RAGSystemCoordinator(config)
        if not coordinator.initialize_system():
            print("❌ 系统初始化失败")
            return False
        
        # 加载简历 - 统一使用通用格式
        if args.resume:
            resume_data = load_resume(args.resume)
            resume_profile = load_resume_profile(resume_data)
            print(f"📝 加载简历档案: {resume_profile.name}")
        else:
            # 使用默认简历档案
            resume_profile = create_default_zhanbin_profile()
            print("📝 使用默认简历档案")
        
        # 使用通用匹配引擎
        matcher = GenericResumeJobMatcher(coordinator.vector_manager, config.get('resume_matching', {}))
        print("🔧 使用通用匹配引擎")
        
        print(f"👤 简历档案: {resume_profile.name}")
        print(f"💼 当前职位: {resume_profile.current_position}")
        print(f"📅 工作经验: {resume_profile.total_experience_years}年")
        
        # 根据子命令执行不同操作
        if args.action == 'find-jobs':
            # 查找匹配职位
            print(f"\n🔍 查找匹配职位 (返回{args.limit}个)")
            
            # 构建过滤条件
            filters = {}
            if args.filters:
                try:
                    filters = json.loads(args.filters)
                except json.JSONDecodeError:
                    print("⚠️ 过滤条件JSON格式错误，忽略过滤")
            
            if not args.dry_run:
                # 执行匹配
                result = await matcher.find_matching_jobs(
                    resume_profile,
                    filters=filters,
                    top_k=args.limit
                )
                
                # 显示匹配摘要
                summary = result.matching_summary
                print(f"\n📊 匹配结果摘要:")
                print(f"   总匹配数: {summary.total_matches}")
                print(f"   高优先级: {summary.high_priority}")
                print(f"   中优先级: {summary.medium_priority}")
                print(f"   低优先级: {summary.low_priority}")
                print(f"   平均分数: {summary.average_score:.3f}")
                print(f"   处理时间: {summary.processing_time:.2f}秒")
                
                # 显示前几个匹配结果
                print(f"\n🎯 前{min(5, len(result.matches))}个匹配职位:")
                for i, match in enumerate(result.matches[:5], 1):
                    print(f"\n{i}. {match.job_title} - {match.company}")
                    print(f"   综合评分: {match.overall_score:.3f} ({match.match_level.value})")
                    print(f"   推荐优先级: {match.recommendation_priority.value}")
                    print(f"   技能匹配: {match.dimension_scores.get('skills_match', 0):.3f}")
                    print(f"   经验匹配: {match.dimension_scores.get('experience_match', 0):.3f}")
                    if match.location:
                        print(f"   地点: {match.location}")
                
                # 保存结果
                if args.output:
                    # 转换为可序列化的格式
                    output_data = {
                        'matching_summary': {
                            'total_matches': summary.total_matches,
                            'high_priority': summary.high_priority,
                            'medium_priority': summary.medium_priority,
                            'low_priority': summary.low_priority,
                            'average_score': summary.average_score,
                            'processing_time': summary.processing_time,
                            'timestamp': summary.timestamp
                        },
                        'matches': [
                            {
                                'job_id': match.job_id,
                                'job_title': match.job_title,
                                'company': match.company,
                                'location': match.location,
                                'salary_range': match.salary_range,
                                'overall_score': match.overall_score,
                                'dimension_scores': match.dimension_scores,
                                'match_level': match.match_level.value,
                                'recommendation_priority': match.recommendation_priority.value,
                                'match_analysis': {
                                    'strengths': match.match_analysis.strengths,
                                    'weaknesses': match.match_analysis.weaknesses,
                                    'recommendations': match.match_analysis.recommendations,
                                    'matched_skills': match.match_analysis.matched_skills,
                                    'missing_skills': match.match_analysis.missing_skills,
                                    'skill_gap_score': match.match_analysis.skill_gap_score,
                                    'experience_alignment': match.match_analysis.experience_alignment,
                                    'industry_fit': match.match_analysis.industry_fit
                                },
                                'confidence_level': match.confidence_level,
                                'timestamp': match.timestamp
                            }
                            for match in result.matches
                        ],
                        'career_insights': {
                            'top_matching_positions': result.career_insights.top_matching_positions,
                            'skill_gap_analysis': result.career_insights.skill_gap_analysis,
                            'salary_analysis': result.career_insights.salary_analysis,
                            'market_trends': result.career_insights.market_trends,
                            'career_recommendations': result.career_insights.career_recommendations
                        },
                        'query_metadata': result.query_metadata
                    }
                    
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
                    print(f"\n💾 匹配结果已保存到: {args.output}")
            else:
                print("🔍 干运行模式 - 跳过实际匹配")
        
        elif args.action == 'analyze-fit':
            # 分析特定职位匹配度
            if not args.job_id:
                print("❌ 需要指定 --job-id 参数")
                return False
            
            print(f"\n🔍 分析职位匹配度: {args.job_id}")
            
            if not args.dry_run:
                # 通用匹配引擎暂时不支持单个职位分析
                print("⚠️ 通用匹配引擎暂不支持单个职位分析，请使用 find-jobs 命令")
                return False
                
                if not match_result:
                    print(f"❌ 未找到职位 {args.job_id} 或分析失败")
                    return False
                
                # 显示详细分析结果
                print(f"\n📊 匹配分析结果:")
                print(f"   职位: {match_result.job_title} - {match_result.company}")
                print(f"   综合评分: {match_result.overall_score:.3f} ({match_result.match_level.value})")
                print(f"   推荐优先级: {match_result.recommendation_priority.value}")
                print(f"   置信度: {match_result.confidence_level:.3f}")
                
                print(f"\n📈 维度评分:")
                for dimension, score in match_result.dimension_scores.items():
                    print(f"   {dimension}: {score:.3f}")
                
                print(f"\n💪 优势:")
                for strength in match_result.match_analysis.strengths:
                    print(f"   • {strength}")
                
                print(f"\n⚠️ 劣势:")
                for weakness in match_result.match_analysis.weaknesses:
                    print(f"   • {weakness}")
                
                print(f"\n💡 建议:")
                for recommendation in match_result.match_analysis.recommendations:
                    print(f"   • {recommendation}")
                
                print(f"\n✅ 匹配技能:")
                for skill in match_result.match_analysis.matched_skills[:10]:  # 只显示前10个
                    print(f"   • {skill}")
                
                print(f"\n❌ 缺失技能:")
                for skill in match_result.match_analysis.missing_skills[:10]:  # 只显示前10个
                    print(f"   • {skill}")
                
                # 保存结果
                if args.output:
                    output_data = {
                        'job_id': match_result.job_id,
                        'job_title': match_result.job_title,
                        'company': match_result.company,
                        'overall_score': match_result.overall_score,
                        'match_level': match_result.match_level.value,
                        'dimension_scores': match_result.dimension_scores,
                        'match_analysis': {
                            'strengths': match_result.match_analysis.strengths,
                            'weaknesses': match_result.match_analysis.weaknesses,
                            'recommendations': match_result.match_analysis.recommendations,
                            'matched_skills': match_result.match_analysis.matched_skills,
                            'missing_skills': match_result.match_analysis.missing_skills
                        },
                        'timestamp': match_result.timestamp
                    }
                    
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
                    print(f"\n💾 分析结果已保存到: {args.output}")
            else:
                print("🔍 干运行模式 - 跳过实际分析")
        
        elif args.action == 'batch-analyze':
            # 批量分析多个职位
            if not args.job_list:
                print("❌ 需要指定 --job-list 参数")
                return False
            
            # 读取职位ID列表
            if not Path(args.job_list).exists():
                print(f"❌ 职位列表文件不存在: {args.job_list}")
                return False
            
            with open(args.job_list, 'r', encoding='utf-8') as f:
                job_ids = [line.strip() for line in f if line.strip()]
            
            print(f"\n🔍 批量分析 {len(job_ids)} 个职位")
            
            if not args.dry_run:
                print("⚠️ 通用匹配引擎暂不支持批量分析，请使用 find-jobs 命令")
                return False
                
                print(f"\n📊 批量分析完成，成功分析 {len(results)} 个职位")
                
                # 显示前几个结果
                print(f"\n🎯 前{min(5, len(results))}个匹配结果:")
                for i, match in enumerate(results[:5], 1):
                    print(f"\n{i}. {match.job_title} - {match.company}")
                    print(f"   评分: {match.overall_score:.3f} ({match.match_level.value})")
                    print(f"   优先级: {match.recommendation_priority.value}")
                
                # 保存结果
                if args.output:
                    output_data = [
                        {
                            'job_id': match.job_id,
                            'job_title': match.job_title,
                            'company': match.company,
                            'overall_score': match.overall_score,
                            'match_level': match.match_level.value,
                            'recommendation_priority': match.recommendation_priority.value,
                            'dimension_scores': match.dimension_scores
                        }
                        for match in results
                    ]
                    
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
                    print(f"\n💾 批量分析结果已保存到: {args.output}")
            else:
                print("🔍 干运行模式 - 跳过实际分析")
        
        elif args.action == 'generate-report':
            # 生成匹配报告
            print(f"\n📄 生成匹配报告")
            
            if not args.dry_run:
                # 先执行匹配
                result = await matcher.find_matching_jobs(
                    resume_profile,
                    top_k=args.limit
                )
                
                # 生成HTML报告
                html_report = generate_html_report(result, resume_profile)
                
                output_file = args.output or f"resume_matching_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(html_report)
                
                print(f"✅ 匹配报告已生成: {output_file}")
            else:
                print("🔍 干运行模式 - 跳过报告生成")
        
        return True
        
    except Exception as e:
        print(f"❌ 匹配失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def resume_command(args):
    """简历文档处理命令"""
    print("📝 简历文档处理")
    print("=" * 30)
    
    try:
        config = load_config(args.config)
        
        if args.action == 'process':
            # 处理单个简历文档
            print(f"📄 处理简历文档: {args.input}")
            
            if not Path(args.input).exists():
                print(f"❌ 简历文件不存在: {args.input}")
                return False
            
            # 创建文档解析器
            parser_config = config.get('resume_processing', {}).get('document_parser', {})
            parser = ResumeDocumentParser(parser_config)
            
            # 解析文档
            try:
                content = parser.extract_content(args.input)
                print(f"✅ 文档解析完成，内容长度: {len(content)} 字符")
                
                if args.dry_run:
                    print("🔍 干运行模式 - 跳过RAG处理")
                    if args.output:
                        with open(args.output, 'w', encoding='utf-8') as f:
                            f.write(content)
                        print(f"📄 原始内容已保存到: {args.output}")
                    return True
                
                # 创建LLM客户端
                llm_config = config.get('rag_system', {}).get('llm', {})
                llm_client = create_llm(
                    provider=llm_config.get('provider', 'zhipu'),
                    api_key=llm_config.get('api_key'),
                    model=llm_config.get('model', 'glm-4-flash'),
                    temperature=llm_config.get('temperature', 0.1),
                    max_tokens=llm_config.get('max_tokens', 2000)
                )
                
                # 创建RAG处理器
                processor_config = config.get('resume_processing', {}).get('rag_processor', {})
                processor = ResumeDocumentProcessor(llm_client, processor_config)
                
                # 处理简历
                user_hints = {}
                if hasattr(args, 'hints') and args.hints:
                    try:
                        user_hints = json.loads(args.hints)
                    except json.JSONDecodeError:
                        print("⚠️ 用户提示JSON格式错误，忽略")
                
                profile = await processor.process_resume_document(content, user_hints)
                
                print(f"✅ 简历处理完成: {profile.name}")
                print(f"   当前职位: {profile.current_position}")
                print(f"   工作经验: {profile.total_experience_years}年")
                print(f"   技能分类: {len(profile.skill_categories)}个")
                print(f"   工作经历: {len(profile.work_history)}段")
                
                # 保存结果
                if args.output:
                    output_data = profile.to_dict()
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
                    print(f"💾 处理结果已保存到: {args.output}")
                
                return True
                
            except Exception as e:
                print(f"❌ 文档处理失败: {e}")
                return False
        
        elif args.action == 'batch-process':
            # 批量处理简历文档
            print(f"📁 批量处理简历文档")
            
            if not Path(args.input_dir).exists():
                print(f"❌ 输入目录不存在: {args.input_dir}")
                return False
            
            # 获取支持的格式
            formats = args.formats.split(',') if args.formats else ['md', 'docx', 'pdf', 'txt']
            print(f"📋 支持格式: {formats}")
            
            # 查找文件
            input_dir = Path(args.input_dir)
            files_to_process = []
            
            for format_ext in formats:
                pattern = f"*.{format_ext}"
                files_to_process.extend(input_dir.glob(pattern))
            
            if not files_to_process:
                print(f"❌ 在目录 {args.input_dir} 中未找到支持的简历文件")
                return False
            
            print(f"📊 找到 {len(files_to_process)} 个文件待处理")
            
            if args.dry_run:
                print("🔍 干运行模式 - 仅显示文件列表")
                for i, file_path in enumerate(files_to_process, 1):
                    print(f"  {i}. {file_path.name}")
                return True
            
            # 创建输出目录
            output_dir = Path(args.output_dir) if args.output_dir else Path('./processed_resumes')
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建解析器和处理器
            parser_config = config.get('resume_processing', {}).get('document_parser', {})
            parser = ResumeDocumentParser(parser_config)
            
            llm_config = config.get('rag_system', {}).get('llm', {})
            llm_client = create_llm(
                provider=llm_config.get('provider', 'zhipu'),
                api_key=llm_config.get('api_key'),
                model=llm_config.get('model', 'glm-4-flash'),
                temperature=llm_config.get('temperature', 0.1),
                max_tokens=llm_config.get('max_tokens', 2000)
            )
            
            processor_config = config.get('resume_processing', {}).get('rag_processor', {})
            processor = ResumeDocumentProcessor(llm_client, processor_config)
            
            # 批量处理
            successful = 0
            failed = 0
            
            for i, file_path in enumerate(files_to_process, 1):
                try:
                    print(f"\n📄 处理文件 {i}/{len(files_to_process)}: {file_path.name}")
                    
                    # 解析文档
                    content = parser.extract_content(str(file_path))
                    
                    # RAG处理
                    profile = await processor.process_resume_document(content)
                    
                    # 保存结果
                    output_file = output_dir / f"{file_path.stem}_processed.json"
                    output_data = profile.to_dict()
                    
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
                    
                    print(f"   ✅ 成功: {profile.name}")
                    successful += 1
                    
                except Exception as e:
                    print(f"   ❌ 失败: {e}")
                    failed += 1
                
                # 并发控制
                if args.parallel and i % args.parallel == 0:
                    await asyncio.sleep(1)  # 简单的速率限制
            
            print(f"\n📊 批量处理完成:")
            print(f"   成功: {successful}")
            print(f"   失败: {failed}")
            print(f"   总计: {len(files_to_process)}")
            print(f"   输出目录: {output_dir}")
            
            return successful > 0
        
        elif args.action == 'validate':
            # 验证简历JSON格式
            print(f"🔍 验证简历JSON: {args.input}")
            
            if not Path(args.input).exists():
                print(f"❌ 文件不存在: {args.input}")
                return False
            
            try:
                with open(args.input, 'r', encoding='utf-8') as f:
                    resume_data = json.load(f)
                
                # 基本格式检查
                if args.schema_check:
                    print("📋 执行模式验证...")
                    
                    # 检查必需字段
                    required_fields = ['name', 'skill_categories', 'work_history']
                    missing_fields = []
                    
                    for field in required_fields:
                        if field not in resume_data:
                            missing_fields.append(field)
                    
                    if missing_fields:
                        print(f"❌ 缺少必需字段: {missing_fields}")
                        return False
                    
                    print("✅ 模式验证通过")
                
                # 完整性检查
                if args.completeness_check:
                    print("📊 执行完整性检查...")
                    
                    issues = []
                    
                    # 检查基本信息完整性
                    if not resume_data.get('name'):
                        issues.append("姓名为空")
                    if not resume_data.get('email'):
                        issues.append("邮箱为空")
                    
                    # 检查技能分类
                    skill_categories = resume_data.get('skill_categories', [])
                    if not skill_categories:
                        issues.append("没有技能分类")
                    else:
                        for i, category in enumerate(skill_categories):
                            if not category.get('skills'):
                                issues.append(f"技能分类 {i+1} 没有技能列表")
                    
                    # 检查工作经历
                    work_history = resume_data.get('work_history', [])
                    if not work_history:
                        issues.append("没有工作经历")
                    else:
                        for i, work in enumerate(work_history):
                            if not work.get('company'):
                                issues.append(f"工作经历 {i+1} 缺少公司名称")
                            if not work.get('position'):
                                issues.append(f"工作经历 {i+1} 缺少职位名称")
                    
                    if issues:
                        print("⚠️ 发现完整性问题:")
                        for issue in issues:
                            print(f"   • {issue}")
                    else:
                        print("✅ 完整性检查通过")
                
                # 尝试创建GenericResumeProfile
                try:
                    profile = GenericResumeProfile.from_dict(resume_data)
                    print(f"✅ 成功创建简历档案: {profile.name}")
                    print(f"   技能分类: {len(profile.skill_categories)}个")
                    print(f"   工作经历: {len(profile.work_history)}段")
                    print(f"   教育背景: {len(profile.education)}条")
                    print(f"   项目经验: {len(profile.projects)}个")
                except Exception as e:
                    print(f"❌ 创建简历档案失败: {e}")
                    return False
                
                return True
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON格式错误: {e}")
                return False
            except Exception as e:
                print(f"❌ 验证失败: {e}")
                return False
        
        elif args.action == 'match':
            # 完整流程：文档处理 + 职位匹配
            print(f"🎯 完整流程: 文档处理 + 职位匹配")
            
            if not Path(args.input).exists():
                print(f"❌ 简历文件不存在: {args.input}")
                return False
            
            # 步骤1: 处理简历文档
            print("📄 步骤1: 处理简历文档")
            
            parser_config = config.get('resume_processing', {}).get('document_parser', {})
            parser = ResumeDocumentParser(parser_config)
            
            content = parser.extract_content(args.input)
            print(f"✅ 文档解析完成")
            
            if not args.dry_run:
                # 创建LLM客户端和处理器
                llm_config = config.get('rag_system', {}).get('llm', {})
                llm_client = create_llm(
                    provider=llm_config.get('provider', 'zhipu'),
                    api_key=llm_config.get('api_key'),
                    model=llm_config.get('model', 'glm-4-flash'),
                    temperature=llm_config.get('temperature', 0.1),
                    max_tokens=llm_config.get('max_tokens', 2000)
                )
                
                processor_config = config.get('resume_processing', {}).get('rag_processor', {})
                processor = ResumeDocumentProcessor(llm_client, processor_config)
                
                profile = await processor.process_resume_document(content)
                print(f"✅ 简历处理完成: {profile.name}")
                
                # 步骤2: 职位匹配
                print("\n🎯 步骤2: 职位匹配")
                
                # 初始化匹配系统
                coordinator = RAGSystemCoordinator(config)
                if not coordinator.initialize_system():
                    print("❌ 匹配系统初始化失败")
                    return False
                
                matcher = GenericResumeJobMatcher(coordinator.vector_manager, config.get('resume_matching', {}))
                
                # 执行匹配
                result = await matcher.find_matching_jobs(profile, top_k=args.limit)
                
                print(f"✅ 匹配完成，找到 {result.matching_summary.total_matches} 个职位")
                print(f"   高优先级: {result.matching_summary.high_priority}")
                print(f"   中优先级: {result.matching_summary.medium_priority}")
                print(f"   低优先级: {result.matching_summary.low_priority}")
                
                # 保存结果
                if args.output:
                    output_data = {
                        'resume_profile': profile.to_dict(),
                        'matching_results': {
                            'matching_summary': {
                                'total_matches': result.matching_summary.total_matches,
                                'high_priority': result.matching_summary.high_priority,
                                'medium_priority': result.matching_summary.medium_priority,
                                'low_priority': result.matching_summary.low_priority,
                                'average_score': result.matching_summary.average_score,
                                'processing_time': result.matching_summary.processing_time
                            },
                            'matches': [
                                {
                                    'job_id': match.job_id,
                                    'job_title': match.job_title,
                                    'company': match.company,
                                    'overall_score': match.overall_score,
                                    'match_level': match.match_level.value,
                                    'recommendation_priority': match.recommendation_priority.value
                                }
                                for match in result.matches
                            ]
                        }
                    }
                    
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
                    print(f"💾 完整结果已保存到: {args.output}")
                
                return True
            else:
                print("🔍 干运行模式 - 跳过RAG处理和匹配")
                return True
        
        else:
            print(f"❌ 未知操作: {args.action}")
            return False
            
    except Exception as e:
        print(f"❌ 简历处理失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def generate_html_report(result, resume_profile):
    """生成HTML格式的匹配报告"""
    html_template = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>简历职位匹配报告 - {name}</title>
        <style>
            body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid #007bff; }}
            .summary {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
            .match-item {{ border: 1px solid #ddd; margin-bottom: 20px; padding: 20px; border-radius: 8px; }}
            .match-excellent {{ border-left: 5px solid #28a745; }}
            .match-good {{ border-left: 5px solid #17a2b8; }}
            .match-fair {{ border-left: 5px solid #ffc107; }}
            .match-poor {{ border-left: 5px solid #dc3545; }}
            .score {{ font-size: 24px; font-weight: bold; color: #007bff; }}
            .skills {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 10px; }}
            .skill-tag {{ background: #007bff; color: white; padding: 3px 8px; border-radius: 12px; font-size: 12px; }}
            .missing-skill {{ background: #dc3545; }}
            .insights {{ background: #e9ecef; padding: 20px; border-radius: 8px; margin-top: 30px; }}
            .chart {{ margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>简历职位匹配报告</h1>
                <h2>{name} - {position}</h2>
                <p>生成时间: {timestamp}</p>
            </div>
            
            <div class="summary">
                <h3>📊 匹配摘要</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
                    <div><strong>总匹配数:</strong> {total_matches}</div>
                    <div><strong>高优先级:</strong> {high_priority}</div>
                    <div><strong>中优先级:</strong> {medium_priority}</div>
                    <div><strong>低优先级:</strong> {low_priority}</div>
                    <div><strong>平均分数:</strong> {average_score:.3f}</div>
                    <div><strong>处理时间:</strong> {processing_time:.2f}秒</div>
                </div>
            </div>
            
            <h3>🎯 匹配职位详情</h3>
            {matches_html}
            
            <div class="insights">
                <h3>💡 职业洞察</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                    <div>
                        <h4>热门职位</h4>
                        <ul>{top_positions}</ul>
                    </div>
                    <div>
                        <h4>技能建议</h4>
                        <ul>{skill_recommendations}</ul>
                    </div>
                    <div>
                        <h4>职业建议</h4>
                        <ul>{career_recommendations}</ul>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    # 生成匹配职位HTML
    matches_html = ""
    for i, match in enumerate(result.matches, 1):
        match_class = f"match-{match.match_level.value}"
        
        matched_skills_html = "".join([f'<span class="skill-tag">{skill}</span>' for skill in match.match_analysis.matched_skills[:10]])
        missing_skills_html = "".join([f'<span class="skill-tag missing-skill">{skill}</span>' for skill in match.match_analysis.missing_skills[:5]])
        
        matches_html += f"""
        <div class="match-item {match_class}">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h4>{match.job_title} - {match.company}</h4>
                    <p>{match.location or '地点未知'}</p>
                </div>
                <div class="score">{match.overall_score:.3f}</div>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 15px 0;">
                <div><strong>技能匹配:</strong> {match.dimension_scores.get('skills_match', 0):.3f}</div>
                <div><strong>经验匹配:</strong> {match.dimension_scores.get('experience_match', 0):.3f}</div>
                <div><strong>行业匹配:</strong> {match.dimension_scores.get('industry_match', 0):.3f}</div>
                <div><strong>薪资匹配:</strong> {match.dimension_scores.get('salary_match', 0):.3f}</div>
            </div>
            
            <div>
                <strong>匹配技能:</strong>
                <div class="skills">{matched_skills_html}</div>
            </div>
            
            <div style="margin-top: 10px;">
                <strong>缺失技能:</strong>
                <div class="skills">{missing_skills_html}</div>
            </div>
            
            <div style="margin-top: 15px;">
                <strong>建议:</strong>
                <ul>{"".join([f"<li>{rec}</li>" for rec in match.match_analysis.recommendations])}</ul>
            </div>
        </div>
        """
    
    # 生成洞察HTML
    top_positions = "".join([f"<li>{pos}</li>" for pos in result.career_insights.top_matching_positions])
    skill_recommendations = "".join([f"<li>{skill}</li>" for skill in result.career_insights.skill_gap_analysis.get('high_demand_missing', [])])
    career_recommendations = "".join([f"<li>{rec}</li>" for rec in result.career_insights.career_recommendations])
    
    return html_template.format(
        name=resume_profile.name,
        position=resume_profile.current_position,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        total_matches=result.matching_summary.total_matches,
        high_priority=result.matching_summary.high_priority,
        medium_priority=result.matching_summary.medium_priority,
        low_priority=result.matching_summary.low_priority,
        average_score=result.matching_summary.average_score,
        processing_time=result.matching_summary.processing_time,
        matches_html=matches_html,
        top_positions=top_positions,
        skill_recommendations=skill_recommendations,
        career_recommendations=career_recommendations
    )

async def chat_command(args):
    """智能分析聊天命令"""
    print("🤖 就业市场分析助手")
    print("=" * 40)
    
    try:
        # 加载配置
        config = load_config(args.config)
        
        # 加载Agent配置
        agent_config_path = args.agent_config or 'config/agent_config.yaml'
        if Path(agent_config_path).exists():
            agent_config = load_config(agent_config_path)
            # 合并配置
            config.update(agent_config)
        else:
            print(f"⚠️ Agent配置文件不存在: {agent_config_path}")
            print("使用默认配置...")
        
        # 初始化RAG系统
        coordinator = RAGSystemCoordinator(config)
        if not coordinator.initialize_system():
            print("❌ RAG系统初始化失败")
            return False
        
        # 创建分析Agent
        try:
            agent = create_analysis_agent(coordinator, config)
            print("✅ 智能分析Agent初始化成功")
        except Exception as e:
            print(f"❌ Agent初始化失败: {e}")
            return False
        
        # 显示Agent状态
        status = agent.get_agent_status()
        print(f"\n📊 Agent状态:")
        print(f"   可用工具: {len(status['tools_available'])}")
        print(f"   工具列表: {', '.join(status['tools_available'])}")
        print(f"   LLM提供商: {status['llm_provider']}")
        
        # 显示欢迎信息
        welcome_msg = config.get('langchain_agent', {}).get('user_experience', {}).get('interaction', {}).get('welcome_message')
        if welcome_msg:
            print(f"\n💬 {welcome_msg}")
        
        # 显示帮助信息
        if args.show_help:
            help_msg = config.get('langchain_agent', {}).get('user_experience', {}).get('interaction', {}).get('help_message')
            if help_msg:
                print(f"\n❓ 使用帮助:\n{help_msg}")
            
            # 显示建议问题
            suggested_questions = config.get('langchain_agent', {}).get('user_experience', {}).get('suggested_questions', [])
            if suggested_questions:
                print(f"\n💡 建议问题:")
                for i, question in enumerate(suggested_questions[:5], 1):
                    print(f"   {i}. {question}")
        
        print(f"\n{'='*40}")
        print("💡 输入 'help' 查看帮助，'quit' 或 'exit' 退出")
        print("💡 输入 'clear' 清除对话历史，'status' 查看Agent状态")
        print("💡 输入 'stats' 查看分析统计信息")
        print("💡 按 Ctrl+C 可以随时退出聊天")
        print("="*40)
        
        # 交互循环
        conversation_count = 0
        
        while True:
            try:
                # 获取用户输入
                user_input = input("\n🤔 您的问题: ").strip()
                
                if not user_input:
                    continue
                
                # 处理特殊命令
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 再见！")
                    break
                
                elif user_input.lower() == 'help':
                    help_msg = config.get('langchain_agent', {}).get('user_experience', {}).get('interaction', {}).get('help_message')
                    if help_msg:
                        print(f"\n❓ 使用帮助:\n{help_msg}")
                    
                    suggested_questions = config.get('langchain_agent', {}).get('user_experience', {}).get('suggested_questions', [])
                    if suggested_questions:
                        print(f"\n💡 建议问题:")
                        for i, question in enumerate(suggested_questions, 1):
                            print(f"   {i}. {question}")
                    continue
                
                elif user_input.lower() == 'clear':
                    agent.clear_memory()
                    conversation_count = 0
                    print("🧹 对话历史已清除")
                    continue
                
                elif user_input.lower() == 'status':
                    status = agent.get_agent_status()
                    print(f"\n📊 Agent状态:")
                    print(f"   可用工具: {len(status['tools_available'])}")
                    print(f"   对话消息数: {status['memory_messages_count']}")
                    print(f"   回调步骤数: {status['callback_steps']}")
                    print(f"   最后分析时间: {status.get('last_analysis_time', '无')}")
                    continue
                
                elif user_input.lower() == 'stats':
                    stats = agent.get_analysis_statistics()
                    print(f"\n📈 分析统计:")
                    print(f"   总分析次数: {stats.get('total_analyses', 0)}")
                    print(f"   成功分析次数: {stats.get('successful_analyses', 0)}")
                    print(f"   成功率: {stats.get('success_rate', 0):.1f}%")
                    print(f"   平均处理时间: {stats.get('average_processing_time', 0):.2f}秒")
                    print(f"   对话长度: {stats.get('conversation_length', 0)}")
                    
                    tool_usage = stats.get('tool_usage', {})
                    if tool_usage:
                        print(f"   工具使用统计:")
                        for tool, count in tool_usage.items():
                            print(f"     {tool}: {count}次")
                    continue
                
                # 处理分析问题
                print(f"\n🔍 正在分析您的问题...")
                
                # 执行分析
                result = agent.run(user_input)
                
                if result['success']:
                    print(f"\n🤖 分析结果:")
                    print(f"{result['response']}")
                    
                    # 显示处理信息
                    if args.verbose:
                        print(f"\n📊 处理信息:")
                        print(f"   处理时间: {result['processing_time']:.2f}秒")
                        print(f"   使用工具: {', '.join(result['tools_used']) if result['tools_used'] else '无'}")
                        
                        if result.get('analysis_steps'):
                            print(f"   分析步骤: {len(result['analysis_steps'])}步")
                    
                    conversation_count += 1
                    
                    # 保存对话记录
                    if args.save_conversations:
                        save_conversation(user_input, result, conversation_count, args.conversation_dir)
                    
                else:
                    print(f"\n❌ 分析失败: {result.get('error', '未知错误')}")
                
                # 性能优化
                if conversation_count % 10 == 0:
                    print("🔧 正在优化性能...")
                    agent.optimize_performance()
                
            except KeyboardInterrupt:
                print("\n\n💡 检测到 Ctrl+C，正在退出...")
                print("👋 再见！")
                break
            except EOFError:
                print("\n👋 再见！")
                break
            except Exception as e:
                print(f"\n❌ 处理错误: {e}")
                if args.debug:
                    import traceback
                    traceback.print_exc()
                continue
        
        # 显示会话统计
        final_stats = agent.get_analysis_statistics()
        print(f"\n📊 本次会话统计:")
        print(f"   总问题数: {conversation_count}")
        print(f"   成功分析: {final_stats.get('successful_analyses', 0)}")
        print(f"   平均处理时间: {final_stats.get('average_processing_time', 0):.2f}秒")
        
        return True
        
    except Exception as e:
        print(f"❌ 聊天系统启动失败: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return False

def save_conversation(question: str, result: dict, count: int, conversation_dir: str = None):
    """保存对话记录"""
    try:
        if not conversation_dir:
            conversation_dir = "logs/conversations"
        
        Path(conversation_dir).mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"conversation_{timestamp}_{count:03d}.json"
        filepath = Path(conversation_dir) / filename
        
        conversation_data = {
            'timestamp': result.get('timestamp'),
            'question': question,
            'response': result.get('response'),
            'processing_time': result.get('processing_time'),
            'tools_used': result.get('tools_used', []),
            'success': result.get('success', False),
            'analysis_steps': result.get('analysis_steps', [])
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(conversation_data, f, ensure_ascii=False, indent=2, default=str)
            
    except Exception as e:
        print(f"⚠️ 保存对话记录失败: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='RAG智能简历投递系统CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 运行数据流水线
  python rag_cli.py pipeline run --batch-size 20 --show-progress
  
  # 查看系统状态
  python rag_cli.py status
  
  # 分析简历差距
  python rag_cli.py optimize analyze --resume resume.json --output analysis.json
  
  # 优化简历内容
  python rag_cli.py optimize optimize --resume resume.json --target-job job123
  
  # 生成求职信
  python rag_cli.py optimize cover-letter --resume resume.json --target-job job123
  
  # 搜索相关职位
  python rag_cli.py search "Python开发工程师" --limit 5
  
  # 简历职位匹配
  python rag_cli.py match find-jobs --resume data/zhanbin_resume.json --limit 20 --output matches.json
  
  # 分析特定职位匹配度
  python rag_cli.py match analyze-fit --resume data/zhanbin_resume.json --job-id job123 --output analysis.json
  
  # 批量分析多个职位
  python rag_cli.py match batch-analyze --resume data/zhanbin_resume.json --job-list jobs.txt --output batch_results.json
  
  # 生成HTML匹配报告
  python rag_cli.py match generate-report --resume data/zhanbin_resume.json --output report.html
  
  # 测试向量数据库
  python rag_cli.py test --test-search --queries "Python,Java,前端"
  
  # 清理向量数据库
  python rag_cli.py clear --force
  
  # 删除特定职位文档
  python rag_cli.py clear --job-id job123
  
  # 启动智能分析聊天
  python rag_cli.py chat --show-help --verbose
  
  # 启动聊天并保存对话记录
  python rag_cli.py chat --save-conversations --conversation-dir logs/chat
        """
    )
    
    # 全局参数
    parser.add_argument('--config', '-c', help='配置文件路径')
    parser.add_argument('--log-level', default='INFO', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       help='日志级别')
    parser.add_argument('--log-file', help='日志文件路径')
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 流水线命令
    pipeline_parser = subparsers.add_parser('pipeline', help='数据流水线管理')
    pipeline_parser.add_argument('action', choices=['run', 'resume'], help='流水线操作')
    pipeline_parser.add_argument('--batch-size', '-b', type=int, help='批处理大小')
    pipeline_parser.add_argument('--max-jobs', '-m', type=int, help='最大处理职位数量')
    pipeline_parser.add_argument('--force-reprocess', '-f', action='store_true', help='强制重新处理')
    pipeline_parser.add_argument('--no-save', action='store_true', help='不保存处理结果')
    pipeline_parser.add_argument('--show-progress', '-p', action='store_true', help='显示处理进度')
    
    # 状态命令
    status_parser = subparsers.add_parser('status', help='查询系统状态')
    
    # 简历优化命令
    optimize_parser = subparsers.add_parser('optimize', help='简历优化')
    optimize_parser.add_argument('action', choices=['analyze', 'optimize', 'cover-letter'], help='优化操作')
    optimize_parser.add_argument('--resume', '-r', required=True, help='简历文件路径')
    optimize_parser.add_argument('--target-jobs', help='目标职位ID列表（逗号分隔）')
    optimize_parser.add_argument('--target-job', help='单个目标职位ID')
    optimize_parser.add_argument('--focus-areas', help='优化重点领域（逗号分隔）')
    optimize_parser.add_argument('--output', '-o', help='输出文件路径')
    optimize_parser.add_argument('--dry-run', action='store_true', help='干运行模式（不调用LLM）')
    
    # 搜索命令
    search_parser = subparsers.add_parser('search', help='职位搜索')
    search_parser.add_argument('query', help='搜索查询')
    search_parser.add_argument('--limit', '-l', type=int, default=10, help='返回结果数量')
    search_parser.add_argument('--output', '-o', help='输出文件路径')
    
    # 测试命令
    test_parser = subparsers.add_parser('test', help='向量数据库测试')
    test_parser.add_argument('--sample-size', '-s', type=int, default=3, help='样本文档数量')
    test_parser.add_argument('--test-search', action='store_true', help='测试搜索功能')
    test_parser.add_argument('--queries', help='测试查询（逗号分隔）')
    test_parser.add_argument('--output', '-o', help='测试报告输出路径')
    
    # 清理命令
    clear_parser = subparsers.add_parser('clear', help='清理向量数据库')
    clear_parser.add_argument('--job-id', help='删除特定职位的文档')
    clear_parser.add_argument('--force', '-f', action='store_true', help='强制删除，不询问确认')
    
    # 简历匹配命令
    match_parser = subparsers.add_parser('match', help='简历职位匹配')
    match_parser.add_argument('action', choices=[
        'find-jobs', 'analyze-fit', 'batch-analyze', 'generate-report'
    ], help='匹配操作')
    match_parser.add_argument('--resume', '-r', help='简历文件路径')
    match_parser.add_argument('--resume-config', help='简历匹配配置文件路径')
    match_parser.add_argument('--limit', '-l', type=int, default=20, help='返回匹配职位数量')
    match_parser.add_argument('--output', '-o', help='输出文件路径')
    match_parser.add_argument('--filters', help='过滤条件（JSON格式）')
    match_parser.add_argument('--threshold', type=float, default=0.5, help='匹配度阈值')
    match_parser.add_argument('--job-id', help='特定职位ID（用于analyze-fit）')
    match_parser.add_argument('--job-list', help='职位ID列表文件路径（用于batch-analyze）')
    match_parser.add_argument('--dry-run', action='store_true', help='干运行模式（不执行实际匹配）')
    
    # 简历处理命令
    resume_parser = subparsers.add_parser('resume', help='简历文档处理')
    resume_parser.add_argument('action', choices=[
        'process', 'batch-process', 'validate', 'match'
    ], help='处理操作')
    
    # 通用参数
    resume_parser.add_argument('--input', '-i', help='输入文件路径')
    resume_parser.add_argument('--output', '-o', help='输出文件路径')
    resume_parser.add_argument('--format', choices=['md', 'docx', 'pdf', 'auto'],
                              default='auto', help='文档格式')
    resume_parser.add_argument('--dry-run', action='store_true', help='干运行模式')
    resume_parser.add_argument('--hints', help='用户提示信息（JSON格式）')
    
    # 批量处理参数
    resume_parser.add_argument('--input-dir', help='输入目录路径')
    resume_parser.add_argument('--output-dir', help='输出目录路径')
    resume_parser.add_argument('--formats', help='支持的格式列表（逗号分隔）')
    resume_parser.add_argument('--parallel', type=int, default=1, help='并行处理数量')
    
    # 验证参数
    resume_parser.add_argument('--schema-check', action='store_true', help='模式验证')
    resume_parser.add_argument('--completeness-check', action='store_true', help='完整性检查')
    
    # 匹配参数
    resume_parser.add_argument('--limit', type=int, default=20, help='匹配职位数量')
    
    # 智能聊天命令
    chat_parser = subparsers.add_parser('chat', help='智能分析聊天')
    chat_parser.add_argument('--agent-config', help='Agent配置文件路径')
    chat_parser.add_argument('--show-help', action='store_true', help='显示详细帮助信息')
    chat_parser.add_argument('--verbose', '-v', action='store_true', help='显示详细处理信息')
    chat_parser.add_argument('--debug', action='store_true', help='调试模式')
    chat_parser.add_argument('--save-conversations', action='store_true', help='保存对话记录')
    chat_parser.add_argument('--conversation-dir', default='logs/conversations', help='对话记录保存目录')
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging(args.log_level, args.log_file)
    
    # 确保必要目录存在
    Path('./logs').mkdir(exist_ok=True)
    Path('./pipeline_results').mkdir(exist_ok=True)
    
    # 执行命令
    success = False
    
    try:
        if args.command == 'pipeline':
            success = asyncio.run(pipeline_command(args))
        elif args.command == 'status':
            success = asyncio.run(status_command(args))
        elif args.command == 'optimize':
            success = asyncio.run(optimize_command(args))
        elif args.command == 'search':
            success = asyncio.run(search_command(args))
        elif args.command == 'test':
            success = asyncio.run(test_command(args))
        elif args.command == 'clear':
            success = asyncio.run(clear_command(args))
        elif args.command == 'match':
            success = asyncio.run(match_command(args))
        elif args.command == 'resume':
            success = asyncio.run(resume_command(args))
        elif args.command == 'chat':
            success = asyncio.run(chat_command(args))
        else:
            parser.print_help()
            success = False
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")
        success = False
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        success = False
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()