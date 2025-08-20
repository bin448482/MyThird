"""
自定义异常类

定义项目中使用的各种自定义异常
"""


class ResumeSubmitterError(Exception):
    """基础异常类"""
    pass


class ConfigError(ResumeSubmitterError):
    """配置相关异常"""
    pass


class WebDriverError(ResumeSubmitterError):
    """WebDriver相关异常"""
    pass


class LoginError(ResumeSubmitterError):
    """登录相关异常"""
    pass


class CrawlerError(ResumeSubmitterError):
    """爬虫相关异常"""
    pass


class AnalyzerError(ResumeSubmitterError):
    """分析器相关异常"""
    pass


class MatcherError(ResumeSubmitterError):
    """匹配器相关异常"""
    pass


class SubmissionError(ResumeSubmitterError):
    """投递相关异常"""
    pass


class DatabaseError(ResumeSubmitterError):
    """数据库相关异常"""
    pass


class NetworkError(ResumeSubmitterError):
    """网络相关异常"""
    pass


class ElementNotFoundError(CrawlerError):
    """页面元素未找到异常"""
    pass


class PageLoadTimeoutError(CrawlerError):
    """页面加载超时异常"""
    pass


class LoginTimeoutError(LoginError):
    """登录超时异常"""
    pass


class PageLoadTimeoutError(CrawlerError):
    """页面加载超时异常"""
    pass


class APIError(AnalyzerError):
    """API调用异常"""
    pass


class RateLimitError(APIError):
    """API速率限制异常"""
    pass


class SessionError(ResumeSubmitterError):
    """会话相关异常"""
    pass


class ContentExtractionError(ResumeSubmitterError):
    """内容提取相关异常"""
    pass


class PageParseError(ContentExtractionError):
    """页面解析异常"""
    pass


class DataStorageError(ResumeSubmitterError):
    """数据存储异常"""
    pass


class RAGSystemError(ResumeSubmitterError):
    """RAG系统相关异常"""
    pass


class VectorStoreError(RAGSystemError):
    """向量存储相关异常"""
    pass


class DocumentProcessingError(RAGSystemError):
    """文档处理相关异常"""
    pass


class LLMProcessingError(RAGSystemError):
    """LLM处理相关异常"""
    pass