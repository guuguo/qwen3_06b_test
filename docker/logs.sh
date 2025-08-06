#!/bin/bash
# 统一日志管理脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="$PROJECT_DIR/workspace/logs"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

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

show_help() {
    echo "🔍 Qwen3 Dashboard 日志管理工具"
    echo "================================"
    echo ""
    echo "用法: $0 [命令] [选项]"
    echo ""
    echo "📋 可用命令:"
    echo "  list          - 列出所有可用的日志文件"
    echo "  tail [日志名]  - 实时查看指定日志 (默认: dashboard)"
    echo "  view [日志名]  - 查看日志文件内容 (默认: dashboard)"
    echo "  clean         - 清理所有日志文件"
    echo "  size          - 显示日志文件大小"
    echo "  docker        - 查看Docker容器日志"
    echo "  all           - 实时查看所有日志"
    echo ""
    echo "📝 可用日志名:"
    echo "  dashboard     - Python Dashboard应用日志"
    echo "  ollama        - Ollama AI服务日志"
    echo "  flask         - Flask Web服务日志"
    echo "  model-preload - 模型预加载日志"
    echo "  model-test    - 模型测试日志"
    echo "  system        - 系统日志 (JSONL格式)"
    echo ""
    echo "💡 使用示例:"
    echo "  $0 list                    # 列出所有日志"
    echo "  $0 tail dashboard          # 实时查看Dashboard日志"
    echo "  $0 view ollama             # 查看Ollama日志"
    echo "  $0 docker                  # 查看容器日志"
    echo "  $0 all                     # 实时查看所有日志"
    echo ""
}

