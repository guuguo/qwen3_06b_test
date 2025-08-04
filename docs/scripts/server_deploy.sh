#!/bin/bash

# Qwen-3 服务器部署脚本
# 支持 Ubuntu 18.04+ 和 CentOS 7+
# 使用方法: bash server_deploy.sh [options]

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
QWEN3_USER="qwen3"
QWEN3_HOME="/opt/qwen3"
QWEN3_LOGS="/var/log/qwen3"
QWEN3_CONFIG="/etc/qwen3"
PYTHON_VERSION="3.9"
OLLAMA_VERSION="latest"

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查是否为 root 用户
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要 root 权限运行"
        log_info "请使用: sudo bash $0"
        exit 1
    fi
}

# 检测操作系统
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        log_error "无法检测操作系统版本"
        exit 1
    fi
    
    log_info "检测到操作系统: $OS $VER"
}

# 安装系统依赖
install_system_deps() {
    log_step "安装系统依赖..."
    
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        apt-get update
        apt-get install -y \
            curl \
            wget \
            git \
            build-essential \
            software-properties-common \
            apt-transport-https \
            ca-certificates \
            gnupg \
            lsb-release \
            python3 \
            python3-pip \
            python3-venv \
            supervisor \
            nginx \
            htop \
            vim \
            unzip
            
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
        yum update -y
        yum groupinstall -y "Development Tools"
        yum install -y \
            curl \
            wget \
            git \
            python3 \
            python3-pip \
            supervisor \
            nginx \
            htop \
            vim \
            unzip
    else
        log_error "不支持的操作系统: $OS"
        exit 1
    fi
    
    log_info "系统依赖安装完成"
}

# 创建用户和目录
create_user_and_dirs() {
    log_step "创建用户和目录..."
    
    # 创建 qwen3 用户
    if ! id "$QWEN3_USER" &>/dev/null; then
        useradd -r -m -s /bin/bash "$QWEN3_USER"
        log_info "创建用户: $QWEN3_USER"
    else
        log_info "用户已存在: $QWEN3_USER"
    fi
    
    # 创建目录
    mkdir -p "$QWEN3_HOME"/{app,models,logs,config,scripts}
    mkdir -p "$QWEN3_LOGS"
    mkdir -p "$QWEN3_CONFIG"
    
    # 设置权限
    chown -R "$QWEN3_USER:$QWEN3_USER" "$QWEN3_HOME"
    chown -R "$QWEN3_USER:$QWEN3_USER" "$QWEN3_LOGS"
    chown -R "$QWEN3_USER:$QWEN3_USER" "$QWEN3_CONFIG"
    
    log_info "目录创建完成"
}

# 安装 Ollama
install_ollama() {
    log_step "安装 Ollama..."
    
    # 下载并安装 Ollama
    curl -fsSL https://ollama.ai/install.sh | sh
    
    # 创建 systemd 服务文件
    cat > /etc/systemd/system/ollama.service << 'EOF'
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=qwen3
Group=qwen3
Restart=always
RestartSec=3
Environment="HOME=/opt/qwen3"
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=multi-user.target
EOF

    # 启用并启动服务
    systemctl daemon-reload
    systemctl enable ollama
    systemctl start ollama
    
    # 等待服务启动
    sleep 10
    
    # 验证服务状态
    if systemctl is-active --quiet ollama; then
        log_info "Ollama 服务启动成功"
    else
        log_error "Ollama 服务启动失败"
        systemctl status ollama
        exit 1
    fi
}

# 下载 Qwen-3 模型
download_models() {
    log_step "下载 Qwen-3 模型..."
    
    # 切换到 qwen3 用户执行
    sudo -u "$QWEN3_USER" bash << 'EOF'
export HOME=/opt/qwen3
cd $HOME

# 等待 Ollama 服务完全启动
sleep 5

# 下载模型
echo "下载 Qwen-3 0.6B 模型..."
/usr/local/bin/ollama pull qwen3:0.6b

echo "下载 Qwen-3 1.7B 模型..."
/usr/local/bin/ollama pull qwen3:1.7b

# 验证模型
echo "验证已下载的模型:"
/usr/local/bin/ollama list
EOF

    log_info "模型下载完成"
}

