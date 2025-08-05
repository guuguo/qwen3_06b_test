"""
基于Markdown的提示词管理器
支持自然语言配置格式，更简单易用
"""

import os
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging


class MarkdownPromptManager:
    """基于Markdown的提示词管理器"""
    
    def __init__(self, prompts_dir: Optional[str] = None):
        """
        初始化管理器
        
        Args:
            prompts_dir: MD提示词目录路径
        """
        if prompts_dir is None:
            current_dir = Path(__file__).parent
            prompts_dir = current_dir / "md_prompts"
        
        self.prompts_dir = Path(prompts_dir)
        self.logger = logging.getLogger(__name__)
        
        # 缓存
        self._cache = {}
        
        # 数据集ID映射（文件名 -> 数据集ID）
        self._dataset_mapping = self._build_dataset_mapping()
    
    def _build_dataset_mapping(self) -> Dict[str, str]:
        """构建数据集文件名到ID的映射"""
        mapping = {}
        
        if not self.prompts_dir.exists():
            self.logger.warning(f"提示词目录不存在: {self.prompts_dir}")
            return mapping
        
        for md_file in self.prompts_dir.glob("*.md"):
            try:
                config = self._parse_md_file(md_file)
                dataset_id = config.get('dataset_id')
                if dataset_id:
                    # 支持多个数据集ID（列表或单个字符串）
                    if isinstance(dataset_id, list):
                        for id in dataset_id:
                            mapping[id] = md_file.stem
                            self.logger.debug(f"映射: {id} -> {md_file.stem}")
                    else:
                        mapping[dataset_id] = md_file.stem
                        self.logger.debug(f"映射: {dataset_id} -> {md_file.stem}")
            except Exception as e:
                self.logger.warning(f"解析文件失败 {md_file}: {str(e)}")
        
        return mapping
    
    def _parse_md_file(self, md_file: Path) -> Dict[str, Any]:
        """解析MD提示词文件"""
        if md_file in self._cache:
            return self._cache[md_file]
        
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        config = {
            'title': '',
            'dataset_id': '',
            'version': '1.0',
            'model_type': '通用版',
            'output_format': '自由格式',
            'description': '',
            'categories': [],
            'prompt_template': '',
            'examples': [],
            'quality_rules': [],
            'keywords': {}
        }
        
        # 解析标题
        title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
        if title_match:
            config['title'] = title_match.group(1).strip()
        
        # 解析配置信息部分
        config_section = self._extract_section(content, "配置信息")
        if config_section:
            config.update(self._parse_config_section(config_section))
        
        # 解析类别定义
        categories_section = self._extract_section(content, "类别定义")
        if categories_section:
            config['categories'] = self._parse_categories(categories_section)
        
        # 解析提示词模板
        prompt_section = self._extract_section(content, "提示词模板")
        if prompt_section:
            config['prompt_template'] = prompt_section.strip()
        
        # 解析示例输出
        examples_section = self._extract_section(content, "示例输出")
        if examples_section:
            config['examples'] = self._parse_examples(examples_section)
        
        # 解析质量检查规则
        quality_section = self._extract_section(content, "质量检查规则")
        if quality_section:
            config['quality_rules'] = self._parse_quality_rules(quality_section)
        
        # 解析关键词
        keywords_section = self._extract_section(content, "常见关键词参考") or self._extract_section(content, "投诉识别关键词")
        if keywords_section:
            config['keywords'] = self._parse_keywords(keywords_section)
        
        self._cache[md_file] = config
        return config
    
    def _extract_section(self, content: str, section_name: str) -> Optional[str]:
        """提取MD文件中的特定章节内容"""
        # 匹配 ## 章节名 到下一个 ## 之间的内容
        pattern = rf'^## {re.escape(section_name)}\s*\n(.*?)(?=^## |\Z)'
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
        
        if match:
            return match.group(1).strip()
        return None
    
    def _parse_config_section(self, config_text: str) -> Dict[str, str]:
        """解析配置信息部分"""
        config = {}
        lines = config_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('- '):
                # 解析 "- 键：值" 格式
                match = re.match(r'- (.+?)：(.+)', line)
                if match:
                    key, value = match.groups()
                    key = key.strip()
                    value = value.strip()
                    
                    # 映射中文字段名到英文
                    key_mapping = {
                        '数据集ID': 'dataset_id',
                        '版本': 'version',
                        '适用模型': 'model_type',
                        '输出格式': 'output_format',
                        '更新时间': 'update_time'
                    }
                    
                    eng_key = key_mapping.get(key, key.lower().replace(' ', '_'))
                    # 处理多个数据集ID（用逗号分隔）
                    if eng_key == 'dataset_id' and ',' in value:
                        config[eng_key] = [id.strip() for id in value.split(',')]
                    else:
                        config[eng_key] = value
        
        return config
    
    def _parse_categories(self, categories_text: str) -> List[Dict[str, str]]:
        """解析类别定义"""
        categories = []
        lines = categories_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('- **') and '**：' in line:
                # 解析 "- **类别名**：描述" 格式
                match = re.match(r'- \*\*(.+?)\*\*：(.+)', line)
                if match:
                    name, description = match.groups()
                    categories.append({
                        'name': name.strip(),
                        'description': description.strip()
                    })
        
        return categories
    
    def _parse_examples(self, examples_text: str) -> List[Dict[str, str]]:
        """解析示例输出"""
        examples = []
        
        # 提取所有代码块中的示例
        code_blocks = re.findall(r'```\n(.*?)\n```', examples_text, re.DOTALL)
        
        for i, block in enumerate(code_blocks):
            examples.append({
                'name': f'示例{i+1}',
                'output': block.strip()
            })
        
        return examples
    
    def _parse_quality_rules(self, quality_text: str) -> List[str]:
        """解析质量检查规则"""
        rules = []
        lines = quality_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if re.match(r'^\d+\.', line):
                # 提取编号列表项
                rule = re.sub(r'^\d+\.\s*', '', line)
                rules.append(rule)
        
        return rules
    
    def _parse_keywords(self, keywords_text: str) -> Dict[str, List[str]]:
        """解析关键词部分"""
        keywords = {}
        lines = keywords_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('- **') and '**：' in line:
                # 解析 "- **类型**：关键词1、关键词2" 格式
                match = re.match(r'- \*\*(.+?)\*\*：(.+)', line)
                if match:
                    category, words_str = match.groups()
                    words = [w.strip() for w in words_str.split('、')]
                    keywords[category.strip()] = words
        
        return keywords
    
    def get_dataset_by_name(self, dataset_name: str) -> Optional[str]:
        """根据数据集名称获取对应的MD文件名"""
        # 直接匹配数据集ID
        if dataset_name in self._dataset_mapping:
            return self._dataset_mapping[dataset_name]
        
        # 模糊匹配文件名
        for dataset_id, file_name in self._dataset_mapping.items():
            if dataset_name in dataset_id or dataset_id in dataset_name:
                return file_name
        
        return None
    
    def render_prompt_from_file(self, template_filename: str, sample_data: Dict[str, Any]) -> str:
        """
        根据指定的文件名渲染提示词，绕过所有复杂的查找逻辑。
        """
        try:
            md_file = self.prompts_dir / template_filename
            if not md_file.exists():
                self.logger.error(f"指定的提示词文件不存在: {md_file}")
                return self._fallback_prompt(sample_data)

            # 解析文件（会使用缓存）
            config = self._parse_md_file(md_file)
            prompt_template = config.get('prompt_template')

            if not prompt_template:
                # 尝试从文件根部查找模板
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 寻找模型指令
                match = re.search(r'## --- 模型指令 \(从此开始\) ---(.*)--- 任务开始 ---', content, re.DOTALL)
                if match:
                    prompt_template = match.group(1).strip()
                else: # 如果找不到，就用整个文件
                    prompt_template = content

            if not prompt_template:
                 return self._fallback_prompt(sample_data)

            # 变量替换
            return self._replace_variables(prompt_template, sample_data)

        except Exception as e:
            self.logger.error(f"从文件渲染提示词失败 '{template_filename}': {e}")
            return self._fallback_prompt(sample_data)
    
    def _find_md_file(self, dataset_name: str) -> Optional[Path]:
        """查找对应的MD文件"""
        # 使用映射直接查找
        file_name = self.get_dataset_by_name(dataset_name)
        if file_name:
            md_file = self.prompts_dir / f"{file_name}.md"
            if md_file.exists():
                return md_file
        
        # 备用：遍历所有文件匹配数据集ID
        for md_file in self.prompts_dir.glob("*.md"):
            try:
                config = self._parse_md_file(md_file)
                dataset_id = config.get('dataset_id')
                if isinstance(dataset_id, list):
                    if dataset_name in dataset_id:
                        return md_file
                elif dataset_id == dataset_name:
                    return md_file
            except:
                continue
        
        # 文件名匹配
        possible_names = [
            f"{dataset_name}.md",
            dataset_name.replace('_simple', '') + '.md',
            dataset_name.replace('_', '') + '.md'
        ]
        
        for name in possible_names:
            md_file = self.prompts_dir / name
            if md_file.exists():
                return md_file
        
        # 模糊匹配
        for md_file in self.prompts_dir.glob("*.md"):
            if dataset_name in md_file.stem or md_file.stem in dataset_name:
                return md_file
        
        return None
    
    def _replace_variables(self, template: str, data: Dict[str, Any]) -> str:
        """替换模板中的变量"""
        result = template
        
        # 标准变量映射
        variable_mapping = {
            'content': str(data.get('content', '')),
            'expected_category': str(data.get('category', '')),
            'expected_score': str(data.get('expected_score', ''))
        }
        
        # 执行替换
        for var_name, var_value in variable_mapping.items():
            pattern = r'\{' + re.escape(var_name) + r'\}'
            result = re.sub(pattern, var_value, result)
        
        return result
    
    def _fallback_prompt(self, sample_data: Dict[str, Any]) -> str:
        """备用提示词"""
        return f"""请分析以下内容：

内容：{sample_data.get('content', '')}

预期类别：{sample_data.get('category', '')}
预期评分：{sample_data.get('expected_score', '')}

请提供你的分析结果。"""
    
    def validate_response(self, dataset_name: str, response: str) -> List[str]:
        """
        验证响应质量
        
        Args:
            dataset_name: 数据集名称
            response: 模型响应
            
        Returns:
            错误信息列表
        """
        try:
            md_file = self._find_md_file(dataset_name)
            if not md_file:
                return []  # 无配置文件时不验证
            
            config = self._parse_md_file(md_file)
            rules = config.get('quality_rules', [])
            
            errors = []
            
            for rule in rules:
                error = self._check_rule(rule, response)
                if error:
                    errors.append(error)
            
            return errors
            
        except Exception as e:
            self.logger.error(f"响应验证失败: {str(e)}")
            return []
    
    def _check_rule(self, rule: str, response: str) -> Optional[str]:
        """检查单个质量规则"""
        response = response.strip()
        
        # 解析规则类型
        if "包含" in rule and "部分" in rule:
            # 检查是否包含必要部分
            required_parts = re.findall(r'"([^"]+)"', rule)
            for part in required_parts:
                if part not in response:
                    return f"缺少必要部分: {part}"
        
        elif "必须是" in rule and "之间的整数" in rule:
            # 检查数值范围
            range_match = re.search(r'(\d+)-(\d+)', rule)
            if range_match:
                min_val, max_val = map(int, range_match.groups())
                # 提取响应中的数字
                numbers = re.findall(r'(\d+)', response)
                if numbers:
                    try:
                        num = int(numbers[0])
                        if not (min_val <= num <= max_val):
                            return f"数值 {num} 不在 {min_val}-{max_val} 范围内"
                    except ValueError:
                        return f"无法解析数值"
                else:
                    return "未找到数值"
        
        elif "不少于" in rule and "字符" in rule:
            # 检查长度
            length_match = re.search(r'(\d+)', rule)
            if length_match:
                min_length = int(length_match.group(1))
                if len(response) < min_length:
                    return f"内容长度 {len(response)} 少于要求的 {min_length} 字符"
        
        return None
    
    def parse_response(self, dataset_name: str, response: str) -> Optional[Dict[str, Any]]:
        """
        解析模型响应
        
        Args:
            dataset_name: 数据集名称  
            response: 模型响应
            
        Returns:
            解析后的结构化数据
        """
        try:
            # 优先尝试JSON解析
            import json
            try:
                return json.loads(response.strip())
            except json.JSONDecodeError:
                pass
            
            # 尝试简化格式解析
            return self._parse_simple_format(response)
            
        except Exception as e:
            self.logger.error(f"响应解析失败: {str(e)}")
            return None
    
    def _parse_simple_format(self, response: str) -> Dict[str, Any]:
        """解析简化格式响应"""
        result = {}
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if '：' in line:
                key, value = line.split('：', 1)
                key = key.strip()
                value = value.strip()
                
                # 标准化字段名
                key_mapping = {
                    '评分': 'ad_score',
                    '类别': 'category',
                    '理由': 'analysis',
                    '严重度': 'severity_score',
                    '说明': 'analysis'
                }
                
                field_name = key_mapping.get(key, key.lower())
                
                # 尝试转换数字
                if field_name in ['ad_score', 'severity_score', 'score']:
                    try:
                        result[field_name] = int(value)
                    except ValueError:
                        result[field_name] = value
                else:
                    result[field_name] = value
        
        return result
    
    def get_available_datasets(self) -> List[Dict[str, str]]:
        """获取所有可用的数据集"""
        datasets = []
        
        for md_file in self.prompts_dir.glob("*.md"):
            try:
                config = self._parse_md_file(md_file)
                datasets.append({
                    'name': config.get('dataset_id', md_file.stem),
                    'display_name': config.get('title', md_file.stem),
                    'description': config.get('description', ''),
                    'version': config.get('version', '1.0'),
                    'model_type': config.get('model_type', '通用版')
                })
            except Exception as e:
                self.logger.warning(f"解析数据集失败 {md_file}: {str(e)}")
        
        return datasets


# 单例实例
_md_prompt_manager = None

def get_md_prompt_manager() -> MarkdownPromptManager:
    """获取MD提示词管理器单例"""
    global _md_prompt_manager
    if _md_prompt_manager is None:
        _md_prompt_manager = MarkdownPromptManager()
    return _md_prompt_manager