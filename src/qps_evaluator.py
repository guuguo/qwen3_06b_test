#!/usr/bin/env python3
"""
QPS评估器

用于评估模型的QPS（每秒查询数）性能，支持：
- 并发请求测试
- 不同负载场景
- 详细的性能指标收集
- 结果持久化存储

作者: Qwen-3 部署团队
版本: 1.0.0
"""

import os
import json
import time
import threading
import asyncio
import concurrent.futures
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging
from dataclasses import dataclass, asdict
import statistics

from ollama_integration import OllamaIntegration, create_ollama_client
from config_manager import get_config
from test_dataset_manager import TestDatasetManager


@dataclass
class QPSTestConfig:
    """QPS测试配置"""
    test_name: str
    model: str
    concurrent_users: int
    duration_seconds: int
    prompt_template: str
    test_prompts: List[str]
    warmup_requests: int = 10
    timeout_seconds: int = 30
    enable_thinking: bool = False  # 是否启用思考模式
    dataset_name: str = None  # 测试集名称


@dataclass
class QPSTestResult:
    """QPS测试结果"""
    test_id: str
    test_name: str
    model: str
    start_time: str
    end_time: str
    duration_seconds: float
    concurrent_users: int
    enable_thinking: bool  # 是否启用思考模式
    total_requests: int
    successful_requests: int
    failed_requests: int
    qps: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    error_rate: float
    throughput_tokens_per_second: float
    detailed_metrics: Dict[str, Any]
    errors: List[str]
    dataset_name: str = None  # 使用的测试集名称


@dataclass
class RequestResult:
    """单个请求结果"""
    request_id: str
    start_time: float
    end_time: float
    latency_ms: float
    success: bool
    error: Optional[str]
    response_length: int
    tokens_per_second: float


