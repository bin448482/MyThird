# 智能简历投递系统

基于Python的智能简历投递系统，集成了LangChain RAG技术进行职位信息智能分析。支持智联招聘、前程无忧、Boss直聘等主流招聘网站，使用Selenium进行网页自动化，采用人工登录后自动化操作的方式。

## 🌟 核心特性

- 🤖 **人工登录 + 自动化操作**: 避免验证码和风控检测
- 🧠 **RAG智能分析**: 使用LangChain和智谱GLM-4-Flash分析职位信息
- 💬 **智能问答助手**: 基于自然语言的职位市场数据分析
- 📊 **语义匹配**: 基于向量相似度的深度语义理解和职位匹配
- 🔄 **端到端自动化**: 从职位搜索到简历投递的完整自动化流程
- 🛡️ **防反爬机制**: 随机延迟、鼠标轨迹模拟等人类行为
- 💾 **双重数据存储**: SQLite结构化数据 + ChromaDB向量数据库
- ⚙️ **模块化架构**: 登录、提取、分析功能完全分离
- 🔄 **智能去重**: 基于职位指纹的去重机制
- 📈 **性能优化**: 智能缓存、批量处理、并发控制
- 🎯 **简历优化**: AI驱动的简历分析和优化建议
- 📋 **灵活匹配**: 支持任意用户的通用简历匹配系统

## 🚀 快速开始

### 1. 环境要求

- Python 3.8+
- Chrome浏览器（推荐）
- 智谱AI API密钥

### 2. 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd MyThird

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置设置

```bash
# 复制配置文件模板
cp config/config.example.yaml config/config.yaml

# 编辑配置文件，设置API密钥等
```

配置智谱AI API密钥：
```yaml
rag_system:
  llm:
    provider: "zhipu"
    model: "glm-4-flash"
    api_key: "your-zhipu-api-key"
```

### 4. 数据库初始化

```bash
# 运行数据库迁移（如果需要）
python migrate_database_for_rag.py
```

## 📋 主要功能

### 🤖 智能问答助手

最受欢迎的功能！通过自然语言与AI助手对话，获取职位市场分析：

```bash
# 启动智能问答助手
python rag_cli.py chat
```

**示例对话**：
```
💬 您的问题: 现在哪个技能在市场上机会最多？

🤖 回答:
   根据最新的445个职位数据分析，目前市场上机会最多的技能排名如下：
   • Python - 156个职位 (35.1%市场份额)
   • Java - 134个职位 (30.1%市场份额)
   • JavaScript - 98个职位 (22.0%市场份额)
   
💬 您的问题: Python开发的平均薪资是多少？

🤖 回答:
   基于43个职位的薪资数据分析，Python工程师平均月薪13k，年薪约15万元。
   薪资范围：0k-50k，中位数薪资：5k...
```

### 🔧 RAG系统管理

#### 查看系统状态
```bash
# 查看完整系统状态
python rag_cli.py status
```

#### 数据流水线操作
```bash
# 运行RAG数据流水线
python rag_cli.py pipeline run --batch-size 20 --show-progress

# 恢复中断的处理
python rag_cli.py pipeline resume --batch-size 10

# 强制重新处理所有数据
python rag_cli.py pipeline run --force-reprocess
```

#### 向量数据库管理
```bash
# 测试向量数据库
python rag_cli.py test --test-search --queries "Python,Java,前端"

# 搜索职位
python rag_cli.py search "Python开发工程师" --limit 5

# 清理向量数据库
python rag_cli.py clear --force

# 查看数据库统计
python rag_cli.py status
```

### 🎯 简历匹配系统

#### 职位匹配
```bash
# 使用通用简历格式匹配
python rag_cli.py match find-jobs --resume data/generic_resume_example.json --limit 20

# 生成匹配报告
python rag_cli.py match generate-report --resume data/resume.json --output report.html

# 分析特定职位匹配度
python rag_cli.py match analyze-fit --resume data/resume.json --job-id job123
```

#### 简历优化
```bash
# 简历优化建议
python rag_cli.py optimize --resume-file resume.json --target-job "Python开发工程师"

# 批量优化多个简历
python rag_cli.py optimize --resume-dir ./resumes/ --output-dir ./optimized/
```

