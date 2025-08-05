#!/bin/bash

# Ollama K8s 一键部署脚本
# 支持构建镜像、部署到 K8s 集群、暴露服务

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="ollama-qwen"
IMAGE_TAG="latest"
NAMESPACE="ollama-system"
REGISTRY=""  # 留空使用本地镜像，或设置为 your-registry.com/

# 帮助信息
show_help() {
    echo "Ollama K8s 部署脚本"
    echo ""
    echo "用法: $0 [选项] [命令]"
    echo ""
    echo "命令:"
    echo "  build       构建 Docker 镜像"
    echo "  deploy      部署到 K8s 集群"
    echo "  undeploy    从 K8s 集群删除"
    echo "  status      查看部署状态"
    echo "  logs        查看服务日志"
    echo "  test        测试服务"
    echo "  all         执行 build + deploy"
    echo ""
    echo "选项:"
    echo "  -r, --registry REGISTRY   Docker 镜像仓库前缀"
    echo "  -t, --tag TAG             镜像标签 (默认: latest)"
    echo "  -n, --namespace NS        K8s 命名空间 (默认: ollama-system)"
    echo "  -h, --help                显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 all                    # 构建并部署"
    echo "  $0 build                  # 只构建镜像"
    echo "  $0 deploy                 # 只部署到 K8s"
    echo "  $0 -r myregistry.com build # 构建并推送到仓库"
}

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    local missing_deps=()
    
    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi
    
    if ! command -v kubectl &> /dev/null; then
        missing_deps+=("kubectl")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "缺少依赖: ${missing_deps[*]}"
        log_error "请先安装所需依赖"
        exit 1
    fi
    
    # 检查 Docker 是否运行
    if ! docker info &> /dev/null; then
        log_error "Docker 服务未运行，请启动 Docker"
        exit 1
    fi
    
    # 检查 kubectl 是否可以连接集群
    if ! kubectl cluster-info &> /dev/null; then
        log_error "无法连接到 K8s 集群，请检查 kubectl 配置"
        exit 1
    fi
    
    log_success "依赖检查通过"
}

# 构建 Docker 镜像
build_image() {
    log_info "开始构建 Docker 镜像..."
    
    local full_image_name="${REGISTRY}${IMAGE_NAME}:${IMAGE_TAG}"
    
    # 构建镜像
    log_info "构建镜像: ${full_image_name}"
    docker build -t "${full_image_name}" "${SCRIPT_DIR}"
    
    # 如果指定了仓库，推送镜像
    if [ -n "${REGISTRY}" ]; then
        log_info "推送镜像到仓库: ${full_image_name}"
        docker push "${full_image_name}"
    fi
    
    log_success "镜像构建完成: ${full_image_name}"
}

