# RAG系统测试文档

## 概述

本文档描述了RAG（Retrieval Augmented Generation）系统的完整测试套件，包括功能测试、性能基准测试和错误场景测试。

## 测试架构

### 测试组件结构
```
tests/
├── test_rag_system_complete.py      # 完整功能测试
├── test_rag_performance_benchmark.py # 性能基准测试
├── test_rag_error_scenarios.py      # 错误场景测试
├── run_all_rag_tests.py            # 测试运行器
└── config/
    └── test_config.yaml             # 测试配置文件
```

### 测试覆盖范围

#### 1. 功能测试 (test_rag_system_complete.py)
- **系统初始化测试**: 验证RAG系统各组件正确初始化
- **数据库操作测试**: 测试数据读取、统计查询、质量报告
- **职位处理测试**: 验证职位数据结构化处理和文档创建
- **向量操作测试**: 测试文档向量化、存储和相似性搜索
- **简历优化测试**: 验证简历分析和优化功能
- **数据流水线测试**: 测试完整的ETL流水线
- **集成工作流测试**: 端到端工作流验证

#### 2. 性能基准测试 (test_rag_performance_benchmark.py)
- **系统初始化性能**: 测量初始化时间和内存使用
- **批量处理性能**: 不同批次大小的处理速度对比
- **向量搜索性能**: 搜索响应时间和准确性
- **并发处理性能**: 多线程处理能力测试
- **内存使用基准**: 内存消耗模式分析

#### 3. 错误场景测试 (test_rag_error_scenarios.py)
- **数据库连接错误**: 文件不存在、权限错误、结构不匹配
- **LLM API错误**: API密钥无效、网络超时、响应格式错误
- **向量数据库错误**: 权限问题、磁盘空间不足、搜索失败
- **数据验证错误**: 空数据、恶意数据、编码错误
- **资源耗尽场景**: 内存不足、文件句柄耗尽

## 快速开始

### 环境准备

1. **安装依赖**:
```bash
pip install -r requirements.txt
```

2. **准备测试数据**:
```bash
# 确保数据库文件存在
ls -la ./data/jobs.db

# 创建测试报告目录
mkdir -p ./test_reports
```

3. **配置测试环境**:
```bash
# 复制并修改测试配置
cp config/test_config.yaml config/test_config_local.yaml
# 根据需要修改API密钥等配置
```

### 运行测试

#### 运行所有测试
```bash
python run_all_rag_tests.py
```

#### 运行特定测试套件
```bash
# 只运行功能测试
python run_all_rag_tests.py --suites functional

# 只运行性能测试
python run_all_rag_tests.py --suites performance

# 只运行错误场景测试
python run_all_rag_tests.py --suites error_scenarios

# 运行多个测试套件
python run_all_rag_tests.py --suites functional performance
```

#### 运行单个测试文件
```bash
# 运行功能测试
python test_rag_system_complete.py

# 运行性能基准测试
python test_rag_performance_benchmark.py

# 运行错误场景测试
python test_rag_error_scenarios.py
```

#### 详细日志模式
```bash
python run_all_rag_tests.py --verbose
```

## 测试配置

### 配置文件说明

测试配置文件位于 [`config/test_config.yaml`](config/test_config.yaml)，包含以下主要配置：

#### 测试环境配置
```yaml
test_environment:
  database:
    test_db_path: "./data/jobs.db"
    backup_db_path: "./test_data/test_jobs_backup.db"
  
  llm:
    provider: "zhipu"
    model: "glm-4-flash"
    api_key: "your-api-key"  # 需要配置有效的API密钥
```

#### 功能测试配置
```yaml
functional_tests:
  job_processing:
    test_fallback_mode: true   # 测试备用处理模式
    test_llm_mode: false       # 是否测试LLM模式
```

#### 性能测试配置
```yaml
performance_tests:
  batch_processing_benchmark:
    batch_sizes: [1, 5, 10, 20, 50]
    acceptable_jobs_per_second: 2
```

### 自定义配置

1. **创建本地配置文件**:
```bash
cp config/test_config.yaml config/test_config_local.yaml
```

