# 代码评审工作流

## 概述
专门用于开发完成后的代码评审，确保代码质量、可行性和结构合理性。包含自动化测试脚本生成和执行功能。

## 适用场景
- 新功能开发完成后的代码评审
- 重要功能修改后的质量检查
- 发布前的代码质量保证
- 代码重构后的验证

## 评审检查项

### 1. 代码质量检查
- **代码规范性**：检查代码风格、命名规范、注释完整性
- **代码复杂度**：分析函数复杂度、嵌套层级、代码重复度
- **错误处理**：检查异常处理的完整性和合理性
- **性能考虑**：识别潜在的性能问题和优化点

### 2. 功能可行性分析
- **逻辑正确性**：验证业务逻辑的正确性
- **边界条件**：检查边界情况的处理
- **数据流验证**：确保数据在各模块间正确流转
- **依赖关系**：检查模块依赖的合理性

### 3. 架构和结构评估
- **模块设计**：评估模块划分的合理性
- **接口设计**：检查API接口的设计和文档
- **扩展性**：评估代码的可扩展性和维护性
- **安全性**：识别潜在的安全风险

### 4. 自动化测试
- **单元测试**：为核心功能生成单元测试
- **集成测试**：创建模块间集成测试
- **边界测试**：生成边界条件测试用例
- **性能测试**：必要时创建性能测试脚本

## 使用指南

### 步骤1：启动代码评审
```
请对以下代码进行全面评审：

[代码路径或具体代码]

需要评审的方面：
- 代码质量和规范性
- 功能逻辑的正确性
- 架构设计的合理性
- 需要生成的测试用例
```

### 步骤2：代码质量分析
评审工具将分析：
- **语法和风格**：PEP 8规范、命名规范、代码格式
- **复杂度指标**：圈复杂度、认知复杂度、代码行数
- **代码重复**：重复代码片段识别和优化建议
- **依赖分析**：模块依赖关系和循环依赖检测

### 步骤3：功能验证
- **逻辑检查**：验证算法逻辑、条件判断、循环控制
- **数据处理**：检查数据验证、类型转换、边界处理
- **错误处理**：异常捕获、错误传播、恢复机制
- **资源管理**：内存使用、文件操作、网络连接管理

### 步骤4：测试脚本生成
自动生成临时测试文件：

**单元测试模板**：
```python
# /tmp/test_[module_name]_[timestamp].py
import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from [module_path] import [functions_to_test]

class Test[ModuleName](unittest.TestCase):
    def setUp(self):
        """测试前准备"""
        pass
    
    def test_[function_name]_normal_case(self):
        """正常情况测试"""
        # 测试正常输入
        pass
    
    def test_[function_name]_boundary_case(self):
        """边界条件测试"""
        # 测试边界值
        pass
    
    def test_[function_name]_error_case(self):
        """异常情况测试"""
        # 测试异常输入
        pass
    
    def tearDown(self):
        """测试后清理"""
        pass

if __name__ == '__main__':
    unittest.main()
```

**集成测试模板**：
```python
# /tmp/integration_test_[feature_name]_[timestamp].py
import unittest
import tempfile
import shutil
from unittest.mock import Mock, patch

class Integration[FeatureName]Test(unittest.TestCase):
    def setUp(self):
        """创建测试环境"""
        self.test_dir = tempfile.mkdtemp()
        
    def test_[workflow_name](self):
        """测试完整工作流"""
        # 模拟完整的用户操作流程
        pass
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
```

### 步骤5：执行测试和清理
```bash
# 运行生成的测试
python /tmp/test_[module_name]_[timestamp].py

# 测试完成后自动清理临时文件
rm /tmp/test_*_[timestamp].py
```

## 评审报告模板

### 代码质量评分
- **整体评分**：[A/B/C/D] (90-100/80-89/70-79/60-69分)
- **代码规范**：[优秀/良好/一般/需改进]
- **复杂度控制**：[优秀/良好/一般/需改进]
- **错误处理**：[完善/基本完善/有缺陷/严重不足]

