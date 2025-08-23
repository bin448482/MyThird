#!/usr/bin/env python3
"""
智能简历投递系统 - 端到端集成验证脚本
验证系统的完整功能和集成效果
"""

import asyncio
import logging
import json
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from src.integration_main import IntegratedResumeSystem

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IntegrationVerifier:
    """集成验证器"""
    
    def __init__(self):
        self.test_results = []
        self.system = None
    
    async def run_verification(self):
        """运行完整验证"""
        print("=" * 60)
        print("智能简历投递系统 - 端到端集成验证")
        print("=" * 60)
        
        try:
            # 1. 系统初始化验证
            await self._verify_system_initialization()
            
            # 2. 配置加载验证
            await self._verify_configuration_loading()
            
            # 3. 组件集成验证
            await self._verify_component_integration()
            
            # 4. 健康检查验证
            await self._verify_health_check()
            
            # 5. 流水线执行验证（模拟模式）
            await self._verify_pipeline_execution()
            
            # 6. 监控功能验证
            await self._verify_monitoring_functionality()
            
            # 7. 错误处理验证
            await self._verify_error_handling()
            
            # 8. 生成验证报告
            self._generate_verification_report()
            
        except Exception as e:
            logger.error(f"验证过程中发生错误: {e}")
            self._add_test_result("整体验证", False, f"验证失败: {e}")
        
        finally:
            if self.system:
                await self.system.stop_system()
    
    async def _verify_system_initialization(self):
        """验证系统初始化"""
        print("\n1. 验证系统初始化...")
        
        try:
            # 创建系统实例
            self.system = IntegratedResumeSystem()
            
            # 检查基本属性
            assert hasattr(self.system, 'master_controller'), "缺少主控制器"
            assert hasattr(self.system, 'monitor'), "缺少监控器"
            assert hasattr(self.system, 'error_handler'), "缺少错误处理器"
            
            self._add_test_result("系统初始化", True, "所有核心组件初始化成功")
            print("✓ 系统初始化成功")
            
        except Exception as e:
            self._add_test_result("系统初始化", False, str(e))
            print(f"✗ 系统初始化失败: {e}")
            raise
    
    async def _verify_configuration_loading(self):
        """验证配置加载"""
        print("\n2. 验证配置加载...")
        
        try:
            config = self.system.config
            
            # 检查关键配置项
            assert 'integration_system' in config, "缺少集成系统配置"
            assert 'monitoring' in config, "缺少监控配置"
            assert 'error_handling' in config, "缺少错误处理配置"
            
            # 检查具体配置
            integration_config = config['integration_system']
            assert 'master_controller' in integration_config, "缺少主控制器配置"
            assert 'auto_submission' in integration_config, "缺少自动投递配置"
            
            self._add_test_result("配置加载", True, "所有必要配置项加载成功")
            print("✓ 配置加载成功")
            
        except Exception as e:
            self._add_test_result("配置加载", False, str(e))
            print(f"✗ 配置加载失败: {e}")
    
    async def _verify_component_integration(self):
        """验证组件集成"""
        print("\n3. 验证组件集成...")
        
        try:
            # 检查主控制器组件
            mc = self.system.master_controller
            assert hasattr(mc, 'job_extractor'), "主控制器缺少职位提取器"
            assert hasattr(mc, 'rag_coordinator'), "主控制器缺少RAG协调器"
            assert hasattr(mc, 'resume_matcher'), "主控制器缺少简历匹配器"
            assert hasattr(mc, 'decision_engine'), "主控制器缺少决策引擎"
            assert hasattr(mc, 'auto_submitter'), "主控制器缺少自动投递器"
            assert hasattr(mc, 'data_bridge'), "主控制器缺少数据桥接器"
            
            # 检查监控器组件
            monitor = self.system.monitor
            assert hasattr(monitor, 'metrics_collector'), "监控器缺少指标收集器"
            assert hasattr(monitor, 'alert_manager'), "监控器缺少告警管理器"
            assert hasattr(monitor, 'report_generator'), "监控器缺少报告生成器"
            
            self._add_test_result("组件集成", True, "所有组件集成正确")
            print("✓ 组件集成验证成功")
            
        except Exception as e:
            self._add_test_result("组件集成", False, str(e))
            print(f"✗ 组件集成验证失败: {e}")
    
    async def _verify_health_check(self):
        """验证健康检查"""
        print("\n4. 验证健康检查...")
        
        try:
            health_status = await self.system.run_health_check()
            
            # 检查健康检查结果
            assert 'overall_health' in health_status, "缺少整体健康状态"
            assert 'components' in health_status, "缺少组件健康状态"
            assert 'timestamp' in health_status, "缺少时间戳"
            
            # 检查组件状态
            components = health_status['components']
            assert 'config' in components, "缺少配置组件状态"
            assert 'error_handler' in components, "缺少错误处理器状态"
            
            overall_health = health_status['overall_health']
            
            self._add_test_result("健康检查", True, f"健康状态: {overall_health}")
            print(f"✓ 健康检查成功，状态: {overall_health}")
            
        except Exception as e:
            self._add_test_result("健康检查", False, str(e))
            print(f"✗ 健康检查失败: {e}")
    
    async def _verify_pipeline_execution(self):
        """验证流水线执行"""
        print("\n5. 验证流水线执行（模拟模式）...")
        
        try:
            # 准备测试数据
            test_resume = {
                'name': '测试用户',
                'skills': ['Python', '机器学习', '数据分析'],
                'experience': '3年',
                'education': '本科',
                'location_preference': ['北京', '上海'],
                'salary_expectation': 25000
            }
            
            test_keywords = ['Python开发', '数据分析师']
            
            # 配置为干运行模式
            submission_config = {
                'dry_run_mode': True,
                'max_submissions_per_day': 5
            }
            
            # 执行流水线
            result = await self.system.run_pipeline(
                search_keywords=test_keywords,
                resume_profile=test_resume,
                search_locations=['北京'],
                max_jobs_per_keyword=5,
                max_pages=1,
                submission_config=submission_config
            )
            
            # 验证结果
            assert 'pipeline_result' in result, "缺少流水线结果"
            assert 'execution_time' in result, "缺少执行时间"
            
            execution_time = result['execution_time']
            pipeline_result = result.get('pipeline_result')
            
            if pipeline_result:
                success_msg = f"流水线执行成功，耗时: {execution_time:.2f}秒"
                self._add_test_result("流水线执行", True, success_msg)
                print(f"✓ {success_msg}")
            else:
                error_msg = result.get('error', '未知错误')
                self._add_test_result("流水线执行", False, f"执行失败: {error_msg}")
                print(f"✗ 流水线执行失败: {error_msg}")
            
        except Exception as e:
            self._add_test_result("流水线执行", False, str(e))
            print(f"✗ 流水线执行验证失败: {e}")
    
    async def _verify_monitoring_functionality(self):
        """验证监控功能"""
        print("\n6. 验证监控功能...")
        
        try:
            # 启动监控
            await self.system.monitor.start_monitoring()
            
            # 等待一段时间让监控收集数据
            await asyncio.sleep(2)
            
            # 检查监控状态
            monitoring_status = self.system.monitor.get_monitoring_status()
            
            assert 'is_monitoring' in monitoring_status, "缺少监控状态"
            assert 'pipeline_stats' in monitoring_status, "缺少流水线统计"
            assert monitoring_status['is_monitoring'], "监控未启动"
            
            # 生成报告
            report = self.system.monitor.generate_report()
            assert hasattr(report, 'report_id'), "报告缺少ID"
            assert hasattr(report, 'generated_at'), "报告缺少生成时间"
            
            self._add_test_result("监控功能", True, "监控功能正常运行")
            print("✓ 监控功能验证成功")
            
        except Exception as e:
            self._add_test_result("监控功能", False, str(e))
            print(f"✗ 监控功能验证失败: {e}")
    
    async def _verify_error_handling(self):
        """验证错误处理"""
        print("\n7. 验证错误处理...")
        
        try:
            # 创建测试错误
            test_error = ValueError("测试错误处理")
            test_context = {'component': 'verification', 'test': True}
            
            # 处理错误
            recovery_result = await self.system.error_handler.handle_error(test_error, test_context)
            
            # 验证恢复结果
            assert hasattr(recovery_result, 'success'), "恢复结果缺少成功标志"
            assert hasattr(recovery_result, 'strategy_used'), "恢复结果缺少策略信息"
            assert hasattr(recovery_result, 'message'), "恢复结果缺少消息"
            
            # 检查错误统计
            error_stats = self.system.error_handler.get_error_stats()
            assert 'total_errors' in error_stats, "错误统计缺少总数"
            assert error_stats['total_errors'] > 0, "错误统计未更新"
            
            self._add_test_result("错误处理", True, "错误处理机制正常工作")
            print("✓ 错误处理验证成功")
            
        except Exception as e:
            self._add_test_result("错误处理", False, str(e))
            print(f"✗ 错误处理验证失败: {e}")
    
    def _add_test_result(self, test_name: str, success: bool, message: str):
        """添加测试结果"""
        self.test_results.append({
            'test_name': test_name,
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
    
    def _generate_verification_report(self):
        """生成验证报告"""
        print("\n" + "=" * 60)
        print("验证报告")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"总测试数: {total_tests}")
        print(f"通过测试: {passed_tests}")
        print(f"失败测试: {failed_tests}")
        print(f"成功率: {passed_tests/total_tests*100:.1f}%")
        
        print("\n详细结果:")
        for result in self.test_results:
            status = "✓" if result['success'] else "✗"
            print(f"{status} {result['test_name']}: {result['message']}")
        
        # 保存报告到文件
        report_file = Path("verification_report.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': failed_tests,
                    'success_rate': passed_tests/total_tests*100
                },
                'results': self.test_results,
                'generated_at': datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n验证报告已保存到: {report_file}")
        
        # 总结
        if failed_tests == 0:
            print("\n🎉 所有验证测试通过！系统集成成功！")
        else:
            print(f"\n⚠️  有 {failed_tests} 个测试失败，请检查相关问题。")


async def main():
    """主函数"""
    verifier = IntegrationVerifier()
    await verifier.run_verification()


if __name__ == '__main__':
    asyncio.run(main())