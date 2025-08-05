#!/usr/bin/env python3
"""
Qwen-3 本地Web监控界面

提供简洁的Web界面用于本地开发环境监控，包括：
- 实时系统指标展示
- 请求日志和性能统计
- Ollama服务状态监控
- 配置管理界面
- 简单的测试工具

作者: Qwen-3 部署团队
版本: 1.0.0
"""

import os
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask import send_from_directory, abort
import plotly.graph_objs as go
import plotly.utils

from ollama_integration import OllamaIntegration, create_ollama_client
from simple_monitor import SimpleFileMonitor, SimplePerformanceMonitor, create_simple_monitor
from config_manager import get_config_manager, get_config
from test_dataset_manager import TestDatasetManager
from local_tester import SimpleLocalTester
from qps_evaluator import QPSEvaluator, create_qps_evaluator


class LocalDashboard:
    """
    本地Web监控界面
    
    提供简洁的Web界面用于监控本地Qwen-3部署状态。
    """
    
    def __init__(self, 
                 host: str = "127.0.0.1",
                 port: int = 8080,
                 debug: bool = True):
        """
        初始化本地监控界面
        
        Args:
            host: 监听地址
            port: 监听端口
            debug: 调试模式
        """
        self.host = host
        self.port = port
        self.debug = debug
        
        # 配置参数
        self.max_response_length = 0  # 模型响应显示的最大长度（0=无限制，>0=限制字符数）
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 创建Flask应用
        self.app = Flask(__name__, 
                        template_folder='../templates',
                        static_folder='../static')
        self.app.secret_key = get_config('web_dashboard.session.secret_key', 'qwen3-local-dev-key')
        
        # 初始化组件
        self.config_manager = get_config_manager()
        self.ollama_client = None
        self.file_monitor = None
        self.perf_monitor = None
        self.dataset_manager = None
        
        # 进度跟踪
        self.test_progress = {
            'current': 0,
            'total': 0,
            'current_sample_id': '',
            'status': 'idle',  # idle, running, completed, error
            'start_time': None,
            'dataset_name': '',
            'model_name': ''
        }
        self.local_tester = None
        
        # 运行状态
        self._running = False
        self._server_thread = None
        
        # 初始化组件
        self._init_components()
        
        # 注册路由
        self._register_routes()
        
        self.logger.info(f"本地监控界面初始化完成: {host}:{port}")
    
    def _init_components(self) -> None:
        """初始化组件"""
        try:
            # 创建Ollama客户端
            self.ollama_client = create_ollama_client()
            
            # 创建监控器
            self.file_monitor, self.perf_monitor = create_simple_monitor(
                log_dir=get_config('monitoring.file_monitor.log_dir', './logs'),
                collection_interval=get_config('monitoring.performance_monitor.collection_interval', 60)
            )
            
            # 启动性能监控
            if get_config('monitoring.performance_monitor.auto_start', True):
                self.perf_monitor.start_monitoring()
            
            # 创建测试集管理器
            self.dataset_manager = TestDatasetManager()
            
            # 创建本地测试器
            self.local_tester = SimpleLocalTester(self.ollama_client)
            
            # 创建QPS评估器
            self.qps_evaluator = create_qps_evaluator(self.ollama_client)
            
            self.logger.info("组件初始化完成")
            
        except Exception as e:
            self.logger.error(f"组件初始化失败: {e}")
            raise
    
    def _truncate_response(self, response: str) -> str:
        """
        截断模型响应以控制显示长度
        
        Args:
            response: 原始响应内容
            
        Returns:
            截断后的响应内容
        """
        # 如果设置为0或负数，则不限制长度
        if self.max_response_length <= 0:
            return response
            
        if len(response) <= self.max_response_length:
            return response
        
        return response[:self.max_response_length] + '...'
    
    def _separate_thinking_and_answer(self, response: str) -> tuple:
        """
        分离模型响应中的思考过程和最终回答
        
        Args:
            response: 完整的模型响应
            
        Returns:
            tuple: (思考过程, 最终回答)
        """
        if not response:
            return None, response
        
        # 尝试识别思考过程的分界点
        separators = [
            '\n评分：',
            '\n类别：', 
            '\n严重度：',
            '评分：',
            '类别：',
            '严重度：'
        ]
        
        for separator in separators:
            if separator in response:
                parts = response.split(separator, 1)
                if len(parts) == 2:
                    thinking_part = parts[0].strip()
                    answer_part = (separator.strip() + parts[1]).strip()
                    
                    # 如果思考部分太短（少于50字符），可能不是真正的思考过程
                    if len(thinking_part) < 50:
                        return None, response
                    
                    return thinking_part, answer_part
        
        # 如果没有找到明确的分界点，返回空思考过程
        return None, response
    
    def _register_routes(self) -> None:
        """注册路由"""
        
        @self.app.route('/')
        def index():
            """主页"""
            return render_template('dashboard.html', 
                                 title="Qwen-3 本地监控",
                                 refresh_interval=get_config('web_dashboard.refresh_interval', 5))
        
        @self.app.route('/api/status')
        def api_status():
            """系统状态API"""
            try:
                # 检查Ollama状态
                ollama_status = self.ollama_client.check_ollama_status()
                
                # 获取当前系统指标
                current_metrics = self.perf_monitor.get_current_metrics()
                
                # 获取模型列表
                models = []
                if ollama_status:
                    try:
                        models = self.ollama_client.list_models()
                    except Exception as e:
                        self.logger.warning(f"获取模型列表失败: {e}")
                
                return jsonify({
                    'timestamp': datetime.now().isoformat(),
                    'ollama': {
                        'status': 'online' if ollama_status else 'offline',
                        'url': get_config('ollama.base_url'),
                        'models': models
                    },
                    'system': current_metrics,
                    'monitoring': {
                        'performance_monitor_running': self.perf_monitor.is_monitoring(),
                        'log_dir': get_config('monitoring.file_monitor.log_dir')
                    }
                })
                
            except Exception as e:
                self.logger.error(f"获取系统状态失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/metrics')
        def api_metrics():
            """指标数据API"""
            try:
                hours = request.args.get('hours', 1, type=int)
                
                # 获取性能摘要
                summary = self.perf_monitor.get_performance_summary(hours=hours)
                
                # 获取最近的系统指标
                recent_system = self.file_monitor.get_recent_system_metrics(limit=hours*12)
                
                # 获取最近的请求记录
                recent_requests = self.file_monitor.get_recent_requests(limit=100)
                
                # 准备图表数据
                chart_data = self._prepare_chart_data(recent_system, recent_requests)
                
                return jsonify({
                    'summary': summary,
                    'charts': chart_data,
                    'recent_requests': [
                        {
                            'timestamp': r.timestamp,
                            'model': r.model,
                            'latency_ms': r.latency_ms,
                            'status': r.status,
                            'prompt_length': r.prompt_length,
                            'response_length': r.response_length
                        }
                        for r in recent_requests[-20:]  # 最近20条
                    ]
                })
                
            except Exception as e:
                self.logger.error(f"获取指标数据失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/test', methods=['POST'])
        def api_test():
            """测试推理API"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'error': '缺少请求数据'}), 400
                
                model = data.get('model', 'qwen3:0.6b')
                prompt = data.get('prompt', '你好')
                
                if not prompt.strip():
                    return jsonify({'error': '提示不能为空'}), 400
                
                # 执行推理
                start_time = time.time()
                result = self.ollama_client.inference_with_metrics(model, prompt)
                end_time = time.time()
                
                # 处理返回结果（可能是字典或 InferenceMetrics 对象）
                if isinstance(result, dict):
                    # 成功情况：返回字典
                    response_text = result.get('response', '')
                    latency_ms = result.get('latency_ms', 0)
                    error_msg = result.get('error')
                    tokens_per_second = result.get('tokens_per_second', 0)
                    status = result.get('status', 'unknown')
                    success = status == 'success'
                else:
                    # 错误情况：返回 InferenceMetrics 对象
                    response_text = ''
                    latency_ms = result.latency_ms
                    error_msg = result.error
                    tokens_per_second = result.tokens_per_second or 0
                    status = result.status
                    success = status == 'success'
                
                # 记录到监控日志
                self.file_monitor.log_request(
                    model=model,
                    prompt=prompt,
                    response=response_text,
                    latency_ms=latency_ms,
                    error=error_msg,
                    tokens_per_second=tokens_per_second
                )
                
                return jsonify({
                    'success': success,
                    'response': response_text,
                    'error': error_msg,
                    'metrics': {
                        'latency_ms': latency_ms,
                        'tokens_per_second': tokens_per_second,
                        'prompt_tokens': len(prompt.split()) if prompt else 0,
                        'response_tokens': len(response_text.split()) if response_text else 0,
                        'total_duration_ms': latency_ms
                    }
                })
                
            except Exception as e:
                self.logger.error(f"测试推理失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/logs')
        def api_logs():
            """日志查看API"""
            try:
                log_type = request.args.get('type', 'requests')  # requests, system
                date = request.args.get('date', datetime.now().strftime('%Y%m%d'))
                limit = request.args.get('limit', 100, type=int)
                
                log_dir = Path(get_config('monitoring.file_monitor.log_dir', './logs'))
                log_file = log_dir / f"{log_type}_{date}.jsonl"
                
                logs = []
                if log_file.exists():
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            # 取最后N行
                            for line in lines[-limit:]:
                                try:
                                    log_entry = json.loads(line.strip())
                                    logs.append(log_entry)
                                except json.JSONDecodeError:
                                    continue
                    except Exception as e:
                        self.logger.error(f"读取日志文件失败: {e}")
                
                return jsonify({
                    'logs': logs,
                    'total': len(logs),
                    'log_file': str(log_file),
                    'exists': log_file.exists()
                })
                
            except Exception as e:
                self.logger.error(f"获取日志失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/config')
        def api_config():
            """配置查看API"""
            try:
                section = request.args.get('section')
                
                if section:
                    config_data = self.config_manager.get_section(section)
                else:
                    config_data = self.config_manager.get_all()
                
                # 隐藏敏感信息
                config_data = self._sanitize_config(config_data)
                
                return jsonify({
                    'config': config_data,
                    'info': self.config_manager.get_config_info()
                })
                
            except Exception as e:
                self.logger.error(f"获取配置失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/daily_summary')
        def api_daily_summary():
            """日度摘要API"""
            try:
                date = request.args.get('date')  # YYYYMMDD格式
                
                summary = self.file_monitor.generate_daily_summary(date)
                
                return jsonify({
                    'summary': {
                        'date': summary.date,
                        'total_requests': summary.total_requests,
                        'successful_requests': summary.successful_requests,
                        'error_requests': summary.error_requests,
                        'success_rate': summary.successful_requests / max(summary.total_requests, 1),
                        'avg_latency_ms': summary.avg_latency_ms,
                        'max_latency_ms': summary.max_latency_ms,
                        'min_latency_ms': summary.min_latency_ms,
                        'p95_latency_ms': summary.p95_latency_ms,
                        'avg_cpu_percent': summary.avg_cpu_percent,
                        'max_memory_percent': summary.max_memory_percent,
                        'avg_memory_gb': summary.avg_memory_gb,
                        'total_tokens': summary.total_tokens,
                        'avg_tokens_per_second': summary.avg_tokens_per_second
                    }
                })
                
            except Exception as e:
                self.logger.error(f"获取日度摘要失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/health')
        def health_check():
            """健康检查"""
            try:
                health_status = {
                    'status': 'healthy',
                    'timestamp': datetime.now().isoformat(),
                    'components': {
                        'ollama': self.ollama_client.check_ollama_status(),
                        'performance_monitor': self.perf_monitor.is_monitoring(),
                        'config_manager': True
                    }
                }
                
                # 检查整体健康状态
                all_healthy = all(health_status['components'].values())
                health_status['status'] = 'healthy' if all_healthy else 'degraded'
                
                status_code = 200 if all_healthy else 503
                return jsonify(health_status), status_code
                
            except Exception as e:
                self.logger.error(f"健康检查失败: {e}")
                return jsonify({
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        # 测试集管理路由
        @self.app.route('/api/datasets')
        def api_datasets():
            """获取可用测试集列表"""
            try:
                datasets = self.dataset_manager.list_available_datasets()
                dataset_info = []
                
                for dataset_name in datasets:
                    info = self.dataset_manager.get_dataset_info(dataset_name)
                    if info:
                        dataset_info.append({
                            'name': dataset_name,
                            'display_name': info.get('name', dataset_name),
                            'description': info.get('description', ''),
                            'total_samples': info.get('total_samples', 0),
                            'categories': info.get('categories', []),
                            'version': info.get('version', '1.0.0')
                        })
                
                return jsonify({
                    'datasets': dataset_info,
                    'total_count': len(dataset_info)
                })
                
            except Exception as e:
                self.logger.error(f"获取测试集列表失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/datasets/<dataset_name>/samples')
        def api_dataset_samples(dataset_name):
            """获取测试集样本预览"""
            try:
                sample_count = request.args.get('count', 5, type=int)
                samples = self.dataset_manager.get_test_samples(
                    dataset_name, 
                    sample_count=sample_count,
                    random_seed=42  # 固定种子以获得一致的预览
                )
                
                sample_data = []
                for sample in samples:
                    sample_data.append({
                        'id': sample.id,
                        'content': sample.content,
                        'category': sample.category,
                        'expected_score': sample.expected_score,
                        'keywords': sample.keywords
                    })
                
                return jsonify({
                    'samples': sample_data,
                    'total_samples': len(samples)
                })
                
            except Exception as e:
                self.logger.error(f"获取测试集样本失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/datasets/<dataset_name>/prompt')
        def api_dataset_prompt(dataset_name):
            """获取数据集关联的提示词文件内容"""
            try:
                # 获取数据集信息
                dataset_info = self.dataset_manager.get_dataset_info(dataset_name)
                if not dataset_info or 'prompt_template_file' not in dataset_info:
                    return jsonify({'error': '该数据集未配置提示词文件'}), 404

                template_filename = dataset_info['prompt_template_file']
                
                # 从md_manager读取文件内容
                md_manager = get_md_prompt_manager()
                md_file_path = md_manager.prompts_dir / template_filename

                if not md_file_path.exists():
                    return jsonify({'error': f'提示词文件不存在: {template_filename}'}), 404

                with open(md_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                return jsonify({
                    'file_name': template_filename,
                    'content': content
                })

            except Exception as e:
                self.logger.error(f"获取数据集提示词失败: {e}")
                return jsonify({'error': str(e)}), 500

        # Ollama模型管理API
        @self.app.route('/api/ollama/models', methods=['GET'])
        def api_ollama_models():
            """获取已安装的Ollama模型列表"""
            try:
                # 直接调用Ollama API获取详细信息
                import requests
                response = requests.get(f"{self.ollama_client.base_url}/api/tags", timeout=10)
                
                if response.status_code != 200:
                    raise Exception(f"Ollama API调用失败: HTTP {response.status_code}")
                
                data = response.json()
                models_data = []
                
                for model in data.get('models', []):
                    # 格式化模型大小
                    size_bytes = model.get('size', 0)
                    if size_bytes > 1024 * 1024 * 1024:
                        size_str = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
                    elif size_bytes > 1024 * 1024:
                        size_str = f"{size_bytes / (1024 * 1024):.0f} MB" 
                    else:
                        size_str = f"{size_bytes} B"
                    
                    # 格式化修改时间
                    modified_at = model.get('modified_at', '')
                    if modified_at:
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(modified_at.replace('Z', '+00:00'))
                            modified_str = dt.strftime('%Y-%m-%d %H:%M')
                        except:
                            modified_str = modified_at
                    else:
                        modified_str = 'Unknown'
                    
                    models_data.append({
                        'name': model.get('name', ''),
                        'digest': model.get('digest', ''),
                        'size': size_bytes,
                        'size_str': size_str,
                        'modified_at': modified_str
                    })
                
                return jsonify({'models': models_data})
                
            except Exception as e:
                self.logger.error(f"获取模型列表失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/ollama/models/pull', methods=['POST'])
        def api_ollama_pull_model():
            """拉取新模型"""
            try:
                data = request.get_json()
                model_name = data.get('model_name', '').strip()
                use_mirror = data.get('use_mirror', False)
                
                if not model_name:
                    return jsonify({'error': '模型名称不能为空'}), 400
                
                # 如果使用镜像源，修改模型名称
                if use_mirror and not model_name.startswith('hf-mirror.com/'):
                    # 处理不同格式的模型名称
                    if '/' in model_name and not model_name.startswith('hf-mirror.com/'):
                        # 已经包含仓库路径的模型
                        model_name = f"hf-mirror.com/{model_name}"
                    elif ':' in model_name:
                        # 标准ollama格式的模型，转换为HF格式
                        base_name = model_name.split(':')[0]
                        tag = model_name.split(':')[1]
                        model_name = f"hf-mirror.com/{base_name}:{tag}"
                
                self.logger.info(f"开始拉取模型: {model_name}")
                
                # 在后台线程中执行拉取操作
                def pull_model_task():
                    try:
                        # 使用OllamaIntegration的pull_model方法
                        success = self.ollama_client.pull_model(model_name, timeout=600)
                        if success:
                            self.logger.info(f"模型拉取完成: {model_name}")
                        else:
                            self.logger.error(f"模型拉取失败: {model_name}")
                    except Exception as e:
                        self.logger.error(f"模型拉取失败: {e}")
                
                # 启动后台任务
                import threading
                pull_thread = threading.Thread(target=pull_model_task, daemon=True)
                pull_thread.start()
                
                return jsonify({
                    'message': f'开始拉取模型 {model_name}，请稍候刷新模型列表查看结果',
                    'model_name': model_name
                })
                
            except Exception as e:
                self.logger.error(f"拉取模型失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/ollama/models/<path:model_name>', methods=['DELETE'])
        def api_ollama_delete_model(model_name):
            """删除指定模型"""
            try:
                self.logger.info(f"开始删除模型: {model_name}")
                success = self.ollama_client.delete_model(model_name)
                
                if success:
                    self.logger.info(f"模型删除完成: {model_name}")
                    return jsonify({
                        'message': f'模型 {model_name} 删除成功'
                    })
                else:
                    raise Exception("删除操作失败")
                
            except Exception as e:
                self.logger.error(f"删除模型失败: {e}")
                return jsonify({'error': str(e)}), 500

        # 静态文件路由
        @self.app.route('/static/<path:filename>')
        def static_files(filename):
            """静态文件服务"""
            static_dir = Path(__file__).parent.parent / 'static'
            if not static_dir.exists():
                static_dir.mkdir(parents=True, exist_ok=True)
            return send_from_directory(str(static_dir), filename)
        
        # 测试相关路由
        @self.app.route('/api/test/progress', methods=['GET'])
        def api_test_progress():
            """获取测试进度"""
            self.logger.info("获取测试进度API被调用")
            progress = self.test_progress.copy()
            
            # 添加计算字段
            if progress['total'] > 0:
                progress['percentage'] = (progress['current'] / progress['total']) * 100
            else:
                progress['percentage'] = 0
            
            # 计算预估剩余时间
            if progress['start_time'] and progress['current'] > 0 and progress['status'] == 'running':
                elapsed = time.time() - progress['start_time']
                avg_time_per_sample = elapsed / progress['current']
                remaining_samples = progress['total'] - progress['current']
                estimated_remaining = avg_time_per_sample * remaining_samples
                progress['estimated_remaining_seconds'] = int(estimated_remaining)
            else:
                progress['estimated_remaining_seconds'] = None
            
            self.logger.info(f"返回测试进度: {progress}")
            return jsonify(progress)
        
        @self.app.route('/api/test/dataset', methods=['POST'])
        def api_test_dataset():
            """运行测试集评估"""
            self.logger.info("测试集评估API被调用")
            try:
                data = request.get_json()
                if not data:
                    self.logger.error("缺少请求数据")
                    return jsonify({'error': '缺少请求数据'}), 400
                
                model_name = data.get('model', 'qwen3:0.6b')
                dataset_name = data.get('dataset')
                sample_count = data.get('sample_count', 10)
                enable_thinking = data.get('enable_thinking', True)  # 默认启用思考
                
                self.logger.info(f"开始测试集评估: model={model_name}, dataset={dataset_name}, samples={sample_count}, thinking={enable_thinking}")
                
                if not dataset_name:
                    self.logger.error("缺少测试集名称")
                    return jsonify({'error': '缺少测试集名称'}), 400
                
                # 检查是否已有测试在运行
                if self.test_progress['status'] == 'running':
                    self.logger.warning("已有测试在运行中")
                    return jsonify({'error': '已有测试在运行中，请等待完成'}), 400
                
                # 初始化进度状态
                self.test_progress.update({
                    'current': 0,
                    'total': 0,
                    'current_sample_id': '初始化中...',
                    'status': 'running',
                    'start_time': time.time(),
                    'dataset_name': dataset_name,
                    'model_name': model_name
                })
                
                # 运行测试集评估
                start_time = time.time()
                report = self.local_tester.run_dataset_evaluation(
                    model_name, 
                    dataset_name, 
                    sample_count=sample_count,
                    enable_thinking=enable_thinking,
                    progress_callback=lambda current, total, sample_id: self.progress_callback(current, total, sample_id)
                )
                end_time = time.time()
                
                # 生成 HTML 报告
                html_report_path = self.dataset_manager.generate_html_report(report)
                
                # 准备详细结果数据
                detailed_results = []
                for result in report.detailed_results:
                    # 调试日志：检查每个result的内容
                    self.logger.info(f"处理结果 - sample_id: {result.sample_id}, comment长度: {len(result.comment) if result.comment else 0}, model_response长度: {len(result.model_response) if result.model_response else 0}")
                    
                    # 确保sample_id不包含长文本（可能是数据错误）
                    clean_sample_id = result.sample_id
                    if len(str(clean_sample_id)) > 50:  # 如果sample_id过长，可能是错误数据
                        self.logger.warning(f"异常的sample_id长度: {len(str(clean_sample_id))}, 内容前50字符: {str(clean_sample_id)[:50]}")
                        # 尝试从ID中提取真正的sample_id（如果包含manga_xxx格式）
                        import re
                        match = re.search(r'manga_\d+', str(clean_sample_id))
                        if match:
                            clean_sample_id = match.group()
                            self.logger.info(f"从异常数据中提取到sample_id: {clean_sample_id}")
                        else:
                            clean_sample_id = 'Unknown'
                    
                    # 分离思考过程和最终回答
                    thinking_process, final_answer = self._separate_thinking_and_answer(result.model_response)
                    
                    detailed_results.append({
                        'sample_id': clean_sample_id,
                        'comment': result.comment,  # 添加原始评论内容
                        'model_response': self._truncate_response(result.model_response),
                        'thinking_process': self._truncate_response(thinking_process) if thinking_process else None,
                        'final_answer': self._truncate_response(final_answer),
                        'thinking_enabled': enable_thinking,  # 记录是否启用思考
                        'model_score': result.model_score,
                        'model_category': result.model_category,
                        'expected_score': result.expected_score,
                        'expected_category': result.expected_category,
                        'score_accuracy': result.score_accuracy,
                        'category_match': result.category_match,
                        'response_time_ms': result.response_time_ms,
                        'error': result.error,
                        'score_diff': abs(result.model_score - result.expected_score) if result.model_score else None
                    })
                
                self.logger.info(f"测试集评估完成: {len(detailed_results)} 个结果")
                
                return jsonify({
                    'success': True,
                    'report': {
                        'dataset_name': report.dataset_name,
                        'model_name': report.model_name,
                        'test_time': report.test_time,
                        'total_samples': report.total_samples,
                        'successful_tests': report.successful_tests,
                        'failed_tests': report.failed_tests,
                        'avg_score_accuracy': report.avg_score_accuracy,
                        'category_accuracy': report.category_accuracy,
                        'avg_response_time_ms': report.avg_response_time_ms,
                        'success_rate': report.successful_tests / max(report.total_samples, 1),
                        'detailed_results': detailed_results
                    },
                    'html_report_path': html_report_path,
                    'execution_time_ms': (end_time - start_time) * 1000
                })
                
                
            except Exception as e:
                self.logger.error(f"运行测试集评估失败: {e}")
                return jsonify({'error': str(e)}), 500
            finally:
                # 重置进度状态
                self.test_progress['status'] = 'idle'
        
        @self.app.route('/api/test/all-datasets', methods=['POST'])
        def api_test_all_datasets():
            """运行所有测试集评估"""
            self.logger.info("所有测试集评估API被调用")
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'error': '缺少请求数据'}), 400
                
                model_name = data.get('model', 'qwen3:0.6b')
                sample_count = data.get('sample_count', 5)
                enable_thinking = data.get('enable_thinking', True)  # 默认启用思考
                
                # 运行所有测试集评估
                start_time = time.time()
                reports = self.local_tester.run_all_dataset_evaluations(
                    model_name, 
                    sample_count=sample_count,
                    enable_thinking=enable_thinking
                )
                end_time = time.time()
                
                report_summaries = []
                for report in reports:
                    # 准备详细结果数据
                    detailed_results = []
                    for result in report.detailed_results:
                        # 分离思考过程和最终回答
                        thinking_process, final_answer = self._separate_thinking_and_answer(result.model_response)
                        
                        detailed_results.append({
                            'sample_id': result.sample_id,
                            'comment': result.comment,  # 添加原始评论内容
                            'model_response': self._truncate_response(result.model_response),
                            'thinking_process': self._truncate_response(thinking_process) if thinking_process else None,
                            'final_answer': self._truncate_response(final_answer),
                            'thinking_enabled': enable_thinking,  # 记录是否启用思考
                            'model_score': result.model_score,
                            'model_category': result.model_category,
                            'expected_score': result.expected_score,
                            'expected_category': result.expected_category,
                            'score_accuracy': result.score_accuracy,
                            'category_match': result.category_match,
                            'response_time_ms': result.response_time_ms,
                            'error': result.error,
                            'score_diff': abs(result.model_score - result.expected_score) if result.model_score else None
                        })
                    
                    summary = {
                        'dataset_name': report.dataset_name,
                        'model_name': report.model_name,
                        'test_time': report.test_time,
                        'total_samples': report.total_samples,
                        'successful_tests': report.successful_tests,
                        'failed_tests': report.failed_tests,
                        'avg_score_accuracy': report.avg_score_accuracy,
                        'category_accuracy': report.category_accuracy,
                        'avg_response_time_ms': report.avg_response_time_ms,
                        'success_rate': report.successful_tests / max(report.total_samples, 1),
                        'detailed_results': detailed_results  # 添加详细结果
                    }
                    report_summaries.append(summary)
                
                return jsonify({
                    'success': True,
                    'reports': report_summaries,
                    'total_datasets': len(reports),
                    'execution_time_ms': (end_time - start_time) * 1000
                })
                
            except Exception as e:
                self.logger.error(f"运行所有测试集评估失败: {e}")
                return jsonify({'error': str(e)}), 500
                
        self.logger.info("路由注册完成")
        
        # QPS评估相关API
        @self.app.route('/api/qps/start', methods=['POST'])
        def api_qps_start():
            """启动QPS评估测试"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'error': '缺少请求数据'}), 400
                
                # 获取测试配置
                test_name = data.get('test_name', '性能测试')
                model = data.get('model', 'qwen3:0.6b')
                concurrent_users = data.get('concurrent_users', 5)
                duration_seconds = data.get('duration_seconds', 60)
                prompt_template = data.get('prompt_template', '你好，请介绍一下你自己。')
                enable_thinking = data.get('enable_thinking', False)  # 获取思考模式配置
                dataset_name = data.get('dataset_name')  # 获取测试集名称
                
                # 创建测试配置
                config = self.qps_evaluator.create_test_config(
                    test_name=test_name,
                    model=model,
                    concurrent_users=concurrent_users,
                    duration_seconds=duration_seconds,
                    prompt_template=prompt_template,
                    enable_thinking=enable_thinking,
                    dataset_name=dataset_name
                )
                
                # 启动测试
                test_id = self.qps_evaluator.start_qps_test(config)
                
                return jsonify({
                    'test_id': test_id,
                    'message': 'QPS测试已启动',
                    'config': {
                        'test_name': test_name,
                        'model': model,
                        'concurrent_users': concurrent_users,
                        'duration_seconds': duration_seconds
                    }
                })
                
            except Exception as e:
                self.logger.error(f"启动QPS测试失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/qps/progress/<test_id>')
        def api_qps_progress(test_id):
            """获取QPS测试进度"""
            try:
                progress = self.qps_evaluator.get_test_progress(test_id)
                if progress is None:
                    return jsonify({'error': '测试ID不存在'}), 404
                
                return jsonify(progress)
                
            except Exception as e:
                self.logger.error(f"获取QPS测试进度失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/qps/results')
        def api_qps_results():
            """获取所有QPS测试结果列表"""
            try:
                results = self.qps_evaluator.get_all_test_results()
                
                # 转换为简化的列表格式
                result_list = []
                for result in results:
                    result_list.append({
                        'test_id': result.test_id,
                        'test_name': result.test_name,
                        'model': result.model,
                        'start_time': result.start_time,
                        'duration_seconds': result.duration_seconds,
                        'concurrent_users': result.concurrent_users,
                        'qps': result.qps,
                        'avg_latency_ms': result.avg_latency_ms,
                        'error_rate': result.error_rate,
                        'total_requests': result.total_requests,
                        'successful_requests': result.successful_requests
                    })
                
                return jsonify({
                    'results': result_list,
                    'total_count': len(result_list)
                })
                
            except Exception as e:
                self.logger.error(f"获取QPS测试结果失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/qps/results/<test_id>')
        def api_qps_result_detail(test_id):
            """获取QPS测试详细结果"""
            try:
                result = self.qps_evaluator.get_test_result(test_id)
                if result is None:
                    return jsonify({'error': '测试结果不存在'}), 404
                
                # 转换为字典格式
                from dataclasses import asdict
                return jsonify(asdict(result))
                
            except Exception as e:
                self.logger.error(f"获取QPS测试详细结果失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/qps/stop', methods=['POST'])
        def api_qps_stop():
            """停止当前QPS测试"""
            try:
                success = self.qps_evaluator.stop_current_test()
                if success:
                    return jsonify({'message': '测试已停止'})
                else:
                    return jsonify({'message': '没有正在运行的测试'})
                    
            except Exception as e:
                self.logger.error(f"停止QPS测试失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/qps/datasets')
        def api_qps_datasets():
            """获取可用的QPS测试集列表"""
            try:
                datasets = self.qps_evaluator.get_available_datasets()
                return jsonify(datasets)
            except Exception as e:
                self.logger.error(f"获取测试集列表失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/qps/models')
        def api_qps_models():
            """获取可用的模型列表"""
            try:
                models = self.ollama_client.list_models()
                return jsonify(models)
            except Exception as e:
                self.logger.error(f"获取模型列表失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/qps')
        def qps_page():
            """QPS评估页面"""
            return render_template('qps.html', 
                                 title="QPS性能评估",
                                 refresh_interval=get_config('web_dashboard.refresh_interval', 5))
        
        # 调试：打印所有注册的路由
        for rule in self.app.url_map.iter_rules():
            self.logger.info(f"已注册路由: {rule.rule} [{', '.join(rule.methods)}]")
    
    def progress_callback(self, current: int, total: int, current_sample_id: str):
        """测试进度回调函数"""
        self.test_progress.update({
            'current': current,
            'total': total,
            'current_sample_id': current_sample_id,
            'status': 'completed' if current >= total else 'running'
        })
        self.logger.info(f"测试进度: {current}/{total} - {current_sample_id}")
    
    def _prepare_chart_data(self, system_metrics: List, request_metrics: List) -> Dict[str, Any]:
        """准备图表数据"""
        charts = {}
        
        try:
            # 系统指标图表
            if system_metrics:
                timestamps = [m.timestamp for m in system_metrics]
                cpu_data = [m.cpu_percent for m in system_metrics]
                memory_data = [m.memory_percent for m in system_metrics]
                
                # CPU使用率图表
                charts['cpu_chart'] = {
                    'data': [{
                        'x': timestamps,
                        'y': cpu_data,
                        'type': 'scatter',
                        'mode': 'lines+markers',
                        'name': 'CPU使用率',
                        'line': {'color': '#667eea', 'width': 2}
                    }],
                    'layout': {
                        'title': {'text': 'CPU使用率 (%)', 'font': {'size': 16, 'color': '#334155'}},
                        'xaxis': {'title': '时间', 'gridcolor': '#e2e8f0'},
                        'yaxis': {'title': 'CPU (%)', 'gridcolor': '#e2e8f0'},
                        'height': 280,
                        'width': 540,
                        'margin': {'l': 60, 'r': 40, 't': 60, 'b': 60},
                        'plot_bgcolor': '#ffffff',
                        'paper_bgcolor': '#ffffff'
                    }
                }
                
                # 内存使用率图表
                charts['memory_chart'] = {
                    'data': [{
                        'x': timestamps,
                        'y': memory_data,
                        'type': 'scatter',
                        'mode': 'lines+markers',
                        'name': '内存使用率',
                        'line': {'color': '#10b981', 'width': 2}
                    }],
                    'layout': {
                        'title': {'text': '内存使用率 (%)', 'font': {'size': 16, 'color': '#334155'}},
                        'xaxis': {'title': '时间', 'gridcolor': '#e2e8f0'},
                        'yaxis': {'title': '内存 (%)', 'gridcolor': '#e2e8f0'},
                        'height': 280,
                        'width': 540,
                        'margin': {'l': 60, 'r': 40, 't': 60, 'b': 60},
                        'plot_bgcolor': '#ffffff',
                        'paper_bgcolor': '#ffffff'
                    }
                }
            
            # 请求延迟图表
            if request_metrics:
                successful_requests = [r for r in request_metrics if r.status == 'success']
                if successful_requests:
                    req_timestamps = [r.timestamp for r in successful_requests]
                    latencies = [r.latency_ms for r in successful_requests]
                    
                    charts['latency_chart'] = {
                        'data': [{
                            'x': req_timestamps,
                            'y': latencies,
                            'type': 'scatter',
                            'mode': 'markers',
                            'name': '请求延迟',
                            'marker': {'color': '#f59e0b', 'size': 6}
                        }],
                        'layout': {
                            'title': {'text': '请求延迟 (ms)', 'font': {'size': 16, 'color': '#334155'}},
                            'xaxis': {'title': '时间', 'gridcolor': '#e2e8f0'},
                            'yaxis': {'title': '延迟 (ms)', 'gridcolor': '#e2e8f0'},
                            'height': 280,
                            'width': 540,
                            'margin': {'l': 60, 'r': 40, 't': 60, 'b': 60},
                            'plot_bgcolor': '#ffffff',
                            'paper_bgcolor': '#ffffff'
                        }
                    }
                
                # 请求状态分布
                status_counts = {}
                for r in request_metrics:
                    status_counts[r.status] = status_counts.get(r.status, 0) + 1
                
                if status_counts:
                    charts['status_chart'] = {
                        'data': [{
                            'labels': list(status_counts.keys()),
                            'values': list(status_counts.values()),
                            'type': 'pie',
                            'name': '请求状态分布',
                            'marker': {'colors': ['#10b981', '#ef4444', '#f59e0b']}
                        }],
                        'layout': {
                            'title': {'text': '请求状态分布', 'font': {'size': 16, 'color': '#334155'}},
                            'height': 280,
                            'width': 540,
                            'margin': {'l': 40, 'r': 40, 't': 60, 'b': 40},
                            'plot_bgcolor': '#ffffff',
                            'paper_bgcolor': '#ffffff'
                        }
                    }
            
        except Exception as e:
            self.logger.error(f"准备图表数据失败: {e}")
        
        return charts
    
    def _sanitize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """清理配置中的敏感信息"""
        sensitive_keys = ['password', 'secret', 'key', 'token', 'api_key']
        
        def sanitize_dict(d):
            if isinstance(d, dict):
                result = {}
                for k, v in d.items():
                    if any(sensitive in k.lower() for sensitive in sensitive_keys):
                        result[k] = '***'
                    else:
                        result[k] = sanitize_dict(v)
                return result
            elif isinstance(d, list):
                return [sanitize_dict(item) for item in d]
            else:
                return d
        
        return sanitize_dict(config)
    
    def start(self) -> None:
        """启动Web服务"""
        if self._running:
            self.logger.warning("Web服务已在运行中")
            return
        
        self._running = True
        
        try:
            self.logger.info(f"启动本地监控界面: http://{self.host}:{self.port}")
            
            # 在单独线程中运行Flask应用
            def run_server():
                self.app.run(
                    host=self.host,
                    port=self.port,
                    debug=self.debug,
                    use_reloader=False,  # 避免在线程中使用reloader
                    threaded=True
                )
            
            self._server_thread = threading.Thread(target=run_server, daemon=True)
            self._server_thread.start()
            
            # 等待服务启动
            time.sleep(1)
            
            self.logger.info("本地监控界面启动成功")
            
        except Exception as e:
            self._running = False
            self.logger.error(f"启动Web服务失败: {e}")
            raise
    
    def stop(self) -> None:
        """停止Web服务"""
        if not self._running:
            return
        
        self._running = False
        
        # 停止性能监控
        if self.perf_monitor:
            self.perf_monitor.stop_monitoring()
        
        self.logger.info("本地监控界面已停止")
    
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._running
    
    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()


def create_local_dashboard(host: str = None, 
                          port: int = None, 
                          debug: bool = None) -> LocalDashboard:
    """
    创建本地监控界面的便捷函数
    
    Args:
        host: 监听地址
        port: 监听端口
        debug: 调试模式
        
    Returns:
        LocalDashboard: 本地监控界面实例
    """
    # 从配置获取默认值
    if host is None:
        host = get_config('web_dashboard.host', '127.0.0.1')
    if port is None:
        port = get_config('web_dashboard.port', 8080)
    if debug is None:
        debug = get_config('web_dashboard.debug', True)
    
    return LocalDashboard(host=host, port=port, debug=debug)


if __name__ == "__main__":
    # 示例用法
    import sys
    import signal
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 启动本地监控界面...")
    
    def signal_handler(signum, frame):
        print("\n🛑 收到停止信号，正在关闭监控界面...")
        dashboard.stop()
        sys.exit(0)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 创建并启动监控界面
        dashboard = create_local_dashboard()
        
        with dashboard:
            host = dashboard.host
            port = dashboard.port
            
            print(f"✅ 本地监控界面已启动!")
            print(f"🌐 访问地址: http://{host}:{port}")
            print(f"📊 健康检查: http://{host}:{port}/health")
            print(f"🔧 API文档: http://{host}:{port}/api/status")
            print("按 Ctrl+C 停止服务...")
            
            # 保持运行
            while dashboard.is_running():
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n🛑 用户中断，正在停止...")
    except Exception as e:
        print(f"❌ 启动异常: {e}")
    finally:
        print("👋 本地监控界面已停止")
