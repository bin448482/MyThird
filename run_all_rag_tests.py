#!/usr/bin/env python3
"""
RAG系统测试运行器

统一运行所有RAG系统测试，包括功能测试、性能基准测试和错误场景测试
"""

import sys
import asyncio
import logging
import json
import time
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

# 导入测试模块
from test_rag_system_complete import RAGSystemTester
from test_rag_performance_benchmark import PerformanceBenchmark
from test_rag_error_scenarios import ErrorScenarioTester

class RAGTestRunner:
    """RAG系统测试运行器"""
    
    def __init__(self):
        self.test_results = {
            'test_start_time': datetime.now().isoformat(),
            'test_suite_results': {},
            'overall_summary': {}
        }
        
        # 测试套件配置
        self.test_suites = {
            'functional': {
                'name': '功能测试',
                'description': '测试RAG系统的核心功能',
                'tester_class': RAGSystemTester,
                'enabled': True,
                'timeout_minutes': 15
            },
            'performance': {
                'name': '性能基准测试',
                'description': '测试RAG系统的性能表现',
                'tester_class': PerformanceBenchmark,
                'enabled': True,
                'timeout_minutes': 30
            },
            'error_scenarios': {
                'name': '错误场景测试',
                'description': '测试RAG系统的错误处理能力',
                'tester_class': ErrorScenarioTester,
                'enabled': True,
                'timeout_minutes': 20
            }
        }
    
    async def run_test_suite(self, suite_name: str, suite_config: dict):
        """运行单个测试套件"""
        print(f"\n{'='*80}")
        print(f"🧪 开始运行: {suite_config['name']}")
        print(f"📝 描述: {suite_config['description']}")
        print(f"⏱️ 超时时间: {suite_config['timeout_minutes']} 分钟")
        print(f"{'='*80}")
        
        start_time = time.time()
        
        try:
            # 创建测试器实例
            tester = suite_config['tester_class']()
            
            # 运行测试
            if suite_name == 'functional':
                success = await tester.run_all_tests()
            elif suite_name == 'performance':
                success = await tester.run_all_benchmarks()
            elif suite_name == 'error_scenarios':
                success = await tester.run_all_error_scenarios()
            else:
                success = False
            
            end_time = time.time()
            duration = end_time - start_time
            
            # 记录结果
            result = {
                'suite_name': suite_config['name'],
                'success': success,
                'duration_seconds': round(duration, 2),
                'duration_minutes': round(duration / 60, 2),
                'start_time': datetime.fromtimestamp(start_time).isoformat(),
                'end_time': datetime.fromtimestamp(end_time).isoformat()
            }
            
            # 获取详细测试结果
            if hasattr(tester, 'test_results'):
                result['detailed_results'] = tester.test_results
            elif hasattr(tester, 'benchmark_results'):
                result['detailed_results'] = tester.benchmark_results
            
            self.test_results['test_suite_results'][suite_name] = result
            
            # 显示结果
            status = "✅ 成功" if success else "❌ 失败"
            print(f"\n{status} - {suite_config['name']} 完成")
            print(f"⏱️ 耗时: {result['duration_minutes']:.1f} 分钟")
            
            return success
            
        except asyncio.TimeoutError:
            print(f"⏰ 测试套件 {suite_config['name']} 超时")
            self.test_results['test_suite_results'][suite_name] = {
                'suite_name': suite_config['name'],
                'success': False,
                'error': 'Timeout',
                'duration_seconds': suite_config['timeout_minutes'] * 60
            }
            return False
            
        except Exception as e:
            print(f"❌ 测试套件 {suite_config['name']} 异常: {e}")
            import traceback
            traceback.print_exc()
            
            self.test_results['test_suite_results'][suite_name] = {
                'suite_name': suite_config['name'],
                'success': False,
                'error': str(e),
                'duration_seconds': time.time() - start_time
            }
            return False
    
    def generate_overall_summary(self):
        """生成总体测试摘要"""
        results = self.test_results['test_suite_results']
        
        total_suites = len(results)
        successful_suites = sum(1 for r in results.values() if r.get('success', False))
        failed_suites = total_suites - successful_suites
        
        total_duration = sum(r.get('duration_seconds', 0) for r in results.values())
        
        summary = {
            'total_test_suites': total_suites,
            'successful_suites': successful_suites,
            'failed_suites': failed_suites,
            'success_rate': (successful_suites / total_suites * 100) if total_suites > 0 else 0,
            'total_duration_seconds': round(total_duration, 2),
            'total_duration_minutes': round(total_duration / 60, 2),
            'overall_success': successful_suites == total_suites
        }
        
        # 收集详细统计
        detailed_stats = {}
        
        for suite_name, result in results.items():
            if 'detailed_results' in result:
                detailed = result['detailed_results']
                
                if suite_name == 'functional':
                    detailed_stats['functional_tests'] = {
                        'total_tests': detailed.get('total_tests', 0),
                        'passed_tests': detailed.get('passed_tests', 0),
                        'failed_tests': detailed.get('failed_tests', 0)
                    }
                
                elif suite_name == 'performance':
                    benchmarks = detailed.get('benchmarks', [])
                    detailed_stats['performance_benchmarks'] = {
                        'total_benchmarks': len(benchmarks),
                        'benchmark_names': [b.get('test_name', 'Unknown') for b in benchmarks]
                    }
                
                elif suite_name == 'error_scenarios':
                    detailed_stats['error_scenarios'] = {
                        'total_scenarios': detailed.get('total_scenarios', 0),
                        'passed_scenarios': detailed.get('passed_scenarios', 0),
                        'failed_scenarios': detailed.get('failed_scenarios', 0)
                    }
        
        summary['detailed_statistics'] = detailed_stats
        self.test_results['overall_summary'] = summary
        
        return summary
    
    def print_final_report(self):
        """打印最终测试报告"""
        summary = self.test_results['overall_summary']
        
        print("\n" + "="*80)
        print("📊 RAG系统测试总体报告")
        print("="*80)
        
        # 总体统计
        print(f"🧪 测试套件总数: {summary['total_test_suites']}")
        print(f"✅ 成功套件数: {summary['successful_suites']}")
        print(f"❌ 失败套件数: {summary['failed_suites']}")
        print(f"📈 成功率: {summary['success_rate']:.1f}%")
        print(f"⏱️ 总耗时: {summary['total_duration_minutes']:.1f} 分钟")
        
        # 各套件结果
        print(f"\n📋 各测试套件结果:")
        for suite_name, result in self.test_results['test_suite_results'].items():
            status = "✅" if result.get('success', False) else "❌"
            duration = result.get('duration_minutes', result.get('duration_seconds', 0) / 60)
            print(f"  {status} {result.get('suite_name', suite_name)} - {duration:.1f}分钟")
            
            if 'error' in result:
                print(f"      错误: {result['error']}")
        
        # 详细统计
        detailed = summary.get('detailed_statistics', {})
        if detailed:
            print(f"\n📊 详细统计:")
            
            if 'functional_tests' in detailed:
                func_stats = detailed['functional_tests']
                print(f"  功能测试: {func_stats['passed_tests']}/{func_stats['total_tests']} 通过")
            
            if 'performance_benchmarks' in detailed:
                perf_stats = detailed['performance_benchmarks']
                print(f"  性能基准: {perf_stats['total_benchmarks']} 个基准测试")
            
            if 'error_scenarios' in detailed:
                error_stats = detailed['error_scenarios']
                print(f"  错误场景: {error_stats['passed_scenarios']}/{error_stats['total_scenarios']} 通过")
        
        # 总体结论
        if summary['overall_success']:
            print(f"\n🎉 所有测试套件均通过！RAG系统质量良好。")
        else:
            print(f"\n⚠️ 部分测试套件失败，需要进一步检查和修复。")
        
        # 保存完整报告
        report_file = f"./test_reports/rag_complete_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        Path(report_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n💾 完整测试报告已保存到: {report_file}")
        
        return summary['overall_success']
    
    async def run_all_tests(self, selected_suites=None):
        """运行所有测试套件"""
        print("🚀 开始RAG系统完整测试")
        print(f"📅 测试开始时间: {self.test_results['test_start_time']}")
        
        # 确定要运行的测试套件
        if selected_suites is None:
            selected_suites = [name for name, config in self.test_suites.items() if config['enabled']]
        
        print(f"📋 将运行以下测试套件: {', '.join(selected_suites)}")
        
        overall_success = True
        
        # 依次运行每个测试套件
        for suite_name in selected_suites:
            if suite_name not in self.test_suites:
                print(f"⚠️ 未知的测试套件: {suite_name}")
                continue
            
            suite_config = self.test_suites[suite_name]
            
            try:
                # 使用超时运行测试套件
                success = await asyncio.wait_for(
                    self.run_test_suite(suite_name, suite_config),
                    timeout=suite_config['timeout_minutes'] * 60
                )
                
                if not success:
                    overall_success = False
                    
            except asyncio.TimeoutError:
                print(f"⏰ 测试套件 {suite_config['name']} 超时")
                overall_success = False
            except Exception as e:
                print(f"❌ 运行测试套件 {suite_config['name']} 时发生异常: {e}")
                overall_success = False
        
        # 生成总体摘要
        self.generate_overall_summary()
        
        # 打印最终报告
        final_success = self.print_final_report()
        
        return final_success and overall_success

async def main():
    """主函数"""
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='RAG系统测试运行器')
    parser.add_argument(
        '--suites',
        nargs='+',
        choices=['functional', 'performance', 'error_scenarios'],
        help='指定要运行的测试套件'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='显示详细日志'
    )
    
    args = parser.parse_args()
    
    # 配置日志
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建测试运行器
    runner = RAGTestRunner()
    
    # 运行测试
    success = await runner.run_all_tests(selected_suites=args.suites)
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)