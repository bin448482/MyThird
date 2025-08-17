# 项目目录结构创建计划

## 需要创建的目录结构

```
resume_auto_submitter/
├── src/
│   ├── __init__.py
│   ├── main.py                 # 主入口
│   ├── core/
│   │   ├── __init__.py
│   │   ├── controller.py       # 核心控制器
│   │   ├── config.py          # 配置管理
│   │   └── exceptions.py      # 自定义异常
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py            # 基础适配器
│   │   ├── zhilian.py         # 智联招聘适配器
│   │   ├── qiancheng.py       # 前程无忧适配器
│   │   └── boss.py            # Boss直聘适配器
│   ├── crawler/
│   │   ├── __init__.py
│   │   ├── engine.py          # 爬虫引擎
│   │   ├── anti_bot.py        # 防反爬机制
│   │   └── selenium_utils.py   # Selenium工具函数
│   ├── analyzer/
│   │   ├── __init__.py
│   │   ├── job_analyzer.py    # 职位分析器
│   │   ├── prompts.py         # LangChain提示词
│   │   └── llm_client.py      # LLM客户端
│   ├── matcher/
│   │   ├── __init__.py
│   │   ├── matching_engine.py # 匹配引擎
│   │   └── scoring.py         # 评分算法
│   ├── submitter/
│   │   ├── __init__.py
│   │   └── submission_engine.py # 投递引擎
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py          # 数据模型
│   │   └── operations.py      # 数据库操作
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── commands.py        # 命令行命令
│   │   └── utils.py           # CLI工具函数
│   └── utils/
│       ├── __init__.py
│       ├── logger.py          # 日志工具
│       └── helpers.py         # 辅助函数
├── config/
│   ├── config.yaml            # 主配置文件
│   ├── config.example.yaml    # 配置示例
│   └── prompts/
│       ├── job_analysis.txt   # 职位分析提示词
│       └── matching.txt       # 匹配分析提示词
├── data/
│   └── .gitkeep
├── logs/
│   └── .gitkeep
├── tests/
│   ├── __init__.py
│   ├── test_crawler.py
│   ├── test_analyzer.py
│   ├── test_matcher.py
│   └── test_integration.py
├── docs/
│   ├── README.md
│   ├── installation.md
│   ├── configuration.md
│   └── usage.md
├── requirements.txt
├── setup.py
├── .gitignore
└── README.md
```

## 核心文件内容规划

### 1. requirements.txt
```
selenium>=4.15.0
langchain>=0.1.0
openai>=1.0.0
pyyaml>=6.0
click>=8.0.0
sqlite3
pytest>=7.0.0
```

### 2. .gitignore
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Project specific
data/*.db
logs/*.log
config/config.yaml
chromedriver*
geckodriver*
```

### 3. setup.py
```python
from setuptools import setup, find_packages

setup(
    name="resume-auto-submitter",
    version="1.0.0",
    description="自动投递简历工具",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "selenium>=4.15.0",
        "langchain>=0.1.0",
        "openai>=1.0.0",
        "pyyaml>=6.0",
        "click>=8.0.0",
        "pytest>=7.0.0",
    ],
    entry_points={
        "console_scripts": [
            "resume-submitter=main:main",
        ],
    },
)
```

### 4. README.md
```markdown
# 自动投递简历工具

基于Python的自动投递简历工具，支持智联招聘、前程无忧、Boss直聘等主流招聘网站。

## 功能特点

- 人工登录 + 自动化操作
- AI职位分析和匹配
- 防反爬机制
- 可配置匹配算法
- 数据持久化

## 安装使用

1. 安装依赖：`pip install -r requirements.txt`
2. 配置设置：复制 `config/config.example.yaml` 到 `config/config.yaml` 并修改
3. 运行工具：`python src/main.py --website zhilian`

## 配置说明

详见 `docs/configuration.md`
```

## 配置文件模板

### config.example.yaml
```yaml
# 基础配置
app:
  name: "Resume Auto Submitter"
  version: "1.0.0"
  debug: false

# 数据库配置
database:
  path: "./data/jobs.db"

# 网站配置
websites:
  zhilian:
    enabled: true
    base_url: "https://www.zhaopin.com"
    login_url: "https://passport.zhaopin.com/login"
    search_url: "https://sou.zhaopin.com"
    login_check_element: ".user-info"
    submit_button_selector: ".btn-apply"
  
  qiancheng:
    enabled: true
    base_url: "https://www.51job.com"
    login_url: "https://login.51job.com"
    search_url: "https://search.51job.com"
    login_check_element: ".login-info"
    submit_button_selector: ".apply-btn"
  
  boss:
    enabled: true
    base_url: "https://www.zhipin.com"
    login_url: "https://login.zhipin.com"
    search_url: "https://www.zhipin.com/c101010100"
    login_check_element: ".user-name"
    submit_button_selector: ".btn-startchat"

# Selenium配置
selenium:
  browser: "chrome"
  headless: false
  window_size: "1920,1080"
  page_load_timeout: 30
  element_wait_timeout: 10
  implicit_wait: 5

# 爬虫配置
crawler:
  delay_min: 2
  delay_max: 5
  max_retries: 3
  login_wait_timeout: 300

# 防反爬配置
anti_bot:
  random_delay: true
  mouse_simulation: true
  user_agent_rotation: true
  scroll_simulation: true

# AI分析配置
ai:
  provider: "openai"
  model: "gpt-3.5-turbo"
  api_key: "your-api-key-here"
  base_url: ""
  temperature: 0.1
  max_tokens: 1000

# 匹配算法配置
matching:
  weights:
    skills: 0.5
    experience: 0.3
    salary: 0.2
  thresholds:
    auto_submit: 0.8
    manual_review: 0.6
    skip: 0.3

# 简历配置
resume:
  skills: ["Python", "Java", "React", "Node.js"]
  experience_years: 3
  expected_salary_min: 15000
  expected_salary_max: 25000
  preferred_locations: ["上海"]

# 日志配置
logging:
  level: "INFO"
  file_path: "./logs/app.log"
  console_output: true
```

## 提示词模板

### prompts/job_analysis.txt
```
你是一个专业的职位分析专家。请分析以下职位信息，并以JSON格式输出结构化数据。

职位信息：
{job_description}

请提取以下信息：
1. 技能要求（skills）：列出所需的技术技能
2. 工作经验要求（experience_years）：提取经验年限要求
3. 薪资范围（salary_range）：提取薪资信息
4. 工作地点（location）：提取工作地点
5. 公司规模（company_size）：提取公司规模信息
6. 职位标签（tags）：生成相关标签

输出格式：
{
  "skills": ["技能1", "技能2"],
  "experience_years": 数字,
  "salary_min": 数字,
  "salary_max": 数字,
  "location": "地点",
  "company_size": "规模",
  "tags": ["标签1", "标签2"]
}
```

### prompts/matching.txt
```
你是一个专业的简历匹配分析师。请分析候选人简历与职位要求的匹配度。

候选人信息：
{resume_info}

职位要求：
{job_requirements}

请从以下维度分析匹配度（0-1分）：
1. 技能匹配度（权重50%）
2. 经验匹配度（权重30%）
3. 薪资匹配度（权重20%）

输出格式：
{
  "skills_match": 0.8,
  "experience_match": 0.7,
  "salary_match": 0.9,
  "overall_score": 0.78,
  "analysis": "详细分析说明"
}
```

## 下一步行动

需要切换到Code模式来实际创建这些文件和目录结构。