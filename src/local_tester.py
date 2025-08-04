#!/usr/bin/env python3
"""
Qwen-3 本地性能测试套件

提供简化的本地性能测试功能，包括：
- 基础 QPS 测试（多线程并发）
- 延迟测试和统计分析（P50/P95/P99）
- 测试结果保存和 HTML 报告生成
- 系统资源监控集成

作者: Qwen-3 部署团队
版本: 1.0.0
"""

import json
import time
import logging
import threading
import statistics
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil

from ollama_integration import OllamaIntegration, InferenceMetrics
from test_dataset_manager import TestDatasetManager, TestResult, EvaluationReport


@dataclass
class TestConfig:
    """测试配置数据类"""
    model: str
    test_prompts: List[str]
    concurrent_users: int = 5
    test_duration: int = 60
    iterations: int = 100
    timeout: int = 30
    warmup_iterations: int = 5


@dataclass
class LatencyStats:
    """延迟统计数据类"""
    count: int
    min_ms: float
    max_ms: float
    mean_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    std_dev_ms: float


@dataclass
class QPSTestResult:
    """QPS 测试结果数据类"""
    test_id: str
    model: str
    start_time: str
    end_time: str
    duration_seconds: float
    concurrent_users: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    timeout_requests: int
    qps: float
    avg_latency_ms: float
    latency_stats: LatencyStats
    error_rate: float
    throughput_tokens_per_second: float
    system_metrics: Dict[str, Any]
    errors: List[str]


@dataclass
class LatencyTestResult:
    """延迟测试结果数据类"""
    test_id: str
    model: str
    start_time: str
    end_time: str
    iterations: int
    successful_iterations: int
    failed_iterations: int
    latency_stats: LatencyStats
    system_metrics: Dict[str, Any]
    errors: List[str]


