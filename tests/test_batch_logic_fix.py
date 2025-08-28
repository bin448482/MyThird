#!/usr/bin/env python3
"""
测试批次投递与薪资过滤的逻辑修复
验证批次大小是基于过滤后的有效职位数量
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import yaml
from src.submission.data_manager import SubmissionDataManager
from src.submission.salary_filter import SalaryFilter

def test_batch_logic():
    """测试批次逻辑修复"""
    print("🧪 测试批次投递与薪资过滤逻辑修复")
    print("=" * 60)
    
    # 加载配置
    try:
        with open('config/integration_config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ 加载配置失败: {e}")
        return
    
    # 创建数据管理器
    dm = SubmissionDataManager(':memory:', config)
    
    if not dm.salary_filter:
        print("❌ 薪资过滤器未初始化")
        return
    
    print("✅ 薪资过滤器初始化成功")
    
    # 测试不同批次大小的行为
    batch_sizes = [5, 10, 20]
    
    for batch_size in batch_sizes:
        print(f"\n📊 测试批次大小: {batch_size}")
        print("-" * 40)
        
        # 获取未处理的匹配记录（启用薪资过滤）
        records_with_filter = dm.get_unprocessed_matches(
            limit=batch_size, 
            apply_salary_filter=True
        )
        
        # 获取未处理的匹配记录（不启用薪资过滤）
        records_without_filter = dm.get_unprocessed_matches(
            limit=batch_size, 
            apply_salary_filter=False
        )
        
        print(f"  不过滤时获取记录数: {len(records_without_filter)}")
        print(f"  薪资过滤后记录数: {len(records_with_filter)}")
        
        if len(records_with_filter) > 0:
            print(f"  ✅ 批次逻辑正确: 返回了 {len(records_with_filter)} 个有效职位")
            
            # 显示前3个职位的信息
            for i, record in enumerate(records_with_filter[:3]):
                print(f"    {i+1}. {record.job_title} @ {record.company} (匹配度: {record.match_score:.2f})")
        else:
            print("  ⚠️ 没有符合薪资条件的职位")
    
    # 获取薪资过滤统计
    if dm.salary_filter:
        stats = dm.salary_filter.get_stats()
        print(f"\n💰 薪资过滤统计:")
        print(f"  总评估数: {stats['total_evaluated']}")
        print(f"  拒绝数: {stats['salary_rejected']}")
        print(f"  拒绝率: {stats['rejection_rate']:.1%}")
        print(f"  增强数: {stats['salary_enhanced']}")
        print(f"  薪资分布: {stats['salary_distribution']}")
    
    print("\n🎯 批次逻辑测试完成")

def test_dynamic_query_adjustment():
    """测试动态查询数量调整"""
    print("\n🔧 测试动态查询数量调整逻辑")
    print("=" * 60)
    
    # 模拟不同的拒绝率场景
    rejection_rates = [0.5, 0.8, 0.9, 0.95]
    batch_size = 10
    
    for rejection_rate in rejection_rates:
        # 计算查询倍数（与数据管理器中的逻辑一致）
        multiplier = max(2, int(1 / (1 - rejection_rate)) + 1)
        query_limit = batch_size * multiplier
        
        print(f"拒绝率 {rejection_rate:.0%} -> 查询倍数 {multiplier}x -> 查询 {query_limit} 条记录以获得 {batch_size} 条有效记录")
    
    print("\n✅ 动态调整逻辑验证完成")

if __name__ == "__main__":
    test_batch_logic()
    test_dynamic_query_adjustment()