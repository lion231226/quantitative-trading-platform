#!/bin/bash

# 代码覆盖率报告生成脚本
# 生成前端和后端的代码覆盖率报告

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 配置
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="$PROJECT_ROOT/coverage-reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# 创建报告目录
mkdir -p "$REPORT_DIR"

# 后端覆盖率报告
generate_backend_coverage() {
    log_info "生成后端代码覆盖率报告..."

    cd "$PROJECT_ROOT/backend"

    # 检查是否存在测试文件
    if [ ! -d "tests" ] || [ -z "$(ls -A tests/)" ]; then
        log_warning "后端测试文件不存在，跳过覆盖率报告生成"
        return
    fi

    # 运行测试并生成覆盖率报告
    log_info "运行后端测试..."
    python -m pytest \
        --cov=app \
        --cov-report=term-missing \
        --cov-report=html:"$REPORT_DIR/backend/html" \
        --cov-report=xml:"$REPORT_DIR/backend/coverage.xml" \
        --cov-report=json:"$REPORT_DIR/backend/coverage.json" \
        --junit-xml="$REPORT_DIR/backend/junit.xml" \
        --verbose \
        tests/

    # 生成覆盖率徽章
    if command -v coverage-badge &> /dev/null; then
        coverage-badge -o "$REPORT_DIR/backend/coverage.svg" -f coverage.json
        log_success "后端覆盖率徽章已生成"
    fi

    # 提取覆盖率数据
    if [ -f "$REPORT_DIR/backend/coverage.json" ]; then
        COVERAGE_PERCENT=$(python -c "
import json
with open('$REPORT_DIR/backend/coverage.json') as f:
    data = json.load(f)
print(f'{data[\"totals\"][\"percent_covered\"]:.1f}')
")
        echo "后端代码覆盖率: ${COVERAGE_PERCENT}%"
    fi

    log_success "后端覆盖率报告生成完成"
}

# 前端覆盖率报告
generate_frontend_coverage() {
    log_info "生成前端代码覆盖率报告..."

    cd "$PROJECT_ROOT/frontend"

    # 检查package.json是否存在
    if [ ! -f "package.json" ]; then
        log_warning "前端package.json不存在，跳过覆盖率报告生成"
        return
    fi

    # 检查是否有测试配置
    if ! grep -q "test" package.json; then
        log_warning "前端未配置测试，跳过覆盖率报告生成"
        return
    fi

    # 安装依赖
    if [ ! -d "node_modules" ]; then
        log_info "安装前端依赖..."
        npm ci
    fi

    # 运行测试并生成覆盖率报告
    log_info "运行前端测试..."
    npm run test:coverage || npm test -- --coverage --coverageReporters=text-lcov --coverageReporters=html --coverageReporters=json --coverageDirectory="$REPORT_DIR/frontend"

    # 生成覆盖率徽章
    if [ -f "$REPORT_DIR/frontend/coverage-summary.json" ]; then
        COVERAGE_PERCENT=$(python -c "
import json
with open('$REPORT_DIR/frontend/coverage-summary.json') as f:
    data = json.load(f)
print(f'{data[\"total\"][\"lines\"][\"pct\"]:.1f}')
")
        echo "前端代码覆盖率: ${COVERAGE_PERCENT}%"

        # 生成简单的徽章
        cat > "$REPORT_DIR/frontend/coverage.svg" << EOF
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="20" role="img" aria-label="Coverage: ${COVERAGE_PERCENT}%">
  <title>Coverage: ${COVERAGE_PERCENT}%</title>
  <linearGradient id="s" x2="0" y2="1">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <g class="bar">
    <rect class="bar" rx="3" width="100" height="20" fill="#555"/>
    <rect class="bar" rx="3" width="${COVERAGE_PERCENT}" height="20" fill="#4c1"/>
  </g>
  <g aria-hidden="true" fill="#fff" text-anchor="start" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11">
    <text x="4" y="15" fill="#010101" fill-opacity=".3">coverage</text>
    <text x="4" y="14">coverage</text>
    <text x="45" y="15" fill="#010101" fill-opacity=".3">${COVERAGE_PERCENT}%</text>
    <text x="45" y="14">${COVERAGE_PERCENT}%</text>
  </g>
</svg>
EOF
        log_success "前端覆盖率徽章已生成"
    fi

    log_success "前端覆盖率报告生成完成"
}

# E2E测试覆盖率
generate_e2e_coverage() {
    log_info "生成E2E测试覆盖率报告..."

    cd "$PROJECT_ROOT"

    # 检查Playwright配置
    if [ ! -f "playwright.config.ts" ]; then
        log_warning "Playwright配置不存在，跳过E2E覆盖率报告生成"
        return
    fi

    # 安装依赖
    if [ ! -d "node_modules" ]; then
        cd frontend
        npm ci
        cd ..
    fi

    # 运行E2E测试
    log_info "运行E2E测试..."
    cd frontend
    npx playwright test --reporter=html --reporter=json --output-dir="$REPORT_DIR/e2e"

    # 生成E2E测试报告摘要
    if [ -f "$REPORT_DIR/e2e/results.json" ]; then
        python -c "
import json
import sys

try:
    with open('$REPORT_DIR/e2e/results.json') as f:
        data = json.load(f)

    total = len(data['suites'][0]['specs']) if data['suites'] else 0
    passed = sum(1 for spec in data['suites'][0]['specs'] if spec['tests'][0]['results'][0]['status'] == 'passed') if data['suites'] else 0
    failed = total - passed

    print(f'E2E测试结果: {passed}/{total} 通过 ({failed} 失败)')

    if failed > 0:
        print('失败的测试:')
        for spec in data['suites'][0]['specs']:
            if spec['tests'][0]['results'][0]['status'] != 'passed':
                print(f'  - {spec[\"title\"]}')
except Exception as e:
    print(f'解析E2E结果失败: {e}')
    sys.exit(1)
"
    fi

    log_success "E2E测试报告生成完成"
}

# 生成综合报告
generate_summary_report() {
    log_info "生成综合覆盖率报告..."

    SUMMARY_FILE="$REPORT_DIR/coverage-summary-${TIMESTAMP}.md"
    HTML_FILE="$REPORT_DIR/coverage-summary-${TIMESTAMP}.html"

    cat > "$SUMMARY_FILE" << EOF
# 代码覆盖率报告

**生成时间**: $(date +"%Y-%m-%d %H:%M:%S")
**项目**: 量化交易平台
**报告目录**: $REPORT_DIR

## 覆盖率概览

EOF

    # 后端覆盖率
    if [ -f "$REPORT_DIR/backend/coverage.json" ]; then
        python -c "
import json
with open('$REPORT_DIR/backend/coverage.json') as f:
    data = json.load(f)

print('### 后端覆盖率')
print(f'- 总体覆盖率: {data[\"totals\"][\"percent_covered\"]:.1f}%')
print(f'- 覆盖行数: {data[\"totals\"][\"covered_lines\"]}/{data[\"totals\"][\"missing_lines\"] + data[\"totals\"][\"covered_lines\"]}')
print(f'- 分支覆盖率: {data[\"totals\"][\"percent_covered_branches\"]:.1f}%')
print(f'- 函数覆盖率: {data[\"totals\"][\"percent_covered_functions\"]:.1f}%')
print()
" >> "$SUMMARY_FILE"
    fi

    # 前端覆盖率
    if [ -f "$REPORT_DIR/frontend/coverage-summary.json" ]; then
        python -c "
import json
with open('$REPORT_DIR/frontend/coverage-summary.json') as f:
    data = json.load(f]

print('### 前端覆盖率')
print(f'- 总体覆盖率: {data[\"total\"][\"lines\"][\"pct\"]:.1f}%')
print(f'- 语句覆盖率: {data[\"total\"][\"statements\"][\"pct\"]:.1f}%')
print(f'- 分支覆盖率: {data[\"total\"][\"branches\"][\"pct\"]:.1f}%')
print(f'- 函数覆盖率: {data[\"total\"][\"functions\"][\"pct\"]:.1f}%')
print(f'- 行覆盖率: {data[\"total\"][\"lines\"][\"pct\"]:.1f}%')
print()
" >> "$SUMMARY_FILE"
    fi

    # E2E测试结果
    if [ -f "$REPORT_DIR/e2e/results.json" ]; then
        python -c "
import json
with open('$REPORT_DIR/e2e/results.json') as f:
    data = json.load(f)

if data['suites']:
    specs = data['suites'][0]['specs']
    total = len(specs)
    passed = sum(1 for spec in specs if spec['tests'][0]['results'][0]['status'] == 'passed')
    failed = total - passed

    print('### E2E测试')
    print(f'- 总测试数: {total}')
    print(f'- 通过: {passed}')
    print(f'- 失败: {failed}')
    print(f'- 通过率: {(passed/total*100):.1f}%')
    print()
" >> "$SUMMARY_FILE"
    fi

    # 添加报告链接
    cat >> "$SUMMARY_FILE" << EOF
## 详细报告

- [后端HTML报告](backend/html/index.html)
- [前端HTML报告](frontend/lcov-report/index.html)
- [E2E测试报告](e2e/index.html)

## 覆盖率徽章

EOF

    # 添加徽章链接
    if [ -f "$REPORT_DIR/backend/coverage.svg" ]; then
        echo "![Backend Coverage](backend/coverage.svg)" >> "$SUMMARY_FILE"
    fi

    if [ -f "$REPORT_DIR/frontend/coverage.svg" ]; then
        echo "![Frontend Coverage](frontend/coverage.svg)" >> "$SUMMARY_FILE"
    fi

    cat >> "$SUMMARY_FILE" << EOF

## 质量标准

- **目标覆盖率**: 80%
- **最低覆盖率**: 70%
- **优秀覆盖率**: 90%+

## 改进建议

基于当前覆盖率结果，以下是一些建议：

1. **提高测试覆盖率**: 优先覆盖核心业务逻辑
2. **边界条件测试**: 增加边界情况和错误处理的测试
3. **集成测试**: 加强模块间的集成测试
4. **E2E测试**: 覆盖关键用户流程

## 历史趋势

(需要多次运行后才能看到趋势)

EOF

    # 生成HTML版本
    python -c "
import markdown
import sys

try:
    with open('$SUMMARY_FILE', 'r', encoding='utf-8') as f:
        md_content = f.read()

    html_content = markdown.markdown(md_content)

    # 添加HTML样式
    html_template = f'''
<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>代码覆盖率报告</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        h1, h2, h3 {{
            color: #2c3e50;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: bold;
        }}
        .coverage-high {{ color: #28a745; font-weight: bold; }}
        .coverage-medium {{ color: #ffc107; font-weight: bold; }}
        .coverage-low {{ color: #dc3545; font-weight: bold; }}
        .summary {{
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        img {{
            max-width: 100px;
            height: auto;
        }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>
'''

    with open('$HTML_FILE', 'w', encoding='utf-8') as f:
        f.write(html_template)

    print('HTML报告生成完成')
except Exception as e:
    print(f'生成HTML报告失败: {e}')
    sys.exit(1)
"

    log_success "综合覆盖率报告生成完成"
    log_info "报告文件: $SUMMARY_FILE"
    log_info "HTML报告: $HTML_FILE"
}

# 清理旧报告
cleanup_old_reports() {
    log_info "清理旧的覆盖率报告..."

    # 保留最近10次的报告
    cd "$REPORT_DIR"
    ls -t coverage-summary-*.md 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
    ls -t coverage-summary-*.html 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true

    log_success "旧报告清理完成"
}

# 检查覆盖率标准
check_coverage_standards() {
    log_info "检查覆盖率是否符合标准..."

    local standards_met=true
    local threshold=80

    # 检查后端覆盖率
    if [ -f "$REPORT_DIR/backend/coverage.json" ]; then
        backend_coverage=$(python -c "
import json
with open('$REPORT_DIR/backend/coverage.json') as f:
    data = json.load(f)
print(data['totals']['percent_covered'])
")

        if (( $(echo "$backend_coverage < $threshold" | bc -l) )); then
            log_warning "后端覆盖率 ${backend_coverage}% 低于标准 ${threshold}%"
            standards_met=false
        else
            log_success "后端覆盖率 ${backend_coverage}% 符合标准"
        fi
    fi

    # 检查前端覆盖率
    if [ -f "$REPORT_DIR/frontend/coverage-summary.json" ]; then
        frontend_coverage=$(python -c "
import json
with open('$REPORT_DIR/frontend/coverage-summary.json') as f:
    data = json.load(f)
print(data['total']['lines']['pct'])
")

        if (( $(echo "$frontend_coverage < $threshold" | bc -l) )); then
            log_warning "前端覆盖率 ${frontend_coverage}% 低于标准 ${threshold}%"
            standards_met=false
        else
            log_success "前端覆盖率 ${frontend_coverage}% 符合标准"
        fi
    fi

    if [ "$standards_met" = false ]; then
        log_warning "部分覆盖率未达到标准，请增加测试用例"
        return 1
    else
        log_success "所有覆盖率都符合标准"
        return 0
    fi
}

# 主函数
main() {
    local start_time=$(date +%s)

    log_info "开始生成代码覆盖率报告..."
    echo "=========================================="

    # 检查依赖
    if ! command -v python &> /dev/null; then
        log_error "Python未安装"
        exit 1
    fi

    if ! command -v node &> /dev/null; then
        log_warning "Node.js未安装，跳过前端覆盖率报告"
    fi

    # 检查必要工具
    if ! python -c "import pytest" 2>/dev/null; then
        log_error "pytest未安装，请运行: pip install pytest pytest-cov"
        exit 1
    fi

    # 生成报告
    generate_backend_coverage
    generate_frontend_coverage
    generate_e2e_coverage
    generate_summary_report
    cleanup_old_reports

    # 检查标准
    check_coverage_standards

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    echo "=========================================="
    log_success "覆盖率报告生成完成! 耗时: ${duration}秒"
    log_info "报告目录: $REPORT_DIR"
    log_info "查看报告: open $REPORT_DIR/coverage-summary-${TIMESTAMP}.html"
}

# 错误处理
trap 'log_error "覆盖率报告生成过程中发生错误"; exit 1' ERR

# 执行主函数
main "$@"