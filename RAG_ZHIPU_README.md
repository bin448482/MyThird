# 智谱GLM + RAG系统使用指南

本文档介绍如何使用重构后的RAG系统，该系统已将LLM从OpenAI更新为智谱GLM-4.5-Flash。

## 🚀 系统概述

重构后的RAG系统具备以下特性：
- **智谱GLM集成**: 使用智谱GLM-4.5-Flash作为核心LLM
- **向量存储**: ChromaDB向量数据库存储职位信息
- **语义搜索**: 基于向量相似度的智能搜索
- **结构化提取**: LLM驱动的职位信息结构化
- **问答系统**: 基于RAG的智能问答

## 📁 文件结构

```
src/rag/
├── zhipu_llm.py          # 智谱GLM LangChain适配器
├── vector_manager.py     # ChromaDB向量存储管理器
├── job_processor.py      # 职位数据处理器
├── document_creator.py   # 文档创建器
├── rag_chain.py         # RAG检索问答链
└── semantic_search.py   # 语义搜索引擎

test_rag_vector_storage.py    # RAG系统测试脚本
requirements_rag_test.txt     # 测试依赖包
```

## 🔧 安装依赖

```bash
pip install -r requirements_rag_test.txt
```

## 🏃‍♂️ 快速开始

### 1. 运行完整测试

```bash
python test_rag_vector_storage.py
```

测试脚本会执行以下步骤：
1. 初始化RAG组件
2. 加载职位JSON数据
3. 结构化提取职位信息
4. 保存到向量数据库
5. 测试语义搜索
6. 测试RAG问答

### 2. 编程接口使用

#### 基础使用示例

```python
import asyncio
from src.rag.vector_manager import ChromaDBManager
from src.rag.job_processor import LangChainJobProcessor
from src.rag.document_creator import DocumentCreator
from src.rag.rag_chain import JobRAGSystem

# 配置
API_KEY = "your_zhipu_api_key"
config = {
    'vectorstore': {
        'persist_directory': './chroma_db',
        'collection_name': 'job_positions'
    },
    'llm': {
        'api_key': API_KEY,
        'model': 'glm-4-flash',
        'temperature': 0.1
    }
}

async def main():
    # 1. 初始化组件
    vector_manager = ChromaDBManager(config['vectorstore'])
    job_processor = LangChainJobProcessor(api_key=API_KEY)
    document_creator = DocumentCreator()
    rag_system = JobRAGSystem(vector_manager, API_KEY, config)
    
    # 2. 处理职位数据
    job_data = {"description": "AI工程师职位..."}
    job_structure = await job_processor.process_job_data(job_data)
    
    # 3. 创建文档并存储
    documents = document_creator.create_job_documents(job_structure)
    doc_ids = vector_manager.add_job_documents(documents)
    
    # 4. 问答查询
    answer = await rag_system.ask_question("这个职位需要什么技能？")
    print(answer['answer'])

asyncio.run(main())
```

#### 语义搜索示例

```python
from src.rag.semantic_search import SemanticSearchEngine

# 初始化搜索引擎
search_engine = SemanticSearchEngine(vector_manager, config)

# 执行搜索
results = search_engine.search(
    query="Python开发工程师",
    strategy='similarity',
    k=5
)

for result in results:
    print(f"相似度: {result['similarity_score']:.3f}")
    print(f"内容: {result['content']}")
```

## 🔍 核心功能

### 1. 职位数据结构化提取

```python
# 使用智谱GLM进行结构化提取
job_structure = await job_processor.process_job_data({
    "description": "职位描述文本...",
    "title": "AI工程师",
    "company": "某科技公司"
})

print(job_structure.job_title)      # 职位名称
print(job_structure.skills)        # 技能要求列表
print(job_structure.responsibilities)  # 职责列表
```

### 2. 向量数据库操作

