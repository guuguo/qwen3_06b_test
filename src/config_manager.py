#!/usr/bin/env python3
"""
Qwen-3 配置管理模块

提供统一的配置管理功能，包括：
- YAML配置文件加载和解析
- 环境变量覆盖支持
- 配置验证和默认值处理
- 热重载配置更新
- 配置缓存和性能优化

作者: Qwen-3 部署团队
版本: 1.0.0
"""

import os
import yaml
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import copy


@dataclass
class ConfigValidationError(Exception):
    """配置验证错误"""
    message: str
    path: str = ""
    value: Any = None


@dataclass
class ConfigChangeEvent:
    """配置变更事件"""
    timestamp: datetime
    config_path: str
    changed_keys: List[str]
    old_values: Dict[str, Any]
    new_values: Dict[str, Any]


class ConfigFileWatcher(FileSystemEventHandler):
    """配置文件监控器"""
    
    def __init__(self, config_manager: 'ConfigManager'):
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
    
    def on_modified(self, event):
        """文件修改事件处理"""
        if event.is_directory:
            return
        
        # 检查是否是配置文件
        if event.src_path in self.config_manager._watched_files:
            self.logger.info(f"检测到配置文件变更: {event.src_path}")
            try:
                # 延迟重载，避免文件写入过程中的读取
                time.sleep(0.1)
                self.config_manager.reload_config()
            except Exception as e:
                self.logger.error(f"重载配置失败: {e}")


