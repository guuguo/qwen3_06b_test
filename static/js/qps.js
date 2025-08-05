// QPS评估页面JavaScript代码
let currentTestId = null;
let progressInterval = null;

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    refreshResults();
    initThinkingToggle();
});

// 初始化思考模式开关
function initThinkingToggle() {
    const toggle = document.getElementById('enableThinkingToggle');
    const text = document.getElementById('thinkingModeText');
    const hint = document.getElementById('thinkingModeHint');
    
    if (toggle && text && hint) {
        toggle.addEventListener('change', function() {
            if (this.checked) {
                text.textContent = '启用思考';
                hint.textContent = '显示模型推理过程';
            } else {
                text.textContent = '关闭思考';
                hint.textContent = '关闭可提升QPS性能';
            }
        });
    }
}

// 标签页切换
function showTab(tabName) {
    // 隐藏所有内容
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // 重置所有标签按钮
    document.querySelectorAll('[id$="Tab"]').forEach(tab => {
        tab.classList.remove('bg-indigo-500', 'text-white');
        tab.classList.add('text-slate-600', 'bg-slate-100');
    });
    
    // 显示选中的内容
    document.getElementById(tabName + 'Content').classList.add('active');
    
    // 激活选中的标签
    const activeTab = document.getElementById(tabName + 'Tab');
    activeTab.classList.remove('text-slate-600', 'bg-slate-100');
    activeTab.classList.add('bg-indigo-500', 'text-white');
    
    // 如果切换到结果页面，刷新数据
    if (tabName === 'results') {
        refreshResults();
    }
}

// 加载预设配置
function loadPreset(preset) {
    const presets = {
        light: {
            concurrentUsers: 3,
            durationSeconds: 30,
            testName: '轻负载测试'
        },
        medium: {
            concurrentUsers: 10,
            durationSeconds: 120,
            testName: '中等负载测试'
        },
        heavy: {
            concurrentUsers: 20,
            durationSeconds: 300,
            testName: '重负载测试'
        }
    };
    
    const config = presets[preset];
    if (config) {
        document.getElementById('testName').value = config.testName;
        document.getElementById('concurrentUsers').value = config.concurrentUsers;
        document.getElementById('durationSeconds').value = config.durationSeconds;
    }
}

// 重置表单
function resetForm() {
    document.getElementById('testName').value = '性能测试';
    document.getElementById('modelSelect').value = 'qwen3:0.6b';
    document.getElementById('concurrentUsers').value = '5';
    document.getElementById('durationSeconds').value = '60';
    document.getElementById('promptTemplate').value = '你好，请介绍一下你自己。';
}

// 启动QPS测试
async function startQPSTest() {
    const startBtn = document.getElementById('startTestBtn');
    const originalText = startBtn.innerHTML;
    
    try {
        startBtn.disabled = true;
        startBtn.innerHTML = '🔄 启动中...';
        
        // 获取表单元素并检查是否存在
        const testNameEl = document.getElementById('testName');
        const modelSelectEl = document.getElementById('modelSelect');
        const concurrentUsersEl = document.getElementById('concurrentUsers');
        const durationSecondsEl = document.getElementById('durationSeconds');
        const promptTemplateEl = document.getElementById('promptTemplate');
        const enableThinkingEl = document.getElementById('enableThinkingToggle');
        
        // 检查元素是否存在
        if (!testNameEl || !modelSelectEl || !concurrentUsersEl || !durationSecondsEl || !promptTemplateEl || !enableThinkingEl) {
            console.error('某些表单元素不存在:', {
                testName: !!testNameEl,
                modelSelect: !!modelSelectEl,
                concurrentUsers: !!concurrentUsersEl,
                durationSeconds: !!durationSecondsEl,
                promptTemplate: !!promptTemplateEl,
                enableThinking: !!enableThinkingEl
            });
            showNotification('表单元素不存在，请刷新页面', 'error');
            return;
        }
        
        const config = {
            test_name: testNameEl.value || '性能测试',
            model: modelSelectEl.value || 'qwen3:0.6b',
            concurrent_users: parseInt(concurrentUsersEl.value) || 5,
            duration_seconds: parseInt(durationSecondsEl.value) || 60,
            prompt_template: promptTemplateEl.value || '你好，请介绍一下你自己。',
            enable_thinking: enableThinkingEl.checked || false
        };
        
        // 调试信息
        console.log('发送QPS测试配置:', config);
        
        const response = await fetch('/api/qps/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            currentTestId = result.test_id;
            showCurrentTestStatus(result.test_id, config);
            startProgressMonitoring(result.test_id);
            
            // 显示成功消息
            showNotification('测试已启动！', 'success');
        } else {
            throw new Error(result.error || '启动测试失败');
        }
        
    } catch (error) {
        console.error('启动QPS测试失败:', error);
        showNotification('启动测试失败: ' + error.message, 'error');
    } finally {
        startBtn.disabled = false;
        startBtn.innerHTML = originalText;
    }
}

// 显示当前测试状态
function showCurrentTestStatus(testId, config) {
    const statusDiv = document.getElementById('currentTestStatus');
    const testIdSpan = document.getElementById('currentTestId');
    
    testIdSpan.textContent = `${config.test_name} (${testId})`;
    statusDiv.classList.remove('hidden');
}

