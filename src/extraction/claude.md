# 内容提取

内容提取模块负责网页内容的智能提取、解析和结构化处理，支持职位信息提取、页面解析和数据存储管理。

## 🎯 核心组件

### 1. 内容提取器 (ContentExtractor)
**文件**: [`content_extractor.py`](content_extractor.py)

**职责**: 智能网页内容提取
- 职位详情页面解析
- 结构化数据提取
- 多网站兼容性适配
- 薪资过滤器自动应用

**增强功能**:
- **薪资过滤器自动点击**: 在每次搜索前自动应用薪资过滤条件
- **多策略元素检测**: 支持JavaScript、XPath、CSS选择器多种检测方式
- **优雅错误处理**: 错误不影响主要提取流程

### 2. 页面解析器 (PageParser)
**文件**: [`page_parser.py`](page_parser.py)

**职责**: 页面结构解析和导航
- HTML结构分析
- 页面元素定位
- 增强的下一页导航
- 页面状态验证

**核心特性**:
- **增强导航机制**: 支持导航失败时的自动恢复
- **多种导航策略**: 直接页码点击、顺序导航、页面验证
- **状态记录**: 完整的页面状态跟踪和验证

### 3. 数据存储管理 (DataStorage)
**文件**: [`data_storage.py`](data_storage.py)

**职责**: 提取数据的存储和管理
- 数据格式标准化
- 批量存储优化
- 重复数据检测
- 数据质量验证

### 4. URL提取器 (URLExtractor)
**文件**: [`url_extractor.py`](url_extractor.py)

**职责**: URL提取和处理
- 职位详情URL提取
- URL标准化处理
- 链接有效性验证
- URL去重和过滤

## 🚀 使用示例

### 基本提取操作
```python
from src.extraction.content_extractor import ContentExtractor

extractor = ContentExtractor(driver, config)

# 提取当前页面职位信息
jobs = extractor.extract_jobs_from_page()

# 提取单个职位详情
job_details = extractor.extract_job_details(job_url)
```

---

**Navigation**: [← Search Automation](../search/claude.md) | [Core Modules →](../core/claude.md)