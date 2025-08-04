---
description: 桌面端Tailwind CSS前端设计规范与美学工作流
---

# 桌面端Tailwind CSS前端设计规范工作流

这个工作流定义了基于Tailwind CSS的优雅极简主义美学与功能完美平衡的桌面端前端设计规范。

## 🎨 设计哲学

### 核心原则
- **桌面端专注**: 专门为桌面端设计，无响应式适配
- **Tailwind CSS驱动**: 使用Tailwind实用类构建一致的设计系统
- **纯HTML方案**: 通过CDN加载Tailwind，不依赖构建工具
- **组件化思维**: 构建可复用的组件设计模式
- **性能优先**: 利用Tailwind的优化特性，减少代码量

## 🌈 Tailwind CSS配色系统

### CDN引入方式
```html
<!-- Tailwind CSS CDN -->
<script src="https://cdn.tailwindcss.com"></script>
<script>
  // 自定义配置
  tailwind.config = {
    theme: {
      extend: {
        colors: {
          'ai-primary': '#667eea',
          'ai-primary-light': '#8fa4f3',
          'ai-primary-dark': '#4c63d2',
        },
        animation: {
          'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        }
      }
    }
  }
</script>
```

### 核心配色方案
```html
<!-- 品牌主色调 -->
<div class="bg-indigo-500 text-white">主色调</div>
<div class="bg-indigo-400 text-white">主色调-浅</div>
<div class="bg-indigo-600 text-white">主色调-深</div>

<!-- 中性色系 -->
<div class="bg-slate-50">极浅灰</div>
<div class="bg-slate-100">浅灰</div>
<div class="bg-slate-200">中浅灰</div>
<div class="bg-slate-300">中灰</div>
<div class="bg-slate-400">灰</div>
<div class="bg-slate-500">深灰</div>
<div class="bg-slate-600">更深灰</div>
<div class="bg-slate-700">很深灰</div>
<div class="bg-slate-800">极深灰</div>
<div class="bg-slate-900">最深灰</div>

<!-- 功能色系 -->
<div class="bg-emerald-500 text-white">成功色</div>
<div class="bg-amber-500 text-white">警告色</div>
<div class="bg-red-500 text-white">错误色</div>
<div class="bg-blue-500 text-white">信息色</div>
```

### 渐变效果
```html
<!-- AI科技风渐变 -->
<div class="bg-gradient-to-br from-indigo-500 to-purple-600">AI渐变</div>
<div class="bg-gradient-to-r from-blue-400 to-cyan-400">科技渐变</div>
<div class="bg-gradient-to-tr from-pink-400 to-red-400">暖色渐变</div>
```

## 📐 桌面端固定布局系统

### 容器布局
```html
<!-- 主容器 - 1200px最大宽度，居中 -->
<div class="max-w-6xl mx-auto px-8">
  <!-- 内容 -->
</div>

<!-- 固定网格系统 - 桌面端专用 -->
<!-- 状态卡片网格 (4列) -->
<div class="grid grid-cols-4 gap-6">
  <div class="..."># 状态卡片</div>
  <div class="..."># 状态卡片</div>
  <div class="..."># 状态卡片</div>
  <div class="..."># 状态卡片</div>
</div>

<!-- 图表网格 (2列) -->
<div class="grid grid-cols-2 gap-6">
  <div class="..."># 图表容器</div>
  <div class="..."># 图表容器</div>
</div>

<!-- 表单网格 (2列) -->
<div class="grid grid-cols-2 gap-6">
  <div class="..."># 表单字段</div>
  <div class="..."># 表单字段</div>
</div>
```

### Tailwind间距系统
```html
<!-- Tailwind标准间距类 -->
<div class="p-1">padding: 4px</div>
<div class="p-2">padding: 8px</div>
<div class="p-3">padding: 12px</div>
<div class="p-4">padding: 16px</div>
<div class="p-6">padding: 24px</div>
<div class="p-8">padding: 32px</div>
<div class="p-12">padding: 48px</div>
<div class="p-16">padding: 64px</div>

<!-- 间距应用示例 -->
<section class="py-8 mb-6">
  <div class="p-6 space-y-4">
    <!-- 内容 -->
  </div>
</section>
```

