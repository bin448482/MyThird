# 集成配置管理与测试框架

## 📋 统一配置管理系统

### 配置文件结构

```yaml
# config/integration_config.yaml - 主集成配置文件
integration_system:
  # 系统全局配置
  global:
    system_name: "智能简历投递系统"
    version: "2.0.0"
    environment: "production"  # development, testing, production
    debug_mode: false
    log_level: "INFO"
    
  # 主控制器配置
  master_controller:
    max_concurrent_pipelines: 5
    pipeline_timeout: 3600  # seconds
    checkpoint_interval: 100
    error_retry_attempts: 3
    enable_performance_monitoring: true
    enable_error_recovery: true
    
  # 作业调度器配置
  job_scheduler:
    queue_size: 1000
    max_concurrent_jobs: 10
    batch_size: 50
    priority_levels: 3
    task_timeout: 1800
    retry_failed_tasks: true
    
  # 数据传递配置
  data_bridge:
    validation_enabled: true
    transformation_cache_enabled: true
    cache_ttl: 3600
    data_retention_days: 30
    backup_enabled: true
    
  # 智能决策配置
  decision_engine:
    enable_learning: true
    decision_model: "multi_criteria"
    weights:
      match_score: 0.35
      company_reputation: 0.20
      salary_attractiveness: 0.15
      location_preference: 0.10
      career_growth: 0.10
      competition_level: 0.10
    thresholds:
      submission_threshold: 0.70
      high_priority_threshold: 0.85
      low_priority_threshold: 0.55
      
  # 自动投递配置
  auto_submission:
    enabled: true
    max_submissions_per_day: 50
    submission_delay_min: 3
    submission_delay_max: 10
    retry_failed_submissions: true
    blacklist_companies: []
    preferred_companies: []

# 模块集成配置
modules:
  job_extraction:
    enabled: true
    max_pages_per_site: 10
    extraction_timeout: 300
    concurrent_extractions: 3
    supported_sites: ["zhilian", "boss", "qiancheng"]
    
  rag_processing:
    enabled: true
    batch_size: 50
    llm_timeout: 30
    max_retry_attempts: 3
    fallback_mode_enabled: true
    
  resume_matching:
    enabled: true
    matching_threshold: 0.6
    max_matches_per_resume: 20
    enable_semantic_search: true
    cache_matching_results: true

# 性能优化配置
performance:
  caching:
    enabled: true
    cache_type: "redis"  # memory, redis, file
    cache_size: 10000
    ttl_seconds: 3600
    
  concurrency:
    max_workers: 10
    semaphore_limit: 5
    use_thread_pool: true
    
  database:
    connection_pool_size: 20
    query_timeout: 30
    batch_insert_size: 100
    enable_query_cache: true

# 监控配置
monitoring:
  enabled: true
  metrics_collection_interval: 30  # seconds
  real_time_dashboard: true
  alert_thresholds:
    error_rate: 0.1
    processing_speed: 100  # jobs/minute
    memory_usage: 0.8
    cpu_usage: 0.8
    disk_usage: 0.9
  
  logging:
    level: "INFO"
    file_rotation: "daily"
    max_file_size: "100MB"
    retention_days: 30
    structured_logging: true

# 安全配置
security:
  api_rate_limiting: true
  request_timeout: 30
  max_request_size: "10MB"
  enable_cors: false
  allowed_origins: []
  
# 备份和恢复配置
backup:
  enabled: true
  backup_interval: "daily"
  retention_days: 30
  backup_location: "./backups"
  compress_backups: true
```

### 配置管理器实现规范

```python
# src/integration/config_manager.py
class IntegrationConfigManager:
    """集成系统配置管理器"""
    
    def __init__(self, config_path: str = "config/integration_config.yaml"):
        self.config_path = config_path
        self.config = {}
        self.watchers = []
        self.last_modified = None
        
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            # 验证配置
            self._validate_config()
            
            # 应用环境变量覆盖
            self._apply_env_overrides()
            
            # 设置默认值
            self._set_defaults()
            
            self.last_modified = os.path.getmtime(self.config_path)
            logger.info("配置加载成功")
            return self.config
            
        except Exception as e:
            logger.error(f"配置加载失败: {e}")
            raise ConfigurationError(f"Failed to load config: {e}")
    
    def get_module_config(self, module_name: str) -> Dict[str, Any]:
        """获取特定模块的配置"""
        return self.config.get('modules', {}).get(module_name, {})
    
    def get_integration_config(self, component: str) -> Dict[str, Any]:
        """获取集成组件配置"""
        return self.config.get('integration_system', {}).get(component, {})
    
    def watch_config_changes(self, callback):
        """监听配置文件变化"""
        self.watchers.append(callback)
        
    def _validate_config(self):
        """验证配置完整性"""
        required_sections = [
            'integration_system',
            'modules',
            'performance',
            'monitoring'
        ]
        
        for section in required_sections:
            if section not in self.config:
                raise ConfigurationError(f"Missing required config section: {section}")
    
    def _apply_env_overrides(self):
        """应用环境变量覆盖"""
        # 支持通过环境变量覆盖配置
        env_mappings = {
            'INTEGRATION_LOG_LEVEL': 'integration_system.global.log_level',
            'INTEGRATION_DEBUG': 'integration_system.global.debug_mode',
            'MAX_CONCURRENT_JOBS': 'integration_system.job_scheduler.max_concurrent_jobs',
            'SUBMISSION_DAILY_LIMIT': 'auto_submission.max_submissions_per_day'
        }
        
        for env_var, config_path in env_mappings.items():
            if env_var in os.environ:
                self._set_nested_config(config_path, os.environ[env_var])
```

