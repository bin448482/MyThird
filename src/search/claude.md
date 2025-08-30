# 搜索和导航

搜索和导航模块负责网站搜索自动化、URL构建、登录检测和页面导航控制，支持多网站兼容和智能导航功能。

## 🎯 核心组件

### 1. 搜索自动化 (SearchAutomation)
**文件**: [`automation.py`](automation.py)

**职责**: 智能搜索自动化和页面导航
- 关键词搜索执行
- 薪资过滤器自动应用
- 增强的下一页导航
- 搜索结果页面解析

**核心功能**:
- **薪资过滤自动点击**: 确保薪资过滤器在搜索前被应用
- **智能页面导航**: 支持失败恢复的强大导航机制
- **多策略元素检测**: JavaScript、XPath、CSS选择器多重检测
- **优雅错误处理**: 不影响主流程的错误处理机制

### 2. URL构建器 (URLBuilder)
**文件**: [`url_builder.py`](url_builder.py)

**职责**: 智能URL构建和管理
- 搜索URL动态构建
- 多网站URL模式适配
- 参数编码和验证
- URL重写和优化

### 3. 登录检测器 (LoginDetector)
**文件**: [`login_detector.py`](login_detector.py)

**职责**: 页面登录状态智能检测
- 登录页面识别
- 登录状态验证
- 重定向检测
- 访问权限判断

## 🔧 使用示例

### 基本搜索操作
```python
from src.search.automation import SearchAutomation

search = SearchAutomation(driver, config)

# 执行关键词搜索
results = search.search_jobs(keywords=["Python开发"], location="北京")

# 导航到下一页
success = search.navigate_to_next_page()
```

---

**Navigation**: [← Database Operations](../database/claude.md) | [Content Extraction →](../extraction/claude.md)