### 主要发现
**优点**：
- 列出代码的优秀之处
- 好的设计模式使用
- 高质量的实现

**需要改进的地方**：
- 具体的问题描述
- 改进建议
- 优先级标记

**潜在风险**：
- 安全性问题
- 性能瓶颈
- 维护性问题

### 测试结果
- **单元测试**：通过率 [x]%，共[x]个测试用例
- **集成测试**：通过率 [x]%，共[x]个测试场景
- **覆盖率**：代码覆盖率 [x]%
- **性能测试**：响应时间、内存使用等指标

### 改进建议
1. **立即修复**（高优先级）
   - 安全漏洞
   - 逻辑错误
   - 严重性能问题

2. **近期改进**（中优先级）
   - 代码重构
   - 性能优化
   - 错误处理完善

3. **长期优化**（低优先级）
   - 架构优化
   - 文档完善
   - 测试增强

## 自动化工具集成

### 静态代码分析
```bash
# Python代码质量检查
flake8 [file_path] --max-line-length=100
pylint [file_path] --rcfile=.pylintrc
black --check [file_path]

# 安全性检查
bandit -r [directory_path]

# 复杂度分析
radon cc [file_path] -a
radon mi [file_path]
```

### 测试执行
```bash
# 单元测试
pytest [test_files] -v --cov=[module_path] --cov-report=html

# 性能测试
python -m cProfile -o profile_output.prof [script_path]
```

## 最佳实践

### 评审准备
1. **代码准备**：确保代码已提交到版本控制系统
2. **文档更新**：确保相关文档已更新
3. **自测完成**：开发者已进行基本自测

### 评审过程
1. **系统性检查**：按照检查清单逐项检查
2. **上下文理解**：理解代码的业务背景和设计意图
3. **建设性反馈**：提供具体的改进建议而非仅指出问题

### 评审后续
1. **问题跟踪**：创建问题清单并跟踪解决进度
2. **验证修复**：对修复的问题进行验证
3. **经验总结**：记录评审中发现的通用问题和解决方案

## 临时文件管理

### 测试文件命名规范
```
/tmp/test_[module_name]_[YYYYMMDD_HHMMSS].py
/tmp/integration_test_[feature_name]_[YYYYMMDD_HHMMSS].py
/tmp/performance_test_[component_name]_[YYYYMMDD_HHMMSS].py
```

### 自动清理机制
```python
import os
import glob
import time

def cleanup_temp_test_files(max_age_hours=24):
    """清理超过指定时间的临时测试文件"""
    pattern = "/tmp/test_*_*.py"
    current_time = time.time()
    
    for filepath in glob.glob(pattern):
        file_age = current_time - os.path.getctime(filepath)
        if file_age > max_age_hours * 3600:
            os.remove(filepath)
            print(f"已清理过期测试文件: {filepath}")
```

## 示例用法

### 评审Python Flask应用
```
请评审以下Flask应用代码的质量和架构：

文件路径：src/local_dashboard.py
主要功能：本地监控界面，包含系统状态监控和测试集评估

重点关注：
1. API路由设计的合理性
2. 错误处理的完整性
3. 并发安全性
4. 性能优化空间
5. 需要生成相应的测试用例
```

### 评审数据处理模块
```
请评审数据处理模块的实现：

文件路径：src/test_dataset_manager.py
主要功能：测试集管理和数据处理

需要特别检查：
1. 数据验证逻辑
2. 文件操作的安全性
3. 内存使用效率
4. 异常情况处理
5. 创建边界条件测试
```

## 注意事项

1. **隐私保护**：不要在测试文件中包含敏感信息
2. **资源清理**：测试完成后及时清理临时文件
3. **环境隔离**：测试应在隔离环境中进行
4. **版本兼容**：考虑不同Python版本的兼容性
5. **依赖管理**：确保测试环境的依赖完整

## 输出格式

评审完成后，输出结构化的评审报告，包括：
- 执行摘要
- 详细分析结果  
- 生成的测试文件路径
- 改进建议优先级列表
- 后续行动计划