## 🧪 集成测试框架

### 测试架构设计

```python
# tests/integration/test_framework.py
class IntegrationTestFramework:
    """集成测试框架"""
    
    def __init__(self):
        self.test_config = self._load_test_config()
        self.test_data_manager = TestDataManager()
        self.mock_services = MockServiceManager()
        self.performance_monitor = PerformanceMonitor()
        
    async def run_full_integration_test(self):
        """运行完整集成测试"""
        test_results = {
            'test_suite': 'full_integration',
            'start_time': datetime.now(),
            'tests': []
        }
        
        try:
            # 1. 系统初始化测试
            init_result = await self.test_system_initialization()
            test_results['tests'].append(init_result)
            
            # 2. 端到端流程测试
            e2e_result = await self.test_end_to_end_pipeline()
            test_results['tests'].append(e2e_result)
            
            # 3. 错误处理测试
            error_result = await self.test_error_handling()
            test_results['tests'].append(error_result)
            
            # 4. 性能测试
            perf_result = await self.test_performance()
            test_results['tests'].append(perf_result)
            
            # 5. 并发测试
            concurrent_result = await self.test_concurrent_processing()
            test_results['tests'].append(concurrent_result)
            
            test_results['end_time'] = datetime.now()
            test_results['total_duration'] = (test_results['end_time'] - test_results['start_time']).total_seconds()
            test_results['success_rate'] = self._calculate_success_rate(test_results['tests'])
            
            return test_results
            
        except Exception as e:
            logger.error(f"集成测试失败: {e}")
            test_results['error'] = str(e)
            return test_results
```

### 端到端测试用例

```python
class EndToEndTestSuite:
    """端到端测试套件"""
    
    async def test_complete_pipeline_flow(self):
        """测试完整流水线流程"""
        # 准备测试数据
        test_resume = self.test_data_manager.create_test_resume()
        test_config = self.test_data_manager.create_test_pipeline_config()
        
        # 初始化系统
        master_controller = MasterController(self.test_config)
        await master_controller.initialize_system()
        
        # 执行完整流程
        start_time = time.time()
        result = await master_controller.run_full_pipeline(test_resume, test_config)
        execution_time = time.time() - start_time
        
        # 验证结果
        assert result.success == True
        assert result.extraction_result['success'] == True
        assert result.rag_result['success'] == True
        assert result.matching_result['success'] == True
        assert result.submission_result['total_attempts'] > 0
        assert execution_time < 1800  # 30分钟内完成
        
        return {
            'test_name': 'complete_pipeline_flow',
            'success': True,
            'execution_time': execution_time,
            'jobs_processed': result.total_jobs_processed,
            'submissions_made': result.submission_result.get('successful_submissions', 0)
        }
    
    async def test_pipeline_with_failures(self):
        """测试包含失败场景的流水线"""
        # 模拟各种失败场景
        failure_scenarios = [
            'extraction_partial_failure',
            'rag_processing_timeout',
            'matching_low_scores',
            'submission_rate_limit'
        ]
        
        results = []
        for scenario in failure_scenarios:
            result = await self._test_failure_scenario(scenario)
            results.append(result)
        
        return {
            'test_name': 'pipeline_with_failures',
            'scenarios_tested': len(failure_scenarios),
            'results': results,
            'recovery_rate': sum(1 for r in results if r['recovered']) / len(results)
        }
```

### 性能测试规范

