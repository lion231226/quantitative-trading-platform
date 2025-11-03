#!/bin/bash

# =============================================================================
# 质量门禁脚本 (Quality Gate Script)
#
# 用途: 在代码提交和故事完成前强制执行质量检查
# 使用:
#   ./scripts/quality-gate.sh                    # 完整检查
#   ./scripts/quality-gate.sh --type=dev         # 开发阶段检查
#   ./scripts/quality-gate.sh --type=review      # 审查阶段检查
#   ./scripts/quality-gate.sh --type=release     # 发布阶段检查
# =============================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_DIR="$PROJECT_ROOT/backend"
REPORTS_DIR="$PROJECT_ROOT/reports/quality"

# 创建报告目录
mkdir -p "$REPORTS_DIR"

# 时间戳
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
REPORT_FILE="$REPORTS_DIR/quality-gate-$TIMESTAMP.txt"

# 检查类型
CHECK_TYPE=${1:-"full"}

# 计数器
ERRORS=0
WARNINGS=0
CHECKS_PASSED=0
TOTAL_CHECKS=0

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$REPORT_FILE"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1" | tee -a "$REPORT_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$REPORT_FILE"
    ((WARNINGS++))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1" | tee -a "$REPORT_FILE"
    ((ERRORS++))
}

# 检查函数
check_command() {
    local cmd=$1
    local description=$2

    ((TOTAL_CHECKS++))
    log_info "检查: $description"

    if command -v "$cmd" &> /dev/null; then
        log_success "$description 已安装"
        ((CHECKS_PASSED++))
        return 0
    else
        log_error "$description 未安装"
        return 1
    fi
}

check_file_exists() {
    local file=$1
    local description=$2

    ((TOTAL_CHECKS++))
    log_info "检查: $description"

    if [ -f "$file" ]; then
        log_success "$description 存在"
        ((CHECKS_PASSED++))
        return 0
    else
        log_error "$description 不存在: $file"
        return 1
    fi
}

check_directory_exists() {
    local dir=$1
    local description=$2

    ((TOTAL_CHECKS++))
    log_info "检查: $description"

    if [ -d "$dir" ]; then
        log_success "$description 存在"
        ((CHECKS_PASSED++))
        return 0
    else
        log_error "$description 不存在: $dir"
        return 1
    fi
}

# TypeScript编译检查
check_typescript_compilation() {
    ((TOTAL_CHECKS++))
    log_info "检查: TypeScript编译"

    cd "$FRONTEND_DIR"

    if npx tsc --noEmit --pretty false 2>&1 | tee -a "$REPORT_FILE"; then
        log_success "TypeScript编译通过"
        ((CHECKS_PASSED++))
        return 0
    else
        log_error "TypeScript编译失败"
        return 1
    fi
}

# ESLint检查
check_eslint() {
    ((TOTAL_CHECKS++))
    log_info "检查: ESLint代码规范"

    cd "$FRONTEND_DIR"

    if npm run lint --silent 2>&1 | tee -a "$REPORT_FILE"; then
        log_success "ESLint检查通过"
        ((CHECKS_PASSED++))
        return 0
    else
        log_error "ESLint检查失败"
        return 1
    fi
}

# Prettier格式检查
check_prettier() {
    ((TOTAL_CHECKS++))
    log_info "检查: Prettier代码格式"

    cd "$FRONTEND_DIR"

    if npx prettier --check "src/**/*.{ts,tsx,js,jsx,json,css,md}" 2>&1 | tee -a "$REPORT_FILE"; then
        log_success "Prettier格式检查通过"
        ((CHECKS_PASSED++))
        return 0
    else
        log_error "Prettier格式检查失败"
        return 1
    fi
}

# 单元测试检查
check_unit_tests() {
    ((TOTAL_CHECKS++))
    log_info "检查: 单元测试"

    cd "$FRONTEND_DIR"

    if npm run test -- --silent --passWithNoTests 2>&1 | tee -a "$REPORT_FILE"; then
        log_success "单元测试通过"
        ((CHECKS_PASSED++))
        return 0
    else
        log_error "单元测试失败"
        return 1
    fi
}