## 🎯 桌面端组件设计规范

### 卡片组件
```html
<!-- 状态卡片 -->
<div class="bg-white rounded-xl p-6 shadow-sm border border-slate-200 min-h-[140px] flex flex-col justify-between transition-all duration-300 relative overflow-hidden hover:-translate-y-0.5 hover:shadow-lg hover:border-indigo-500 group">
  <!-- 左侧装饰条 -->
  <div class="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-indigo-500 to-purple-600 rounded-r-sm"></div>
  
  <!-- 卡片内容 -->
  <div class="flex-1">
    <div class="flex items-center justify-between mb-3">
      <h3 class="text-sm font-medium text-slate-600 uppercase tracking-wide">系统状态</h3>
      <div class="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
    </div>
    <div class="text-3xl font-bold text-slate-900 mb-1">正常</div>
    <div class="text-sm text-slate-500">最后更新: 刚刚</div>
  </div>
</div>

<!-- 图表卡片 -->
<div class="bg-white rounded-xl shadow-sm border border-slate-200 p-4 overflow-hidden transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg">
  <div class="flex items-center justify-between mb-4">
    <h3 class="text-lg font-semibold text-slate-800">CPU使用率</h3>
    <span class="text-xs text-slate-500 bg-slate-100 px-2 py-1 rounded-full">实时</span>
  </div>
  <div class="chart-container">
    <!-- Plotly图表容器 -->
  </div>
</div>
```

### 按钮组件
```html
<!-- 主按钮 -->
<button class="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg font-medium text-sm text-white bg-gradient-to-r from-indigo-500 to-purple-600 shadow-sm transition-all duration-150 hover:-translate-y-0.5 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none">
  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
  </svg>
  开始测试
</button>

<!-- 次要按钮 -->
<button class="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg font-medium text-sm text-slate-700 bg-white border border-slate-300 shadow-sm transition-all duration-150 hover:bg-slate-50 hover:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed">
  取消
</button>

<!-- 图标按钮 -->
<button class="inline-flex items-center justify-center w-10 h-10 rounded-lg text-slate-500 bg-white border border-slate-200 shadow-sm transition-all duration-150 hover:bg-slate-50 hover:text-indigo-600 hover:border-indigo-300">
  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
  </svg>
</button>

<!-- 状态按钮 -->
<div class="inline-flex items-center gap-2">
  <button class="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-emerald-700 bg-emerald-50 border border-emerald-200">
    <div class="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
    运行中
  </button>
  
  <button class="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-slate-700 bg-slate-100 border border-slate-200">
    <div class="w-2 h-2 bg-slate-400 rounded-full"></div>
    已停止
  </button>
</div>
```

### 表单组件
```html
<!-- 表单组 -->
<div class="flex flex-col gap-2">
  <label class="text-sm font-medium text-slate-600 uppercase tracking-wide">
    模型名称
  </label>
  <input 
    type="text" 
    class="px-4 py-3 border border-slate-300 rounded-lg text-sm transition-all duration-150 bg-white text-slate-900 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-3 focus:ring-indigo-500/10" 
    placeholder="qwen3:0.6b"
  />
</div>

<!-- 选择框 -->
<div class="flex flex-col gap-2">
  <label class="text-sm font-medium text-slate-600 uppercase tracking-wide">
    测试集
  </label>
  <select class="px-4 py-3 border border-slate-300 rounded-lg text-sm transition-all duration-150 bg-white text-slate-900 focus:outline-none focus:border-indigo-500 focus:ring-3 focus:ring-indigo-500/10">
    <option value="">选择测试集</option>
    <option value="call-complaints">通话投诉分类</option>
    <option value="manga-ads">漫画广告检测</option>
  </select>
</div>

<!-- 数字输入 -->
<div class="flex flex-col gap-2">
  <label class="text-sm font-medium text-slate-600 uppercase tracking-wide">
    样本数量
  </label>
  <input 
    type="number" 
    min="1" 
    max="50" 
    value="10"
    class="px-4 py-3 border border-slate-300 rounded-lg text-sm transition-all duration-150 bg-white text-slate-900 focus:outline-none focus:border-indigo-500 focus:ring-3 focus:ring-indigo-500/10" 
  />
</div>

<!-- 文本域 -->
<div class="flex flex-col gap-2">
  <label class="text-sm font-medium text-slate-600 uppercase tracking-wide">
    测试提示
  </label>
  <textarea 
    rows="4"
    class="px-4 py-3 border border-slate-300 rounded-lg text-sm transition-all duration-150 bg-white text-slate-900 placeholder-slate-500 resize-none focus:outline-none focus:border-indigo-500 focus:ring-3 focus:ring-indigo-500/10" 
    placeholder="输入自定义测试提示..."
  ></textarea>
</div>
```