class SystemMonitor:
    """系统资源监控器"""
    
    def __init__(self):
        self.monitoring = False
        self.metrics = []
        self.monitor_thread = None
        self.lock = threading.Lock()
    
    def start_monitoring(self, interval: float = 1.0):
        """开始监控系统资源"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.metrics = []
        
        def monitor():
            while self.monitoring:
                try:
                    metric = {
                        'timestamp': datetime.now().isoformat(),
                        'cpu_percent': psutil.cpu_percent(interval=None),
                        'memory_percent': psutil.virtual_memory().percent,
                        'memory_used_mb': psutil.virtual_memory().used / 1024 / 1024,
                        'disk_usage_percent': psutil.disk_usage('/').percent
                    }
                    
                    with self.lock:
                        self.metrics.append(metric)
                        
                except Exception as e:
                    logging.error(f"系统监控错误: {e}")
                
                time.sleep(interval)
        
        self.monitor_thread = threading.Thread(target=monitor, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """停止监控并返回统计信息"""
        self.monitoring = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
        
        with self.lock:
            if not self.metrics:
                return {}
            
            cpu_values = [m['cpu_percent'] for m in self.metrics]
            memory_values = [m['memory_percent'] for m in self.metrics]
            memory_mb_values = [m['memory_used_mb'] for m in self.metrics]
            
            return {
                'samples_count': len(self.metrics),
                'duration_seconds': len(self.metrics),  # 假设每秒一个样本
                'cpu': {
                    'avg_percent': statistics.mean(cpu_values),
                    'max_percent': max(cpu_values),
                    'min_percent': min(cpu_values)
                },
                'memory': {
                    'avg_percent': statistics.mean(memory_values),
                    'max_percent': max(memory_values),
                    'min_percent': min(memory_values),
                    'avg_used_mb': statistics.mean(memory_mb_values),
                    'max_used_mb': max(memory_mb_values)
                }
            }


class SimpleLocalTester:
    """
    简化的本地性能测试器
    
    提供基础的 QPS 和延迟测试功能，适用于本地开发和简单的性能评估。
    """
    
    def __init__(self, ollama_integration: OllamaIntegration, 
                 results_dir: str = "./test_results"):
        """
        初始化测试器
        
        Args:
            ollama_integration: Ollama 集成实例
            results_dir: 测试结果保存目录
        """
        self.ollama = ollama_integration
        self.results_dir = results_dir
        self.logger = logging.getLogger(__name__)
        
        # 创建结果目录
        os.makedirs(results_dir, exist_ok=True)
        
        # 默认测试提示
        self.default_prompts = [
            "你好，请简单介绍一下你自己。",
            "请解释一下人工智能的基本概念。",
            "写一个简单的 Python 函数来计算阶乘。",
            "描述一下机器学习和深度学习的区别。",
            "请给出一些提高编程效率的建议。"
        ]
        
        # 初始化测试集管理器
        self.dataset_manager = TestDatasetManager()
        
        self.logger.info(f"本地测试器初始化完成，结果目录: {results_dir}")
    
    def _calculate_latency_stats(self, latencies: List[float]) -> LatencyStats:
        """计算延迟统计信息"""
        if not latencies:
            return LatencyStats(0, 0, 0, 0, 0, 0, 0, 0)
        
        sorted_latencies = sorted(latencies)
        count = len(sorted_latencies)
        
        return LatencyStats(
            count=count,
            min_ms=min(sorted_latencies),
            max_ms=max(sorted_latencies),
            mean_ms=statistics.mean(sorted_latencies),
            median_ms=statistics.median(sorted_latencies),
            p95_ms=sorted_latencies[int(count * 0.95)] if count > 0 else 0,
            p99_ms=sorted_latencies[int(count * 0.99)] if count > 0 else 0,
            std_dev_ms=statistics.stdev(sorted_latencies) if count > 1 else 0
        )
    
    def run_basic_qps_test(self, 
                          model: str, 
                          test_prompts: Optional[List[str]] = None,
                          concurrent_users: int = 5, 
                          duration: int = 60,
                          warmup_duration: int = 10) -> QPSTestResult:
        """
        运行基础 QPS 测试
        
        Args:
            model: 测试模型名称
            test_prompts: 测试提示列表，None 使用默认提示
            concurrent_users: 并发用户数
            duration: 测试持续时间（秒）
            warmup_duration: 预热时间（秒）
            
        Returns:
            QPSTestResult: 测试结果
        """
        test_id = f"qps_{model.replace(':', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.logger.info(f"开始 QPS 测试: {test_id}")
        
        if test_prompts is None:
            test_prompts = self.default_prompts
        
        # 验证模型存在
        if not self.ollama.model_exists(model):
            error_msg = f"模型不存在: {model}"
            self.logger.error(error_msg)
            return QPSTestResult(
                test_id=test_id,
                model=model,
                start_time=datetime.now().isoformat(),
                end_time=datetime.now().isoformat(),
                duration_seconds=0,
                concurrent_users=concurrent_users,
                total_requests=0,
                successful_requests=0,
                failed_requests=1,
                timeout_requests=0,
                qps=0,
                avg_latency_ms=0,
                latency_stats=LatencyStats(0, 0, 0, 0, 0, 0, 0, 0),
                error_rate=1.0,
                throughput_tokens_per_second=0,
                system_metrics={},
                errors=[error_msg]
            )
        
        # 预热
        if warmup_duration > 0:
            self.logger.info(f"预热阶段开始 ({warmup_duration}s)...")
            self._run_warmup(model, test_prompts, min(concurrent_users, 2), warmup_duration)
            self.logger.info("预热阶段完成")
        
        # 开始系统监控
        monitor = SystemMonitor()
        monitor.start_monitoring()
        
        # 测试数据收集
        results = []
        errors = []
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=duration)
        
        self.logger.info(f"QPS 测试开始: {concurrent_users} 并发用户, {duration}s 持续时间")
        
        def worker():
            """工作线程函数"""
            prompt_index = 0
            while datetime.now() < end_time:
                try:
                    prompt = test_prompts[prompt_index % len(test_prompts)]
                    result = self.ollama.inference_with_metrics(model, prompt)
                    results.append(result)
                    prompt_index += 1
                except Exception as e:
                    error_msg = f"工作线程错误: {e}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
        
        # 启动并发测试
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(worker) for _ in range(concurrent_users)]
            
            # 等待测试完成
            for future in as_completed(futures, timeout=duration + 30):
                try:
                    future.result()
                except Exception as e:
                    error_msg = f"线程执行错误: {e}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
        
        # 停止监控
        system_metrics = monitor.stop_monitoring()
        
        actual_end_time = datetime.now()
        actual_duration = (actual_end_time - start_time).total_seconds()
        
        # 分析结果
        total_requests = len(results)
        successful_requests = len([r for r in results if r.get('status') == 'success'])
        failed_requests = len([r for r in results if r.get('status') == 'error'])
        timeout_requests = len([r for r in results if r.get('status') == 'timeout'])
        
        # 计算延迟统计
        successful_latencies = [
            r['latency_ms'] for r in results 
            if r.get('status') == 'success' and 'latency_ms' in r
        ]
        latency_stats = self._calculate_latency_stats(successful_latencies)
        
        # 计算 QPS 和其他指标
        qps = total_requests / actual_duration if actual_duration > 0 else 0
        error_rate = failed_requests / total_requests if total_requests > 0 else 0
        avg_latency = latency_stats.mean_ms
        
        # 计算吞吐量（tokens per second）
        total_tokens = sum(
            r.get('tokens_per_second', 0) for r in results 
            if r.get('status') == 'success'
        )
        throughput_tps = total_tokens / actual_duration if actual_duration > 0 else 0
        
        test_result = QPSTestResult(
            test_id=test_id,
            model=model,
            start_time=start_time.isoformat(),
            end_time=actual_end_time.isoformat(),
            duration_seconds=actual_duration,
            concurrent_users=concurrent_users,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            timeout_requests=timeout_requests,
            qps=qps,
            avg_latency_ms=avg_latency,
            latency_stats=latency_stats,
            error_rate=error_rate,
            throughput_tokens_per_second=throughput_tps,
            system_metrics=system_metrics,
            errors=errors
        )
        
        # 保存详细结果
        self._save_qps_test_results(test_result, results)
        
        self.logger.info(f"QPS 测试完成: QPS={qps:.2f}, 平均延迟={avg_latency:.2f}ms, "
                        f"错误率={error_rate:.2%}")
        
        return test_result
    
    def run_latency_test(self, 
                        model: str, 
                        test_prompts: Optional[List[str]] = None,
                        iterations: int = 100,
                        warmup_iterations: int = 5) -> LatencyTestResult:
        """
        运行延迟测试
        
        Args:
            model: 测试模型名称
            test_prompts: 测试提示列表，None 使用默认提示
            iterations: 测试迭代次数
            warmup_iterations: 预热迭代次数
            
        Returns:
            LatencyTestResult: 测试结果
        """
        test_id = f"latency_{model.replace(':', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.logger.info(f"开始延迟测试: {test_id}")
        
        if test_prompts is None:
            test_prompts = self.default_prompts
        
        # 验证模型存在
        if not self.ollama.model_exists(model):
            error_msg = f"模型不存在: {model}"
            self.logger.error(error_msg)
            return LatencyTestResult(
                test_id=test_id,
                model=model,
                start_time=datetime.now().isoformat(),
                end_time=datetime.now().isoformat(),
                iterations=0,
                successful_iterations=0,
                failed_iterations=1,
                latency_stats=LatencyStats(0, 0, 0, 0, 0, 0, 0, 0),
                system_metrics={},
                errors=[error_msg]
            )
        
        # 预热
        if warmup_iterations > 0:
            self.logger.info(f"预热阶段开始 ({warmup_iterations} 次迭代)...")
            for i in range(warmup_iterations):
                prompt = test_prompts[i % len(test_prompts)]
                self.ollama.inference_with_metrics(model, prompt)
            self.logger.info("预热阶段完成")
        
        # 开始系统监控
        monitor = SystemMonitor()
        monitor.start_monitoring()
        
        start_time = datetime.now()
        results = []
        errors = []
        
        self.logger.info(f"延迟测试开始: {iterations} 次迭代")
        
        for i in range(iterations):
            try:
                prompt = test_prompts[i % len(test_prompts)]
                result = self.ollama.inference_with_metrics(model, prompt)
                results.append(result)
                
                # 进度报告
                if (i + 1) % max(1, iterations // 10) == 0:
                    progress = (i + 1) / iterations * 100
                    self.logger.info(f"延迟测试进度: {progress:.1f}% ({i + 1}/{iterations})")
                    
            except Exception as e:
                error_msg = f"迭代 {i+1} 错误: {e}"
                errors.append(error_msg)
                self.logger.error(error_msg)
        
        end_time = datetime.now()
        
        # 停止监控
        system_metrics = monitor.stop_monitoring()
        
        # 分析结果
        successful_results = [r for r in results if r.get('status') == 'success']
        failed_results = [r for r in results if r.get('status') != 'success']
        
        successful_latencies = [
            r['latency_ms'] for r in successful_results 
            if 'latency_ms' in r
        ]
        
        latency_stats = self._calculate_latency_stats(successful_latencies)
        
        test_result = LatencyTestResult(
            test_id=test_id,
            model=model,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            iterations=iterations,
            successful_iterations=len(successful_results),
            failed_iterations=len(failed_results),
            latency_stats=latency_stats,
            system_metrics=system_metrics,
            errors=errors
        )
        
        # 保存详细结果
        self._save_latency_test_results(test_result, results)
        
        self.logger.info(f"延迟测试完成: 平均延迟={latency_stats.mean_ms:.2f}ms, "
                        f"P95={latency_stats.p95_ms:.2f}ms, P99={latency_stats.p99_ms:.2f}ms")
        
        return test_result
    
    def _run_warmup(self, model: str, test_prompts: List[str], 
                   concurrent_users: int, duration: int):
        """执行预热"""
        end_time = datetime.now() + timedelta(seconds=duration)
        
        def warmup_worker():
            prompt_index = 0
            while datetime.now() < end_time:
                try:
                    prompt = test_prompts[prompt_index % len(test_prompts)]
                    self.ollama.inference_with_metrics(model, prompt)
                    prompt_index += 1
                except Exception:
                    pass  # 预热阶段忽略错误
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(warmup_worker) for _ in range(concurrent_users)]
            for future in as_completed(futures, timeout=duration + 10):
                try:
                    future.result()
                except Exception:
                    pass  # 预热阶段忽略错误
    
    def _save_qps_test_results(self, test_result: QPSTestResult, 
                              detailed_results: List[Dict[str, Any]]):
        """保存 QPS 测试结果"""
        # 保存汇总结果
        summary_file = os.path.join(self.results_dir, f"{test_result.test_id}_summary.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(test_result), f, indent=2, ensure_ascii=False)
        
        # 保存详细结果
        details_file = os.path.join(self.results_dir, f"{test_result.test_id}_details.jsonl")
        with open(details_file, 'w', encoding='utf-8') as f:
            for result in detailed_results:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
        
        self.logger.info(f"QPS 测试结果已保存: {summary_file}")
    
    def _save_latency_test_results(self, test_result: LatencyTestResult, 
                                  detailed_results: List[Dict[str, Any]]):
        """保存延迟测试结果"""
        # 保存汇总结果
        summary_file = os.path.join(self.results_dir, f"{test_result.test_id}_summary.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(test_result), f, indent=2, ensure_ascii=False)
        
        # 保存详细结果
        details_file = os.path.join(self.results_dir, f"{test_result.test_id}_details.jsonl")
        with open(details_file, 'w', encoding='utf-8') as f:
            for result in detailed_results:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
        
        self.logger.info(f"延迟测试结果已保存: {summary_file}")
    
    def generate_simple_html_report(self, test_result) -> str:
        """
        生成简单的 HTML 报告
        
        Args:
            test_result: 测试结果（QPSTestResult 或 LatencyTestResult）
            
        Returns:
            str: 生成的 HTML 文件路径
        """
        if isinstance(test_result, QPSTestResult):
            return self._generate_qps_html_report(test_result)
        elif isinstance(test_result, LatencyTestResult):
            return self._generate_latency_html_report(test_result)
        else:
            raise ValueError("不支持的测试结果类型")
    
    def _generate_qps_html_report(self, test_result: QPSTestResult) -> str:
        """生成 QPS 测试的 HTML 报告"""
        html_template = """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Qwen-3 QPS 性能测试报告</title>
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
                .status-badge {{
                    display: inline-block;
                    padding: 4px 12px;
                    border-radius: 20px;
                    font-size: 0.9em;
                    font-weight: bold;
                }}
                .status-success {{ background: #d4edda; color: #155724; }}
                .status-warning {{ background: #fff3cd; color: #856404; }}
                .status-error {{ background: #f8d7da; color: #721c24; }}
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
                <h1>🚀 Qwen-3 QPS 性能测试报告</h1>
                
                <div class="metric-grid">
                    <div class="metric">
                        <div class="metric-title">测试模型</div>
                        <div class="metric-value">{model}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-title">测试 ID</div>
                        <div class="metric-value">{test_id}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-title">测试时间</div>
                        <div class="metric-value">{duration:.1f}s</div>
                    </div>
                    <div class="metric">
                        <div class="metric-title">并发用户</div>
                        <div class="metric-value">{concurrent_users}</div>
                    </div>
                </div>

                <h2>📊 核心性能指标</h2>
                <div class="metric-grid">
                    <div class="metric">
                        <div class="metric-title">QPS (每秒查询数)</div>
                        <div class="metric-value {qps_class}">{qps:.2f}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-title">平均延迟</div>
                        <div class="metric-value {latency_class}">{avg_latency:.2f}ms</div>
                    </div>
                    <div class="metric">
                        <div class="metric-title">错误率</div>
                        <div class="metric-value {error_class}">{error_rate:.2%}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-title">吞吐量</div>
                        <div class="metric-value">{throughput:.2f} tokens/s</div>
                    </div>
                </div>

                <h2>📈 延迟分布统计</h2>
                <table>
                    <tr>
                        <th>指标</th>
                        <th>值 (ms)</th>
                        <th>说明</th>
                    </tr>
                    <tr>
                        <td>最小延迟</td>
                        <td>{min_latency:.2f}</td>
                        <td>最快响应时间</td>
                    </tr>
                    <tr>
                        <td>最大延迟</td>
                        <td>{max_latency:.2f}</td>
                        <td>最慢响应时间</td>
                    </tr>
                    <tr>
                        <td>中位数 (P50)</td>
                        <td>{p50_latency:.2f}</td>
                        <td>50% 的请求延迟低于此值</td>
                    </tr>
                    <tr>
                        <td>95分位数 (P95)</td>
                        <td>{p95_latency:.2f}</td>
                        <td>95% 的请求延迟低于此值</td>
                    </tr>
                    <tr>
                        <td>99分位数 (P99)</td>
                        <td>{p99_latency:.2f}</td>
                        <td>99% 的请求延迟低于此值</td>
                    </tr>
                    <tr>
                        <td>标准差</td>
                        <td>{std_dev:.2f}</td>
                        <td>延迟分布的离散程度</td>
                    </tr>
                </table>

                <h2>💻 系统资源使用</h2>
                <div class="metric-grid">
                    <div class="metric">
                        <div class="metric-title">平均 CPU 使用率</div>
                        <div class="metric-value">{cpu_avg:.1f}%</div>
                    </div>
                    <div class="metric">
                        <div class="metric-title">最大 CPU 使用率</div>
                        <div class="metric-value">{cpu_max:.1f}%</div>
                    </div>
                    <div class="metric">
                        <div class="metric-title">平均内存使用率</div>
                        <div class="metric-value">{memory_avg:.1f}%</div>
                    </div>
                    <div class="metric">
                        <div class="metric-title">最大内存使用</div>
                        <div class="metric-value">{memory_max:.1f} MB</div>
                    </div>
                </div>

                <h2>📋 测试详情</h2>
                <table>
                    <tr>
                        <th>指标</th>
                        <th>数值</th>
                    </tr>
                    <tr>
                        <td>总请求数</td>
                        <td>{total_requests}</td>
                    </tr>
                    <tr>
                        <td>成功请求数</td>
                        <td><span class="good">{successful_requests}</span></td>
                    </tr>
                    <tr>
                        <td>失败请求数</td>
                        <td><span class="error">{failed_requests}</span></td>
                    </tr>
                    <tr>
                        <td>超时请求数</td>
                        <td><span class="warning">{timeout_requests}</span></td>
                    </tr>
                    <tr>
                        <td>开始时间</td>
                        <td>{start_time}</td>
                    </tr>
                    <tr>
                        <td>结束时间</td>
                        <td>{end_time}</td>
                    </tr>
                </table>

                <div class="footer">
                    <p>报告生成时间: {report_time}</p>
                    <p>🤖 由 Qwen-3 本地性能测试套件生成</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # 确定性能指标的样式类
        qps_class = "good" if test_result.qps > 10 else "warning" if test_result.qps > 5 else "error"
        latency_class = "good" if test_result.avg_latency_ms < 1000 else "warning" if test_result.avg_latency_ms < 3000 else "error"
        error_class = "good" if test_result.error_rate < 0.01 else "warning" if test_result.error_rate < 0.05 else "error"
        
        # 系统资源指标
        cpu_avg = test_result.system_metrics.get('cpu', {}).get('avg_percent', 0)
        cpu_max = test_result.system_metrics.get('cpu', {}).get('max_percent', 0)
        memory_avg = test_result.system_metrics.get('memory', {}).get('avg_percent', 0)
        memory_max = test_result.system_metrics.get('memory', {}).get('max_used_mb', 0)
        
        html_content = html_template.format(
            model=test_result.model,
            test_id=test_result.test_id,
            duration=test_result.duration_seconds,
            concurrent_users=test_result.concurrent_users,
            qps=test_result.qps,
            qps_class=qps_class,
            avg_latency=test_result.avg_latency_ms,
            latency_class=latency_class,
            error_rate=test_result.error_rate,
            error_class=error_class,
            throughput=test_result.throughput_tokens_per_second,
            min_latency=test_result.latency_stats.min_ms,
            max_latency=test_result.latency_stats.max_ms,
            p50_latency=test_result.latency_stats.median_ms,
            p95_latency=test_result.latency_stats.p95_ms,
            p99_latency=test_result.latency_stats.p99_ms,
            std_dev=test_result.latency_stats.std_dev_ms,
            cpu_avg=cpu_avg,
            cpu_max=cpu_max,
            memory_avg=memory_avg,
            memory_max=memory_max,
            total_requests=test_result.total_requests,
            successful_requests=test_result.successful_requests,
            failed_requests=test_result.failed_requests,
            timeout_requests=test_result.timeout_requests,
            start_time=test_result.start_time,
            end_time=test_result.end_time,
            report_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        report_file = os.path.join(self.results_dir, f"{test_result.test_id}_report.html")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"QPS 测试 HTML 报告已生成: {report_file}")
        return report_file
    
    def _generate_latency_html_report(self, test_result: LatencyTestResult) -> str:
        """生成延迟测试的 HTML 报告"""
        html_template = """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Qwen-3 延迟性能测试报告</title>
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
                <h1>⚡ Qwen-3 延迟性能测试报告</h1>
                
                <div class="metric-grid">
                    <div class="metric">
                        <div class="metric-title">测试模型</div>
                        <div class="metric-value">{model}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-title">测试 ID</div>
                        <div class="metric-value">{test_id}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-title">测试迭代次数</div>
                        <div class="metric-value">{iterations}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-title">成功率</div>
                        <div class="metric-value {success_class}">{success_rate:.2%}</div>
                    </div>
                </div>

                <h2>📊 延迟统计分析</h2>
                <table>
                    <tr>
                        <th>指标</th>
                        <th>值 (ms)</th>
                        <th>说明</th>
                    </tr>
                    <tr>
                        <td>平均延迟</td>
                        <td class="{avg_class}">{mean_latency:.2f}</td>
                        <td>所有成功请求的平均响应时间</td>
                    </tr>
                    <tr>
                        <td>中位数延迟 (P50)</td>
                        <td>{median_latency:.2f}</td>
                        <td>50% 的请求延迟低于此值</td>
                    </tr>
                    <tr>
                        <td>95分位数 (P95)</td>
                        <td class="{p95_class}">{p95_latency:.2f}</td>
                        <td>95% 的请求延迟低于此值</td>
                    </tr>
                    <tr>
                        <td>99分位数 (P99)</td>
                        <td class="{p99_class}">{p99_latency:.2f}</td>
                        <td>99% 的请求延迟低于此值</td>
                    </tr>
                    <tr>
                        <td>最小延迟</td>
                        <td class="good">{min_latency:.2f}</td>
                        <td>最快响应时间</td>
                    </tr>
                    <tr>
                        <td>最大延迟</td>
                        <td class="{max_class}">{max_latency:.2f}</td>
                        <td>最慢响应时间</td>
                    </tr>
                    <tr>
                        <td>标准差</td>
                        <td>{std_dev:.2f}</td>
                        <td>延迟分布的离散程度</td>
                    </tr>
                </table>

                <h2>💻 系统资源使用</h2>
                <div class="metric-grid">
                    <div class="metric">
                        <div class="metric-title">平均 CPU 使用率</div>
                        <div class="metric-value">{cpu_avg:.1f}%</div>
                    </div>
                    <div class="metric">
                        <div class="metric-title">最大 CPU 使用率</div>
                        <div class="metric-value">{cpu_max:.1f}%</div>
                    </div>
                    <div class="metric">
                        <div class="metric-title">平均内存使用率</div>
                        <div class="metric-value">{memory_avg:.1f}%</div>
                    </div>
                    <div class="metric">
                        <div class="metric-title">最大内存使用</div>
                        <div class="metric-value">{memory_max:.1f} MB</div>
                    </div>
                </div>

                <h2>📋 测试详情</h2>
                <table>
                    <tr>
                        <th>指标</th>
                        <th>数值</th>
                    </tr>
                    <tr>
                        <td>总迭代次数</td>
                        <td>{iterations}</td>
                    </tr>
                    <tr>
                        <td>成功迭代次数</td>
                        <td><span class="good">{successful_iterations}</span></td>
                    </tr>
                    <tr>
                        <td>失败迭代次数</td>
                        <td><span class="error">{failed_iterations}</span></td>
                    </tr>
                    <tr>
                        <td>开始时间</td>
                        <td>{start_time}</td>
                    </tr>
                    <tr>
                        <td>结束时间</td>
                        <td>{end_time}</td>
                    </tr>
                </table>

                <div class="footer">
                    <p>报告生成时间: {report_time}</p>
                    <p>🤖 由 Qwen-3 本地性能测试套件生成</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # 计算成功率
        success_rate = (test_result.successful_iterations / test_result.iterations 
                       if test_result.iterations > 0 else 0)
        
        # 确定性能指标的样式类
        success_class = "good" if success_rate > 0.95 else "warning" if success_rate > 0.9 else "error"
        avg_class = "good" if test_result.latency_stats.mean_ms < 1000 else "warning" if test_result.latency_stats.mean_ms < 3000 else "error"
        p95_class = "good" if test_result.latency_stats.p95_ms < 2000 else "warning" if test_result.latency_stats.p95_ms < 5000 else "error"
        p99_class = "good" if test_result.latency_stats.p99_ms < 3000 else "warning" if test_result.latency_stats.p99_ms < 8000 else "error"
        max_class = "good" if test_result.latency_stats.max_ms < 5000 else "warning" if test_result.latency_stats.max_ms < 10000 else "error"
        
        # 系统资源指标
        cpu_avg = test_result.system_metrics.get('cpu', {}).get('avg_percent', 0)
        cpu_max = test_result.system_metrics.get('cpu', {}).get('max_percent', 0)
        memory_avg = test_result.system_metrics.get('memory', {}).get('avg_percent', 0)
        memory_max = test_result.system_metrics.get('memory', {}).get('max_used_mb', 0)
        
        html_content = html_template.format(
            model=test_result.model,
            test_id=test_result.test_id,
            iterations=test_result.iterations,
            success_rate=success_rate,
            success_class=success_class,
            mean_latency=test_result.latency_stats.mean_ms,
            avg_class=avg_class,
            median_latency=test_result.latency_stats.median_ms,
            p95_latency=test_result.latency_stats.p95_ms,
            p95_class=p95_class,
            p99_latency=test_result.latency_stats.p99_ms,
            p99_class=p99_class,
            min_latency=test_result.latency_stats.min_ms,
            max_latency=test_result.latency_stats.max_ms,
            max_class=max_class,
            std_dev=test_result.latency_stats.std_dev_ms,
            cpu_avg=cpu_avg,
            cpu_max=cpu_max,
            memory_avg=memory_avg,
            memory_max=memory_max,
            successful_iterations=test_result.successful_iterations,
            failed_iterations=test_result.failed_iterations,
            start_time=test_result.start_time,
            end_time=test_result.end_time,
            report_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        report_file = os.path.join(self.results_dir, f"{test_result.test_id}_report.html")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"延迟测试 HTML 报告已生成: {report_file}")
        return report_file
    
    def run_comprehensive_test(self, model: str, 
                             test_prompts: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        运行综合性能测试
        
        Args:
            model: 测试模型名称
            test_prompts: 测试提示列表
            
        Returns:
            Dict: 包含所有测试结果的字典
        """
        self.logger.info(f"开始综合性能测试: {model}")
        
        results = {}
        
        try:
            # 延迟测试
            self.logger.info("第 1/2 步: 执行延迟测试...")
            latency_result = self.run_latency_test(model, test_prompts, iterations=50)
            results['latency_test'] = latency_result
            latency_report = self.generate_simple_html_report(latency_result)
            results['latency_report'] = latency_report
            
            # QPS 测试
            self.logger.info("第 2/2 步: 执行 QPS 测试...")
            qps_result = self.run_basic_qps_test(model, test_prompts, 
                                               concurrent_users=3, duration=30)
            results['qps_test'] = qps_result
            qps_report = self.generate_simple_html_report(qps_result)
            results['qps_report'] = qps_report
            
            # 生成综合摘要
            summary = {
                'model': model,
                'test_time': datetime.now().isoformat(),
                'latency_summary': {
                    'avg_ms': latency_result.latency_stats.mean_ms,
                    'p95_ms': latency_result.latency_stats.p95_ms,
                    'p99_ms': latency_result.latency_stats.p99_ms,
                    'success_rate': (latency_result.successful_iterations / 
                                   latency_result.iterations if latency_result.iterations > 0 else 0)
                },
                'qps_summary': {
                    'qps': qps_result.qps,
                    'avg_latency_ms': qps_result.avg_latency_ms,
                    'error_rate': qps_result.error_rate,
                    'throughput_tps': qps_result.throughput_tokens_per_second
                }
            }
            
            results['comprehensive_summary'] = summary
            
            # 保存综合摘要
            summary_file = os.path.join(self.results_dir, 
                                      f"comprehensive_{model.replace(':', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            results['summary_file'] = summary_file
            
            self.logger.info(f"综合性能测试完成: {model}")
            
        except Exception as e:
            error_msg = f"综合测试执行错误: {e}"
            self.logger.error(error_msg)
            results['error'] = error_msg
        
        return results
    
    def run_dataset_evaluation(self, model: str, dataset_name: str,
                             sample_count: Optional[int] = None,
                             categories: Optional[List[str]] = None) -> EvaluationReport:
        """
        运行测试集评估
        
        Args:
            model: 测试模型名称
            dataset_name: 测试集名称
            sample_count: 样本数量限制
            categories: 筛选特定类别
            
        Returns:
            EvaluationReport: 评估报告
        """
        self.logger.info(f"开始测试集评估: {model} on {dataset_name}")
        
        # 验证模型存在
        if not self.ollama.model_exists(model):
            raise ValueError(f"模型不存在: {model}")
        
        # 获取测试样本
        test_samples = self.dataset_manager.get_test_samples(
            dataset_name, sample_count, categories
        )
        
        if not test_samples:
            raise ValueError(f"未找到测试样本: {dataset_name}")
        
        self.logger.info(f"获取到 {len(test_samples)} 个测试样本")
        
        # 创建测试提示词
        prompts = self.dataset_manager.create_test_prompts(dataset_name, test_samples)
        
        # 执行模型推理
        model_responses = []
        for i, prompt in enumerate(prompts):
            try:
                self.logger.info(f"处理样本 {i+1}/{len(prompts)}")
                response = self.ollama.inference_with_metrics(model, prompt)
                model_responses.append(response)
            except Exception as e:
                self.logger.error(f"样本 {i+1} 推理失败: {e}")
                model_responses.append({
                    'response': '',
                    'latency_ms': 0,
                    'status': 'error',
                    'error': str(e)
                })
        
        # 评估结果
        test_results = self.dataset_manager.evaluate_model_responses(
            dataset_name, test_samples, model_responses
        )
        
        # 生成评估报告
        report = self.dataset_manager.generate_evaluation_report(
            dataset_name, model, test_results
        )
        
        # 保存报告
        json_report_path = self.dataset_manager.save_evaluation_report(
            report, self.results_dir
        )
        html_report_path = self.dataset_manager.generate_html_report(
            report, self.results_dir
        )
        
        self.logger.info(f"测试集评估完成")
        self.logger.info(f"JSON报告: {json_report_path}")
        self.logger.info(f"HTML报告: {html_report_path}")
        
        return report
    
    def run_all_dataset_evaluations(self, model: str,
                                   sample_count: Optional[int] = None) -> Dict[str, EvaluationReport]:
        """
        运行所有可用测试集的评估
        
        Args:
            model: 测试模型名称
            sample_count: 每个测试集的样本数量限制
            
        Returns:
            Dict[str, EvaluationReport]: 所有测试集的评估报告
        """
        self.logger.info(f"开始运行所有测试集评估: {model}")
        
        available_datasets = self.dataset_manager.list_available_datasets()
        reports = {}
        
        for dataset_name in available_datasets:
            try:
                self.logger.info(f"评估测试集: {dataset_name}")
                report = self.run_dataset_evaluation(model, dataset_name, sample_count)
                reports[dataset_name] = report
                
                # 显示简要结果
                self.logger.info(f"  - 总样本数: {report.total_samples}")
                self.logger.info(f"  - 成功率: {report.successful_tests/report.total_samples:.2%}")
                self.logger.info(f"  - 评分准确性: {report.avg_score_accuracy:.2%}")
                self.logger.info(f"  - 类别准确性: {report.category_accuracy:.2%}")
                
            except Exception as e:
                self.logger.error(f"测试集 {dataset_name} 评估失败: {e}")
                continue
        
        # 生成综合摘要
        summary = {
            'model': model,
            'evaluation_time': datetime.now().isoformat(),
            'datasets_evaluated': len(reports),
            'total_samples': sum(r.total_samples for r in reports.values()),
            'overall_success_rate': sum(r.successful_tests for r in reports.values()) / sum(r.total_samples for r in reports.values()) if reports else 0,
            'average_score_accuracy': sum(r.avg_score_accuracy for r in reports.values()) / len(reports) if reports else 0,
            'average_category_accuracy': sum(r.category_accuracy for r in reports.values()) / len(reports) if reports else 0,
            'dataset_summaries': {
                name: {
                    'total_samples': report.total_samples,
                    'success_rate': report.successful_tests / report.total_samples if report.total_samples > 0 else 0,
                    'score_accuracy': report.avg_score_accuracy,
                    'category_accuracy': report.category_accuracy
                }
                for name, report in reports.items()
            }
        }
        
        # 保存综合摘要
        summary_file = os.path.join(self.results_dir, 
                                  f"all_datasets_{model.replace(':', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"所有测试集评估完成")
        self.logger.info(f"综合摘要: {summary_file}")
        self.logger.info(f"评估了 {len(reports)} 个测试集，共 {summary['total_samples']} 个样本")
        self.logger.info(f"整体成功率: {summary['overall_success_rate']:.2%}")
        self.logger.info(f"平均评分准确性: {summary['average_score_accuracy']:.2%}")
        self.logger.info(f"平均类别准确性: {summary['average_category_accuracy']:.2%}")
        
        return reports
    
    def list_available_datasets(self) -> List[str]:
        """列出可用的测试集"""
        return self.dataset_manager.list_available_datasets()
    
    def get_dataset_info(self, dataset_name: str) -> Optional[Dict[str, Any]]:
        """获取测试集信息"""
        return self.dataset_manager.get_dataset_info(dataset_name)


if __name__ == "__main__":
    # 示例用法和测试
    import sys
    import argparse
    from .ollama_integration import create_ollama_client
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='Qwen-3 本地性能测试工具')
    parser.add_argument('--model', default='qwen3:0.6b', help='测试模型名称')
    parser.add_argument('--test-type', choices=['latency', 'qps', 'comprehensive', 'dataset', 'all-datasets'], 
                       default='comprehensive', help='测试类型')
    parser.add_argument('--concurrent-users', type=int, default=5, help='QPS 测试并发用户数')
    parser.add_argument('--duration', type=int, default=60, help='QPS 测试持续时间（秒）')
    parser.add_argument('--iterations', type=int, default=100, help='延迟测试迭代次数')
    parser.add_argument('--ollama-url', default='http://localhost:11434', help='Ollama 服务地址')
    parser.add_argument('--dataset', help='指定测试集名称（用于dataset测试类型）')
    parser.add_argument('--sample-count', type=int, help='测试样本数量限制')
    parser.add_argument('--categories', nargs='+', help='筛选特定类别')
    
    args = parser.parse_args()
    
    try:
        # 创建 Ollama 客户端和测试器
        with create_ollama_client(args.ollama_url) as ollama_client:
            tester = SimpleLocalTester(ollama_client)
            
            print(f"🔍 检查 Ollama 服务状态...")
            if not ollama_client.check_ollama_status():
                print("❌ Ollama 服务未运行，请先启动 Ollama")
                sys.exit(1)
            
            print("✅ Ollama 服务正常")
            
            # 检查模型存在性
            if not ollama_client.model_exists(args.model):
                print(f"❌ 模型不存在: {args.model}")
                print("可用模型:")
                for model in ollama_client.list_models():
                    print(f"  - {model}")
                sys.exit(1)
            
            print(f"✅ 模型存在: {args.model}")
            
            # 执行测试
            if args.test_type == 'latency':
                print(f"📊 开始延迟测试 ({args.iterations} 次迭代)...")
                result = tester.run_latency_test(args.model, iterations=args.iterations)
                report = tester.generate_simple_html_report(result)
                print(f"✅ 延迟测试完成")
                print(f"   平均延迟: {result.latency_stats.mean_ms:.2f}ms")
                print(f"   P95 延迟: {result.latency_stats.p95_ms:.2f}ms")
                print(f"   P99 延迟: {result.latency_stats.p99_ms:.2f}ms")
                print(f"   报告文件: {report}")
                
            elif args.test_type == 'qps':
                print(f"📊 开始 QPS 测试 ({args.concurrent_users} 并发, {args.duration}s)...")
                result = tester.run_basic_qps_test(
                    args.model, 
                    concurrent_users=args.concurrent_users,
                    duration=args.duration
                )
                report = tester.generate_simple_html_report(result)
                print(f"✅ QPS 测试完成")
                print(f"   QPS: {result.qps:.2f}")
                print(f"   平均延迟: {result.avg_latency_ms:.2f}ms")
                print(f"   错误率: {result.error_rate:.2%}")
                print(f"   报告文件: {report}")
                
            elif args.test_type == 'comprehensive':
                print(f"📊 开始综合性能测试...")
                results = tester.run_comprehensive_test(args.model)
                
                if 'error' in results:
                    print(f"❌ 测试失败: {results['error']}")
                    sys.exit(1)
                
                print(f"✅ 综合测试完成")
                summary = results['comprehensive_summary']
                print(f"   延迟 - 平均: {summary['latency_summary']['avg_ms']:.2f}ms, "
                      f"P95: {summary['latency_summary']['p95_ms']:.2f}ms")
                print(f"   QPS: {summary['qps_summary']['qps']:.2f}, "
                      f"错误率: {summary['qps_summary']['error_rate']:.2%}")
                print(f"   延迟报告: {results['latency_report']}")
                print(f"   QPS 报告: {results['qps_report']}")
                print(f"   综合摘要: {results['summary_file']}")
                
            elif args.test_type == 'dataset':
                if not args.dataset:
                    print("❌ 请指定测试集名称 (--dataset)")
                    print("可用测试集:")
                    for dataset in tester.list_available_datasets():
                        info = tester.get_dataset_info(dataset)
                        if info:
                            print(f"  - {dataset}: {info.get('name', 'N/A')} ({info.get('total_samples', 0)} 样本)")
                    sys.exit(1)
                
                print(f"📊 开始测试集评估: {args.dataset}")
                try:
                    report = tester.run_dataset_evaluation(
                        args.model, args.dataset, 
                        args.sample_count, args.categories
                    )
                    print(f"✅ 测试集评估完成")
                    print(f"   总样本数: {report.total_samples}")
                    print(f"   成功测试数: {report.successful_tests}")
                    print(f"   成功率: {report.successful_tests/report.total_samples:.2%}")
                    print(f"   评分准确性: {report.avg_score_accuracy:.2%}")
                    print(f"   类别准确性: {report.category_accuracy:.2%}")
                    print(f"   平均响应时间: {report.avg_response_time_ms:.2f}ms")
                except Exception as e:
                    print(f"❌ 测试集评估失败: {e}")
                    sys.exit(1)
                    
            elif args.test_type == 'all-datasets':
                print(f"📊 开始所有测试集评估...")
                try:
                    reports = tester.run_all_dataset_evaluations(args.model, args.sample_count)
                    print(f"✅ 所有测试集评估完成")
                    print(f"   评估了 {len(reports)} 个测试集")
                    
                    for dataset_name, report in reports.items():
                        print(f"   📋 {dataset_name}:")
                        print(f"     - 样本数: {report.total_samples}")
                        print(f"     - 成功率: {report.successful_tests/report.total_samples:.2%}")
                        print(f"     - 评分准确性: {report.avg_score_accuracy:.2%}")
                        print(f"     - 类别准确性: {report.category_accuracy:.2%}")
                        
                except Exception as e:
                    print(f"❌ 所有测试集评估失败: {e}")
                    sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 测试被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 测试执行错误: {e}")
        sys.exit(1)