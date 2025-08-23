#!/usr/bin/env python3
"""
测试点击改进效果
验证失败job日志记录和多重点击策略
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

def check_failed_jobs_log():
    """检查失败job日志"""
    failed_jobs_file = "logs/failed_jobs.json"
    
    if os.path.exists(failed_jobs_file):
        try:
            with open(failed_jobs_file, 'r', encoding='utf-8') as f:
                failed_jobs = json.load(f)
            
            print(f"\n📋 失败job日志分析 ({failed_jobs_file}):")
            print(f"   总失败数量: {len(failed_jobs)}")
            
            # 按失败原因分组
            failure_reasons = {}
            for job in failed_jobs:
                reason = job.get('reason', '未知原因')
                if reason not in failure_reasons:
                    failure_reasons[reason] = []
                failure_reasons[reason].append(job)
            
            print(f"\n📊 失败原因分析:")
            for reason, jobs in failure_reasons.items():
                print(f"   {reason}: {len(jobs)} 个")
                # 显示前3个失败的job详情
                for i, job in enumerate(jobs[:3]):
                    print(f"     - {job.get('title', 'N/A')} @ {job.get('company', 'N/A')}")
                if len(jobs) > 3:
                    print(f"     ... 还有 {len(jobs) - 3} 个")
            
            return failed_jobs
            
        except Exception as e:
            print(f"❌ 读取失败job日志出错: {e}")
            return []
    else:
        print(f"📋 暂无失败job日志文件: {failed_jobs_file}")
        return []

async def test_click_improvements():
    """测试点击改进效果"""
    
    print("🚀 开始测试点击改进效果")
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
    
    # 配置流水线参数（只测试第一页，减少测试时间）
    pipeline_config = PipelineConfig(
        search_keywords=["Python开发"],
        search_locations=["上海"],
        max_jobs_per_keyword=20,  # 只测试第一页
        max_pages=1,              # 只测试1页
        resume_profile=resume_profile,
        decision_criteria={
            "min_salary": 15000,
            "preferred_locations": ["上海", "北京"]
        },
        submission_config={
            "dry_run": True,
            "max_submissions": 5
        }
    )
    
    print(f"📊 测试参数:")
    print(f"   关键词: {pipeline_config.search_keywords}")
    print(f"   最大职位数: {pipeline_config.max_jobs_per_keyword}")
    print(f"   最大页数: {pipeline_config.max_pages}")
    print()
    
    # 记录开始时间
    start_time = datetime.now()
    print(f"⏰ 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 只执行职位提取阶段
        print("🎯 只执行职位提取阶段以测试点击改进...")
        extraction_result = await controller._execute_job_extraction(pipeline_config)
        
        # 记录结束时间
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 60)
        print("🎉 测试完成!")
        print(f"⏰ 结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️ 总执行时间: {execution_time:.2f} 秒")
        
        # 打印提取结果
        print(f"\n📋 职位提取结果:")
        print(f"   提取成功: {extraction_result.get('success', False)}")
        print(f"   提取数量: {extraction_result.get('total_extracted', 0)}")
        print(f"   提取耗时: {extraction_result.get('extraction_time', 0):.2f} 秒")
        
        # 检查失败job日志
        failed_jobs = check_failed_jobs_log()
        
        # 计算成功率
        total_expected = 20  # 第一页预期20个职位
        actual_extracted = extraction_result.get('total_extracted', 0)
        failed_count = len(failed_jobs)
        success_rate = (actual_extracted / total_expected) * 100 if total_expected > 0 else 0
        
        print(f"\n📈 改进效果分析:")
        print(f"   预期职位数: {total_expected}")
        print(f"   成功提取数: {actual_extracted}")
        print(f"   失败数量: {failed_count}")
        print(f"   成功率: {success_rate:.1f}%")
        
        if success_rate >= 95:
            print("🎉 优秀！成功率达到95%以上")
        elif success_rate >= 90:
            print("✅ 良好！成功率达到90%以上")
        elif success_rate >= 85:
            print("⚠️ 一般，成功率在85%以上，还有改进空间")
        else:
            print("❌ 需要进一步优化，成功率低于85%")
        
        return {
            'success_rate': success_rate,
            'extracted_count': actual_extracted,
            'failed_count': failed_count,
            'execution_time': execution_time
        }
        
    except Exception as e:
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        print(f"\n❌ 测试失败!")
        print(f"⏰ 失败时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️ 执行时间: {execution_time:.2f} 秒")
        print(f"❌ 错误信息: {e}")
        
        # 仍然检查失败job日志
        check_failed_jobs_log()
        
        import traceback
        print(f"\n🔍 详细错误信息:")
        traceback.print_exc()
        
        return None

if __name__ == "__main__":
    # 运行测试
    result = asyncio.run(test_click_improvements())
    
    if result:
        print(f"\n📋 测试总结:")
        print(f"   成功率: {result['success_rate']:.1f}%")
        print(f"   提取数量: {result['extracted_count']}")
        print(f"   失败数量: {result['failed_count']}")
        print(f"   执行时间: {result['execution_time']:.2f} 秒")