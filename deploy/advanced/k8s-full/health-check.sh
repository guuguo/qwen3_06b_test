#!/bin/bash

# Ollama 健康检查脚本
set -e

# 检查 Ollama 服务是否响应
if ! curl -s --max-time 5 http://localhost:11434/api/tags > /dev/null; then
    echo "❌ Ollama 服务无响应"
    exit 1
fi

# 检查模型是否可用
MODEL_NAME=${MODEL_NAME:-qwen3:0.6b}
if ! curl -s --max-time 5 http://localhost:11434/api/tags | jq -r '.models[].name' | grep -q "${MODEL_NAME}"; then
    echo "❌ 模型 ${MODEL_NAME} 不可用"
    exit 1
fi

# 简单的推理测试
RESPONSE=$(curl -s --max-time 10 -X POST http://localhost:11434/api/generate \
    -H "Content-Type: application/json" \
    -d "{\"model\": \"${MODEL_NAME}\", \"prompt\": \"hi\", \"stream\": false}" 2>/dev/null || echo "")

if [ -z "$RESPONSE" ] || ! echo "$RESPONSE" | jq -e '.response' > /dev/null 2>&1; then
    echo "❌ 模型推理测试失败"
    exit 1
fi

echo "✅ Ollama 服务健康"
exit 0