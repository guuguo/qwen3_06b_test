#!/usr/bin/env python3
import requests
import time
import json

def test_ollama_performance():
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "qwen3:0.6b",
        "prompt": "Hi",
        "stream": False
    }
    
    print("🚀 测试Ollama API性能...")
    start_time = time.time()
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"⏱️  响应时间: {duration:.2f}秒")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 请求成功")
            print(f"📝 响应内容: {result.get('response', '无响应')[:50]}...")
            print(f"📊 响应长度: {len(result.get('response', ''))}")
        else:
            print(f"❌ 请求失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text[:200]}")
            
    except requests.Timeout:
        print("⏰ 请求超时 (>60秒)")
    except requests.RequestException as e:
        print(f"❌ 请求错误: {e}")
    except Exception as e:
        print(f"❌ 其他错误: {e}")

if __name__ == "__main__":
    test_ollama_performance()