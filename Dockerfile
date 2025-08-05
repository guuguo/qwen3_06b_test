# Multi-stage build for Qwen3 Dashboard with CPU-optimized Ollama
FROM ubuntu:22.04 as base

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV OLLAMA_HOST=0.0.0.0:11434

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-pip \
    python3.11-dev \
    curl \
    wget \
    supervisor \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 创建应用目录
WORKDIR /app

# 复制requirements.txt并安装Python依赖
COPY requirements.txt .
RUN python3.11 -m pip install --no-cache-dir -r requirements.txt

# 安装Ollama (CPU版本)
RUN curl -fsSL https://ollama.com/install.sh | sh

# 复制应用代码
COPY src/ ./src/
COPY static/ ./static/
COPY templates/ ./templates/
COPY test_datasets/ ./test_datasets/
COPY prompts/ ./prompts/

# 复制配置文件
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/ollama-config.sh /ollama-config.sh
COPY docker/run_dashboard.py /app/run_dashboard.py

# 设置执行权限
RUN chmod +x /entrypoint.sh /ollama-config.sh

# 创建数据目录
RUN mkdir -p /app/data /app/test_results /root/.ollama

# 设置CPU优化的默认环境变量
ENV OLLAMA_NUM_PARALLEL=2
ENV OLLAMA_MAX_LOADED_MODELS=1
ENV OLLAMA_MAX_QUEUE=8
ENV OLLAMA_NUM_THREADS=0
ENV OLLAMA_KEEP_ALIVE=30s
ENV FLASK_HOST=0.0.0.0
ENV FLASK_PORT=5000

# 暴露端口
EXPOSE 5000 11434

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# 设置入口点
ENTRYPOINT ["/entrypoint.sh"]