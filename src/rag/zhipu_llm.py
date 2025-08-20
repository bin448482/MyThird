"""
智谱GLM LangChain适配器

将智谱GLM集成到LangChain框架中，提供统一的LLM接口。
"""

from typing import Any, Dict, List, Optional, Union
from langchain.llms.base import LLM
from langchain.callbacks.manager import CallbackManagerForLLMRun
import requests
import json
import logging

logger = logging.getLogger(__name__)


class ZhipuGLM(LLM):
    """智谱GLM LangChain适配器"""
    
    api_key: str
    model: str = "glm-4-flash"
    temperature: float = 0.7
    max_tokens: int = 1024
    base_url: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    
    def __init__(self, api_key: str, **kwargs):
        """
        初始化智谱GLM
        
        Args:
            api_key: 智谱AI的API密钥
            **kwargs: 其他参数
        """
        super().__init__(api_key=api_key, **kwargs)
    
    @property
    def _llm_type(self) -> str:
        """返回LLM类型"""
        return "zhipu_glm"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """
        调用智谱GLM API
        
        Args:
            prompt: 输入提示
            stop: 停止词列表
            run_manager: 回调管理器
            **kwargs: 其他参数
            
        Returns:
            str: 模型回复
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
            # 添加停止词
            if stop:
                data["stop"] = stop
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                
                # 如果有回调管理器，记录token使用情况
                if run_manager:
                    usage = result.get("usage", {})
                    run_manager.on_llm_end({
                        "generations": [[{"text": content}]],
                        "llm_output": {
                            "token_usage": usage,
                            "model_name": self.model
                        }
                    })
                
                return content
            else:
                raise ValueError(f"未收到有效回复: {result}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"智谱GLM API请求失败: {e}")
            raise ValueError(f"API请求失败: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            raise ValueError(f"响应解析失败: {e}")
        except Exception as e:
            logger.error(f"智谱GLM调用失败: {e}")
            raise ValueError(f"模型调用失败: {e}")
    
    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """
        异步调用智谱GLM API
        
        Args:
            prompt: 输入提示
            stop: 停止词列表
            run_manager: 回调管理器
            **kwargs: 其他参数
            
        Returns:
            str: 模型回复
        """
        # 对于简单实现，直接调用同步方法
        # 在生产环境中，应该使用真正的异步HTTP客户端
        return self._call(prompt, stop, run_manager, **kwargs)
    
    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """返回识别参数"""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "api_key": f"***{self.api_key[-4:]}" if self.api_key else None
        }


class ZhipuChatGLM(ZhipuGLM):
    """智谱ChatGLM聊天模型适配器"""
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """
        调用智谱ChatGLM API（聊天格式）
        
        Args:
            prompt: 输入提示
            stop: 停止词列表
            run_manager: 回调管理器
            **kwargs: 其他参数
            
        Returns:
            str: 模型回复
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 解析prompt为消息格式
            messages = self._parse_prompt_to_messages(prompt)
            
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
            if stop:
                data["stop"] = stop
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                raise ValueError(f"未收到有效回复: {result}")
                
        except Exception as e:
            logger.error(f"智谱ChatGLM调用失败: {e}")
            raise ValueError(f"模型调用失败: {e}")
    
    def _parse_prompt_to_messages(self, prompt: str) -> List[Dict[str, str]]:
        """
        将prompt解析为消息格式
        
        Args:
            prompt: 输入提示
            
        Returns:
            List[Dict]: 消息列表
        """
        # 简单的解析逻辑，可以根据需要扩展
        if "Human:" in prompt and "Assistant:" in prompt:
            # 解析对话格式
            messages = []
            parts = prompt.split("Human:")
            
            for part in parts[1:]:  # 跳过第一个空部分
                if "Assistant:" in part:
                    human_part, assistant_part = part.split("Assistant:", 1)
                    messages.append({"role": "user", "content": human_part.strip()})
                    messages.append({"role": "assistant", "content": assistant_part.strip()})
                else:
                    messages.append({"role": "user", "content": part.strip()})
            
            return messages
        else:
            # 单轮对话
            return [{"role": "user", "content": prompt}]


def create_zhipu_llm(api_key: str, model: str = "glm-4-flash", **kwargs) -> ZhipuGLM:
    """
    创建智谱GLM实例的工厂函数
    
    Args:
        api_key: API密钥
        model: 模型名称
        **kwargs: 其他参数
        
    Returns:
        ZhipuGLM: 智谱GLM实例
    """
    return ZhipuGLM(
        api_key=api_key,
        model=model,
        **kwargs
    )


def create_zhipu_chat_llm(api_key: str, model: str = "glm-4-flash", **kwargs) -> ZhipuChatGLM:
    """
    创建智谱ChatGLM实例的工厂函数
    
    Args:
        api_key: API密钥
        model: 模型名称
        **kwargs: 其他参数
        
    Returns:
        ZhipuChatGLM: 智谱ChatGLM实例
    """
    return ZhipuChatGLM(
        api_key=api_key,
        model=model,
        **kwargs
    )