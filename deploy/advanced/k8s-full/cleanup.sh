#!/bin/bash

# Ollama K8s 清理脚本
# 清理所有相关资源

set -e

echo "🧹 开始清理 Ollama K8s 资源..."

NAMESPACE="ollama-system"

# 删除命名空间（会自动删除其中的所有资源）
if kubectl get namespace "${NAMESPACE}" &> /dev/null; then
    echo "🗑️  删除命名空间 ${NAMESPACE}..."
    kubectl delete namespace "${NAMESPACE}"
    echo "✅ 命名空间已删除"
else
    echo "⚠️  命名空间 ${NAMESPACE} 不存在"
fi

# 清理本地镜像（可选）
echo ""
read -p "是否删除本地 Docker 镜像? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️  清理本地镜像..."
    docker images | grep ollama-qwen | awk '{print $1":"$2}' | xargs -r docker rmi || true
    echo "✅ 本地镜像已清理"
fi

echo ""
echo "🎉 清理完成！"