list_logs() {
    log_info "📂 可用日志文件列表:"
    echo ""
    
    cd "$PROJECT_DIR"
    
    if [ ! -d "$LOGS_DIR" ]; then
        log_warning "日志目录不存在: $LOGS_DIR"
        return
    fi
    
    echo -e "${CYAN}应用日志:${NC}"
    for log_file in "$LOGS_DIR"/*.log; do
        if [ -f "$log_file" ]; then
            filename=$(basename "$log_file")
            size=$(du -h "$log_file" | cut -f1)
            modified=$(ls -l "$log_file" | awk '{print $6, $7, $8}')
            echo "  📄 $filename (${size}, 修改时间: $modified)"
        fi
    done
    
    echo ""
    echo -e "${CYAN}系统日志:${NC}"
    for log_file in "$LOGS_DIR"/*.jsonl; do
        if [ -f "$log_file" ]; then
            filename=$(basename "$log_file")
            size=$(du -h "$log_file" | cut -f1)
            modified=$(ls -l "$log_file" | awk '{print $6, $7, $8}')
            echo "  📊 $filename (${size}, 修改时间: $modified)"
        fi
    done
}

tail_log() {
    local log_name="${1:-dashboard}"
    local log_file=""
    
    case "$log_name" in
        "dashboard")
            log_file="$LOGS_DIR/dashboard.log"
            ;;
        "ollama")
            log_file="$LOGS_DIR/ollama.out.log"
            ;;
        "flask")
            log_file="$LOGS_DIR/flask.out.log"
            ;;
        "model-preload")
            log_file="$LOGS_DIR/model-preload.out.log"
            ;;
        "model-test")
            log_file="$LOGS_DIR/model-test.out.log"
            ;;
        "system")
            # 查找最新的系统日志文件
            log_file=$(ls -t "$LOGS_DIR"/system_*.jsonl 2>/dev/null | head -n 1)
            ;;
        *)
            # 尝试直接使用文件名
            if [ -f "$LOGS_DIR/$log_name" ]; then
                log_file="$LOGS_DIR/$log_name"
            else
                log_warning "未知的日志名称: $log_name"
                echo "使用 '$0 list' 查看可用日志"
                exit 1
            fi
            ;;
    esac
    
    if [ ! -f "$log_file" ]; then
        log_warning "日志文件不存在: $log_file"
        return 1
    fi
    
    log_info "🔄 实时查看日志: $(basename "$log_file")"
    echo -e "${YELLOW}按 Ctrl+C 退出${NC}"
    echo ""
    
    tail -f "$log_file"
}

view_log() {
    local log_name="${1:-dashboard}"
    local log_file=""
    local lines="${2:-50}"
    
    case "$log_name" in
        "dashboard")
            log_file="$LOGS_DIR/dashboard.log"
            ;;
        "ollama")
            log_file="$LOGS_DIR/ollama.out.log"
            ;;
        "flask")
            log_file="$LOGS_DIR/flask.out.log"
            ;;
        "model-preload")
            log_file="$LOGS_DIR/model-preload.out.log"
            ;;
        "model-test")
            log_file="$LOGS_DIR/model-test.out.log"
            ;;
        "system")
            log_file=$(ls -t "$LOGS_DIR"/system_*.jsonl 2>/dev/null | head -n 1)
            ;;
        *)
            if [ -f "$LOGS_DIR/$log_name" ]; then
                log_file="$LOGS_DIR/$log_name"
            else
                log_warning "未知的日志名称: $log_name"
                exit 1
            fi
            ;;
    esac
    
    if [ ! -f "$log_file" ]; then
        log_warning "日志文件不存在: $log_file"
        return 1
    fi
    
    log_info "📖 查看日志文件: $(basename "$log_file") (最近 $lines 行)"
    echo ""
    
    tail -n "$lines" "$log_file"
}

clean_logs() {
    log_warning "⚠️  即将清理所有日志文件"
    echo -n "确定要继续吗? [y/N]: "
    read -r confirm
    
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        cd "$PROJECT_DIR"
        rm -f "$LOGS_DIR"/*.log
        rm -f "$LOGS_DIR"/*.jsonl
        log_success "✅ 日志文件已清理"
    else
        log_info "❌ 取消清理操作"
    fi
}

show_size() {
    log_info "📊 日志文件大小统计:"
    echo ""
    
    cd "$PROJECT_DIR"
    
    if [ ! -d "$LOGS_DIR" ]; then
        log_warning "日志目录不存在"
        return
    fi
    
    echo -e "${CYAN}文件大小:${NC}"
    du -h "$LOGS_DIR"/* 2>/dev/null | sort -hr || echo "  没有找到日志文件"
    
    echo ""
    echo -e "${CYAN}总大小:${NC}"
    du -sh "$LOGS_DIR" 2>/dev/null || echo "  0B"
}

docker_logs() {
    log_info "🐳 查看Docker容器日志"
    echo -e "${YELLOW}按 Ctrl+C 退出${NC}"
    echo ""
    
    cd "$PROJECT_DIR"
    docker compose logs -f qwen3-dashboard
}

tail_all() {
    log_info "📺 实时查看所有应用日志"
    echo -e "${YELLOW}按 Ctrl+C 退出${NC}"
    echo ""
    
    cd "$PROJECT_DIR"
    
    # 使用multitail如果可用，否则使用tail
    if command -v multitail >/dev/null 2>&1; then
        multitail \
            -l "tail -f $LOGS_DIR/dashboard.log" \
            -l "tail -f $LOGS_DIR/ollama.out.log" \
            -l "tail -f $LOGS_DIR/flask.out.log" 2>/dev/null
    else
        # 简单的并行tail
        tail -f "$LOGS_DIR"/*.log 2>/dev/null &
        tail -f "$LOGS_DIR"/*.jsonl 2>/dev/null &
        wait
    fi
}

# 主逻辑
case "${1:-help}" in
    "help" | "-h" | "--help")
        show_help
        ;;
    "list" | "ls")
        list_logs
        ;;
    "tail" | "follow" | "f")
        tail_log "$2"
        ;;
    "view" | "cat" | "show")
        view_log "$2" "$3"
        ;;
    "clean" | "clear")
        clean_logs
        ;;
    "size" | "du")
        show_size
        ;;
    "docker" | "container")
        docker_logs
        ;;
    "all" | "multi")
        tail_all
        ;;
    *)
        echo "❌ 未知命令: $1"
        echo "使用 '$0 help' 查看帮助"
        exit 1
        ;;
esac