#!/bin/bash

# 环境检查脚本
# 检查 K8s 集群和系统环境是否满足部署要求

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "🔍 检查 Ollama K8s 部署环境..."
echo ""

# 检查结果
CHECKS_PASSED=0
CHECKS_TOTAL=0

check_command() {
    local cmd=$1
    local desc=$2
    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    
    if command -v "$cmd" &> /dev/null; then
        echo -e "${GREEN}✅${NC} $desc"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
        return 0
    else
        echo -e "${RED}❌${NC} $desc"
        return 1
    fi
}

check_service() {
    local cmd="$1"
    local desc="$2"
    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    
    if eval "$cmd" &> /dev/null; then
        echo -e "${GREEN}✅${NC} $desc"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
        return 0
    else
        echo -e "${RED}❌${NC} $desc"
        return 1
    fi
}

check_resource() {
    local resource_type="$1"
    local min_value="$2"
    local desc="$3"
    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    
    local available
    case "$resource_type" in
        "memory")
            available=$(kubectl top nodes --no-headers 2>/dev/null | awk '{sum+=$5} END {print sum}' | sed 's/Mi//')
            ;;
        "cpu")
            available=$(kubectl top nodes --no-headers 2>/dev/null | awk '{sum+=$3} END {print sum}' | sed 's/m//')
            ;;
        *)
            echo -e "${YELLOW}⚠️${NC} 未知资源类型: $resource_type"
            return 1
            ;;
    esac
    
    if [ -n "$available" ] && [ "$available" -ge "$min_value" ]; then
        echo -e "${GREEN}✅${NC} $desc (可用: ${available})"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
        return 0
    else
        echo -e "${YELLOW}⚠️${NC} $desc (可用: ${available:-未知}, 需要: $min_value)"
        return 1
    fi
}

echo "=== 基础工具检查 ==="
check_command "docker" "Docker 已安装"
check_command "kubectl" "kubectl 已安装"
check_command "curl" "curl 已安装"
check_command "jq" "jq 已安装 (可选)"

echo ""
echo "=== 服务状态检查 ==="
check_service "docker info" "Docker 服务运行中"
check_service "kubectl cluster-info" "K8s 集群连接正常"

echo ""
echo "=== K8s 集群信息 ==="
echo -n "集群版本: "
kubectl version --short --client 2>/dev/null | grep Client || echo "未知"
echo -n "服务器版本: "
kubectl version --short 2>/dev/null | grep Server || echo "未知"

echo -n "节点数量: "
kubectl get nodes --no-headers 2>/dev/null | wc -l || echo "0"

echo "节点状态:"
kubectl get nodes 2>/dev/null || echo "无法获取节点信息"

echo ""
echo "=== 存储类检查 ==="
STORAGE_CLASSES=$(kubectl get storageclass --no-headers 2>/dev/null | wc -l)
if [ "$STORAGE_CLASSES" -gt 0 ]; then
    echo -e "${GREEN}✅${NC} 存储类可用 ($STORAGE_CLASSES 个)"
    kubectl get storageclass 2>/dev/null
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${YELLOW}⚠️${NC} 未找到存储类，可能影响 PVC 创建"
fi
CHECKS_TOTAL=$((CHECKS_TOTAL + 1))

echo ""
echo "=== 资源检查 ==="
if kubectl top nodes &>/dev/null; then
    check_resource "memory" "2000" "内存充足 (需要 2GB+)"
    check_resource "cpu" "1000" "CPU 充足 (需要 1 core+)"
else
    echo -e "${YELLOW}⚠️${NC} 无法获取节点资源使用情况 (metrics-server 可能未安装)"
    CHECKS_TOTAL=$((CHECKS_TOTAL + 2))
fi

echo ""
echo "=== 网络检查 ==="
CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if curl -s --max-time 10 https://ollama.com > /dev/null; then
    echo -e "${GREEN}✅${NC} 网络连接正常 (可访问 Ollama 官网)"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${YELLOW}⚠️${NC} 网络连接可能有问题，可能影响模型下载"
fi

echo ""
echo "=== 权限检查 ==="
CHECKS_TOTAL=$((CHECKS_TOTAL + 2))

# 检查是否可以创建命名空间
if kubectl auth can-i create namespaces &>/dev/null; then
    echo -e "${GREEN}✅${NC} 有创建命名空间权限"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${RED}❌${NC} 无创建命名空间权限"
fi

# 检查是否可以创建 Deployment
if kubectl auth can-i create deployments &>/dev/null; then
    echo -e "${GREEN}✅${NC} 有创建 Deployment 权限"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${RED}❌${NC} 无创建 Deployment 权限"
fi

echo ""
echo "=== 检查结果 ==="
echo "通过检查: $CHECKS_PASSED/$CHECKS_TOTAL"

if [ "$CHECKS_PASSED" -eq "$CHECKS_TOTAL" ]; then
    echo -e "${GREEN}🎉 环境检查全部通过，可以开始部署！${NC}"
    echo ""
    echo "建议的下一步:"
    echo "1. 运行快速部署: ./quick-start.sh"
    echo "2. 或手动部署: ./deploy.sh all"
    exit 0
elif [ "$CHECKS_PASSED" -ge $((CHECKS_TOTAL * 3 / 4)) ]; then
    echo -e "${YELLOW}⚠️ 大部分检查通过，可以尝试部署，但可能遇到问题${NC}"
    echo ""
    echo "建议:"
    echo "1. 解决上述警告项目"
    echo "2. 运行部署: ./deploy.sh all"
    exit 1
else
    echo -e "${RED}❌ 环境检查失败，请解决上述问题后再部署${NC}"
    echo ""
    echo "常见解决方案:"
    echo "1. 安装 Docker: https://docs.docker.com/get-docker/"
    echo "2. 安装 kubectl: https://kubernetes.io/docs/tasks/tools/"
    echo "3. 配置 K8s 集群访问"
    echo "4. 检查集群资源是否充足"
    exit 2
fi