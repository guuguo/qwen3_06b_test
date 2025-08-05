# 提示词管理系统 (Markdown版)

## 📁 目录结构

```
prompts/
├── md_prompts/              # MD配置文件目录
│   ├── 漫画评论广告检测.md      # 漫画广告检测配置
│   ├── 通话语义投诉分类.md      # 通话投诉分类配置
│   └── 通用内容分析.md          # 通用分析配置
├── md_manager.py            # MD提示词管理器
├── test_md_system.py        # 系统测试脚本
├── MD_PROMPT_GUIDE.md       # 详细使用指南
└── README.md               # 本文档
```

## 🚀 快速开始

### 1. 使用现有配置
```python
from md_manager import get_md_prompt_manager

manager = get_md_prompt_manager()
prompt = manager.render_prompt('manga_comment_ad_detection_simple', {
    'content': '这个漫画真不错！'
})
```

### 2. 添加新配置
在 `md_prompts/` 目录创建新的 `.md` 文件，参考现有文件格式。

### 3. 测试系统
```bash
python test_md_system.py
```

## ✨ 主要优势

- ✅ **零学习成本** - 只需会写Markdown
- ✅ **自然语言配置** - 用中文描述规则和要求
- ✅ **多格式支持** - 同时支持JSON和简化输出格式
- ✅ **自动质量检查** - 内置响应格式验证
- ✅ **完善的容错机制** - 多层备选确保系统稳定

详细使用方法请参考 `MD_PROMPT_GUIDE.md`。