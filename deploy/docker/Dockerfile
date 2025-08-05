# Ollama + Qwen 0.6b 模型容器 (简化版)
FROM ubuntu:22.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV OLLAMA_HOST=0.0.0.0
ENV OLLAMA_PORT=11434

# 安装依赖
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 安装 Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# 创建用户
RUN useradd -m -u 1000 ollama
USER ollama
WORKDIR /home/ollama

# 预下载模型 (构建时)
RUN ollama serve & \
    sleep 15 && \
    ollama pull qwen3:0.6b && \
    pkill ollama

# 暴露端口
EXPOSE 11434

# 启动命令
CMD ["ollama", "serve"]
