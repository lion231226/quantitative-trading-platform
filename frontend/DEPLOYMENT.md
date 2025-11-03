# 部署指南

本文档提供了量化交易前端应用的部署指南。

## 前置条件

- Node.js 18.0.0 或更高版本
- npm 或 pnpm 包管理器
- Vercel 账户（用于生产部署）
- Git 仓库

## 本地开发

1. 克隆仓库
```bash
git clone <repository-url>
cd frontend
```

2. 安装依赖
```bash
npm install
# 或
pnpm install
```

3. 配置环境变量
```bash
cp .env.example .env.local
```

编辑 `.env.local` 文件，设置适当的环境变量：
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_NODE_ENV=development
```

4. 启动开发服务器
```bash
npm run dev
# 或
pnpm dev
```

访问 http://localhost:3000 查看应用。

## 生产部署

### 方法一：通过 Vercel Dashboard（推荐）

由于 Windows 环境下 Vercel CLI 可能存在兼容性问题，推荐使用 Vercel Dashboard：

1. 访问 [vercel.com](https://vercel.com) 并登录
2. 点击 "New Project"
3. 导入你的 Git 仓库
4. 配置项目设置：
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`
5. 配置环境变量：
   - `NEXT_PUBLIC_API_URL`: 后端 API 地址
   - `NEXT_PUBLIC_NODE_ENV`: production
6. 点击 "Deploy"

### 方法二：通过 GitHub Actions（自动部署）

1. 将代码推送到 GitHub 仓库
2. 在 Vercel Dashboard 中生成 Personal Access Token
3. 在 GitHub 仓库设置中添加 Secret：
   - `VERCEL_TOKEN`: 你的 Vercel token
   - `VERCEL_ORG_ID`: 你的组织 ID
   - `VERCEL_PROJECT_ID`: 项目 ID
4. 推送代码将自动触发部署

### 方法三：静态文件部署

1. 构建静态文件：
```bash
cd frontend
npm run deploy:static
```

2. 静态文件将生成在 `frontend/out/` 目录
3. 可以部署到任何静态托管服务：
   - GitHub Pages
   - Netlify
   - Surge.sh
   - AWS S3

**部署到 Netlify 示例：**
```bash
npm install -g netlify-cli
cd frontend/out
netlify deploy --prod --dir .
```

### 方法四：通过 Vercel CLI（如果可用）

如果你的环境支持 Vercel CLI：

1. 安装 Vercel CLI
```bash
npm i -g vercel
```

2. 登录 Vercel
```bash
vercel login
```

3. 部署到预览环境
```bash
cd frontend
npm run deploy:preview
```

4. 部署到生产环境
```bash
cd frontend
npm run deploy
```

### 环境变量配置

在 Vercel Dashboard 中设置以下环境变量：

**必需：**
- `NEXT_PUBLIC_API_URL`: 生产环境的 API 地址
- `NEXT_PUBLIC_NODE_ENV`: production

**可选：**
- `NEXT_TELEMETRY_DISABLED`: 1 (禁用 Next.js 遥测)
- `NEXT_PUBLIC_ENABLE_ANALYTICS`: false/true (启用分析)
- `NEXT_PUBLIC_ENABLE_ERROR_REPORTING`: false/true (启用错误报告)

## 构建和导出

如果需要静态导出：

1. 构建并导出
```bash
npm run deploy:build
```

2. 生成的静态文件将在 `out` 目录中

## 部署脚本说明

- `npm run deploy`: 部署到 Vercel 生产环境
- `npm run deploy:preview`: 部署到 Vercel 预览环境
- `npm run deploy:build`: 构建并导出静态文件
- `npm run export`: 导出静态文件

## 故障排除

### 常见问题

1. **构建失败**
   - 检查 Node.js 版本是否满足要求（>=18.0.0）
   - 确保所有依赖已正确安装
   - 检查环境变量配置

2. **API 连接问题**
   - 确认 `NEXT_PUBLIC_API_URL` 设置正确
   - 检查后端服务是否正常运行
   - 验证 CORS 配置

3. **部署后页面空白**
   - 检查浏览器控制台错误
   - 确认所有环境变量已设置
   - 检查构建日志

### 性能优化

- 应用已配置适当的缓存头
- 静态资源会自动优化
- 图片和字体文件已设置长期缓存

## 监控和维护

- 使用 Vercel Analytics 监控性能
- 检查 Vercel Logs 中的错误
- 定期更新依赖包

## 安全注意事项

- 不要在前端暴露敏感信息
- 使用 HTTPS 进行生产部署
- 定期检查依赖的安全漏洞