## ✨ 微交互设计

### 悬停效果
```html
<!-- 交互元素 -->
<div class="transition-all duration-300 hover:-translate-y-0.5 hover:brightness-105">
  <!-- 内容 -->
</div>

<!-- 可点击元素 -->
<div class="cursor-pointer select-none active:scale-95 transition-transform duration-75">
  <!-- 内容 -->
</div>

<!-- 卡片悬停效果 -->
<div class="transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-indigo-500/10">
  <!-- 卡片内容 -->
</div>
```

### 状态指示器
```html
<!-- 在线状态 -->
<div class="flex items-center gap-2">
  <div class="w-2 h-2 bg-emerald-500 rounded-full animate-pulse shadow-sm shadow-emerald-500/50"></div>
  <span class="text-sm text-slate-600">在线</span>
</div>

<!-- 离线状态 -->
<div class="flex items-center gap-2">
  <div class="w-2 h-2 bg-red-500 rounded-full shadow-sm shadow-red-500/50"></div>
  <span class="text-sm text-slate-600">离线</span>
</div>

<!-- 处理中状态 -->
<div class="flex items-center gap-2">
  <div class="w-2 h-2 bg-amber-500 rounded-full animate-ping shadow-sm shadow-amber-500/50"></div>
  <span class="text-sm text-slate-600">处理中</span>
</div>

<!-- 状态徽章 -->
<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
  <div class="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></div>
  运行中
</span>
```

### 加载效果
```html
<!-- 骨架屏加载 -->
<div class="animate-pulse">
  <div class="h-4 bg-slate-200 rounded w-3/4 mb-2"></div>
  <div class="h-4 bg-slate-200 rounded w-1/2 mb-2"></div>
  <div class="h-4 bg-slate-200 rounded w-5/6"></div>
</div>

<!-- 闪烁加载效果 -->
<div class="relative overflow-hidden bg-slate-200 rounded">
  <div class="absolute inset-0 -translate-x-full animate-[shimmer_1.5s_infinite] bg-gradient-to-r from-transparent via-white/60 to-transparent"></div>
</div>

<!-- 加载按钮 -->
<button class="inline-flex items-center gap-2 px-6 py-3 bg-indigo-500 text-white rounded-lg disabled:opacity-50" disabled>
  <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
  </svg>
  处理中...
</button>

<!-- 自定义闪烁动画 -->
<style>
  @keyframes shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
  }
</style>
```

## 🎭 主题系统

### 桌面端浅色主题（默认）
```html
<!-- 主要背景色 -->
<div class="bg-white">主背景</div>
<div class="bg-slate-50">次背景</div>
<div class="bg-slate-100">三级背景</div>

<!-- 文字颜色 -->
<div class="text-slate-900">主要文字</div>
<div class="text-slate-600">次要文字</div>
<div class="text-slate-500">辅助文字</div>

<!-- 边框颜色 -->
<div class="border border-slate-200">默认边框</div>
<div class="border border-slate-300">强调边框</div>
```