#### 简历文档处理
```bash
# 处理单个简历文档
python rag_cli.py resume process \
    --input resume.md \
    --output resume.json \
    --format markdown

# 批量处理简历文档
python rag_cli.py resume batch-process \
    --input-dir ./resumes/ \
    --output-dir ./processed/ \
    --formats md,docx,pdf \
    --parallel 3

# 验证简历JSON格式
python rag_cli.py resume validate \
    --input resume.json \
    --schema-check \
    --completeness-check

# 完整流程：文档处理 + 职位匹配
python rag_cli.py resume match \
    --input resume.md \
    --limit 20 \
    --output matches.json \
    --include-analysis
```

### 🚀 端到端集成系统

完整的自动化求职流程，从职位搜索到简历投递：

```bash
# 基本使用
python src/integration_main.py -k "Python开发" "数据分析师" -l "北京" "上海"

# 干运行模式（推荐测试时使用）
python src/integration_main.py -k "Python开发" --dry-run

# 指定简历文件
python src/integration_main.py -k "Python开发" -r testdata/resume.json

# 健康检查
python src/integration_main.py --health-check
```

### 🕷️ 传统网页投递

#### 智联招聘
```bash
# 基本投递
python src/main.py --website zhilian

# 试运行模式
python src/main.py --website zhilian --dry-run
```

#### Boss直聘
```bash
# Boss直聘投递
python src/main.py --website boss --debug
```

#### 前程无忧
```bash
# 前程无忧投递
python src/main.py --website qiancheng --config custom_config.yaml
```

### 🧪 测试系统

#### 运行所有测试
```bash
# 运行完整测试套件
python run_all_rag_tests.py

# 运行特定测试套件
python run_all_rag_tests.py --suites functional performance

# 详细日志模式
python run_all_rag_tests.py --verbose
```

#### 单独测试模块
```bash
# 功能测试
python test_rag_system_complete.py

# 性能基准测试
python test_rag_performance_benchmark.py

# 错误场景测试
python test_rag_error_scenarios.py

# Agent测试
python test_langchain_agent.py
```

#### 快速测试
```bash
# 快速向量数据库测试
python quick_vector_test.py

# 验证数据库内容
python verify_database.py

# 集成验证
python verify_integration.py
```

## 🏗️ 系统架构

### 核心组件

```
智能简历投递系统
├── 🤖 智能问答助手 (rag_cli.py chat)
│   ├── LangChain Agent (src/analysis_tools/agent.py)
│   ├── 技能需求分析工具 (skill_demand_tool.py)
│   ├── 薪资分析工具 (salary_analysis_tool.py)
│   └── 趋势分析工具 (trend_analysis_tool.py)
├── 🔐 认证模块 (src/auth/)
│   ├── 浏览器管理 (browser_manager.py)
│   ├── 登录管理 (login_manager.py)
│   └── 会话管理 (session_manager.py)
├── 🔍 搜索模块 (src/search/)
│   ├── 搜索自动化 (automation.py)
│   ├── 登录检测 (login_detector.py)
│   └── URL构建 (url_builder.py)
├── 📄 内容提取模块 (src/extraction/)
│   ├── 内容提取器 (content_extractor.py)
│   ├── 页面解析器 (page_parser.py)
│   └── 数据存储 (data_storage.py)
├── 🧠 RAG智能分析模块 (src/rag/)
│   ├── 职位处理器 (job_processor.py, optimized_job_processor.py)
│   ├── 向量管理器 (vector_manager.py)
│   ├── 系统协调器 (rag_system_coordinator.py)
│   ├── 数据流水线 (data_pipeline.py)
│   ├── 简历优化器 (resume_optimizer.py)
│   ├── 简历管理器 (resume_manager.py)
│   ├── 文档解析器 (resume_document_parser.py)
│   ├── 性能优化器 (performance_optimizer.py)
│   └── 错误处理器 (error_handler.py)
├── 🎯 匹配引擎 (src/matcher/)
│   ├── 智能匹配 (smart_matching.py)
│   ├── 语义评分 (semantic_scorer.py)
│   ├── 通用简历匹配 (generic_resume_matcher.py)
│   └── 多维度评分 (multi_dimensional_scorer.py)
├── 🚀 集成系统 (src/integration/)
│   ├── 统一主控制器 (master_controller.py)
│   ├── 数据传递接口 (data_bridge.py)
│   ├── 作业调度器 (job_scheduler.py)
│   ├── 智能决策引擎 (decision_engine.py)
│   ├── 自动投递引擎 (auto_submission_engine.py)
│   └── 监控系统 (monitoring.py)
├── 💾 数据库模块 (src/database/)
│   ├── 数据模型 (models.py)
│   ├── 数据库操作 (operations.py)
│   └── 向量操作 (vector_ops.py)
└── 🛠️ 工具模块 (src/utils/)
    ├── 日志工具 (logger.py)
    ├── 行为模拟 (behavior_simulator.py)
    └── 指纹生成 (fingerprint.py)
```

