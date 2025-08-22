#!/usr/bin/env python3
"""
简历处理系统性能监控和质量保证模块
提供性能监控、质量评估和优化建议
"""

import time
import psutil
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    operation: str
    start_time: float
    end_time: float
    duration: float
    memory_usage_mb: float
    cpu_usage_percent: float
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_ms(self) -> float:
        """获取持续时间（毫秒）"""
        return self.duration * 1000


@dataclass
class QualityMetrics:
    """质量指标"""
    extraction_completeness: float  # 提取完整性 0-1
    data_accuracy: float           # 数据准确性 0-1
    format_consistency: float      # 格式一致性 0-1
    validation_score: float        # 验证得分 0-1
    overall_quality: float         # 总体质量 0-1
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.metrics_history: List[PerformanceMetrics] = []
        self.enable_monitoring = self.config.get('enable_monitoring', True)
        self.max_history_size = self.config.get('max_history_size', 1000)
        
        logger.info("性能监控器初始化完成")
    
    @asynccontextmanager
    async def monitor_operation(self, operation: str, metadata: Dict = None):
        """
        监控操作性能的上下文管理器
        
        Args:
            operation: 操作名称
            metadata: 额外的元数据
        """
        if not self.enable_monitoring:
            yield
            return
        
        # 记录开始状态
        start_time = time.time()
        start_memory = self._get_memory_usage()
        start_cpu = self._get_cpu_usage()
        
        success = True
        error_message = None
        
        try:
            yield
        except Exception as e:
            success = False
            error_message = str(e)
            raise
        finally:
            # 记录结束状态
            end_time = time.time()
            end_memory = self._get_memory_usage()
            end_cpu = self._get_cpu_usage()
            
            # 创建性能指标
            metrics = PerformanceMetrics(
                operation=operation,
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                memory_usage_mb=max(end_memory - start_memory, 0),
                cpu_usage_percent=(start_cpu + end_cpu) / 2,
                success=success,
                error_message=error_message,
                metadata=metadata or {}
            )
            
            # 记录指标
            self._record_metrics(metrics)
            
            # 记录日志
            if success:
                logger.info(f"操作完成: {operation}, 耗时: {metrics.duration:.3f}s, 内存: {metrics.memory_usage_mb:.1f}MB")
            else:
                logger.error(f"操作失败: {operation}, 耗时: {metrics.duration:.3f}s, 错误: {error_message}")
    
    def _get_memory_usage(self) -> float:
        """获取当前内存使用量（MB）"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """获取当前CPU使用率"""
        try:
            return psutil.cpu_percent(interval=0.1)
        except Exception:
            return 0.0
    
    def _record_metrics(self, metrics: PerformanceMetrics):
        """记录性能指标"""
        self.metrics_history.append(metrics)
        
        # 限制历史记录大小
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]
    
    def get_performance_summary(self, operation: str = None) -> Dict[str, Any]:
        """
        获取性能摘要
        
        Args:
            operation: 特定操作名称，None表示所有操作
            
        Returns:
            Dict: 性能摘要
        """
        if operation:
            filtered_metrics = [m for m in self.metrics_history if m.operation == operation]
        else:
            filtered_metrics = self.metrics_history
        
        if not filtered_metrics:
            return {'message': '没有性能数据'}
        
        # 计算统计信息
        total_operations = len(filtered_metrics)
        successful_operations = len([m for m in filtered_metrics if m.success])
        failed_operations = total_operations - successful_operations
        
        durations = [m.duration for m in filtered_metrics]
        memory_usages = [m.memory_usage_mb for m in filtered_metrics]
        
        return {
            'operation': operation or 'all',
            'total_operations': total_operations,
            'successful_operations': successful_operations,
            'failed_operations': failed_operations,
            'success_rate': successful_operations / total_operations if total_operations > 0 else 0,
            'duration_stats': {
                'min': min(durations),
                'max': max(durations),
                'avg': sum(durations) / len(durations),
                'total': sum(durations)
            },
            'memory_stats': {
                'min': min(memory_usages),
                'max': max(memory_usages),
                'avg': sum(memory_usages) / len(memory_usages)
            },
            'recent_errors': [
                m.error_message for m in filtered_metrics[-10:] 
                if not m.success and m.error_message
            ]
        }
    
    def get_performance_recommendations(self) -> List[str]:
        """获取性能优化建议"""
        recommendations = []
        
        if not self.metrics_history:
            return ['暂无性能数据，无法提供建议']
        
        # 分析平均处理时间
        avg_duration = sum(m.duration for m in self.metrics_history) / len(self.metrics_history)
        if avg_duration > 30:  # 超过30秒
            recommendations.append('平均处理时间较长，建议优化算法或增加并行处理')
        
        # 分析内存使用
        avg_memory = sum(m.memory_usage_mb for m in self.metrics_history) / len(self.metrics_history)
        if avg_memory > 500:  # 超过500MB
            recommendations.append('内存使用量较高，建议优化数据结构或增加内存清理')
        
        # 分析失败率
        success_rate = len([m for m in self.metrics_history if m.success]) / len(self.metrics_history)
        if success_rate < 0.9:  # 成功率低于90%
            recommendations.append('操作失败率较高，建议增强错误处理和重试机制')
        
        # 分析操作频率
        operation_counts = {}
        for m in self.metrics_history:
            operation_counts[m.operation] = operation_counts.get(m.operation, 0) + 1
        
        most_frequent = max(operation_counts.items(), key=lambda x: x[1])
        if most_frequent[1] > len(self.metrics_history) * 0.5:
            recommendations.append(f'操作 "{most_frequent[0]}" 频率较高，建议考虑缓存优化')
        
        return recommendations or ['系统性能良好，暂无优化建议']


class QualityAssurance:
    """质量保证"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.min_completeness_score = self.config.get('min_completeness_score', 0.7)
        self.min_accuracy_score = self.config.get('min_accuracy_score', 0.8)
        
        logger.info("质量保证模块初始化完成")
    
    def assess_extraction_quality(self, profile, original_content: str) -> QualityMetrics:
        """
        评估提取质量
        
        Args:
            profile: 提取的简历档案
            original_content: 原始简历内容
            
        Returns:
            QualityMetrics: 质量指标
        """
        # 计算各项质量指标
        completeness = self._assess_completeness(profile)
        accuracy = self._assess_accuracy(profile, original_content)
        consistency = self._assess_consistency(profile)
        validation = self._assess_validation(profile)
        
        # 计算总体质量
        overall_quality = (completeness + accuracy + consistency + validation) / 4
        
        # 收集问题和建议
        issues = []
        recommendations = []
        
        if completeness < self.min_completeness_score:
            issues.append(f'提取完整性不足: {completeness:.2f} < {self.min_completeness_score}')
            recommendations.append('建议优化提取算法或增加更多提示信息')
        
        if accuracy < self.min_accuracy_score:
            issues.append(f'数据准确性不足: {accuracy:.2f} < {self.min_accuracy_score}')
            recommendations.append('建议改进LLM提示词或增加数据验证')
        
        if not profile.name:
            issues.append('缺少姓名信息')
            recommendations.append('确保简历中包含明确的姓名信息')
        
        if not profile.skill_categories:
            issues.append('缺少技能信息')
            recommendations.append('确保简历中包含技能描述')
        
        return QualityMetrics(
            extraction_completeness=completeness,
            data_accuracy=accuracy,
            format_consistency=consistency,
            validation_score=validation,
            overall_quality=overall_quality,
            issues=issues,
            recommendations=recommendations
        )
    
    def _assess_completeness(self, profile) -> float:
        """评估提取完整性"""
        total_fields = 10  # 总字段数
        filled_fields = 0
        
        # 检查基本信息
        if profile.name: filled_fields += 1
        if profile.phone: filled_fields += 1
        if profile.email: filled_fields += 1
        if profile.location: filled_fields += 1
        if profile.current_position: filled_fields += 1
        if profile.total_experience_years > 0: filled_fields += 1
        
        # 检查结构化信息
        if profile.skill_categories: filled_fields += 1
        if profile.work_history: filled_fields += 1
        if profile.education: filled_fields += 1
        if profile.projects: filled_fields += 1
        
        return filled_fields / total_fields
    
    def _assess_accuracy(self, profile, original_content: str) -> float:
        """评估数据准确性"""
        accuracy_score = 1.0
        
        # 检查姓名是否在原文中
        if profile.name and profile.name not in original_content:
            accuracy_score -= 0.2
        
        # 检查技能是否在原文中
        for category in profile.skill_categories:
            for skill in category.skills:
                if skill not in original_content:
                    accuracy_score -= 0.1
                    break
        
        # 检查工作经验
        for work in profile.work_history:
            if work.company and work.company not in original_content:
                accuracy_score -= 0.1
                break
        
        return max(0.0, accuracy_score)
    
    def _assess_consistency(self, profile) -> float:
        """评估格式一致性"""
        consistency_score = 1.0
        
        # 检查日期格式一致性
        date_formats = set()
        for work in profile.work_history:
            if work.start_date:
                date_formats.add(len(work.start_date.split('-')))
            if work.end_date:
                date_formats.add(len(work.end_date.split('-')))
        
        if len(date_formats) > 1:
            consistency_score -= 0.2
        
        # 检查技能分类命名一致性
        category_names = [cat.category_name for cat in profile.skill_categories]
        if len(set(category_names)) != len(category_names):
            consistency_score -= 0.2
        
        return max(0.0, consistency_score)
    
    def _assess_validation(self, profile) -> float:
        """评估数据验证"""
        validation_score = 1.0
        
        # 验证邮箱格式
        if profile.email and '@' not in profile.email:
            validation_score -= 0.2
        
        # 验证电话格式
        if profile.phone and not profile.phone.replace('-', '').replace(' ', '').isdigit():
            validation_score -= 0.2
        
        # 验证工作年限合理性
        if profile.total_experience_years > 50:
            validation_score -= 0.2
        
        return max(0.0, validation_score)


