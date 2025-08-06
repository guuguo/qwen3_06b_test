#!/bin/bash
set -e

echo "🧪 Starting automated model testing..."

# 等待Ollama服务完全启动
echo "⏳ Waiting for Ollama service..."
for i in {1..60}; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Ollama service is ready!"
        break
    fi
    if [ $i -eq 60 ]; then
        echo "❌ Ollama service failed to start within 60 seconds"
        exit 1
    fi
    sleep 1
done

# 检查模型是否已下载
echo "📋 Checking available models..."
MODELS_JSON=$(curl -s http://localhost:11434/api/tags)
echo "Available models: $MODELS_JSON"

# 测试qwen3:0.6b-q4_k_m模型（量化版本）
if echo "$MODELS_JSON" | grep -q "qwen3:0.6b-q4_k_m"; then
    echo "🔬 Testing qwen3:0.6b-q4_k_m model..."
    
    TEST_RESPONSE=$(curl -s -X POST http://localhost:11434/api/generate \
        -H "Content-Type: application/json" \
        -d '{
            "model": "qwen3:0.6b-q4_k_m",
            "prompt": "你好，请用一句话介绍你自己。",
            "stream": false,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 100
            }
        }' --max-time 120)
    
    if echo "$TEST_RESPONSE" | grep -q "response" && ! echo "$TEST_RESPONSE" | grep -q "error"; then
        echo "✅ qwen3:0.6b-q4_k_m model test PASSED"
        echo "📝 Response: $(echo "$TEST_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('response', 'No response')[:100])")"
    else
        echo "❌ qwen3:0.6b-q4_k_m model test FAILED"
        echo "Error response: $TEST_RESPONSE"
    fi
else
    echo "⚠️  qwen3:0.6b-q4_k_m model not found, skipping test"
fi

# 测试qwen3:0.6b模型（普通版本）
if echo "$MODELS_JSON" | grep -q "qwen3:0.6b\""; then
    echo "🔬 Testing qwen3:0.6b model..."
    
    TEST_RESPONSE=$(curl -s -X POST http://localhost:11434/api/generate \
        -H "Content-Type: application/json" \
        -d '{
            "model": "qwen3:0.6b",
            "prompt": "请简单介绍一下人工智能。",
            "stream": false,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 150
            }
        }' --max-time 120)
    
    if echo "$TEST_RESPONSE" | grep -q "response" && ! echo "$TEST_RESPONSE" | grep -q "error"; then
        echo "✅ qwen3:0.6b model test PASSED"
        echo "📝 Response: $(echo "$TEST_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('response', 'No response')[:100])")"
    else
        echo "❌ qwen3:0.6b model test FAILED"
        echo "Error response: $TEST_RESPONSE"
    fi
else
    echo "⚠️  qwen3:0.6b model not found, skipping test"
fi

# 性能基准测试
echo "⚡ Running performance benchmark..."
BENCHMARK_START=$(date +%s)

BENCHMARK_RESPONSE=$(curl -s -X POST http://localhost:11434/api/generate \
    -H "Content-Type: application/json" \
    -d '{
        "model": "qwen3:0.6b-q4_k_m",
        "prompt": "请用50个字介绍Python编程语言的特点。",
        "stream": false,
        "options": {
            "temperature": 0.5,
            "max_tokens": 100
        }
    }' --max-time 120)

BENCHMARK_END=$(date +%s)
BENCHMARK_TIME=$((BENCHMARK_END - BENCHMARK_START))

if echo "$BENCHMARK_RESPONSE" | grep -q "response"; then
    echo "✅ Benchmark test completed in ${BENCHMARK_TIME} seconds"
    
    # 计算token数量（粗略估计）
    RESPONSE_TEXT=$(echo "$BENCHMARK_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('response', ''))")
    TOKEN_COUNT=$(echo "$RESPONSE_TEXT" | wc -c)
    
    if [ $BENCHMARK_TIME -gt 0 ]; then
        TOKENS_PER_SEC=$((TOKEN_COUNT / BENCHMARK_TIME))
        echo "📊 Approximate performance: ${TOKENS_PER_SEC} chars/second"
    fi
else
    echo "❌ Benchmark test failed"
fi

# 生成测试报告
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
cat > /app/data/model-test-report.json << EOF
{
    "timestamp": "$TIMESTAMP",
    "ollama_status": "healthy",
    "models_tested": {
        "qwen3:0.6b-q4_k_m": {
            "available": $(echo "$MODELS_JSON" | grep -q "qwen3:0.6b-q4_k_m" && echo "true" || echo "false"),
            "test_passed": $(echo "$TEST_RESPONSE" | grep -q "response" && ! echo "$TEST_RESPONSE" | grep -q "error" && echo "true" || echo "false")
        },
        "qwen3:0.6b": {
            "available": $(echo "$MODELS_JSON" | grep -q "qwen3:0.6b\"" && echo "true" || echo "false"),
            "test_passed": $(echo "$BENCHMARK_RESPONSE" | grep -q "response" && echo "true" || echo "false")
        }
    },
    "benchmark": {
        "response_time_seconds": $BENCHMARK_TIME,
        "approximate_tokens_per_second": $([ $BENCHMARK_TIME -gt 0 ] && echo $((TOKEN_COUNT / BENCHMARK_TIME)) || echo 0)
    }
}
EOF

echo "📋 Test report saved to /app/data/model-test-report.json"
echo "🎉 Automated model testing completed!"

# 如果所有测试都通过，返回成功状态
if echo "$MODELS_JSON" | grep -q "qwen3" && echo "$BENCHMARK_RESPONSE" | grep -q "response"; then
    echo "✅ All model tests PASSED - Container is ready for use!"
    exit 0
else
    echo "❌ Some model tests FAILED - Please check the logs"
    exit 1
fi