# 部署配置总结

## 已创建的文件

### 配置文件
1. **frontend/vercel.json** - Vercel 部署配置
2. **frontend/.env.example** - 环境变量模板
3. **frontend/next.config.js** - Next.js 配置（已更新支持静态导出）
4. **frontend/package.json** - 已更新部署脚本
5. **.github/workflows/deploy.yml** - GitHub Actions 自动部署

### 部署脚本
1. **simple-deploy.bat** - Windows 部署脚本（推荐）
2. **deploy.bat** - 完整版 Windows 部署脚本
3. **deploy.sh** - Linux/macOS 部署脚本

### 文档
1. **frontend/DEPLOYMENT.md** - 详细部署指南
2. **DEPLOYMENT-SUMMARY.md** - 本总结文档

## 快速部署方法

### 方法一：使用 Windows 脚本（最简单）
```cmd
.\simple-deploy.bat
```

### 方法二：手动静态构建
```cmd
cd frontend
npm run deploy:static
```
静态文件将在 `frontend/out/` 目录

### 方法三：Vercel Dashboard（推荐用于生产）
1. 访问 [vercel.com](https://vercel.com)
2. 导入 Git 仓库
3. 设置 Root Directory: `frontend`
4. Build Command: `npm run build`
5. 配置环境变量

## 环境变量配置

创建 `frontend/.env.local` 文件：
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_NODE_ENV=development
```

生产环境需要：
```env
NEXT_PUBLIC_API_URL=https://your-api-domain.com
NEXT_PUBLIC_NODE_ENV=production
```

## 部署目标

### 静态托管服务
- **Netlify**: 直接拖拽 `frontend/out` 文件夹到 [app.netlify.com/drop](https://app.netlify.com/drop)
- **Vercel**: 使用 Dashboard 导入项目
- **GitHub Pages**: 推送到 gh-pages 分支
- **Surge.sh**: `cd frontend/out && surge .`

### 自定义服务器
将 `frontend/out` 目录的内容复制到任何 Web 服务器

## 故障排除

1. **Vercel CLI 问题**: 使用 Vercel Dashboard 或静态导出
2. **构建失败**: 检查 Node.js 版本（需要 >= 18.0.0）
3. **环境变量**: 确保 `.env.local` 文件存在且配置正确
4. **API 连接**: 检查 `NEXT_PUBLIC_API_URL` 设置

## 验证部署

部署后检查：
1. 页面能正常加载
2. 所有导航链接工作正常
3. API 连接正常（如果有后端）
4. 图片和静态资源加载正常

## 支持的部署选项

| 方法 | 复杂度 | 推荐场景 | 费用 |
|------|--------|----------|------|
| simple-deploy.bat | 极低 | 快速测试、预览 | 免费 |
| Vercel Dashboard | 低 | 生产环境 | 免费套餐 |
| GitHub Actions | 中等 | CI/CD 自动化 | 免费 |
| 静态托管 | 低 | 简单网站 | 多数免费 |

## 联系支持

如果遇到问题：
1. 检查 `frontend/DEPLOYMENT.md` 详细文档
2. 查看构建日志中的错误信息
3. 确认环境变量配置正确