# 测试覆盖率检查
check_test_coverage() {
    ((TOTAL_CHECKS++))
    log_info "检查: 测试覆盖率"

    cd "$FRONTEND_DIR"

    # 运行覆盖率测试
    npm run test:coverage --silent 2>&1 | tee "$REPORTS_DIR/coverage-$TIMESTAMP.txt"

    # 提取覆盖率数据
    COVERAGE_LINES=$(grep "Lines" "$REPORTS_DIR/coverage-$TIMESTAMP.txt" | awk '{print $2}' | sed 's/%//' || echo "0")
    COVERAGE_FUNCTIONS=$(grep "Functions" "$REPORTS_DIR/coverage-$TIMESTAMP.txt" | awk '{print $2}' | sed 's/%//' || echo "0")
    COVERAGE_BRANCHES=$(grep "Branches" "$REPORTS_DIR/coverage-$TIMESTAMP.txt" | awk '{print $2}' | sed 's/%//' || echo "0")
    COVERAGE_STATEMENTS=$(grep "Statements" "$REPORTS_DIR/coverage-$TIMESTAMP.txt" | awk '{print $2}' | sed 's/%//' || echo "0")

    log_info "覆盖率数据: 行$COVERAGE_LINES%, 函数$COVERAGE_FUNCTIONS%, 分支$COVERAGE_BRANCHES%, 语句$COVERAGE_STATEMENTS%"

    # 检查最低覆盖率要求
    MIN_COVERAGE=80
    if [ "$COVERAGE_LINES" -ge "$MIN_COVERAGE" ]; then
        log_success "测试覆盖率达标 ($COVERAGE_LINES% >= $MIN_COVERAGE%)"
        ((CHECKS_PASSED++))
        return 0
    else
        log_error "测试覆盖率不足 ($COVERAGE_LINES% < $MIN_COVERAGE%)"
        return 1
    fi
}

# 构建检查
check_build() {
    ((TOTAL_CHECKS++))
    log_info "检查: 项目构建"

    cd "$FRONTEND_DIR"

    if npm run build 2>&1 | tee -a "$REPORT_FILE"; then
        log_success "项目构建成功"
        ((CHECKS_PASSED++))
        return 0
    else
        log_error "项目构建失败"
        return 1
    fi
}

# 安全检查
check_security() {
    ((TOTAL_CHECKS++))
    log_info "检查: 安全漏洞扫描"

    cd "$FRONTEND_DIR"

    if command -v npm-audit-resolver &> /dev/null; then
        npm audit --audit-level moderate 2>&1 | tee -a "$REPORT_FILE"
        AUDIT_RESULT=$?

        if [ $AUDIT_RESULT -eq 0 ]; then
            log_success "安全检查通过"
            ((CHECKS_PASSED++))
            return 0
        else
            log_warning "发现安全漏洞，建议修复"
            return 1
        fi
    else
        log_warning "npm-audit-resolver未安装，跳过安全检查"
        return 0
    fi
}

# 文件大小检查
check_bundle_size() {
    ((TOTAL_CHECKS++))
    log_info "检查: 打包文件大小"

    cd "$FRONTEND_DIR"

    # 检查是否已经构建
    if [ ! -d ".next" ]; then
        log_warning "未找到构建文件，跳过大小检查"
        return 0
    fi

    # 检查主bundle大小
    BUNDLE_SIZE=$(find .next -name "*.js" -exec du -b {} + | awk '{sum += $1} END {print sum/1024/1024}' || echo "0")

    # 设置大小限制 (5MB)
    MAX_SIZE=5
    if (( $(echo "$BUNDLE_SIZE <= $MAX_SIZE" | bc -l) )); then
        log_success "打包文件大小正常 (${BUNDLE_SIZE}MB <= ${MAX_SIZE}MB)"
        ((CHECKS_PASSED++))
        return 0
    else
        log_warning "打包文件过大 (${BUNDLE_SIZE}MB > ${MAX_SIZE}MB)"
        return 1
    fi
}

# 依赖检查
check_dependencies() {
    ((TOTAL_CHECKS++))
    log_info "检查: 项目依赖"

    cd "$FRONTEND_DIR"

    # 检查package.json
    if [ -f "package.json" ]; then
        # 检查是否有未安装的依赖
        if npm ls --depth=0 2>&1 | grep -q "UNMET DEPENDENCY"; then
            log_error "发现未安装的依赖"
            return 1
        else
            log_success "依赖检查通过"
            ((CHECKS_PASSED++))
            return 0
        fi
    else
        log_error "package.json不存在"
        return 1
    fi
}

