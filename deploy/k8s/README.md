# Ollama K8s 部署 (简化版)

一键部署 Ollama + Qwen 0.6b 模型到 Kubernetes 集群。

## 🚀 快速开始

### 前置要求
- Docker (构建镜像)
- kubectl (K8s 命令行工具)
- Kubernetes 集群 (推荐使用 Docker Desktop 内置的 K8s)

### 一键部署
```bash
./quick-start.sh
```

### 使用服务
```bash
# 1. 端口转发
kubectl port-forward -n ollama-system svc/ollama-service 11434:11434

# 2. 测试服务
curl http://localhost:11434/api/tags

# 3. 聊天测试
curl -X POST http://localhost:11434/api/generate \
  -H 'Content-Type: application/json' \
  -d '{"model": "qwen3:0.6b", "prompt": "你好", "stream": false}'
```

### 清理部署
```bash
kubectl delete -f deployment.yaml
```

## 📁 文件说明

- `quick-start.sh` - 一键部署脚本
- `deployment.yaml` - K8s 部署配置 (包含 Namespace + Deployment + Service)

## 💡 提示

- 如果需要更多高级功能，请查看 `../advanced/k8s-full/` 目录
- 如果只想用 Docker 运行，请查看 `../docker/` 目录
