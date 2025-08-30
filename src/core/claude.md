# 核心模块

核心模块提供系统的基础配置管理、异常处理和控制器功能，是整个系统的基础设施层。

## 🎯 核心组件

### 1. 配置管理器 (ConfigManager)
**文件**: [`config.py`](config.py)

**职责**: 统一的配置管理
- YAML配置文件解析
- 分层配置架构支持
- 配置验证和默认值
- 环境变量集成

### 2. 自定义异常 (Custom Exceptions)
**文件**: [`exceptions.py`](exceptions.py)

**职责**: 系统异常定义和处理
- 业务异常定义
- 错误分类和编码
- 异常处理策略
- 错误信息本地化

### 3. 传统控制器 (Controller)
**文件**: [`controller.py`](controller.py)

**职责**: 传统投递系统的主控制器
- 基础投递流程控制
- Selenium自动化管理
- 简单的错误处理
- 基本的状态跟踪

## 🔧 配置架构

### 主配置文件 (config/config.yaml)
- RAG系统配置
- 向量数据库配置
- LLM配置
- 登录模式配置

### 集成配置 (config/integration_config.yaml)
- 集成系统配置
- 决策引擎配置
- 性能配置
- 监控配置

## 🚀 使用示例

### 配置加载
```python
from src.core.config import load_config

# 加载主配置
config = load_config("config/config.yaml")

# 加载集成配置
integration_config = load_config("config/integration_config.yaml")
```

---

**Navigation**: [← Content Extraction](../extraction/claude.md) | [Source Overview ↑](../claude.md)