2. **修改配置**:
```yaml
# 启用LLM测试（需要有效API密钥）
functional_tests:
  job_processing:
    test_llm_mode: true

# 调整性能基准
performance_tests:
  batch_processing_benchmark:
    acceptable_jobs_per_second: 5  # 提高期望性能
```

3. **使用自定义配置**:
```bash
export TEST_CONFIG_PATH="config/test_config_local.yaml"
python run_all_rag_tests.py
```

## 测试结果

### 报告格式

测试完成后会生成以下报告文件：

```
test_reports/
├── rag_complete_test_report_YYYYMMDD_HHMMSS.json      # 完整测试报告
├── rag_system_test_report_YYYYMMDD_HHMMSS.json        # 功能测试报告
├── rag_performance_benchmark_YYYYMMDD_HHMMSS.json     # 性能基准报告
└── rag_error_scenarios_report_YYYYMMDD_HHMMSS.json    # 错误场景报告
```

### 报告内容

#### 功能测试报告
```json
{
  "total_tests": 15,
  "passed_tests": 14,
  "failed_tests": 1,
  "test_details": [
    {
      "test_name": "系统初始化",
      "status": "✅ PASS",
      "details": "组件状态: {'db_reader': True, 'job_processor': True, ...}"
    }
  ]
}
```

#### 性能基准报告
```json
{
  "benchmarks": [
    {
      "test_name": "系统初始化性能",
      "avg_init_time_seconds": 2.5,
      "avg_memory_increase_mb": 45.2
    },
    {
      "test_name": "批量处理性能",
      "optimal_batch_size": 10,
      "batch_results": [...]
    }
  ]
}
```

#### 错误场景报告
```json
{
  "total_scenarios": 20,
  "passed_scenarios": 18,
  "failed_scenarios": 2,
  "scenario_details": [
    {
      "scenario_name": "数据库文件不存在",
      "status": "✅ PASS",
      "error_handled": true,
      "details": "正确抛出异常: FileNotFoundError"
    }
  ]
}
```

### 成功标准

#### 功能测试
- **通过率**: ≥ 80%
- **核心功能**: 系统初始化、数据处理、向量搜索必须通过
- **集成测试**: 端到端工作流必须正常运行

#### 性能基准测试
- **初始化时间**: ≤ 10秒
- **处理速度**: ≥ 2职位/秒
- **搜索响应**: ≤ 500ms
- **内存使用**: ≤ 5MB/职位

#### 错误场景测试
- **通过率**: ≥ 70%
- **错误处理率**: ≥ 80%
- **关键错误**: 数据库连接、API调用错误必须正确处理

## 故障排除

### 常见问题

#### 1. 数据库连接失败
```
错误: sqlite3.OperationalError: no such file: ./data/jobs.db
解决: 确保数据库文件存在，或运行数据库初始化脚本
```

#### 2. LLM API调用失败
```
错误: API key invalid
解决: 在test_config.yaml中配置有效的API密钥
```

#### 3. 向量数据库权限错误
```
错误: PermissionError: [Errno 13] Permission denied
解决: 检查test_chroma_db目录权限，或使用sudo运行
```

#### 4. 内存不足
```
错误: MemoryError: Out of memory
解决: 减少测试批次大小，或增加系统内存
```

### 调试模式

#### 启用详细日志
```bash
python run_all_rag_tests.py --verbose
```

#### 单步调试
```python
# 在测试文件中添加断点
import pdb; pdb.set_trace()

# 或使用IDE调试器
```

#### 性能分析
```bash
# 使用cProfile分析性能
python -m cProfile -o test_profile.prof test_rag_system_complete.py

# 查看分析结果
python -c "import pstats; pstats.Stats('test_profile.prof').sort_stats('cumulative').print_stats(20)"
```

## 持续集成

### GitHub Actions配置

创建 `.github/workflows/rag_tests.yml`:

```yaml
name: RAG System Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run RAG tests
      run: |
        python run_all_rag_tests.py --suites functional error_scenarios
      env:
        ZHIPU_API_KEY: ${{ secrets.ZHIPU_API_KEY }}
    
    - name: Upload test reports
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: test-reports
        path: test_reports/
```

### 本地预提交钩子

