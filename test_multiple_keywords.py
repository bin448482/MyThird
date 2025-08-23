#!/usr/bin/env python3
"""
测试多关键词顺序执行
验证同步方法和关键词顺序处理
"""

import asyncio
import logging
import yaml
import json
import os
from datetime import datetime
from src.integration.master_controller import MasterController, PipelineConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_multiple_keywords_sync():
    """测试多关键词同步顺序执行"""
    
    print("🚀 开始测试多关键词同步顺序执行")
    print("=" * 60)
    
    # 清理之前的失败日志
    failed_jobs_file = "logs/failed_jobs.json"
    if os.path.exists(failed_jobs_file):
        os.remove(failed_jobs_file)
        print("🧹 已清理之前的失败job日志")
    
    # 加载配置
    try:
        with open('config/integration_config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print("✅ 配置文件加载成功")
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        return
    
    # 创建 MasterController 实例
    try:
        controller = MasterController(config)
        print("✅ MasterController 实例创建成功")
    except Exception as e:
        print(f"❌ MasterController 创建失败: {e}")
        return
    
    # 加载简历配置
    try:
        with open('testdata/resume.json', 'r', encoding='utf-8') as f:
            resume_profile = json.load(f)
        print("✅ 简历配置加载成功")
    except Exception as e:
        print(f"❌ 简历配置加载失败: {e}")
        return
    
    # 配置多关键词测试参数
    keywords = ["Python", "Java", "前端"]  # 3个不同的关键词
    pipeline_config = PipelineConfig(
        search_keywords=keywords,
        search_locations=["上海"],
        max_jobs_per_keyword=10,  # 每个关键词10个职位
        max_pages=1,              # 每个关键词1页
        resume_profile=resume_profile,
        decision_criteria={
            "min_salary": 10000,
            "preferred_locations": ["上海", "北京"]
        },
        submission_config={
            "dry_run": True,
            "max_submissions": 3
        }
    )
    
    print(f"📊 测试参数:")
    print(f"   关键词: {pipeline_config.search_keywords}")
    print(f"   每个关键词最大职位数: {pipeline_config.max_jobs_per_keyword}")
    print(f"   每个关键词最大页数: {pipeline_config.max_pages}")
    print(f"   预期总职位数: {len(keywords) * pipeline_config.max_jobs_per_keyword}")
    print()
    
    # 记录开始时间
    start_time = datetime.now()
    print(f"⏰ 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 只执行职位提取阶段（使用新的同步方法）
        print("🎯 执行多关键词同步职位提取...")
        extraction_result = controller._execute_job_extraction_sync(pipeline_config)
        
        # 记录结束时间
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 60)
        print("🎉 测试完成!")
        print(f"⏰ 结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️ 总执行时间: {execution_time:.2f} 秒")
        
        # 打印提取结果
        print(f"\n📋 多关键词提取结果:")
        print(f"   提取成功: {extraction_result.get('success', False)}")
        print(f"   总提取数量: {extraction_result.get('total_extracted', 0)}")
        print(f"   关键词处理数: {extraction_result.get('keywords_processed', 0)}")
        print(f"   提取耗时: {extraction_result.get('extraction_time', 0):.2f} 秒")
        
        # 按关键词分析结果
        jobs = extraction_result.get('jobs', [])
        if jobs:
            print(f"\n📊 按关键词分析:")
            keyword_stats = {}
            for job in jobs:
                keyword = job.get('search_keyword', 'unknown')
                if keyword not in keyword_stats:
                    keyword_stats[keyword] = []
                keyword_stats[keyword].append(job)
            
            for keyword, keyword_jobs in keyword_stats.items():
                print(f"   {keyword}: {len(keyword_jobs)} 个职位")
                # 显示前3个职位
                for i, job in enumerate(keyword_jobs[:3]):
                    print(f"     - {job.get('title', 'N/A')} @ {job.get('company', 'N/A')}")
                if len(keyword_jobs) > 3:
                    print(f"     ... 还有 {len(keyword_jobs) - 3} 个")
        
        # 检查失败job日志
        failed_jobs = []
        if os.path.exists(failed_jobs_file):
            try:
                with open(failed_jobs_file, 'r', encoding='utf-8') as f:
                    failed_jobs = json.load(f)
            except:
                pass
        
        # 计算成功率
        total_expected = len(keywords) * pipeline_config.max_jobs_per_keyword
        actual_extracted = extraction_result.get('total_extracted', 0)
        failed_count = len(failed_jobs)
        success_rate = (actual_extracted / total_expected) * 100 if total_expected > 0 else 0
        
        print(f"\n📈 多关键词执行效果分析:")
        print(f"   预期总职位数: {total_expected}")
        print(f"   成功提取数: {actual_extracted}")
        print(f"   失败数量: {failed_count}")
        print(f"   整体成功率: {success_rate:.1f}%")
        print(f"   平均每关键词: {actual_extracted / len(keywords):.1f} 个职位")
        print(f"   平均每关键词耗时: {extraction_result.get('extraction_time', 0) / len(keywords):.1f} 秒")
        
        # 分析失败原因
        if failed_jobs:
            print(f"\n⚠️ 失败job分析:")
            failure_reasons = {}
            for job in failed_jobs:
                reason = job.get('reason', '未知原因')
                keyword = job.get('extraction_session', 'unknown')
                if reason not in failure_reasons:
                    failure_reasons[reason] = {}
                if keyword not in failure_reasons[reason]:
                    failure_reasons[reason][keyword] = 0
                failure_reasons[reason][keyword] += 1
            
            for reason, keyword_counts in failure_reasons.items():
                print(f"   {reason}:")
                for keyword, count in keyword_counts.items():
                    print(f"     - {keyword}: {count} 个")
        
        return {
            'success_rate': success_rate,
            'extracted_count': actual_extracted,
            'failed_count': failed_count,
            'execution_time': execution_time,
            'keywords_processed': len(keywords),
            'keyword_stats': keyword_stats if jobs else {}
        }
        
    except Exception as e:
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        print(f"\n❌ 测试失败!")
        print(f"⏰ 失败时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️ 执行时间: {execution_time:.2f} 秒")
        print(f"❌ 错误信息: {e}")
        
        import traceback
        print(f"\n🔍 详细错误信息:")
        traceback.print_exc()
        
        return None

if __name__ == "__main__":
    # 运行测试
    result = asyncio.run(test_multiple_keywords_sync())
    
    if result:
        print(f"\n📋 多关键词测试总结:")
        print(f"   整体成功率: {result['success_rate']:.1f}%")
        print(f"   总提取数量: {result['extracted_count']}")
        print(f"   失败数量: {result['failed_count']}")
        print(f"   执行时间: {result['execution_time']:.2f} 秒")
        print(f"   关键词处理数: {result['keywords_processed']}")
        
        if result['success_rate'] >= 90:
            print("🎉 优秀！多关键词同步执行效果良好")
        elif result['success_rate'] >= 80:
            print("✅ 良好！多关键词同步执行基本满足要求")
        else:
            print("⚠️ 需要进一步优化多关键词处理逻辑")