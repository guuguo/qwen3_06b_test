# Qwen-3 测试集使用指南

本目录包含了为 Qwen-3 模型评估设计的专业测试集，涵盖通话语义投诉分类和用户评论广告推广评估两个重要应用场景。

## 测试集概览

### 1. 通话语义投诉分类测试集 (`call_semantic_complaints.json`)

**用途**: 评估模型在客服通话语义理解和投诉分类方面的能力

**数据规模**: 50个真实场景样本

**分类体系**:
- 服务质量投诉
- 产品功能投诉  
- 收费争议投诉
- 技术故障投诉
- 态度问题投诉
- 无投诉内容

**评分标准**: 投诉严重度 1-5 分
- 1分: 轻微不满，客户表达了小的担忧但情绪稳定
- 2分: 一般投诉，客户有明确的不满但语气相对平和
- 3分: 严重投诉，客户情绪激动，使用强烈措辞
- 4分: 非常严重，客户愤怒，威胁投诉到监管部门
- 5分: 极度严重，客户怒不可遏，要求退款或解约

### 2. 漫画评论区广告检测测试集 (`manga_comment_ad_detection.json`)

**用途**: 评估模型在识别漫画评论区广告、推广、诈骗等非正常内容的能力

**数据规模**: 50个真实漫画评论样本

**分类体系**:
- 正常评论：真实的漫画阅读体验和感想
- APP推广广告：推广漫画阅读软件
- QQ/微信联系广告：提供联系方式的引流广告
- 网站推广广告：推广漫画网站或盗版资源
- 诈骗类广告：涉及金钱、中奖、刷单等诈骗内容
- 色情引流广告：包含不当内容的引流广告
- 游戏推广广告：推广手机游戏或游戏服务
- 其他商业广告：各类商品或服务推广

**检测评分标准** (0-5分):
- 0分: 明确的正常评论，无任何广告嫌疑
- 1分: 疑似广告，包含轻微推广元素但不确定
- 2分: 可能是广告，包含明显的推广意图
- 3分: 很可能是广告，包含联系方式或明确推广内容
- 4分: 确定是广告，包含完整的推广信息
- 5分: 明显的垃圾广告，可能涉及诈骗或违法内容

## 使用方法

### 1. 基本使用

```python
from src.test_dataset_manager import TestDatasetManager

# 创建测试集管理器
manager = TestDatasetManager()

# 列出可用测试集
datasets = manager.list_available_datasets()
print("可用测试集:", datasets)

# 加载测试集
dataset = manager.load_dataset('call_semantic_complaints')

# 获取测试样本
samples = manager.get_test_samples('call_semantic_complaints', sample_count=10)
```

### 2. 命令行测试

```bash
# 运行投诉分类测试
python -m src.local_tester --test-type dataset --dataset call_semantic_complaints --model qwen3:0.6b --sample-count 10

# 运行漫画广告检测测试
python -m src.local_tester --test-type dataset --dataset manga_comment_ad_detection --model qwen3:0.6b

# 运行所有测试集
python -m src.local_tester --test-type all-datasets --model qwen3:0.6b --sample-count 5
```

### 3. 集成到性能测试

```python
from src.local_tester import SimpleLocalTester
from src.ollama_integration import create_ollama_client

# 创建测试器
with create_ollama_client() as ollama_client:
    tester = SimpleLocalTester(ollama_client)
    
    # 运行测试集评估
    report1 = tester.run_dataset_evaluation('qwen3:0.6b', 'call_semantic_complaints')
    report2 = tester.run_dataset_evaluation('qwen3:0.6b', 'manga_comment_ad_detection')
    
    # 生成HTML报告
    html_report = tester.dataset_manager.generate_html_report(report)
```

## 测试结果解读

### 评估指标说明

1. **成功率**: 模型成功解析和响应的比例
2. **评分准确性**: 模型给出的评分与标准答案的相似度
3. **类别准确性**: 模型分类结果与标准分类的匹配度
4. **响应时间**: 模型处理每个样本的平均时间

### 性能基准

**投诉分类测试集**:
- 优秀水平: 评分准确性 > 85%, 类别准确性 > 90%
- 良好水平: 评分准确性 > 75%, 类别准确性 > 85%
- 及格水平: 评分准确性 > 65%, 类别准确性 > 80%

**漫画广告检测测试集**:
- 优秀水平: 广告检测准确性 > 90%, 分类准确性 > 85%
- 良好水平: 广告检测准确性 > 85%, 分类准确性 > 80%
- 及格水平: 广告检测准确性 > 80%, 分类准确性 > 75%

## 自定义测试集

### 数据格式规范

```json
{
  "dataset_info": {
    "name": "测试集名称",
    "description": "测试集描述",
    "version": "1.0.0",
    "created_date": "2024-08-04",
    "total_samples": 样本数量,
    "categories": ["类别1", "类别2"],
    "scoring_criteria": {
      "评分名称": {
        "1分": "评分说明",
        "2分": "评分说明"
      }
    }
  },
  "test_samples": [
    {
      "id": "sample_001",
      "content": "测试内容",
      "category": "分类",
      "expected_score": 评分,
      "keywords": ["关键词"],
      "expected_response": "期望回复",
      "metadata": {}
    }
  ]
}
```

### 添加新测试集

1. 按照上述格式创建JSON文件
2. 将文件放置在 `test_datasets/` 目录下
3. 在 `TestDatasetManager` 中添加相应的解析逻辑（如需要）
4. 更新提示词模板以适配新的测试类型

## 测试报告

系统会自动生成两种格式的测试报告：

1. **JSON报告**: 包含详细的测试数据和统计信息
2. **HTML报告**: 可视化的测试结果展示，包含图表和分析

报告保存在 `test_results/` 目录下，文件名包含时间戳以区分不同的测试。

## 最佳实践

1. **样本选择**: 建议使用代表性样本进行测试，涵盖各种难度级别
2. **批量测试**: 对于大规模评估，建议分批次进行以避免资源过载
3. **结果分析**: 重点关注失败样本，分析模型的不足之处
4. **持续改进**: 根据测试结果调整模型参数或训练数据

## 技术支持

如需技术支持或有改进建议，请联系 Qwen-3 部署团队。

---

*🤖 本文档由 Qwen-3 测试集管理系统生成*