```python
# 添加文档
doc_ids = vector_manager.add_job_documents(documents, job_id="job_001")

# 搜索相似职位
similar_docs = vector_manager.search_similar_jobs("Python开发", k=5)

# 获取统计信息
stats = vector_manager.get_collection_stats()
print(f"文档总数: {stats['document_count']}")
```

### 3. RAG问答系统

```python
# 问答查询
answer_result = await rag_system.ask_question(
    question="这个职位的薪资范围是多少？",
    k=5
)

print(f"回答: {answer_result['answer']}")
print(f"置信度: {answer_result['confidence']}")
print(f"参考文档: {len(answer_result['source_documents'])}")
```

### 4. 职位匹配

```python
# 查找匹配职位
user_profile = "3年Python开发经验，熟悉机器学习"
matching_jobs = await rag_system.find_matching_jobs(
    user_profile=user_profile,
    k=10
)

for job in matching_jobs:
    print(f"职位: {job['job_title']}")
    print(f"匹配度: {job['match_score']:.3f}")
    print(f"匹配原因: {job['match_reasons']}")
```

## ⚙️ 配置选项

### 智谱GLM配置

```python
llm_config = {
    'api_key': 'your_api_key',
    'model': 'glm-4-flash',        # 模型名称
    'temperature': 0.1,            # 温度参数
    'max_tokens': 2000            # 最大token数
}
```

### 向量数据库配置

```python
vectorstore_config = {
    'persist_directory': './chroma_db',
    'collection_name': 'job_positions'
}
```

### 嵌入模型配置

```python
embeddings_config = {
    'model_name': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
    'device': 'cpu',
    'normalize_embeddings': True
}
```

## 🧪 测试结果示例

运行测试脚本后，你会看到类似的输出：

```
🚀 RAG向量存储功能测试
============================================================

📋 步骤1: 初始化RAG组件
✅ 向量存储管理器初始化完成
✅ 职位处理器初始化完成
✅ 文档创建器初始化完成
✅ RAG系统初始化完成
✅ 语义搜索引擎初始化完成

📋 步骤2: 加载职位数据
📂 成功加载职位数据: fixed_job_detail_result.json

📋 步骤3: 测试职位数据处理和向量存储
✅ 职位结构化提取完成: 上海AI工程师
✅ 创建了 6 个文档对象
✅ 成功保存 6 个文档到向量数据库

📋 步骤4: 测试向量搜索功能
🔎 搜索查询: AI工程师职位要求
  📋 找到 3 个相关结果
    1. 相似度: 0.856
       内容: 职位：上海AI工程师，公司：中国软件与技术服务股份有限公司...
       类型: overview

📋 步骤5: 测试RAG问答功能
❓ 问题: 这个职位需要什么技能？
  💡 回答: 根据职位信息，这个AI工程师职位需要以下技能：...
  📊 置信度: 0.892
  📚 参考文档数: 5

🎉 所有测试通过！RAG向量存储功能正常工作
```

## 🔧 故障排除

### 常见问题

1. **API密钥错误**
   - 确认智谱GLM API密钥正确
   - 检查API密钥是否有足够的额度

2. **依赖包问题**
   - 确保安装了所有必需的依赖包
   - 使用 `pip install -r requirements_rag_test.txt`

3. **向量数据库问题**
   - 确保有足够的磁盘空间
   - 检查ChromaDB版本兼容性

4. **嵌入模型下载**
   - 首次运行会下载嵌入模型
   - 确保网络连接正常

### 调试模式

启用详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 性能优化

1. **批量处理**: 一次处理多个职位数据
2. **缓存机制**: 缓存常用查询结果
3. **异步处理**: 使用异步方法提高并发性能
4. **索引优化**: 定期优化向量数据库索引

## 🔮 下一步

- 集成到完整的求职系统中
- 添加更多的搜索策略
- 实现实时数据更新
- 添加用户反馈机制
- 优化匹配算法

## 📞 支持

如果遇到问题，请检查：
1. API密钥配置
2. 依赖包版本
3. 网络连接
4. 日志输出信息