# 量化交易平台 CI/CD 说明

## 🚨 重要说明

此仓库的 CI/CD 流程设计为 **无 Docker 依赖**，以确保 GitHub Actions 的稳定运行。

## 📋 开发环境

### 本地开发（需要Docker）
```bash
# 启动完整的开发环境（包含Redis、后端、前端）
./start.sh

# 或者分步启动
./quick-start.sh
```

### CI/CD 环境（无Docker）
- **前端测试**: Jest + React Testing Library
- **后端测试**: pytest + SQLite (内存数据库)
- **覆盖率报告**: Codecov集成
- **Redis**: 使用GitHub Actions的Redis service

## 🔧 GitHub Actions 工作流

### 主要工作流
- `coverage.yml`: 生成测试覆盖率报告
- `disable-docker.yml`: 明确禁用Docker自动化

### 测试策略
- ✅ 前端测试不需要Docker
- ✅ 后端测试使用内存数据库
- ✅ Redis通过GitHub Actions service提供
- ❌ 不启动完整Docker容器

## 🚫 禁用Docker的原因

1. **GitHub Actions限制**: 标准runner不包含Docker
2. **速度优化**: 无Docker的测试运行更快
3. **成本控制**: 避免使用更大的runner
4. **简化维护**: 减少依赖，提高可靠性

## 📝 开发者注意事项

- 本地开发可以使用Docker (./start.sh)
- CI/CD流程自动适应无Docker环境
- 所有测试都设计为在无Docker环境下运行
- 如需Docker测试，请使用自托管的runner

## 🐛 故障排除

如果看到Docker相关错误：
1. 检查是否在正确的环境中（本地 vs CI/CD）
2. 确认没有意外提交Docker相关脚本到工作流
3. 验证package.json中的测试脚本是否正确