```python
class PerformanceTestSuite:
    """性能测试套件"""
    
    async def test_throughput_performance(self):
        """测试吞吐量性能"""
        test_loads = [10, 50, 100, 200, 500]
        results = []
        
        for load in test_loads:
            start_time = time.time()
            
            # 创建测试任务
            tasks = []
            for i in range(load):
                task = self._create_performance_test_task(f"job_{i}")
                tasks.append(task)
            
            # 并发执行
            completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # 计算性能指标
            successful_tasks = len([t for t in completed_tasks if not isinstance(t, Exception)])
            throughput = successful_tasks / execution_time
            
            results.append({
                'load': load,
                'execution_time': execution_time,
                'successful_tasks': successful_tasks,
                'throughput': throughput,
                'error_rate': (load - successful_tasks) / load
            })
        
        return {
            'test_name': 'throughput_performance',
            'results': results,
            'max_throughput': max(r['throughput'] for r in results),
            'optimal_load': self._find_optimal_load(results)
        }
    
    async def test_memory_usage(self):
        """测试内存使用情况"""
        import psutil
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 执行大负载测试
        large_dataset = self.test_data_manager.create_large_test_dataset(1000)
        
        memory_samples = []
        for i in range(0, len(large_dataset), 100):
            batch = large_dataset[i:i+100]
            await self._process_test_batch(batch)
            
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append({
                'processed_items': i + len(batch),
                'memory_usage': current_memory,
                'memory_increase': current_memory - initial_memory
            })
        
        return {
            'test_name': 'memory_usage',
            'initial_memory': initial_memory,
            'peak_memory': max(s['memory_usage'] for s in memory_samples),
            'memory_growth_rate': self._calculate_memory_growth_rate(memory_samples),
            'samples': memory_samples
        }
```

### 错误处理测试

```python
class ErrorHandlingTestSuite:
    """错误处理测试套件"""
    
    async def test_network_failures(self):
        """测试网络故障处理"""
        failure_types = [
            'connection_timeout',
            'dns_resolution_failure',
            'http_500_error',
            'rate_limit_exceeded'
        ]
        
        results = []
        for failure_type in failure_types:
            # 模拟网络故障
            with self.mock_services.simulate_network_failure(failure_type):
                result = await self._test_network_resilience()
                results.append({
                    'failure_type': failure_type,
                    'recovery_successful': result['recovered'],
                    'recovery_time': result['recovery_time'],
                    'data_integrity': result['data_integrity_maintained']
                })
        
        return {
            'test_name': 'network_failures',
            'results': results,
            'overall_resilience': sum(r['recovery_successful'] for r in results) / len(results)
        }
    
    async def test_data_corruption_recovery(self):
        """测试数据损坏恢复"""
        # 创建测试数据
        test_data = self.test_data_manager.create_test_pipeline_data()
        
        # 模拟数据损坏场景
        corruption_scenarios = [
            'partial_database_corruption',
            'vector_db_index_corruption',
            'config_file_corruption',
            'checkpoint_file_corruption'
        ]
        
        recovery_results = []
        for scenario in corruption_scenarios:
            # 备份原始数据
            backup = self._create_data_backup(test_data)
            
            # 模拟损坏
            self._simulate_data_corruption(scenario, test_data)
            
            # 测试恢复
            recovery_start = time.time()
            recovery_success = await self._attempt_data_recovery(scenario)
            recovery_time = time.time() - recovery_start
            
            # 验证数据完整性
            integrity_check = self._verify_data_integrity(test_data, backup)
            
            recovery_results.append({
                'scenario': scenario,
                'recovery_successful': recovery_success,
                'recovery_time': recovery_time,
                'data_integrity_restored': integrity_check
            })
            
            # 恢复原始数据
            self._restore_from_backup(backup)
        
        return {
            'test_name': 'data_corruption_recovery',
            'scenarios_tested': len(corruption_scenarios),
            'results': recovery_results,
            'recovery_success_rate': sum(r['recovery_successful'] for r in recovery_results) / len(recovery_results)
        }
```

### 测试数据管理

```python
class TestDataManager:
    """测试数据管理器"""
    
    def __init__(self):
        self.test_data_dir = Path("tests/data")
        self.test_data_dir.mkdir(exist_ok=True)
    
    def create_test_resume(self) -> GenericResumeProfile:
        """创建测试简历"""
        return GenericResumeProfile(
            name="测试用户",
            phone="13800138000",
            email="test@example.com",
            location="北京",
            total_experience_years=5,
            current_position="高级Python工程师",
            skill_categories=[
                SkillCategory(
                    category_name="编程语言",
                    skills=["Python", "Java", "JavaScript"],
                    proficiency_level="advanced",
                    years_experience=5
                ),
                SkillCategory(
                    category_name="框架技术",
                    skills=["Django", "Flask", "React"],
                    proficiency_level="intermediate",
                    years_experience=3
                )
            ]
        )
    
    def create_test_pipeline_config(self) -> PipelineConfig:
        """创建测试流水线配置"""
        return PipelineConfig(
            search_keywords=["Python工程师", "后端开发"],
            search_locations=["北京", "上海"],
            max_pages=2,
            max_jobs_per_keyword=20,
            rag_batch_size=10,
            matching_threshold=0.5,
            auto_submit_threshold=0.7,
            max_submissions_per_day=5
        )
    
    def create_large_test_dataset(self, size: int) -> List[Dict]:
        """创建大型测试数据集"""
        dataset = []
        for i in range(size):
            job_data = {
                'job_id': f'test_job_{i}',
                'title': f'测试职位_{i}',
                'company': f'测试公司_{i % 100}',
                'location': ['北京', '上海', '深圳', '杭州'][i % 4],
                'description': f'这是测试职位{i}的描述信息...',
                'requirements': f'测试职位{i}的要求...',
                'salary': f'{15 + (i % 20)}-{25 + (i % 20)}K'
            }
            dataset.append(job_data)
        
        return dataset
    
    def save_test_results(self, test_name: str, results: Dict):
        """保存测试结果"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{test_name}_{timestamp}.json"
        filepath = self.test_data_dir / "results" / filename
        
        filepath.parent.mkdir(exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"测试结果已保存: {filepath}")
```

