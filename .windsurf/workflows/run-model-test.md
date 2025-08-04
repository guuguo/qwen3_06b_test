---
description: 运行模型测试和评估的标准流程
---

# 模型测试评估工作流

这个工作流用于对Qwen-3模型进行标准化测试和性能评估。

## 1. 准备测试环境

```bash
# 确保服务正在运行
python main.py --environment local --host 0.0.0.0 --port 8080 &

# 等待服务启动
sleep 5
```

## 2. 检查测试数据集

```bash
# 列出可用的测试集
python -c "from src.test_dataset_manager import TestDatasetManager; tdm = TestDatasetManager(); print(tdm.list_available_datasets())"

# 验证测试集格式
python -c "from src.test_dataset_manager import TestDatasetManager; tdm = TestDatasetManager(); print(tdm.get_dataset_info('sentiment_analysis'))"
```

## 3. 运行单个测试集评估

```bash
# 运行情感分析测试集
python -c "
from src.local_tester import SimpleLocalTester
tester = SimpleLocalTester()
result = tester.run_dataset_test('sentiment_analysis', 'qwen3:0.6b', sample_count=10)
print(f'测试完成，成功率: {result[\"success_rate\"]:.2%}')
"
```

## 4. 运行批量测试

```bash
# 运行所有测试集的评估
python -c "
from src.local_tester import SimpleLocalTester
tester = SimpleLocalTester()
results = tester.run_all_datasets_test('qwen3:0.6b', sample_count=5)
for result in results:
    print(f'{result[\"dataset_name\"]}: {result[\"success_rate\"]:.2%}')
"
```

## 5. 生成测试报告

```bash
# 查看最新的测试结果
ls -la test_results/

# 生成HTML报告（通过Web界面）
echo "访问 http://localhost:8080 查看详细的测试报告"
```

## 6. 性能基准测试

```bash
# 运行性能测试
python -c "
from src.local_tester import SimpleLocalTester
import time
tester = SimpleLocalTester()
start_time = time.time()
result = tester.test_single_request('测试文本', 'qwen3:0.6b')
end_time = time.time()
print(f'响应时间: {(end_time - start_time) * 1000:.1f}ms')
print(f'测试结果: {result}')
"
```

## 7. 对比不同模型

```bash
# 对比0.6b和1.7b模型
for model in qwen3:0.6b qwen3:1.7b; do
    echo "测试模型: $model"
    python -c "
from src.local_tester import SimpleLocalTester
tester = SimpleLocalTester()
result = tester.run_dataset_test('sentiment_analysis', '$model', sample_count=5)
print(f'模型 $model 成功率: {result[\"success_rate\"]:.2%}')
"
done
```

## 测试结果分析

1. **成功率**: 模型正确响应的比例
2. **评分准确性**: 模型评分与期望评分的匹配度
3. **类别准确性**: 模型分类与期望分类的匹配度
4. **响应时间**: 平均响应时间性能指标

## 故障排除

1. **测试超时**: 检查模型服务是否正常运行
2. **数据集加载失败**: 验证测试集文件格式和路径
3. **评估结果异常**: 检查模型响应格式是否符合预期
