# 前程无忧自动化搜索实现方案

## 🎯 需求分析

### 核心功能
1. **人工登录**: 用户手动完成登录过程
2. **登录检测**: 自动检测登录成功状态
3. **自动导航**: 登录成功后自动跳转到搜索页面
4. **关键词配置**: 将搜索关键词作为配置项管理
5. **URL参数化**: 支持动态构建搜索URL

### 目标URL分析
```
搜索页面URL: https://we.51job.com/pc/search?jobArea=020000&keyword=AI&searchType=2&keywordType=

URL参数说明:
- jobArea=020000: 上海地区代码
- keyword=AI: 搜索关键词 (可配置)
- searchType=2: 搜索类型
- keywordType=: 关键词类型 (空值)
```

## 📋 配置文件更新方案

### 1. 搜索关键词配置
```yaml
# 搜索配置
search:
  # 基础搜索参数
  base_url: "https://we.51job.com/pc/search"
  job_area: "020000"  # 上海地区
  search_type: "2"
  keyword_type: ""
  
  # 搜索关键词列表 (按优先级排序)
  keywords:
    priority_1:
      - "数据架构师"
      - "Azure架构师" 
      - "AI工程师"
    priority_2:
      - "Databricks工程师"
      - "技术总监"
      - "机器学习工程师"
    priority_3:
      - "LLM工程师"
      - "数据平台负责人"
      - "制药 数据工程师"
  
  # 当前使用的关键词
  current_keyword: "AI"
  
  # 搜索策略配置
  strategy:
    max_results_per_keyword: 50
    delay_between_searches: 3  # 秒
    auto_scroll_pages: 5
    save_job_details: true
```

### 2. 登录检测配置
```yaml
# 登录相关配置
login:
  # 登录页面URL
  login_url: "https://login.51job.com"
  
  # 登录成功检测元素
  success_indicators:
    - ".user-info"
    - ".user-name"
    - "[data-testid='user-avatar']"
    - ".header-user"
  
  # 登录等待配置
  wait_timeout: 300  # 5分钟等待用户登录
  check_interval: 2  # 每2秒检查一次登录状态
  
  # 登录失败检测
  failure_indicators:
    - ".error-message"
    - ".login-error"
    - ".alert-danger"
```

### 3. 页面元素配置
```yaml
# 页面元素选择器
selectors:
  # 搜索页面元素
  search_page:
    job_list: ".job-list-item"
    job_title: ".job-title a"
    company_name: ".company-name"
    salary: ".salary"
    location: ".location"
    experience: ".experience"
    education: ".education"
    next_page: ".next-page"
    load_more: ".load-more"
  
  # 职位详情页元素
  job_detail:
    job_description: ".job-description"
    requirements: ".job-requirements"
    company_info: ".company-info"
    benefits: ".job-benefits"
    apply_button: ".apply-btn"
```

## 🔧 代码实现方案

### 1. 搜索URL构建器
```python
class SearchURLBuilder:
    def __init__(self, config):
        self.config = config
        self.search_config = config['search']
    
    def build_search_url(self, keyword=None):
        """构建搜索URL"""
        if keyword is None:
            keyword = self.search_config['current_keyword']
        
        params = {
            'jobArea': self.search_config['job_area'],
            'keyword': keyword,
            'searchType': self.search_config['search_type'],
            'keywordType': self.search_config['keyword_type']
        }
        
        base_url = self.search_config['base_url']
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        
        return f"{base_url}?{query_string}"
    
    def get_keywords_by_priority(self, priority_level=1):
        """获取指定优先级的关键词"""
        priority_key = f"priority_{priority_level}"
        return self.search_config['keywords'].get(priority_key, [])
    
    def get_all_keywords(self):
        """获取所有关键词"""
        all_keywords = []
        for priority in ['priority_1', 'priority_2', 'priority_3']:
            all_keywords.extend(
                self.search_config['keywords'].get(priority, [])
            )
        return all_keywords
```