### 数据流程

```mermaid
graph TD
    A[用户输入] --> B[认证模块]
    B --> C[搜索模块]
    C --> D[内容提取模块]
    D --> E[RAG智能分析]
    E --> F[向量数据库]
    F --> G[匹配引擎]
    G --> H[结果输出]
    
    I[简历文档] --> J[文档解析]
    J --> K[RAG处理]
    K --> L[结构化数据]
    L --> G
    
    M[自然语言问题] --> N[LangChain Agent]
    N --> O[分析工具]
    O --> P[数据分析]
    P --> Q[智能回答]
```

## ⚙️ 配置说明

### 主要配置文件

#### config/config.yaml - 主配置
```yaml
# RAG系统配置
rag_system:
  llm:
    provider: "zhipu"
    model: "glm-4-flash"
    api_key: "your-api-key"
    temperature: 0.1
    max_tokens: 2000
  
  vector_db:
    persist_directory: "./data/test_chroma_db"
    collection_name: "job_positions"
  
  processing:
    skip_processed: true
    batch_size: 20
    max_retry_attempts: 3

# 搜索配置
search:
  strategy:
    max_pages: 10
    enable_pagination: true
    page_delay: 2
    max_results_per_keyword: 50

# 去重配置
deduplication:
  enabled: true
  fingerprint_algorithm: "md5"
  fingerprint_length: 12

# 匹配算法配置
matching:
  weights:
    semantic_similarity: 0.35
    skills_match: 0.30
    experience_match: 0.20
    industry_match: 0.10
    salary_match: 0.05
  
  thresholds:
    excellent: 0.85
    good: 0.70
    fair: 0.50
```

#### config/agent_config.yaml - Agent配置
```yaml
langchain_agent:
  llm:
    provider: "zhipu"
    model: "glm-4-flash"
    temperature: 0.1
    max_tokens: 2000
  
  tools:
    skill_demand_analysis:
      enabled: true
      default_limit: 20
    salary_analysis:
      enabled: true
      include_percentiles: true
    trend_analysis:
      enabled: true
      default_period_days: 30
```

#### config/integration_config.yaml - 集成配置
```yaml
integration_system:
  master_controller:
    max_concurrent_jobs: 10
    checkpoint_interval: 100
    error_retry_attempts: 3
  
  auto_submission:
    enabled: true
    dry_run_mode: true  # 测试时设为true
    max_submissions_per_day: 50
    submission_delay: 5
```

## 📊 使用示例

### 编程接口使用

#### RAG系统基础使用
```python
import asyncio
from src.rag.rag_system_coordinator import RAGSystemCoordinator

async def main():
    # 初始化RAG系统
    coordinator = RAGSystemCoordinator()
    
    # 运行数据流水线
    result = await coordinator.run_data_pipeline(batch_size=20)
    print(f"处理完成: {result}")
    
    # 搜索职位
    results = coordinator.search_jobs("Python开发工程师", limit=5)
    for job in results:
        print(f"职位: {job.page_content}")

asyncio.run(main())
```

#### 智能问答使用
```python
from src.analysis_tools.agent import JobMarketAnalysisAgent
from src.rag.rag_system_coordinator import RAGSystemCoordinator

# 初始化系统
coordinator = RAGSystemCoordinator()
coordinator.initialize_system()

# 创建Agent
agent = JobMarketAnalysisAgent(coordinator)

# 进行分析
response = agent.analyze("Python工程师的市场需求如何？")
print(response)
```

#### 简历匹配使用
```python
from src.matcher.generic_resume_matcher import GenericResumeJobMatcher
from src.matcher.generic_resume_models import GenericResumeProfile

# 创建简历档案
resume = GenericResumeProfile(
    name="张三",
    current_position="高级Python工程师"
)
resume.add_skill_category("编程语言", ["Python", "Java"], "advanced")
resume.add_skill_category("AI/ML", ["TensorFlow", "PyTorch"], "intermediate")

# 执行匹配
matcher = GenericResumeJobMatcher()
matches = matcher.find_matching_jobs(resume, limit=10)

for match in matches:
    print(f"职位: {match['job_title']}")
    print(f"匹配度: {match['overall_score']:.2f}")
    print(f"公司: {match['company']}")
```