class ConfigManager:
    """
    配置管理器
    
    提供统一的配置管理功能，支持多环境配置、热重载、验证等。
    """
    
    def __init__(self, 
                 config_dir: str = "./config",
                 environment: str = "local",
                 enable_hot_reload: bool = True):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录
            environment: 环境名称 (local, server, production)
            enable_hot_reload: 是否启用热重载
        """
        self.config_dir = Path(config_dir)
        self.environment = environment
        self.enable_hot_reload = enable_hot_reload
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 配置存储
        self._config = {}
        self._config_lock = threading.RLock()
        self._last_modified = {}
        self._watched_files = set()
        
        # 变更监听器
        self._change_listeners: List[Callable[[ConfigChangeEvent], None]] = []
        
        # 文件监控
        self._observer = None
        self._file_watcher = None
        
        # 默认配置
        self._default_config = self._get_default_config()
        
        # 加载配置
        self._load_config()
        
        # 启动热重载
        if self.enable_hot_reload:
            self._start_file_watcher()
        
        self.logger.info(f"配置管理器初始化完成: 环境={environment}, 热重载={'启用' if enable_hot_reload else '禁用'}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'ollama': {
                'base_url': 'http://localhost:11434',
                'timeout': 30,
                'retry': {
                    'max_attempts': 3,
                    'backoff_factor': 1.5,
                    'max_delay': 10
                },
                'connection_pool': {
                    'max_connections': 10,
                    'max_keepalive_connections': 5,
                    'keepalive_expiry': 300
                },
                'model_cache': {
                    'enabled': True,
                    'ttl_seconds': 300,
                    'max_entries': 50
                }
            },
            'monitoring': {
                'file_monitor': {
                    'log_dir': './logs',
                    'max_log_files': 30,
                    'enable_request_logging': True,
                    'enable_system_logging': True
                },
                'performance_monitor': {
                    'collection_interval': 60,
                    'auto_start': True
                }
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file_logging': {
                    'enabled': True,
                    'filename': './logs/qwen3.log'
                },
                'console_logging': {
                    'enabled': True,
                    'level': 'INFO'
                }
            }
        }
    
    def _load_config(self) -> None:
        """加载配置文件"""
        with self._config_lock:
            # 从默认配置开始
            self._config = copy.deepcopy(self._default_config)
            
            # 加载环境配置文件
            config_file = self.config_dir / f"{self.environment}_config.yaml"
            
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        file_config = yaml.safe_load(f) or {}
                    
                    # 深度合并配置
                    self._deep_merge(self._config, file_config)
                    
                    # 记录文件信息
                    self._last_modified[str(config_file)] = config_file.stat().st_mtime
                    self._watched_files.add(str(config_file))
                    
                    self.logger.info(f"已加载配置文件: {config_file}")
                    
                except Exception as e:
                    self.logger.error(f"加载配置文件失败 {config_file}: {e}")
                    raise ConfigValidationError(f"配置文件加载失败: {e}", str(config_file))
            else:
                self.logger.warning(f"配置文件不存在: {config_file}")
            
            # 应用环境变量覆盖
            self._apply_env_overrides()
            
            # 验证配置
            self._validate_config()
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """深度合并字典"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _apply_env_overrides(self) -> None:
        """应用环境变量覆盖"""
        # 定义环境变量映射
        env_mappings = {
            'QWEN3_OLLAMA_URL': ['ollama', 'base_url'],
            'QWEN3_OLLAMA_TIMEOUT': ['ollama', 'timeout'],
            'QWEN3_LOG_LEVEL': ['logging', 'level'],
            'QWEN3_LOG_DIR': ['monitoring', 'file_monitor', 'log_dir'],
            'QWEN3_MONITOR_INTERVAL': ['monitoring', 'performance_monitor', 'collection_interval'],
            'QWEN3_MAX_CONNECTIONS': ['ollama', 'connection_pool', 'max_connections'],
            'QWEN3_CACHE_TTL': ['ollama', 'model_cache', 'ttl_seconds'],
        }
        
        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    # 尝试转换数据类型
                    if env_value.lower() in ('true', 'false'):
                        env_value = env_value.lower() == 'true'
                    elif env_value.isdigit():
                        env_value = int(env_value)
                    elif '.' in env_value and env_value.replace('.', '').isdigit():
                        env_value = float(env_value)
                    
                    # 设置配置值
                    self._set_nested_value(self._config, config_path, env_value)
                    self.logger.info(f"环境变量覆盖: {env_var} -> {'.'.join(config_path)} = {env_value}")
                    
                except Exception as e:
                    self.logger.warning(f"环境变量处理失败 {env_var}: {e}")
    
    def _set_nested_value(self, config: Dict[str, Any], path: List[str], value: Any) -> None:
        """设置嵌套配置值"""
        current = config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def _validate_config(self) -> None:
        """验证配置"""
        try:
            # 验证必需的配置项
            required_paths = [
                ['ollama', 'base_url'],
                ['monitoring', 'file_monitor', 'log_dir'],
                ['logging', 'level']
            ]
            
            for path in required_paths:
                if not self._get_nested_value(self._config, path):
                    raise ConfigValidationError(
                        f"缺少必需的配置项: {'.'.join(path)}",
                        '.'.join(path)
                    )
            
            # 验证数据类型和范围
            validations = [
                (['ollama', 'timeout'], int, lambda x: x > 0, "超时时间必须大于0"),
                (['ollama', 'retry', 'max_attempts'], int, lambda x: 1 <= x <= 10, "重试次数必须在1-10之间"),
                (['monitoring', 'performance_monitor', 'collection_interval'], int, lambda x: x >= 10, "收集间隔必须至少10秒"),
                (['ollama', 'connection_pool', 'max_connections'], int, lambda x: x > 0, "连接池大小必须大于0"),
            ]
            
            for path, expected_type, validator, error_msg in validations:
                value = self._get_nested_value(self._config, path)
                if value is not None:
                    if not isinstance(value, expected_type):
                        raise ConfigValidationError(
                            f"配置项类型错误: {'.'.join(path)} 应为 {expected_type.__name__}",
                            '.'.join(path),
                            value
                        )
                    if not validator(value):
                        raise ConfigValidationError(
                            f"配置项值无效: {'.'.join(path)} - {error_msg}",
                            '.'.join(path),
                            value
                        )
            
            self.logger.info("配置验证通过")
            
        except ConfigValidationError:
            raise
        except Exception as e:
            raise ConfigValidationError(f"配置验证失败: {e}")
    
    def _get_nested_value(self, config: Dict[str, Any], path: List[str]) -> Any:
        """获取嵌套配置值"""
        current = config
        for key in path:
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        return current
    
    def _start_file_watcher(self) -> None:
        """启动文件监控"""
        try:
            self._file_watcher = ConfigFileWatcher(self)
            self._observer = Observer()
            self._observer.schedule(
                self._file_watcher,
                str(self.config_dir),
                recursive=False
            )
            self._observer.start()
            self.logger.info("配置文件监控已启动")
        except Exception as e:
            self.logger.error(f"启动文件监控失败: {e}")
    
    def _stop_file_watcher(self) -> None:
        """停止文件监控"""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            self._file_watcher = None
            self.logger.info("配置文件监控已停止")
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            path: 配置路径，使用点号分隔 (如 'ollama.base_url')
            default: 默认值
            
        Returns:
            Any: 配置值
        """
        with self._config_lock:
            keys = path.split('.')
            return self._get_nested_value(self._config, keys) or default
    
    def set(self, path: str, value: Any) -> None:
        """
        设置配置值（仅内存中）
        
        Args:
            path: 配置路径
            value: 配置值
        """
        with self._config_lock:
            keys = path.split('.')
            self._set_nested_value(self._config, keys, value)
            self.logger.info(f"配置已更新: {path} = {value}")
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        获取配置段
        
        Args:
            section: 配置段名称
            
        Returns:
            Dict[str, Any]: 配置段内容
        """
        with self._config_lock:
            return copy.deepcopy(self._config.get(section, {}))
    
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        Returns:
            Dict[str, Any]: 完整配置
        """
        with self._config_lock:
            return copy.deepcopy(self._config)
    
    def reload_config(self) -> None:
        """重新加载配置"""
        try:
            old_config = copy.deepcopy(self._config)
            
            # 重新加载
            self._load_config()
            
            # 检测变更
            changed_keys = self._detect_changes(old_config, self._config)
            
            if changed_keys:
                # 触发变更事件
                event = ConfigChangeEvent(
                    timestamp=datetime.now(),
                    config_path=str(self.config_dir / f"{self.environment}_config.yaml"),
                    changed_keys=changed_keys,
                    old_values={key: self._get_nested_value(old_config, key.split('.')) for key in changed_keys},
                    new_values={key: self._get_nested_value(self._config, key.split('.')) for key in changed_keys}
                )
                
                self._notify_change_listeners(event)
                
                self.logger.info(f"配置已重载，变更项: {', '.join(changed_keys)}")
            else:
                self.logger.info("配置已重载，无变更")
                
        except Exception as e:
            self.logger.error(f"重载配置失败: {e}")
            raise
    
    def _detect_changes(self, old_config: Dict[str, Any], new_config: Dict[str, Any], prefix: str = "") -> List[str]:
        """检测配置变更"""
        changes = []
        
        # 检查所有键
        all_keys = set(old_config.keys()) | set(new_config.keys())
        
        for key in all_keys:
            current_path = f"{prefix}.{key}" if prefix else key
            
            old_value = old_config.get(key)
            new_value = new_config.get(key)
            
            if old_value != new_value:
                if isinstance(old_value, dict) and isinstance(new_value, dict):
                    # 递归检查嵌套字典
                    changes.extend(self._detect_changes(old_value, new_value, current_path))
                else:
                    changes.append(current_path)
        
        return changes
    
    def add_change_listener(self, listener: Callable[[ConfigChangeEvent], None]) -> None:
        """
        添加配置变更监听器
        
        Args:
            listener: 监听器函数
        """
        self._change_listeners.append(listener)
        self.logger.info(f"已添加配置变更监听器: {listener.__name__}")
    
    def remove_change_listener(self, listener: Callable[[ConfigChangeEvent], None]) -> None:
        """
        移除配置变更监听器
        
        Args:
            listener: 监听器函数
        """
        if listener in self._change_listeners:
            self._change_listeners.remove(listener)
            self.logger.info(f"已移除配置变更监听器: {listener.__name__}")
    
    def _notify_change_listeners(self, event: ConfigChangeEvent) -> None:
        """通知配置变更监听器"""
        for listener in self._change_listeners:
            try:
                listener(event)
            except Exception as e:
                self.logger.error(f"配置变更监听器异常 {listener.__name__}: {e}")
    
    def export_config(self, output_path: str) -> None:
        """
        导出当前配置到文件
        
        Args:
            output_path: 输出文件路径
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(
                    self.get_all(),
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    indent=2
                )
            
            self.logger.info(f"配置已导出到: {output_path}")
            
        except Exception as e:
            self.logger.error(f"导出配置失败: {e}")
            raise
    
    def get_config_info(self) -> Dict[str, Any]:
        """
        获取配置信息
        
        Returns:
            Dict[str, Any]: 配置信息
        """
        with self._config_lock:
            return {
                'environment': self.environment,
                'config_dir': str(self.config_dir),
                'hot_reload_enabled': self.enable_hot_reload,
                'watched_files': list(self._watched_files),
                'last_modified': dict(self._last_modified),
                'change_listeners_count': len(self._change_listeners),
                'config_keys_count': len(self._flatten_config(self._config))
            }
    
    def _flatten_config(self, config: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """扁平化配置字典"""
        result = {}
        for key, value in config.items():
            current_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                result.update(self._flatten_config(value, current_key))
            else:
                result[current_key] = value
        return result
    
    def validate_config_file(self, config_file: str) -> List[str]:
        """
        验证配置文件
        
        Args:
            config_file: 配置文件路径
            
        Returns:
            List[str]: 验证错误列表
        """
        errors = []
        
        try:
            config_path = Path(config_file)
            if not config_path.exists():
                errors.append(f"配置文件不存在: {config_file}")
                return errors
            
            # 加载配置文件
            with open(config_path, 'r', encoding='utf-8') as f:
                test_config = yaml.safe_load(f) or {}
            
            # 创建临时配置管理器进行验证
            temp_config = copy.deepcopy(self._default_config)
            self._deep_merge(temp_config, test_config)
            
            # 验证配置
            try:
                # 这里可以添加更多的验证逻辑
                pass
            except ConfigValidationError as e:
                errors.append(str(e))
            
        except yaml.YAMLError as e:
            errors.append(f"YAML格式错误: {e}")
        except Exception as e:
            errors.append(f"验证失败: {e}")
        
        return errors
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self._stop_file_watcher()


# 全局配置管理器实例
_global_config_manager: Optional[ConfigManager] = None
_config_lock = threading.Lock()


def get_config_manager(config_dir: str = "./config",
                      environment: str = None,
                      enable_hot_reload: bool = True) -> ConfigManager:
    """
    获取全局配置管理器实例
    
    Args:
        config_dir: 配置文件目录
        environment: 环境名称，None表示自动检测
        enable_hot_reload: 是否启用热重载
        
    Returns:
        ConfigManager: 配置管理器实例
    """
    global _global_config_manager
    
    with _config_lock:
        if _global_config_manager is None:
            # 自动检测环境
            if environment is None:
                environment = os.getenv('QWEN3_ENV', 'local')
            
            _global_config_manager = ConfigManager(
                config_dir=config_dir,
                environment=environment,
                enable_hot_reload=enable_hot_reload
            )
        
        return _global_config_manager


def reset_config_manager():
    """重置全局配置管理器"""
    global _global_config_manager
    
    with _config_lock:
        if _global_config_manager:
            _global_config_manager._stop_file_watcher()
            _global_config_manager = None


# 便捷函数
def get_config(path: str, default: Any = None) -> Any:
    """获取配置值的便捷函数"""
    return get_config_manager().get(path, default)


def get_config_section(section: str) -> Dict[str, Any]:
    """获取配置段的便捷函数"""
    return get_config_manager().get_section(section)


if __name__ == "__main__":
    # 示例用法
    import sys
    import signal
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 启动配置管理器测试...")
    
    def config_change_handler(event: ConfigChangeEvent):
        """配置变更处理器"""
        print(f"📝 配置变更检测:")
        print(f"   时间: {event.timestamp}")
        print(f"   文件: {event.config_path}")
        print(f"   变更项: {', '.join(event.changed_keys)}")
        for key in event.changed_keys:
            old_val = event.old_values.get(key)
            new_val = event.new_values.get(key)
            print(f"   {key}: {old_val} -> {new_val}")
    
    def signal_handler(signum, frame):
        print("\n🛑 收到停止信号，正在关闭配置管理器...")
        reset_config_manager()
        sys.exit(0)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 创建配置管理器
        config_manager = get_config_manager()
        
        # 添加变更监听器
        config_manager.add_change_listener(config_change_handler)
        
        # 显示配置信息
        info = config_manager.get_config_info()
        print(f"📋 配置管理器信息:")
        print(f"   环境: {info['environment']}")
        print(f"   配置目录: {info['config_dir']}")
        print(f"   热重载: {'启用' if info['hot_reload_enabled'] else '禁用'}")
        print(f"   监控文件: {len(info['watched_files'])}")
        print(f"   配置项数: {info['config_keys_count']}")
        
        # 测试配置获取
        print(f"📊 配置测试:")
        print(f"   Ollama URL: {config_manager.get('ollama.base_url')}")
        print(f"   日志级别: {config_manager.get('logging.level')}")
        print(f"   监控间隔: {config_manager.get('monitoring.performance_monitor.collection_interval')}")
        
        # 测试配置段获取
        ollama_config = config_manager.get_section('ollama')
        print(f"   Ollama配置: {len(ollama_config)} 项")
        
        # 测试便捷函数
        log_dir = get_config('monitoring.file_monitor.log_dir')
        print(f"   日志目录: {log_dir}")
        
        print("✅ 配置管理器测试完成！")
        
        if config_manager.enable_hot_reload:
            print("🔄 热重载已启用，修改配置文件将自动重载...")
            print("按 Ctrl+C 停止测试")
            
            # 保持运行以测试热重载
            while True:
                time.sleep(1)
        
    except KeyboardInterrupt:
        print("\n🛑 用户中断，正在停止...")
    except Exception as e:
        print(f"❌ 测试异常: {e}")
    finally:
        reset_config_manager()
        print("👋 配置管理器已停止")
