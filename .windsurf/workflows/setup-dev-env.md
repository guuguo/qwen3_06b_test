---
description: 配置Qwen-3开发环境的标准流程
---

# 开发环境配置工作流

这个工作流用于快速配置Qwen-3项目的开发环境。

## 1. 环境准备

```bash
# 检查Python版本（需要3.8+）
python --version

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
```

## 2. 安装依赖

```bash
# 安装项目依赖
pip install -r requirements.txt

# 验证关键依赖
python -c "import yaml, flask, requests; print('核心依赖安装成功')"
```

## 3. 配置文件设置

```bash
# 检查配置目录
ls -la config/

# 复制默认配置（如果需要）
if [ ! -f config/local.yaml ]; then
    cp config/default.yaml config/local.yaml
    echo "已创建本地配置文件"
fi
```

## 4. 创建必要目录

```bash
# 创建日志目录
mkdir -p logs

# 创建测试结果目录
mkdir -p test_results

# 创建静态文件目录
mkdir -p static

# 设置权限
chmod 755 logs test_results static
```

## 5. 验证Ollama连接

```bash
# 检查Ollama服务状态
curl -s http://localhost:11434/api/tags || echo "Ollama服务未启动，请先启动Ollama"

# 验证模型可用性
python -c "
from src.ollama_integration import create_ollama_client
client = create_ollama_client()
models = client.list_models()
print(f'可用模型: {[m[\"name\"] for m in models]}')
"
```

## 6. 初始化测试数据

```bash
# 检查测试数据集
ls -la test_datasets/

# 验证测试数据格式
python -c "
from src.test_dataset_manager import TestDatasetManager
tdm = TestDatasetManager()
datasets = tdm.list_available_datasets()
print(f'可用测试集: {datasets}')
"
```

## 7. 运行健康检查

```bash
# 启动服务进行健康检查
python main.py --environment local --port 8080 &
PID=$!

# 等待服务启动
sleep 10

# 检查服务状态
curl -s http://localhost:8080/api/status | python -m json.tool

# 停止测试服务
kill $PID
```

## 8. IDE配置建议

### VSCode配置
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    }
}
```

### 调试配置
```json
{
    "name": "Qwen-3 Debug",
    "type": "python",
    "request": "launch",
    "program": "main.py",
    "args": ["--environment", "local", "--port", "8080"],
    "console": "integratedTerminal"
}
```

## 开发建议

1. **使用虚拟环境**: 避免依赖冲突
2. **配置热重载**: 开发时启用配置文件热重载
3. **日志级别**: 开发环境使用DEBUG级别
4. **测试驱动**: 修改代码后及时运行测试

## 故障排除

1. **依赖安装失败**: 检查网络连接和pip源配置
2. **权限问题**: 确保目录有正确的读写权限
3. **端口冲突**: 使用不同端口或停止冲突服务
4. **配置错误**: 检查YAML文件格式和路径