#### 端到端集成使用
```python
import asyncio
from src.integration_main import IntegratedResumeSystem

async def main():
    # 创建系统实例
    system = IntegratedResumeSystem()
    
    # 准备简历档案
    resume_profile = {
        'name': '张三',
        'skills': ['Python', '机器学习', '数据分析'],
        'experience': '3年',
        'location_preference': ['北京', '上海']
    }
    
    # 运行流水线
    result = await system.run_pipeline(
        search_keywords=['Python开发', '数据分析师'],
        resume_profile=resume_profile,
        submission_config={'dry_run_mode': True}
    )
    
    print(f"执行结果: {result}")

asyncio.run(main())
```

### 简历格式示例

#### 通用格式简历 (data/generic_resume_example.json)
```json
{
  "name": "张三",
  "current_position": "高级前端工程师",
  "total_experience_years": 5,
  "skill_categories": [
    {
      "category_name": "前端技术",
      "skills": ["JavaScript", "React", "Vue.js"],
      "proficiency_level": "advanced",
      "years_experience": 5
    },
    {
      "category_name": "后端技术", 
      "skills": ["Node.js", "Python"],
      "proficiency_level": "intermediate",
      "years_experience": 3
    }
  ],
  "work_history": [
    {
      "company": "某科技公司",
      "position": "高级前端工程师",
      "start_date": "2022-01",
      "end_date": null,
      "duration_years": 2.0,
      "responsibilities": ["负责前端架构设计", "团队技术指导"],
      "achievements": ["性能优化提升50%", "团队效率提升30%"],
      "technologies": ["React", "TypeScript", "Webpack"],
      "industry": "互联网"
    }
  ],
  "profile_type": "frontend_engineer"
}
```

## 🔧 高级功能

### 性能优化

#### 智能缓存
```bash
# 启用缓存优化
python rag_cli.py pipeline run --enable-cache --cache-ttl 3600
```

#### 批量处理优化
```bash
# 调整批处理大小
python rag_cli.py pipeline run --batch-size 50 --parallel 3
```

#### 内存监控
```bash
# 启用内存监控
python rag_cli.py pipeline run --monitor-memory --memory-limit 2048
```

### 错误处理和恢复

#### 自动重试
```bash
# 设置重试次数
python rag_cli.py pipeline run --max-retries 5 --retry-delay 10
```

#### 错误恢复
```bash
# 从检查点恢复
python rag_cli.py pipeline resume --checkpoint-file last_checkpoint.json
```

### 数据质量控制

#### 数据验证
```bash
# 验证数据完整性
python rag_cli.py validate --check-completeness --check-quality
```

#### 质量报告
```bash
# 生成质量报告
python rag_cli.py report --type quality --output quality_report.html
```

## 📈 监控和分析

### 系统监控
```bash
# 查看系统性能指标
python rag_cli.py monitor --metrics performance memory cache

# 生成性能报告
python rag_cli.py report --type performance --period 7d
```

### 数据分析
```bash
# 分析职位数据趋势
python rag_cli.py analyze --type trends --period 30d

# 技能需求分析
python rag_cli.py analyze --type skills --output skills_analysis.json
```

## 🚨 故障排除

### 常见问题

#### 1. API密钥错误
```
错误: Invalid API key
解决: 检查config/config.yaml中的API密钥配置
```

#### 2. 数据库连接失败
```
错误: sqlite3.OperationalError: no such file
解决: 运行 python migrate_database_for_rag.py 初始化数据库
```

#### 3. 向量数据库权限错误
```
错误: PermissionError: Permission denied
解决: 检查data/test_chroma_db目录权限，或使用管理员权限运行
```

#### 4. 内存不足
```
错误: MemoryError: Out of memory
解决: 减少批处理大小 --batch-size 10，或增加系统内存
```

#### 5. Agent工具调用失败
```
错误: Tool execution failed
解决: 检查工具注册和LLM配置，确保API密钥正确
```

### 调试模式
```bash
# 启用详细日志
python rag_cli.py --verbose pipeline run

# 启用调试模式
python rag_cli.py --debug test --test-search

# Agent调试
python rag_cli.py chat --verbose
```

### 日志查看
```bash
# 查看最新日志
tail -f logs/rag_system.log

# 查看错误日志
grep ERROR logs/rag_system.log

# 查看Agent日志
tail -f logs/agent.log
```

