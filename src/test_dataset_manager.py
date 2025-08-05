#!/usr/bin/env python3
"""
测试集管理和验证工具

提供测试集的加载、验证、管理和评估功能，包括：
- 测试集数据加载和验证
- 模型评估和结果分析
- 测试集统计和报告生成
- 预设测试场景管理

作者: Qwen-3 部署团队
版本: 1.0.0
"""

import json
import os
import logging
import random
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import statistics
import sys

# 添加prompts目录到Python路径
current_dir = Path(__file__).parent.parent
prompts_dir = current_dir / "prompts"
sys.path.append(str(prompts_dir))

from md_manager import get_md_prompt_manager


@dataclass
class TestSample:
    """测试样本数据类"""
    id: str
    content: str
    category: str
    expected_score: float
    keywords: List[str]
    expected_response: str
    metadata: Dict[str, Any] = None


@dataclass
class TestResult:
    """测试结果数据类"""
    sample_id: str
    comment: str  # 添加原始评论内容
    model_response: str
    model_score: Optional[float]
    model_category: Optional[str]
    expected_score: float
    expected_category: str
    score_accuracy: float
    category_match: bool
    response_time_ms: float
    error: Optional[str] = None


@dataclass
class EvaluationReport:
    """评估报告数据类"""
    dataset_name: str
    model_name: str
    test_time: str
    total_samples: int
    successful_tests: int
    failed_tests: int
    avg_score_accuracy: float
    category_accuracy: float
    avg_response_time_ms: float
    score_distribution: Dict[str, int]
    category_distribution: Dict[str, int]
    detailed_results: List[TestResult]


