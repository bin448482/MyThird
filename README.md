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