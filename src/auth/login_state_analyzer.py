"""
登录状态分析工具

用于分析和调试登录状态，帮助优化登录检测逻辑
"""

import json
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, NoSuchElementException


class QianchengLoginStateAnalyzer:
    """前程无忧登录状态分析器"""
    
    def __init__(self, driver: webdriver.Chrome, config: dict):
        """
        初始化分析器
        
        Args:
            driver: WebDriver实例
            config: 配置字典
        """
        self.driver = driver
        self.config = config
        self.login_config = config.get('login', {})
        self.logger = logging.getLogger(__name__)
        
        # 分析结果存储
        self.analysis_results = {
            'timestamp': datetime.now().isoformat(),
            'current_url': '',
            'page_title': '',
            'login_indicators': {},
            'page_elements': {},
            'cookies_analysis': {},
            'storage_analysis': {},
            'network_analysis': {},
            'recommendations': []
        }
    
    def analyze_full_login_state(self) -> Dict[str, Any]:
        """
        执行完整的登录状态分析
        
        Returns:
            完整的分析结果字典
        """
        try:
            self.logger.info("🔍 开始完整登录状态分析")
            
            # 基本页面信息
            self._analyze_basic_page_info()
            
            # 登录指示器分析
            self._analyze_login_indicators()
            
            # 页面元素分析
            self._analyze_page_elements()
            
            # Cookie分析
            self._analyze_cookies()
            
            # 存储分析
            self._analyze_storage()
            
            # 网络状态分析
            self._analyze_network_state()
            
            # 生成建议
            self._generate_recommendations()
            
            self.logger.info("✅ 登录状态分析完成")
            return self.analysis_results
            
        except Exception as e:
            self.logger.error(f"❌ 登录状态分析失败: {e}")
            self.analysis_results['error'] = str(e)
            return self.analysis_results
    
    def _analyze_basic_page_info(self) -> None:
        """分析基本页面信息"""
        try:
            self.analysis_results['current_url'] = self.driver.current_url
            self.analysis_results['page_title'] = self.driver.title
            self.analysis_results['window_size'] = self.driver.get_window_size()
            self.analysis_results['user_agent'] = self.driver.execute_script("return navigator.userAgent;")
            
            self.logger.debug(f"页面URL: {self.analysis_results['current_url']}")
            self.logger.debug(f"页面标题: {self.analysis_results['page_title']}")
            
        except Exception as e:
            self.logger.warning(f"分析基本页面信息失败: {e}")
    
    def _analyze_login_indicators(self) -> None:
        """分析登录指示器"""
        try:
            indicators = {
                'success_indicators': {},
                'failure_indicators': {},
                'summary': {
                    'found_success': 0,
                    'found_failure': 0,
                    'login_state': 'unknown'
                }
            }
            
            # 检查成功指示器
            success_selectors = self.login_config.get('success_indicators', [])
            for selector in success_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    visible_elements = [e for e in elements if e.is_displayed()]
                    
                    indicators['success_indicators'][selector] = {
                        'found': len(elements),
                        'visible': len(visible_elements),
                        'texts': [e.text.strip() for e in visible_elements if e.text.strip()],
                        'attributes': [self._get_element_attributes(e) for e in visible_elements[:3]]
                    }
                    
                    if visible_elements:
                        indicators['summary']['found_success'] += 1
                        
                except Exception as e:
                    indicators['success_indicators'][selector] = {'error': str(e)}
            
            # 检查失败指示器
            failure_selectors = self.login_config.get('failure_indicators', [])
            for selector in failure_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    visible_elements = [e for e in elements if e.is_displayed()]
                    
                    indicators['failure_indicators'][selector] = {
                        'found': len(elements),
                        'visible': len(visible_elements),
                        'texts': [e.text.strip() for e in visible_elements if e.text.strip()],
                        'attributes': [self._get_element_attributes(e) for e in visible_elements[:3]]
                    }
                    
                    if visible_elements:
                        indicators['summary']['found_failure'] += 1
                        
                except Exception as e:
                    indicators['failure_indicators'][selector] = {'error': str(e)}
            
            # 判断登录状态
            if indicators['summary']['found_success'] > 0:
                indicators['summary']['login_state'] = 'logged_in'
            elif indicators['summary']['found_failure'] > 0:
                indicators['summary']['login_state'] = 'login_failed'
            else:
                indicators['summary']['login_state'] = 'unknown'
            
            self.analysis_results['login_indicators'] = indicators
            
            self.logger.info(f"登录指示器分析: 成功指示器 {indicators['summary']['found_success']} 个, "
                           f"失败指示器 {indicators['summary']['found_failure']} 个, "
                           f"状态: {indicators['summary']['login_state']}")
            
        except Exception as e:
            self.logger.warning(f"分析登录指示器失败: {e}")
    
    def _analyze_page_elements(self) -> None:
        """分析页面元素"""
        try:
            elements_info = {
                'forms': [],
                'inputs': [],
                'buttons': [],
                'links': [],
                'user_info_elements': []
            }
            
            # 分析表单
            forms = self.driver.find_elements(By.TAG_NAME, "form")
            for form in forms[:5]:  # 限制数量
                elements_info['forms'].append({
                    'action': form.get_attribute('action'),
                    'method': form.get_attribute('method'),
                    'id': form.get_attribute('id'),
                    'class': form.get_attribute('class')
                })
            
            # 分析输入框
            inputs = self.driver.find_elements(By.TAG_NAME, "input")
            for inp in inputs[:10]:  # 限制数量
                if inp.is_displayed():
                    elements_info['inputs'].append({
                        'type': inp.get_attribute('type'),
                        'name': inp.get_attribute('name'),
                        'id': inp.get_attribute('id'),
                        'placeholder': inp.get_attribute('placeholder'),
                        'value': inp.get_attribute('value')[:20] if inp.get_attribute('value') else None
                    })
            
            # 分析按钮
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons[:10]:  # 限制数量
                if btn.is_displayed():
                    elements_info['buttons'].append({
                        'text': btn.text.strip(),
                        'type': btn.get_attribute('type'),
                        'id': btn.get_attribute('id'),
                        'class': btn.get_attribute('class')
                    })
            
            # 分析可能的用户信息元素
            user_selectors = ['.user', '.username', '.member', '.profile', '[data-user]', '.welcome']
            for selector in user_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements[:3]:
                        if elem.is_displayed() and elem.text.strip():
                            elements_info['user_info_elements'].append({
                                'selector': selector,
                                'text': elem.text.strip()[:50],
                                'tag': elem.tag_name,
                                'attributes': self._get_element_attributes(elem)
                            })
                except:
                    continue
            
            self.analysis_results['page_elements'] = elements_info
            
            self.logger.debug(f"页面元素分析: 表单 {len(elements_info['forms'])} 个, "
                            f"输入框 {len(elements_info['inputs'])} 个, "
                            f"按钮 {len(elements_info['buttons'])} 个")
            
        except Exception as e:
            self.logger.warning(f"分析页面元素失败: {e}")
    
    def _analyze_cookies(self) -> None:
        """分析Cookie"""
        try:
            cookies = self.driver.get_cookies()
            
            cookie_analysis = {
                'total_count': len(cookies),
                'session_cookies': 0,
                'persistent_cookies': 0,
                'secure_cookies': 0,
                'httponly_cookies': 0,
                'important_cookies': [],
                'cookie_domains': set(),
                'cookie_paths': set()
            }
            
            # 重要Cookie关键词
            important_keywords = ['session', 'login', 'auth', 'user', 'token', 'sid', 'jsessionid']
            
            for cookie in cookies:
                # 统计类型
                if cookie.get('expiry'):
                    cookie_analysis['persistent_cookies'] += 1
                else:
                    cookie_analysis['session_cookies'] += 1
                
                if cookie.get('secure'):
                    cookie_analysis['secure_cookies'] += 1
                
                if cookie.get('httpOnly'):
                    cookie_analysis['httponly_cookies'] += 1
                
                # 收集域名和路径
                cookie_analysis['cookie_domains'].add(cookie.get('domain', ''))
                cookie_analysis['cookie_paths'].add(cookie.get('path', ''))
                
                # 检查重要Cookie
                cookie_name = cookie.get('name', '').lower()
                if any(keyword in cookie_name for keyword in important_keywords):
                    cookie_analysis['important_cookies'].append({
                        'name': cookie.get('name'),
                        'domain': cookie.get('domain'),
                        'path': cookie.get('path'),
                        'secure': cookie.get('secure', False),
                        'httpOnly': cookie.get('httpOnly', False),
                        'has_expiry': bool(cookie.get('expiry')),
                        'value_length': len(cookie.get('value', ''))
                    })
            
            # 转换set为list以便JSON序列化
            cookie_analysis['cookie_domains'] = list(cookie_analysis['cookie_domains'])
            cookie_analysis['cookie_paths'] = list(cookie_analysis['cookie_paths'])
            
            self.analysis_results['cookies_analysis'] = cookie_analysis
            
            self.logger.debug(f"Cookie分析: 总数 {cookie_analysis['total_count']}, "
                            f"重要Cookie {len(cookie_analysis['important_cookies'])} 个")
            
        except Exception as e:
            self.logger.warning(f"分析Cookie失败: {e}")
    
    def _analyze_storage(self) -> None:
        """分析本地存储"""
        try:
            storage_analysis = {
                'localStorage': {},
                'sessionStorage': {}
            }
            
            # 分析localStorage
            try:
                local_storage = self.driver.execute_script(
                    "var items = {}; "
                    "for (var i = 0; i < localStorage.length; i++) { "
                    "    var key = localStorage.key(i); "
                    "    items[key] = localStorage.getItem(key).substring(0, 100); "
                    "} "
                    "return items;"
                )
                storage_analysis['localStorage'] = {
                    'count': len(local_storage),
                    'keys': list(local_storage.keys()),
                    'sample_data': {k: v for k, v in list(local_storage.items())[:5]}
                }
            except Exception as e:
                storage_analysis['localStorage'] = {'error': str(e)}
            
            # 分析sessionStorage
            try:
                session_storage = self.driver.execute_script(
                    "var items = {}; "
                    "for (var i = 0; i < sessionStorage.length; i++) { "
                    "    var key = sessionStorage.key(i); "
                    "    items[key] = sessionStorage.getItem(key).substring(0, 100); "
                    "} "
                    "return items;"
                )
                storage_analysis['sessionStorage'] = {
                    'count': len(session_storage),
                    'keys': list(session_storage.keys()),
                    'sample_data': {k: v for k, v in list(session_storage.items())[:5]}
                }
            except Exception as e:
                storage_analysis['sessionStorage'] = {'error': str(e)}
            
            self.analysis_results['storage_analysis'] = storage_analysis
            
            self.logger.debug(f"存储分析: localStorage {storage_analysis['localStorage'].get('count', 0)} 项, "
                            f"sessionStorage {storage_analysis['sessionStorage'].get('count', 0)} 项")
            
        except Exception as e:
            self.logger.warning(f"分析存储失败: {e}")
    
    def _analyze_network_state(self) -> None:
        """分析网络状态"""
        try:
            network_analysis = {
                'current_url': self.driver.current_url,
                'url_analysis': {},
                'redirect_chain': [],
                'response_time': None
            }
            
            # URL分析
            from urllib.parse import urlparse
            parsed_url = urlparse(self.driver.current_url)
            network_analysis['url_analysis'] = {
                'scheme': parsed_url.scheme,
                'netloc': parsed_url.netloc,
                'path': parsed_url.path,
                'params': parsed_url.params,
                'query': parsed_url.query,
                'fragment': parsed_url.fragment
            }
            
            # 尝试获取性能信息
            try:
                performance = self.driver.execute_script(
                    "return window.performance && window.performance.timing ? "
                    "window.performance.timing : null;"
                )
                if performance:
                    load_time = performance.get('loadEventEnd', 0) - performance.get('navigationStart', 0)
                    network_analysis['response_time'] = load_time
            except:
                pass
            
            self.analysis_results['network_analysis'] = network_analysis
            
        except Exception as e:
            self.logger.warning(f"分析网络状态失败: {e}")
    
    def _generate_recommendations(self) -> None:
        """生成优化建议"""
        try:
            recommendations = []
            
            # 基于登录指示器分析的建议
            login_indicators = self.analysis_results.get('login_indicators', {})
            summary = login_indicators.get('summary', {})
            
            if summary.get('found_success') == 0 and summary.get('found_failure') == 0:
                recommendations.append({
                    'type': 'login_indicators',
                    'priority': 'high',
                    'message': '未找到任何登录指示器，建议检查选择器配置',
                    'suggestion': '分析页面元素，更新success_indicators和failure_indicators配置'
                })
            
            if summary.get('found_success') > 3:
                recommendations.append({
                    'type': 'login_indicators',
                    'priority': 'medium',
                    'message': f'找到过多成功指示器({summary["found_success"]}个)，可能影响性能',
                    'suggestion': '优化选择器，保留最可靠的指示器'
                })
            
            # 基于Cookie分析的建议
            cookies_analysis = self.analysis_results.get('cookies_analysis', {})
            if cookies_analysis.get('total_count', 0) == 0:
                recommendations.append({
                    'type': 'cookies',
                    'priority': 'high',
                    'message': '未找到任何Cookie，可能影响会话保存',
                    'suggestion': '检查网站是否正常设置Cookie'
                })
            
            if len(cookies_analysis.get('important_cookies', [])) == 0:
                recommendations.append({
                    'type': 'cookies',
                    'priority': 'medium',
                    'message': '未找到重要的认证相关Cookie',
                    'suggestion': '检查是否有session、auth等关键Cookie'
                })
            
            # 基于存储分析的建议
            storage_analysis = self.analysis_results.get('storage_analysis', {})
            local_count = storage_analysis.get('localStorage', {}).get('count', 0)
            session_count = storage_analysis.get('sessionStorage', {}).get('count', 0)
            
            if local_count == 0 and session_count == 0:
                recommendations.append({
                    'type': 'storage',
                    'priority': 'low',
                    'message': '未使用本地存储，会话恢复可能受限',
                    'suggestion': '考虑是否需要保存localStorage和sessionStorage'
                })
            
            self.analysis_results['recommendations'] = recommendations
            
            self.logger.info(f"生成了 {len(recommendations)} 条优化建议")
            
        except Exception as e:
            self.logger.warning(f"生成建议失败: {e}")
    
    def _get_element_attributes(self, element) -> Dict[str, str]:
        """获取元素的重要属性"""
        try:
            attrs = {}
            important_attrs = ['id', 'class', 'name', 'type', 'href', 'src', 'data-*']
            
            for attr in important_attrs:
                value = element.get_attribute(attr)
                if value:
                    attrs[attr] = value[:100]  # 限制长度
            
            return attrs
        except:
            return {}
    
    def save_analysis_report(self, filepath: Optional[str] = None) -> str:
        """
        保存分析报告到文件
        
        Args:
            filepath: 保存路径，如果为None则自动生成
            
        Returns:
            保存的文件路径
        """
        try:
            if filepath is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = f"logs/login_analysis_{timestamp}.json"
            
            # 确保目录存在
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            # 保存报告
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.analysis_results, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"📄 分析报告已保存到: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"保存分析报告失败: {e}")
            return ""
    
    def generate_summary_report(self) -> str:
        """
        生成摘要报告
        
        Returns:
            摘要报告字符串
        """
        try:
            summary_lines = [
                "=" * 60,
                "🔍 登录状态分析摘要报告",
                "=" * 60,
                f"分析时间: {self.analysis_results.get('timestamp', 'Unknown')}",
                f"页面URL: {self.analysis_results.get('current_url', 'Unknown')}",
                f"页面标题: {self.analysis_results.get('page_title', 'Unknown')}",
                "",
                "📊 登录指示器分析:",
            ]
            
            # 登录指示器摘要
            login_indicators = self.analysis_results.get('login_indicators', {})
            summary = login_indicators.get('summary', {})
            summary_lines.extend([
                f"  - 登录状态: {summary.get('login_state', 'unknown')}",
                f"  - 成功指示器: {summary.get('found_success', 0)} 个",
                f"  - 失败指示器: {summary.get('found_failure', 0)} 个"
            ])
            
            # Cookie摘要
            cookies_analysis = self.analysis_results.get('cookies_analysis', {})
            summary_lines.extend([
                "",
                "🍪 Cookie分析:",
                f"  - 总Cookie数: {cookies_analysis.get('total_count', 0)}",
                f"  - 重要Cookie: {len(cookies_analysis.get('important_cookies', []))} 个",
                f"  - 会话Cookie: {cookies_analysis.get('session_cookies', 0)} 个",
                f"  - 持久Cookie: {cookies_analysis.get('persistent_cookies', 0)} 个"
            ])
            
            # 存储摘要
            storage_analysis = self.analysis_results.get('storage_analysis', {})
            local_count = storage_analysis.get('localStorage', {}).get('count', 0)
            session_count = storage_analysis.get('sessionStorage', {}).get('count', 0)
            summary_lines.extend([
                "",
                "💾 存储分析:",
                f"  - localStorage: {local_count} 项",
                f"  - sessionStorage: {session_count} 项"
            ])
            
            # 建议摘要
            recommendations = self.analysis_results.get('recommendations', [])
            if recommendations:
                summary_lines.extend([
                    "",
                    "💡 优化建议:",
                ])
                for i, rec in enumerate(recommendations[:5], 1):
                    priority_icon = "🔴" if rec['priority'] == 'high' else "🟡" if rec['priority'] == 'medium' else "🟢"
                    summary_lines.append(f"  {i}. {priority_icon} {rec['message']}")
            
            summary_lines.append("=" * 60)
            
            return "\n".join(summary_lines)
            
        except Exception as e:
            self.logger.error(f"生成摘要报告失败: {e}")
            return f"摘要报告生成失败: {e}"