
# 部署与监控运维指南

## 🚀 生产环境部署

### 部署架构设计

```mermaid
graph TB
    subgraph "负载均衡层"
        LB[负载均衡器]
    end
    
    subgraph "应用层"
        APP1[应用实例1]
        APP2[应用实例2]
        APP3[应用实例3]
    end
    
    subgraph "数据层"
        DB[(主数据库)]
        VDB[(向量数据库)]
        CACHE[(Redis缓存)]
    end
    
    subgraph "监控层"
        PROM[Prometheus]
        GRAF[Grafana]
        ALERT[AlertManager]
    end
    
    subgraph "日志层"
        ELK[ELK Stack]
    end
    
    LB --> APP1
    LB --> APP2
    LB --> APP3
    
    APP1 --> DB
    APP1 --> VDB
    APP1 --> CACHE
    
    APP2 --> DB
    APP2 --> VDB
    APP2 --> CACHE
    
    APP3 --> DB
    APP3 --> VDB
    APP3 --> CACHE
    
    PROM --> APP1
    PROM --> APP2
    PROM --> APP3
    
    GRAF --> PROM
    ALERT --> PROM
    
    APP1 --> ELK
    APP2 --> ELK
    APP3 --> ELK
```

### Docker容器化部署

#### 主应用Dockerfile

```dockerfile
# Dockerfile
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    wget \
    curl \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要目录
RUN mkdir -p logs data/chroma_db backups

# 设置环境变量
ENV PYTHONPATH=/app
ENV INTEGRATION_ENV=production
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROME_DRIVER=/usr/bin/chromedriver

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["python", "-m", "src.integration.main"]
```

#### Docker Compose配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  # 主应用服务
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - INTEGRATION_ENV=production
      - DATABASE_URL=postgresql://user:password@postgres:5432/resume_system
      - REDIS_URL=redis://redis:6379
      - VECTOR_DB_PATH=/app/data/chroma_db
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
    depends_on:
      - postgres
      - redis
      - chromadb
    restart: unless-stopped
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G

  # 数据库服务
  postgres:
    image: postgres:13
    environment:
      - POSTGRES_DB=resume_system
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    restart: unless-stopped

  # Redis缓存
  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    command: redis-server --appendonly yes

  # 向量数据库
  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma
    environment:
      - CHROMA_SERVER_HOST=0.0.0.0
      - CHROMA_SERVER_HTTP_PORT=8000
    restart: unless-stopped

  # 负载均衡器
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped

  # 监控服务
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
    restart: unless-stopped

  # 可视化监控
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    depends_on:
      - prometheus
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  chroma_data:
  prometheus_data:
  grafana_data:
```

### Kubernetes部署配置

#### 应用部署清单

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: resume-system
  labels:
    app: resume-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: resume-system
  template:
    metadata:
      labels:
        app: resume-system
    spec:
      containers:
      - name: resume-system
        image: resume-system:latest
        ports:
        - containerPort: 8000
        env:
        - name: INTEGRATION_ENV
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        volumeMounts:
        - name: data-volume
          mountPath: /app/data
        - name: config-volume
          mountPath: /app/config
      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: resume-system-pvc
      - name: config-volume
        configMap:
          name: resume-system-config
---
apiVersion: v1
kind: Service
metadata:
  name: resume-system-service
spec:
  selector:
    app: resume-system
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

#### 配置管理

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: resume-system-config
data:
  integration_config.yaml: |
    integration_system:
      global:
        system_name: "智能简历投递系统"
        version: "2.0.0"
        environment: "production"
        debug_mode: false
        log_level: "INFO"
      
      master_controller:
        max_concurrent_pipelines: 5
        pipeline_timeout: 3600
        checkpoint_interval: 100
        error_retry_attempts: 3
        
      performance:
        caching:
          enabled: true
          cache_type: "redis"
          cache_size: 10000
          ttl_seconds: 3600
        
        concurrency:
          max_workers: 10
          semaphore_limit: 5
          
      monitoring:
        enabled: true
        metrics_collection_interval: 30
        real_time_dashboard: true
---
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  url: cG9zdGdyZXNxbDovL3VzZXI6cGFzc3dvcmRAcG9zdGdyZXM6NTQzMi9yZXN1bWVfc3lzdGVt
```

## 📊 监控系统设计

### Prometheus监控配置

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  # 应用监控
  - job_name: 'resume-system'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
    
  # 系统监控
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
      
  # 数据库监控
  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['postgres-exporter:9187']
      
  # Redis监控
  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['redis-exporter:9121']
