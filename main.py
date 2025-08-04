#!/usr/bin/env python3
"""
Qwen-3 主启动脚本

提供统一的启动入口，支持：
- 本地开发环境启动
- 监控界面启动
- 性能测试运行
- 配置管理
- 系统状态检查

作者: Qwen-3 部署团队
版本: 1.0.0
"""

import os
import sys
import time
import signal
import argparse
import logging
from pathlib import Path
from typing import Optional

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config_manager import get_config_manager, reset_config_manager
from src.ollama_integration import create_ollama_client
from src.simple_monitor import create_simple_monitor
from src.local_dashboard import create_local_dashboard
from src.local_tester import SimpleLocalTester


class Qwen3Launcher:
    """Qwen-3 启动器"""
    
    def __init__(self, environment: str = "local"):
        """
        初始化启动器
        
        Args:
            environment: 环境名称 (local, server, production)
        """
        self.environment = environment
        self.logger = None
        self.components = {}
        
        # 设置日志
        self._setup_logging()
        
        # 信号处理
        self._setup_signal_handlers()
        
        self.logger.info(f"Qwen-3 启动器初始化完成: 环境={environment}")
    
    def _setup_logging(self):
        """设置日志"""
        # 创建日志目录
        log_dir = Path("./logs")
        log_dir.mkdir(exist_ok=True)
        
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "qwen3_main.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            self.logger.info(f"收到信号 {signum}，正在关闭...")
            self.stop_all()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def check_dependencies(self) -> bool:
        """检查依赖"""
        self.logger.info("检查系统依赖...")
        
        try:
            # 检查Python版本
            if sys.version_info < (3, 8):
                self.logger.error("需要Python 3.8或更高版本")
                return False
            
            # 检查必需的包
            required_packages = [
                'requests', 'flask', 'yaml', 'psutil', 
                'watchdog', 'plotly'
            ]
            
            missing_packages = []
            for package in required_packages:
                try:
                    __import__(package)
                except ImportError:
                    missing_packages.append(package)
            
            if missing_packages:
                self.logger.error(f"缺少必需的包: {', '.join(missing_packages)}")
                self.logger.info("请运行: pip install -r requirements.txt")
                return False
            
            self.logger.info("✅ 依赖检查通过")
            return True
            
        except Exception as e:
            self.logger.error(f"依赖检查失败: {e}")
            return False
    
    def check_ollama_service(self) -> bool:
        """检查Ollama服务"""
        self.logger.info("检查Ollama服务状态...")
        
        try:
            ollama_client = create_ollama_client()
            if ollama_client.check_ollama_status():
                models = ollama_client.list_models()
                self.logger.info(f"✅ Ollama服务正常，可用模型: {len(models)}")
                for model in models:
                    self.logger.info(f"   - {model}")
                return True
            else:
                self.logger.warning("❌ Ollama服务不可用")
                self.logger.info("请确保Ollama服务已启动: ollama serve")
                return False
                
        except Exception as e:
            self.logger.error(f"检查Ollama服务失败: {e}")
            return False
    
    def start_monitoring(self) -> bool:
        """启动监控组件"""
        self.logger.info("启动监控组件...")
        
        try:
            # 创建监控器
            file_monitor, perf_monitor = create_simple_monitor()
            
            # 启动性能监控
            perf_monitor.start_monitoring()
            
            self.components['file_monitor'] = file_monitor
            self.components['perf_monitor'] = perf_monitor
            
            self.logger.info("✅ 监控组件启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"启动监控组件失败: {e}")
            return False
    
    def start_dashboard(self, host: str = None, port: int = None) -> bool:
        """启动Web监控界面"""
        self.logger.info("启动Web监控界面...")
        
        try:
            dashboard = create_local_dashboard(host=host, port=port)
            dashboard.start()
            
            self.components['dashboard'] = dashboard
            
            actual_host = dashboard.host
            actual_port = dashboard.port
            
            self.logger.info(f"✅ Web监控界面启动成功")
            self.logger.info(f"🌐 访问地址: http://{actual_host}:{actual_port}")
            self.logger.info(f"📊 健康检查: http://{actual_host}:{actual_port}/health")
            
            return True
            
        except Exception as e:
            self.logger.error(f"启动Web监控界面失败: {e}")
            return False
    
    def run_system_check(self) -> dict:
        """运行系统检查"""
        self.logger.info("运行系统检查...")
        
        results = {
            'dependencies': False,
            'ollama_service': False,
            'config': False,
            'directories': False
        }
        
        try:
            # 检查依赖
            results['dependencies'] = self.check_dependencies()
            
            # 检查Ollama服务
            results['ollama_service'] = self.check_ollama_service()
            
            # 检查配置
            try:
                config_manager = get_config_manager(environment=self.environment)
                config_info = config_manager.get_config_info()
                self.logger.info(f"✅ 配置加载成功: {config_info['config_keys_count']} 项配置")
                results['config'] = True
            except Exception as e:
                self.logger.error(f"配置检查失败: {e}")
            
            # 检查目录结构
            required_dirs = ['logs', 'config', 'src', 'templates']
            missing_dirs = []
            
            for dir_name in required_dirs:
                dir_path = Path(dir_name)
                if not dir_path.exists():
                    missing_dirs.append(dir_name)
                    dir_path.mkdir(parents=True, exist_ok=True)
            
            if missing_dirs:
                self.logger.info(f"创建缺失目录: {', '.join(missing_dirs)}")
            
            results['directories'] = True
            self.logger.info("✅ 目录结构检查完成")
            
            # 总结
            passed = sum(results.values())
            total = len(results)
            
            self.logger.info(f"系统检查完成: {passed}/{total} 项通过")
            
            if passed == total:
                self.logger.info("🎉 系统检查全部通过，可以正常使用！")
            else:
                self.logger.warning("⚠️  部分检查未通过，可能影响功能使用")
            
            return results
            
        except Exception as e:
            self.logger.error(f"系统检查异常: {e}")
            return results
    
    def start_full_stack(self, host: str = None, port: int = None) -> bool:
        """启动完整技术栈"""
        self.logger.info("🚀 启动Qwen-3完整技术栈...")
        
        # 系统检查
        check_results = self.run_system_check()
        
        if not check_results['dependencies']:
            self.logger.error("❌ 依赖检查失败，无法启动")
            return False
        
        # 启动监控
        if not self.start_monitoring():
            self.logger.error("❌ 监控组件启动失败")
            return False
        
        # 启动Web界面
        if not self.start_dashboard(host, port):
            self.logger.error("❌ Web界面启动失败")
            return False
        
        self.logger.info("🎉 Qwen-3技术栈启动完成！")
        
        if not check_results['ollama_service']:
            self.logger.warning("⚠️  Ollama服务未运行，推理功能不可用")
            self.logger.info("💡 启动Ollama: ollama serve")
        
        return True
    
    def stop_all(self):
        """停止所有组件"""
        self.logger.info("停止所有组件...")
        
        for name, component in self.components.items():
            try:
                if hasattr(component, 'stop'):
                    component.stop()
                elif hasattr(component, 'stop_monitoring'):
                    component.stop_monitoring()
                self.logger.info(f"✅ {name} 已停止")
            except Exception as e:
                self.logger.error(f"停止 {name} 失败: {e}")
        
        # 重置配置管理器
        try:
            reset_config_manager()
        except Exception as e:
            self.logger.error(f"重置配置管理器失败: {e}")
        
        self.logger.info("👋 所有组件已停止")
    
    def keep_alive(self):
        """保持程序运行"""
        try:
            self.logger.info("程序运行中，按 Ctrl+C 停止...")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("收到中断信号")
        finally:
            self.stop_all()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Qwen-3 大语言模型部署与监控系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py                          # 启动完整系统（本地环境）
  python main.py --check                  # 仅运行系统检查
  python main.py --dashboard-only         # 仅启动Web界面
  python main.py --monitor-only           # 仅启动监控
  python main.py --env server             # 使用服务器环境配置
  python main.py --host 0.0.0.0 --port 8080  # 自定义Web界面地址
        """
    )
    
    parser.add_argument(
        '--env', 
        choices=['local', 'server', 'production'],
        default='local',
        help='运行环境 (默认: local)'
    )
    
    parser.add_argument(
        '--host',
        default=None,
        help='Web界面监听地址 (默认: 从配置读取)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=None,
        help='Web界面监听端口 (默认: 从配置读取)'
    )
    
    parser.add_argument(
        '--check',
        action='store_true',
        help='仅运行系统检查'
    )
    
    parser.add_argument(
        '--dashboard-only',
        action='store_true',
        help='仅启动Web监控界面'
    )
    
    parser.add_argument(
        '--monitor-only',
        action='store_true',
        help='仅启动监控组件'
    )
    
    args = parser.parse_args()
    
    # 创建启动器
    launcher = Qwen3Launcher(environment=args.env)
    
    try:
        if args.check:
            # 仅运行系统检查
            launcher.run_system_check()
            
        elif args.dashboard_only:
            # 仅启动Web界面
            if launcher.start_dashboard(args.host, args.port):
                launcher.keep_alive()
            
        elif args.monitor_only:
            # 仅启动监控
            if launcher.start_monitoring():
                launcher.keep_alive()
            
        else:
            # 启动完整系统
            if launcher.start_full_stack(args.host, args.port):
                launcher.keep_alive()
        
    except Exception as e:
        launcher.logger.error(f"启动异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
