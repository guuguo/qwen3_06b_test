#!/bin/bash

# Ollama 启动脚本
set -e

echo "=== Ollama 服务启动中 ==="
echo "Host: ${OLLAMA_HOST:-0.0.0.0}"
echo "Port: ${OLLAMA_PORT:-11434}"
echo "Model: ${MODEL_NAME:-qwen3:0.6b}"

# 启动 Ollama 服务
echo "启动 Ollama 服务..."
/usr/local/bin/ollama serve &
OLLAMA_PID=$!

# 等待服务启动
echo "等待 Ollama 服务启动..."
for i in {1..30}; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "Ollama 服务已启动 (尝试 $i/30)"
        break
    fi
    echo "等待服务启动... ($i/30)"
    sleep 2
done

# 检查模型是否存在，如果不存在则拉取
echo "检查模型 ${MODEL_NAME} 是否存在..."
if ! /usr/local/bin/ollama list | grep -q "${MODEL_NAME}"; then
    echo "模型不存在，开始拉取 ${MODEL_NAME}..."
    /usr/local/bin/ollama pull "${MODEL_NAME}"
    echo "模型拉取完成"
else
    echo "模型 ${MODEL_NAME} 已存在"
fi

# 预热模型
echo "预热模型..."
curl -s -X POST http://localhost:11434/api/generate \
    -H "Content-Type: application/json" \
    -d "{\"model\": \"${MODEL_NAME}\", \"prompt\": \"hello\", \"stream\": false}" > /dev/null || true

echo "=== Ollama 服务启动完成 ==="
echo "API 地址: http://localhost:11434"
echo "健康检查: http://localhost:11434/api/tags"

# 保持前台运行
wait $OLLAMA_PID