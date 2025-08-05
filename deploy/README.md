# Ollama 部署方案

多种部署方式，适合不同用户需求。

## 🎯 选择适合你的方案

### 🐳 Docker 版本 (推荐新手)
**适合人群**: 纯小白，只想快速体验
**要求**: 只需要 Docker
**特点**: 超简单，一键启动

```bash
cd docker/
./run.sh
```

### ☸️ K8s 版本 (简化版)
**适合人群**: 有基础的用户，想要生产级部署
**要求**: Docker + kubectl + Kubernetes 集群
**特点**: 高可用，易扩展

```bash
cd k8s/
./quick-start.sh
```

### 🔧 高级版本
**适合人群**: 专业用户，需要完整功能
**要求**: 深度定制需求
**特点**: 功能最全，配置最灵活

```bash
cd advanced/k8s-full/
./deploy.sh all
```

## 📁 目录结构

```
deploy/
├── docker/              # Docker 部署 (超简单)
│   ├── run.sh           # 一键启动脚本 ⭐
│   ├── Dockerfile       # 容器定义
│   └── README.md        # 使用说明
├── k8s/                 # K8s 部署 (简化版)
│   ├── quick-start.sh   # 一键部署脚本 ⭐
│   ├── deployment.yaml  # 核心配置
│   └── README.md        # 使用说明
└── advanced/            # 高级配置
    ├── k8s-full/        # 完整 K8s 配置
    └── scripts/         # 工具脚本
```

## 🚀 快速开始建议

1. **完全新手** → 使用 `docker/` 目录
2. **有一定基础** → 使用 `k8s/` 目录  
3. **专业用户** → 使用 `advanced/` 目录

## 💡 常见问题

**Q: 我应该选择哪个版本？**
A: 如果你是纯小白，强烈推荐 Docker 版本。如果你有 K8s 集群，可以试试 K8s 版本。

**Q: Docker 版本和 K8s 版本有什么区别？**
A: Docker 版本更简单，适合单机运行；K8s 版本适合生产环境，支持高可用和扩展。

**Q: 我需要修改配置吗？**
A: 不需要！所有版本都是开箱即用的。
