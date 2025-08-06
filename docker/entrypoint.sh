#!/bin/bash
set -e

echo "🚀 Starting Qwen3 Dashboard Container..."

# 创建必要的目录
mkdir -p /var/log/supervisor
mkdir -p /app/data
mkdir -p /app/test_results
mkdir -p /root/.ollama

# CPU优化检测和配置
CPU_CORES=$(nproc)
MEMORY_GB=$(free -g | awk 'NR==2{printf "%.0f", $2}')

echo "📊 System Info:"
echo "   CPU Cores: $CPU_CORES"
echo "   Memory: ${MEMORY_GB}GB"

# 根据硬件动态调整参数
if [ $CPU_CORES -ge 16 ]; then
    export OLLAMA_NUM_PARALLEL=${OLLAMA_NUM_PARALLEL:-4}
    export OLLAMA_NUM_THREADS=${OLLAMA_NUM_THREADS:-12}
elif [ $CPU_CORES -ge 8 ]; then
    export OLLAMA_NUM_PARALLEL=${OLLAMA_NUM_PARALLEL:-3}
    export OLLAMA_NUM_THREADS=${OLLAMA_NUM_THREADS:-6}
elif [ $CPU_CORES -ge 4 ]; then
    export OLLAMA_NUM_PARALLEL=${OLLAMA_NUM_PARALLEL:-2}
    export OLLAMA_NUM_THREADS=${OLLAMA_NUM_THREADS:-4}
else
    export OLLAMA_NUM_PARALLEL=${OLLAMA_NUM_PARALLEL:-1}
    export OLLAMA_NUM_THREADS=${OLLAMA_NUM_THREADS:-2}
fi

# 内存优化
if [ $MEMORY_GB -lt 4 ]; then
    export OLLAMA_MAX_LOADED_MODELS=1
    export OLLAMA_KEEP_ALIVE="15s"
    echo "⚠️  Low memory detected, using conservative settings"
elif [ $MEMORY_GB -lt 8 ]; then
    export OLLAMA_MAX_LOADED_MODELS=1
    export OLLAMA_KEEP_ALIVE="30s"
else
    export OLLAMA_MAX_LOADED_MODELS=${OLLAMA_MAX_LOADED_MODELS:-2}
    export OLLAMA_KEEP_ALIVE=${OLLAMA_KEEP_ALIVE:-"60s"}
fi

echo "🔧 Ollama Configuration:"
echo "   OLLAMA_NUM_PARALLEL=$OLLAMA_NUM_PARALLEL"
echo "   OLLAMA_NUM_THREADS=$OLLAMA_NUM_THREADS"
echo "   OLLAMA_MAX_LOADED_MODELS=$OLLAMA_MAX_LOADED_MODELS"
echo "   OLLAMA_KEEP_ALIVE=$OLLAMA_KEEP_ALIVE"

# 设置权限
chown -R root:root /app
chmod +x /ollama-config.sh

# 健康检查端点
cat > /app/health.py << 'EOF'
#!/usr/bin/env python3
from flask import Flask, jsonify
import requests
import sys

app = Flask(__name__)

@app.route('/health')
def health():
    try:
        # 检查Ollama服务
        ollama_response = requests.get('http://localhost:11434/api/tags', timeout=5)
        ollama_ok = ollama_response.status_code == 200
        
        # 检查Flask应用（通过导入测试）
        try:
            from src.local_dashboard import LocalDashboard
            flask_ok = True
        except:
            flask_ok = False
        
        if ollama_ok and flask_ok:
            return jsonify({
                'status': 'healthy',
                'ollama': 'ok',
                'flask': 'ok',
                'timestamp': str(__import__('datetime').datetime.now())
            }), 200
        else:
            return jsonify({
                'status': 'unhealthy',
                'ollama': 'ok' if ollama_ok else 'error',
                'flask': 'ok' if flask_ok else 'error'
            }), 503
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
EOF

# 启动健康检查服务（后台）
python /app/health.py &

echo "✅ Starting services with supervisor..."

# 启动supervisor
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf