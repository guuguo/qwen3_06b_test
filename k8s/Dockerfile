# Ollama with Qwen 0.6b Model - Production Ready Container
FROM ubuntu:22.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV OLLAMA_HOST=0.0.0.0
ENV OLLAMA_PORT=11434
ENV MODEL_NAME=qwen3:0.6b

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    ca-certificates \
    gnupg \
    lsb-release \
    software-properties-common \
    jq \
    && rm -rf /var/lib/apt/lists/*

# 安装 Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# 创建专用用户
RUN useradd -m -u 1000 ollama && \
    mkdir -p /home/ollama/.ollama && \
    chown -R ollama:ollama /home/ollama

# 设置工作目录
WORKDIR /home/ollama

# 创建启动脚本
COPY start-ollama.sh /home/ollama/start-ollama.sh
RUN chmod +x /home/ollama/start-ollama.sh && \
    chown ollama:ollama /home/ollama/start-ollama.sh

# 创建健康检查脚本
COPY health-check.sh /home/ollama/health-check.sh
RUN chmod +x /home/ollama/health-check.sh && \
    chown ollama:ollama /home/ollama/health-check.sh

# 切换到 ollama 用户
USER ollama

# 预拉取模型(在构建时)
RUN /usr/local/bin/ollama serve & \
    sleep 10 && \
    /usr/local/bin/ollama pull ${MODEL_NAME} && \
    pkill ollama

# 暴露端口
EXPOSE 11434

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /home/ollama/health-check.sh

# 启动服务
CMD ["/home/ollama/start-ollama.sh"]