```

### 告警规则配置

```yaml
# monitoring/alert_rules.yml
groups:
- name: resume_system_alerts
  rules:
  # 应用可用性告警
  - alert: ApplicationDown
    expr: up{job="resume-system"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "应用实例不可用"
      description: "应用实例 {{ $labels.instance }} 已经下线超过1分钟"

  # 错误率告警
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "高错误率告警"
      description: "错误率超过10%，当前值: {{ $value }}"

  # 响应时间告警
  - alert: HighResponseTime
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
    for: 3m
    labels:
      severity: warning
    annotations:
      summary: "响应时间过长"
      description: "95%分位响应时间超过2秒，当前值: {{ $value }}s"

  # 内存使用告警
  - alert: HighMemoryUsage
    expr: (process_resident_memory_bytes / 1024 / 1024) > 3000
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "内存使用过高"
      description: "内存使用超过3GB，当前值: {{ $value }}MB"

  # CPU使用告警
  - alert: HighCPUUsage
    expr: rate(process_cpu_seconds_total[5m]) * 100 > 80
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "CPU使用率过高"
      description: "CPU使用率超过80%，当前值: {{ $value }}%"

  # 数据库连接告警
  - alert: DatabaseConnectionHigh
    expr: pg_stat_activity_count > 80
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "数据库连接数过高"
      description: "数据库连接数超过80，当前值: {{ $value }}"

  # 磁盘空间告警
  - alert: DiskSpaceLow
    expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100 < 10
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "磁盘空间不足"
      description: "磁盘可用空间低于10%，当前值: {{ $value }}%"
```

### Grafana仪表板配置

```json
{
  "dashboard": {
    "id": null,
    "title": "智能简历投递系统监控",
    "tags": ["resume-system"],
    "timezone": "Asia/Shanghai",
    "panels": [
      {
        "id": 1,
        "title": "系统概览",
        "type": "stat",
        "targets": [
          {
            "expr": "up{job=\"resume-system\"}",
            "legendFormat": "实例状态"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "thresholds": {
              "steps": [
                {"color": "red", "value": 0},
                {"color": "green", "value": 1}
              ]
            }
          }
        }
      },
      {
        "id": 2,
        "title": "请求速率",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{status}}"
          }
        ]
      },
      {
        "id": 3,
        "title": "响应时间分布",
        "type": "heatmap",
        "targets": [
          {
            "expr": "rate(http_request_duration_seconds_bucket[5m])",
            "legendFormat": "{{le}}"
          }
        ]
      },
      {
        "id": 4,
        "title": "流水线执行统计",
        "type": "graph",
        "targets": [
          {
            "expr": "pipeline_executions_total",
            "legendFormat": "总执行数"
          },
          {
            "expr": "pipeline_executions_success_total",
            "legendFormat": "成功执行数"
          }
        ]
      },
      {
        "id": 5,
        "title": "资源使用情况",
        "type": "graph",
        "targets": [
          {
            "expr": "process_resident_memory_bytes / 1024 / 1024",
            "legendFormat": "内存使用(MB)"
          },
          {
            "expr": "rate(process_cpu_seconds_total[5m]) * 100",
            "legendFormat": "CPU使用率(%)"
          }
        ]
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
```

## 📈 性能监控指标

### 应用级指标

```python
# src/integration/metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time
import functools

# 定义监控指标
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
PIPELINE_EXECUTIONS = Counter('pipeline_executions_total', 'Total pipeline executions', ['status'])
PIPELINE_DURATION = Histogram('pipeline_duration_seconds', 'Pipeline execution duration')
ACTIVE_PIPELINES = Gauge('active_pipelines', 'Number of active pipelines')
JOB_PROCESSING_RATE = Gauge('job_processing_rate', 'Jobs processed per second')
MEMORY_USAGE = Gauge('memory_usage_bytes', 'Memory usage in bytes')
CPU_USAGE = Gauge('cpu_usage_percent', 'CPU usage percentage')

class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.start_time = time.time()
        
    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        """记录HTTP请求指标"""
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
        REQUEST_DURATION.observe(duration)
    
    def record_pipeline_execution(self, status: str, duration: float):
        """记录流水线执行指标"""
        PIPELINE_EXECUTIONS.labels(status=status).inc()
        PIPELINE_DURATION.observe(duration)
    
    def update_active_pipelines(self, count: int):
        """更新活跃流水线数量"""
        ACTIVE_PIPELINES.set(count)
    
    def update_processing_rate(self, rate: float):
        """更新处理速率"""
        JOB_PROCESSING_RATE.set(rate)
    
    def update_resource_usage(self, memory_bytes: int, cpu_percent: float):
        """更新资源使用情况"""
        MEMORY_USAGE.set(memory_bytes)
        CPU_USAGE.set(cpu_percent)

def monitor_performance(func):
    """性能监控装饰器"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            
            # 记录成功执行
            if hasattr(func, '__name__') and 'pipeline' in func.__name__:
                metrics_collector.record_pipeline_execution('success', duration)
            
            return result
        except Exception as e:
            duration = time.time() - start_time
            
            # 记录失败执行
            if hasattr(func, '__name__') and 'pipeline' in func.__name__:
                metrics_collector.record_pipeline_execution('failure', duration)
            
            raise e
    return wrapper

# 全局指标收集器实例
metrics_collector = MetricsCollector()

def start_metrics_server(port: int = 8001):
    """启动指标服务器"""
    start_http_server(port)
    logger.info(f"指标服务器已启动，端口: {port}")
```

### 业务指标监控

```python
# src/integration/business_metrics.py
from prometheus_client import Counter, Histogram, Gauge

# 业务指标定义
JOB_EXTRACTION_COUNT = Counter('job_extraction_total', 'Total jobs extracted', ['source', 'status'])
JOB_EXTRACTION_DURATION = Histogram('job_extraction_duration_seconds', 'Job extraction duration')

RAG_PROCESSING_COUNT = Counter('rag_processing_total', 'Total RAG processing', ['status'])
RAG_PROCESSING_DURATION = Histogram('rag_processing_duration_seconds', 'RAG processing duration')

RESUME_MATCHING_COUNT = Counter('resume_matching_total', 'Total resume matching', ['status'])
RESUME_MATCHING_DURATION = Histogram('resume_matching_duration_seconds', 'Resume matching duration')

SUBMISSION_COUNT = Counter('submission_total', 'Total submissions', ['status'])
SUBMISSION_SUCCESS_RATE = Gauge('submission_success_rate', 'Submission success rate')

VECTOR_DB_OPERATIONS = Counter('vector_db_operations_total', 'Vector DB operations', ['operation', 'status'])
CACHE_OPERATIONS = Counter('cache_operations_total', 'Cache operations', ['operation', 'status'])

class BusinessMetricsCollector:
    """业务指标收集器"""
    
    def record_job_extraction(self, source: str, status: str, duration: float, count: int):
        """记录职位提取指标"""
        JOB_EXTRACTION_COUNT.labels(source=source, status=status).inc(count)
        JOB_EXTRACTION_DURATION.observe(duration)
    
    def record_rag_processing(self, status: str, duration: float, count: int):
        """记录RAG处理指标"""
        RAG_PROCESSING_COUNT.labels(status=status).inc(count)
        RAG_PROCESSING_DURATION.observe(duration)
    
    def record_resume_matching(self, status: str, duration: float, matches: int):
        """记录简历匹配指标"""
        RESUME_MATCHING_COUNT.labels(status=status).inc(matches)
        RESUME_MATCHING_DURATION.observe(duration)
    
    def record_submission(self, status: str, count: int):
        """记录投递指标"""
        SUBMISSION_COUNT.labels(status=status).inc(count)
    
    def update_submission_success_rate(self, rate: float):
        """更新投递成功率"""
        SUBMISSION_SUCCESS_RATE.set(rate)
    
    def record_vector_db_operation(self, operation: str, status: str):
        """记录向量数据库操作"""
        VECTOR_DB_OPERATIONS.labels(operation=operation, status=status).inc()
    
    def record_cache_operation(self, operation: str, status: str):
        """记录缓存操作"""
        CACHE_OPERATIONS.labels(operation=operation, status=status).inc()

# 全局业务指标收集器
business_metrics = BusinessMetricsCollector()
```

## 🔧 运维自动化

### 健康检查端点

```python
# src/integration/health_check.py
from fastapi import FastAPI, HTTPException
from typing import Dict, Any
import asyncio
import time

app = FastAPI()

class HealthChecker:
    """健康检查器"""
    
    def __init__(self, master_controller):
        self.master_controller = master_controller
        self.last_check_time = None
        self.health_status = {}
    
    async def check_system_health(self) -> Dict[str, Any]:
        """检查系统健康状态"""
        health_status = {
            'timestamp': time.time(),
            'overall_status': 'healthy',
            'components': {}
        }
        
        try:
            # 检查数据库连接
            db_status = await self._check_database_health()
            health_status['components']['database'] = db_status
            
            # 检查向量数据库
            vector_db_status = await self._check_vector_db_health()
            health_status['components']['vector_db'] = vector_db_status
            
            # 检查缓存系统
            cache_status = await self._check_cache_health()
            health_status['components']['cache'] = cache_status
            
            # 检查RAG系统
            rag_status = await self._check_rag_system_health()
            health_status['components']['rag_system'] = rag_status
            
            # 检查外部服务
            external_status = await self._check_external_services()
            health_status['components']['external_services'] = external_status
            
            # 计算整体状态
            component_statuses = [comp['status'] for comp in health_status['components'].values()]
            if all(status == 'healthy' for status in component_statuses):
                health_status['overall_status'] = 'healthy'
            elif any(status == 'unhealthy' for status in component_statuses):
                health_status['overall_status'] = 'unhealthy'
            else:
                health_status['overall_status'] = 'degraded'
            
            self.health_status = health_status
            self.last_check_time = time.time()
            
            return health_status
            
        except Exception as e:
            return {
                'timestamp': time.time(),
                'overall_status': 'unhealthy',
                'error': str(e)
            }
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """检查数据库健康状态"""
        try:
            # 执行简单查询测试连接
            result = await self.master_controller.rag_coordinator.db_reader.test_connection()
            return {
                'status': 'healthy' if result else 'unhealthy',
                'response_time': 0.1,  # 实际测量
                'details': 'Database connection successful'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def _check_vector_db_health(self) -> Dict[str, Any]:
        """检查向量数据库健康状态"""
        try:
            stats = self.master_controller.rag_coordinator.vector_manager.get_collection_stats()
            return {
                'status': 'healthy',
                'document_count': stats.get('document_count', 0),
                'collection_name': stats.get('collection_name', 'unknown')
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }

@app.get("/health")
async def health_check():
    """健康检查端点"""
    health_checker = HealthChecker(master_controller)
    health_status = await health_checker.check_system_health()
    
    if health_status['overall_status'] == 'healthy':
        return health_status
    else:
        raise HTTPException(status_code=503, detail=health_status)

@app.get("/ready")
async def readiness_check():
    """就绪检查端点"""
    if master_controller.is_initialized:
        return {"status": "ready"}
    else:
        raise HTTPException(status_code=503, detail="System not ready")

@app.get("/metrics")
async def metrics_endpoint():
    """指标端点"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

### 自动化部署脚本

```bash
#!/bin/bash
# deploy.sh - 自动化部署脚本

set -e

# 配置变量
APP_NAME="resume-system"
VERSION=${1:-latest}
ENVIRONMENT=${2:-production}
NAMESPACE=${3:-default}

echo "开始部署 $APP_NAME:$VERSION 到 $ENVIRONMENT 环境"

# 1. 构建Docker镜像
echo "构建Docker镜像..."
docker build -t $APP_NAME:$VERSION .
docker tag $APP_NAME:$VERSION $APP_NAME:latest

# 2. 推送到镜像仓库
echo "推送镜像到仓库..."
docker push $APP_NAME:$VERSION
docker push $APP_NAME:latest

# 3. 更新Kubernetes配置
echo "更新Kubernetes配置..."
sed -i "s|image: $APP_NAME:.*|image: $APP_NAME:$VERSION|g" k8s/deployment.yaml

# 4. 应用配置
echo "应用Kubernetes配置..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# 5. 等待部署完成
echo "等待部署完成..."
kubectl rollout status deployment/$APP_NAME -n $NAMESPACE --timeout=600s

# 6. 验证部署
echo "验证部署状态..."
kubectl get pods -n $NAMESPACE -l app=$APP_NAME
kubectl get services -n $NAMESPACE -l app=$APP_NAME

# 7. 运行健康检查
echo "运行健康检查..."
HEALTH_URL=$(kubectl get service $APP_NAME-service -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [ -n "$HEALTH_URL" ]; then
    curl -f http://$HEALTH_URL/health || echo "健康检查失败"
else
    echo "无法获取服务IP，跳过健康检查"
fi

echo "部署完成！"
```

### 备份和恢复脚本

```bash
#!/bin/bash
# backup.sh - 数据备份脚本

set -e

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
APP_NAME="resume-system"

echo "开始数据备份 - $DATE"

# 1. 创建备份目录
mkdir -p $BACKUP_DIR/$DATE

# 2. 备份数据库
echo "备份PostgreSQL数据库..."
kubectl exec -n default deployment/postgres -- pg_dump -U user resume_system > $BACKUP_DIR/$DATE/database.sql

# 3. 备份向量数据库
echo "备份ChromaDB数据..."
kubectl cp default/chromadb-pod:/chroma/chroma $BACKUP_DIR/$DATE/chroma_data

# 4. 备份配置文件
echo "备份配置文件..."
kubectl get configmap resume-system-config -o yaml > $BACKUP_DIR/$DATE/configmap.yaml
kubectl get secret db-secret -o yaml > $BACKUP_DIR/$DATE/secret.yaml

# 5. 备份应用数据
echo "备份应用数据..."
kubectl cp default/resume-system-pod:/app/data $BACKUP_DIR/$DATE/app_data

# 6. 压缩备份
echo "压缩备份文件..."
cd $BACKUP_DIR
tar -czf $DATE.tar.gz $DATE/
rm -rf $DATE/

# 7. 清理旧备份（保留30天）
echo