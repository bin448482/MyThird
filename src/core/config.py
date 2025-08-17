"""
配置管理模块

负责加载和管理应用程序配置
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any

from .exceptions import ConfigError


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.config = {}
    
    def load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            配置字典
            
        Raises:
            ConfigError: 配置文件不存在或格式错误
        """
        try:
            if not self.config_path.exists():
                raise ConfigError(f"配置文件不存在: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            # 验证配置
            self._validate_config()
            
            # 处理环境变量替换
            self._process_env_vars()
            
            return self.config
            
        except yaml.YAMLError as e:
            raise ConfigError(f"配置文件格式错误: {e}")
        except Exception as e:
            raise ConfigError(f"加载配置文件失败: {e}")
    
    def _validate_config(self):
        """验证配置文件的必要字段"""
        required_sections = ['app', 'database', 'websites', 'selenium', 'crawler']
        
        for section in required_sections:
            if section not in self.config:
                raise ConfigError(f"配置文件缺少必要部分: {section}")
        
        # 验证网站配置
        websites = self.config.get('websites', {})
        for website_name, website_config in websites.items():
            if not website_config.get('enabled', False):
                continue
                
            required_fields = ['base_url', 'login_url', 'search_url', 'login_check_element']
            for field in required_fields:
                if field not in website_config:
                    raise ConfigError(f"网站 {website_name} 配置缺少字段: {field}")
    
    def _process_env_vars(self):
        """处理环境变量替换"""
        def replace_env_vars(obj):
            if isinstance(obj, dict):
                return {k: replace_env_vars(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_env_vars(item) for item in obj]
            elif isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
                env_var = obj[2:-1]
                default_value = ""
                if ':' in env_var:
                    env_var, default_value = env_var.split(':', 1)
                return os.getenv(env_var, default_value)
            else:
                return obj
        
        self.config = replace_env_vars(self.config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，支持点号分隔的嵌套键
        
        Args:
            key: 配置键，支持 'section.subsection.key' 格式
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_website_config(self, website: str) -> Dict[str, Any]:
        """
        获取指定网站的配置
        
        Args:
            website: 网站名称
            
        Returns:
            网站配置字典
            
        Raises:
            ConfigError: 网站配置不存在或未启用
        """
        websites = self.config.get('websites', {})
        
        if website not in websites:
            raise ConfigError(f"网站配置不存在: {website}")
        
        website_config = websites[website]
        
        if not website_config.get('enabled', False):
            raise ConfigError(f"网站未启用: {website}")
        
        return website_config
    
    def create_example_config(self, output_path: str = "config/config.example.yaml"):
        """
        创建示例配置文件
        
        Args:
            output_path: 输出路径
        """
        example_config = {
            'app': {
                'name': 'Resume Auto Submitter',
                'version': '1.0.0',
                'debug': False
            },
            'database': {
                'path': './data/jobs.db'
            },
            'websites': {
                'zhilian': {
                    'enabled': True,
                    'base_url': 'https://www.zhaopin.com',
                    'login_url': 'https://passport.zhaopin.com/login',
                    'search_url': 'https://sou.zhaopin.com',
                    'login_check_element': '.user-info',
                    'submit_button_selector': '.btn-apply'
                },
                'qiancheng': {
                    'enabled': True,
                    'base_url': 'https://www.51job.com',
                    'login_url': 'https://login.51job.com',
                    'search_url': 'https://search.51job.com',
                    'login_check_element': '.login-info',
                    'submit_button_selector': '.apply-btn'
                },
                'boss': {
                    'enabled': True,
                    'base_url': 'https://www.zhipin.com',
                    'login_url': 'https://login.zhipin.com',
                    'search_url': 'https://www.zhipin.com/c101010100',
                    'login_check_element': '.user-name',
                    'submit_button_selector': '.btn-startchat'
                }
            },
            'selenium': {
                'browser': 'chrome',
                'headless': False,
                'window_size': '1920,1080',
                'page_load_timeout': 30,
                'element_wait_timeout': 10,
                'implicit_wait': 5
            },
            'crawler': {
                'delay_min': 2,
                'delay_max': 5,
                'max_retries': 3,
                'login_wait_timeout': 300
            },
            'anti_bot': {
                'random_delay': True,
                'mouse_simulation': True,
                'user_agent_rotation': True,
                'scroll_simulation': True
            },
            'ai': {
                'provider': 'openai',
                'model': 'gpt-3.5-turbo',
                'api_key': '${OPENAI_API_KEY:your-api-key-here}',
                'base_url': '',
                'temperature': 0.1,
                'max_tokens': 1000
            },
            'matching': {
                'weights': {
                    'skills': 0.5,
                    'experience': 0.3,
                    'salary': 0.2
                },
                'thresholds': {
                    'auto_submit': 0.8,
                    'manual_review': 0.6,
                    'skip': 0.3
                }
            },
            'resume': {
                'skills': ['Python', 'Java', 'React', 'Node.js'],
                'experience_years': 3,
                'expected_salary_min': 15000,
                'expected_salary_max': 25000,
                'preferred_locations': ['上海']
            },
            'logging': {
                'level': 'INFO',
                'file_path': './logs/app.log',
                'console_output': True
            }
        }
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(example_config, f, default_flow_style=False, 
                     allow_unicode=True, indent=2)