# 故事文件检查
check_story_files() {
    local story_path=$1

    if [ -z "$story_path" ]; then
        log_warning "未指定故事文件路径，跳过故事检查"
        return 0
    fi

    ((TOTAL_CHECKS++))
    log_info "检查: 故事文件完整性"

    # 检查故事文件存在
    if [ ! -f "$story_path" ]; then
        log_error "故事文件不存在: $story_path"
        return 1
    fi

    # 检查必要章节
    local required_sections=("Story" "Acceptance Criteria" "Tasks")
    for section in "${required_sections[@]}"; do
        if ! grep -q "^## $section" "$story_path"; then
            log_error "故事文件缺少必要章节: $section"
            return 1
        fi
    done

    log_success "故事文件检查通过"
    ((CHECKS_PASSED++))
    return 0
}

# 验收标准映射检查
check_acceptance_criteria_mapping() {
    local story_path=$1

    if [ -z "$story_path" ]; then
        log_warning "未指定故事文件路径，跳过验收标准映射检查"
        return 0
    fi

    ((TOTAL_CHECKS++))
    log_info "检查: 验收标准映射"

    # 提取验收标准
    local ac_count=$(grep -c "^[0-9]\+\." "$story_path" || echo "0")

    if [ "$ac_count" -eq 0 ]; then
        log_error "未找到验收标准"
        return 1
    fi

    log_success "发现 $ac_count 个验收标准"
    ((CHECKS_PASSED++))
    return 0
}

# 主函数
main() {
    echo "🔍 质量门禁检查开始 - $(date)" | tee "$REPORT_FILE"
    echo "检查类型: $CHECK_TYPE" | tee -a "$REPORT_FILE"
    echo "项目路径: $PROJECT_ROOT" | tee -a "$REPORT_FILE"
    echo "======================================" | tee -a "$REPORT_FILE"

    # 环境检查
    log_info "阶段1: 环境检查"
    check_command "node" "Node.js"
    check_command "npm" "NPM"
    check_command "npx" "NPX"
    check_directory_exists "$FRONTEND_DIR" "前端项目目录"
    check_file_exists "$FRONTEND_DIR/package.json" "Package.json文件"

    # 基础质量检查
    log_info "阶段2: 基础质量检查"
    check_dependencies
    check_typescript_compilation
    check_eslint
    check_prettier

    # 测试检查
    log_info "阶段3: 测试检查"
    check_unit_tests
    check_test_coverage

    # 构建检查
    log_info "阶段4: 构建检查"
    check_build
    check_bundle_size

    # 安全检查
    log_info "阶段5: 安全检查"
    check_security

    # 根据检查类型执行额外检查
    case "$CHECK_TYPE" in
        "review"|"release")
            log_info "阶段6: 审查/发布专项检查"
            STORY_PATH="$2"
            check_story_files "$STORY_PATH"
            check_acceptance_criteria_mapping "$STORY_PATH"
            ;;
        "dev")
            log_info "开发阶段检查，跳过额外检查"
            ;;
    esac

    # 生成报告
    echo "======================================" | tee -a "$REPORT_FILE"
    echo "📊 质量门禁检查结果 - $(date)" | tee -a "$REPORT_FILE"
    echo "总检查项: $TOTAL_CHECKS" | tee -a "$REPORT_FILE"
    echo "通过检查: $CHECKS_PASSED" | tee -a "$REPORT_FILE"
    echo "错误数量: $ERRORS" | tee -a "$REPORT_FILE"
    echo "警告数量: $WARNINGS" | tee -a "$REPORT_FILE"
    echo "成功率: $(( CHECKS_PASSED * 100 / TOTAL_CHECKS ))%" | tee -a "$REPORT_FILE"
    echo "详细报告: $REPORT_FILE" | tee -a "$REPORT_FILE"

    # 最终判断
    if [ $ERRORS -eq 0 ]; then
        echo -e "\n${GREEN}✅ 质量门禁检查通过${NC}" | tee -a "$REPORT_FILE"
        exit 0
    else
        echo -e "\n${RED}❌ 质量门禁检查失败，发现 $ERRORS 个错误${NC}" | tee -a "$REPORT_FILE"
        echo -e "${YELLOW}请修复所有错误后重新运行检查${NC}" | tee -a "$REPORT_FILE"
        exit 1
    fi
}

# 执行主函数
main "$@"