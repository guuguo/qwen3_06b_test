#!/usr/bin/env python3
"""
Qwen-3 简化性能监控模块

提供轻量级的性能监控功能，包括：
- 文件日志监控和管理
- 系统指标收集（CPU、内存、磁盘）
- 日度摘要报告生成
- 实时性能指标收集
- 指标数据持久化存储

作者: Qwen-3 部署团队
版本: 1.0.0
"""

import os
import json
import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
from collections import deque, defaultdict
import statistics


@dataclass
class SystemMetrics:
    """系统指标数据类"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_available_gb: float
    disk_usage_percent: float
    disk_used_gb: float
    disk_free_gb: float
    load_average: Optional[Tuple[float, float, float]] = None
    network_io: Optional[Dict[str, int]] = None


@dataclass
class RequestMetrics:
    """请求指标数据类"""
    timestamp: str
    model: str
    prompt_length: int
    response_length: int
    latency_ms: float
    status: str
    error: Optional[str] = None
    tokens_per_second: Optional[float] = None
    memory_usage_mb: Optional[float] = None


@dataclass
class DailySummary:
    """日度摘要数据类"""
    date: str
    total_requests: int
    successful_requests: int
    error_requests: int
    avg_latency_ms: float
    max_latency_ms: float
    min_latency_ms: float
    p95_latency_ms: float
    avg_cpu_percent: float
    max_memory_percent: float
    avg_memory_gb: float
    total_tokens: int
    avg_tokens_per_second: float


class SimpleFileMonitor:
    """
    简单文件日志监控器
    
    提供基于文件的日志记录和监控功能，适用于本地开发环境。
    """
    
    def __init__(self, log_dir: str = "./logs", max_log_files: int = 30):
        """
        初始化文件监控器
        
        Args:
            log_dir: 日志目录路径
            max_log_files: 最大保留日志文件数
        """
        self.log_dir = Path(log_dir)
        self.max_log_files = max_log_files
        
        # 创建日志目录
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 内存缓存
        self._request_cache = deque(maxlen=1000)  # 最近1000条请求
        self._system_cache = deque(maxlen=288)    # 最近24小时系统指标（5分钟间隔）
        
        self.logger.info(f"文件监控器初始化完成: {self.log_dir}")
    
    def log_request(self, 
                   model: str, 
                   prompt: str, 
                   response: str, 
                   latency_ms: float, 
                   error: str = None,
                   tokens_per_second: float = None) -> None:
        """
        记录请求日志
        
        Args:
            model: 模型名称
            prompt: 输入提示
            response: 模型响应
            latency_ms: 延迟（毫秒）
            error: 错误信息
            tokens_per_second: 每秒处理的token数
        """
        timestamp = datetime.now().isoformat()
        
        # 创建请求指标
        metrics = RequestMetrics(
            timestamp=timestamp,
            model=model,
            prompt_length=len(prompt),
            response_length=len(response) if response else 0,
            latency_ms=latency_ms,
            status="error" if error else "success",
            error=error,
            tokens_per_second=tokens_per_second
        )
        
        # 添加到内存缓存
        self._request_cache.append(metrics)
        
        # 写入日志文件
        log_file = self.log_dir / f"requests_{datetime.now().strftime('%Y%m%d')}.jsonl"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(metrics), ensure_ascii=False) + "\n")
        except Exception as e:
            self.logger.error(f"写入请求日志失败: {e}")
    
    def log_system_metrics(self) -> SystemMetrics:
        """
        记录系统指标
        
        Returns:
            SystemMetrics: 当前系统指标
        """
        try:
            # 收集系统指标
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # 获取负载平均值（仅Linux/macOS）
            load_avg = None
            try:
                if hasattr(os, 'getloadavg'):
                    load_avg = os.getloadavg()
            except (OSError, AttributeError):
                pass
            
            # 获取网络IO（可选）
            network_io = None
            try:
                net_io = psutil.net_io_counters()
                if net_io:
                    network_io = {
                        'bytes_sent': net_io.bytes_sent,
                        'bytes_recv': net_io.bytes_recv,
                        'packets_sent': net_io.packets_sent,
                        'packets_recv': net_io.packets_recv
                    }
            except Exception:
                pass
            
            # 创建系统指标
            metrics = SystemMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_gb=memory.used / (1024**3),
                memory_available_gb=memory.available / (1024**3),
                disk_usage_percent=disk.percent,
                disk_used_gb=disk.used / (1024**3),
                disk_free_gb=disk.free / (1024**3),
                load_average=load_avg,
                network_io=network_io
            )
            
            # 添加到内存缓存
            self._system_cache.append(metrics)
            
            # 写入日志文件
            log_file = self.log_dir / f"system_{datetime.now().strftime('%Y%m%d')}.jsonl"
            try:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(asdict(metrics), ensure_ascii=False) + "\n")
            except Exception as e:
                self.logger.error(f"写入系统日志失败: {e}")
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"收集系统指标失败: {e}")
            # 返回默认值
            return SystemMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_gb=0.0,
                memory_available_gb=0.0,
                disk_usage_percent=0.0,
                disk_used_gb=0.0,
                disk_free_gb=0.0
            )
    
    def get_recent_requests(self, limit: int = 100) -> List[RequestMetrics]:
        """
        获取最近的请求记录
        
        Args:
            limit: 返回记录数限制
            
        Returns:
            List[RequestMetrics]: 最近的请求记录
        """
        return list(self._request_cache)[-limit:]
    
    def get_recent_system_metrics(self, limit: int = 50) -> List[SystemMetrics]:
        """
        获取最近的系统指标
        
        Args:
            limit: 返回记录数限制
            
        Returns:
            List[SystemMetrics]: 最近的系统指标
        """
        return list(self._system_cache)[-limit:]
    
    def generate_daily_summary(self, date: str = None) -> DailySummary:
        """
        生成日度摘要报告
        
        Args:
            date: 日期字符串 (YYYYMMDD)，None表示今天
            
        Returns:
            DailySummary: 日度摘要
        """
        if not date:
            date = datetime.now().strftime('%Y%m%d')
        
        # 读取请求日志
        request_file = self.log_dir / f"requests_{date}.jsonl"
        system_file = self.log_dir / f"system_{date}.jsonl"
        
        # 初始化摘要
        summary = DailySummary(
            date=date,
            total_requests=0,
            successful_requests=0,
            error_requests=0,
            avg_latency_ms=0.0,
            max_latency_ms=0.0,
            min_latency_ms=0.0,
            p95_latency_ms=0.0,
            avg_cpu_percent=0.0,
            max_memory_percent=0.0,
            avg_memory_gb=0.0,
            total_tokens=0,
            avg_tokens_per_second=0.0
        )
        
        # 分析请求日志
        if request_file.exists():
            latencies = []
            tokens_per_second_list = []
            
            try:
                with open(request_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            summary.total_requests += 1
                            
                            if entry.get("status") == "success":
                                summary.successful_requests += 1
                                latencies.append(entry["latency_ms"])
                                
                                # 统计token数
                                response_length = entry.get("response_length", 0)
                                summary.total_tokens += response_length
                                
                                # 统计TPS
                                tps = entry.get("tokens_per_second")
                                if tps:
                                    tokens_per_second_list.append(tps)
                            else:
                                summary.error_requests += 1
                                
                        except (json.JSONDecodeError, KeyError) as e:
                            self.logger.warning(f"解析请求日志行失败: {e}")
                            continue
                            
            except Exception as e:
                self.logger.error(f"读取请求日志失败: {e}")
            
            # 计算延迟统计
            if latencies:
                summary.avg_latency_ms = statistics.mean(latencies)
                summary.max_latency_ms = max(latencies)
                summary.min_latency_ms = min(latencies)
                summary.p95_latency_ms = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
            
            # 计算TPS统计
            if tokens_per_second_list:
                summary.avg_tokens_per_second = statistics.mean(tokens_per_second_list)
        
        # 分析系统日志
        if system_file.exists():
            cpu_values = []
            memory_values = []
            memory_gb_values = []
            
            try:
                with open(system_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            cpu_values.append(entry["cpu_percent"])
                            memory_values.append(entry["memory_percent"])
                            memory_gb_values.append(entry["memory_used_gb"])
                        except (json.JSONDecodeError, KeyError) as e:
                            self.logger.warning(f"解析系统日志行失败: {e}")
                            continue
                            
            except Exception as e:
                self.logger.error(f"读取系统日志失败: {e}")
            
            # 计算系统指标统计
            if cpu_values:
                summary.avg_cpu_percent = statistics.mean(cpu_values)
            if memory_values:
                summary.max_memory_percent = max(memory_values)
            if memory_gb_values:
                summary.avg_memory_gb = statistics.mean(memory_gb_values)
        
        return summary
    
    def cleanup_old_logs(self) -> int:
        """
        清理旧日志文件
        
        Returns:
            int: 删除的文件数量
        """
        deleted_count = 0
        
        try:
            # 获取所有日志文件
            log_files = []
            for pattern in ["requests_*.jsonl", "system_*.jsonl"]:
                log_files.extend(self.log_dir.glob(pattern))
            
            # 按修改时间排序
            log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # 删除超过限制的文件
            if len(log_files) > self.max_log_files:
                for log_file in log_files[self.max_log_files:]:
                    try:
                        log_file.unlink()
                        deleted_count += 1
                        self.logger.info(f"删除旧日志文件: {log_file.name}")
                    except Exception as e:
                        self.logger.error(f"删除日志文件失败 {log_file}: {e}")
                        
        except Exception as e:
            self.logger.error(f"清理日志文件失败: {e}")
        
        return deleted_count
    
    def get_log_files_info(self) -> Dict[str, Any]:
        """
        获取日志文件信息
        
        Returns:
            Dict[str, Any]: 日志文件统计信息
        """
        info = {
            'total_files': 0,
            'total_size_mb': 0.0,
            'oldest_file': None,
            'newest_file': None,
            'files_by_type': defaultdict(int)
        }
        
        try:
            log_files = list(self.log_dir.glob("*.jsonl"))
            info['total_files'] = len(log_files)
            
            if log_files:
                # 计算总大小
                total_size = sum(f.stat().st_size for f in log_files)
                info['total_size_mb'] = total_size / (1024 * 1024)
                
                # 找到最新和最旧的文件
                log_files.sort(key=lambda x: x.stat().st_mtime)
                info['oldest_file'] = log_files[0].name
                info['newest_file'] = log_files[-1].name
                
                # 按类型统计
                for log_file in log_files:
                    if log_file.name.startswith('requests_'):
                        info['files_by_type']['requests'] += 1
                    elif log_file.name.startswith('system_'):
                        info['files_by_type']['system'] += 1
                    else:
                        info['files_by_type']['other'] += 1
                        
        except Exception as e:
            self.logger.error(f"获取日志文件信息失败: {e}")
        
        return dict(info)


class SimplePerformanceMonitor:
    """
    简单性能监控器
    
    提供实时性能指标收集和分析功能。
    """
    
    def __init__(self, 
                 file_monitor: SimpleFileMonitor,
                 collection_interval: int = 60):
        """
        初始化性能监控器
        
        Args:
            file_monitor: 文件监控器实例
            collection_interval: 指标收集间隔（秒）
        """
        self.file_monitor = file_monitor
        self.collection_interval = collection_interval
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 监控状态
        self._monitoring = False
        self._monitor_thread = None
        
        # 实时指标缓存
        self._current_metrics = {}
        self._metrics_lock = threading.Lock()
        
        self.logger.info("性能监控器初始化完成")
    
    def start_monitoring(self) -> None:
        """开始监控"""
        if self._monitoring:
            self.logger.warning("监控已在运行中")
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="PerformanceMonitor"
        )
        self._monitor_thread.start()
        
        self.logger.info(f"性能监控已启动，收集间隔: {self.collection_interval}秒")
    
    def stop_monitoring(self) -> None:
        """停止监控"""
        if not self._monitoring:
            return
        
        self._monitoring = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        
        self.logger.info("性能监控已停止")
    
    def _monitoring_loop(self) -> None:
        """监控循环"""
        while self._monitoring:
            try:
                # 收集系统指标
                metrics = self.file_monitor.log_system_metrics()
                
                # 更新当前指标
                with self._metrics_lock:
                    self._current_metrics = asdict(metrics)
                
                # 等待下次收集
                time.sleep(self.collection_interval)
                
            except Exception as e:
                self.logger.error(f"监控循环异常: {e}")
                time.sleep(5)  # 出错时短暂等待
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """
        获取当前指标
        
        Returns:
            Dict[str, Any]: 当前系统指标
        """
        with self._metrics_lock:
            return self._current_metrics.copy()
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取性能摘要
        
        Args:
            hours: 统计时间范围（小时）
            
        Returns:
            Dict[str, Any]: 性能摘要
        """
        # 获取最近的系统指标
        recent_metrics = self.file_monitor.get_recent_system_metrics(
            limit=hours * 12  # 假设5分钟间隔
        )
        
        # 获取最近的请求记录
        recent_requests = self.file_monitor.get_recent_requests(limit=1000)
        
        summary = {
            'time_range_hours': hours,
            'system_metrics': {
                'avg_cpu_percent': 0.0,
                'max_cpu_percent': 0.0,
                'avg_memory_percent': 0.0,
                'max_memory_percent': 0.0,
                'avg_memory_gb': 0.0,
                'disk_usage_percent': 0.0
            },
            'request_metrics': {
                'total_requests': len(recent_requests),
                'successful_requests': 0,
                'error_requests': 0,
                'avg_latency_ms': 0.0,
                'max_latency_ms': 0.0,
                'requests_per_hour': 0.0
            }
        }
        
        # 分析系统指标
        if recent_metrics:
            cpu_values = [m.cpu_percent for m in recent_metrics]
            memory_values = [m.memory_percent for m in recent_metrics]
            memory_gb_values = [m.memory_used_gb for m in recent_metrics]
            
            summary['system_metrics'].update({
                'avg_cpu_percent': statistics.mean(cpu_values),
                'max_cpu_percent': max(cpu_values),
                'avg_memory_percent': statistics.mean(memory_values),
                'max_memory_percent': max(memory_values),
                'avg_memory_gb': statistics.mean(memory_gb_values),
                'disk_usage_percent': recent_metrics[-1].disk_usage_percent
            })
        
        # 分析请求指标
        if recent_requests:
            successful = [r for r in recent_requests if r.status == "success"]
            error = [r for r in recent_requests if r.status != "success"]
            
            summary['request_metrics'].update({
                'successful_requests': len(successful),
                'error_requests': len(error),
                'requests_per_hour': len(recent_requests) / hours
            })
            
            if successful:
                latencies = [r.latency_ms for r in successful]
                summary['request_metrics'].update({
                    'avg_latency_ms': statistics.mean(latencies),
                    'max_latency_ms': max(latencies)
                })
        
        return summary
    
    def is_monitoring(self) -> bool:
        """检查是否正在监控"""
        return self._monitoring
    
    def __enter__(self):
        """上下文管理器入口"""
        self.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop_monitoring()


