# 自动投递简历工具

基于Python的自动投递简历工具，支持智联招聘、前程无忧、Boss直聘等主流招聘网站。

## 功能特点

- 🤖 **人工登录 + 自动化操作**: 避免验证码和风控检测
- 🧠 **AI职位分析**: 使用LangChain和大语言模型分析职位信息
- 📊 **智能匹配**: 多维度评估简历与职位的匹配度
- 🛡️ **防反爬机制**: 随机延迟、鼠标轨迹模拟等人类行为
- 💾 **数据持久化**: SQLite数据库存储职位信息和投递记录
- ⚙️ **可配置**: 灵活的配置文件，支持多种参数调整
- 🔄 **断点续传**: 程序重启后可继续处理未完成的职位

## 支持的招聘网站

- 智联招聘 (zhilian)
- 前程无忧 (qiancheng)
- Boss直聘 (boss)

## 安装使用

### 1. 环境要求

- Python 3.8+
- Chrome浏览器（推荐）

### 2. 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd resume-auto-submitter

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

# 编辑配置文件
# 设置AI API密钥、简历信息等
```

### 4. 运行工具

```bash
# 基本使用
python src/main.py --website zhilian

# 调试模式
python src/main.py --website boss --debug

# 试运行模式（不实际投递）
python src/main.py --website qiancheng --dry-run
```

## 配置说明

### 主要配置项

```yaml
# AI分析配置
ai:
  provider: "openai"
  model: "gpt-3.5-turbo"
  api_key: "your-api-key-here"

# 匹配算法配置
matching:
  weights:
    skills: 0.5      # 技能匹配权重
    experience: 0.3  # 经验匹配权重
    salary: 0.2      # 薪资匹配权重
  thresholds:
    auto_submit: 0.8    # 自动投递阈值
    manual_review: 0.6  # 人工审核阈值
    skip: 0.3          # 跳过阈值

# 简历配置
resume:
  skills: ["Python", "Java", "React", "Node.js"]
  experience_years: 3
  expected_salary_min: 15000
  expected_salary_max: 25000
  preferred_locations: ["上海"]
```

## 使用流程

1. **启动程序**: 运行命令后，程序会自动打开浏览器
2. **人工登录**: 在浏览器中手动完成登录操作
3. **自动化开始**: 登录完成后，程序自动检测并开始爬取
4. **职位分析**: AI分析每个职位的详细信息
5. **匹配评分**: 根据配置的权重计算匹配度
6. **自动投递**: 匹配度达到阈值的职位自动投递
7. **生成报告**: 完成后显示执行统计报告

## 项目结构

```
resume_auto_submitter/
├── src/                    # 源代码
│   ├── core/              # 核心模块
│   ├── adapters/          # 网站适配器
│   ├── crawler/           # 爬虫引擎
│   ├── analyzer/          # 职位分析器
│   ├── matcher/           # 匹配引擎
│   ├── submitter/         # 投递引擎
│   ├── database/          # 数据库操作
│   └── utils/             # 工具函数
├── config/                # 配置文件
├── data/                  # 数据库文件
├── logs/                  # 日志文件
└── docs/                  # 文档
```

## 注意事项

1. **合规使用**: 请遵守各招聘网站的使用条款，合理控制频率
2. **简历准备**: 使用前请确保在目标网站上传并设置好默认简历
3. **网络环境**: 建议在稳定的网络环境下使用
4. **数据备份**: 重要数据请定期备份

## 开发说明

### 添加新网站支持

1. 在 `src/adapters/` 目录下创建新的适配器文件
2. 继承 `BaseAdapter` 类并实现必要方法
3. 在配置文件中添加网站配置
4. 在 `AdapterFactory` 中注册新适配器

### 自定义匹配算法

1. 修改 `src/matcher/scoring.py` 中的评分逻辑
2. 调整配置文件中的权重和阈值
3. 更新AI分析提示词以提取更多维度信息

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 免责声明

本工具仅供学习和研究使用，使用者需自行承担使用风险，遵守相关法律法规和网站条款。

## 向量数据库测试和管理

### 📋 概述

本项目集成了完整的RAG（检索增强生成）系统，包括向量数据库管理功能。以下是测试和管理向量数据库的完整指南。

### 🚀 快速测试

#### 使用CLI工具快速测试

```bash
# 查看系统状态
python rag_cli.py status

# 快速测试向量数据库
python rag_cli.py test --test-search --queries "Python,Java,前端"

# 搜索特定内容
python rag_cli.py search "Python开发工程师" --limit 5
```

#### 使用快速测试脚本

```bash
# 运行快速测试脚本
python quick_vector_test.py
```

### 🔍 详细测试

#### 运行完整测试套件

```bash
# 运行完整的向量数据库测试
python test_vector_database_content.py
```

这个测试会检查：

- **📊 数据库统计信息**: 文档数量、集合名称、存储路径
- **📄 文档内容**: 样本文档的内容和元数据
- **🔍 搜索功能**: 多个查询的搜索结果和相似度
- **🏷️ 元数据验证**: 字段完整性和数据质量
- **🎯 相似度质量**: 相关和不相关查询的相似度分析

#### 测试结果解读

**数据库统计信息**:
```
📊 数据库统计:
   文档数量: 51          # 向量数据库中的文档总数
   集合名称: job_positions # ChromaDB集合名称
   存储路径: ./chroma_db   # 数据库文件存储位置
