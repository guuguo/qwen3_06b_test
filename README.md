# Qwen3 Dashboard - AI模型性能测试与管理平台

[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.11-green.svg)](https://python.org)
[![Ollama](https://img.shields.io/badge/Ollama-Integrated-orange.svg)](https://ollama.ai/)

一个专为Qwen3模型设计的Web管理平台，集成了性能测试、模型管理、系统监控等功能。支持CPU优化的Docker一键部署。

## ✨ 核心功能

### 🎯 模型管理
- **一键下载**: Web界面直接下载模型，支持镜像源
- **模型列表**: 查看已安装模型的详细信息
- **智能删除**: 安全删除不需要的模型
- **CPU优化**: 自动选择最适合CPU推理的量化版本

### 📊 性能测试
- **QPS测试**: 多并发压力测试，实时监控
- **延迟分析**: P95/P99延迟统计和分布图
- **吞吐量评估**: tokens/s性能指标
- **数据集评估**: 自定义测试集准确性评估

### 🖥️ 系统监控  
- **实时指标**: CPU、内存、网络使用情况
- **服务状态**: Ollama服务健康监控
- **性能图表**: 可视化性能趋势
- **日志管理**: 完整的操作日志记录

## 🚀 快速开始

### 方式一：一键部署（推荐）

```bash
# 克隆项目
git clone <repository-url>
cd qwen3-dashboard

# 一键部署
./docker/deploy.sh

# 访问Web界面
open http://localhost:5000
```

### 方式二：Docker Compose

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 方式三：手动Docker

```bash
# 构建镜像
docker build -t qwen3-dashboard .

# 运行容器
docker run -d \
  --name qwen3-dashboard \
  -p 5000:5000 -p 11434:11434 \
  -v qwen3_models:/root/.ollama \
  --cpus="8" --memory="6g" \
  qwen3-dashboard
```

## 💻 系统要求

### 最低配置
- **CPU**: 2核心
- **内存**: 2GB
- **存储**: 5GB可用空间
- **系统**: Linux/macOS/Windows (Docker支持)

### 推荐配置  
- **CPU**: 8核心+ (更好的并发性能)
- **内存**: 8GB+ (支持更大模型)
- **存储**: 20GB+ SSD (更快的模型加载)

### CPU优化参数

系统会根据硬件自动调优，也可以手动配置：

```yaml
environment:
  # 并发配置
  - OLLAMA_NUM_PARALLEL=2      # 并发请求数
  - OLLAMA_NUM_THREADS=8       # CPU线程数 (0=自动)
  
  # 内存优化
  - OLLAMA_MAX_LOADED_MODELS=1 # 同时加载模型数
  - OLLAMA_KEEP_ALIVE=30s      # 模型缓存时间
  
  # 队列管理
  - OLLAMA_MAX_QUEUE=8         # 请求队列长度
```

## 📖 使用指南

### 1. 模型管理

#### 下载推荐的CPU优化模型：
```bash
# Web界面操作或CLI命令
docker-compose exec qwen3-dashboard ollama pull qwen3:0.6b-q4_k_m
```

#### 推荐模型（按性能排序）：
- `qwen3:0.6b-q4_k_m` - 平衡性能和精度 ⭐推荐
- `qwen3:0.6b-q4_0` - 更快推理速度
- `qwen3:0.6b-q8_0` - 更高精度（较慢）
- `qwen3:0.6b` - 原始模型（最慢）

### 2. 性能测试  

#### QPS压力测试：
1. 访问 http://localhost:5000
2. 选择测试场景（轻负载/中负载/高负载）
3. 配置并发用户数和测试时间
4. 查看实时性能指标和测试报告

#### 数据集评估：
1. 选择预置测试集或上传自定义数据
2. 配置评估参数
3. 运行评估并查看详细报告

### 3. 系统监控

- **实时监控**: 访问首页查看系统状态
- **历史数据**: 查看性能趋势图表
- **告警通知**: 系统异常时的状态提醒

## 🔧 配置选项

### 环境变量配置

```bash
# Ollama配置
OLLAMA_HOST=0.0.0.0:11434
OLLAMA_NUM_PARALLEL=2
OLLAMA_NUM_THREADS=8
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_KEEP_ALIVE=30s

# Flask配置  
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_ENV=production

# 预下载模型（可选）
PRELOAD_MODEL=qwen3:0.6b-q4_k_m
```

### 资源限制

```yaml
deploy:
  resources:
    limits:
      cpus: '8.0'      # CPU限制
      memory: 6G       # 内存限制
    reservations:
      cpus: '2.0'      # CPU预留
      memory: 2G       # 内存预留
```

## 📊 性能参考

### CPU性能表现（参考）

| 硬件配置 | QPS | 平均延迟 | P95延迟 | 内存占用 |
|---------|-----|---------|---------|----------|
| 4核8GB  | 2-3 | 1.5-3s  | 3-5s    | 3-4GB    |
| 8核16GB | 4-6 | 0.8-1.5s| 1.5-2.5s| 4-6GB    |
| 16核32GB| 8-12| 0.5-1s  | 1-1.5s  | 6-8GB    |

> 性能会根据具体硬件、模型选择和负载情况有所差异

## 🛠️ 常用命令

```bash
# 服务管理
./docker/deploy.sh start     # 启动服务
./docker/deploy.sh stop      # 停止服务
./docker/deploy.sh restart   # 重启服务
./docker/deploy.sh logs      # 查看日志

# 模型管理
docker-compose exec qwen3-dashboard ollama list
docker-compose exec qwen3-dashboard ollama pull <model-name>
docker-compose exec qwen3-dashboard ollama rm <model-name>

# 容器管理
docker-compose ps           # 查看容器状态
docker-compose exec qwen3-dashboard bash  # 进入容器
```

## 🔍 故障排除

### 常见问题

**1. 服务启动失败**
```bash
# 查看详细日志
docker-compose logs qwen3-dashboard

# 检查端口占用
netstat -tlnp | grep :5000
netstat -tlnp | grep :11434
```

**2. 模型下载慢**
```bash
# 使用镜像源
docker-compose exec qwen3-dashboard ollama pull hf-mirror.com/Qwen/Qwen3-0.6B-GGUF:Q4_K_M
```

**3. 内存不足**  
```bash
# 调整配置
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_KEEP_ALIVE=15s
```

**4. CPU使用率过高**
```bash
# 降低并发
OLLAMA_NUM_PARALLEL=1
OLLAMA_NUM_THREADS=4
```

### 健康检查

```bash
# 检查服务健康状态
curl http://localhost:5000/health

# 检查Ollama API
curl http://localhost:11434/api/tags
```

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📞 支持

- 🐛 [报告Bug](https://github.com/your-repo/issues)
- 💡 [功能建议](https://github.com/your-repo/issues)
- 📖 [文档](https://github.com/your-repo/wiki)

---

⚡ **享受AI模型管理和性能测试的便捷体验！**