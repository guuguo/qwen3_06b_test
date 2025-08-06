#!/bin/bash
set -e

# Qwen3 Dashboard Docker 部署脚本
# 支持CPU优化的单容器部署

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 检查系统要求
check_requirements() {
    log_info "检查系统要求..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    # 检查Docker Compose（优先使用新版本命令）
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    elif command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
    else
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    # 检查系统资源（兼容macOS和Linux）
    if command -v nproc >/dev/null 2>&1; then
        CPU_CORES=$(nproc)
    else
        CPU_CORES=$(sysctl -n hw.ncpu 2>/dev/null || echo "4")
    fi
    
    if command -v free >/dev/null 2>&1; then
        MEMORY_GB=$(free -g | awk 'NR==2{printf "%.0f", $2}')
    else
        MEMORY_GB=$(echo "$(sysctl -n hw.memsize 2>/dev/null || echo "8589934592") / 1073741824" | bc 2>/dev/null || echo "8")
    fi
    
    DISK_GB=$(df -h . | awk 'NR==2{print $4}' | sed 's/G.*//' | head -c 3)
    
    log_info "系统配置："
    echo "  CPU核心: ${CPU_CORES}"
    echo "  内存: ${MEMORY_GB}GB"
    echo "  可用磁盘: ${DISK_GB}GB"
    
    # 最低要求检查
    if [ $CPU_CORES -lt 2 ]; then
        log_warning "CPU核心数较少 ($CPU_CORES)，建议至少4核心以获得更好性能"
    fi
    
    if [ $MEMORY_GB -lt 2 ]; then
        log_error "内存不足 (${MEMORY_GB}GB)，至少需要2GB内存"
        exit 1
    fi
    
    if [ $DISK_GB -lt 5 ]; then
        log_warning "磁盘空间较少 (${DISK_GB}GB)，建议至少10GB用于模型存储"
    fi
    
    log_success "系统要求检查通过"
}

# 创建必要目录
create_directories() {
    log_info "创建工作目录..."
    
    cd "$PROJECT_DIR"
    mkdir -p workspace/data
    mkdir -p workspace/logs
    mkdir -p workspace/test_results
    mkdir -p workspace/test_datasets
    
    log_success "目录创建完成"
}

# 构建Docker镜像
build_image() {
    log_info "构建Docker镜像..."
    
    # 确保DOCKER_COMPOSE变量已设置
    if [ -z "$DOCKER_COMPOSE" ]; then
        if docker compose version &> /dev/null; then
            DOCKER_COMPOSE="docker compose"
        elif command -v docker-compose &> /dev/null; then
            DOCKER_COMPOSE="docker-compose"
        else
            log_error "Docker Compose未安装，请先安装Docker Compose"
            exit 1
        fi
    fi
    
    cd "$PROJECT_DIR"
    
    # 构建镜像 (使用缓存加速)
    if $DOCKER_COMPOSE build; then
        log_success "Docker镜像构建成功"
    else
        log_error "Docker镜像构建失败"
        exit 1
    fi
}

# 强制重建镜像 (无缓存)
force_rebuild() {
    log_info "强制重建Docker镜像 (无缓存)..."
    
    # 确保DOCKER_COMPOSE变量已设置
    if [ -z "$DOCKER_COMPOSE" ]; then
        if docker compose version &> /dev/null; then
            DOCKER_COMPOSE="docker compose"
        elif command -v docker-compose &> /dev/null; then
            DOCKER_COMPOSE="docker-compose"
        else
            log_error "Docker Compose未安装，请先安装Docker Compose"
            exit 1
        fi
    fi
    
    cd "$PROJECT_DIR"
    
    # 强制重建镜像
    if $DOCKER_COMPOSE build --no-cache; then
        log_success "Docker镜像强制重建成功"
    else
        log_error "Docker镜像强制重建失败"
        exit 1
    fi
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    cd "$PROJECT_DIR"
    
    # 启动服务
    if $DOCKER_COMPOSE up -d; then
        log_success "服务启动成功"
    else
        log_error "服务启动失败"
        exit 1
    fi
    
    # 等待服务就绪
    log_info "等待服务就绪..."
    sleep 10
    
    # 检查服务状态
    if $DOCKER_COMPOSE ps | grep -q "Up"; then
        log_success "服务运行正常"
    else
        log_error "服务启动异常，请检查日志"
        $DOCKER_COMPOSE logs
        exit 1
    fi
}

# 显示访问信息
show_access_info() {
    log_success "🎉 Qwen3 Dashboard 部署完成！"
    echo ""
    echo "📊 Web管理界面: http://localhost:9080"
    echo "🤖 Ollama API:   http://localhost:11434"
    echo ""
    echo "📋 常用命令:"
    echo "  查看日志: ./docker/logs.sh tail dashboard"
    echo "  所有日志: ./docker/logs.sh all"
    echo "  日志列表: ./docker/logs.sh list"
    echo "  停止服务: $DOCKER_COMPOSE down"
    echo "  重启服务: $DOCKER_COMPOSE restart"
    echo "  进入容器: $DOCKER_COMPOSE exec qwen3-dashboard bash"
    echo ""
    echo "🔧 模型管理:"
    echo "  Web界面下载模型或使用命令:"
    echo "  $DOCKER_COMPOSE exec qwen3-dashboard ollama pull qwen3:0.6b-q4_k_m"
    echo ""
    echo "🚀 缓存构建:"
    echo "  快速重建: ./docker/deploy.sh rebuild"
    echo "  强制重建: ./docker/deploy.sh force-rebuild"
    echo ""
}

# 主函数
main() {
    echo "🚀 Qwen3 Dashboard Docker 部署脚本"
    echo "=================================="
    
    check_requirements
    create_directories
    build_image
    start_services
    show_access_info
}

# 解析命令行参数
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "build" | "rebuild")
        build_image
        ;;
    "force-rebuild")
        force_rebuild
        ;;
    "start")
        start_services
        ;;
    "stop")
        cd "$PROJECT_DIR"
        $DOCKER_COMPOSE down
        log_success "服务已停止"
        ;;
    "restart")
        cd "$PROJECT_DIR"
        $DOCKER_COMPOSE restart
        log_success "服务已重启"
        ;;
    "logs")
        cd "$PROJECT_DIR"
        $DOCKER_COMPOSE logs -f
        ;;
    "clean")
        cd "$PROJECT_DIR"
        $DOCKER_COMPOSE down -v
        docker rmi $(docker images | grep qwen3 | awk '{print $3}') 2>/dev/null || true
        log_success "清理完成"
        ;;
    *)
        echo "用法: $0 {deploy|build|rebuild|force-rebuild|start|stop|restart|logs|clean}"
        echo ""
        echo "命令说明:"
        echo "  deploy       - 完整部署 (默认)"
        echo "  build        - 只构建镜像 (使用缓存)"
        echo "  rebuild      - 重新构建 (使用缓存)"
        echo "  force-rebuild- 强制重建 (无缓存)"
        echo "  start        - 只启动服务"
        echo "  stop         - 停止服务"
        echo "  restart      - 重启服务"
        echo "  logs         - 查看日志"
        echo "  clean        - 清理所有资源"
        echo ""
        echo "🚀 缓存优化:"
        echo "  快速构建: $0 rebuild     (推荐，使用缓存)"
        echo "  完全重建: $0 force-rebuild (慢，但最新代码)"
        exit 1
        ;;
esac