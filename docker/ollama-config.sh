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

# 预下载推荐的CPU优化模型
echo "📥 Pre-downloading CPU-optimized models..."

# 下载量化版本（更快推理）
echo "📦 Downloading qwen3:0.6b-q4_k_m (quantized, balanced performance)..."
ollama pull qwen3:0.6b-q4_k_m || {
    echo "⚠️  Failed to download qwen3:0.6b-q4_k_m"
}

# 下载普通版本（更高质量）
echo "📦 Downloading qwen3:0.6b (original, higher quality)..."
ollama pull qwen3:0.6b || {
    echo "⚠️  Failed to download qwen3:0.6b"
}

# 检查是否有额外指定的模型
PRELOAD_MODEL=${PRELOAD_MODEL:-""}
if [ -n "$PRELOAD_MODEL" ] && [ "$PRELOAD_MODEL" != "qwen3:0.6b-q4_k_m" ] && [ "$PRELOAD_MODEL" != "qwen3:0.6b" ]; then
    echo "📥 Pre-downloading additional model: $PRELOAD_MODEL"
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