#!/bin/bash

# 量化交易前端部署脚本
# 使用说明：./deploy.sh [环境] [方法]

set -e

ENVIRONMENT=${1:-production}
METHOD=${2:-vercel}

echo "🚀 开始部署量化交易前端应用..."
echo "环境: $ENVIRONMENT"
echo "方法: $METHOD"

# 进入前端目录
cd frontend

# 检查环境变量文件
if [ ! -f ".env.local" ]; then
    echo "⚠️  未找到 .env.local 文件，使用 .env.example 创建..."
    cp .env.example .env.local
    echo "📝 请编辑 frontend/.env.local 文件设置正确的环境变量"
    echo "   特别是 NEXT_PUBLIC_API_URL"
    read -p "按 Enter 继续..."
fi

# 根据方法选择部署方式
case $METHOD in
    "vercel")
        echo "📦 使用 Vercel 部署..."
        echo "⚠️  如果 Vercel CLI 有问题，请使用 Vercel Dashboard 方法"
        echo "   访问 https://vercel.com/docs/concepts/deployments/overview"
        ;;
    "static")
        echo "📦 构建静态文件..."
        npm run deploy:static
        echo "✅ 静态文件已生成在 frontend/out/ 目录"
        echo "💡 你可以使用以下命令部署到静态托管："
        echo "   Netlify: cd frontend/out && netlify deploy --prod --dir ."
        echo "   Surge.sh: cd frontend/out && surge ."
        ;;
    "build-only")
        echo "📦 仅构建项目..."
        npm run build
        echo "✅ 构建完成，文件在 frontend/.next 目录"
        ;;
    *)
        echo "❌ 未知的部署方法: $METHOD"
        echo "可用的方法: vercel, static, build-only"
        exit 1
        ;;
esac

echo ""
echo "🎉 部署脚本执行完成！"
echo ""
echo "📚 更多部署选项请查看: frontend/DEPLOYMENT.md"