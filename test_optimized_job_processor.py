#!/usr/bin/env python3
"""
测试优化的JobProcessor功能
"""

import sys
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from src.rag.optimized_job_processor import OptimizedJobProcessor
from src.rag.database_job_reader import DatabaseJobReader

def test_optimized_job_processor():
    """测试优化的职位处理器"""
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🧪 测试OptimizedJobProcessor功能")
    print("=" * 50)
    
    async def run_tests():
        try:
            # 初始化组件
            llm_config = {
                'provider': 'zhipu',
                'model': 'glm-4-flash',
                'api_key': 'your-api-key-here',  # 实际使用时需要配置
                'temperature': 0.1,
                'max_tokens': 1500
            }
            
            processor = OptimizedJobProcessor(llm_config=llm_config)
            print("✅ OptimizedJobProcessor初始化成功")
            
            # 初始化数据库读取器
            db_reader = DatabaseJobReader("./data/jobs.db")
            print("✅ DatabaseJobReader初始化成功")
            
            # 测试1: 获取测试数据
            print("\n📊 测试1: 获取测试数据")
            test_jobs = db_reader.get_jobs_for_rag_processing(limit=2)
            print(f"   获取到 {len(test_jobs)} 个测试职位")
            
            if not test_jobs:
                print("❌ 没有可测试的职位数据")
                return False
            
            # 测试2: 处理职位数据（模拟模式，不实际调用LLM）
            print("\n🔄 测试2: 职位数据处理（模拟模式）")
            for i, job_data in enumerate(test_jobs[:2], 1):
                print(f"\n   处理职位 {i}: {job_data.get('title', '无标题')}")
                print(f"      公司: {job_data.get('company', '无公司')}")
                print(f"      薪资: {job_data.get('salary', '无薪资信息')}")
                print(f"      描述长度: {len(job_data.get('description', '') or '')}")
                print(f"      要求长度: {len(job_data.get('requirements', '') or '')}")
                
                # 模拟处理结果（不实际调用LLM）
                mock_job_structure = processor._fallback_extraction_from_db(job_data)
                print(f"      处理结果: {mock_job_structure.job_title} - {mock_job_structure.company}")
                
                # 测试文档创建
                documents = processor.create_documents(
                    mock_job_structure, 
                    job_id=job_data.get('job_id'),
                    job_url=job_data.get('url')
                )
                print(f"      创建文档数: {len(documents)}")
                
                # 显示文档类型
                doc_types = [doc.metadata.get('type') for doc in documents]
                print(f"      文档类型: {', '.join(doc_types)}")
                
                # 验证职位结构
                is_valid = processor.validate_job_structure(mock_job_structure)
                print(f"      结构有效性: {'✅ 有效' if is_valid else '❌ 无效'}")
                
                # 获取处理统计
                stats = processor.get_processing_stats(mock_job_structure)
                print(f"      处理统计: 职责{stats['responsibilities_count']}个, 要求{stats['requirements_count']}个, 技能{stats['skills_count']}个")
            
            # 测试3: 字段映射验证
            print("\n🔍 测试3: 字段映射验证")
            sample_job = test_jobs[0]
            
            # 直接映射字段测试
            direct_fields = {
                'title': sample_job.get('title'),
                'company': sample_job.get('company'),
                'location': sample_job.get('location'),
                'education': sample_job.get('education'),
                'experience': sample_job.get('experience'),
                'company_scale': sample_job.get('company_scale')
            }
            
            print("   直接映射字段:")
            for field, value in direct_fields.items():
                status = "✅" if value else "⚠️"
                print(f"      {field}: {status} {value or '空值'}")
            
            # LLM处理字段测试
            llm_fields = {
                'salary': sample_job.get('salary'),
                'description': len(sample_job.get('description', '') or ''),
                'requirements': len(sample_job.get('requirements', '') or '')
            }
            
            print("   LLM处理字段:")
            for field, value in llm_fields.items():
                if field in ['description', 'requirements']:
                    status = "✅" if value > 0 else "⚠️"
                    print(f"      {field}: {status} {value} 字符")
                else:
                    status = "✅" if value else "⚠️"
                    print(f"      {field}: {status} {value or '空值'}")
            
            # 测试4: 语义分割测试
            print("\n📝 测试4: 语义分割测试")
            test_text = sample_job.get('description', '')
            if test_text:
                chunks = processor.split_text_semantically(test_text[:500])  # 只测试前500字符
                print(f"   原文长度: {len(test_text)} 字符")
                print(f"   分割块数: {len(chunks)}")
                print(f"   平均块长度: {sum(len(chunk) for chunk in chunks) // len(chunks) if chunks else 0} 字符")
            else:
                print("   ⚠️ 没有描述文本可供分割测试")
            
            print("\n🎉 所有测试完成!")
            return True
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # 运行异步测试
    return asyncio.run(run_tests())

if __name__ == "__main__":
    success = test_optimized_job_processor()
    sys.exit(0 if success else 1)