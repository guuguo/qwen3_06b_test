#!/bin/bash

# Ollama K8s 一键部署脚本 (简化版)
# 适合新手用户快速体验

set -e

echo "🚀 Ollama K8s 一键部署开始..."
echo ""

# 基础检查
if ! command -v docker &> /dev/null; then
    echo "❌ 请先安装 Docker"
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    echo "❌ 请先安装 kubectl"
    echo "💡 提示: 可以使用 Docker Desktop 内置的 Kubernetes"
    exit 1
fi

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "📦 1. 构建 Ollama 镜像..."
docker build -t ollama-qwen:latest -f "${SCRIPT_DIR}/../advanced/k8s-full/Dockerfile" "${SCRIPT_DIR}/../advanced/k8s-full/"

echo "🚀 2. 部署到 Kubernetes..."
kubectl apply -f "${SCRIPT_DIR}/deployment.yaml"

echo "⏳ 3. 等待服务启动..."
kubectl wait --for=condition=available --timeout=300s deployment/ollama-deployment -n ollama-system

echo ""
echo "🎉 部署完成！"
echo ""
echo "📋 使用方法:"
echo "1. 端口转发: kubectl port-forward -n ollama-system svc/ollama-service 11434:11434"
echo "2. 测试服务: curl http://localhost:11434/api/tags"
echo "3. 聊天测试: curl -X POST http://localhost:11434/api/generate -H 'Content-Type: application/json' -d '{\"model\": \"qwen3:0.6b\", \"prompt\": \"你好\", \"stream\": false}'"
echo ""
echo "🗑️  删除部署: kubectl delete -f ${SCRIPT_DIR}/deployment.yaml"
echo ""
