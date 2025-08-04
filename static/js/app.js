// 简化的全局状态管理
window.AppState = {
    user: null,
    loading: false,
    currentPage: 'dashboard',
    
    // 设置状态
    set(key, value) {
        this[key] = value;
        this.notify(key, value);
    },
    
    // 监听器
    listeners: {},
    
    // 监听状态变化
    on(key, callback) {
        if (!this.listeners[key]) this.listeners[key] = [];
        this.listeners[key].push(callback);
    },
    
    // 通知变化
    notify(key, value) {
        if (this.listeners[key]) {
            this.listeners[key].forEach(cb => cb(value));
        }
    },
    
    // 显示通知
    showNotification(message, type = 'info') {
        console.log(`[${type.toUpperCase()}] ${message}`);
        // 可以扩展为实际的通知组件
    }
};

// 工具函数
window.Utils = {
    // 显示错误信息
    showError(message) {
        console.error(message);
        AppState.showNotification(message, 'error');
    },
    
    // 格式化时间
    formatTime(timestamp) {
        return new Date(timestamp).toLocaleString();
    },
    
    // 安全的JSON解析
    safeJSONParse(str, fallback = null) {
        try {
            return JSON.parse(str);
        } catch (e) {
            console.error('JSON解析失败:', e);
            return fallback;
        }
    }
};

// 页面导航
function navigateTo(page) {
    window.location.href = `/${page}`;
}

// 全局初始化
document.addEventListener('DOMContentLoaded', function() {
    AppState.set('currentPage', window.location.pathname.split('/')[1] || 'dashboard');
    console.log('应用已初始化');
});