class SystemOptimizer:
    """系统优化器"""
    
    def __init__(self, performance_monitor: PerformanceMonitor, 
                 quality_assurance: QualityAssurance):
        self.performance_monitor = performance_monitor
        self.quality_assurance = quality_assurance
        
        logger.info("系统优化器初始化完成")
    
    def generate_optimization_report(self) -> Dict[str, Any]:
        """生成优化报告"""
        # 获取性能摘要
        perf_summary = self.performance_monitor.get_performance_summary()
        perf_recommendations = self.performance_monitor.get_performance_recommendations()
        
        # 生成报告
        report = {
            'timestamp': datetime.now().isoformat(),
            'performance_summary': perf_summary,
            'performance_recommendations': perf_recommendations,
            'system_status': self._assess_system_status(perf_summary),
            'optimization_priorities': self._get_optimization_priorities(perf_summary)
        }
        
        return report
    
    def _assess_system_status(self, perf_summary: Dict) -> str:
        """评估系统状态"""
        if not perf_summary or 'success_rate' not in perf_summary:
            return 'unknown'
        
        success_rate = perf_summary['success_rate']
        avg_duration = perf_summary.get('duration_stats', {}).get('avg', 0)
        
        if success_rate >= 0.95 and avg_duration <= 30:
            return 'excellent'
        elif success_rate >= 0.90 and avg_duration <= 60:
            return 'good'
        elif success_rate >= 0.80 and avg_duration <= 120:
            return 'fair'
        else:
            return 'poor'
    
    def _get_optimization_priorities(self, perf_summary: Dict) -> List[str]:
        """获取优化优先级"""
        priorities = []
        
        if not perf_summary or 'success_rate' not in perf_summary:
            return ['收集更多性能数据']
        
        success_rate = perf_summary['success_rate']
        avg_duration = perf_summary.get('duration_stats', {}).get('avg', 0)
        avg_memory = perf_summary.get('memory_stats', {}).get('avg', 0)
        
        # 按优先级排序
        if success_rate < 0.8:
            priorities.append('高优先级: 提升系统稳定性和错误处理')
        
        if avg_duration > 60:
            priorities.append('高优先级: 优化处理速度')
        
        if avg_memory > 500:
            priorities.append('中优先级: 优化内存使用')
        
        if success_rate < 0.9:
            priorities.append('中优先级: 改进异常处理机制')
        
        if avg_duration > 30:
            priorities.append('低优先级: 进一步优化性能')
        
        return priorities or ['系统运行良好，保持当前状态']


# 全局实例
performance_monitor = PerformanceMonitor()
quality_assurance = QualityAssurance()
system_optimizer = SystemOptimizer(performance_monitor, quality_assurance)


# 便捷函数
def monitor_performance(operation: str, metadata: Dict = None):
    """性能监控装饰器"""
    return performance_monitor.monitor_operation(operation, metadata)


def assess_quality(profile, original_content: str) -> QualityMetrics:
    """评估质量的便捷函数"""
    return quality_assurance.assess_extraction_quality(profile, original_content)


def get_optimization_report() -> Dict[str, Any]:
    """获取优化报告的便捷函数"""
    return system_optimizer.generate_optimization_report()


if __name__ == "__main__":
    # 示例用法
    import asyncio
    
    async def example_usage():
        # 监控操作性能
        async with monitor_performance('test_operation', {'test': True}):
            await asyncio.sleep(1)  # 模拟操作
        
        # 获取性能摘要
        summary = performance_monitor.get_performance_summary()
        print("性能摘要:", summary)
        
        # 获取优化报告
        report = get_optimization_report()
        print("优化报告:", report)
    
    asyncio.run(example_usage())