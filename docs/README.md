# Qwen-3 模型部署与优化文档

本文档库包含 Qwen-3 模型部署、性能测试和微调的完整指南。

## 文档结构

### 📦 部署文档
- [`local-deployment.md`](./deployment/local-deployment.md) - 本地部署完整指南
- [`server-deployment.md`](./deployment/server-deployment.md) - 服务器部署完整指南
- [`kubernetes-deployment.md`](./deployment/kubernetes-deployment.md) - Kubernetes 部署指南

### 🚀 部署脚本
- [`scripts/`](./scripts/) - 自动化部署脚本集合
  - `local_setup.sh` - 本地环境一键安装脚本
  - `server_deploy.sh` - 服务器部署脚本
  - `k8s_deploy.sh` - Kubernetes 部署脚本

### 📊 性能测试
- [`performance/`](./performance/) - 性能测试相关文档
  - `testing-guide.md` - 性能测试指南
  - `optimization-guide.md` - 性能优化指南
  - `benchmark-results.md` - 基准测试结果

### 🔧 微调指南
- [`fine-tuning/`](./fine-tuning/) - 模型微调文档
  - `data-preparation.md` - 数据准备指南
  - `training-guide.md` - 训练流程指南
  - `evaluation-guide.md` - 模型评估指南

### 📈 监控运维
- [`monitoring/`](./monitoring/) - 监控和运维文档
  - `local-monitoring.md` - 本地监控方案
  - `production-monitoring.md` - 生产环境监控
  - `troubleshooting.md` - 故障排查指南

### 🔧 配置参考
- [`config/`](./config/) - 配置文件示例
  - `local-config.yaml` - 本地配置示例
  - `server-config.yaml` - 服务器配置示例
  - `k8s-manifests/` - Kubernetes 配置文件

## 快速开始

1. **本地部署**: 参考 [本地部署指南](./deployment/local-deployment.md)
2. **性能测试**: 参考 [性能测试指南](./performance/testing-guide.md)
3. **监控设置**: 参考 [本地监控方案](./monitoring/local-monitoring.md)

## 环境要求

- Python 3.8+
- 8GB+ 内存（推荐 16GB）
- 50GB+ 可用磁盘空间
- macOS/Linux 操作系统

## 支持的模型

- Qwen-3 0.6B
- Qwen-3 1.7B

## 联系方式

如有问题，请查看 [故障排查指南](./monitoring/troubleshooting.md) 或提交 Issue。
