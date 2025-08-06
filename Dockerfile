# Multi-stage build for Qwen3 Dashboard with CPU-optimized Ollama  
FROM python:3.11-slim as base

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV OLLAMA_HOST=0.0.0.0:11434

# 使用中国镜像源加速下载
RUN rm -f /etc/apt/sources.list.d/* && \
    echo "deb https://mirrors.ustc.edu.cn/debian/ bookworm main contrib non-free" > /etc/apt/sources.list && \
    echo "deb https://mirrors.ustc.edu.cn/debian/ bookworm-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.ustc.edu.cn/debian-security bookworm-security main contrib non-free" >> /etc/apt/sources.list

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    supervisor \
    build-essential \
    procps \
    bc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# 创建应用目录
WORKDIR /app

# 复制requirements.txt并安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

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
COPY docker/model-test.sh /model-test.sh
COPY docker/health-check.sh /health-check.sh
COPY docker/run_dashboard.py /app/run_dashboard.py

# 设置执行权限
RUN chmod +x /entrypoint.sh /ollama-config.sh /model-test.sh /health-check.sh

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
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD /health-check.sh || exit 1

# 设置入口点
ENTRYPOINT ["/entrypoint.sh"]