class TestDatasetManager:
    """
    测试集管理器
    
    负责加载、验证和管理各种测试集数据
    """
    
    def __init__(self, datasets_dir: str = "./test_datasets"):
        """
        初始化测试集管理器
        
        Args:
            datasets_dir: 测试集目录路径
        """
        self.datasets_dir = Path(datasets_dir)
        self.logger = logging.getLogger(__name__)
        self.loaded_datasets = {}
        
        # 确保目录存在
        self.datasets_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"测试集管理器初始化完成，目录: {datasets_dir}")
    
    def load_dataset(self, dataset_name: str) -> Optional[Dict[str, Any]]:
        """
        加载测试集数据
        
        Args:
            dataset_name: 测试集名称（不含扩展名）
            
        Returns:
            Dict: 测试集数据，失败返回 None
        """
        dataset_file = self.datasets_dir / f"{dataset_name}.json"
        
        if not dataset_file.exists():
            self.logger.error(f"测试集文件不存在: {dataset_file}")
            return None
        
        try:
            with open(dataset_file, 'r', encoding='utf-8') as f:
                dataset = json.load(f)
            
            # 验证数据集格式
            if not self._validate_dataset(dataset):
                self.logger.error(f"测试集格式验证失败: {dataset_name}")
                return None
            
            self.loaded_datasets[dataset_name] = dataset
            self.logger.info(f"测试集加载成功: {dataset_name}, "
                           f"样本数: {len(dataset.get('test_samples', []))}")
            
            return dataset
            
        except Exception as e:
            self.logger.error(f"加载测试集失败: {dataset_name}, 错误: {e}")
            return None
    
    def _validate_dataset(self, dataset: Dict[str, Any]) -> bool:
        """验证测试集数据格式"""
        required_fields = ['dataset_info', 'test_samples']
        
        # 检查必需字段
        for field in required_fields:
            if field not in dataset:
                self.logger.error(f"缺少必需字段: {field}")
                return False
        
        # 检查数据集信息
        info = dataset['dataset_info']
        required_info_fields = ['name', 'description', 'version', 'total_samples']
        for field in required_info_fields:
            if field not in info:
                self.logger.error(f"数据集信息缺少字段: {field}")
                return False
        
        # 检查样本数量
        samples = dataset['test_samples']
        if len(samples) != info['total_samples']:
            self.logger.warning(f"样本数量不匹配: 声明{info['total_samples']}, 实际{len(samples)}")
        
        # 检查样本格式
        for i, sample in enumerate(samples):
            required_sample_fields = ['id']
            for field in required_sample_fields:
                if field not in sample:
                    self.logger.error(f"样本 {i} 缺少字段: {field}")
                    return False
        
        return True
    
    def get_test_samples(self, dataset_name: str, 
                        sample_count: Optional[int] = None,
                        categories: Optional[List[str]] = None,
                        random_seed: Optional[int] = None) -> List[TestSample]:
        """
        获取测试样本
        
        Args:
            dataset_name: 测试集名称
            sample_count: 样本数量限制，None 表示全部
            categories: 筛选特定类别，None 表示全部
            random_seed: 随机种子，用于确保结果可重现
            
        Returns:
            List[TestSample]: 测试样本列表
        """
        if dataset_name not in self.loaded_datasets:
            dataset = self.load_dataset(dataset_name)
            if not dataset:
                return []
        else:
            dataset = self.loaded_datasets[dataset_name]
        
        samples = dataset['test_samples']
        test_samples = []
        
        # 转换为 TestSample 对象
        for sample in samples:
            # 根据不同数据集类型解析样本
            if dataset_name == 'call_semantic_complaints':
                test_sample = TestSample(
                    id=sample['id'],
                    content=sample['conversation_text'],
                    category=sample['category'],
                    expected_score=sample['severity_score'],
                    keywords=sample['keywords'],
                    expected_response=sample['expected_response'],
                    metadata={
                        'severity_score': sample['severity_score'],
                        'keywords': sample['keywords']
                    }
                )
            elif dataset_name == 'manga_comment_ad_detection':
                test_sample = TestSample(
                    id=sample['id'],
                    content=sample['comment_text'],
                    category=sample['category'],
                    expected_score=sample['ad_score'],
                    keywords=sample['keywords'],
                    expected_response=sample['expected_response'],
                    metadata={
                        'ad_score': sample['ad_score'],
                        'context': sample['context'],
                        'category': sample['category']
                    }
                )
            else:
                # 通用格式
                test_sample = TestSample(
                    id=sample['id'],
                    content=sample.get('content', ''),
                    category=sample.get('category', ''),
                    expected_score=sample.get('expected_score', 0),
                    keywords=sample.get('keywords', []),
                    expected_response=sample.get('expected_response', ''),
                    metadata=sample.get('metadata', {})
                )
            
            test_samples.append(test_sample)
        
        # 类别筛选
        if categories:
            test_samples = [s for s in test_samples if s.category in categories]
        
        # 随机采样
        if sample_count and sample_count < len(test_samples):
            if random_seed is not None:
                random.seed(random_seed)
            test_samples = random.sample(test_samples, sample_count)
        
        self.logger.info(f"获取测试样本: {len(test_samples)} 个")
        return test_samples
    
    def create_test_prompts(self, dataset_name: str, 
                          test_samples: List[TestSample]) -> List[str]:
        """
        为测试样本创建提示词
        
        使用新的提示词管理系统，从配置文件中加载提示词模板
        
        Args:
            dataset_name: 测试集名称
            test_samples: 测试样本列表
            
        Returns:
            List[str]: 格式化的提示词列表
        """
        prompts = []
        
        try:
            # 使用MD提示词管理器
            md_manager = get_md_prompt_manager()
            
            for sample in test_samples:
                # 准备样本数据
                sample_data = {
                    'content': sample.content,
                    'category': sample.category,
                    'expected_score': sample.expected_score
                }
                
                # 使用MD提示词管理器渲染提示词
                prompt = md_manager.render_prompt(dataset_name, sample_data)
                prompts.append(prompt)
                
            self.logger.info(f"使用MD提示词管理器为 {dataset_name} 生成了 {len(prompts)} 个提示词")
            
        except Exception as e:
            self.logger.warning(f"MD提示词管理器失败，使用硬编码备用方法: {str(e)}")
            # 备用方法：使用原始硬编码逻辑
            prompts = self._create_fallback_prompts(dataset_name, test_samples)
        
        return prompts
    
    def _create_fallback_prompts(self, dataset_name: str, 
                               test_samples: List[TestSample]) -> List[str]:
        """
        备用提示词创建方法（保持与原始逻辑兼容）
        
        Args:
            dataset_name: 测试集名称
            test_samples: 测试样本列表
            
        Returns:
            List[str]: 格式化的提示词列表
        """
        prompts = []
        
        for sample in test_samples:
            if dataset_name == 'call_semantic_complaints':
                prompt = f"""请分析以下通话语义内容，并进行投诉分类评估：

通话内容：{sample.content}

请按照以下要求进行分析：
1. 判断投诉类别：服务质量投诉、产品功能投诉、收费争议投诉、技术故障投诉、态度问题投诉、无投诉内容
2. 评估投诉严重度（1-5分）：1分=轻微不满，2分=一般投诉，3分=严重投诉，4分=非常严重，5分=极度严重
3. 提供简要分析说明

请以JSON格式回复：
{{
  "category": "投诉类别",
  "severity_score": 评分数字,
  "analysis": "分析说明"
}}"""
            
            elif dataset_name == 'manga_comment_ad_detection':
                prompt = f"""请分析以下漫画评论，判断是否为广告内容：

评论内容：{sample.content}

请按照以下要求进行分析：
1. 判断是否为广告（0-5分）：0分=正常评论，1分=疑似广告，2分=可能是广告，3分=很可能是广告，4分=确定是广告，5分=明显垃圾广告
2. 广告类型分类：正常评论、APP推广广告、QQ/微信联系广告、网站推广广告、诈骗类广告、色情引流广告、游戏推广广告、其他商业广告
3. 提供判断依据说明

请以JSON格式回复：
{{
  "ad_score": 评分数字,
  "category": "广告类型",
  "analysis": "判断依据说明"
}}"""
            
            else:
                # 通用格式
                prompt = f"""请分析以下内容：

内容：{sample.content}

预期类别：{sample.category}
预期评分：{sample.expected_score}

请提供你的分析结果。"""
            
            prompts.append(prompt)
            
        self.logger.info(f"使用备用方法为 {dataset_name} 生成了 {len(prompts)} 个提示词")
        return prompts
    
    def evaluate_model_responses(self, dataset_name: str,
                                test_samples: List[TestSample],
                                model_responses: List[Dict[str, Any]]) -> List[TestResult]:
        """
        评估模型响应结果
        
        Args:
            dataset_name: 测试集名称
            test_samples: 测试样本列表
            model_responses: 模型响应列表
            
        Returns:
            List[TestResult]: 评估结果列表
        """
        if len(test_samples) != len(model_responses):
            raise ValueError("测试样本数量与模型响应数量不匹配")
        
        results = []
        
        for sample, response in zip(test_samples, model_responses):
            try:
                # 解析模型响应
                model_response_text = response.get('response', '')
                response_time = response.get('latency_ms', 0)
                
                # 尝试解析JSON响应
                model_result = self._parse_model_response(model_response_text, dataset_name)
                
                # 使用MD提示词管理器进行响应质量检查
                try:
                    md_manager = get_md_prompt_manager()
                    validation_errors = md_manager.validate_response(dataset_name, model_response_text)
                    if validation_errors:
                        self.logger.warning(f"响应质量检查发现问题 - 样本 {sample.id}: {'; '.join(validation_errors)}")
                except Exception as e:
                    self.logger.debug(f"响应质量检查失败 - 样本 {sample.id}: {str(e)}")
                
                if model_result:
                    # 计算准确性
                    score_accuracy = self._calculate_score_accuracy(
                        model_result.get('score'), sample.expected_score
                    )
                    
                    category_match = self._check_category_match(
                        model_result.get('category'), sample.category, dataset_name
                    )
                    
                    test_result = TestResult(
                        sample_id=sample.id,
                        comment=sample.content,  # 添加原始评论内容
                        model_response=model_response_text,
                        model_score=model_result.get('score'),
                        model_category=model_result.get('category'),
                        expected_score=sample.expected_score,
                        expected_category=sample.category,
                        score_accuracy=score_accuracy,
                        category_match=category_match,
                        response_time_ms=response_time
                    )
                else:
                    # 解析失败
                    test_result = TestResult(
                        sample_id=sample.id,
                        comment=sample.content,  # 添加原始评论内容
                        model_response=model_response_text,
                        model_score=None,
                        model_category=None,
                        expected_score=sample.expected_score,
                        expected_category=sample.category,
                        score_accuracy=0.0,
                        category_match=False,
                        response_time_ms=response_time,
                        error="无法解析模型响应"
                    )
                
                results.append(test_result)
                
            except Exception as e:
                error_result = TestResult(
                    sample_id=sample.id,
                    comment=sample.content,  # 添加原始评论内容
                    model_response=str(response),
                    model_score=None,
                    model_category=None,
                    expected_score=sample.expected_score,
                    expected_category=sample.category,
                    score_accuracy=0.0,
                    category_match=False,
                    response_time_ms=0,
                    error=str(e)
                )
                results.append(error_result)
        
        return results
    
    def _parse_model_response(self, response_text: str, dataset_name: str) -> Optional[Dict[str, Any]]:
        """解析模型响应"""
        try:
            # 尝试解析JSON
            if '{' in response_text and '}' in response_text:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                json_text = response_text[json_start:json_end]
                
                parsed = json.loads(json_text)
                
                if dataset_name == 'call_semantic_complaints':
                    return {
                        'category': parsed.get('category'),
                        'score': parsed.get('severity_score'),
                        'analysis': parsed.get('analysis')
                    }
                elif dataset_name == 'manga_comment_ad_detection':
                    return {
                        'category': parsed.get('category'),
                        'score': parsed.get('ad_score'),
                        'analysis': parsed.get('analysis')
                    }
                else:
                    return parsed
                    
        except Exception as e:
            self.logger.warning(f"JSON解析失败: {e}")
        
        # 尝试文本解析
        try:
            result = {}
            lines = response_text.split('\n')
            
            for line in lines:
                if '分' in line or '评分' in line:
                    # 提取数字
                    import re
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        result['score'] = int(numbers[0])
                
                if '类别' in line or '投诉' in line:
                    if '服务质量' in line:
                        result['category'] = '服务质量投诉'
                    elif '产品功能' in line:
                        result['category'] = '产品功能投诉'
                    elif '收费争议' in line:
                        result['category'] = '收费争议投诉'
                    elif '技术故障' in line:
                        result['category'] = '技术故障投诉'
                    elif '态度问题' in line:
                        result['category'] = '态度问题投诉'
                    elif '无投诉' in line:
                        result['category'] = '无投诉内容'
                
                # 广告检测的类别匹配
                if '正常评论' in line:
                    result['category'] = '正常评论'
                elif 'APP推广' in line or 'app推广' in line:
                    result['category'] = 'APP推广广告'
                elif 'QQ' in line or '微信' in line:
                    result['category'] = 'QQ/微信联系广告'
                elif '网站推广' in line or '网站' in line:
                    result['category'] = '网站推广广告'
                elif '诈骗' in line or '中奖' in line:
                    result['category'] = '诈骗类广告'
                elif '色情' in line or '直播' in line:
                    result['category'] = '色情引流广告'
                elif '游戏' in line:
                    result['category'] = '游戏推广广告'
                elif '商业广告' in line or '广告' in line:
                    result['category'] = '其他商业广告'
                
                # 原有的推广等级匹配（保持兼容性）
                if 'A级' in line or 'B级' in line or 'C级' in line or 'D级' in line or 'E级' in line:
                    import re
                    match = re.search(r'([ABCDE])级', line)
                    if match:
                        result['category'] = f"{match.group(1)}级"
            
            return result if result else None
            
        except Exception:
            return None
    
    def _calculate_score_accuracy(self, model_score: Optional[float], 
                                expected_score: float) -> float:
        """计算评分准确性"""
        if model_score is None:
            return 0.0
        
        # 计算相对误差的准确性
        max_diff = max(5, expected_score)  # 假设最大评分是5
        diff = abs(model_score - expected_score)
        accuracy = max(0, 1 - diff / max_diff)
        
        return accuracy
    
    def _check_category_match(self, model_category: Optional[str], 
                            expected_category: str, dataset_name: str) -> bool:
        """检查类别匹配"""
        if not model_category:
            return False
        
        # 精确匹配
        if model_category == expected_category:
            return True
        
        # 模糊匹配
        if dataset_name == 'call_semantic_complaints':
            # 投诉分类的模糊匹配
            category_keywords = {
                '服务质量投诉': ['服务', '质量'],
                '产品功能投诉': ['产品', '功能'],
                '收费争议投诉': ['收费', '争议', '费用'],
                '技术故障投诉': ['技术', '故障'],
                '态度问题投诉': ['态度', '问题'],
                '无投诉内容': ['无投诉', '无']
            }
            
            expected_keywords = category_keywords.get(expected_category, [])
            for keyword in expected_keywords:
                if keyword in model_category:
                    return True
        
        elif dataset_name == 'user_comment_ad_evaluation':
            # 广告推广等级的模糊匹配
            if expected_category in model_category or model_category in expected_category:
                return True
        
        return False
    
    def generate_evaluation_report(self, dataset_name: str, model_name: str,
                                 test_results: List[TestResult]) -> EvaluationReport:
        """
        生成评估报告
        
        Args:
            dataset_name: 测试集名称
            model_name: 模型名称
            test_results: 测试结果列表
            
        Returns:
            EvaluationReport: 评估报告
        """
        total_samples = len(test_results)
        successful_tests = len([r for r in test_results if r.error is None])
        failed_tests = total_samples - successful_tests
        
        # 计算准确性指标
        valid_results = [r for r in test_results if r.error is None and r.model_score is not None]
        
        if valid_results:
            avg_score_accuracy = statistics.mean([r.score_accuracy for r in valid_results])
            category_accuracy = sum([1 for r in valid_results if r.category_match]) / len(valid_results)
            avg_response_time = statistics.mean([r.response_time_ms for r in test_results])
        else:
            avg_score_accuracy = 0.0
            category_accuracy = 0.0
            avg_response_time = 0.0
        
        # 分数分布统计
        score_distribution = {}
        for result in valid_results:
            score_range = f"{int(result.model_score)}-{int(result.model_score)+1}"
            score_distribution[score_range] = score_distribution.get(score_range, 0) + 1
        
        # 类别分布统计
        category_distribution = {}
        for result in test_results:
            category = result.expected_category
            category_distribution[category] = category_distribution.get(category, 0) + 1
        
        return EvaluationReport(
            dataset_name=dataset_name,
            model_name=model_name,
            test_time=datetime.now().isoformat(),
            total_samples=total_samples,
            successful_tests=successful_tests,
            failed_tests=failed_tests,
            avg_score_accuracy=avg_score_accuracy,
            category_accuracy=category_accuracy,
            avg_response_time_ms=avg_response_time,
            score_distribution=score_distribution,
            category_distribution=category_distribution,
            detailed_results=test_results
        )
    
    def save_evaluation_report(self, report: EvaluationReport, 
                             output_dir: str = "./test_results") -> str:
        """
        保存评估报告
        
        Args:
            report: 评估报告
            output_dir: 输出目录
            
        Returns:
            str: 保存的文件路径
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{report.dataset_name}_{report.model_name}_{timestamp}_evaluation.json"
        
        report_file = output_path / filename
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(report), f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"评估报告已保存: {report_file}")
            return str(report_file)
            
        except Exception as e:
            self.logger.error(f"保存评估报告失败: {e}")
            raise
    
    def generate_html_report(self, report: EvaluationReport, 
                           output_dir: str = "./test_results") -> str:
        """
        生成HTML格式的评估报告
        
        Args:
            report: 评估报告
            output_dir: 输出目录
            
        Returns:
            str: HTML报告文件路径
        """
        html_template = """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{dataset_name} - {model_name} 测试评估报告</title>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; 
                    margin: 20px; 
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{ color: #2c3e50; text-align: center; margin-bottom: 30px; }}
                h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                .metric-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin: 20px 0;
                }}
                .metric {{ 
                    padding: 15px; 
                    background: #f8f9fa; 
                    border-radius: 8px;
                    border-left: 4px solid #3498db;
                }}
                .metric-title {{ font-weight: bold; color: #2c3e50; margin-bottom: 5px; }}
                .metric-value {{ font-size: 1.2em; color: #27ae60; }}
                .good {{ color: #27ae60; }}
                .warning {{ color: #f39c12; }}
                .error {{ color: #e74c3c; }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                th, td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{ background-color: #3498db; color: white; }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    color: #7f8c8d;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 {dataset_name} - {model_name} 测试评估报告</h1>
                
                <div class="metric-grid">
                    <div class="metric">
                        <div class="metric-title">测试集</div>
                        <div class="metric-value">{dataset_name}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-title">测试模型</div>
                        <div class="metric-value">{model_name}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-title">测试时间</div>
                        <div class="metric-value">{test_time}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-title">总样本数</div>
                        <div class="metric-value">{total_samples}</div>
                    </div>
                </div>

                <h2>📈 核心评估指标</h2>
                <div class="metric-grid">
                    <div class="metric">
                        <div class="metric-title">成功测试数</div>
                        <div class="metric-value good">{successful_tests}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-title">失败测试数</div>
                        <div class="metric-value {failed_class}">{failed_tests}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-title">评分准确性</div>
                        <div class="metric-value {score_class}">{avg_score_accuracy:.2%}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-title">类别准确性</div>
                        <div class="metric-value {category_class}">{category_accuracy:.2%}</div>
                    </div>
                </div>

                <div class="metric-grid">
                    <div class="metric">
                        <div class="metric-title">平均响应时间</div>
                        <div class="metric-value">{avg_response_time_ms:.2f}ms</div>
                    </div>
                    <div class="metric">
                        <div class="metric-title">成功率</div>
                        <div class="metric-value {success_class}">{success_rate:.2%}</div>
                    </div>
                </div>

                <h2>📊 分布统计</h2>
                <table>
                    <tr>
                        <th>类别</th>
                        <th>样本数量</th>
                        <th>占比</th>
                    </tr>
                    {category_rows}
                </table>

                <div class="footer">
                    <p>报告生成时间: {report_time}</p>
                    <p>🤖 由 Qwen-3 测试集管理器生成</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # 计算样式类
        failed_class = "error" if report.failed_tests > 0 else "good"
        score_class = "good" if report.avg_score_accuracy > 0.8 else "warning" if report.avg_score_accuracy > 0.6 else "error"
        category_class = "good" if report.category_accuracy > 0.8 else "warning" if report.category_accuracy > 0.6 else "error"
        success_rate = report.successful_tests / report.total_samples if report.total_samples > 0 else 0
        success_class = "good" if success_rate > 0.9 else "warning" if success_rate > 0.7 else "error"
        
        # 生成类别分布表格
        category_rows = ""
        for category, count in report.category_distribution.items():
            percentage = count / report.total_samples * 100 if report.total_samples > 0 else 0
            category_rows += f"""
            <tr>
                <td>{category}</td>
                <td>{count}</td>
                <td>{percentage:.1f}%</td>
            </tr>
            """
        
        html_content = html_template.format(
            dataset_name=report.dataset_name,
            model_name=report.model_name,
            test_time=report.test_time,
            total_samples=report.total_samples,
            successful_tests=report.successful_tests,
            failed_tests=report.failed_tests,
            failed_class=failed_class,
            avg_score_accuracy=report.avg_score_accuracy,
            score_class=score_class,
            category_accuracy=report.category_accuracy,
            category_class=category_class,
            avg_response_time_ms=report.avg_response_time_ms,
            success_rate=success_rate,
            success_class=success_class,
            category_rows=category_rows,
            report_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{report.dataset_name}_{report.model_name}_{timestamp}_report.html"
        
        report_file = output_path / filename
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"HTML评估报告已生成: {report_file}")
        return str(report_file)
    
    def list_available_datasets(self) -> List[str]:
        """列出可用的测试集"""
        datasets = []
        for file_path in self.datasets_dir.glob("*.json"):
            datasets.append(file_path.stem)
        return sorted(datasets)
    
    def get_dataset_info(self, dataset_name: str) -> Optional[Dict[str, Any]]:
        """获取测试集信息"""
        dataset = self.load_dataset(dataset_name)
        if dataset:
            return dataset.get('dataset_info')
        return None


if __name__ == "__main__":
    # 示例用法
    import sys
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建测试集管理器
    manager = TestDatasetManager()
    
    # 列出可用测试集
    print("📋 可用测试集:")
    for dataset in manager.list_available_datasets():
        info = manager.get_dataset_info(dataset)
        if info:
            print(f"  - {dataset}: {info.get('name', 'N/A')} ({info.get('total_samples', 0)} 样本)")
    
    # 演示加载和使用测试集
    if len(sys.argv) > 1:
        dataset_name = sys.argv[1]
        print(f"\n🔍 加载测试集: {dataset_name}")
        
        # 获取测试样本
        samples = manager.get_test_samples(dataset_name, sample_count=5)
        if samples:
            print(f"✅ 获取到 {len(samples)} 个测试样本")
            
            # 创建测试提示词
            prompts = manager.create_test_prompts(dataset_name, samples)
            print(f"✅ 生成 {len(prompts)} 个测试提示词")
            
            # 显示第一个样本
            print(f"\n📝 第一个测试样本:")
            print(f"ID: {samples[0].id}")
            print(f"类别: {samples[0].category}")
            print(f"预期评分: {samples[0].expected_score}")
            print(f"内容: {samples[0].content[:100]}...")
            print(f"\n提示词: {prompts[0][:200]}...")
        else:
            print("❌ 未找到测试样本")
    else:
        print("\n💡 使用方法: python test_dataset_manager.py <dataset_name>")
        print("例如: python test_dataset_manager.py call_semantic_complaints")