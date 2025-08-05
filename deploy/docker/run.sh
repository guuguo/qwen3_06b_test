#!/bin/bash

# Ollama Docker 一键运行脚本 (超简单版)
# 适合纯小白用户

set -e

echo "🐳 Ollama Docker 一键启动..."
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ 请先安装 Docker"
    echo "💡 下载地址: https://www.docker.com/products/docker-desktop"
    exit 1
fi

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "📦 1. 构建 Ollama 镜像 (首次运行需要几分钟)..."
docker build -t ollama-qwen:simple "${SCRIPT_DIR}"

echo "🚀 2. 启动 Ollama 服务..."
docker run -d \
  --name ollama-qwen \
  -p 11434:11434 \
  -v ollama-data:/home/ollama/.ollama \
  --restart unless-stopped \
  ollama-qwen:simple

echo "⏳ 3. 等待服务启动..."
sleep 10

echo ""
echo "🎉 启动完成！"
echo ""
echo "📋 使用方法:"
echo "1. 测试服务: curl http://localhost:11434/api/tags"
echo "2. 聊天测试: curl -X POST http://localhost:11434/api/generate -H 'Content-Type: application/json' -d '{\"model\": \"qwen3:0.6b\", \"prompt\": \"你好\", \"stream\": false}'"
echo ""
echo "🔍 查看状态: docker ps | grep ollama-qwen"
echo "📝 查看日志: docker logs ollama-qwen"
echo "🛑 停止服务: docker stop ollama-qwen"
echo "🗑️  删除服务: docker rm ollama-qwen"
echo ""
echo "💡 提示: 服务会在 Docker 重启后自动启动"
echo ""
