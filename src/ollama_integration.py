#!/usr/bin/env python3
"""
Qwen-3 Ollama 集成模块

提供与 Ollama 服务的完整集成功能，包括：
- 服务状态检查和健康监控
- 模型管理和列表获取
- 带指标收集的推理接口
- 错误处理和重试机制
- 连接池管理和性能优化

作者: Qwen-3 部署团队
版本: 1.0.0
"""

import json
import time
import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urljoin
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


@dataclass
class InferenceMetrics:
    """推理指标数据类"""
    model: str
    prompt_length: int
    response_length: int
    latency_ms: float
    status: str
    timestamp: str
    error: Optional[str] = None
    tokens_per_second: Optional[float] = None
    memory_usage_mb: Optional[float] = None


@dataclass
class HealthStatus:
    """健康状态数据类"""
    status: str  # healthy, unhealthy, degraded
    latency_ms: float
    models_count: int
    models: List[str]
    timestamp: str
    error: Optional[str] = None
    uptime_seconds: Optional[float] = None


class OllamaConnectionError(Exception):
    """Ollama 连接错误"""
    pass


class OllamaModelError(Exception):
    """Ollama 模型错误"""
    pass


class OllamaIntegration:
    """
    Ollama 集成核心类
    
    提供与 Ollama 服务的完整集成功能，包括连接管理、
    模型操作、推理服务和性能监控。
    """
    
    def __init__(self, 
                 base_url: str = "http://localhost:11434",
                 timeout: int = 30,
                 max_retries: int = 3,
                 retry_backoff_factor: float = 0.3,
                 pool_connections: int = 10,
                 pool_maxsize: int = 10):
        """
        初始化 Ollama 集成
        
        Args:
            base_url: Ollama 服务基础 URL
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            retry_backoff_factor: 重试退避因子
            pool_connections: 连接池连接数
            pool_maxsize: 连接池最大大小
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 创建会话和连接池
        self.session = self._create_session(
            max_retries, retry_backoff_factor, 
            pool_connections, pool_maxsize
        )
        
        # 性能统计
        self._stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_latency': 0.0,
            'start_time': time.time()
        }
        self._stats_lock = threading.Lock()
        
        # 缓存
        self._models_cache = None
        self._models_cache_time = 0
        self._cache_ttl = 300  # 5分钟缓存
        
        self.logger.info(f"Ollama 集成初始化完成: {self.base_url}")
    
    def _create_session(self, max_retries: int, backoff_factor: float,
                       pool_connections: int, pool_maxsize: int) -> requests.Session:
        """创建配置好的 requests 会话"""
        session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"]
        )
        
        # 配置适配器
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # 设置默认头部
        session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Qwen3-Integration/1.0.0'
        })
        
        return session
    
    def _update_stats(self, success: bool, latency: float):
        """更新性能统计"""
        with self._stats_lock:
            self._stats['total_requests'] += 1
            self._stats['total_latency'] += latency
            
            if success:
                self._stats['successful_requests'] += 1
            else:
                self._stats['failed_requests'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        with self._stats_lock:
            stats = self._stats.copy()
            
        uptime = time.time() - stats['start_time']
        avg_latency = (stats['total_latency'] / stats['total_requests'] 
                      if stats['total_requests'] > 0 else 0)
        success_rate = (stats['successful_requests'] / stats['total_requests'] 
                       if stats['total_requests'] > 0 else 0)
        
        return {
            **stats,
            'uptime_seconds': uptime,
            'average_latency_ms': avg_latency * 1000,
            'success_rate': success_rate,
            'requests_per_second': stats['total_requests'] / uptime if uptime > 0 else 0
        }
    
    def check_ollama_status(self) -> bool:
        """
        检查 Ollama 服务状态
        
        Returns:
            bool: 服务是否正常运行
        """
        try:
            start_time = time.time()
            response = self.session.get(
                urljoin(self.base_url, '/api/tags'),
                timeout=5  # 使用较短的超时时间进行快速检查
            )
            latency = time.time() - start_time
            
            success = response.status_code == 200
            self._update_stats(success, latency)
            
            if success:
                self.logger.debug(f"Ollama 服务状态检查成功，延迟: {latency*1000:.2f}ms")
                return True
            else:
                self.logger.warning(f"Ollama 服务状态检查失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            latency = time.time() - start_time if 'start_time' in locals() else 0
            self._update_stats(False, latency)
            self.logger.error(f"Ollama 服务状态检查异常: {e}")
            return False
    
    def list_models(self, use_cache: bool = False) -> List[str]:
        """
        获取可用模型列表
        
        Args:
            use_cache: 是否使用缓存（默认False，因为模型列表查询很快且需要实时性）
            
        Returns:
            List[str]: 模型名称列表
            
        Raises:
            OllamaConnectionError: 连接失败
        """
        # 检查缓存（仅在明确要求时使用）
        if use_cache and self._models_cache is not None:
            cache_age = time.time() - self._models_cache_time
            if cache_age < self._cache_ttl:
                self.logger.debug(f"使用缓存的模型列表，缓存年龄: {cache_age:.1f}s")
                return self._models_cache
        
        try:
            start_time = time.time()
            response = self.session.get(
                urljoin(self.base_url, '/api/tags'),
                timeout=self.timeout
            )
            latency = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                models = [model['name'] for model in data.get('models', [])]
                
                # 更新缓存（备用）
                self._models_cache = models
                self._models_cache_time = time.time()
                
                self._update_stats(True, latency)
                self.logger.debug(f"获取模型列表成功: {len(models)} 个模型 (耗时: {latency*1000:.1f}ms)")
                return models
            else:
                self._update_stats(False, latency)
                error_msg = f"获取模型列表失败: HTTP {response.status_code}"
                self.logger.error(error_msg)
                raise OllamaConnectionError(error_msg)
                
        except requests.exceptions.RequestException as e:
            latency = time.time() - start_time if 'start_time' in locals() else 0
            self._update_stats(False, latency)
            error_msg = f"获取模型列表网络错误: {e}"
            self.logger.error(error_msg)
            raise OllamaConnectionError(error_msg)
    
    def model_exists(self, model_name: str) -> bool:
        """
        检查模型是否存在
        
        Args:
            model_name: 模型名称
            
        Returns:
            bool: 模型是否存在
        """
        try:
            models = self.list_models()
            return model_name in models
        except Exception as e:
            self.logger.error(f"检查模型存在性失败: {e}")
            return False
    
    def inference_with_metrics(self, 
                             model: str, 
                             prompt: str,
                             stream: bool = False,
                             enable_thinking: bool = True,
                             **options) -> InferenceMetrics:
        """
        带指标收集的推理接口
        
        Args:
            model: 模型名称
            prompt: 输入提示
            stream: 是否流式输出
            enable_thinking: 是否启用模型思考过程
            **options: 其他推理选项
            
        Returns:
            InferenceMetrics: 推理结果和指标
            
        Raises:
            OllamaModelError: 模型相关错误
            OllamaConnectionError: 连接错误
        """
        start_time = time.time()
        
        # 验证模型存在性
        if not self.model_exists(model):
            error_msg = f"模型不存在: {model}"
            self.logger.error(error_msg)
            return InferenceMetrics(
                model=model,
                prompt_length=len(prompt),
                response_length=0,
                latency_ms=0,
                status="error",
                timestamp=datetime.now().isoformat(),
                error=error_msg
            )
        
        request_data = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "think": enable_thinking,  # 直接控制思考开关
            **options
        }
        
        # 记录思考开关状态
        thinking_status = "启用" if enable_thinking else "禁用"
        self.logger.info(f"模型推理请求 - 模型: {model}, 思考: {thinking_status} (think: {enable_thinking})")
        
        try:
            response = self.session.post(
                urljoin(self.base_url, '/api/generate'),
                json=request_data,
                timeout=self.timeout
            )
            
            end_time = time.time()
            latency = end_time - start_time
            
            if response.status_code == 200:
                result_data = response.json()
                response_text = result_data.get("response", "")
                
                # 计算 tokens per second (估算)
                response_tokens = len(response_text.split())
                tokens_per_second = response_tokens / latency if latency > 0 else 0
                
                metrics = InferenceMetrics(
                    model=model,
                    prompt_length=len(prompt),
                    response_length=len(response_text),
                    latency_ms=latency * 1000,
                    status="success",
                    timestamp=datetime.now().isoformat(),
                    tokens_per_second=tokens_per_second
                )
                
                self._update_stats(True, latency)
                self.logger.info(f"推理成功: {model}, 延迟: {latency*1000:.2f}ms, "
                               f"TPS: {tokens_per_second:.2f}")
                
                # 添加响应内容到指标中（用于返回给调用者）
                metrics_dict = asdict(metrics)
                metrics_dict['response'] = response_text
                return metrics_dict
                
            else:
                error_msg = f"推理请求失败: HTTP {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                self._update_stats(False, latency)
                
                return InferenceMetrics(
                    model=model,
                    prompt_length=len(prompt),
                    response_length=0,
                    latency_ms=latency * 1000,
                    status="error",
                    timestamp=datetime.now().isoformat(),
                    error=error_msg
                )
                
        except requests.exceptions.Timeout:
            latency = time.time() - start_time
            error_msg = f"推理请求超时: {self.timeout}s"
            self.logger.error(error_msg)
            self._update_stats(False, latency)
            
            return InferenceMetrics(
                model=model,
                prompt_length=len(prompt),
                response_length=0,
                latency_ms=latency * 1000,
                status="timeout",
                timestamp=datetime.now().isoformat(),
                error=error_msg
            )
            
        except requests.exceptions.RequestException as e:
            latency = time.time() - start_time
            error_msg = f"推理请求网络错误: {e}"
            self.logger.error(error_msg)
            self._update_stats(False, latency)
            
            return InferenceMetrics(
                model=model,
                prompt_length=len(prompt),
                response_length=0,
                latency_ms=latency * 1000,
                status="error",
                timestamp=datetime.now().isoformat(),
                error=error_msg
            )
    
    def health_check(self) -> HealthStatus:
        """
        综合健康检查
        
        Returns:
            HealthStatus: 详细的健康状态信息
        """
        start_time = time.time()
        
        try:
            # 检查服务状态
            response = self.session.get(
                urljoin(self.base_url, '/api/tags'),
                timeout=10
            )
            latency = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                # 获取模型列表
                try:
                    models = self.list_models(use_cache=False)
                    models_count = len(models)
                    
                    # 判断健康状态
                    if models_count == 0:
                        status = "degraded"
                        error = "没有可用的模型"
                    elif latency > 5000:  # 5秒以上认为性能降级
                        status = "degraded"
                        error = f"响应延迟过高: {latency:.2f}ms"
                    else:
                        status = "healthy"
                        error = None
                        
                except Exception as e:
                    status = "degraded"
                    models = []
                    models_count = 0
                    error = f"获取模型列表失败: {e}"
                
                # 获取统计信息
                stats = self.get_stats()
                
                return HealthStatus(
                    status=status,
                    latency_ms=latency,
                    models_count=models_count,
                    models=models,
                    timestamp=datetime.now().isoformat(),
                    error=error,
                    uptime_seconds=stats['uptime_seconds']
                )
                
            else:
                return HealthStatus(
                    status="unhealthy",
                    latency_ms=latency,
                    models_count=0,
                    models=[],
                    timestamp=datetime.now().isoformat(),
                    error=f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return HealthStatus(
                status="unhealthy",
                latency_ms=latency,
                models_count=0,
                models=[],
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )
    
    def pull_model(self, model_name: str, timeout: Optional[int] = None) -> bool:
        """
        拉取模型
        
        Args:
            model_name: 模型名称
            timeout: 超时时间（秒），None 使用默认值
            
        Returns:
            bool: 是否成功
        """
        try:
            self.logger.info(f"开始拉取模型: {model_name}")
            
            response = self.session.post(
                urljoin(self.base_url, '/api/pull'),
                json={"name": model_name},
                timeout=timeout or 600  # 默认10分钟超时
            )
            
            if response.status_code == 200:
                self.logger.info(f"模型拉取成功: {model_name}")
                # 清除模型缓存
                self._models_cache = None
                return True
            else:
                self.logger.error(f"模型拉取失败: {model_name}, HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"模型拉取异常: {model_name}, {e}")
            return False
    
    def delete_model(self, model_name: str) -> bool:
        """
        删除模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            bool: 是否成功
        """
        try:
            self.logger.info(f"开始删除模型: {model_name}")
            
            response = self.session.delete(
                urljoin(self.base_url, '/api/delete'),
                json={"name": model_name},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                self.logger.info(f"模型删除成功: {model_name}")
                # 清除模型缓存
                self._models_cache = None
                return True
            else:
                self.logger.error(f"模型删除失败: {model_name}, HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"模型删除异常: {model_name}, {e}")
            return False
    
    def close(self):
        """关闭连接"""
        if self.session:
            self.session.close()
            self.logger.info("Ollama 集成连接已关闭")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


# 便捷函数
def create_ollama_client(base_url: str = "http://localhost:11434", **kwargs) -> OllamaIntegration:
    """
    创建 Ollama 客户端的便捷函数
    
    Args:
        base_url: Ollama 服务地址
        **kwargs: 其他初始化参数
        
    Returns:
        OllamaIntegration: 配置好的客户端实例
    """
    return OllamaIntegration(base_url=base_url, **kwargs)


if __name__ == "__main__":
    # 示例用法
    import sys
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建客户端
    with create_ollama_client() as client:
        print("🔍 检查 Ollama 服务状态...")
        if client.check_ollama_status():
            print("✅ Ollama 服务正常")
            
            print("\n📋 获取模型列表...")
            try:
                models = client.list_models()
                print(f"✅ 发现 {len(models)} 个模型: {', '.join(models)}")
                
                if models:
                    print(f"\n🧪 测试推理 ({models[0]})...")
                    result = client.inference_with_metrics(
                        models[0], 
                        "你好，请简单介绍一下你自己。"
                    )
                    
                    if result['status'] == 'success':
                        print(f"✅ 推理成功!")
                        print(f"   延迟: {result['latency_ms']:.2f}ms")
                        print(f"   TPS: {result.get('tokens_per_second', 0):.2f}")
                        print(f"   响应: {result['response'][:100]}...")
                    else:
                        print(f"❌ 推理失败: {result.get('error', '未知错误')}")
                
                print(f"\n📊 健康检查...")
                health = client.health_check()
                print(f"状态: {health.status}")
                print(f"延迟: {health.latency_ms:.2f}ms")
                print(f"模型数量: {health.models_count}")
                
                print(f"\n📈 性能统计...")
                stats = client.get_stats()
                print(f"总请求数: {stats['total_requests']}")
                print(f"成功率: {stats['success_rate']:.2%}")
                print(f"平均延迟: {stats['average_latency_ms']:.2f}ms")
                
            except Exception as e:
                print(f"❌ 操作失败: {e}")
                sys.exit(1)
        else:
            print("❌ Ollama 服务未运行，请先启动 Ollama:")
            print("   ollama serve")
            sys.exit(1)
