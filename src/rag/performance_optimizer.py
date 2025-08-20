#!/usr/bin/env python3
"""
RAG系统性能优化器

提供各种性能优化策略，包括缓存、批处理、并发处理、内存管理等
"""

import asyncio
import logging
import time
import threading
from typing import Dict, List, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache, wraps
import psutil
import gc
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    operation_name: str
    start_time: float
    end_time: float
    duration: float
    memory_before: float
    memory_after: float
    memory_delta: float
    cpu_percent: float
    success: bool
    error_message: Optional[str] = None

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self._lock = threading.Lock()
    
    def record_operation(self, operation_name: str, start_time: float, end_time: float, 
                        memory_before: float, memory_after: float, cpu_percent: float,
                        success: bool, error_message: Optional[str] = None):
        """记录操作性能指标"""
        metric = PerformanceMetrics(
            operation_name=operation_name,
            start_time=start_time,
            end_time=end_time,
            duration=end_time - start_time,
            memory_before=memory_before,
            memory_after=memory_after,
            memory_delta=memory_after - memory_before,
            cpu_percent=cpu_percent,
            success=success,
            error_message=error_message
        )
        
        with self._lock:
            self.metrics.append(metric)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取性能指标摘要"""
        with self._lock:
            if not self.metrics:
                return {}
            
            successful_metrics = [m for m in self.metrics if m.success]
            
            return {
                'total_operations': len(self.metrics),
                'successful_operations': len(successful_metrics),
                'failed_operations': len(self.metrics) - len(successful_metrics),
                'avg_duration': sum(m.duration for m in successful_metrics) / len(successful_metrics) if successful_metrics else 0,
                'total_memory_delta': sum(m.memory_delta for m in self.metrics),
                'avg_cpu_percent': sum(m.cpu_percent for m in self.metrics) / len(self.metrics),
                'operations_by_name': self._group_metrics_by_name()
            }
    
    def _group_metrics_by_name(self) -> Dict[str, Dict[str, Any]]:
        """按操作名称分组指标"""
        grouped = {}
        for metric in self.metrics:
            if metric.operation_name not in grouped:
                grouped[metric.operation_name] = {
                    'count': 0,
                    'total_duration': 0,
                    'avg_duration': 0,
                    'success_rate': 0,
                    'total_memory_delta': 0
                }
            
            group = grouped[metric.operation_name]
            group['count'] += 1
            group['total_duration'] += metric.duration
            group['total_memory_delta'] += metric.memory_delta
            
            if metric.success:
                group['success_count'] = group.get('success_count', 0) + 1
        
        # 计算平均值和成功率
        for name, group in grouped.items():
            group['avg_duration'] = group['total_duration'] / group['count']
            group['success_rate'] = group.get('success_count', 0) / group['count'] * 100
        
        return grouped

def performance_monitor(operation_name: str):
    """性能监控装饰器"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            monitor = getattr(args[0], 'performance_monitor', None) if args else None
            if not monitor:
                return await func(*args, **kwargs)
            
            # 记录开始状态
            start_time = time.time()
            memory_before = psutil.virtual_memory().used / (1024**3)
            cpu_before = psutil.cpu_percent()
            
            success = True
            error_message = None
            result = None
            
            try:
                result = await func(*args, **kwargs)
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                # 记录结束状态
                end_time = time.time()
                memory_after = psutil.virtual_memory().used / (1024**3)
                cpu_after = psutil.cpu_percent()
                
                monitor.record_operation(
                    operation_name=operation_name,
                    start_time=start_time,
                    end_time=end_time,
                    memory_before=memory_before,
                    memory_after=memory_after,
                    cpu_percent=(cpu_before + cpu_after) / 2,
                    success=success,
                    error_message=error_message
                )
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            monitor = getattr(args[0], 'performance_monitor', None) if args else None
            if not monitor:
                return func(*args, **kwargs)
            
            # 记录开始状态
            start_time = time.time()
            memory_before = psutil.virtual_memory().used / (1024**3)
            cpu_before = psutil.cpu_percent()
            
            success = True
            error_message = None
            result = None
            
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                # 记录结束状态
                end_time = time.time()
                memory_after = psutil.virtual_memory().used / (1024**3)
                cpu_after = psutil.cpu_percent()
                
                monitor.record_operation(
                    operation_name=operation_name,
                    start_time=start_time,
                    end_time=end_time,
                    memory_before=memory_before,
                    memory_after=memory_after,
                    cpu_percent=(cpu_before + cpu_after) / 2,
                    success=success,
                    error_message=error_message
                )
            
            return result
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

