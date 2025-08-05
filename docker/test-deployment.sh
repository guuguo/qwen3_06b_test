#!/bin/bash
set -e

# Qwen3 Dashboard Docker部署测试脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 清理旧容器
cleanup() {
    log_info "清理旧的测试容器..."
    docker-compose -f "$PROJECT_DIR/docker-compose.yml" down -v 2>/dev/null || true
    docker rmi $(docker images | grep qwen3 | awk '{print $3}') 2>/dev/null || true
}

# 构建和启动
build_and_start() {
    log_info "构建Docker镜像..."
    cd "$PROJECT_DIR"
    
    if ! docker-compose build --no-cache; then
        log_error "Docker镜像构建失败"
        exit 1
    fi
    
    log_success "Docker镜像构建成功"
    
    log_info "启动服务..."
    if ! docker-compose up -d; then
        log_error "服务启动失败"
        exit 1
    fi
    
    log_success "服务启动成功"
}

# 等待服务就绪
wait_for_services() {
    log_info "等待服务就绪..."
    
    # 等待容器启动
    sleep 15
    
    # 检查容器状态
    if ! docker-compose ps | grep -q "Up"; then
        log_error "容器未正常启动"
        docker-compose logs
        exit 1
    fi
    
    # 等待Ollama服务
    log_info "等待Ollama服务..."
    for i in {1..30}; do
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            log_success "Ollama服务就绪"
            break
        fi
        
        if [ $i -eq 30 ]; then
            log_error "Ollama服务启动超时"
            docker-compose logs qwen3-dashboard
            exit 1
        fi
        
        sleep 2
    done
    
    # 等待Web服务
    log_info "等待Web服务..."
    for i in {1..30}; do
        if curl -s http://localhost:5000 > /dev/null 2>&1; then
            log_success "Web服务就绪"
            break
        fi
        
        if [ $i -eq 30 ]; then
            log_error "Web服务启动超时"
            docker-compose logs qwen3-dashboard
            exit 1
        fi
        
        sleep 2
    done
}

# 测试API功能
test_apis() {
    log_info "测试API功能..."
    
    # 测试健康检查
    if curl -f http://localhost:5001/health > /dev/null 2>&1; then
        log_success "健康检查API正常"
    else
        log_error "健康检查API失败"
        return 1
    fi
    
    # 测试Ollama API
    if curl -f http://localhost:11434/api/tags > /dev/null 2>&1; then
        log_success "Ollama API正常"
    else
        log_error "Ollama API失败"
        return 1
    fi
    
    # 测试Web界面
    if curl -f http://localhost:5000 > /dev/null 2>&1; then
        log_success "Web界面正常"
    else
        log_error "Web界面失败"
        return 1
    fi
    
    # 测试模型管理API
    if curl -f http://localhost:5000/api/ollama/models > /dev/null 2>&1; then
        log_success "模型管理API正常"
    else
        log_error "模型管理API失败"
        return 1
    fi
}

# 显示服务信息
show_service_info() {
    log_success "🎉 Qwen3 Dashboard 部署测试成功！"
    echo ""
    echo "🌐 服务访问地址:"
    echo "   Web管理界面: http://localhost:5000"
    echo "   Ollama API:  http://localhost:11434"
    echo "   健康检查:    http://localhost:5001/health"
    echo ""
    echo "📊 容器状态:"
    docker-compose ps
    echo ""
    echo "💾 资源使用:"
    docker stats --no-stream qwen3-dashboard
    echo ""
}

# 主测试流程
main() {
    echo "🧪 Qwen3 Dashboard Docker部署测试"
    echo "=================================="
    
    case "${1:-test}" in
        "test")
            cleanup
            build_and_start
            wait_for_services
            test_apis
            show_service_info
            ;;
        "cleanup")
            cleanup
            log_success "清理完成"
            ;;
        "logs")
            cd "$PROJECT_DIR"
            docker-compose logs -f
            ;;
        *)
            echo "用法: $0 {test|cleanup|logs}"
            exit 1
            ;;
    esac
}

main "$@"