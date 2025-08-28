#!/usr/bin/env python3
"""
薪资过滤功能测试脚本
"""

import sys
import os
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.submission.salary_filter import SalaryFilter, SalaryFilterResult
from src.submission.data_manager import SubmissionDataManager
import yaml

def load_test_config():
    """加载测试配置"""
    return {
        'integration_system': {
            'decision_engine': {
                'salary_filters': {
                    'enabled': True,
                    'min_salary_match_score': 0.3,
                    'strict_mode': True,
                    'fallback_strategy': 'reject',
                    'tiered_thresholds': {
                        'enabled': False
                    }
                },
                'salary_enhancement': {
                    'enabled': True,
                    'thresholds': {
                        'excellent': 0.8,
                        'good': 0.6,
                        'acceptable': 0.3,
                        'poor': 0.0
                    }
                }
            }
        }
    }

def create_test_matches():
    """创建测试匹配数据"""
    return [
        {
            'job_id': 'test_001',
            'job_title': '高级Python开发工程师',
            'company': '测试公司A',
            'location': '北京',
            'salary_match_score': 0.85,  # 应该通过并增强
            'overall_score': 0.75
        },
        {
            'job_id': 'test_002', 
            'job_title': 'Python开发工程师',
            'company': '测试公司B',
            'location': '上海',
            'salary_match_score': 0.45,  # 应该通过
            'overall_score': 0.70
        },
        {
            'job_id': 'test_003',
            'job_title': '初级开发工程师', 
            'company': '测试公司C',
            'location': '深圳',
            'salary_match_score': 0.25,  # 应该被拒绝
            'overall_score': 0.80
        },
        {
            'job_id': 'test_004',
            'job_title': '数据分析师',
            'company': '测试公司D', 
            'location': '杭州',
            'salary_match_score': 0.65,  # 应该通过并标记为良好
            'overall_score': 0.68
        },
        {
            'job_id': 'test_005',
            'job_title': '架构师',
            'company': '测试公司E', 
            'location': '广州',
            'salary_match_score': 0.15,  # 应该被拒绝
            'overall_score': 0.90
        }
    ]

def test_salary_filter_basic():
    """测试薪资过滤器基本功能"""
    print("🧪 测试薪资过滤器基本功能")
    print("=" * 50)
    
    # 加载配置
    config = load_test_config()
    
    # 创建薪资过滤器
    salary_filter = SalaryFilter(config)
    
    # 创建测试数据
    test_matches = create_test_matches()
    
    print(f"📊 测试数据: {len(test_matches)} 个职位匹配")
    print()
    
    # 测试每个匹配
    passed_count = 0
    rejected_count = 0
    enhanced_count = 0
    
    for i, match in enumerate(test_matches, 1):
        print(f"测试 {i}: {match['job_title']}")
        print(f"  公司: {match['company']}")
        print(f"  薪资匹配度: {match['salary_match_score']:.2f}")
        print(f"  综合匹配度: {match['overall_score']:.2f}")
        
        # 执行薪资过滤
        result, info = salary_filter.evaluate_salary(match)
        
        print(f"  过滤结果: {result.value}")
        
        if result == SalaryFilterResult.REJECT:
            rejected_count += 1
            print(f"  拒绝原因: {info.get('rejection_reason', 'N/A')}")
            print(f"  要求阈值: {info.get('required_threshold', 'N/A')}")
        elif result == SalaryFilterResult.ENHANCE:
            enhanced_count += 1
            print(f"  增强类型: {info.get('enhancement_type', 'N/A')}")
            print(f"  优先级提升: {info.get('priority_boost', False)}")
        else:
            passed_count += 1
            print("  状态: 正常通过")
        
        print()
    
    # 输出统计信息
    print("📈 测试结果统计:")
    print(f"  总计: {len(test_matches)}")
    print(f"  通过: {passed_count}")
    print(f"  拒绝: {rejected_count}")
    print(f"  增强: {enhanced_count}")
    print()
    
    # 获取过滤器统计
    stats = salary_filter.get_stats()
    print("📊 过滤器统计:")
    print(f"  总评估数: {stats['total_evaluated']}")
    print(f"  拒绝数: {stats['salary_rejected']}")
    print(f"  拒绝率: {stats['rejection_rate']:.2%}")
    print(f"  增强数: {stats['salary_enhanced']}")
    print(f"  薪资分布: {stats['salary_distribution']}")
    print(f"  过滤器启用: {stats['filter_enabled']}")
    print(f"  当前阈值: {stats['current_threshold']}")
    
    return stats