# 安装 Python 应用
install_python_app() {
    log_step "安装 Python 应用..."
    
    # 切换到 qwen3 用户
    sudo -u "$QWEN3_USER" bash << 'EOF'
export HOME=/opt/qwen3
cd $HOME/app

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 升级 pip
pip install --upgrade pip

# 创建 requirements.txt
cat > requirements.txt << 'REQUIREMENTS'
requests>=2.28.0
psutil>=5.9.0
flask>=2.3.0
gunicorn>=20.1.0
transformers>=4.30.0
torch>=2.0.0
numpy>=1.24.0
pandas>=2.0.0
matplotlib>=3.7.0
seaborn>=0.12.0
tqdm>=4.65.0
pyyaml>=6.0
click>=8.1.0
prometheus-client>=0.16.0
REQUIREMENTS

# 安装依赖
pip install -r requirements.txt

echo "Python 环境安装完成"
EOF

    log_info "Python 应用安装完成"
}

# 创建应用代码
create_app_code() {
    log_step "创建应用代码..."
    
    # 创建主应用文件
    cat > "$QWEN3_HOME/app/app.py" << 'EOF'
#!/usr/bin/env python3
"""
Qwen-3 服务器应用
"""

import os
import sys
import yaml
import logging
from flask import Flask, request, jsonify
from datetime import datetime
import requests
import time
import psutil
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/qwen3/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Prometheus 指标
REQUEST_COUNT = Counter('qwen3_requests_total', 'Total requests', ['model', 'status'])
REQUEST_DURATION = Histogram('qwen3_request_duration_seconds', 'Request duration')
ACTIVE_CONNECTIONS = Gauge('qwen3_active_connections', 'Active connections')
SYSTEM_CPU = Gauge('qwen3_system_cpu_percent', 'CPU usage')
SYSTEM_MEMORY = Gauge('qwen3_system_memory_percent', 'Memory usage')

app = Flask(__name__)

class OllamaClient:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def inference(self, model, prompt, **kwargs):
        """模型推理"""
        start_time = time.time()
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    **kwargs
                },
                timeout=30
            )
            
            duration = time.time() - start_time
            REQUEST_DURATION.observe(duration)
            
            if response.status_code == 200:
                result = response.json()
                REQUEST_COUNT.labels(model=model, status='success').inc()
                return {
                    "status": "success",
                    "response": result.get("response", ""),
                    "model": model,
                    "duration": duration
                }
            else:
                REQUEST_COUNT.labels(model=model, status='error').inc()
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}",
                    "duration": duration
                }
                
        except Exception as e:
            duration = time.time() - start_time
            REQUEST_DURATION.observe(duration)
            REQUEST_COUNT.labels(model=model, status='error').inc()
            logger.error(f"推理错误: {e}")
            return {
                "status": "error",
                "error": str(e),
                "duration": duration
            }

ollama_client = OllamaClient()

