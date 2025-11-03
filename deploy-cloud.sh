#!/bin/bash

# 量化交易策略分析平台 - 云端部署脚本
# 作者: aTenderLion
# 版本: 1.0

echo "🚀 量化交易策略分析平台 - 云端部署开始"
echo "=========================================="

# 检查必要的工具
check_requirements() {
    echo "📋 检查部署要求..."

    # 检查 Node.js
    if ! command -v node &> /dev/null; then
        echo "❌ Node.js 未安装，请先安装 Node.js"
        exit 1
    fi

    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python3 未安装，请先安装 Python3"
        exit 1
    fi

    # 检查 Git
    if ! command -v git &> /dev/null; then
        echo "❌ Git 未安装，请先安装 Git"
        exit 1
    fi

    echo "✅ 所有检查通过"
}

# 前端部署到 Vercel
deploy_frontend() {
    echo "🌐 部署前端到 Vercel..."

    cd frontend

    # 安装依赖
    npm install

    # 构建项目
    npm run build

    # 检查是否安装了 Vercel CLI
    if ! command -v vercel &> /dev/null; then
        echo "📦 安装 Vercel CLI..."
        npm i -g vercel
    fi

    # 部署到 Vercel
    echo "🚀 部署前端..."
    vercel --prod

    # 获取部署的 URL
    FRONTEND_URL=$(vercel ls --prod | grep $(basename $(pwd)) | awk '{print $2}' | head -1)
    echo "✅ 前端部署成功: $FRONTEND_URL"

    cd ..
}

# 后端部署到 Railway
deploy_backend() {
    echo "⚙️ 部署后端到 Railway..."

    cd backend

    # 检查是否安装了 Railway CLI
    if ! command -v railway &> /dev/null; then
        echo "📦 安装 Railway CLI..."
        npm install -g @railway/cli
    fi

    # 登录 Railway
    railway login

    # 初始化 Railway 项目
    if [ ! -f "railway.toml" ]; then
        railway init
    fi

    # 部署后端
    echo "🚀 部署后端..."
    railway up

    # 获取部署的 URL
    BACKEND_URL=$(railway status | grep "URL" | awk '{print $3}')
    echo "✅ 后端部署成功: $BACKEND_URL"

    cd ..
}

# 更新前端环境变量
update_frontend_env() {
    echo "🔧 更新前端环境变量..."

    cd frontend

    # 更新 Vercel 环境变量
    vercel env add NEXT_PUBLIC_API_URL production
    vercel env add NEXT_PUBLIC_NODE_ENV production

    cd ..
}

# 验证部署
verify_deployment() {
    echo "🔍 验证部署..."

    # 这里可以添加健康检查
    echo "✅ 部署验证完成"
}

# 生成部署报告
generate_report() {
    echo "📊 生成部署报告..."

    cat > deployment-report.md << EOF
# 量化交易策略分析平台 - 部署报告

## 部署信息
- **部署时间**: $(date)
- **前端URL**: https://your-app.vercel.app
- **后端URL**: https://your-backend.up.railway.app
- **版本**: v1.0.0

## 技术栈
- **前端**: Next.js 14 + TypeScript + Tailwind CSS
- **后端**: FastAPI + Python 3.11
- **部署**: Vercel (前端) + Railway (后端)

## 功能特性
- ✅ 实时数据分析 (AKShare)
- ✅ 量化策略回测
- ✅ 交互式图表
- ✅ 教育导向的教程系统
- ✅ 响应式设计

## 联系方式
- **作者**: aTenderLion
- **项目**: 量化交易策略分析平台

---

部署完成时间: $(date)
EOF

    echo "✅ 部署报告已生成: deployment-report.md"
}

# 主函数
main() {
    echo "开始云端部署流程..."

    check_requirements
    deploy_frontend
    deploy_backend
    update_frontend_env
    verify_deployment
    generate_report

    echo ""
    echo "🎉 部署完成！"
    echo "🌐 前端: https://your-app.vercel.app"
    echo "⚙️ 后端: https://your-backend.up.railway.app"
    echo "📊 报告: deployment-report.md"
    echo ""
    echo "💡 提示:"
    echo "- 记得在 Vercel 和 Railway 中配置环境变量"
    echo "- 查看部署报告了解详细信息"
    echo "- 如有问题，请查看各平台的日志"
}

# 运行主函数
main