// 隐藏当前测试状态
function hideCurrentTestStatus() {
    document.getElementById('currentTestStatus').classList.add('hidden');
}

// 开始进度监控
function startProgressMonitoring(testId) {
    if (progressInterval) {
        clearInterval(progressInterval);
    }
    
    progressInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/qps/progress/${testId}`);
            const progress = await response.json();
            
            if (response.ok) {
                updateProgress(progress);
                
                // 如果测试完成或失败，停止监控
                if (progress.status === 'completed' || progress.status === 'failed' || progress.status === 'stopped') {
                    clearInterval(progressInterval);
                    progressInterval = null;
                    currentTestId = null;
                    
                    setTimeout(() => {
                        hideCurrentTestStatus();
                        refreshResults();
                    }, 2000);
                }
            }
        } catch (error) {
            console.error('获取进度失败:', error);
        }
    }, 2000);
}

// 更新进度显示
function updateProgress(progress) {
    const progressBar = document.getElementById('currentProgressBar');
    const progressText = document.getElementById('currentProgress');
    
    if (progressBar) {
        progressBar.style.width = `${progress.progress}%`;
    }
    if (progressText) {
        progressText.textContent = `${progress.progress}%`;
    }
}

// 停止当前测试
async function stopCurrentTest() {
    if (!currentTestId) return;
    
    try {
        const response = await fetch('/api/qps/stop', {
            method: 'POST'
        });
        
        const result = await response.json();
        showNotification(result.message, response.ok ? 'success' : 'error');
        
        if (response.ok) {
            if (progressInterval) {
                clearInterval(progressInterval);
                progressInterval = null;
            }
            currentTestId = null;
            hideCurrentTestStatus();
        }
        
    } catch (error) {
        console.error('停止测试失败:', error);
        showNotification('停止测试失败: ' + error.message, 'error');
    }
}

// 刷新结果列表
async function refreshResults() {
    try {
        const response = await fetch('/api/qps/results');
        const data = await response.json();
        
        if (response.ok) {
            updateResultsTable(data.results);
            updateResultsStats(data.results);
        } else {
            throw new Error(data.error || '获取结果失败');
        }
        
    } catch (error) {
        console.error('刷新结果失败:', error);
        showNotification('刷新结果失败: ' + error.message, 'error');
    }
}

// 更新结果表格
function updateResultsTable(results) {
    const tbody = document.getElementById('resultsTableBody');
    
    if (results.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center py-8 text-slate-500">
                    暂无测试结果
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = results.map(result => {
        // 处理思考模式显示
        const thinkingMode = result.enable_thinking !== undefined ? 
            (result.enable_thinking ? 
                '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800">启用</span>' : 
                '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">禁用</span>'
            ) : 
            '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">未知</span>';
        
        return `
        <tr class="clickable-row border-b border-slate-100 hover:bg-slate-50" onclick="showTestDetail('${result.test_id}')">
            <td class="py-3 px-4">${result.test_name}</td>
            <td class="py-3 px-4">${result.model}</td>
            <td class="py-3 px-4">${new Date(result.start_time).toLocaleString()}</td>
            <td class="py-3 px-4">${result.concurrent_users}</td>
            <td class="py-3 px-4">${thinkingMode}</td>
            <td class="py-3 px-4 font-medium">${result.qps.toFixed(2)}</td>
            <td class="py-3 px-4">${result.avg_latency_ms.toFixed(0)}ms</td>
            <td class="py-3 px-4 ${result.error_rate > 5 ? 'text-red-600' : result.error_rate > 1 ? 'text-yellow-600' : 'text-green-600'}">${result.error_rate.toFixed(1)}%</td>
            <td class="py-3 px-4">
                <button onclick="event.stopPropagation(); showTestDetail('${result.test_id}')" class="text-indigo-600 hover:text-indigo-800 text-sm">
                    查看详情
                </button>
            </td>
        </tr>
        `;
    }).join('');
}

// 更新结果统计
function updateResultsStats(results) {
    if (results.length === 0) {
        document.getElementById('totalTests').textContent = '0';
        document.getElementById('avgQPS').textContent = '-';
        document.getElementById('avgLatency').textContent = '-';
        document.getElementById('avgErrorRate').textContent = '-';
        return;
    }
    
    const totalTests = results.length;
    const avgQPS = results.reduce((sum, r) => sum + r.qps, 0) / totalTests;
    const avgLatency = results.reduce((sum, r) => sum + r.avg_latency_ms, 0) / totalTests;
    const avgErrorRate = results.reduce((sum, r) => sum + r.error_rate, 0) / totalTests;
    
    document.getElementById('totalTests').textContent = totalTests;
    document.getElementById('avgQPS').textContent = avgQPS.toFixed(1);
    document.getElementById('avgLatency').textContent = avgLatency.toFixed(0);
    document.getElementById('avgErrorRate').textContent = avgErrorRate.toFixed(1) + '%';
}

// 显示测试详情
async function showTestDetail(testId) {
    try {
        const response = await fetch(`/api/qps/results/${testId}`);
        const result = await response.json();
        
        if (response.ok) {
            showDetailModal(result);
        } else {
            throw new Error(result.error || '获取详情失败');
        }
        
    } catch (error) {
        console.error('获取测试详情失败:', error);
        showNotification('获取测试详情失败: ' + error.message, 'error');
    }
}

// 显示详情模态框
function showDetailModal(result) {
    const modal = document.getElementById('detailModal');
    const content = document.getElementById('detailContent');
    
    content.innerHTML = `
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div class="space-y-4">
                <h4 class="font-semibold text-slate-800">基本信息</h4>
                <div class="space-y-2 text-sm">
                    <div><span class="font-medium">测试名称:</span> ${result.test_name}</div>
                    <div><span class="font-medium">模型:</span> ${result.model}</div>
                    <div><span class="font-medium">开始时间:</span> ${new Date(result.start_time).toLocaleString()}</div>
                    <div><span class="font-medium">结束时间:</span> ${new Date(result.end_time).toLocaleString()}</div>
                    <div><span class="font-medium">测试时长:</span> ${result.duration_seconds.toFixed(1)}秒</div>
                    <div><span class="font-medium">并发用户数:</span> ${result.concurrent_users}</div>
                    <div><span class="font-medium">思考模式:</span> ${result.enable_thinking !== undefined ? (result.enable_thinking ? '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800">启用</span>' : '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">禁用</span>') : '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">未知</span>'}</div>
                </div>
            </div>
            
            <div class="space-y-4">
                <h4 class="font-semibold text-slate-800">性能指标</h4>
                <div class="space-y-2 text-sm">
                    <div><span class="font-medium">QPS:</span> ${result.qps.toFixed(2)}</div>
                    <div><span class="font-medium">总请求数:</span> ${result.total_requests}</div>
                    <div><span class="font-medium">成功请求:</span> ${result.successful_requests}</div>
                    <div><span class="font-medium">失败请求:</span> ${result.failed_requests}</div>
                    <div><span class="font-medium">错误率:</span> ${result.error_rate.toFixed(2)}%</div>
                    <div><span class="font-medium">吞吐量:</span> ${result.throughput_tokens_per_second.toFixed(1)} tokens/s</div>
                </div>
            </div>
        </div>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="space-y-4">
                <h4 class="font-semibold text-slate-800">延迟统计 (ms)</h4>
                <div class="space-y-2 text-sm">
                    <div><span class="font-medium">平均延迟:</span> ${result.avg_latency_ms.toFixed(2)}</div>
                    <div><span class="font-medium">最小延迟:</span> ${result.min_latency_ms.toFixed(2)}</div>
                    <div><span class="font-medium">最大延迟:</span> ${result.max_latency_ms.toFixed(2)}</div>
                    <div><span class="font-medium">P50延迟:</span> ${result.p50_latency_ms.toFixed(2)}</div>
                    <div><span class="font-medium">P95延迟:</span> ${result.p95_latency_ms.toFixed(2)}</div>
                    <div><span class="font-medium">P99延迟:</span> ${result.p99_latency_ms.toFixed(2)}</div>
                </div>
            </div>
            
            <div class="space-y-4">
                <h4 class="font-semibold text-slate-800">延迟分布</h4>
                <div class="space-y-2 text-sm">
                    ${Object.entries(result.detailed_metrics.latency_distribution.buckets).map(([bucket, count]) => 
                        `<div><span class="font-medium">${bucket}:</span> ${count}个请求</div>`
                    ).join('')}
                </div>
            </div>
        </div>
        
        ${result.errors.length > 0 ? `
            <div class="mt-6">
                <h4 class="font-semibold text-slate-800 mb-2">错误信息</h4>
                <div class="bg-red-50 border border-red-200 rounded p-4">
                    <ul class="text-sm text-red-700 space-y-1">
                        ${result.errors.map(error => `<li>• ${error}</li>`).join('')}
                    </ul>
                </div>
            </div>
        ` : ''}
    `;
    
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

// 关闭详情模态框
function closeDetailModal() {
    const modal = document.getElementById('detailModal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

// 显示通知消息
function showNotification(message, type = 'info') {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg transition-all duration-300 transform translate-x-full`;
    
    // 根据类型设置样式
    switch (type) {
        case 'success':
            notification.classList.add('bg-green-500', 'text-white');
            break;
        case 'error':
            notification.classList.add('bg-red-500', 'text-white');
            break;
        case 'warning':
            notification.classList.add('bg-yellow-500', 'text-white');
            break;
        default:
            notification.classList.add('bg-blue-500', 'text-white');
    }
    
    notification.innerHTML = `
        <div class="flex items-center gap-2">
            <span>${message}</span>
            <button onclick="this.parentElement.parentElement.remove()" class="ml-2 text-white hover:text-gray-200">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
            </button>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // 显示动画
    setTimeout(() => {
        notification.classList.remove('translate-x-full');
    }, 100);
    
    // 自动隐藏
    setTimeout(() => {
        notification.classList.add('translate-x-full');
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 300);
    }, 5000);
}