### 深色主题（可选扩展）
```html
<!-- 如需支持深色主题，可使用 dark: 前缀 -->
<div class="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
  自适应主题内容
</div>

<!-- 深色主题切换器 -->
<button 
  onclick="document.documentElement.classList.toggle('dark')" 
  class="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
>
  <svg class="w-5 h-5 dark:hidden" fill="currentColor" viewBox="0 0 20 20">
    <path fill-rule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clip-rule="evenodd"></path>
  </svg>
  <svg class="w-5 h-5 hidden dark:block" fill="currentColor" viewBox="0 0 20 20">
    <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z"></path>
  </svg>
</button>
```

## 📊 图表组件规范

### 固定尺寸图表容器
```html
<!-- 图表容器 -->
<div class="bg-white rounded-xl shadow-sm border border-slate-200 p-4 overflow-hidden transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg">
  <!-- 图表头部 -->
  <div class="flex items-center justify-between mb-4">
    <h3 class="text-lg font-semibold text-slate-800">CPU使用率</h3>
    <div class="flex items-center gap-2">
      <span class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-emerald-100 text-emerald-800 rounded-full">
        <div class="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></div>
        实时
      </span>
    </div>
  </div>
  
  <!-- 图表内容区域 -->
  <div class="chart-container" id="cpu-chart">
    <!-- Plotly图表将在此渲染 -->
  </div>
</div>

<!-- 网格布局的图表组 -->
<div class="grid grid-cols-2 gap-6">
  <!-- CPU图表 -->
  <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-slate-800">CPU使用率</h3>
      <span class="text-xs text-slate-500 bg-slate-100 px-2 py-1 rounded-full">%</span>
    </div>
    <div id="cpu-chart" class="w-full h-[280px]"></div>
  </div>
  
  <!-- 内存图表 -->
  <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-slate-800">内存使用率</h3>
      <span class="text-xs text-slate-500 bg-slate-100 px-2 py-1 rounded-full">MB</span>
    </div>
    <div id="memory-chart" class="w-full h-[280px]"></div>
  </div>
</div>
```

### Plotly图表配置
```javascript
// 桌面端固定尺寸配置（兼容Tailwind）
const chartLayout = {
    height: 280,
    width: 540,
    margin: { l: 60, r: 40, t: 60, b: 60 },
    plot_bgcolor: '#ffffff',
    paper_bgcolor: '#ffffff',
    title: { 
        font: { size: 16, color: '#1e293b' } // slate-800
    },
    xaxis: { 
        gridcolor: '#e2e8f0', // slate-200
        title: { font: { color: '#64748b' } } // slate-500
    },
    yaxis: { 
        gridcolor: '#e2e8f0', // slate-200
        title: { font: { color: '#64748b' } } // slate-500
    },
    font: {
        family: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif',
        color: '#475569' // slate-600
    }
};

// 创建图表（无响应式）
Plotly.newPlot(chartId, data, chartLayout, {
    displayModeBar: false,
    staticPlot: false
});

// Tailwind兼容的配色方案
const tailwindColors = {
    indigo: '#6366f1',     // indigo-500
    emerald: '#10b981',    // emerald-500
    amber: '#f59e0b',      // amber-500
    red: '#ef4444',        // red-500
    blue: '#3b82f6',       // blue-500
    purple: '#8b5cf6',     // purple-500
    pink: '#ec4899',       // pink-500
    slate: '#64748b'       // slate-500
};
```

## 📋 实施检查清单

### 桌面端设计审查
- [ ] 配色符合Tailwind设计规范
- [ ] 1200px容器宽度适配（max-w-6xl）
- [ ] 圆角统一（rounded-lg/rounded-xl）
- [ ] 阴影层次清晰（shadow-sm/shadow-lg）
- [ ] 微交互自然流畅（hover:-translate-y-0.5）
- [ ] 固定网格布局合理（grid-cols-2/4）