@app.route('/health')
def health_check():
    """健康检查"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})
        else:
            return jsonify({"status": "unhealthy", "error": "Ollama not responding"}), 503
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 503

@app.route('/api/v1/inference', methods=['POST'])
def inference():
    """推理接口"""
    ACTIVE_CONNECTIONS.inc()
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
            
        model = data.get('model', 'qwen3:0.6b')
        prompt = data.get('prompt', '')
        
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400
            
        result = ollama_client.inference(model, prompt, **data.get('options', {}))
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"推理接口错误: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        ACTIVE_CONNECTIONS.dec()

@app.route('/api/v1/models')
def list_models():
    """获取模型列表"""
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            data = response.json()
            models = [model['name'] for model in data.get('models', [])]
            return jsonify({"models": models})
        else:
            return jsonify({"error": "Failed to fetch models"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/metrics')
def metrics():
    """Prometheus 指标"""
    # 更新系统指标
    SYSTEM_CPU.set(psutil.cpu_percent())
    SYSTEM_MEMORY.set(psutil.virtual_memory().percent)
    
    return generate_latest()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
EOF

    # 设置权限
    chown "$QWEN3_USER:$QWEN3_USER" "$QWEN3_HOME/app/app.py"
    chmod +x "$QWEN3_HOME/app/app.py"
    
    log_info "应用代码创建完成"
}

# 配置 Supervisor
configure_supervisor() {
    log_step "配置 Supervisor..."
    
    # 创建 Supervisor 配置
    cat > /etc/supervisor/conf.d/qwen3.conf << 'EOF'
[program:qwen3-api]
command=/opt/qwen3/app/venv/bin/gunicorn --bind 0.0.0.0:8000 --workers 4 --timeout 120 app:app
directory=/opt/qwen3/app
user=qwen3
autostart=true
autorestart=true
stderr_logfile=/var/log/qwen3/api_error.log
stdout_logfile=/var/log/qwen3/api_access.log
environment=HOME="/opt/qwen3",PATH="/opt/qwen3/app/venv/bin:%(ENV_PATH)s"
EOF

    # 重新加载 Supervisor 配置
    supervisorctl reread
    supervisorctl update
    supervisorctl start qwen3-api
    
    log_info "Supervisor 配置完成"
}

# 配置 Nginx
configure_nginx() {
    log_step "配置 Nginx..."
    
    # 创建 Nginx 配置
    cat > /etc/nginx/sites-available/qwen3 << 'EOF'
upstream qwen3_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name _;
    
    client_max_body_size 10M;
    
    location / {
        proxy_pass http://qwen3_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 120s;
    }
    
    location /health {
        proxy_pass http://qwen3_backend/health;
        access_log off;
    }
    
    location /metrics {
        proxy_pass http://qwen3_backend/metrics;
        allow 127.0.0.1;
        deny all;
    }
}
EOF

    # 启用站点
    ln -sf /etc/nginx/sites-available/qwen3 /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # 测试配置
    nginx -t
    
    # 重启 Nginx
    systemctl restart nginx
    systemctl enable nginx
    
    log_info "Nginx 配置完成"
}

# 创建管理脚本
create_management_scripts() {
    log_step "创建管理脚本..."
    
    # 创建状态检查脚本
    cat > "$QWEN3_HOME/scripts/status.sh" << 'EOF'
#!/bin/bash

echo "=== Qwen-3 服务状态 ==="
echo

echo "1. Ollama 服务:"
systemctl status ollama --no-pager -l

echo
echo "2. Qwen-3 API 服务:"
supervisorctl status qwen3-api

echo
echo "3. Nginx 服务:"
systemctl status nginx --no-pager -l

echo
echo "4. 系统资源:"
echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')%"
echo "内存: $(free | grep Mem | awk '{printf("%.1f%%", $3/$2 * 100.0)}')"
echo "磁盘: $(df -h / | awk 'NR==2{printf "%s", $5}')"

echo
echo "5. 端口监听:"
netstat -tlnp | grep -E ':(80|8000|11434) '

echo
echo "6. 可用模型:"
curl -s http://localhost:11434/api/tags | python3 -m json.tool 2>/dev/null || echo "无法获取模型列表"
EOF

    # 创建重启脚本
    cat > "$QWEN3_HOME/scripts/restart.sh" << 'EOF'
#!/bin/bash

echo "重启 Qwen-3 服务..."

echo "1. 重启 Ollama..."
systemctl restart ollama
sleep 5

echo "2. 重启 API 服务..."
supervisorctl restart qwen3-api
sleep 3

echo "3. 重启 Nginx..."
systemctl restart nginx

echo "4. 检查服务状态..."
bash /opt/qwen3/scripts/status.sh
EOF

    # 创建日志查看脚本
    cat > "$QWEN3_HOME/scripts/logs.sh" << 'EOF'
#!/bin/bash

case "$1" in
    "api")
        tail -f /var/log/qwen3/api_access.log
        ;;
    "error")
        tail -f /var/log/qwen3/api_error.log
        ;;
    "ollama")
        journalctl -u ollama -f
        ;;
    "nginx")
        tail -f /var/log/nginx/access.log
        ;;
    *)
        echo "使用方法: $0 {api|error|ollama|nginx}"
        echo "  api    - API 访问日志"
        echo "  error  - API 错误日志"
        echo "  ollama - Ollama 服务日志"
        echo "  nginx  - Nginx 访问日志"
        ;;
esac
EOF

    # 设置执行权限
    chmod +x "$QWEN3_HOME/scripts/"*.sh
    chown -R "$QWEN3_USER:$QWEN3_USER" "$QWEN3_HOME/scripts"
    
    log_info "管理脚本创建完成"
}

# 验证部署
verify_deployment() {
    log_step "验证部署..."
    
    # 等待服务启动
    sleep 10
    
    # 检查服务状态
    local services=("ollama" "nginx")
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service"; then
            log_info "$service 服务运行正常"
        else
            log_error "$service 服务未运行"
            return 1
        fi
    done
    
    # 检查 API 服务
    if supervisorctl status qwen3-api | grep -q "RUNNING"; then
        log_info "API 服务运行正常"
    else
        log_error "API 服务未运行"
        return 1
    fi
    
    # 测试 API 接口
    log_info "测试 API 接口..."
    
    local test_result=$(curl -s -X POST http://localhost/api/v1/inference \
        -H "Content-Type: application/json" \
        -d '{"model": "qwen3:0.6b", "prompt": "你好"}' \
        --connect-timeout 10 \
        --max-time 30)
    
    if echo "$test_result" | grep -q "success"; then
        log_info "API 测试成功"
        echo "$test_result" | python3 -m json.tool
    else
        log_warn "API 测试失败或超时"
        echo "响应: $test_result"
    fi
    
    log_info "部署验证完成"
}

# 显示部署信息
show_deployment_info() {
    log_step "部署信息"
    
    echo
    echo "🎉 Qwen-3 服务器部署完成!"
    echo
    echo "📍 服务信息:"
    echo "  - API 地址: http://$(hostname -I | awk '{print $1}')/api/v1/inference"
    echo "  - 健康检查: http://$(hostname -I | awk '{print $1}')/health"
    echo "  - 指标监控: http://$(hostname -I | awk '{print $1}')/metrics"
    echo
    echo "📂 重要路径:"
    echo "  - 应用目录: $QWEN3_HOME"
    echo "  - 日志目录: $QWEN3_LOGS"
    echo "  - 配置目录: $QWEN3_CONFIG"
    echo
    echo "🔧 管理命令:"
    echo "  - 查看状态: bash $QWEN3_HOME/scripts/status.sh"
    echo "  - 重启服务: bash $QWEN3_HOME/scripts/restart.sh"
    echo "  - 查看日志: bash $QWEN3_HOME/scripts/logs.sh [api|error|ollama|nginx]"
    echo
    echo "📋 测试命令:"
    echo "  curl -X POST http://localhost/api/v1/inference \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"model\": \"qwen3:0.6b\", \"prompt\": \"你好，请介绍一下你自己\"}'"
    echo
}

# 主函数
main() {
    echo "🚀 开始 Qwen-3 服务器部署..."
    echo
    
    check_root
    detect_os
    install_system_deps
    create_user_and_dirs
    install_ollama
    download_models
    install_python_app
    create_app_code
    configure_supervisor
    configure_nginx
    create_management_scripts
    verify_deployment
    show_deployment_info
    
    log_info "部署完成! 🎉"
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            echo "Qwen-3 服务器部署脚本"
            echo
            echo "使用方法: bash $0 [选项]"
            echo
            echo "选项:"
            echo "  -h, --help     显示帮助信息"
            echo "  --user USER    指定运行用户 (默认: qwen3)"
            echo "  --home DIR     指定安装目录 (默认: /opt/qwen3)"
            echo
            exit 0
            ;;
        --user)
            QWEN3_USER="$2"
            shift 2
            ;;
        --home)
            QWEN3_HOME="$2"
            shift 2
            ;;
        *)
            log_error "未知选项: $1"
            exit 1
            ;;
    esac
done

# 运行主函数
main
