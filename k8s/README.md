# Ollama K8s 部署方案

一键构建和部署包含 Ollama 和 Qwen 0.6b 模型的 Kubernetes 服务，提供高可用的 AI 推理接口。

## 🚀 快速开始

### 前置要求

- Docker (用于构建镜像)
- kubectl (用于 K8s 操作)
- 可用的 Kubernetes 集群
- 至少 4GB 内存和 10GB 存储空间

### 一键部署

```bash
# 快速部署 (推荐)
./quick-start.sh

# 或者使用完整部署脚本
./deploy.sh all
```

### 验证部署

```bash
# 查看部署状态
./deploy.sh status

# 查看服务日志
./deploy.sh logs

# 测试服务
./deploy.sh test
```

## 📁 文件结构

```
k8s/
├── Dockerfile              # Ollama 容器镜像定义
├── start-ollama.sh         # 容器启动脚本
├── health-check.sh         # 健康检查脚本
├── namespace.yaml          # K8s 命名空间
├── configmap.yaml          # 配置文件
├── storage.yaml            # 持久化存储
├── deployment.yaml         # 应用部署
├── service.yaml            # 服务暴露
├── ingress.yaml            # 外部访问 (可选)
├── deploy.sh               # 主部署脚本
├── quick-start.sh          # 快速启动脚本
├── cleanup.sh              # 清理脚本
└── README.md               # 文档
```

## 🛠️ 详细使用

### 部署脚本选项

```bash
./deploy.sh [选项] [命令]

命令:
  build       构建 Docker 镜像
  deploy      部署到 K8s 集群
  undeploy    从 K8s 集群删除
  status      查看部署状态
  logs        查看服务日志
  test        测试服务
  all         执行 build + deploy

选项:
  -r, --registry REGISTRY   Docker 镜像仓库前缀
  -t, --tag TAG             镜像标签 (默认: latest)
  -n, --namespace NS        K8s 命名空间 (默认: ollama-system)
  -h, --help                显示帮助信息
```

### 访问服务

部署成功后，服务可通过以下方式访问：

#### 1. 端口转发 (推荐测试)

```bash
kubectl port-forward -n ollama-system svc/ollama-service 11434:11434
```

然后访问: `http://localhost:11434`

#### 2. NodePort (集群外访问)

```bash
# 获取节点端口
kubectl get svc ollama-nodeport -n ollama-system

# 访问: http://<NODE_IP>:30434
```

#### 3. 集群内访问

服务地址: `http://ollama-service.ollama-system.svc.cluster.local:11434`

### API 使用示例

```bash
# 检查可用模型
curl http://localhost:11434/api/tags

# 文本生成
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3:0.6b",
    "prompt": "你好，请介绍一下你自己",
    "stream": false
  }'

# 流式生成
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3:0.6b",
    "prompt": "讲一个故事",
    "stream": true
  }'
```

## ⚙️ 配置说明

### 资源配置

可以在 `deployment.yaml` 中调整资源配置：

```yaml
resources:
  requests:
    memory: "2Gi"    # 最小内存
    cpu: "1000m"     # 最小 CPU
  limits:
    memory: "4Gi"    # 最大内存
    cpu: "2000m"     # 最大 CPU
```

### 存储配置

在 `storage.yaml` 中配置持久化存储：

```yaml
resources:
  requests:
    storage: 10Gi    # 模型存储空间
```

### 环境变量

在 `configmap.yaml` 中配置服务参数：

```yaml
data:
  OLLAMA_HOST: "0.0.0.0"
  OLLAMA_PORT: "11434"
  MODEL_NAME: "qwen3:0.6b"
  OLLAMA_NUM_PARALLEL: "4"        # 并行请求数
  OLLAMA_MAX_LOADED_MODELS: "1"   # 最大加载模型数
```

## 🔍 监控和诊断

### 查看 Pod 状态

```bash
kubectl get pods -n ollama-system -o wide
```

### 查看服务日志

```bash
kubectl logs -n ollama-system deployment/ollama-deployment -f
```

### 进入容器调试

```bash
kubectl exec -it -n ollama-system deployment/ollama-deployment -- /bin/bash
```

### 检查存储

```bash
kubectl get pvc -n ollama-system
```

## 🔧 高级配置

### GPU 支持

如果集群支持 GPU，可以在 `deployment.yaml` 中添加：

```yaml
resources:
  limits:
    nvidia.com/gpu: 1

nodeSelector:
  gpu: "true"
```

### 多副本部署

```yaml
spec:
  replicas: 3  # 增加副本数
```

### 自定义镜像仓库

```bash
# 使用私有仓库
./deploy.sh -r your-registry.com build
./deploy.sh -r your-registry.com deploy
```

### Ingress 配置

如果需要通过域名访问，编辑 `ingress.yaml`：

```yaml
rules:
- host: ollama.yourdomain.com
  http:
    paths:
    - path: /
      pathType: Prefix
      backend:
        service:
          name: ollama-service
          port:
            number: 11434
```

然后应用配置：

```bash
kubectl apply -f ingress.yaml
```

## 🧹 清理资源

### 删除部署

```bash
./deploy.sh undeploy
```

### 完全清理

```bash
./cleanup.sh
```

## ❗ 故障排除

### 常见问题

1. **Pod 启动失败**
   ```bash
   kubectl describe pod -n ollama-system <pod-name>
   kubectl logs -n ollama-system <pod-name>
   ```

2. **模型下载慢**
   - 检查网络连接
   - 考虑预先下载模型到 PV

3. **内存不足**
   - 增加资源限制
   - 检查节点可用资源

4. **存储权限问题**
   ```bash
   # 检查 PVC 状态
   kubectl get pvc -n ollama-system
   # 检查存储类
   kubectl get storageclass
   ```

### 健康检查

服务包含完整的健康检查：

- **启动探针**: 检查服务是否启动
- **就绪探针**: 检查服务是否准备接收流量  
- **活跃探针**: 检查服务是否健康运行

### 性能调优

1. **CPU 密集型负载**：增加 CPU 限制
2. **内存不足**：增加内存限制
3. **并发优化**：调整 `OLLAMA_NUM_PARALLEL`
4. **存储性能**：使用 SSD 存储类

## 📝 开发和定制

### 修改模型

1. 编辑 `configmap.yaml` 中的 `MODEL_NAME`
2. 重新构建镜像: `./deploy.sh build`
3. 重新部署: `./deploy.sh deploy`

### 添加额外模型

修改 `start-ollama.sh` 脚本，添加多个模型拉取命令。

### 自定义配置

所有配置都在 YAML 文件中，可以根据需要修改。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个部署方案。

## 📄 许可证

本项目采用 MIT 许可证。