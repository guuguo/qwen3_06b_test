# Qwen-3 服务器部署指南

本指南将帮助你在 Linux 服务器上部署 Qwen-3 模型，包括完整的生产环境配置。

## 📋 环境要求

### 系统要求
- **操作系统**: Ubuntu 18.04+ 或 CentOS 7+
- **内存**: 16GB+ (推荐 32GB)
- **存储**: 100GB+ SSD 存储
- **网络**: 稳定的互联网连接

### 硬件要求
- **CPU**: 8核心以上 (推荐 16核心)
- **内存**: 16GB+ (0.6B 模型需要约 4-6GB，1.7B 模型需要约 8-12GB)
- **存储**: 100GB+ SSD (用于模型存储和日志)
- **网络**: 1Gbps+ 带宽

### 端口要求
- **80**: HTTP 服务 (Nginx)
- **8000**: API 服务 (内部)
- **11434**: Ollama 服务 (内部)

## 🚀 一键部署

### 下载部署脚本

```bash
# 下载部署脚本
wget https://raw.githubusercontent.com/your-repo/qwen3-deployment/main/scripts/server_deploy.sh

# 或者使用 curl
curl -O https://raw.githubusercontent.com/your-repo/qwen3-deployment/main/scripts/server_deploy.sh

# 设置执行权限
chmod +x server_deploy.sh
```

### 执行部署

```bash
# 使用默认配置部署
sudo bash server_deploy.sh

# 自定义用户和安装目录
sudo bash server_deploy.sh --user myuser --home /opt/myapp
```

### 部署过程

部署脚本将自动执行以下步骤：

1. ✅ **检测操作系统** - 自动识别 Ubuntu/CentOS
2. ✅ **安装系统依赖** - Python、Nginx、Supervisor 等
3. ✅ **创建用户和目录** - 创建专用用户和目录结构
4. ✅ **安装 Ollama** - 下载并配置 Ollama 服务
5. ✅ **下载模型** - 自动下载 Qwen-3 0.6B 和 1.7B 模型
6. ✅ **安装 Python 应用** - 创建虚拟环境并安装依赖
7. ✅ **配置服务** - 设置 Supervisor 和 Nginx
8. ✅ **验证部署** - 自动测试所有服务

## 📁 目录结构

部署完成后的目录结构：

```
/opt/qwen3/                    # 主目录
├── app/                       # 应用代码
│   ├── venv/                  # Python 虚拟环境
│   ├── app.py                 # 主应用文件
│   └── requirements.txt       # Python 依赖
├── models/                    # 模型存储 (Ollama 管理)
├── logs/                      # 应用日志
├── config/                    # 配置文件
└── scripts/                   # 管理脚本
    ├── status.sh              # 状态检查
    ├── restart.sh             # 重启服务
    └── logs.sh                # 日志查看

/var/log/qwen3/               # 系统日志
├── api_access.log            # API 访问日志
└── api_error.log             # API 错误日志

/etc/qwen3/                   # 配置目录
```

## 🔧 服务管理

### 查看服务状态

```bash
# 查看所有服务状态
bash /opt/qwen3/scripts/status.sh

# 查看具体服务
systemctl status ollama
systemctl status nginx
supervisorctl status qwen3-api
```

### 重启服务

```bash
# 重启所有服务
bash /opt/qwen3/scripts/restart.sh

# 重启单个服务
systemctl restart ollama
systemctl restart nginx
supervisorctl restart qwen3-api
```

### 查看日志

```bash
# 查看 API 访问日志
bash /opt/qwen3/scripts/logs.sh api

# 查看 API 错误日志
bash /opt/qwen3/scripts/logs.sh error

# 查看 Ollama 服务日志
bash /opt/qwen3/scripts/logs.sh ollama

# 查看 Nginx 日志
bash /opt/qwen3/scripts/logs.sh nginx
```

## 🌐 API 使用

### 健康检查

```bash
curl http://your-server-ip/health
```

期望响应：
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000000"
}
```

### 模型推理

```bash
curl -X POST http://your-server-ip/api/v1/inference \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3:0.6b",
    "prompt": "你好，请介绍一下你自己",
    "options": {
      "temperature": 0.7,
      "max_tokens": 100
    }
  }'
```

期望响应：
```json
{
  "status": "success",
  "response": "你好！我是Qwen，一个由阿里云开发的大型语言模型...",
  "model": "qwen3:0.6b",
  "duration": 1.234
}
```

### 获取模型列表

```bash
curl http://your-server-ip/api/v1/models
```

期望响应：
```json
{
  "models": ["qwen3:0.6b", "qwen3:1.7b"]
}
```

## 📊 监控和指标

### Prometheus 指标

访问指标端点（仅限本地访问）：
```bash
curl http://localhost/metrics
```

主要指标：
- `qwen3_requests_total` - 总请求数
- `qwen3_request_duration_seconds` - 请求延迟
- `qwen3_active_connections` - 活跃连接数
- `qwen3_system_cpu_percent` - CPU 使用率
- `qwen3_system_memory_percent` - 内存使用率

### 系统监控

```bash
# CPU 和内存使用情况
htop

# 磁盘使用情况
df -h

# 网络连接
netstat -tlnp | grep -E ':(80|8000|11434)'

# 进程状态
ps aux | grep -E '(ollama|gunicorn|nginx)'
```

## 🔒 安全配置

### 防火墙设置

```bash
# Ubuntu (UFW)
sudo ufw allow 80/tcp
sudo ufw allow 22/tcp
sudo ufw enable