# 部署到 K8s
deploy_k8s() {
    log_info "开始部署到 K8s 集群..."
    
    local full_image_name="${REGISTRY}${IMAGE_NAME}:${IMAGE_TAG}"
    
    # 创建临时部署文件
    local temp_dir=$(mktemp -d)
    cp "${SCRIPT_DIR}"/*.yaml "${temp_dir}/"
    
    # 替换镜像名称
    sed -i.bak "s|ollama-qwen:latest|${full_image_name}|g" "${temp_dir}/deployment.yaml"
    
    # 应用 K8s 配置
    log_info "创建命名空间..."
    kubectl apply -f "${temp_dir}/namespace.yaml"
    
    log_info "应用配置..."
    kubectl apply -f "${temp_dir}/configmap.yaml"
    kubectl apply -f "${temp_dir}/storage.yaml"
    
    log_info "部署应用..."
    kubectl apply -f "${temp_dir}/deployment.yaml"
    kubectl apply -f "${temp_dir}/service.yaml"
    
    # 等待部署完成
    log_info "等待部署完成..."
    kubectl rollout status deployment/ollama-deployment -n "${NAMESPACE}" --timeout=600s
    
    # 清理临时文件
    rm -rf "${temp_dir}"
    
    log_success "部署完成"
    
    # 显示访问信息
    show_access_info
}

# 删除部署
undeploy_k8s() {
    log_info "开始删除 K8s 部署..."
    
    if kubectl get namespace "${NAMESPACE}" &> /dev/null; then
        kubectl delete namespace "${NAMESPACE}"
        log_success "命名空间 ${NAMESPACE} 已删除"
    else
        log_warning "命名空间 ${NAMESPACE} 不存在"
    fi
}

# 查看状态
show_status() {
    log_info "查看部署状态..."
    
    if ! kubectl get namespace "${NAMESPACE}" &> /dev/null; then
        log_warning "命名空间 ${NAMESPACE} 不存在"
        return 1
    fi
    
    echo ""
    echo "=== 命名空间状态 ==="
    kubectl get all -n "${NAMESPACE}"
    
    echo ""
    echo "=== Pod 详细状态 ==="
    kubectl get pods -n "${NAMESPACE}" -o wide
    
    echo ""
    echo "=== 服务状态 ==="
    kubectl get svc -n "${NAMESPACE}"
    
    echo ""
    echo "=== 存储状态 ==="
    kubectl get pvc -n "${NAMESPACE}"
}

# 查看日志
show_logs() {
    log_info "查看服务日志..."
    
    local pod_name=$(kubectl get pods -n "${NAMESPACE}" -l app=ollama -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [ -z "${pod_name}" ]; then
        log_error "未找到运行中的 Pod"
        return 1
    fi
    
    log_info "显示 Pod ${pod_name} 的日志..."
    kubectl logs -n "${NAMESPACE}" "${pod_name}" -f
}

# 测试服务
test_service() {
    log_info "测试 Ollama 服务..."
    
    # 获取服务端点
    local nodeport=$(kubectl get svc ollama-nodeport -n "${NAMESPACE}" -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null)
    local cluster_ip=$(kubectl get svc ollama-service -n "${NAMESPACE}" -o jsonpath='{.spec.clusterIP}' 2>/dev/null)
    
    if [ -z "${nodeport}" ] || [ -z "${cluster_ip}" ]; then
        log_error "无法获取服务信息"
        return 1
    fi
    
    # 通过 kubectl port-forward 测试
    log_info "通过端口转发测试服务..."
    kubectl port-forward -n "${NAMESPACE}" svc/ollama-service 11434:11434 &
    local port_forward_pid=$!
    
    sleep 5
    
    # 测试 API
    if curl -s http://localhost:11434/api/tags > /dev/null; then
        log_success "服务响应正常"
        
        # 测试模型推理
        log_info "测试模型推理..."
        local response=$(curl -s -X POST http://localhost:11434/api/generate \
            -H "Content-Type: application/json" \
            -d '{"model": "qwen3:0.6b", "prompt": "Hello", "stream": false}' | jq -r '.response' 2>/dev/null)
        
        if [ -n "${response}" ] && [ "${response}" != "null" ]; then
            log_success "模型推理测试通过"
            echo "响应: ${response}"
        else
            log_warning "模型推理测试失败"
        fi
    else
        log_error "服务无响应"
    fi
    
    # 清理端口转发
    kill ${port_forward_pid} 2>/dev/null || true
}

# 显示访问信息
show_access_info() {
    log_info "获取访问信息..."
    
    local nodeport=$(kubectl get svc ollama-nodeport -n "${NAMESPACE}" -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null)
    local nodes=$(kubectl get nodes -o jsonpath='{.items[*].status.addresses[?(@.type=="ExternalIP")].address}' 2>/dev/null)
    
    if [ -z "${nodes}" ]; then
        nodes=$(kubectl get nodes -o jsonpath='{.items[*].status.addresses[?(@.type=="InternalIP")].address}' 2>/dev/null)
    fi
    
    echo ""
    echo "=== 访问信息 ==="
    echo "内部访问: http://ollama-service.${NAMESPACE}.svc.cluster.local:11434"
    
    if [ -n "${nodeport}" ] && [ -n "${nodes}" ]; then
        echo "外部访问: http://<NODE_IP>:${nodeport}"
        echo "节点 IP: ${nodes}"
    fi
    
    echo ""
    echo "=== 端口转发命令 ==="
    echo "kubectl port-forward -n ${NAMESPACE} svc/ollama-service 11434:11434"
    echo "然后访问: http://localhost:11434"
    
    echo ""
    echo "=== API 测试命令 ==="
    echo "curl http://localhost:11434/api/tags"
    echo "curl -X POST http://localhost:11434/api/generate -H 'Content-Type: application/json' -d '{\"model\": \"qwen3:0.6b\", \"prompt\": \"Hello\", \"stream\": false}'"
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--registry)
            REGISTRY="$2/"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        build|deploy|undeploy|status|logs|test|all)
            COMMAND="$1"
            shift
            ;;
        *)
            log_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 如果没有指定命令，显示帮助
if [ -z "${COMMAND}" ]; then
    show_help
    exit 1
fi

# 执行命令
case "${COMMAND}" in
    build)
        check_dependencies
        build_image
        ;;
    deploy)
        check_dependencies
        deploy_k8s
        ;;
    undeploy)
        check_dependencies
        undeploy_k8s
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    test)
        test_service
        ;;
    all)
        check_dependencies
        build_image
        deploy_k8s
        test_service
        ;;
    *)
        log_error "未知命令: ${COMMAND}"
        show_help
        exit 1
        ;;
esac

log_success "操作完成"