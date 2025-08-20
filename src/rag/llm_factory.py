"""
统一的LLM工厂模式

支持多种LLM提供商的统一接口，便于切换不同的语言模型。
"""

from typing import Any, Dict, Optional, Union
from langchain.llms.base import LLM
from langchain.callbacks.manager import CallbackManagerForLLMRun
import requests
import json
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseLLMAdapter(LLM, ABC):
    """LLM适配器基类"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    @property
    @abstractmethod
    def _llm_type(self) -> str:
        """返回LLM类型"""
        pass
    
    @abstractmethod
    def _call(
        self,
        prompt: str,
        stop: Optional[list] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """调用LLM"""
        pass


class ZhipuGLMAdapter(BaseLLMAdapter):
    """智谱GLM适配器"""
    
    api_key: str
    model: str = "glm-4-flash"
    temperature: float = 0.7
    max_tokens: int = 1024
    base_url: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
    
    @property
    def _llm_type(self) -> str:
        return "zhipu_glm"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[list] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
            if stop:
                data["stop"] = stop
            
            response = requests.post(self.base_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                raise ValueError(f"未收到有效回复: {result}")
                
        except Exception as e:
            logger.error(f"智谱GLM调用失败: {e}")
            raise ValueError(f"模型调用失败: {e}")
    
    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "api_key": f"***{self.api_key[-4:]}" if self.api_key else None
        }


class OllamaAdapter(BaseLLMAdapter):
    """Ollama本地模型适配器"""
    
    model: str = "llama2"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.7
    max_tokens: int = 1024
    
    def __init__(self, model: str = "llama2", base_url: str = "http://localhost:11434", **kwargs):
        super().__init__(model=model, base_url=base_url, **kwargs)
    
    @property
    def _llm_type(self) -> str:
        return "ollama"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[list] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        try:
            url = f"{self.base_url}/api/generate"
            
            data = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens
                }
            }
            
            if stop:
                data["options"]["stop"] = stop
            
            response = requests.post(url, json=data, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            if "response" in result:
                return result["response"]
            else:
                raise ValueError(f"未收到有效回复: {result}")
                
        except Exception as e:
            logger.error(f"Ollama调用失败: {e}")
            raise ValueError(f"模型调用失败: {e}")
    
    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }


class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI模型适配器"""
    
    api_key: str
    model: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: int = 1024
    base_url: str = "https://api.openai.com/v1/chat/completions"
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
    
    @property
    def _llm_type(self) -> str:
        return "openai"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[list] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
            if stop:
                data["stop"] = stop
            
            response = requests.post(self.base_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                raise ValueError(f"未收到有效回复: {result}")
                
        except Exception as e:
            logger.error(f"OpenAI调用失败: {e}")
            raise ValueError(f"模型调用失败: {e}")
    
    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "api_key": f"***{self.api_key[-4:]}" if self.api_key else None
        }


class ClaudeAdapter(BaseLLMAdapter):
    """Claude模型适配器"""
    
    api_key: str
    model: str = "claude-3-sonnet-20240229"
    temperature: float = 0.7
    max_tokens: int = 1024
    base_url: str = "https://api.anthropic.com/v1/messages"
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
    
    @property
    def _llm_type(self) -> str:
        return "claude"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[list] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        try:
            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            data = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            if stop:
                data["stop_sequences"] = stop
            
            response = requests.post(self.base_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if "content" in result and len(result["content"]) > 0:
                return result["content"][0]["text"]
            else:
                raise ValueError(f"未收到有效回复: {result}")
                
        except Exception as e:
            logger.error(f"Claude调用失败: {e}")
            raise ValueError(f"模型调用失败: {e}")
    
    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "api_key": f"***{self.api_key[-4:]}" if self.api_key else None
        }


class LLMFactory:
    """LLM工厂类"""
    
    _adapters = {
        "zhipu": ZhipuGLMAdapter,
        "ollama": OllamaAdapter,
        "openai": OpenAIAdapter,
        "claude": ClaudeAdapter
    }
    
    @classmethod
    def create_llm(cls, provider: str, **kwargs) -> BaseLLMAdapter:
        """
        创建LLM实例
        
        Args:
            provider: LLM提供商 ("zhipu", "ollama", "openai", "claude")
            **kwargs: 模型参数
            
        Returns:
            BaseLLMAdapter: LLM适配器实例
        """
        if provider not in cls._adapters:
            raise ValueError(f"不支持的LLM提供商: {provider}. 支持的提供商: {list(cls._adapters.keys())}")
        
        adapter_class = cls._adapters[provider]
        return adapter_class(**kwargs)
    
    @classmethod
    def register_adapter(cls, provider: str, adapter_class: type):
        """
        注册新的LLM适配器
        
        Args:
            provider: 提供商名称
            adapter_class: 适配器类
        """
        if not issubclass(adapter_class, BaseLLMAdapter):
            raise ValueError("适配器类必须继承自BaseLLMAdapter")
        
        cls._adapters[provider] = adapter_class
        logger.info(f"注册LLM适配器: {provider}")
    
    @classmethod
    def get_supported_providers(cls) -> list:
        """获取支持的LLM提供商列表"""
        return list(cls._adapters.keys())


# 便捷函数
def create_llm(provider: str, **kwargs) -> BaseLLMAdapter:
    """
    创建LLM实例的便捷函数
    
    Args:
        provider: LLM提供商
        **kwargs: 模型参数
        
    Returns:
        BaseLLMAdapter: LLM适配器实例
    """
    return LLMFactory.create_llm(provider, **kwargs)


# 预定义配置
LLM_CONFIGS = {
    "zhipu_default": {
        "provider": "zhipu",
        "model": "glm-4-flash",
        "temperature": 0.1,
        "max_tokens": 2000
    },
    "ollama_llama2": {
        "provider": "ollama",
        "model": "llama2",
        "base_url": "http://localhost:11434",
        "temperature": 0.1,
        "max_tokens": 2000
    },
    "ollama_qwen": {
        "provider": "ollama",
        "model": "qwen:7b",
        "base_url": "http://localhost:11434",
        "temperature": 0.1,
        "max_tokens": 2000
    },
    "openai_gpt35": {
        "provider": "openai",
        "model": "gpt-3.5-turbo",
        "temperature": 0.1,
        "max_tokens": 2000
    },
    "claude_sonnet": {
        "provider": "claude",
        "model": "claude-3-sonnet-20240229",
        "temperature": 0.1,
        "max_tokens": 2000
    }
}


def create_llm_from_config(config_name: str, **override_params) -> BaseLLMAdapter:
    """
    从预定义配置创建LLM实例
    
    Args:
        config_name: 配置名称
        **override_params: 覆盖参数
        
    Returns:
        BaseLLMAdapter: LLM适配器实例
    """
    if config_name not in LLM_CONFIGS:
        raise ValueError(f"未找到配置: {config_name}. 可用配置: {list(LLM_CONFIGS.keys())}")
    
    config = LLM_CONFIGS[config_name].copy()
    provider = config.pop("provider")
    
    # 合并覆盖参数
    config.update(override_params)
    
    return create_llm(provider, **config)