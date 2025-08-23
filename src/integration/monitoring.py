"""
监控和报告功能
提供实时监控、性能指标收集和报告生成
"""

import asyncio
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
from pathlib import Path

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"

class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class Metric:
    """指标数据"""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    description: str = ""

@dataclass
class Alert:
    """告警信息"""
    alert_id: str
    metric_name: str
    level: AlertLevel
    message: str
    threshold: float
    current_value: float
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    resolved: bool = False

@dataclass
class PerformanceReport:
    """性能报告"""
    report_id: str
    start_time: datetime
    end_time: datetime
    pipeline_stats: Dict[str, Any]
    system_stats: Dict[str, Any]
    error_stats: Dict[str, Any]
    recommendations: List[str]
    generated_at: datetime

class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.monitoring_config = config.get('monitoring', {})
        
        # 指标存储
        self.metrics = defaultdict(deque)
        self.metric_history_size = self.monitoring_config.get('metric_history_size', 1000)
        
        # 系统指标
        self.system_metrics = {}
        self.collection_interval = self.monitoring_config.get('collection_interval', 10)
        
        # 收集器状态
        self.is_collecting = False
        self.collection_task = None
        
        # 统计信息
        self.stats = {
            'total_metrics_collected': 0,
            'collection_start_time': None,
            'last_collection_time': None,
            'collection_errors': 0
        }
    
    async def start_collection(self):
        """开始指标收集"""
        if self.is_collecting:
            logger.warning("指标收集已经在运行")
            return
        
        self.is_collecting = True
        self.stats['collection_start_time'] = datetime.now()
        
        # 启动收集任务
        self.collection_task = asyncio.create_task(self._collection_loop())
        logger.info("指标收集已启动")
    
    async def stop_collection(self):
        """停止指标收集"""
        if not self.is_collecting:
            return
        
        self.is_collecting = False
        
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
        
        logger.info("指标收集已停止")
    
    def record_metric(self, name: str, value: float, metric_type: MetricType = MetricType.GAUGE,
                     labels: Dict[str, str] = None, description: str = ""):
        """记录指标"""
        metric = Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            timestamp=datetime.now(),
            labels=labels or {},
            description=description
        )
        
        # 添加到历史记录
        self.metrics[name].append(metric)
        
        # 限制历史记录大小
        if len(self.metrics[name]) > self.metric_history_size:
            self.metrics[name].popleft()
        
        self.stats['total_metrics_collected'] += 1
        self.stats['last_collection_time'] = datetime.now()
    
    def increment_counter(self, name: str, value: float = 1, labels: Dict[str, str] = None):
        """增加计数器"""
        self.record_metric(name, value, MetricType.COUNTER, labels)
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """设置仪表盘值"""
        self.record_metric(name, value, MetricType.GAUGE, labels)
    
    def record_timer(self, name: str, duration: float, labels: Dict[str, str] = None):
        """记录计时器"""
        self.record_metric(name, duration, MetricType.TIMER, labels)
    
    def get_metric_history(self, name: str, limit: int = 100) -> List[Metric]:
        """获取指标历史"""
        if name not in self.metrics:
            return []
        
        history = list(self.metrics[name])
        return history[-limit:] if limit > 0 else history
    
    def get_latest_metric(self, name: str) -> Optional[Metric]:
        """获取最新指标"""
        if name not in self.metrics or not self.metrics[name]:
            return None
        
        return self.metrics[name][-1]
    
    def get_metric_summary(self, name: str, time_window: timedelta = None) -> Dict[str, float]:
        """获取指标摘要"""
        if name not in self.metrics:
            return {}
        
        # 过滤时间窗口
        now = datetime.now()
        if time_window:
            cutoff_time = now - time_window
            metrics = [m for m in self.metrics[name] if m.timestamp >= cutoff_time]
        else:
            metrics = list(self.metrics[name])
        
        if not metrics:
            return {}
        
        values = [m.value for m in metrics]
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'latest': values[-1],
            'first': values[0]
        }
    
    async def _collection_loop(self):
        """收集循环"""
        while self.is_collecting:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"指标收集错误: {e}")
                self.stats['collection_errors'] += 1
                await asyncio.sleep(self.collection_interval)
    
    async def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            # 简化的系统指标收集
            import os
            import threading
            
            # 进程数量
            self.set_gauge('system_process_count', len(threading.enumerate()))
            
            # 当前时间戳
            self.set_gauge('system_timestamp', time.time())
            
            # 内存使用（简化版）
            try:
                import psutil
                memory = psutil.virtual_memory()
                self.set_gauge('system_memory_usage', memory.percent / 100)
                cpu_percent = psutil.cpu_percent(interval=0.1)
                self.set_gauge('system_cpu_usage', cpu_percent / 100)
            except ImportError:
                # 如果没有psutil，使用简化指标
                self.set_gauge('system_memory_usage', 0.5)  # 默认值
                self.set_gauge('system_cpu_usage', 0.3)     # 默认值
            
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")


