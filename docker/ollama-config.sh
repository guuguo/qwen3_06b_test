#!/bin/bash
set -e

echo "🤖 Configuring Ollama for CPU optimization..."

# 等待Ollama服务启动
echo "⏳ Waiting for Ollama service to start..."
for i in {1..30}; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Ollama service is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Ollama service failed to start within 30 seconds"
        exit 1
    fi
    sleep 1
done

# 检查是否需要预下载模型
PRELOAD_MODEL=${PRELOAD_MODEL:-""}
if [ -n "$PRELOAD_MODEL" ]; then
    echo "📥 Pre-downloading model: $PRELOAD_MODEL"
    ollama pull $PRELOAD_MODEL || {
        echo "⚠️  Failed to download $PRELOAD_MODEL, continuing without preload"
    }
fi

# 推荐最佳CPU模型
echo "💡 Recommended CPU-optimized models:"
echo "   - qwen3:0.6b-q4_k_m  (Balanced performance/quality)"
echo "   - qwen3:0.6b-q4_0    (Faster inference)"
echo "   - qwen3:0.6b         (Original model)"

echo "🎯 Model management available at: http://localhost:5000"
echo "🔧 To download a model: ollama pull qwen3:0.6b-q4_k_m"

echo "✅ Ollama configuration completed!"