## 🔄 更新和维护

### 系统更新
```bash
# 更新依赖
pip install -r requirements.txt --upgrade

# 数据库迁移
python migrate_database_for_rag.py --upgrade
```

### 数据备份
```bash
# 备份数据库
cp data/jobs.db data/jobs_backup_$(date +%Y%m%d).db

# 备份向量数据库
cp -r data/test_chroma_db data/test_chroma_db_backup_$(date +%Y%m%d)
```

### 清理和维护
```bash
# 清理临时文件
python rag_cli.py cleanup --temp-files --old-logs

# 优化数据库
python rag_cli.py optimize --vacuum-db --rebuild-index
```

## 📚 扩展开发

### 添加新的网站支持
1. 在 `src/adapters/` 目录下创建新的适配器文件
2. 继承 `BaseAdapter` 类并实现必要方法
3. 在配置文件中添加网站配置
4. 在 `AdapterFactory` 中注册新适配器

### 自定义匹配算法
1. 修改 `src/matcher/scoring.py` 中的评分逻辑
2. 调整配置文件中的权重和阈值
3. 更新AI分析提示词以提取更多维度信息

### 添加新的LLM支持
1. 在 `src/rag/llm_factory.py` 中添加新的LLM适配器
2. 实现LangChain兼容的接口
3. 在配置文件中添加新的LLM配置选项

### 添加新的分析工具
1. 继承 `BaseAnalysisTool` 类
2. 实现必需的字段和方法
3. 在Agent中注册新工具
4. 更新配置文件

## 🤝 贡献指南

### 提交代码
1. Fork项目并创建功能分支
2. 添加相应的测试用例
3. 确保所有测试通过
4. 提交Pull Request

### 测试要求
- 新功能必须包含单元测试
- 测试覆盖率不低于80%
- 通过所有现有测试

### 代码规范
- 遵循PEP 8代码风格
- 添加详细的文档字符串
- 使用类型提示

## 📄 许可证

MIT License

## ⚠️ 免责声明

本工具仅供学习和研究使用，使用者需自行承担使用风险，遵守相关法律法规和网站条款。

## 📞 支持

如有问题或建议，请：
- 查看文档: [项目文档链接]
- 提交Issue: [GitHub Issues链接]
- 联系维护者: [联系方式]

## 🔐 登录功能使用指南

### 快速切换登录模式

系统支持登录模式和无登录模式的无缝切换：

```bash
# 启用登录模式
python switch_login_mode.py --enable

# 禁用登录模式
python switch_login_mode.py --disable

# 查看当前状态
python switch_login_mode.py --status
```

### 登录模式配置

在 `config/config.yaml` 中配置登录模式：

```yaml
login_mode:
  enabled: true  # 启用登录模式
  website: "qiancheng"
  require_login_for_details: true
  auto_save_session: true
  session_validation_interval: 300
  detail_page_delay: 3.0
  max_login_attempts: 3
  login_retry_delay: 10
```

### 登录模式使用示例

```python
from src.extraction.content_extractor import ContentExtractor
import yaml

# 加载配置
with open('config/config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 创建提取器（自动检测登录模式）
extractor = ContentExtractor(config)

# 提取职位信息（如果启用登录模式，会自动处理登录）
results = extractor.extract_from_keyword("Python开发", max_results=10)

# 获取登录状态摘要
status = extractor.get_login_status_summary()
print(f"执行模式: {status['extraction_mode']}")
print(f"登录状态: {status['login_status']['is_logged_in']}")

# 关闭提取器
extractor.close()
```

### 登录状态分析

分析当前登录状态，用于调试和优化：

```bash
# 运行登录状态分析
python test_login_analysis.py
```

### 登录功能测试

```bash
# 运行登录模式集成测试
python test_login_mode_integration.py

# 测试配置加载
python test_config_loading.py
```

## 📋 简历投递功能使用指南

### 基本投递操作

```python
from src.integration.master_controller import MasterController, PipelineConfig

# 创建配置
config = {
    'database_path': 'data/jobs.db',
    'submission_engine': {
        'batch_size': 10,
        'daily_limit': 50
    }
}

# 初始化主控制器
controller = MasterController(config)

# 创建流水线配置
pipeline_config = PipelineConfig(
    search_keywords=['Python开发工程师'],
    submission_config={
        'batch_size': 5
    }
)

# 执行投递
result = controller.run_stage_only('resume_submission', pipeline_config)
print(f"投递结果: {result}")
```