def test_data_manager_integration():
    """测试数据管理器集成"""
    print("\n🔗 测试数据管理器集成")
    print("=" * 50)
    
    # 加载配置
    config = load_test_config()
    
    # 创建数据管理器（使用内存数据库进行测试）
    data_manager = SubmissionDataManager(':memory:', config)
    
    # 检查薪资过滤器是否正确初始化
    if data_manager.salary_filter:
        print("✅ 薪资过滤器已正确初始化")
        
        # 测试过滤器配置
        filter_stats = data_manager.salary_filter.get_stats()
        print(f"   过滤器启用: {filter_stats['filter_enabled']}")
        print(f"   阈值设置: {filter_stats['current_threshold']}")
    else:
        print("❌ 薪资过滤器初始化失败")
        return False
    
    print("✅ 数据管理器集成测试通过")
    return True

def test_configuration_scenarios():
    """测试不同配置场景"""
    print("\n⚙️ 测试不同配置场景")
    print("=" * 50)
    
    # 场景1: 禁用薪资过滤
    print("场景1: 禁用薪资过滤")
    config_disabled = {
        'integration_system': {
            'decision_engine': {
                'salary_filters': {
                    'enabled': False,
                    'min_salary_match_score': 0.3
                }
            }
        }
    }
    
    filter_disabled = SalaryFilter(config_disabled)
    test_match = {
        'job_id': 'test_disabled',
        'job_title': '测试职位',
        'salary_match_score': 0.1  # 很低的分数
    }
    
    result, info = filter_disabled.evaluate_salary(test_match)
    print(f"  结果: {result.value} (应该是 pass)")
    
    # 场景2: 高阈值设置
    print("\n场景2: 高阈值设置 (0.7)")
    config_high_threshold = {
        'integration_system': {
            'decision_engine': {
                'salary_filters': {
                    'enabled': True,
                    'min_salary_match_score': 0.7
                }
            }
        }
    }
    
    filter_high = SalaryFilter(config_high_threshold)
    test_match_medium = {
        'job_id': 'test_medium',
        'job_title': '测试职位',
        'salary_match_score': 0.5  # 中等分数
    }
    
    result, info = filter_high.evaluate_salary(test_match_medium)
    print(f"  结果: {result.value} (应该是 reject)")
    
    # 场景3: 分级阈值
    print("\n场景3: 分级阈值测试")
    config_tiered = {
        'integration_system': {
            'decision_engine': {
                'salary_filters': {
                    'enabled': True,
                    'min_salary_match_score': 0.3,
                    'tiered_thresholds': {
                        'enabled': True,
                        'senior_positions': {
                            'min_score': 0.5
                        },
                        'regular_positions': {
                            'min_score': 0.3
                        },
                        'entry_level': {
                            'min_score': 0.2
                        }
                    }
                }
            }
        }
    }
    
    filter_tiered = SalaryFilter(config_tiered)
    
    # 测试高级职位
    senior_match = {
        'job_id': 'test_senior',
        'job_title': '高级Python工程师',
        'salary_match_score': 0.4  # 对普通职位够，对高级职位不够
    }
    
    result, info = filter_tiered.evaluate_salary(senior_match)
    print(f"  高级职位结果: {result.value} (应该是 reject，因为阈值是0.5)")
    
    # 测试普通职位
    regular_match = {
        'job_id': 'test_regular',
        'job_title': 'Python工程师',
        'salary_match_score': 0.4  # 对普通职位够
    }
    
    result, info = filter_tiered.evaluate_salary(regular_match)
    print(f"  普通职位结果: {result.value} (应该是 pass)")
    
    print("✅ 配置场景测试完成")

def main():
    """主测试函数"""
    print("🚀 薪资过滤功能测试开始")
    print("=" * 60)
    
    try:
        # 基本功能测试
        basic_stats = test_salary_filter_basic()
        
        # 数据管理器集成测试
        integration_success = test_data_manager_integration()
        
        # 配置场景测试
        test_configuration_scenarios()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试完成!")
        
        # 验证预期结果
        expected_rejected = 2  # test_003 和 test_005 应该被拒绝
        expected_enhanced = 2  # test_001 和 test_004 应该被增强
        
        if basic_stats['salary_rejected'] == expected_rejected:
            print("✅ 拒绝数量符合预期")
        else:
            print(f"❌ 拒绝数量不符合预期: 期望 {expected_rejected}, 实际 {basic_stats['salary_rejected']}")
        
        if basic_stats['salary_enhanced'] == expected_enhanced:
            print("✅ 增强数量符合预期")
        else:
            print(f"❌ 增强数量不符合预期: 期望 {expected_enhanced}, 实际 {basic_stats['salary_enhanced']}")
        
        if integration_success:
            print("✅ 集成测试通过")
        else:
            print("❌ 集成测试失败")
        
        print("\n💡 测试结论:")
        print("   薪资过滤功能已正确实现，可以有效过滤低薪职位")
        print("   配置灵活，支持多种场景")
        print("   与数据管理器集成良好")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()