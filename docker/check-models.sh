#!/bin/bash

echo "🔍 Checking Qwen3 Dashboard Model Status..."
echo "============================================"

# 检查容器状态
echo "📦 Container Status:"
docker ps --filter name=qwen3-dashboard --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "🤖 Model Testing Results:"

# 检查模型测试报告
if docker exec qwen3-dashboard test -f /app/data/model-test-report.json; then
    echo "📋 Model Test Report:"
    docker exec qwen3-dashboard cat /app/data/model-test-report.json | python3 -m json.tool
else
    echo "⚠️  Model test report not found. Testing may still be in progress."
fi

echo ""
echo "📊 Available Models:"
docker exec qwen3-dashboard curl -s http://localhost:11434/api/tags | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    models = data.get('models', [])
    if models:
        for model in models:
            name = model.get('name', 'Unknown')
            size = model.get('size', 0)
            size_mb = round(size / (1024*1024), 1)
            print(f'  ✅ {name} ({size_mb} MB)')
    else:
        print('  ❌ No models found')
except:
    print('  ⚠️  Unable to fetch model list')
"

echo ""
echo "🌐 Service Endpoints:"
echo "  • Web Dashboard: http://localhost:8080"
echo "  • Ollama API: http://localhost:11434"
echo "  • Health Check: http://localhost:8080/health"

echo ""
echo "🧪 Quick Model Test:"
echo "Run this command to test the quantized model:"
echo 'curl -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d '\''{"model": "qwen3:0.6b-q4_k_m", "prompt": "你好，请介绍一下你自己。", "stream": false}'\'''

echo ""
echo "📝 View detailed logs:"
echo "  • docker logs qwen3-dashboard"
echo "  • docker exec qwen3-dashboard cat /var/log/supervisor/model-test.out.log"