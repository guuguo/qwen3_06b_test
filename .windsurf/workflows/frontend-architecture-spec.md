---
description: 简化的WebUI前端扩展指南
---

# WebUI前端扩展简化指南

当需要从单页面扩展到多页面时的实用方案。

## 🎯 扩展原则

### 保持简单
- **继续使用当前架构**: Jinja2模板 + Tailwind CSS
- **渐进式扩展**: 只有需要时才添加新功能
- **最小化复杂度**: 避免过度工程化

## 📁 推荐结构

```
templates/
├── base.html                   # 基础模板
├── layouts/
│   └── dashboard.html         # 仪表板布局
├── pages/
│   ├── dashboard.html         # 主页(当前)
│   ├── models.html            # 模型管理页
│   └── settings.html          # 设置页
└── components/
    ├── header.html            # 页头组件
    ├── sidebar.html           # 侧边栏组件
    └── ui/
        ├── button.html        # 按钮组件
        └── card.html          # 卡片组件

static/
├── js/
│   ├── app.js                 # 全局脚本
│   └── pages/
│       ├── dashboard.js       # 页面专用脚本
│       └── models.js
└── css/
    └── custom.css             # 自定义样式补充
```

## 🧩 简单组件化

### 1. 基础模板 base.html
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}AI监控平台{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        'primary': '#667eea'
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-slate-50">
    {% block content %}{% endblock %}
    
    <script src="{{ url_for('static', filename='js/app.js') }}"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

### 2. 布局模板 layouts/dashboard.html
```html
{% extends "base.html" %}

{% block content %}
<div class="min-h-screen flex">
    {% include 'components/sidebar.html' %}
    
    <div class="flex-1">
        {% include 'components/header.html' %}
        
        <main class="p-6">
            {% block page_content %}{% endblock %}
        </main>
    </div>
</div>
{% endblock %}
```

### 3. 组件例子 components/ui/button.html
```html
<!-- 使用: {% include 'components/ui/button.html' %} -->
<button class="inline-flex items-center gap-2 px-6 py-3 rounded-lg font-medium text-sm 
               {% if variant == 'primary' %}text-white bg-gradient-to-r from-indigo-500 to-purple-600{% endif %}
               {% if variant == 'secondary' %}text-slate-700 bg-white border border-slate-300{% endif %}
               transition-all duration-150 hover:-translate-y-0.5">
    {% if icon %}{{ icon|safe }}{% endif %}
    {{ text }}
</button>
```

## 🔄 简单状态管理

### app.js - 全局状态
```javascript
// 简单全局状态
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
        // 简单的通知实现
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
};

// 页面导航
function navigateTo(page) {
    window.location.href = `/${page}`;
}
```

## 🛠 开发工作流

### 添加新页面
```bash
# 1. 创建页面模板
touch templates/pages/new-page.html

# 2. 创建页面脚本
touch static/js/pages/new-page.js

# 3. 在Flask中添加路由
# @app.route('/new-page')
# def new_page():
#     return render_template('pages/new-page.html')
```

### 创建可复用组件
```bash
# 1. 创建组件模板
touch templates/components/ui/new-component.html

# 2. 在页面中使用
# {% include 'components/ui/new-component.html' %}
```

## 📊 图表组件

### 简单图表组件
```html
<!-- components/chart.html -->
<div class="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
    <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold text-slate-800">{{ title }}</h3>
        <span class="text-xs text-slate-500 bg-slate-100 px-2 py-1 rounded-full">{{ unit }}</span>
    </div>
    <div id="{{ chart_id }}" class="w-full h-[280px]"></div>
</div>

<script>
// 在页面脚本中初始化
function initChart(chartId, data) {
    Plotly.newPlot(chartId, data, {
        height: 280,
        margin: { l: 60, r: 40, t: 20, b: 60 },
        plot_bgcolor: '#ffffff',
        paper_bgcolor: '#ffffff'
    }, { displayModeBar: false });
}
</script>
```

## 🎨 样式扩展

### 自定义样式 custom.css
```css
/* 只在需要时添加自定义样式 */
.chart-container {
    /* Plotly图表的特殊样式调整 */
}

.status-indicator {
    /* 状态指示器动画 */
    animation: pulse 2s infinite;
}

/* 响应式调整(如果需要) */
@media (max-width: 768px) {
    .desktop-only {
        display: none;
    }
}
```

## ✅ 实施步骤

### 第一步: 重构当前页面
1. 将dashboard.html拆分为base.html + layout + components
2. 提取可复用的UI组件
3. 整理JavaScript代码

### 第二步: 添加新页面
1. 复用layout和components
2. 创建页面特定的脚本
3. 添加Flask路由

### 第三步: 优化(可选)
1. 添加简单的状态管理
2. 实现组件间通信
3. 添加页面切换动画

这个简化方案保持了项目的轻量级特性，同时为扩展提供了清晰的路径。