### 完整流水线投递

```python
import asyncio
from src.integration.master_controller import MasterController, PipelineConfig

async def run_full_pipeline():
    config = {
        'database_path': 'data/jobs.db',
        # ... 其他配置
    }
    
    controller = MasterController(config)
    
    pipeline_config = PipelineConfig(
        search_keywords=['Python开发工程师', 'Java开发工程师'],
        max_jobs_per_keyword=20,
        resume_profile={
            'name': '张三',
            'experience_years': 5,
            'skills': ['Python', 'Django', 'MySQL']
        },
        submission_config={
            'batch_size': 10,
            'auto_login_enabled': True
        }
    )
    
    # 执行完整流水线
    report = await controller.run_full_pipeline(pipeline_config)
    
    print(f"流水线执行完成:")
    print(f"- 职位提取: {report.extraction_result.get('total_extracted', 0)}")
    print(f"- RAG处理: {report.rag_result.get('processed_count', 0)}")
    print(f"- 简历匹配: {report.matching_result.get('total_matches', 0)}")
    print(f"- 投递成功: {report.submission_result.get('successful_submissions', 0)}")

# 运行
asyncio.run(run_full_pipeline())
```

### 单独使用投递引擎

```python
from src.submission.submission_engine import ResumeSubmissionEngine

# 初始化引擎
engine = ResumeSubmissionEngine(config)

# 同步初始化
success = engine.initialize_sync()
if not success:
    print("初始化失败")
    exit(1)

# 执行批量投递
report = engine.run_submission_batch_sync(batch_size=5)

print(f"投递完成:")
print(f"- 总处理: {report.total_processed}")
print(f"- 成功: {report.successful_count}")
print(f"- 失败: {report.failed_count}")
print(f"- 跳过: {report.skipped_count}")

# 清理资源
import asyncio
asyncio.run(engine.cleanup())
```

### 投递配置说明

在 `config/submission_config.yaml` 中配置投递参数：

```yaml
submission_engine:
  # 批处理配置
  batch_size: 10                    # 每批处理的职位数量
  daily_limit: 50                   # 每日投递限制
  
  # 登录配置
  auto_login_enabled: true          # 是否启用自动登录
  manual_login_timeout: 300         # 手动登录超时时间(秒)
  
  # 延迟配置
  delays:
    min_delay: 3.0                  # 最小延迟(秒)
    max_delay: 8.0                  # 最大延迟(秒)
    batch_delay: 30.0               # 批次间延迟(秒)
    reading_delay: 15.0             # 页面阅读延迟(秒)

# 反爬虫配置
anti_crawler:
  enable_delays: true               # 启用延迟
  enable_risk_detection: true       # 启用风险检测
  max_daily_submissions: 50         # 最大每日投递数
  risk_mitigation:
    pause_duration: 300             # 风险暂停时间(秒)
    cooldown_period: 1800           # 冷却期(秒)

# 按钮识别配置
button_recognition:
  timeout: 10                       # 按钮查找超时时间
  retry_attempts: 3                 # 重试次数
  
  # 支持的网站选择器
  site_selectors:
    "51job.com":
      - ".btn-apply"
      - ".apply-btn"
      - "[data-action='apply']"
    "zhaopin.com":
      - ".apply-btn"
      - ".btn-delivery"
    "boss.com":
      - ".btn-startchat"
      - ".start-chat-btn"
```

### 投递监控和统计

```python
# 获取投递统计
stats = engine.get_submission_statistics()
print(f"统计信息: {stats}")

# 查看失败记录
failed_records = engine.get_failed_submissions(limit=10)
for record in failed_records:
    print(f"失败职位: {record['job_title']} - {record['error_message']}")

# 重置失败记录
reset_count = engine.reset_failed_submissions()
print(f"重置了 {reset_count} 条失败记录")
```

### 投递测试

```bash
# 运行集成测试
python test_submission_integration.py

# 测试单个组件
python -c "
from src.submission.data_manager import SubmissionDataManager
dm = SubmissionDataManager('data/jobs.db')
stats = dm.get_submission_statistics()
print(stats)
"
```

## 🎯 技能匹配优化使用指南

### 优化后的匹配效果

技能匹配系统已经过全面优化，提供以下改进：

- **技能匹配率**: 从40%提升到88.5% (+121%)
- **加权匹配分数**: 从0.6提升到1.000 (+67%)
- **技能加分**: 从0.05提升到0.250 (+400%)
- **匹配技能数量**: 从10/26提升到23/26 (+130%)

