---
description: 启动Qwen-3服务的标准流程
---

# 启动Qwen-3服务工作流

这个工作流用于启动Qwen-3大模型服务的不同模式。

## 1. 检查环境依赖

```bash
# 检查Python环境
python --version

# 检查依赖包
pip install -r requirements.txt
```

## 2. 验证配置文件

```bash
# 检查配置文件是否存在
ls -la config/

# 验证配置格式
python -c "from src.config_manager import get_config_manager; cm = get_config_manager(); print('配置验证通过')"
```

## 3. 启动服务（选择一种模式）

### 完整服务模式
```bash
# 启动完整的Qwen-3服务栈
python main.py --environment local --host 0.0.0.0 --port 8080
```

### 仅启动仪表板
```bash
# 只启动Web监控界面
python main.py --dashboard-only --host 0.0.0.0 --port 8080
```

### 仅启动监控
```bash
# 只启动系统监控
python main.py --monitor-only
```

## 4. 验证服务状态

```bash
# 检查服务是否正常启动
curl http://localhost:8080/api/status

# 查看日志
tail -f logs/qwen3_*.log
```

## 5. 访问服务

- 仪表板: http://localhost:8080
- API文档: http://localhost:8080/api/docs
- 系统状态: http://localhost:8080/api/status

## 故障排除

1. **端口被占用**: 使用 `--port` 参数指定其他端口
2. **配置文件错误**: 检查 `config/` 目录下的YAML文件格式
3. **依赖缺失**: 重新运行 `pip install -r requirements.txt`
4. **Ollama连接失败**: 确保Ollama服务正在运行
