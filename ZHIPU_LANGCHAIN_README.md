# 智谱GLM-4.5-Flash + LangChain 使用指南

这个示例展示了如何使用LangChain框架调用智谱AI的GLM-4.5-Flash模型。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements_zhipu.txt
```

### 2. 设置API密钥

获取智谱AI的API密钥：
1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/)
2. 注册并登录
3. 创建API密钥

设置环境变量：

**Windows:**
```cmd
set ZHIPU_API_KEY=your_api_key_here
```

**Linux/Mac:**
```bash
export ZHIPU_API_KEY=your_api_key_here
```

### 3. 运行示例

```bash
python langchain_zhipu_example.py
```

## 示例功能

该示例包含以下功能演示：

1. **基础聊天** - 简单的问答对话
2. **提示模板** - 使用LangChain的提示模板功能
3. **带记忆对话** - 多轮对话，能记住上下文
4. **代码生成** - 生成Python代码
5. **批量处理** - 批量进行情感分析
6. **流式输出** - 实时流式显示回答

## 核心代码片段

### 基础设置

```python
from langchain_community.chat_models import ChatZhipuAI

# 创建智谱AI模型实例
llm = ChatZhipuAI(
    model="glm-4-flash",  # GLM-4.5-Flash
    api_key=os.getenv("ZHIPU_API_KEY"),
    temperature=0.7,
    max_tokens=1024,
)
```

### 简单调用

```python
from langchain_core.messages import HumanMessage

response = llm.invoke([
    HumanMessage(content="你好，请介绍一下Python")
])
print(response.content)
```

### 使用提示模板

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个{domain}专家"),
    ("human", "{question}")
])

chain = prompt | llm | StrOutputParser()

response = chain.invoke({
    "domain": "Python编程",
    "question": "什么是装饰器？"
})
```

## 注意事项

1. 确保API密钥有效且有足够的额度
2. GLM-4.5-Flash在API中的模型名称是 `glm-4-flash`
3. 网络连接需要能访问智谱AI的API服务
4. 建议在生产环境中使用 `.env` 文件管理API密钥

## 故障排除

如果遇到问题，请检查：

1. **API密钥错误**: 确认环境变量设置正确
2. **网络问题**: 确认能访问 `https://open.bigmodel.cn`
3. **依赖问题**: 确认安装了所有必需的包
4. **额度不足**: 检查智谱AI账户余额

## 更多功能

LangChain提供了丰富的功能，你可以进一步探索：

- **RAG (检索增强生成)**: 结合向量数据库进行知识问答
- **Agent**: 创建能使用工具的智能代理
- **Chain**: 构建复杂的处理链路
- **Memory**: 各种类型的对话记忆管理

参考LangChain官方文档了解更多：https://python.langchain.com/