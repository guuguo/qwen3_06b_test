#!/usr/bin/env python3
"""
Docker环境下的Dashboard启动脚本
专门为容器环境优化的启动配置
"""

import os
import sys
import time
import logging
from pathlib import Path

# 添加项目路径到Python路径
sys.path.insert(0, '/app')

def setup_logging():
    """设置日志配置"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/app/logs/dashboard.log')
        ]
    )

def wait_for_ollama():
    """等待Ollama服务启动"""
    import requests
    import time
    
    logger = logging.getLogger(__name__)
    ollama_url = "http://localhost:11434/api/tags"
    
    logger.info("等待Ollama服务启动...")
    
    for i in range(60):  # 等待最多60秒
        try:
            response = requests.get(ollama_url, timeout=5)
            if response.status_code == 200:
                logger.info("✅ Ollama服务已就绪")
                return True
        except Exception as e:
            if i % 10 == 0:  # 每10秒打印一次
                logger.info(f"等待Ollama服务... ({i+1}/60)")
        
        time.sleep(1)
    
    logger.error("❌ Ollama服务启动超时")
    return False

def main():
    """主函数"""
    # 设置日志
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 启动Docker环境下的Qwen3 Dashboard...")
    
    # 设置环境变量
    os.environ.setdefault('FLASK_HOST', '0.0.0.0')
    os.environ.setdefault('FLASK_PORT', '5000')
    os.environ.setdefault('FLASK_ENV', 'production')
    
    # 创建必要目录
    os.makedirs('/app/logs', exist_ok=True)
    os.makedirs('/app/data', exist_ok=True)
    os.makedirs('/app/test_results', exist_ok=True)
    
    # 等待Ollama服务
    if not wait_for_ollama():
        logger.error("Ollama服务未能启动，退出")
        sys.exit(1)
    
    # 导入并启动Dashboard
    try:
        # 添加src路径到Python路径
        src_path = os.path.join('/app', 'src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        
        from local_dashboard import create_local_dashboard
        
        logger.info("创建Dashboard实例...")
        dashboard = create_local_dashboard(
            host=os.environ.get('FLASK_HOST', '0.0.0.0'),
            port=int(os.environ.get('FLASK_PORT', 5000)),
            debug=False
        )
        
        logger.info("启动Dashboard服务...")
        with dashboard:
            host = dashboard.host
            port = dashboard.port
            
            logger.info(f"✅ Qwen3 Dashboard已启动!")
            logger.info(f"🌐 Web界面: http://{host}:{port}")
            logger.info(f"🤖 Ollama API: http://localhost:11434")
            logger.info(f"📊 健康检查: http://{host}:{port}/health")
            
            # 保持运行
            try:
                while dashboard.is_running():
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("收到停止信号...")
                
    except Exception as e:
        logger.error(f"❌ Dashboard启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    logger.info("👋 Dashboard已停止")

if __name__ == "__main__":
    main()