```

**搜索质量指标**:
```
🧪 测试查询: 'Python开发工程师' (relevant)
   平均相似度: 0.724      # 数值越小表示相似度越高
   最高相似度: 0.837      # 最相关文档的相似度
   最低相似度: 0.547      # 最不相关文档的相似度
   关键词匹配率: 100.00%  # 包含关键词的文档比例
```

**相似度分数解读**:
- `< 0.8`: 高度相关
- `0.8 - 1.2`: 中等相关
- `> 1.2`: 低相关或不相关

### 🛠️ CLI工具使用

#### 系统状态查询

```bash
# 查看完整系统状态
python rag_cli.py status
```

输出示例：
```
组件状态:
  db_reader: ✅
  job_processor: ✅
  vector_manager: ✅
数据库统计:
  总职位数: 4
  已处理: 4
  未处理: 0
  处理率: 100.0%
向量数据库:
  文档数量: 51
  集合名称: job_positions
```

#### 向量数据库测试

```bash
# 基础测试
python rag_cli.py test

# 测试搜索功能
python rag_cli.py test --test-search

# 自定义测试查询
python rag_cli.py test --test-search --queries "Python,React,数据分析"

# 调整样本大小
python rag_cli.py test --sample-size 5

# 保存测试报告
python rag_cli.py test --test-search --output test_report.json
```

#### 职位搜索

```bash
# 搜索相关职位
python rag_cli.py search "Python开发工程师" --limit 5

# 保存搜索结果
python rag_cli.py search "前端开发" --limit 10 --output search_results.json
```

### 🗑️ 清理和维护

#### 清理向量数据库

```bash
# 查看当前状态（清理前）
python rag_cli.py status

# 清空所有文档（会询问确认）
python rag_cli.py clear

# 强制清空所有文档（不询问确认）
python rag_cli.py clear --force

# 删除特定职位的文档
python rag_cli.py clear --job-id qc_167390385
```

#### 清理操作的安全建议

1. **备份数据**: 清理前备份重要数据
```bash
# 手动备份chroma_db目录
cp -r ./chroma_db ./chroma_db_backup_$(date +%Y%m%d_%H%M%S)
```

2. **确认清理范围**: 使用测试命令确认要清理的内容
```bash
python rag_cli.py test --sample-size 10
```

3. **分步清理**: 先删除特定职位，再考虑全量清理
```bash
# 先删除特定职位
python rag_cli.py clear --job-id specific_job_id
# 确认结果
python rag_cli.py status
```

#### 重新构建向量数据库

清理后重新构建：

```bash
# 1. 清理现有数据
python rag_cli.py clear --force

# 2. 运行数据流水线重新处理
python rag_cli.py pipeline run --batch-size 20 --show-progress

# 3. 验证重建结果
python rag_cli.py test --test-search
```

### 📊 数据质量评估

#### 评估指标

1. **文档数量合理性**
   - 每个职位应该有3-5个文档（overview, responsibility, requirement等）
   - 总文档数 ≈ 职位数 × 平均文档数

2. **搜索相关性**
   - 相关查询的平均相似度应 < 1.0
   - 关键词匹配率应 > 80%

3. **元数据完整性**
   - 所有文档都应有 `job_id`, `type`, `created_at` 字段
   - 公司、地点等信息应完整

### ❓ 常见问题

#### Q1: 向量数据库为空怎么办？
```bash
# 检查数据库状态
python rag_cli.py status

# 如果未处理职位数 > 0，运行流水线
python rag_cli.py pipeline run

# 如果数据库本身为空，需要先爬取职位数据
```

#### Q2: 搜索结果质量差怎么办？
1. 检查嵌入模型是否适合中文
2. 调整搜索参数（k值、相似度阈值）
3. 优化文档内容质量
4. 考虑使用不同的嵌入模型

#### Q3: 清理后如何恢复数据？
```bash
# 如果有备份
cp -r ./chroma_db_backup_* ./chroma_db

# 如果没有备份，重新运行流水线
python rag_cli.py pipeline run --force-reprocess
```

### 📝 最佳实践

1. **定期测试**: 每次数据更新后运行测试
2. **备份重要数据**: 清理前备份向量数据库
3. **监控质量指标**: 关注搜索相关性和元数据完整性
4. **渐进式清理**: 先测试小范围清理，再扩大范围
5. **文档化操作**: 记录重要的清理和维护操作

### 🔧 高级操作

#### 自定义测试脚本

创建自定义测试：

```python
# custom_test.py
from src.rag.vector_manager import ChromaDBManager
import yaml

# 加载配置
with open('config/test_config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 初始化向量管理器
vector_manager = ChromaDBManager(config.get('vector_store', {}))

# 自定义测试逻辑
stats = vector_manager.get_collection_stats()
print(f"文档数量: {stats.get('document_count', 0)}")

# 测试特定查询
results = vector_manager.search_similar_jobs("你的查询", k=5)
for i, doc in enumerate(results):
    print(f"{i+1}. {doc.page_content[:100]}...")

vector_manager.close()
```

通过这些工具和方法，您可以有效地测试、管理和维护向量数据库，确保RAG系统的数据质量和搜索效果达到预期。

详细的使用指南请参考：[VECTOR_DATABASE_GUIDE.md](VECTOR_DATABASE_GUIDE.md)