### 2. 登录检测器
```python
class LoginDetector:
    def __init__(self, driver, config):
        self.driver = driver
        self.login_config = config['login']
        self.logger = logging.getLogger(__name__)
    
    def wait_for_login(self):
        """等待用户完成登录"""
        self.logger.info("等待用户登录...")
        
        timeout = self.login_config['wait_timeout']
        check_interval = self.login_config['check_interval']
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.is_logged_in():
                self.logger.info("登录成功检测到!")
                return True
            
            if self.has_login_error():
                self.logger.warning("检测到登录错误，请重试")
            
            time.sleep(check_interval)
        
        raise TimeoutError("登录等待超时")
    
    def is_logged_in(self):
        """检测是否已登录"""
        success_indicators = self.login_config['success_indicators']
        
        for selector in success_indicators:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element and element.is_displayed():
                    self.logger.debug(f"找到登录成功指示器: {selector}")
                    return True
            except:
                continue
        
        return False
    
    def has_login_error(self):
        """检测是否有登录错误"""
        failure_indicators = self.login_config['failure_indicators']
        
        for selector in failure_indicators:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element and element.is_displayed():
                    error_text = element.text
                    self.logger.warning(f"登录错误: {error_text}")
                    return True
            except:
                continue
        
        return False
```

### 3. 自动化搜索控制器
```python
class JobSearchAutomation:
    def __init__(self, config_path="config/config.yaml"):
        self.config = self._load_config(config_path)
        self.driver = None
        self.url_builder = SearchURLBuilder(self.config)
        self.logger = logging.getLogger(__name__)
    
    def start_search_session(self, keyword=None):
        """开始搜索会话"""
        try:
            # 1. 启动浏览器
            self._setup_driver()
            
            # 2. 导航到登录页面
            self._navigate_to_login()
            
            # 3. 等待用户登录
            login_detector = LoginDetector(self.driver, self.config)
            login_detector.wait_for_login()
            
            # 4. 登录成功后自动导航到搜索页面
            search_url = self.url_builder.build_search_url(keyword)
            self._navigate_to_search(search_url)
            
            # 5. 开始搜索流程
            self._execute_search()
            
        except Exception as e:
            self.logger.error(f"搜索会话失败: {e}")
            raise
        finally:
            self._cleanup()
    
    def _navigate_to_login(self):
        """导航到登录页面"""
        login_url = self.config['login']['login_url']
        self.logger.info(f"导航到登录页面: {login_url}")
        self.driver.get(login_url)
        
        # 等待页面加载
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )
    
    def _navigate_to_search(self, search_url):
        """导航到搜索页面"""
        self.logger.info(f"导航到搜索页面: {search_url}")
        self.driver.get(search_url)
        
        # 等待搜索页面加载
        WebDriverWait(self.driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".job-list-item"))
        )
        
        self.logger.info("搜索页面加载完成")
    
    def _execute_search(self):
        """执行搜索和数据收集"""
        selectors = self.config['selectors']['search_page']
        
        # 获取职位列表
        job_elements = self.driver.find_elements(By.CSS_SELECTOR, selectors['job_list'])
        self.logger.info(f"找到 {len(job_elements)} 个职位")
        
        # 处理每个职位
        for i, job_element in enumerate(job_elements, 1):
            try:
                job_data = self._extract_job_data(job_element, selectors)
                self.logger.info(f"职位 {i}: {job_data['title']} - {job_data['company']}")
                
                # 保存职位数据
                self._save_job_data(job_data)
                
            except Exception as e:
                self.logger.warning(f"处理职位 {i} 时出错: {e}")
                continue
    
    def _extract_job_data(self, job_element, selectors):
        """提取职位数据"""
        job_data = {}
        
        try:
            job_data['title'] = job_element.find_element(
                By.CSS_SELECTOR, selectors['job_title']
            ).text.strip()
        except:
            job_data['title'] = "未知职位"
        
        try:
            job_data['company'] = job_element.find_element(
                By.CSS_SELECTOR, selectors['company_name']
            ).text.strip()
        except:
            job_data['company'] = "未知公司"
        
        try:
            job_data['salary'] = job_element.find_element(
                By.CSS_SELECTOR, selectors['salary']
            ).text.strip()
        except:
            job_data['salary'] = "薪资面议"
        
        try:
            job_data['location'] = job_element.find_element(
                By.CSS_SELECTOR, selectors['location']
            ).text.strip()
        except:
            job_data['location'] = "未知地点"
        
        # 获取职位链接
        try:
            job_data['url'] = job_element.find_element(
                By.CSS_SELECTOR, selectors['job_title']
            ).get_attribute('href')
        except:
            job_data['url'] = ""
        
        return job_data
```

