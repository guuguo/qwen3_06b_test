# Ollama Docker 部署 (超简单版)

一键运行 Ollama + Qwen 0.6b 模型，无需复杂配置。

## 🚀 快速开始

### 前置要求
- 只需要 Docker (下载: https://www.docker.com/products/docker-desktop)

### 一键启动
```bash
./run.sh
```

就这么简单！脚本会自动：
1. 构建包含 Qwen 0.6b 模型的镜像
2. 启动 Ollama 服务
3. 显示使用方法

### 使用服务
```bash
# 测试服务
curl http://localhost:11434/api/tags

# 聊天测试
curl -X POST http://localhost:11434/api/generate \
  -H 'Content-Type: application/json' \
  -d '{"model": "qwen3:0.6b", "prompt": "你好", "stream": false}'
```

### 管理服务
```bash
# 查看状态
docker ps | grep ollama-qwen

# 查看日志
docker logs ollama-qwen

# 停止服务
docker stop ollama-qwen

# 删除服务
docker rm ollama-qwen
```

## 📁 文件说明

- `run.sh` - 一键启动脚本 (这是你唯一需要的文件!)
- `Dockerfile` - 容器构建配置
- `README.md` - 使用说明

## 💡 优势

- ✅ **超简单** - 只需要一条命令
- ✅ **零配置** - 无需修改任何文件
- ✅ **自动重启** - Docker 重启后服务自动启动
- ✅ **数据持久化** - 模型数据不会丢失

## 🆚 对比其他方案

- **Docker 版本** (当前) - 适合小白，只要有 Docker 就行
- **K8s 版本** (`../k8s/`) - 适合生产环境，需要 Kubernetes 集群
- **高级版本** (`../advanced/`) - 适合专业用户，功能最全
