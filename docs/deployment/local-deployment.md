# Qwen-3 本地部署指南

本指南将帮助你在本地环境部署 Qwen-3 模型，包括 Ollama 集成和简化监控方案。

## 📋 环境要求

### 系统要求
- **操作系统**: macOS 10.15+ 或 Linux (Ubuntu 18.04+)
- **内存**: 8GB+ (推荐 16GB)
- **存储**: 20GB+ 可用空间
- **Python**: 3.8+

### 硬件要求
- **CPU**: 4核心以上 (推荐 8核心)
- **内存**: 8GB+ (0.6B 模型需要约 2-4GB，1.7B 模型需要约 4-8GB)
- **存储**: SSD 推荐，用于更快的模型加载

## 🚀 快速开始

### 步骤 1: 安装 Ollama

如果你还没有安装 Ollama，请按照以下步骤：

```bash
# macOS
curl -fsSL https://ollama.ai/install.sh | sh

# 或者使用 Homebrew
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh
```

### 步骤 2: 启动 Ollama 服务

```bash
# 启动 Ollama 服务
ollama serve

# 验证服务状态
curl http://localhost:11434/api/tags
```

### 步骤 3: 下载 Qwen-3 模型

```bash
# 下载 Qwen-3 0.6B 模型
ollama pull qwen3:0.6b

# 下载 Qwen-3 1.7B 模型（可选）
ollama pull qwen3:1.7b

# 验证模型下载
ollama list
```

### 步骤 4: 测试模型

```bash
# 测试 0.6B 模型
ollama run qwen3:0.6b "你好，请介绍一下你自己"

# 测试 1.7B 模型
ollama run qwen3:1.7b "Hello, can you introduce yourself?"
```

## 🔧 Python 环境设置

### 创建虚拟环境

```bash
# 创建项目目录
mkdir qwen3-deployment
cd qwen3-deployment

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# macOS/Linux
source venv/bin/activate

# Windows
# venv\Scripts\activate
```

### 安装依赖

创建 `requirements.txt` 文件：

```txt
requests>=2.28.0
psutil>=5.9.0
flask>=2.3.0
transformers>=4.30.0
torch>=2.0.0
numpy>=1.24.0
pandas>=2.0.0
matplotlib>=3.7.0
seaborn>=0.12.0
tqdm>=4.65.0
pyyaml>=6.0
click>=8.1.0
```

安装依赖：

```bash
pip install -r requirements.txt
```

## 📊 部署监控组件

### 创建项目结构

```bash
mkdir -p {src,logs,config,tests,scripts}
touch src/__init__.py
```

### 基础配置文件

创建 `config/local_config.yaml`：

```yaml
# Qwen-3 本地部署配置
ollama:
  base_url: "http://localhost:11434"
  timeout: 30
  models:
    - "qwen3:0.6b"
    - "qwen3:1.7b"

monitoring:
  log_dir: "./logs"
  metrics_interval: 60  # 秒
  web_dashboard:
    host: "0.0.0.0"
    port: 5000
    debug: true

performance_testing:
  default_model: "qwen3:0.6b"
  test_prompts:
    - "你好，请介绍一下你自己。"
    - "请解释一下人工智能的基本概念。"
    - "写一个简单的 Python 函数来计算阶乘。"
    - "什么是机器学习？"
    - "请描述一下深度学习的工作原理。"
  
  qps_test:
    concurrent_users: 5
    duration: 60
    
  latency_test:
    iterations: 100
```

### 核心代码文件

创建 `src/ollama_integration.py`：

```python
import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
import logging

class OllamaIntegration:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        
    def check_ollama_status(self) -> bool:
        """检查 Ollama 服务状态"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Ollama 服务检查失败: {e}")
            return False
            
    def list_models(self) -> List[str]:
        """获取可用模型列表"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except Exception as e:
            self.logger.error(f"获取模型列表失败: {e}")
            return []
            
    def inference_with_metrics(self, model: str, prompt: str, **kwargs) -> Dict:
        """带指标收集的推理"""
        start_time = time.time()
        
        request_data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            **kwargs
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=request_data,
                timeout=kwargs.get('timeout', 30)
            )
            end_time = time.time()
            
            if response.status_code == 200:
                result_data = response.json()
                result = {
                    "response": result_data.get("response", ""),
                    "model": model,
                    "prompt_length": len(prompt),
                    "response_length": len(result_data.get("response", "")),
                    "latency_ms": (end_time - start_time) * 1000,
                    "status_code": response.status_code,
                    "timestamp": datetime.now().isoformat(),
                    "status": "success"
                }
            else:
                result = {
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "model": model,
                    "prompt_length": len(prompt),
                    "latency_ms": (end_time - start_time) * 1000,
                    "status_code": response.status_code,
                    "timestamp": datetime.now().isoformat(),
                    "status": "error"
                }
                
        except Exception as e:
            end_time = time.time()
            result = {
                "error": str(e),
                "model": model,
                "prompt_length": len(prompt),
                "latency_ms": (end_time - start_time) * 1000,
                "timestamp": datetime.now().isoformat(),
                "status": "error"
            }
            
        return result

    def health_check(self) -> Dict:
        """健康检查"""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            latency = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                models = self.list_models()
                return {
                    "status": "healthy",
                    "latency_ms": latency,
                    "models_count": len(models),
                    "models": models,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}",
                    "latency_ms": latency,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
```