### 4. 使用示例
```python
# 使用示例
def main():
    # 创建搜索自动化实例
    automation = JobSearchAutomation()
    
    # 开始搜索会话 - 使用配置中的默认关键词
    automation.start_search_session()
    
    # 或者指定特定关键词
    # automation.start_search_session(keyword="数据架构师")

if __name__ == "__main__":
    main()
```

## 📊 配置文件完整示例

### config/config.yaml 更新版本
```yaml
# 自动投递简历工具配置文件
# 基于config.example.yaml创建的实际配置

# 基础配置
app:
  name: "Resume Auto Submitter"
  version: "1.0.0"
  debug: true

# 数据库配置
database:
  path: "./data/jobs.db"

# 搜索配置
search:
  # 基础搜索参数
  base_url: "https://we.51job.com/pc/search"
  job_area: "020000"  # 上海地区
  search_type: "2"
  keyword_type: ""
  
  # 搜索关键词列表 (按优先级排序)
  keywords:
    priority_1:
      - "数据架构师"
      - "Azure架构师" 
      - "AI工程师"
    priority_2:
      - "Databricks工程师"
      - "技术总监"
      - "机器学习工程师"
    priority_3:
      - "LLM工程师"
      - "数据平台负责人"
      - "制药 数据工程师"
  
  # 当前使用的关键词
  current_keyword: "AI"
  
  # 搜索策略配置
  strategy:
    max_results_per_keyword: 50
    delay_between_searches: 3
    auto_scroll_pages: 5
    save_job_details: true

# 登录相关配置
login:
  login_url: "https://login.51job.com"
  success_indicators:
    - ".user-info"
    - ".user-name"
    - "[data-testid='user-avatar']"
    - ".header-user"
  wait_timeout: 300
  check_interval: 2
  failure_indicators:
    - ".error-message"
    - ".login-error"
    - ".alert-danger"

# 页面元素选择器
selectors:
  search_page:
    job_list: ".job-list-item"
    job_title: ".job-title a"
    company_name: ".company-name"
    salary: ".salary"
    location: ".location"
    experience: ".experience"
    education: ".education"
    next_page: ".next-page"
    load_more: ".load-more"
  
  job_detail:
    job_description: ".job-description"
    requirements: ".job-requirements"
    company_info: ".company-info"
    benefits: ".job-benefits"
    apply_button: ".apply-btn"

# 网站配置 (保持原有配置)
websites:
  zhilian:
    enabled: true
    base_url: "https://www.zhaopin.com"
    login_url: "https://passport.zhaopin.com/login"
    search_url: "https://sou.zhaopin.com"
    login_check_element: ".user-info"
    submit_button_selector: ".btn-apply"
  
  qiancheng:
    enabled: true
    base_url: "https://www.51job.com"
    login_url: "https://login.51job.com"
    search_url: "https://search.51job.com"
    login_check_element: ".login-info"
    submit_button_selector: ".apply-btn"
  
  boss:
    enabled: true
    base_url: "https://www.zhipin.com"
    login_url: "https://login.zhipin.com"
    search_url: "https://www.zhipin.com/c101010100"
    login_check_element: ".user-name"
    submit_button_selector: ".btn-startchat"

# Selenium配置
selenium:
  browser: "chrome"
  headless: false
  window_size: "1920,1080"
  page_load_timeout: 30
  element_wait_timeout: 10
  implicit_wait: 5

# 其他配置保持不变...
```

## 🚀 实施步骤

### 第一步: 切换到Code模式
需要切换到Code模式来实际修改配置文件和创建代码

### 第二步: 更新配置文件
1. 更新 `config/config.yaml` 添加搜索配置
2. 添加登录检测配置
3. 添加页面元素选择器配置

### 第三步: 创建核心模块
1. 创建 `src/search/url_builder.py` - URL构建器
2. 创建 `src/search/login_detector.py` - 登录检测器
3. 创建 `src/search/automation.py` - 自动化控制器

### 第四步: 集成测试
1. 测试登录检测功能
2. 测试URL构建和导航
3. 测试搜索页面数据提取

### 第五步: 完善功能
1. 添加多关键词轮换搜索
2. 添加数据持久化
3. 添加搜索结果分析

这个方案将搜索关键词完全配置化，支持人工登录后自动导航到指定搜索页面，并且可以灵活调整搜索参数。