#!/bin/bash

# Ollama K8s 快速启动脚本
# 一键构建、部署并测试 Ollama 服务

set -e

echo "🚀 Ollama K8s 快速部署开始..."
echo ""

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 检查是否有 Docker 和 kubectl
if ! command -v docker &> /dev/null; then
    echo "❌ 请先安装 Docker"
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    echo "❌ 请先安装 kubectl"
    exit 1
fi

# 执行完整部署
echo "📦 开始构建和部署..."
"${SCRIPT_DIR}/deploy.sh" all

echo ""
echo "🎉 部署完成！"
echo ""
echo "📋 快速访问指南:"
echo "1. 端口转发: kubectl port-forward -n ollama-system svc/ollama-service 11434:11434"
echo "2. 测试 API: curl http://localhost:11434/api/tags"
echo "3. 测试推理: curl -X POST http://localhost:11434/api/generate -H 'Content-Type: application/json' -d '{\"model\": \"qwen3:0.6b\", \"prompt\": \"你好\", \"stream\": false}'"
echo ""
echo "🔍 查看状态: ${SCRIPT_DIR}/deploy.sh status"
echo "📝 查看日志: ${SCRIPT_DIR}/deploy.sh logs"
echo "🧪 运行测试: ${SCRIPT_DIR}/deploy.sh test"
echo ""