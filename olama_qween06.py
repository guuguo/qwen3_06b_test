import requests
import json
from typing import List, Dict

def check_ad(comment):
    # 使用更简单直接的提示词策略
    prompt = (
        "请判断以下评论是否为广告。\n\n"
        "广告定义：同时包含联系方式+交易行为+价格信息的内容。\n\n"
        "示例：\n"
        "广告：'加微信123购买软件，只要99元' - 包含联系方式(微信123)+交易(购买)+价格(99元)\n"
        "非广告：'推荐Chrome浏览器' - 只是推荐，无联系方式、交易、价格\n"
        "非广告：'这个软件不错' - 只是评价，无联系方式、交易、价格\n\n"
        f"待判断：{comment}\n\n"
        "要求：只有同时包含【联系方式+交易行为+价格信息】才回答'是'，否则回答'否'。\n"
        "回答："
    )
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen3:0.6b",
                "prompt": prompt,
                "stream": False,
                "temperature": 0.0,  # 最大确定性
                "max_tokens": 3,   # 限制输出长度
                "stop": ["\n", "。", "，", " "]  # 设置停止符号
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if "response" in result:
                answer = result["response"].strip()
                # 清理答案，只保留是或否
                if "是" in answer:
                    return "是"
                elif "否" in answer:
                    return "否"
                else:
                    return "否"  # 默认保守判断
            else:
                return "否"
        else:
            return "否"
    except Exception as e:
        print(f"API调用错误: {e}")
        return "否"  # 出错时保守判断

def run_test_cases():
    """运行测试案例并分析结果"""
    test_cases = [
        # 明显广告案例
        {"comment": "加微信123456购买正版软件，限时8折优惠！", "expected": "是", "category": "明显广告"},
        {"comment": "联系QQ888888下载破解版，免费使用！", "expected": "是", "category": "明显广告"},
        {"comment": "点击链接www.xxx.com购买，现在只要99元！", "expected": "是", "category": "明显广告"},
        {"comment": "关注公众号领取免费资源，限量1000份", "expected": "是", "category": "明显广告"},
        
        # 边界案例 - 应该判否
        {"comment": "搜索喵趣漫画,比这个好", "expected": "否", "category": "产品提及"},
        {"comment": "推荐使用Chrome浏览器", "expected": "否", "category": "产品推荐"},
        {"comment": "我觉得iPhone比安卓好用", "expected": "否", "category": "个人观点"},
        {"comment": "这个软件不错，值得试试", "expected": "否", "category": "使用体验"},
        {"comment": "有没有好用的视频编辑软件推荐？", "expected": "否", "category": "求助询问"},
        
        # 模糊边界案例
        {"comment": "某宝上有卖的，搜索XXX就能找到", "expected": "否", "category": "模糊边界"},
        {"comment": "这个比XX软件好用多了", "expected": "否", "category": "比较评价"},
        {"comment": "试试看这个应用，挺不错的", "expected": "否", "category": "一般推荐"},
        
        # 潜在广告但不够明确
        {"comment": "需要的私信我", "expected": "否", "category": "潜在广告"},
        {"comment": "有兴趣的可以了解一下", "expected": "否", "category": "潜在广告"},
        
        # 正常评论
        {"comment": "这个功能很实用", "expected": "否", "category": "正常评论"},
        {"comment": "谢谢分享，学到了", "expected": "否", "category": "正常评论"},
        {"comment": "同意楼主的观点", "expected": "否", "category": "正常评论"},
    ]
    
    print("=" * 60)
    print("内容审核测试开始")
    print("=" * 60)
    
    correct = 0
    total = len(test_cases)
    results = []
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n测试案例 {i}/{total}:")
        print(f"评论: {case['comment']}")
        print(f"类别: {case['category']}")
        print(f"期望: {case['expected']}")
        
        actual = check_ad(case['comment'])
        print(f"实际: {actual}")
        
        is_correct = actual == case['expected']
        status = "✓" if is_correct else "✗"
        print(f"结果: {status}")
        
        if is_correct:
            correct += 1
        
        results.append({
            'case': case,
            'actual': actual,
            'correct': is_correct
        })
    
    # 统计结果
    accuracy = correct / total * 100
    print("\n" + "=" * 60)
    print(f"测试完成！准确率: {correct}/{total} ({accuracy:.1f}%)")
    print("=" * 60)
    
    # 分析错误案例
    errors = [r for r in results if not r['correct']]
    if errors:
        print("\n错误案例分析:")
        for error in errors:
            case = error['case']
            print(f"- [{case['category']}] {case['comment']}")
            print(f"  期望: {case['expected']}, 实际: {error['actual']}")
    
    # 按类别统计
    category_stats = {}
    for result in results:
        category = result['case']['category']
        if category not in category_stats:
            category_stats[category] = {'total': 0, 'correct': 0}
        category_stats[category]['total'] += 1
        if result['correct']:
            category_stats[category]['correct'] += 1
    
    print("\n按类别统计:")
    for category, stats in category_stats.items():
        acc = stats['correct'] / stats['total'] * 100
        print(f"- {category}: {stats['correct']}/{stats['total']} ({acc:.1f}%)")
    
    return accuracy, results

if __name__ == "__main__":
    # 运行测试
    accuracy, results = run_test_cases()
    
    # 如果准确率不够高，可以根据结果进一步优化提示词
    if accuracy < 90:
        print(f"\n⚠️  准确率 {accuracy:.1f}% 偏低，建议优化提示词")
    else:
        print(f"\n✅ 准确率 {accuracy:.1f}% 表现良好")