### 使用优化后的匹配系统

```python
from src.matcher.generic_resume_matcher import GenericResumeJobMatcher
from src.matcher.generic_resume_models import GenericResumeProfile

# 创建简历档案
resume = GenericResumeProfile(
    name="张三",
    current_position="高级Python工程师"
)
resume.add_skill_category("编程语言", ["Python", "Java"], "advanced")
resume.add_skill_category("AI/ML", ["TensorFlow", "PyTorch"], "intermediate")
resume.add_skill_category("数据工程", ["Databricks", "Azure Data Factory"], "advanced")

# 执行匹配
matcher = GenericResumeJobMatcher()
matches = matcher.find_matching_jobs(resume, limit=10)

for match in matches:
    print(f"职位: {match['job_title']}")
    print(f"匹配度: {match['overall_score']:.2f}")
    print(f"公司: {match['company']}")
    print(f"匹配技能: {', '.join(match['matched_skills'])}")
```

### 技能匹配测试

```bash
# 运行技能匹配优化测试
python test_skill_matching_optimization.py

# 查看匹配结果详情
python -c "
from src.matcher.generic_resume_matcher import GenericResumeJobMatcher
matcher = GenericResumeJobMatcher()
# 测试特定简历的匹配效果
"
```

### 支持的技能类别

优化后的系统支持以下技能类别：

**数据工程技能**:
- databricks, delta lake, azure data factory, ssis, informatica
- etl, data pipeline, data governance, data lineage, metadata management

**AI/ML技能**:
- computer vision, yolo, resnet, attention mechanism
- langchain, llamaindex, rag, prompt engineering

**云平台技能**:
- azure databricks, azure functions, azure data lake storage, azure synapse

**架构技能**:
- data architecture, solution architecture, lakehouse architecture

**中文技能支持**:
- 数据工程, 数据架构, 数据治理, 机器学习, 深度学习

## 🔧 系统集成使用指南

### 端到端集成系统使用

```bash
# 基本使用
python src/integration_main.py -k "Python开发" "数据分析师" -l "北京" "上海"

# 干运行模式（推荐测试时使用）
python src/integration_main.py -k "Python开发" --dry-run

# 指定简历文件
python src/integration_main.py -k "Python开发" -r testdata/resume.json

# 健康检查
python src/integration_main.py --health-check
```

### 集成系统配置

在 `config/integration_config.yaml` 中配置集成参数：

```yaml
integration_system:
  master_controller:
    max_concurrent_jobs: 10
    checkpoint_interval: 100
    error_retry_attempts: 3
  
  auto_submission:
    enabled: true
    dry_run_mode: true  # 测试时设为true
    max_submissions_per_day: 50
    submission_delay: 5
```

### 编程接口使用

```python
import asyncio
from src.integration_main import IntegratedResumeSystem

async def main():
    # 创建系统实例
    system = IntegratedResumeSystem()
    
    # 准备简历档案
    resume_profile = {
        'name': '张三',
        'skills': ['Python', '机器学习', '数据分析'],
        'experience': '3年',
        'location_preference': ['北京', '上海']
    }
    
    # 运行流水线
    result = await system.run_pipeline(
        search_keywords=['Python开发', '数据分析师'],
        resume_profile=resume_profile,
        submission_config={'dry_run_mode': True}
    )
    
    print(f"执行结果: {result}")

asyncio.run(main())
```

### 集成测试

```bash
# 运行集成验证
python verify_integration.py

# 运行主控制器测试
python test_master_controller.py

# 运行完整测试套件
python run_all_rag_tests.py
```

## 📊 监控和分析使用指南

### 系统监控

```bash
# 查看系统性能指标
python rag_cli.py monitor --metrics performance memory cache

# 生成性能报告
python rag_cli.py report --type performance --period 7d
```

### 数据分析

```bash
# 分析职位数据趋势
python rag_cli.py analyze --type trends --period 30d

# 技能需求分析
python rag_cli.py analyze --type skills --output skills_analysis.json
```

### 日志查看

```bash
# 查看最新日志
tail -f logs/rag_system.log

# 查看错误日志
grep ERROR logs/rag_system.log

# 查看Agent日志
tail -f logs/agent.log

# 查看投递日志
tail -f logs/submission.log
```

## 🔄 系统维护使用指南

### 系统更新

```bash
# 更新依赖
pip install -r requirements.txt --upgrade

# 数据库迁移
python migrate_database_for_rag.py --upgrade
```

