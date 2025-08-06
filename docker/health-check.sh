#!/bin/bash

# 健康检查脚本 - 验证容器和模型是否正常工作

# 检查Flask应用
curl -f http://localhost:5000/health > /dev/null 2>&1
FLASK_STATUS=$?

# 检查Ollama API
curl -f http://localhost:11434/api/tags > /dev/null 2>&1
OLLAMA_STATUS=$?

# 检查模型测试报告
if [ -f /app/data/model-test-report.json ]; then
    TEST_REPORT_EXISTS=0
else
    TEST_REPORT_EXISTS=1
fi

# 综合健康状态评估
if [ $FLASK_STATUS -eq 0 ] && [ $OLLAMA_STATUS -eq 0 ] && [ $TEST_REPORT_EXISTS -eq 0 ]; then
    exit 0  # 健康
else
    exit 1  # 不健康
fi