# CentOS (firewalld)
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=22/tcp
sudo firewall-cmd --reload
```

### SSL/TLS 配置 (可选)

如需 HTTPS 支持，可以使用 Let's Encrypt：

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx  # Ubuntu
sudo yum install certbot python3-certbot-nginx  # CentOS

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo crontab -e
# 添加: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 访问控制

编辑 Nginx 配置 `/etc/nginx/sites-available/qwen3`：

```nginx
# 限制指标端点访问
location /metrics {
    proxy_pass http://qwen3_backend/metrics;
    allow 127.0.0.1;
    allow 10.0.0.0/8;    # 内网访问
    deny all;
}

# API 速率限制
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

location /api/ {
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://qwen3_backend;
    # ... 其他配置
}
```

## 🔧 性能调优

### Nginx 优化

编辑 `/etc/nginx/nginx.conf`：

```nginx
worker_processes auto;
worker_connections 1024;

http {
    # 启用 gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain application/json;
    
    # 连接保持
    keepalive_timeout 65;
    keepalive_requests 100;
    
    # 缓冲区大小
    client_body_buffer_size 128k;
    client_max_body_size 10m;
}
```

### Gunicorn 优化

编辑 `/etc/supervisor/conf.d/qwen3.conf`：

```ini
[program:qwen3-api]
command=/opt/qwen3/app/venv/bin/gunicorn 
    --bind 0.0.0.0:8000 
    --workers 4 
    --worker-class sync 
    --worker-connections 1000 
    --timeout 120 
    --keepalive 5 
    --max-requests 1000 
    --max-requests-jitter 100 
    app:app
```

### 系统优化

```bash
# 增加文件描述符限制
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# 优化网络参数
echo "net.core.somaxconn = 1024" >> /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog = 1024" >> /etc/sysctl.conf
sysctl -p
```

## 🔄 备份和恢复

### 备份脚本

创建 `/opt/qwen3/scripts/backup.sh`：

```bash
#!/bin/bash

BACKUP_DIR="/backup/qwen3"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# 备份配置文件
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" /etc/qwen3 /etc/nginx/sites-available/qwen3 /etc/supervisor/conf.d/qwen3.conf

# 备份应用代码
tar -czf "$BACKUP_DIR/app_$DATE.tar.gz" /opt/qwen3/app

# 备份日志 (最近7天)
find /var/log/qwen3 -name "*.log" -mtime -7 | tar -czf "$BACKUP_DIR/logs_$DATE.tar.gz" -T -

echo "备份完成: $BACKUP_DIR"
```

### 恢复流程

```bash
# 停止服务
systemctl stop nginx
supervisorctl stop qwen3-api
systemctl stop ollama

# 恢复配置
tar -xzf config_backup.tar.gz -C /

# 恢复应用
tar -xzf app_backup.tar.gz -C /

# 重启服务
systemctl start ollama
supervisorctl start qwen3-api
systemctl start nginx
```

## 🚨 故障排查

### 常见问题

#### 1. Ollama 服务无法启动

```bash
# 检查日志
journalctl -u ollama -f

# 检查端口占用
lsof -i :11434

# 重置服务
systemctl stop ollama
rm -rf /opt/qwen3/.ollama
systemctl start ollama
```

#### 2. API 服务 502 错误

```bash
# 检查 Gunicorn 进程
supervisorctl status qwen3-api

# 检查应用日志
tail -f /var/log/qwen3/api_error.log

# 重启 API 服务
supervisorctl restart qwen3-api
```

#### 3. 内存不足

```bash
# 检查内存使用
free -h
ps aux --sort=-%mem | head

# 优化配置
# 减少 Gunicorn worker 数量
# 使用较小的模型 (0.6B 而不是 1.7B)
```

#### 4. 磁盘空间不足

```bash
# 检查磁盘使用
df -h
du -sh /opt/qwen3/* /var/log/qwen3/*

# 清理日志
find /var/log/qwen3 -name "*.log" -mtime +7 -delete
logrotate -f /etc/logrotate.d/qwen3
```

### 日志分析

```bash
# 分析 API 访问模式
awk '{print $1}' /var/log/qwen3/api_access.log | sort | uniq -c | sort -nr

# 查看错误统计
grep "ERROR" /var/log/qwen3/api_error.log | tail -20

# 性能分析
grep "duration" /var/log/qwen3/api_access.log | awk '{print $NF}' | sort -n
```

## 📈 扩展部署

### 负载均衡

使用多台服务器时，可以配置负载均衡：

```nginx
upstream qwen3_cluster {
    server 192.168.1.10:80;
    server 192.168.1.11:80;
    server 192.168.1.12:80;
}

server {
    listen 80;
    location / {
        proxy_pass http://qwen3_cluster;
    }
}
```

### 容器化部署

参考 [Kubernetes 部署指南](./kubernetes-deployment.md) 进行容器化部署。

## 📞 技术支持

如需技术支持：

1. 查看 [故障排查指南](../monitoring/troubleshooting.md)
2. 检查系统日志和应用日志
3. 确认网络和防火墙配置
4. 提交详细的错误信息和环境描述

## 📝 更新日志

- **v1.0.0** - 初始版本，支持基础部署
- **v1.1.0** - 添加监控和指标支持
- **v1.2.0** - 增强安全配置和性能优化