# 便捷函数
def create_simple_monitor(log_dir: str = "./logs", 
                         collection_interval: int = 60) -> Tuple[SimpleFileMonitor, SimplePerformanceMonitor]:
    """
    创建简单监控器的便捷函数
    
    Args:
        log_dir: 日志目录
        collection_interval: 收集间隔（秒）
        
    Returns:
        Tuple[SimpleFileMonitor, SimplePerformanceMonitor]: 文件监控器和性能监控器
    """
    file_monitor = SimpleFileMonitor(log_dir)
    perf_monitor = SimplePerformanceMonitor(file_monitor, collection_interval)
    
    return file_monitor, perf_monitor


if __name__ == "__main__":
    # 示例用法
    import sys
    import signal
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 启动简单监控器测试...")
    
    # 创建监控器
    file_monitor, perf_monitor = create_simple_monitor()
    
    def signal_handler(signum, frame):
        print("\n🛑 收到停止信号，正在关闭监控器...")
        perf_monitor.stop_monitoring()
        sys.exit(0)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 启动性能监控
        perf_monitor.start_monitoring()
        
        # 模拟一些请求日志
        print("📝 记录测试请求...")
        file_monitor.log_request(
            model="qwen3:0.6b",
            prompt="测试提示",
            response="测试响应内容",
            latency_ms=1234.5,
            tokens_per_second=15.2
        )
        
        # 等待一些指标收集
        print("⏳ 等待指标收集...")
        time.sleep(5)
        
        # 显示当前指标
        current = perf_monitor.get_current_metrics()
        if current:
            print(f"📊 当前系统指标:")
            print(f"   CPU: {current.get('cpu_percent', 0):.1f}%")
            print(f"   内存: {current.get('memory_percent', 0):.1f}%")
            print(f"   磁盘: {current.get('disk_usage_percent', 0):.1f}%")
        
        # 生成摘要报告
        print("📋 生成日度摘要...")
        summary = file_monitor.generate_daily_summary()
        print(f"   总请求数: {summary.total_requests}")
        print(f"   成功请求: {summary.successful_requests}")
        print(f"   平均延迟: {summary.avg_latency_ms:.2f}ms")
        
        # 获取日志文件信息
        log_info = file_monitor.get_log_files_info()
        print(f"📁 日志文件信息:")
        print(f"   文件数量: {log_info['total_files']}")
        print(f"   总大小: {log_info['total_size_mb']:.2f}MB")
        
        print("✅ 监控器测试完成！按 Ctrl+C 停止监控...")
        
        # 保持运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 用户中断，正在停止...")
    except Exception as e:
        print(f"❌ 测试异常: {e}")
    finally:
        perf_monitor.stop_monitoring()
        print("👋 监控器已停止")