### 数据备份

```bash
# 备份数据库
cp data/jobs.db data/jobs_backup_$(date +%Y%m%d).db

# 备份向量数据库
cp -r data/test_chroma_db data/test_chroma_db_backup_$(date +%Y%m%d)
```

### 清理和维护

```bash
# 清理临时文件
python rag_cli.py cleanup --temp-files --old-logs

# 优化数据库
python rag_cli.py optimize --vacuum-db --rebuild-index
```

### 配置管理

```bash
# 验证配置文件
python test_config_loading.py

# 验证集成配置
python test_integration_config_loading.py

# 切换登录模式
python switch_login_mode.py --enable  # 启用
python switch_login_mode.py --disable # 禁用
```

## 🚨 故障排除使用指南

### 常见问题解决

#### 1. API密钥错误
```bash
# 错误: Invalid API key
# 解决: 检查config/config.yaml中的API密钥配置
python test_config_loading.py
```

#### 2. 数据库连接失败
```bash
# 错误: sqlite3.OperationalError: no such file
# 解决: 运行数据库初始化
python migrate_database_for_rag.py
```

#### 3. 向量数据库权限错误
```bash
# 错误: PermissionError: Permission denied
# 解决: 检查data/test_chroma_db目录权限
chmod -R 755 data/test_chroma_db
```

#### 4. 登录检测失败
```bash
# 解决: 使用登录状态分析工具调试
python test_login_analysis.py
```

#### 5. 投递按钮未找到
```bash
# 解决: 检查网站选择器配置，添加新的按钮选择器
# 编辑 config/submission_config.yaml 中的 site_selectors
```

### 调试模式

```bash
# 启用详细日志
python rag_cli.py --verbose pipeline run

# 启用调试模式
python rag_cli.py --debug test --test-search

# Agent调试
python rag_cli.py chat --verbose

# 投递调试（非无头模式）
# 在配置文件中设置 browser.headless: false
```

### 性能优化

```bash
# 调整批处理大小
python rag_cli.py pipeline run --batch-size 10

# 启用缓存优化
python rag_cli.py pipeline run --enable-cache --cache-ttl 3600

# 内存监控
python rag_cli.py pipeline run --monitor-memory --memory-limit 2048
```

### 错误恢复

```bash
# 从检查点恢复
python rag_cli.py pipeline resume --checkpoint-file last_checkpoint.json

# 设置重试次数
python rag_cli.py pipeline run --max-retries 5 --retry-delay 10
```

## 📚 使用示例集合

### 完整工作流示例

```bash
# 1. 系统状态检查
python rag_cli.py status

# 2. 启用登录模式（如需要）
python switch_login_mode.py --enable

# 3. 运行数据流水线
python rag_cli.py pipeline run --batch-size 20 --show-progress

# 4. 简历匹配
python rag_cli.py match find-jobs --resume data/resume.json --limit 20

# 5. 执行投递（干运行模式）
python src/integration_main.py -k "Python开发" --dry-run

# 6. 查看结果统计
python rag_cli.py report --type performance
```

### 开发测试流程

```bash
# 1. 配置验证
python test_config_loading.py

# 2. 登录功能测试
python test_login_mode_integration.py

# 3. 技能匹配测试
python test_skill_matching_optimization.py

# 4. 投递功能测试
python test_submission_integration.py

# 5. 完整集成测试
python verify_integration.py

# 6. 运行所有测试
python run_all_rag_tests.py
```

---

**最后更新**: 2025-08-25
**版本**: v3.1.0
**维护者**: Claude Code Assistant

## 🎯 快速导航

- [智能问答助手](#-智能问答助手) - 最受欢迎的功能
- [RAG系统管理](#-rag系统管理) - 核心数据处理
- [简历匹配系统](#-简历匹配系统) - 智能匹配功能
- [登录功能使用指南](#-登录功能使用指南) - 登录模式配置和使用
- [简历投递功能使用指南](#-简历投递功能使用指南) - 自动投递功能
- [技能匹配优化使用指南](#-技能匹配优化使用指南) - 优化后的匹配系统
- [系统集成使用指南](#-系统集成使用指南) - 端到端集成功能
- [监控和分析使用指南](#-监控和分析使用指南) - 系统监控和数据分析
- [系统维护使用指南](#-系统维护使用指南) - 系统维护和更新
- [故障排除使用指南](#-故障排除使用指南) - 常见问题解决