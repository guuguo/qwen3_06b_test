---
description: 项目规范和最佳实践指南
---

# 项目开发规范工作流

这个工作流定义了Qwen-3项目的开发规范和最佳实践。

## 1. 代码结构规范

### 目录结构
```
qwen3-project/
├── src/                    # 核心源代码
│   ├── config_manager.py   # 配置管理
│   ├── ollama_integration.py # Ollama集成
│   ├── local_dashboard.py  # Web界面
│   ├── local_tester.py     # 测试工具
│   └── test_dataset_manager.py # 数据集管理
├── config/                 # 配置文件
├── templates/              # HTML模板
├── test_datasets/          # 测试数据集
├── test_results/           # 测试结果
├── logs/                   # 日志文件
└── docs/                   # 文档
```

### 模块命名规范
- 使用小写字母和下划线
- 模块名应该简洁且描述性强
- 避免使用缩写，除非是通用缩写

## 2. 配置管理规范

### 配置文件结构
```yaml
# 环境配置
environment: local

# Ollama配置
ollama:
  base_url: "http://localhost:11434"
  timeout: 30
  models:
    - "qwen3:0.6b"
    - "qwen3:1.7b"

# 监控配置
monitoring:
  enabled: true
  interval: 5
  metrics:
    - "cpu"
    - "memory"
    - "disk"

# 测试配置
testing:
  default_sample_count: 10
  timeout: 30
  output_dir: "./test_results"
```

### 配置使用规范
```python
# 正确的配置获取方式
from src.config_manager import get_config

# 获取配置值
base_url = get_config('ollama.base_url', 'http://localhost:11434')
timeout = get_config('ollama.timeout', 30)

# 获取配置段
ollama_config = get_config_section('ollama')
```

## 3. 日志记录规范

### 日志级别使用
- **DEBUG**: 详细的调试信息
- **INFO**: 一般信息，程序正常运行
- **WARNING**: 警告信息，可能的问题
- **ERROR**: 错误信息，功能异常
- **CRITICAL**: 严重错误，系统无法继续

### 日志格式规范
```python
import logging

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/qwen3.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 使用示例
logger.info("服务启动成功")
logger.warning("配置文件未找到，使用默认配置")
logger.error("模型连接失败: %s", error_msg)
```

## 4. 错误处理规范

### 异常处理模式
```python
# 标准异常处理
try:
    result = risky_operation()
except SpecificException as e:
    logger.error("特定错误: %s", e)
    return None
except Exception as e:
    logger.error("未知错误: %s", e)
    raise
finally:
    cleanup_resources()
```

### 自定义异常
```python
class Qwen3Exception(Exception):
    """Qwen-3基础异常类"""
    pass

class ConfigurationError(Qwen3Exception):
    """配置错误"""
    pass

class ModelConnectionError(Qwen3Exception):
    """模型连接错误"""
    pass
```

## 5. 测试规范

### 测试数据集格式
```json
{
    "name": "sentiment_analysis",
    "description": "情感分析测试集",
    "version": "1.0",
    "samples": [
        {
            "id": "sample_001",
            "content": "这个产品真的很棒！",
            "category": "positive",
            "expected_score": 4.5,
            "keywords": ["产品", "棒"],
            "expected_response": "积极情感，评分4-5分"
        }
    ]
}
```

### 测试用例编写
```python
def test_model_response():
    """测试模型响应功能"""
    # 准备测试数据
    test_input = "测试文本"
    expected_category = "positive"
    
    # 执行测试
    result = model.predict(test_input)
    
    # 验证结果
    assert result is not None
    assert result.get('category') == expected_category
    assert 0 <= result.get('score', 0) <= 5
```

## 6. API设计规范

### RESTful API规范
```python
# 状态查询
GET /api/status
GET /api/models

# 测试执行
POST /api/test/single
POST /api/test/dataset

# 结果查询
GET /api/results
GET /api/results/{test_id}
```

### 响应格式规范
```json
{
    "success": true,
    "data": {
        "result": "响应数据"
    },
    "message": "操作成功",
    "timestamp": "2024-01-01T00:00:00Z"
}
```

## 7. 性能优化规范

### 缓存策略
- 配置数据缓存
- 模型响应缓存
- 测试结果缓存

### 资源管理
- 及时关闭文件句柄
- 合理使用内存
- 避免内存泄漏

## 8. 安全规范

### 输入验证
- 验证所有用户输入
- 防止SQL注入
- 防止XSS攻击

### 配置安全
- 敏感信息使用环境变量
- 不在代码中硬编码密钥
- 定期更新依赖包

## 开发检查清单

- [ ] 代码符合PEP 8规范
- [ ] 添加适当的日志记录
- [ ] 编写单元测试
- [ ] 更新文档
- [ ] 配置验证
- [ ] 错误处理完整
- [ ] 性能测试通过
