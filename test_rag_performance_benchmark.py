#!/usr/bin/env python3
"""
RAG系统性能基准测试

测试RAG系统在不同负载下的性能表现，包括处理速度、内存使用、并发能力等
"""

import sys
import asyncio
import time
import psutil
import json
import logging
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from src.rag.rag_system_coordinator import RAGSystemCoordinator
from src.rag.data_pipeline import RAGDataPipeline

class PerformanceBenchmark:
    """性能基准测试器"""
    
    def __init__(self):
        self.benchmark_results = {
            'test_start_time': datetime.now().isoformat(),
            'system_info': self._get_system_info(),
            'benchmarks': []
        }
        
        # 测试配置
        self.config = {
            'rag_system': {
                'database': {
                    'path': './data/jobs.db',
                    'batch_size': 20
                },
                'llm': {
                    'provider': 'zhipu',
                    'model': 'glm-4-flash',
                    'api_key': 'test-key',
                    'temperature': 0.1,
                    'max_tokens': 1500
                },
                'vector_db': {
                    'persist_directory': './data/test_chroma_db_perf',
                    'collection_name': 'perf_test_jobs',
                    'embeddings': {
                        'model_name': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                        'device': 'cpu',
                        'normalize_embeddings': True
                    }
                },
                'documents': {
                    'types': ['overview', 'responsibility', 'requirement', 'skills', 'basic_requirements']
                },
                'processing': {
                    'skip_processed': False,  # 性能测试时不跳过
                    'batch_size': 10
                }
            }
        }
    
    def _get_system_info(self):
        """获取系统信息"""
        return {
            'cpu_count': psutil.cpu_count(),
            'memory_total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
            'python_version': sys.version,
            'platform': sys.platform
        }
    
    def _monitor_resources(self, duration_seconds=60):
        """监控系统资源使用"""
        start_time = time.time()
        measurements = []
        
        while time.time() - start_time < duration_seconds:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            measurements.append({
                'timestamp': time.time() - start_time,
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_gb': round(memory.used / (1024**3), 2)
            })
        
        return {
            'avg_cpu_percent': sum(m['cpu_percent'] for m in measurements) / len(measurements),
            'max_cpu_percent': max(m['cpu_percent'] for m in measurements),
            'avg_memory_percent': sum(m['memory_percent'] for m in measurements) / len(measurements),
            'max_memory_percent': max(m['memory_percent'] for m in measurements),
            'peak_memory_gb': max(m['memory_used_gb'] for m in measurements),
            'measurements': measurements
        }
    
    async def benchmark_system_initialization(self):
        """基准测试：系统初始化性能"""
        print("🚀 基准测试1: 系统初始化性能")
        
        results = []
        
        for i in range(5):  # 测试5次取平均值
            start_time = time.time()
            start_memory = psutil.virtual_memory().used / (1024**3)
            
            try:
                coordinator = RAGSystemCoordinator(self.config)
                init_success = coordinator.initialize_system()
                
                end_time = time.time()
                end_memory = psutil.virtual_memory().used / (1024**3)
                
                if init_success:
                    results.append({
                        'run': i + 1,
                        'init_time_seconds': round(end_time - start_time, 3),
                        'memory_increase_mb': round((end_memory - start_memory) * 1024, 2),
                        'success': True
                    })
                    
                    # 清理资源
                    coordinator.cleanup_system()
                else:
                    results.append({
                        'run': i + 1,
                        'success': False,
                        'error': 'Initialization failed'
                    })
                    
            except Exception as e:
                results.append({
                    'run': i + 1,
                    'success': False,
                    'error': str(e)
                })
        
        # 计算统计信息
        successful_runs = [r for r in results if r.get('success', False)]
        
        if successful_runs:
            avg_init_time = sum(r['init_time_seconds'] for r in successful_runs) / len(successful_runs)
            avg_memory_increase = sum(r['memory_increase_mb'] for r in successful_runs) / len(successful_runs)
            
            benchmark = {
                'test_name': '系统初始化性能',
                'runs': len(results),
                'successful_runs': len(successful_runs),
                'avg_init_time_seconds': round(avg_init_time, 3),
                'avg_memory_increase_mb': round(avg_memory_increase, 2),
                'min_init_time_seconds': min(r['init_time_seconds'] for r in successful_runs),
                'max_init_time_seconds': max(r['init_time_seconds'] for r in successful_runs),
                'detailed_results': results
            }
        else:
            benchmark = {
                'test_name': '系统初始化性能',
                'runs': len(results),
                'successful_runs': 0,
                'error': 'All initialization attempts failed',
                'detailed_results': results
            }
        
        self.benchmark_results['benchmarks'].append(benchmark)
        
        print(f"   平均初始化时间: {benchmark.get('avg_init_time_seconds', 'N/A')} 秒")
        print(f"   平均内存增长: {benchmark.get('avg_memory_increase_mb', 'N/A')} MB")
        print(f"   成功率: {len(successful_runs)}/{len(results)}")
    
    async def benchmark_batch_processing(self):
        """基准测试：批量处理性能"""
        print("\n📊 基准测试2: 批量处理性能")
        
        try:
            coordinator = RAGSystemCoordinator(self.config)
            coordinator.initialize_system()
            
            # 获取测试数据
            jobs = coordinator.db_reader.get_jobs_for_rag_processing(limit=50)
            
            if not jobs:
                print("   ⚠️ 没有可用的测试数据")
                return
            
            # 测试不同批次大小的性能
            batch_sizes = [1, 5, 10, 20]
            batch_results = []
            
            for batch_size in batch_sizes:
                print(f"   测试批次大小: {batch_size}")
                
                start_time = time.time()
                start_memory = psutil.virtual_memory().used / (1024**3)
                
                processed_count = 0
                error_count = 0
                
                # 分批处理
                for i in range(0, min(len(jobs), 20), batch_size):  # 最多处理20个职位
                    batch = jobs[i:i+batch_size]
                    
                    for job in batch:
                        try:
                            # 使用备用处理方法（不调用LLM）
                            job_structure = coordinator.job_processor._fallback_extraction_from_db(job)
                            documents = coordinator.job_processor.create_documents(
                                job_structure,
                                job_id=job.get('job_id'),
                                job_url=job.get('url')
                            )
                            
                            # 添加到向量数据库
                            coordinator.vector_manager.add_job_documents(documents, job.get('job_id'))
                            processed_count += 1
                            
                        except Exception as e:
                            error_count += 1
                
                end_time = time.time()
                end_memory = psutil.virtual_memory().used / (1024**3)
                
                batch_result = {
                    'batch_size': batch_size,
                    'processed_jobs': processed_count,
                    'error_count': error_count,
                    'total_time_seconds': round(end_time - start_time, 3),
                    'jobs_per_second': round(processed_count / (end_time - start_time), 2) if end_time > start_time else 0,
                    'memory_increase_mb': round((end_memory - start_memory) * 1024, 2)
                }
                
                batch_results.append(batch_result)
                
                print(f"     处理速度: {batch_result['jobs_per_second']} 职位/秒")
                print(f"     内存增长: {batch_result['memory_increase_mb']} MB")
            
            benchmark = {
                'test_name': '批量处理性能',
                'total_jobs_available': len(jobs),
                'batch_results': batch_results,
                'optimal_batch_size': max(batch_results, key=lambda x: x['jobs_per_second'])['batch_size']
            }
            
            self.benchmark_results['benchmarks'].append(benchmark)
            
            # 清理资源
            coordinator.cleanup_system()
            
        except Exception as e:
            print(f"   ❌ 批量处理测试失败: {e}")
    
    async def benchmark_vector_search_performance(self):
        """基准测试：向量搜索性能"""
        print("\n🔍 基准测试3: 向量搜索性能")
        
        try:
            coordinator = RAGSystemCoordinator(self.config)
            coordinator.initialize_system()
            
            # 先添加一些测试数据
            jobs = coordinator.db_reader.get_jobs_for_rag_processing(limit=10)
            
            if not jobs:
                print("   ⚠️ 没有可用的测试数据")
                return
            
            # 添加测试文档
            for job in jobs[:5]:  # 只处理前5个
                try:
                    job_structure = coordinator.job_processor._fallback_extraction_from_db(job)
                    documents = coordinator.job_processor.create_documents(
                        job_structure,
                        job_id=job.get('job_id'),
                        job_url=job.get('url')
                    )
                    coordinator.vector_manager.add_job_documents(documents, job.get('job_id'))
                except:
                    continue
            
            # 测试搜索性能
            search_queries = [
                "Python开发工程师",
                "Java后端开发",
                "前端React开发",
                "数据分析师",
                "机器学习工程师"
            ]
            
            search_results = []
            
            for query in search_queries:
                # 测试不同的k值
                for k in [1, 3, 5, 10]:
                    start_time = time.time()
                    
                    try:
                        results = coordinator.vector_manager.search_similar_jobs(query, k=k)
                        
                        end_time = time.time()
                        
                        search_results.append({
                            'query': query,
                            'k': k,
                            'search_time_ms': round((end_time - start_time) * 1000, 2),
                            'results_count': len(results),
                            'success': True
                        })
                        
                    except Exception as e:
                        search_results.append({
                            'query': query,
                            'k': k,
                            'success': False,
                            'error': str(e)
                        })
            
            # 计算统计信息
            successful_searches = [r for r in search_results if r.get('success', False)]
            
            if successful_searches:
                avg_search_time = sum(r['search_time_ms'] for r in successful_searches) / len(successful_searches)
                
                benchmark = {
                    'test_name': '向量搜索性能',
                    'total_searches': len(search_results),
                    'successful_searches': len(successful_searches),
                    'avg_search_time_ms': round(avg_search_time, 2),
                    'min_search_time_ms': min(r['search_time_ms'] for r in successful_searches),
                    'max_search_time_ms': max(r['search_time_ms'] for r in successful_searches),
                    'search_results': search_results
                }
            else:
                benchmark = {
                    'test_name': '向量搜索性能',
                    'total_searches': len(search_results),
                    'successful_searches': 0,
                    'error': 'All searches failed',
                    'search_results': search_results
                }
            
            self.benchmark_results['benchmarks'].append(benchmark)
            
            print(f"   平均搜索时间: {benchmark.get('avg_search_time_ms', 'N/A')} ms")
            print(f"   搜索成功率: {len(successful_searches)}/{len(search_results)}")
            
            # 清理资源
            coordinator.cleanup_system()
            
        except Exception as e:
            print(f"   ❌ 向量搜索测试失败: {e}")
    
    async def benchmark_concurrent_processing(self):
        """基准测试：并发处理性能"""
        print("\n🔄 基准测试4: 并发处理性能")
        
        try:
            coordinator = RAGSystemCoordinator(self.config)
            coordinator.initialize_system()
            
            jobs = coordinator.db_reader.get_jobs_for_rag_processing(limit=20)
            
            if not jobs:
                print("   ⚠️ 没有可用的测试数据")
                return
            
            # 测试不同并发级别
            concurrency_levels = [1, 2, 4, 8]
            concurrent_results = []
            
            for concurrency in concurrency_levels:
                print(f"   测试并发级别: {concurrency}")
                
                start_time = time.time()
                processed_count = 0
                error_count = 0
                
                # 使用线程池进行并发处理
                with ThreadPoolExecutor(max_workers=concurrency) as executor:
                    futures = []
                    
                    for job in jobs[:10]:  # 处理前10个职位
                        future = executor.submit(self._process_single_job, coordinator, job)
                        futures.append(future)
                    
                    # 等待所有任务完成
                    for future in futures:
                        try:
                            result = future.result(timeout=30)  # 30秒超时
                            if result:
                                processed_count += 1
                            else:
                                error_count += 1
                        except Exception:
                            error_count += 1
                
                end_time = time.time()
                
                concurrent_result = {
                    'concurrency_level': concurrency,
                    'processed_jobs': processed_count,
                    'error_count': error_count,
                    'total_time_seconds': round(end_time - start_time, 3),
                    'jobs_per_second': round(processed_count / (end_time - start_time), 2) if end_time > start_time else 0
                }
                
                concurrent_results.append(concurrent_result)
                
                print(f"     处理速度: {concurrent_result['jobs_per_second']} 职位/秒")
                print(f"     成功率: {processed_count}/{processed_count + error_count}")
            
            benchmark = {
                'test_name': '并发处理性能',
                'concurrent_results': concurrent_results,
                'optimal_concurrency': max(concurrent_results, key=lambda x: x['jobs_per_second'])['concurrency_level']
            }
            
            self.benchmark_results['benchmarks'].append(benchmark)
            
            # 清理资源
            coordinator.cleanup_system()
            
        except Exception as e:
            print(f"   ❌ 并发处理测试失败: {e}")
    
    def _process_single_job(self, coordinator, job):
        """处理单个职位（用于并发测试）"""
        try:
            job_structure = coordinator.job_processor._fallback_extraction_from_db(job)
            documents = coordinator.job_processor.create_documents(
                job_structure,
                job_id=job.get('job_id'),
                job_url=job.get('url')
            )
            coordinator.vector_manager.add_job_documents(documents, job.get('job_id'))
            return True
        except Exception:
            return False
    
    async def benchmark_memory_usage(self):
        """基准测试：内存使用情况"""
        print("\n💾 基准测试5: 内存使用情况")
        
        try:
            # 监控资源使用
            resource_monitor = threading.Thread(
                target=lambda: self._monitor_resources(60),
                daemon=True
            )
            
            start_memory = psutil.virtual_memory().used / (1024**3)
            
            coordinator = RAGSystemCoordinator(self.config)
            coordinator.initialize_system()
            
            jobs = coordinator.db_reader.get_jobs_for_rag_processing(limit=30)
            
            memory_checkpoints = []
            
            # 处理不同数量的职位，记录内存使用
            for i, checkpoint in enumerate([5, 10, 15, 20, 25, 30]):
                if checkpoint > len(jobs):
                    break
                
                # 处理到当前检查点
                for job in jobs[i*5:checkpoint]:
                    try:
                        job_structure = coordinator.job_processor._fallback_extraction_from_db(job)
                        documents = coordinator.job_processor.create_documents(
                            job_structure,
                            job_id=job.get('job_id'),
                            job_url=job.get('url')
                        )
                        coordinator.vector_manager.add_job_documents(documents, job.get('job_id'))
                    except:
                        continue
                
                current_memory = psutil.virtual_memory().used / (1024**3)
                
                memory_checkpoints.append({
                    'processed_jobs': checkpoint,
                    'memory_used_gb': round(current_memory, 2),
                    'memory_increase_gb': round(current_memory - start_memory, 2)
                })
                
                print(f"   处理 {checkpoint} 个职位后内存使用: {round(current_memory, 2)} GB")
            
            benchmark = {
                'test_name': '内存使用情况',
                'start_memory_gb': round(start_memory, 2),
                'memory_checkpoints': memory_checkpoints,
                'peak_memory_increase_gb': max(cp['memory_increase_gb'] for cp in memory_checkpoints) if memory_checkpoints else 0
            }
            
            self.benchmark_results['benchmarks'].append(benchmark)
            
            # 清理资源
            coordinator.cleanup_system()
            
        except Exception as e:
            print(f"   ❌ 内存使用测试失败: {e}")
    
    def generate_benchmark_report(self):
        """生成性能基准报告"""
        print("\n" + "="*60)
        print("📊 RAG系统性能基准报告")
        print("="*60)
        
        # 系统信息
        sys_info = self.benchmark_results['system_info']
        print(f"系统信息:")
        print(f"  CPU核心数: {sys_info['cpu_count']}")
        print(f"  总内存: {sys_info['memory_total_gb']} GB")
        print(f"  Python版本: {sys_info['python_version']}")
        print(f"  平台: {sys_info['platform']}")
        
        # 基准测试结果
        print(f"\n基准测试结果:")
        for benchmark in self.benchmark_results['benchmarks']:
            print(f"\n📋 {benchmark['test_name']}")
            
            if benchmark['test_name'] == '系统初始化性能':
                if benchmark.get('avg_init_time_seconds'):
                    print(f"  平均初始化时间: {benchmark['avg_init_time_seconds']} 秒")
                    print(f"  平均内存增长: {benchmark['avg_memory_increase_mb']} MB")
                    print(f"  成功率: {benchmark['successful_runs']}/{benchmark['runs']}")
            
            elif benchmark['test_name'] == '批量处理性能':
                print(f"  最优批次大小: {benchmark.get('optimal_batch_size', 'N/A')}")
                for result in benchmark.get('batch_results', []):
                    print(f"    批次大小 {result['batch_size']}: {result['jobs_per_second']} 职位/秒")
            
            elif benchmark['test_name'] == '向量搜索性能':
                if benchmark.get('avg_search_time_ms'):
                    print(f"  平均搜索时间: {benchmark['avg_search_time_ms']} ms")
                    print(f"  搜索成功率: {benchmark['successful_searches']}/{benchmark['total_searches']}")
            
            elif benchmark['test_name'] == '并发处理性能':
                print(f"  最优并发级别: {benchmark.get('optimal_concurrency', 'N/A')}")
                for result in benchmark.get('concurrent_results', []):
                    print(f"    并发级别 {result['concurrency_level']}: {result['jobs_per_second']} 职位/秒")
            
            elif benchmark['test_name'] == '内存使用情况':
                print(f"  峰值内存增长: {benchmark.get('peak_memory_increase_gb', 'N/A')} GB")
        
        # 保存报告
        report_file = f"./test_reports/rag_performance_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        Path(report_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.benchmark_results, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n💾 性能基准报告已保存到: {report_file}")
    
    async def run_all_benchmarks(self):
        """运行所有性能基准测试"""
        print("🏃‍♂️ 开始RAG系统性能基准测试")
        print("="*60)
        
        try:
            await self.benchmark_system_initialization()
            await self.benchmark_batch_processing()
            await self.benchmark_vector_search_performance()
            await self.benchmark_concurrent_processing()
            await self.benchmark_memory_usage()
            
            self.generate_benchmark_report()
            
            return True
            
        except Exception as e:
            print(f"❌ 性能基准测试异常: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.ERROR,  # 只显示错误日志
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建基准测试器并运行
    benchmark = PerformanceBenchmark()
    success = await benchmark.run_all_benchmarks()
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)