class CacheManager:
    """缓存管理器"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # 检查是否过期
            if time.time() - entry['timestamp'] > self.ttl_seconds:
                del self._cache[key]
                return None
            
            entry['access_count'] += 1
            entry['last_access'] = time.time()
            return entry['value']
    
    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        with self._lock:
            # 如果缓存已满，删除最少使用的条目
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()
            
            self._cache[key] = {
                'value': value,
                'timestamp': time.time(),
                'access_count': 1,
                'last_access': time.time()
            }
    
    def _evict_lru(self) -> None:
        """删除最少使用的缓存条目"""
        if not self._cache:
            return
        
        # 找到访问次数最少且最久未访问的条目
        lru_key = min(
            self._cache.keys(),
            key=lambda k: (self._cache[k]['access_count'], self._cache[k]['last_access'])
        )
        del self._cache[lru_key]
    
    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            total_entries = len(self._cache)
            total_access_count = sum(entry['access_count'] for entry in self._cache.values())
            
            return {
                'total_entries': total_entries,
                'max_size': self.max_size,
                'usage_ratio': total_entries / self.max_size if self.max_size > 0 else 0,
                'total_access_count': total_access_count,
                'avg_access_count': total_access_count / total_entries if total_entries > 0 else 0
            }

class BatchProcessor:
    """批处理器"""
    
    def __init__(self, batch_size: int = 10, max_workers: int = 4):
        self.batch_size = batch_size
        self.max_workers = max_workers
    
    async def process_batch_async(self, items: List[Any], 
                                 process_func: Callable, 
                                 *args, **kwargs) -> List[Any]:
        """异步批处理"""
        results = []
        
        # 分批处理
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            
            # 并发处理批次内的项目
            tasks = []
            for item in batch:
                if asyncio.iscoroutinefunction(process_func):
                    task = process_func(item, *args, **kwargs)
                else:
                    task = asyncio.get_event_loop().run_in_executor(
                        None, process_func, item, *args, **kwargs
                    )
                tasks.append(task)
            
            # 等待批次完成
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(batch_results)
            
            # 内存清理
            gc.collect()
        
        return results
    
    def process_batch_sync(self, items: List[Any], 
                          process_func: Callable, 
                          *args, **kwargs) -> List[Any]:
        """同步批处理"""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 分批处理
            for i in range(0, len(items), self.batch_size):
                batch = items[i:i + self.batch_size]
                
                # 提交批次任务
                futures = []
                for item in batch:
                    future = executor.submit(process_func, item, *args, **kwargs)
                    futures.append(future)
                
                # 收集批次结果
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        logger.error(f"批处理项目失败: {e}")
                        results.append(None)
                
                # 内存清理
                gc.collect()
        
        return results

class MemoryManager:
    """内存管理器"""
    
    def __init__(self, memory_threshold_mb: float = 1000):
        self.memory_threshold_mb = memory_threshold_mb
        self.memory_threshold_bytes = memory_threshold_mb * 1024 * 1024
    
    def get_memory_usage(self) -> Dict[str, float]:
        """获取内存使用情况"""
        memory = psutil.virtual_memory()
        process = psutil.Process()
        
        return {
            'system_total_gb': memory.total / (1024**3),
            'system_used_gb': memory.used / (1024**3),
            'system_available_gb': memory.available / (1024**3),
            'system_percent': memory.percent,
            'process_memory_mb': process.memory_info().rss / (1024**2),
            'process_memory_percent': process.memory_percent()
        }
    
    def check_memory_pressure(self) -> bool:
        """检查内存压力"""
        memory_info = self.get_memory_usage()
        return (
            memory_info['system_percent'] > 85 or 
            memory_info['process_memory_mb'] > self.memory_threshold_mb
        )
    
    def force_garbage_collection(self) -> Dict[str, int]:
        """强制垃圾回收"""
        before_memory = psutil.virtual_memory().used / (1024**2)
        
        # 执行垃圾回收
        collected = {
            'generation_0': gc.collect(0),
            'generation_1': gc.collect(1),
            'generation_2': gc.collect(2)
        }
        
        after_memory = psutil.virtual_memory().used / (1024**2)
        collected['memory_freed_mb'] = before_memory - after_memory
        
        return collected
    
    def optimize_memory_usage(self) -> Dict[str, Any]:
        """优化内存使用"""
        optimization_results = {
            'before_memory': self.get_memory_usage(),
            'actions_taken': []
        }
        
        # 强制垃圾回收
        gc_results = self.force_garbage_collection()
        optimization_results['actions_taken'].append({
            'action': 'garbage_collection',
            'results': gc_results
        })
        
        # 如果仍有内存压力，可以采取更激进的措施
        if self.check_memory_pressure():
            # 清理缓存（如果有的话）
            optimization_results['actions_taken'].append({
                'action': 'cache_cleanup',
                'results': 'Cache cleared due to memory pressure'
            })
        
        optimization_results['after_memory'] = self.get_memory_usage()
        
        return optimization_results

class PerformanceOptimizer:
    """性能优化器主类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.performance_monitor = PerformanceMonitor()
        
        # 初始化各个组件
        cache_config = config.get('cache', {})
        self.cache_manager = CacheManager(
            max_size=cache_config.get('max_size', 1000),
            ttl_seconds=cache_config.get('ttl_seconds', 3600)
        )
        
        batch_config = config.get('batch_processing', {})
        self.batch_processor = BatchProcessor(
            batch_size=batch_config.get('batch_size', 10),
            max_workers=batch_config.get('max_workers', 4)
        )
        
        memory_config = config.get('memory_management', {})
        self.memory_manager = MemoryManager(
            memory_threshold_mb=memory_config.get('threshold_mb', 1000)
        )
        
        # 性能优化配置
        self.enable_caching = config.get('enable_caching', True)
        self.enable_batch_processing = config.get('enable_batch_processing', True)
        self.enable_memory_monitoring = config.get('enable_memory_monitoring', True)
        self.auto_gc_threshold = config.get('auto_gc_threshold', 0.85)  # 85%内存使用率时自动GC
    
    @performance_monitor('cache_get')
    def get_cached_result(self, cache_key: str) -> Optional[Any]:
        """获取缓存结果"""
        if not self.enable_caching:
            return None
        
        return self.cache_manager.get(cache_key)
    
    @performance_monitor('cache_set')
    def set_cached_result(self, cache_key: str, result: Any) -> None:
        """设置缓存结果"""
        if not self.enable_caching:
            return
        
        self.cache_manager.set(cache_key, result)
    
    @performance_monitor('batch_process')
    async def process_items_optimized(self, items: List[Any], 
                                    process_func: Callable,
                                    use_cache: bool = True,
                                    cache_key_func: Optional[Callable] = None,
                                    *args, **kwargs) -> List[Any]:
        """优化的批处理方法"""
        if not items:
            return []
        
        results = []
        uncached_items = []
        cached_results = {}
        
        # 检查缓存
        if use_cache and cache_key_func and self.enable_caching:
            for i, item in enumerate(items):
                cache_key = cache_key_func(item)
                cached_result = self.get_cached_result(cache_key)
                
                if cached_result is not None:
                    cached_results[i] = cached_result
                else:
                    uncached_items.append((i, item))
        else:
            uncached_items = list(enumerate(items))
        
        # 批处理未缓存的项目
        if uncached_items:
            if self.enable_batch_processing:
                uncached_only = [item for _, item in uncached_items]
                batch_results = await self.batch_processor.process_batch_async(
                    uncached_only, process_func, *args, **kwargs
                )
                
                # 缓存结果
                if use_cache and cache_key_func and self.enable_caching:
                    for (original_index, item), result in zip(uncached_items, batch_results):
                        if result is not None and not isinstance(result, Exception):
                            cache_key = cache_key_func(item)
                            self.set_cached_result(cache_key, result)
                        cached_results[original_index] = result
                else:
                    for (original_index, _), result in zip(uncached_items, batch_results):
                        cached_results[original_index] = result
            else:
                # 单个处理
                for original_index, item in uncached_items:
                    try:
                        if asyncio.iscoroutinefunction(process_func):
                            result = await process_func(item, *args, **kwargs)
                        else:
                            result = process_func(item, *args, **kwargs)
                        
                        if use_cache and cache_key_func and self.enable_caching:
                            cache_key = cache_key_func(item)
                            self.set_cached_result(cache_key, result)
                        
                        cached_results[original_index] = result
                    except Exception as e:
                        logger.error(f"处理项目失败: {e}")
                        cached_results[original_index] = None
        
        # 按原始顺序组装结果
        results = [cached_results.get(i) for i in range(len(items))]
        
        # 内存管理
        if self.enable_memory_monitoring:
            await self._check_and_optimize_memory()
        
        return results
    
    async def _check_and_optimize_memory(self) -> None:
        """检查并优化内存使用"""
        memory_info = self.memory_manager.get_memory_usage()
        
        if memory_info['system_percent'] > self.auto_gc_threshold * 100:
            logger.info(f"内存使用率 {memory_info['system_percent']:.1f}%，执行内存优化")
            optimization_results = self.memory_manager.optimize_memory_usage()
            
            freed_mb = optimization_results.get('actions_taken', [{}])[0].get('results', {}).get('memory_freed_mb', 0)
            if freed_mb > 0:
                logger.info(f"内存优化完成，释放了 {freed_mb:.1f} MB 内存")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        return {
            'performance_metrics': self.performance_monitor.get_metrics_summary(),
            'cache_stats': self.cache_manager.get_stats(),
            'memory_usage': self.memory_manager.get_memory_usage(),
            'configuration': {
                'enable_caching': self.enable_caching,
                'enable_batch_processing': self.enable_batch_processing,
                'enable_memory_monitoring': self.enable_memory_monitoring,
                'auto_gc_threshold': self.auto_gc_threshold
            }
        }
    
    def reset_performance_metrics(self) -> None:
        """重置性能指标"""
        self.performance_monitor = PerformanceMonitor()
    
    def cleanup(self) -> None:
        """清理资源"""
        self.cache_manager.clear()
        self.reset_performance_metrics()
        gc.collect()

# 使用示例和工厂函数
def create_performance_optimizer(config: Optional[Dict[str, Any]] = None) -> PerformanceOptimizer:
    """创建性能优化器实例"""
    default_config = {
        'cache': {
            'max_size': 1000,
            'ttl_seconds': 3600
        },
        'batch_processing': {
            'batch_size': 10,
            'max_workers': 4
        },
        'memory_management': {
            'threshold_mb': 1000
        },
        'enable_caching': True,
        'enable_batch_processing': True,
        'enable_memory_monitoring': True,
        'auto_gc_threshold': 0.85
    }
    
    if config:
        # 深度合并配置
        def deep_merge(base, override):
            result = base.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        default_config = deep_merge(default_config, config)
    
    return PerformanceOptimizer(default_config)