#!/usr/bin/env python3
"""
测试 MasterController 的 run_full_pipeline 方法
测试配置：2页，每页20条，总40个职位
"""

import asyncio
import logging
import yaml
import json
import signal
import sys
from datetime import datetime
from src.integration.master_controller import MasterController, PipelineConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 全局变量用于控制程序终止
shutdown_event = asyncio.Event()

def signal_handler(signum, frame):
    """信号处理器 - 处理 Ctrl+C"""
    print(f"\n🛑 接收到中断信号 ({signum})，正在优雅地停止程序...")
    shutdown_event.set()

async def test_master_controller():
    """测试 MasterController 的完整流水线"""
    
    print("🚀 开始测试 MasterController.run_full_pipeline")
    print("=" * 60)
    
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
    
    # 配置流水线参数
    pipeline_config = PipelineConfig(
        # search_keywords=["AI", "Python", ".net", "Azure", "数据工程师"],    # 5个关键词
        search_keywords=["AI"],  # 修改为AI，与你的配置一致
        search_locations=["上海"],
        max_jobs_per_keyword=40,  # 总40个职位（2页 × 20条/页）
        max_pages=2,              # 测试2页
        resume_profile=resume_profile,
        decision_criteria={
            "min_salary": 15000,
            "preferred_locations": ["上海"]
        },
        submission_config={
            "dry_run": True,  # 测试模式，不实际投递
            "max_submissions": 5
        }
    )
    
    print(f"📊 测试参数:")
    print(f"   关键词: {pipeline_config.search_keywords}")
    print(f"   每个关键词最大职位数: {pipeline_config.max_jobs_per_keyword}")
    print(f"   最大页数: {pipeline_config.max_pages}")
    print(f"   预期每页职位数: ~20条")
    print(f"   预期总职位数: {pipeline_config.max_jobs_per_keyword} (2页 × 20条/页)")
    print()
    
    # 记录开始时间
    start_time = datetime.now()
    print(f"⏰ 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        print("💡 提示: 按 Ctrl+C 可以随时终止程序")
        print()
        
        # 执行完整流水线
        pipeline_task = asyncio.create_task(controller.run_full_pipeline(pipeline_config))
        shutdown_task = asyncio.create_task(shutdown_event.wait())
        
        # 等待流水线完成或收到中断信号
        done, pending = await asyncio.wait(
            [pipeline_task, shutdown_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # 如果是中断信号，取消流水线任务
        if shutdown_event.is_set():
            print("🛑 正在取消流水线任务...")
            pipeline_task.cancel()
            try:
                await pipeline_task
            except asyncio.CancelledError:
                print("✅ 流水线任务已取消")
            
            # 取消其他待处理任务
            for task in pending:
                task.cancel()
            
            print("🔄 程序已优雅地终止")
            return None
        
        # 正常完成，获取结果
        report = pipeline_task.result()
        
        # 记录结束时间
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 60)
        print("🎉 测试完成!")
        print(f"⏰ 结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️ 总执行时间: {execution_time:.2f} 秒")
        
        # 打印执行报告
        print("\n📊 执行报告:")
        print(f"   流水线ID: {report.pipeline_id}")
        print(f"   执行成功: {report.success}")
        if report.error_message:
            print(f"   错误信息: {report.error_message}")
        
        # 职位提取结果
        extraction_result = report.extraction_result
        print(f"\n📋 职位提取结果:")
        print(f"   提取成功: {extraction_result.get('success', False)}")
        print(f"   提取数量: {extraction_result.get('total_extracted', 0)}")
        print(f"   关键词处理数: {extraction_result.get('keywords_processed', 0)}")
        print(f"   提取耗时: {extraction_result.get('extraction_time', 0):.2f} 秒")
        
        # 显示前5个职位详情
        jobs = extraction_result.get('jobs', [])
        if jobs:
            print(f"\n📝 前5个职位详情:")
            for i, job in enumerate(jobs[:5], 1):
                print(f"   职位 {i}:")
                print(f"     标题: {job.get('title', 'N/A')}")
                print(f"     公司: {job.get('company', 'N/A')}")
                print(f"     地点: {job.get('location', 'N/A')}")
                print(f"     薪资: {job.get('salary', 'N/A')}")
                if job.get('description'):
                    desc_preview = job['description'][:100] + "..." if len(job['description']) > 100 else job['description']
                    print(f"     描述: {desc_preview}")
                print()
        
        # 性能分析
        if execution_time > 0:
            jobs_per_second = extraction_result.get('total_extracted', 0) / execution_time
            print(f"📈 性能指标:")
            print(f"   处理速度: {jobs_per_second:.2f} 职位/秒")
            print(f"   平均每职位: {execution_time / max(extraction_result.get('total_extracted', 1), 1):.2f} 秒")
        
        # 生成执行摘要
        summary = controller.generate_execution_summary(report)
        print(f"\n📋 执行摘要:")
        for stage, result in summary['stage_results'].items():
            print(f"   {stage}: 成功={result['success']}")
        
        return report
        
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
    asyncio.run(test_master_controller())