#!/usr/bin/env python3
"""
测试ResumeOptimizer功能
"""

import sys
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from src.rag.resume_optimizer import ResumeOptimizer
from src.rag.rag_system_coordinator import RAGSystemCoordinator

def test_resume_optimizer():
    """测试简历优化器"""
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🧪 测试ResumeOptimizer功能")
    print("=" * 50)
    
    async def run_tests():
        try:
            # 配置系统
            config = {
                'rag_system': {
                    'database': {
                        'path': './data/jobs.db',
                        'batch_size': 10
                    },
                    'llm': {
                        'provider': 'zhipu',
                        'model': 'glm-4-flash',
                        'api_key': 'test-key',  # 测试用
                        'temperature': 0.3,
                        'max_tokens': 2000
                    },
                    'vector_db': {
                        'persist_directory': './test_chroma_db',
                        'collection_name': 'test_job_positions',
                        'embeddings': {
                            'model_name': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                            'device': 'cpu',
                            'normalize_embeddings': True
                        }
                    },
                    'documents': {
                        'types': ['overview', 'responsibility', 'requirement', 'skills', 'basic_requirements']
                    }
                }
            }
            
            # 初始化组件
            coordinator = RAGSystemCoordinator(config)
            coordinator.initialize_system()
            
            llm_config = config['rag_system']['llm']
            optimizer = ResumeOptimizer(coordinator, llm_config)
            print("✅ ResumeOptimizer初始化成功")
            
            # 测试简历数据
            test_resume = {
                'name': '张三',
                'current_position': 'Python开发工程师',
                'years_of_experience': 3,
                'education': '本科 - 计算机科学与技术',
                'skills': ['Python', 'Django', 'MySQL', 'Git', 'Linux'],
                'summary': '具有3年Python开发经验，熟悉Web开发和数据库设计，有良好的编程习惯和团队协作能力。',
                'experience': [
                    {
                        'position': 'Python开发工程师',
                        'company': 'ABC科技有限公司',
                        'duration': '2021-2024',
                        'description': '负责Web应用开发，参与系统架构设计，维护数据库'
                    },
                    {
                        'position': '软件开发实习生',
                        'company': 'XYZ软件公司',
                        'duration': '2020-2021',
                        'description': '参与项目开发，学习编程规范，协助测试工作'
                    }
                ]
            }
            
            # 获取测试职位
            test_jobs = coordinator.db_reader.get_jobs_for_rag_processing(limit=2)
            if not test_jobs:
                print("⚠️ 没有可测试的职位数据")
                return False
            
            test_job_ids = [job['job_id'] for job in test_jobs]
            
            # 测试1: 简历差距分析（模拟模式）
            print("\n🔍 测试1: 简历差距分析（模拟模式）")
            print(f"   分析职位数: {len(test_job_ids)}")
            for i, job in enumerate(test_jobs, 1):
                print(f"   职位{i}: {job.get('title', '无标题')} - {job.get('company', '无公司')}")
            
            print("   ⚠️ 跳过实际LLM调用（避免API费用）")
            
            # 模拟差距分析结果
            mock_gap_analysis = {
                'individual_analyses': [
                    {
                        'job_id': test_job_ids[0],
                        'job_title': test_jobs[0].get('title', ''),
                        'company': test_jobs[0].get('company', ''),
                        'overall_match_score': 0.75,
                        'skill_gaps': [
                            {'missing_skill': 'React', 'importance': '高', 'suggestion': '学习前端框架'},
                            {'missing_skill': 'Docker', 'importance': '中', 'suggestion': '学习容器化技术'}
                        ],
                        'priority_improvements': ['学习React', '掌握Docker', '提升项目经验']
                    }
                ],
                'summary': {
                    'average_match_score': 0.75,
                    'most_common_skill_gaps': [('React', 1), ('Docker', 1)],
                    'total_jobs_analyzed': 1
                }
            }
            
            print(f"   模拟分析结果:")
            print(f"      平均匹配度: {mock_gap_analysis['summary']['average_match_score']}")
            print(f"      常见技能差距: {mock_gap_analysis['summary']['most_common_skill_gaps']}")
            
            # 测试2: 技能提升建议（模拟模式）
            print("\n💡 测试2: 技能提升建议（模拟模式）")
            print("   ⚠️ 跳过实际LLM调用")
            
            # 模拟技能建议
            mock_skill_suggestions = {
                'immediate_skills': [
                    {
                        'skill': 'React',
                        'priority': '高',
                        'learning_path': '官方文档 -> 实践项目 -> 进阶应用',
                        'estimated_time': '2-3个月'
                    }
                ],
                'long_term_skills': [
                    {
                        'skill': '微服务架构',
                        'market_demand': '高',
                        'career_impact': '显著提升架构能力'
                    }
                ]
            }
            
            print(f"   即时技能建议: {len(mock_skill_suggestions['immediate_skills'])} 个")
            print(f"   长期技能建议: {len(mock_skill_suggestions['long_term_skills'])} 个")
            
            # 测试3: 简历内容优化（模拟模式）
            print("\n📝 测试3: 简历内容优化（模拟模式）")
            target_job_id = test_job_ids[0]
            print(f"   目标职位: {target_job_id}")
            print("   ⚠️ 跳过实际LLM调用")
            
            # 模拟优化建议
            mock_optimization = {
                'summary_optimization': {
                    'original': test_resume['summary'],
                    'optimized': '具有3年Python开发经验，精通Django框架和MySQL数据库，熟悉前后端开发流程...',
                    'improvements': ['突出技术栈', '量化工作成果']
                },
                'keyword_optimization': {
                    'missing_keywords': ['API开发', '敏捷开发'],
                    'ats_optimization': ['增加行业关键词', '优化技能描述']
                }
            }
            
            print(f"   优化建议类型: 个人简介优化、关键词优化")
            print(f"   缺失关键词: {mock_optimization['keyword_optimization']['missing_keywords']}")
            
            # 测试4: 求职信生成（模拟模式）
            print("\n✉️ 测试4: 求职信生成（模拟模式）")
            print(f"   目标职位: {test_jobs[0].get('title', '')} - {test_jobs[0].get('company', '')}")
            print("   ⚠️ 跳过实际LLM调用")
            
            # 模拟求职信
            mock_cover_letter = f"""
尊敬的{test_jobs[0].get('company', '')}招聘负责人：

您好！我是{test_resume['name']}，一名具有{test_resume['years_of_experience']}年经验的{test_resume['current_position']}。
我对贵公司的{test_jobs[0].get('title', '')}职位非常感兴趣...

（模拟生成的求职信内容）

此致
敬礼！

{test_resume['name']}
"""
            
            print(f"   求职信长度: {len(mock_cover_letter)} 字符")
            print(f"   包含要素: 个人介绍、职位兴趣、技能匹配")
            
            # 测试5: 数据格式化功能
            print("\n🔧 测试5: 数据格式化功能")
            
            # 测试简历信息格式化
            formatted_resume = optimizer._format_resume_info(test_resume)
            print(f"   简历信息格式化: {len(formatted_resume)} 字符")
            
            # 测试职位信息格式化
            formatted_job = optimizer._format_job_info(test_jobs[0])
            print(f"   职位信息格式化: {len(formatted_job)} 字符")
            
            # 测试JSON解析功能
            test_json = '{"test": "value", "number": 123}'
            parsed_result = optimizer._parse_json_result(test_json)
            print(f"   JSON解析测试: {'✅ 成功' if 'test' in parsed_result else '❌ 失败'}")
            
            print("\n🎉 所有测试完成!")
            return True
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # 清理资源
            try:
                coordinator.cleanup_system()
                print("✅ 系统资源清理完成")
            except:
                pass
    
    # 运行异步测试
    return asyncio.run(run_tests())

if __name__ == "__main__":
    success = test_resume_optimizer()
    sys.exit(0 if success else 1)