class AlertManager:
    """告警管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.alert_config = config.get('monitoring', {}).get('alert_thresholds', {})
        
        # 告警存储
        self.active_alerts = {}
        self.alert_history = []
        
        # 告警规则
        self.alert_rules = {
            'error_rate': {
                'threshold': self.alert_config.get('error_rate', 0.1),
                'level': AlertLevel.ERROR,
                'message': '错误率过高'
            },
            'processing_speed': {
                'threshold': self.alert_config.get('processing_speed', 100),
                'level': AlertLevel.WARNING,
                'message': '处理速度过慢',
                'comparison': 'less_than'
            },
            'memory_usage': {
                'threshold': self.alert_config.get('memory_usage', 0.8),
                'level': AlertLevel.WARNING,
                'message': '内存使用率过高'
            },
            'cpu_usage': {
                'threshold': self.alert_config.get('cpu_usage', 0.8),
                'level': AlertLevel.WARNING,
                'message': 'CPU使用率过高'
            }
        }
    
    def check_alerts(self, metrics_collector: MetricsCollector):
        """检查告警"""
        for metric_name, rule in self.alert_rules.items():
            latest_metric = metrics_collector.get_latest_metric(metric_name)
            if not latest_metric:
                continue
            
            threshold = rule['threshold']
            comparison = rule.get('comparison', 'greater_than')
            
            # 检查阈值
            should_alert = False
            if comparison == 'greater_than' and latest_metric.value > threshold:
                should_alert = True
            elif comparison == 'less_than' and latest_metric.value < threshold:
                should_alert = True
            
            if should_alert:
                self._trigger_alert(metric_name, rule, latest_metric.value)
            else:
                self._resolve_alert(metric_name)
    
    def _trigger_alert(self, metric_name: str, rule: Dict, current_value: float):
        """触发告警"""
        if metric_name in self.active_alerts:
            return  # 告警已存在
        
        alert_id = f"{metric_name}_{int(time.time())}"
        alert = Alert(
            alert_id=alert_id,
            metric_name=metric_name,
            level=rule['level'],
            message=rule['message'],
            threshold=rule['threshold'],
            current_value=current_value,
            triggered_at=datetime.now()
        )
        
        self.active_alerts[metric_name] = alert
        self.alert_history.append(alert)
        
        logger.warning(f"告警触发: {alert.message} (当前值: {current_value}, 阈值: {alert.threshold})")
    
    def _resolve_alert(self, metric_name: str):
        """解决告警"""
        if metric_name not in self.active_alerts:
            return
        
        alert = self.active_alerts[metric_name]
        alert.resolved = True
        alert.resolved_at = datetime.now()
        
        del self.active_alerts[metric_name]
        
        logger.info(f"告警已解决: {alert.message}")
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """获取告警历史"""
        return self.alert_history[-limit:] if limit > 0 else self.alert_history


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.report_dir = Path("reports")
        self.report_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_performance_report(self, 
                                  metrics_collector: MetricsCollector,
                                  alert_manager: AlertManager,
                                  pipeline_stats: Dict[str, Any] = None,
                                  error_stats: Dict[str, Any] = None) -> PerformanceReport:
        """生成性能报告"""
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)  # 最近1小时
        
        # 收集系统统计
        system_stats = self._collect_system_stats(metrics_collector, start_time, end_time)
        
        # 生成建议
        recommendations = self._generate_recommendations(
            system_stats, pipeline_stats or {}, error_stats or {}
        )
        
        report = PerformanceReport(
            report_id=f"report_{int(time.time())}",
            start_time=start_time,
            end_time=end_time,
            pipeline_stats=pipeline_stats or {},
            system_stats=system_stats,
            error_stats=error_stats or {},
            recommendations=recommendations,
            generated_at=datetime.now()
        )
        
        # 保存报告
        self._save_report(report)
        
        return report
    
    def _collect_system_stats(self, metrics_collector: MetricsCollector, 
                            start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """收集系统统计"""
        time_window = end_time - start_time
        
        stats = {}
        
        # 关键指标
        key_metrics = [
            'system_cpu_usage',
            'system_memory_usage',
            'pipeline_processing_rate',
            'error_rate',
            'success_rate'
        ]
        
        for metric_name in key_metrics:
            summary = metrics_collector.get_metric_summary(metric_name, time_window)
            if summary:
                stats[metric_name] = summary
        
        return stats
    
    def _generate_recommendations(self, system_stats: Dict, 
                                pipeline_stats: Dict, 
                                error_stats: Dict) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 基于系统指标的建议
        cpu_stats = system_stats.get('system_cpu_usage', {})
        if cpu_stats.get('avg', 0) > 0.8:
            recommendations.append("CPU使用率较高，建议优化算法或增加并发限制")
        
        memory_stats = system_stats.get('system_memory_usage', {})
        if memory_stats.get('avg', 0) > 0.8:
            recommendations.append("内存使用率较高，建议优化内存管理或增加缓存清理")
        
        # 基于流水线统计的建议
        if pipeline_stats.get('average_processing_time', 0) > 300:  # 5分钟
            recommendations.append("流水线处理时间较长，建议优化处理逻辑或增加并发")
        
        # 基于错误统计的建议
        if error_stats.get('total_errors', 0) > 10:
            recommendations.append("错误数量较多，建议检查错误日志并优化错误处理")
        
        if not recommendations:
            recommendations.append("系统运行正常，无特殊优化建议")
        
        return recommendations
    
    def _save_report(self, report: PerformanceReport):
        """保存报告"""
        try:
            report_file = self.report_dir / f"{report.report_id}.json"
            
            report_data = {
                'report_id': report.report_id,
                'start_time': report.start_time.isoformat(),
                'end_time': report.end_time.isoformat(),
                'pipeline_stats': report.pipeline_stats,
                'system_stats': report.system_stats,
                'error_stats': report.error_stats,
                'recommendations': report.recommendations,
                'generated_at': report.generated_at.isoformat()
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"性能报告已保存: {report_file}")
            
        except Exception as e:
            logger.error(f"保存报告失败: {e}")


class PipelineMonitor:
    """流水线监控器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metrics_collector = MetricsCollector(config)
        self.alert_manager = AlertManager(config)
        self.report_generator = ReportGenerator(config)
        
        # 监控状态
        self.is_monitoring = False
        self.monitoring_task = None
        
        # 流水线统计
        self.pipeline_stats = {
            'total_pipelines_executed': 0,
            'successful_pipelines': 0,
            'failed_pipelines': 0,
            'average_execution_time': 0,
            'last_execution_time': None
        }
    
    async def start_monitoring(self):
        """开始监控"""
        if self.is_monitoring:
            logger.warning("监控已经在运行")
            return
        
        self.is_monitoring = True
        
        # 启动指标收集
        await self.metrics_collector.start_collection()
        
        # 启动监控任务
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("流水线监控已启动")
    
    async def stop_monitoring(self):
        """停止监控"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        
        # 停止指标收集
        await self.metrics_collector.stop_collection()
        
        # 停止监控任务
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("流水线监控已停止")
    
    def record_pipeline_execution(self, success: bool, execution_time: float):
        """记录流水线执行"""
        self.pipeline_stats['total_pipelines_executed'] += 1
        
        if success:
            self.pipeline_stats['successful_pipelines'] += 1
            self.metrics_collector.increment_counter('pipeline_success')
        else:
            self.pipeline_stats['failed_pipelines'] += 1
            self.metrics_collector.increment_counter('pipeline_failed')
        
        # 更新平均执行时间
        total_time = (self.pipeline_stats['average_execution_time'] * 
                     (self.pipeline_stats['total_pipelines_executed'] - 1) + execution_time)
        self.pipeline_stats['average_execution_time'] = total_time / self.pipeline_stats['total_pipelines_executed']
        self.pipeline_stats['last_execution_time'] = execution_time
        
        # 记录指标
        self.metrics_collector.record_timer('pipeline_execution_time', execution_time)
        
        # 计算成功率
        success_rate = self.pipeline_stats['successful_pipelines'] / self.pipeline_stats['total_pipelines_executed']
        self.metrics_collector.set_gauge('pipeline_success_rate', success_rate)
    
    async def _monitoring_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                # 检查告警
                self.alert_manager.check_alerts(self.metrics_collector)
                
                await asyncio.sleep(30)  # 每30秒检查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                await asyncio.sleep(30)
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """获取监控状态"""
        return {
            'is_monitoring': self.is_monitoring,
            'pipeline_stats': self.pipeline_stats,
            'active_alerts': len(self.alert_manager.get_active_alerts()),
            'metrics_collected': self.metrics_collector.stats['total_metrics_collected']
        }
    
    def generate_report(self) -> PerformanceReport:
        """生成性能报告"""
        return self.report_generator.generate_performance_report(
            self.metrics_collector,
            self.alert_manager,
            self.pipeline_stats,
            {}
        )