### 测试执行脚本

```python
# tests/run_integration_tests.py
async def main():
    """主测试执行函数"""
    # 初始化测试框架
    test_framework = IntegrationTestFramework()
    
    # 设置测试环境
    await test_framework.setup_test_environment()
    
    try:
        # 运行完整集成测试
        logger.info("开始运行集成测试...")
        results = await test_framework.run_full_integration_test()
        
        # 生成测试报告
        report = TestReportGenerator().generate_html_report(results)
        
        # 保存结果
        test_framework.test_data_manager.save_test_results("integration_test", results)
        
        # 输出摘要
        print("\n" + "="*50)
        print("集成测试完成")
        print("="*50)
        print(f"总测试数: {len(results['tests'])}")
        print(f"成功率: {results['success_rate']:.2%}")
        print(f"总耗时: {results['total_duration']:.2f}秒")
        print(f"报告文件: {report['file_path']}")
        print("="*50)
        
        # 根据测试结果设置退出码
        exit_code = 0 if results['success_rate'] >= 0.9 else 1
        sys.exit(exit_code)
        
    except Exception as e:
        logger.error(f"测试执行失败: {e}")
        sys.exit(1)
    
    finally:
        # 清理测试环境
        await test_framework.cleanup_test_environment()

if __name__ == "__main__":
    asyncio.run(main())
```

### 持续集成配置

```yaml
# .github/workflows/integration_test.yml
name: Integration Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  integration-test:
    runs-on: ubuntu-latest
    
    services:
      redis:
        image: redis:6
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Setup test environment
      run: |
        mkdir -p data/test
        mkdir -p logs/test
        cp config/test_config.yaml config/config.yaml
    
    - name: Run integration tests
      run: |
        python tests/run_integration_tests.py
      env:
        INTEGRATION_ENV: testing
        REDIS_URL: redis://localhost:6379
    
    - name: Upload test results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: integration-test-results
        path: tests/data/results/
    
    - name: Upload test reports
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: integration-test-reports
        path: tests/reports/
```

## 📊 测试报告模板

### HTML测试报告

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>集成测试报告</title>
    <style>
        body { font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .summary { background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 30px; }
        .test-result { border: 1px solid #ddd; margin-bottom: 20px; padding: 15px; border-radius: 5px; }
        .success { border-left: 5px solid #28a745; }
        .failure { border-left: 5px solid #dc3545; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .metric { background: white; padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <div class="header">
        <h1>智能简历投递系统 - 集成测试报告</h1>
        <p>生成时间: {{timestamp}}</p>
    </div>
    
    <div class="summary">
        <h2>测试摘要</h2>
        <div class="metrics">
            <div class="metric">
                <h3>总测试数</h3>
                <p>{{total_tests}}</p>
            </div>
            <div class="metric">
                <h3>成功率</h3>
                <p>{{success_rate}}%</p>
            </div>
            <div class="metric">
                <h3>总耗时</h3>
                <p>{{total_duration}}秒</p>
            </div>
            <div class="metric">
                <h3>平均响应时间</h3>
                <p>{{avg_response_time}}ms</p>
            </div>
        </div>
    </div>
    
    <div class="test-results">
        <h2>详细测试结果</h2>
        {{#each test_results}}
        <div class="test-result {{#if success}}success{{else}}failure{{/if}}">
            <h3>{{test_name}}</h3>
            <p><strong>状态:</strong> {{#if success}}通过{{else}}失败{{/if}}</p>
            <p><strong>执行时间:</strong> {{execution_time}}秒</p>
            {{#if error}}
            <p><strong>错误信息:</strong> {{error}}</p>
            {{/if}}
            <p><strong>详细信息:</strong> {{details}}</p>
        </div>
        {{/each}}
    </div>
</body>
</html>
```

这个配置管理和测试框架提供了完整的集成测试解决方案，确保系统的可靠性和性能。