### Tailwind CSS技术审查
- [ ] Tailwind CDN正确引入
- [ ] 无构建工具依赖
- [ ] 样式类直接在HTML中使用
- [ ] 自定义配置正确设置
- [ ] 图片资源CDN引用
- [ ] 字体使用系统字体栈

### 性能优化
- [ ] Tailwind类名精简高效
- [ ] 动画使用transform和opacity
- [ ] 图表固定尺寸避免重排
- [ ] 避免不必要的响应式类
- [ ] 合理使用transition-all

## 🛠 开发工具

### Tailwind主题管理
```javascript
// 动态主题切换（如需深色主题）
function toggleTheme() {
    const html = document.documentElement;
    const isDark = html.classList.contains('dark');
    
    if (isDark) {
        html.classList.remove('dark');
        localStorage.setItem('theme', 'light');
    } else {
        html.classList.add('dark');
        localStorage.setItem('theme', 'dark');
    }
}

// 初始化主题
function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
        document.documentElement.classList.add('dark');
    }
}

// 在页面加载时初始化
document.addEventListener('DOMContentLoaded', initTheme);
```

### 桌面端工具函数
```javascript
// 桌面端专用工具类
class DesktopUtils {
    // 获取容器宽度（对应 max-w-6xl = 1152px）
    static getContainerWidth() {
        return Math.min(1152, window.innerWidth - 64); // 减去 px-8 的padding
    }
    
    // 计算网格列数（对应 grid-cols-* ）
    static getGridColumns(itemMinWidth, gap = 24) {
        const containerWidth = this.getContainerWidth();
        return Math.floor((containerWidth + gap) / (itemMinWidth + gap));
    }
    
    // 图表尺寸计算（对应固定图表尺寸）
    static getChartSize() {
        const containerWidth = this.getContainerWidth();
        const chartWidth = (containerWidth - 24) / 2; // 2列布局 gap-6
        return {
            width: Math.min(540, chartWidth),
            height: 280
        };
    }
    
    // 检查是否为桌面端（最小宽度）
    static isDesktop() {
        return window.innerWidth >= 1024; // lg breakpoint
    }
    
    // 动态添加/移除Tailwind类
    static toggleClass(element, className, condition) {
        if (condition) {
            element.classList.add(...className.split(' '));
        } else {
            element.classList.remove(...className.split(' '));
        }
    }
    
    // 批量设置Tailwind类
    static setClasses(element, classMap) {
        Object.entries(classMap).forEach(([condition, classes]) => {
            this.toggleClass(element, classes, condition);
        });
    }
}

// 使用示例
// DesktopUtils.toggleClass(element, 'bg-red-500 text-white', isError);
// DesktopUtils.setClasses(button, {
//     [isLoading]: 'opacity-50 cursor-not-allowed',
//     [isPrimary]: 'bg-indigo-500 text-white',
//     [isSecondary]: 'bg-white text-slate-700 border border-slate-300'
// });
```

### 完整HTML模板
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Qwen-3 本地监控 - 桌面端</title>
    
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        'ai-primary': '#667eea',
                        'ai-primary-light': '#8fa4f3',
                        'ai-primary-dark': '#4c63d2',
                    },
                    animation: {
                        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                        'shimmer': 'shimmer 1.5s infinite',
                    },
                    keyframes: {
                        shimmer: {
                            '0%': { transform: 'translateX(-100%)' },
                            '100%': { transform: 'translateX(100%)' }
                        }
                    }
                }
            }
        }
    </script>
    
    <!-- Plotly.js -->
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>
<body class="bg-slate-50 font-sans antialiased">
    <!-- 页面内容 -->
    <div class="max-w-6xl mx-auto px-8 py-6">
        <!-- 组件内容 -->
    </div>
    
    <!-- 工具函数 -->
    <script>
        // DesktopUtils 类定义...
    </script>
</body>
</html>
```

这个设计规范专注于桌面端，通过Tailwind CSS和纯HTML方案，创造出高性能、易维护、代码量更少的用户界面。