创建 `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: rag-tests
        name: RAG System Tests
        entry: python run_all_rag_tests.py --suites functional
        language: system
        pass_filenames: false
        always_run: true
```

## 扩展测试

### 添加新测试用例

1. **功能测试**:
```python
async def test_new_feature(self, coordinator):
    """测试新功能"""
    print("\n🆕 测试: 新功能")
    
    try:
        # 测试逻辑
        result = await coordinator.new_feature()
        
        self.log_test_result(
            "新功能测试",
            result is not None,
            f"结果: {result}"
        )
        
    except Exception as e:
        self.log_test_result("新功能测试", False, f"异常: {e}")
```

2. **性能基准测试**:
```python
async def benchmark_new_feature(self):
    """新功能性能基准测试"""
    print("\n⚡ 基准测试: 新功能性能")
    
    start_time = time.time()
    # 执行测试
    end_time = time.time()
    
    benchmark = {
        'test_name': '新功能性能',
        'execution_time': end_time - start_time,
        # 其他指标
    }
    
    self.benchmark_results['benchmarks'].append(benchmark)
```

3. **错误场景测试**:
```python
async def test_new_error_scenario(self):
    """测试新错误场景"""
    print("\n🚨 错误场景: 新错误类型")
    
    try:
        # 模拟错误条件
        with patch('some.module.function') as mock_func:
            mock_func.side_effect = Exception("New error type")
            
            # 执行测试
            result = await some_operation()
            
            self.log_scenario_result(
                "新错误场景",
                result is None,  # 期望失败
                "正确处理新错误类型",
                error_handled=True
            )
            
    except Exception as e:
        self.log_scenario_result(
            "新错误场景",
            True,
            f"正确捕获异常: {type(e).__name__}",
            error_handled=True
        )
```

### 自定义测试套件

创建新的测试文件 `test_custom_rag_features.py`:

```python
#!/usr/bin/env python3
"""
自定义RAG功能测试
"""

import sys
import asyncio
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

class CustomRAGTester:
    """自定义RAG测试器"""
    
    def __init__(self):
        self.test_results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_details': []
        }
    
    async def run_custom_tests(self):
        """运行自定义测试"""
        # 实现自定义测试逻辑
        pass

if __name__ == "__main__":
    tester = CustomRAGTester()
    success = asyncio.run(tester.run_custom_tests())
    sys.exit(0 if success else 1)
```

## 最佳实践

### 测试设计原则

1. **独立性**: 每个测试应该独立运行，不依赖其他测试的结果
2. **可重复性**: 测试结果应该在相同条件下可重复
3. **快速反馈**: 优先运行快速的功能测试，性能测试可以单独运行
4. **清晰断言**: 测试失败时应该提供清晰的错误信息

### 测试数据管理

1. **使用测试专用数据**: 不要在生产数据上运行测试
2. **数据隔离**: 每个测试使用独立的数据集
3. **清理策略**: 测试完成后清理临时数据
4. **备份恢复**: 重要测试前备份数据

### 性能测试注意事项

1. **基准建立**: 建立性能基准线，监控性能回归
2. **环境一致性**: 在相同环境下进行性能对比
3. **多次测量**: 进行多次测量取平均值
4. **资源监控**: 监控CPU、内存、磁盘等资源使用

### 错误测试策略

1. **边界条件**: 测试极端输入和边界条件
2. **异常路径**: 覆盖所有可能的异常路径
3. **恢复机制**: 验证系统的错误恢复能力
4. **优雅降级**: 测试系统在部分功能失效时的表现

## 贡献指南

### 提交测试

1. **Fork项目**: 创建项目的分支
2. **添加测试**: 为新功能添加相应的测试
3. **运行测试**: 确保所有测试通过
4. **提交PR**: 提交包含测试的Pull Request

### 测试审查

1. **代码覆盖率**: 确保新代码有足够的测试覆盖
2. **测试质量**: 审查测试的有效性和完整性
3. **性能影响**: 评估新功能对性能的影响
4. **文档更新**: 更新相关的测试文档

---

## 联系信息

如有测试相关问题，请联系：
- 项目维护者: [项目负责人]
- 技术支持: [技术支持邮箱]
- 问题反馈: [GitHub Issues链接]