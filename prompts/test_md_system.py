#!/usr/bin/env python3
"""
测试MD提示词管理系统
"""

import sys
from pathlib import Path

# 添加路径
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from md_manager import get_md_prompt_manager

def test_basic_functionality():
    """测试基本功能"""
    print("=== 测试MD提示词管理系统 ===\n")
    
    # 获取管理器
    manager = get_md_prompt_manager()
    
    # 1. 测试获取可用数据集
    print("1. 可用数据集:")
    datasets = manager.get_available_datasets()
    for dataset in datasets:
        print(f"   - {dataset['display_name']} ({dataset['name']})")
        print(f"     模型类型: {dataset['model_type']}")
        print(f"     版本: {dataset['version']}")
    print()
    
    # 2. 测试提示词渲染
    print("2. 提示词渲染测试:")
    
    # 测试数据
    sample_data = {
        'content': '这个漫画太好看了！强烈推荐大家去看！',
        'category': '正常评论',
        'expected_score': 0
    }
    
    # 渲染提示词
    prompt = manager.render_prompt('manga_comment_ad_detection_simple', sample_data)
    print("生成的提示词:")
    print("-" * 50)
    print(prompt)
    print("-" * 50)
    print()
    
    # 3. 测试响应解析
    print("3. 响应解析测试:")
    
    test_responses = [
        # 简化格式
        """评分：0
类别：正常评论  
理由：表达对漫画的喜爱，无广告特征""",
        
        # JSON格式
        '{"ad_score": 0, "category": "正常评论", "analysis": "正常的漫画讨论"}',
        
        # 格式错误的响应
        "这是一个正常的评论，评分0分"
    ]
    
    for i, response in enumerate(test_responses, 1):
        print(f"响应 {i}:")
        print(f"原始: {response}")
        
        parsed = manager.parse_response('manga_comment_ad_detection_simple', response)
        print(f"解析结果: {parsed}")
        
        # 验证质量
        errors = manager.validate_response('manga_comment_ad_detection_simple', response)
        if errors:
            print(f"质量检查错误: {errors}")
        else:
            print("质量检查: 通过")
        print()
    
    # 4. 测试通话投诉分类
    print("4. 通话投诉分类测试:")
    
    complaint_data = {
        'content': '你们的服务态度太差了！等了半天都没人理我！我要投诉！',
        'category': '态度问题',
        'expected_score': 4
    }
    
    complaint_prompt = manager.render_prompt('call_semantic_complaints_simple', complaint_data)
    print("通话投诉提示词:")
    print("-" * 50)
    print(complaint_prompt)
    print("-" * 50)

def test_error_handling():
    """测试错误处理"""
    print("\n=== 错误处理测试 ===\n")
    
    manager = get_md_prompt_manager()
    
    # 测试不存在的数据集
    print("1. 不存在的数据集:")
    prompt = manager.render_prompt('nonexistent_dataset', {'content': 'test'})
    print(f"备用提示词: {prompt[:100]}...")
    print()
    
    # 测试空数据
    print("2. 空数据:")
    prompt = manager.render_prompt('manga_comment_ad_detection_simple', {})
    print(f"空数据提示词: {prompt[:100]}...")
    print()

if __name__ == "__main__":
    test_basic_functionality()
    test_error_handling()
    print("✅ MD提示词管理系统测试完成!")