class QPSEvaluator:
    """
    QPS评估器
    
    用于评估模型的QPS性能，支持多种测试场景和详细的指标收集。
    """
    
    def __init__(self, 
                 ollama_client: Optional[OllamaIntegration] = None,
                 results_dir: str = "./test_results/qps"):
        """
        初始化QPS评估器
        
        Args:
            ollama_client: Ollama客户端
            results_dir: 结果存储目录
        """
        self.ollama_client = ollama_client or create_ollama_client()
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        
        # 测试集管理器
        self.dataset_manager = TestDatasetManager()
        
        # 当前测试状态
        self.current_test: Optional[str] = None
        self.test_progress: Dict[str, Any] = {}
        self.test_results: Dict[str, QPSTestResult] = {}
        
        self.logger.info(f"QPS评估器初始化完成，结果目录: {self.results_dir}")
    
    def get_available_datasets(self) -> List[Dict[str, Any]]:
        """
        获取可用的测试集列表
        
        Returns:
            List[Dict]: 测试集信息列表
        """
        try:
            return self.dataset_manager.get_available_datasets()
        except Exception as e:
            self.logger.error(f"获取测试集列表失败: {e}")
            return []
    
    def create_test_config(self,
                          test_name: str,
                          model: str,
                          concurrent_users: int,
                          duration_seconds: int,
                          prompt_template: str = "你好，请介绍一下你自己。",
                          test_prompts: Optional[List[str]] = None,
                          enable_thinking: bool = False,
                          dataset_name: str = None) -> QPSTestConfig:
        """
        创建测试配置
        
        Args:
            test_name: 测试名称
            model: 模型名称
            concurrent_users: 并发用户数
            duration_seconds: 测试持续时间（秒）
            prompt_template: 提示模板
            test_prompts: 测试提示列表
            enable_thinking: 是否启用思考模式
            dataset_name: 测试集名称，如果指定则使用测试集数据
            
        Returns:
            QPSTestConfig: 测试配置
        """
        # 如果指定了测试集，从测试集加载数据
        if dataset_name:
            try:
                dataset = self.dataset_manager.load_dataset(dataset_name)
                if dataset:
                    # 获取测试集中的样本数据  
                    test_samples = self.dataset_manager.get_test_samples(dataset_name)
                    # 生成基于测试集的提示词
                    dataset_prompts = self.dataset_manager.create_test_prompts(dataset_name, test_samples)
                    if dataset_prompts:
                        test_prompts = dataset_prompts
                        # 使用测试集的第一个提示作为模板展示
                        if test_prompts:
                            prompt_template = f"使用测试集: {dataset_name}"
                        self.logger.info(f"从测试集 {dataset_name} 加载了 {len(test_prompts)} 个测试提示")
                    else:
                        self.logger.warning(f"无法从测试集 {dataset_name} 生成提示词，使用默认提示")
                else:
                    self.logger.warning(f"无法加载测试集 {dataset_name}，使用默认提示")
            except Exception as e:
                self.logger.error(f"加载测试集 {dataset_name} 失败: {e}，使用默认提示")
        
        # 如果没有指定测试集或测试集加载失败，使用默认提示
        if test_prompts is None:
            test_prompts = [
                "你好，请介绍一下你自己。",
                "请解释一下机器学习的基本概念。",
                "写一个简单的Python函数来计算斐波那契数列。",
                "请分析一下当前人工智能的发展趋势。",
                "如何优化深度学习模型的性能？"
            ]
        
        return QPSTestConfig(
            test_name=test_name,
            model=model,
            concurrent_users=concurrent_users,
            duration_seconds=duration_seconds,
            prompt_template=prompt_template,
            test_prompts=test_prompts,
            enable_thinking=enable_thinking,
            dataset_name=dataset_name
        )
    
    def start_qps_test(self, config: QPSTestConfig) -> str:
        """
        启动QPS测试
        
        Args:
            config: 测试配置
            
        Returns:
            str: 测试ID
        """
        test_id = f"qps_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{config.test_name}"
        
        # 检查是否有正在运行的测试
        if self.current_test:
            raise RuntimeError(f"已有测试正在运行: {self.current_test}")
        
        self.current_test = test_id
        self.test_progress[test_id] = {
            'status': 'starting',
            'progress': 0,
            'start_time': datetime.now().isoformat(),
            'config': asdict(config)
        }
        
        # 在后台线程中运行测试
        thread = threading.Thread(
            target=self._run_qps_test,
            args=(test_id, config),
            daemon=True
        )
        thread.start()
        
        self.logger.info(f"QPS测试已启动: {test_id}")
        return test_id
    
    def _run_qps_test(self, test_id: str, config: QPSTestConfig) -> None:
        """
        运行QPS测试（内部方法）
        
        Args:
            test_id: 测试ID
            config: 测试配置
        """
        try:
            start_time = time.time()
            
            # 更新状态
            self.test_progress[test_id]['status'] = 'warming_up'
            self.test_progress[test_id]['progress'] = 5
            
            # 预热
            self._warmup_model(config)
            
            # 更新状态
            self.test_progress[test_id]['status'] = 'running'
            self.test_progress[test_id]['progress'] = 10
            
            # 执行并发测试
            request_results = self._execute_concurrent_test(test_id, config)
            
            # 更新状态
            self.test_progress[test_id]['status'] = 'analyzing'
            self.test_progress[test_id]['progress'] = 90
            
            # 分析结果
            test_result = self._analyze_results(test_id, config, request_results, start_time)
            
            # 保存结果
            self._save_test_result(test_result)
            self.test_results[test_id] = test_result
            
            # 更新状态
            self.test_progress[test_id]['status'] = 'completed'
            self.test_progress[test_id]['progress'] = 100
            self.test_progress[test_id]['result'] = asdict(test_result)
            
            self.logger.info(f"QPS测试完成: {test_id}, QPS: {test_result.qps:.2f}")
            
        except Exception as e:
            self.logger.error(f"QPS测试失败: {test_id}, 错误: {e}")
            self.test_progress[test_id]['status'] = 'failed'
            self.test_progress[test_id]['error'] = str(e)
        
        finally:
            self.current_test = None
    
    def _warmup_model(self, config: QPSTestConfig) -> None:
        """
        预热模型
        
        Args:
            config: 测试配置
        """
        self.logger.info(f"开始预热模型: {config.model}")
        
        # 获取当前测试ID以更新进度
        test_id = self.current_test
        
        for i in range(config.warmup_requests):
            try:
                prompt = config.test_prompts[i % len(config.test_prompts)]
                # 根据配置决定是否启用思考模式
                self.ollama_client.inference_with_metrics(config.model, prompt, enable_thinking=config.enable_thinking)
                
                # 更新预热进度 (5% - 10%)
                if test_id and test_id in self.test_progress:
                    progress = 5 + int((i + 1) / config.warmup_requests * 5)
                    self.test_progress[test_id]['progress'] = progress
                    self.logger.debug(f"预热进度: {i+1}/{config.warmup_requests} ({progress}%)")
                
                time.sleep(0.1)  # 短暂延迟
            except Exception as e:
                self.logger.warning(f"预热请求失败: {e}")
        
        self.logger.info("模型预热完成")
    
    def _execute_concurrent_test(self, test_id: str, config: QPSTestConfig) -> List[RequestResult]:
        """
        执行并发测试
        
        Args:
            test_id: 测试ID
            config: 测试配置
            
        Returns:
            List[RequestResult]: 请求结果列表
        """
        self.logger.info(f"开始并发测试: 并发数={config.concurrent_users}, 持续时间={config.duration_seconds}秒")
        
        request_results = []
        request_counter = 0
        start_time = time.time()
        
        def worker():
            nonlocal request_counter
            worker_results = []
            
            while time.time() - start_time < config.duration_seconds:
                request_id = f"{test_id}_req_{request_counter}"
                request_counter += 1
                
                # 选择提示
                prompt = config.test_prompts[request_counter % len(config.test_prompts)]
                
                # 执行请求
                result = self._execute_single_request(request_id, config.model, prompt, config.timeout_seconds, config.enable_thinking)
                worker_results.append(result)
                
                # 更新进度
                elapsed = time.time() - start_time
                progress = min(10 + (elapsed / config.duration_seconds) * 80, 89)
                self.test_progress[test_id]['progress'] = progress
                
                # 短暂延迟避免过度负载
                time.sleep(0.01)
            
            return worker_results
        
        # 启动并发工作线程
        with concurrent.futures.ThreadPoolExecutor(max_workers=config.concurrent_users) as executor:
            futures = [executor.submit(worker) for _ in range(config.concurrent_users)]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    worker_results = future.result()
                    request_results.extend(worker_results)
                except Exception as e:
                    self.logger.error(f"工作线程执行失败: {e}")
        
        self.logger.info(f"并发测试完成，总请求数: {len(request_results)}")
        return request_results
    
    def _execute_single_request(self, request_id: str, model: str, prompt: str, timeout: int, enable_thinking: bool = False) -> RequestResult:
        """
        执行单个请求
        
        Args:
            request_id: 请求ID
            model: 模型名称
            prompt: 提示
            timeout: 超时时间
            enable_thinking: 是否启用思考模式
            
        Returns:
            RequestResult: 请求结果
        """
        start_time = time.time()
        
        try:
            # 根据配置决定是否启用思考模式
            result = self.ollama_client.inference_with_metrics(model, prompt, enable_thinking=enable_thinking)
            end_time = time.time()
            
            if isinstance(result, dict) and result.get('status') == 'success':
                latency_ms = (end_time - start_time) * 1000
                response_length = len(result.get('response', ''))
                tokens_per_second = result.get('tokens_per_second', 0)
                
                return RequestResult(
                    request_id=request_id,
                    start_time=start_time,
                    end_time=end_time,
                    latency_ms=latency_ms,
                    success=True,
                    error=None,
                    response_length=response_length,
                    tokens_per_second=tokens_per_second
                )
            else:
                error_msg = result.get('error', '未知错误') if isinstance(result, dict) else str(result)
                return RequestResult(
                    request_id=request_id,
                    start_time=start_time,
                    end_time=time.time(),
                    latency_ms=(time.time() - start_time) * 1000,
                    success=False,
                    error=error_msg,
                    response_length=0,
                    tokens_per_second=0
                )
                
        except Exception as e:
            return RequestResult(
                request_id=request_id,
                start_time=start_time,
                end_time=time.time(),
                latency_ms=(time.time() - start_time) * 1000,
                success=False,
                error=str(e),
                response_length=0,
                tokens_per_second=0
            )
    
    def _analyze_results(self, test_id: str, config: QPSTestConfig, 
                        request_results: List[RequestResult], start_time: float) -> QPSTestResult:
        """
        分析测试结果
        
        Args:
            test_id: 测试ID
            config: 测试配置
            request_results: 请求结果列表
            start_time: 测试开始时间
            
        Returns:
            QPSTestResult: 测试结果
        """
        end_time = time.time()
        duration = end_time - start_time
        
        # 基本统计
        total_requests = len(request_results)
        successful_requests = sum(1 for r in request_results if r.success)
        failed_requests = total_requests - successful_requests
        
        # QPS计算
        qps = total_requests / duration if duration > 0 else 0
        
        # 延迟统计（仅成功请求）
        successful_latencies = [r.latency_ms for r in request_results if r.success]
        
        if successful_latencies:
            avg_latency = statistics.mean(successful_latencies)
            min_latency = min(successful_latencies)
            max_latency = max(successful_latencies)
            p50_latency = statistics.median(successful_latencies)
            
            sorted_latencies = sorted(successful_latencies)
            p95_idx = int(len(sorted_latencies) * 0.95)
            p99_idx = int(len(sorted_latencies) * 0.99)
            p95_latency = sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)]
            p99_latency = sorted_latencies[min(p99_idx, len(sorted_latencies) - 1)]
        else:
            avg_latency = min_latency = max_latency = p50_latency = p95_latency = p99_latency = 0
        
        # 错误率
        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
        
        # 吞吐量（tokens/秒）
        total_tokens_per_second = sum(r.tokens_per_second for r in request_results if r.success)
        avg_tokens_per_second = total_tokens_per_second / successful_requests if successful_requests > 0 else 0
        
        # 收集错误信息
        errors = [r.error for r in request_results if r.error]
        unique_errors = list(set(errors))
        
        # 详细指标
        detailed_metrics = {
            'duration_seconds': duration,
            'requests_per_user': total_requests / config.concurrent_users if config.concurrent_users > 0 else 0,
            'avg_response_length': statistics.mean([r.response_length for r in request_results if r.success]) if successful_requests > 0 else 0,
            'total_response_tokens': sum(r.response_length for r in request_results if r.success),
            'error_distribution': {error: errors.count(error) for error in unique_errors},
            'latency_distribution': {
                'buckets': self._create_latency_buckets(successful_latencies),
                'percentiles': {
                    'p90': sorted(successful_latencies)[int(len(successful_latencies) * 0.9)] if successful_latencies else 0,
                    'p99.9': sorted(successful_latencies)[int(len(successful_latencies) * 0.999)] if successful_latencies else 0
                }
            }
        }
        
        return QPSTestResult(
            test_id=test_id,
            test_name=config.test_name,
            model=config.model,
            start_time=datetime.fromtimestamp(start_time).isoformat(),
            end_time=datetime.fromtimestamp(end_time).isoformat(),
            duration_seconds=duration,
            concurrent_users=config.concurrent_users,
            enable_thinking=config.enable_thinking,  # 添加思考模式配置
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            qps=qps,
            avg_latency_ms=avg_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            p50_latency_ms=p50_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            error_rate=error_rate,
            throughput_tokens_per_second=avg_tokens_per_second,
            detailed_metrics=detailed_metrics,
            errors=unique_errors,
            dataset_name=config.dataset_name  # 添加测试集信息
        )
    
    def _create_latency_buckets(self, latencies: List[float]) -> Dict[str, int]:
        """
        创建延迟分布桶
        
        Args:
            latencies: 延迟列表
            
        Returns:
            Dict[str, int]: 延迟分布桶
        """
        if not latencies:
            return {}
        
        buckets = {
            '0-100ms': 0,
            '100-500ms': 0,
            '500ms-1s': 0,
            '1s-5s': 0,
            '5s+': 0
        }
        
        for latency in latencies:
            if latency < 100:
                buckets['0-100ms'] += 1
            elif latency < 500:
                buckets['100-500ms'] += 1
            elif latency < 1000:
                buckets['500ms-1s'] += 1
            elif latency < 5000:
                buckets['1s-5s'] += 1
            else:
                buckets['5s+'] += 1
        
        return buckets
    
    def _save_test_result(self, result: QPSTestResult) -> None:
        """
        保存测试结果
        
        Args:
            result: 测试结果
        """
        result_file = self.results_dir / f"{result.test_id}.json"
        
        try:
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(result), f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"测试结果已保存: {result_file}")
            
        except Exception as e:
            self.logger.error(f"保存测试结果失败: {e}")
    
    def get_test_progress(self, test_id: str) -> Optional[Dict[str, Any]]:
        """
        获取测试进度
        
        Args:
            test_id: 测试ID
            
        Returns:
            Optional[Dict[str, Any]]: 测试进度信息
        """
        return self.test_progress.get(test_id)
    
    def get_all_test_results(self) -> List[QPSTestResult]:
        """
        获取所有测试结果
        
        Returns:
            List[QPSTestResult]: 测试结果列表
        """
        results = []
        
        # 从内存中获取
        results.extend(self.test_results.values())
        
        # 从文件中加载
        for result_file in self.results_dir.glob("*.json"):
            try:
                with open(result_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 为向后兼容，添加默认字段
                    if 'enable_thinking' not in data:
                        data['enable_thinking'] = False
                    if 'dataset_name' not in data:
                        data['dataset_name'] = None
                    result = QPSTestResult(**data)
                    if result.test_id not in self.test_results:
                        results.append(result)
            except Exception as e:
                self.logger.warning(f"加载测试结果失败: {result_file}, 错误: {e}")
        
        # 按时间排序
        results.sort(key=lambda x: x.start_time, reverse=True)
        return results
    
    def get_test_result(self, test_id: str) -> Optional[QPSTestResult]:
        """
        获取指定测试结果
        
        Args:
            test_id: 测试ID
            
        Returns:
            Optional[QPSTestResult]: 测试结果
        """
        # 先从内存中查找
        if test_id in self.test_results:
            return self.test_results[test_id]
        
        # 从文件中加载
        result_file = self.results_dir / f"{test_id}.json"
        if result_file.exists():
            try:
                with open(result_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return QPSTestResult(**data)
            except Exception as e:
                self.logger.error(f"加载测试结果失败: {result_file}, 错误: {e}")
        
        return None
    
    def stop_current_test(self) -> bool:
        """
        停止当前测试
        
        Returns:
            bool: 是否成功停止
        """
        if self.current_test:
            self.test_progress[self.current_test]['status'] = 'stopped'
            self.current_test = None
            self.logger.info("当前测试已停止")
            return True
        return False


def create_qps_evaluator(ollama_client: Optional[OllamaIntegration] = None) -> QPSEvaluator:
    """
    创建QPS评估器的便捷函数
    
    Args:
        ollama_client: Ollama客户端
        
    Returns:
        QPSEvaluator: QPS评估器实例
    """
    results_dir = get_config('qps_evaluation.results_dir', './test_results/qps')
    return QPSEvaluator(ollama_client, results_dir)


if __name__ == "__main__":
    # 示例用法
    evaluator = create_qps_evaluator()
    
    # 创建测试配置
    config = evaluator.create_test_config(
        test_name="基础性能测试",
        model="qwen3:0.6b",
        concurrent_users=5,
        duration_seconds=60
    )
    
    # 启动测试
    test_id = evaluator.start_qps_test(config)
    print(f"测试已启动: {test_id}")
    
    # 监控进度
    while True:
        progress = evaluator.get_test_progress(test_id)
        if progress:
            print(f"状态: {progress['status']}, 进度: {progress['progress']}%")
            if progress['status'] in ['completed', 'failed']:
                break
        time.sleep(5)
    
    # 获取结果
    result = evaluator.get_test_result(test_id)
    if result:
        print(f"QPS: {result.qps:.2f}")
        print(f"平均延迟: {result.avg_latency_ms:.2f}ms")
        print(f"错误率: {result.error_rate:.2f}%")