### 启动脚本

创建 `scripts/start_local_monitoring.py`：

```python
#!/usr/bin/env python3
"""
Qwen-3 本地监控启动脚本
"""

import os
import sys
import yaml
import logging
import argparse
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ollama_integration import OllamaIntegration

def setup_logging(log_level="INFO"):
    """设置日志"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/app.log')
        ]
    )

def load_config(config_path="config/local_config.yaml"):
    """加载配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        return None

def check_prerequisites():
    """检查先决条件"""
    print("🔍 检查环境先决条件...")
    
    # 检查 Python 版本
    if sys.version_info < (3, 8):
        print("❌ Python 版本需要 3.8+")
        return False
        
    # 检查必要目录
    for dir_name in ['logs', 'config']:
        os.makedirs(dir_name, exist_ok=True)
        
    print("✅ 环境检查通过")
    return True

def main():
    parser = argparse.ArgumentParser(description="Qwen-3 本地监控")
    parser.add_argument("--config", default="config/local_config.yaml", help="配置文件路径")
    parser.add_argument("--log-level", default="INFO", help="日志级别")
    parser.add_argument("--test", action="store_true", help="运行快速测试")
    
    args = parser.parse_args()
    
    # 检查先决条件
    if not check_prerequisites():
        sys.exit(1)
        
    # 设置日志
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # 加载配置
    config = load_config(args.config)
    if not config:
        sys.exit(1)
        
    # 初始化 Ollama 集成
    ollama = OllamaIntegration(config['ollama']['base_url'])
    
    print("🚀 启动 Qwen-3 本地监控...")
    
    # 检查 Ollama 服务状态
    if not ollama.check_ollama_status():
        print("❌ Ollama 服务未运行，请先启动 Ollama:")
        print("   ollama serve")
        sys.exit(1)
        
    print("✅ Ollama 服务正常")
    
    # 检查可用模型
    models = ollama.list_models()
    if not models:
        print("❌ 未找到可用模型，请先下载模型:")
        print("   ollama pull qwen3:0.6b")
        sys.exit(1)
        
    print(f"✅ 发现模型: {', '.join(models)}")
    
    if args.test:
        # 运行快速测试
        print("📊 运行快速测试...")
        test_prompt = "你好，请介绍一下你自己。"
        result = ollama.inference_with_metrics("qwen3:0.6b", test_prompt)
        
        if result['status'] == 'success':
            print(f"✅ 测试成功!")
            print(f"   延迟: {result['latency_ms']:.2f}ms")
            print(f"   响应长度: {result['response_length']} 字符")
            print(f"   响应内容: {result['response'][:100]}...")
        else:
            print(f"❌ 测试失败: {result.get('error', '未知错误')}")
    else:
        print("✅ 本地监控已就绪")
        print("💡 使用 --test 参数运行快速测试")
        print("💡 使用 python scripts/performance_test.py 运行性能测试")

if __name__ == "__main__":
    main()
```

## 🧪 验证部署

### 运行健康检查

```bash
# 进入项目目录
cd qwen3-deployment

# 激活虚拟环境
source venv/bin/activate

# 运行健康检查
python scripts/start_local_monitoring.py --test
```

期望输出：
```
🔍 检查环境先决条件...
✅ 环境检查通过
🚀 启动 Qwen-3 本地监控...
✅ Ollama 服务正常
✅ 发现模型: qwen3:0.6b
📊 运行快速测试...
✅ 测试成功!
   延迟: 1234.56ms
   响应长度: 89 字符
   响应内容: 你好！我是Qwen，一个由阿里云开发的大型语言模型...
```

## 🔧 常见问题排查

### Ollama 服务无法启动

```bash
# 检查端口占用
lsof -i :11434

# 重启 Ollama 服务
pkill ollama
ollama serve
```

### 模型下载失败

```bash
# 检查网络连接
curl -I https://ollama.ai

# 手动下载模型
ollama pull qwen3:0.6b --verbose
```

### Python 依赖安装失败

```bash
# 升级 pip
pip install --upgrade pip

# 清除缓存重新安装
pip cache purge
pip install -r requirements.txt --no-cache-dir
```

### 内存不足

- 确保至少有 8GB 可用内存
- 关闭其他占用内存的应用程序
- 考虑使用 0.6B 模型而不是 1.7B 模型

## 📈 下一步

部署成功后，你可以：

1. **运行性能测试**: 参考 [性能测试指南](../performance/testing-guide.md)
2. **设置监控**: 参考 [本地监控方案](../monitoring/local-monitoring.md)
3. **开始微调**: 参考 [微调指南](../fine-tuning/training-guide.md)

## 🆘 获取帮助

如果遇到问题：

1. 查看 [故障排查指南](../monitoring/troubleshooting.md)
2. 检查日志文件 `logs/app.log`
3. 确认环境要求是否满足
4. 提交 Issue 并附上详细的错误信息
