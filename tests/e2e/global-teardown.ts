import { FullConfig } from '@playwright/test';

async function globalTeardown(config: FullConfig) {
  console.log('🧹 E2E测试全局清理开始...');

  try {
    // 清理测试数据
    const fs = require('fs');
    const path = require('path');
    const resultsDir = path.join(__dirname, '../e2e-results');

    if (fs.existsSync(resultsDir)) {
      const files = fs.readdirSync(resultsDir);
      console.log(`📁 清理测试结果文件: ${files.length} 个文件`);

      // 保留最新的测试结果，删除旧的
      const maxFilesToKeep = 10;
      if (files.length > maxFilesToKeep) {
        files
          .sort((a: string, b: string) => {
            const statA = fs.statSync(path.join(resultsDir, a));
            const statB = fs.statSync(path.join(resultsDir, b));
            return statA.mtime.getTime() - statB.mtime.getTime();
          })
          .slice(0, files.length - maxFilesToKeep)
          .forEach((file: string) => {
            fs.unlinkSync(path.join(resultsDir, file));
          });
      }
    }

    // 清理临时文件
    const tempDirs = [
      path.join(__dirname, '../temp'),
      path.join(__dirname, '../coverage'),
    ];

    tempDirs.forEach(dir => {
      if (fs.existsSync(dir)) {
        try {
          fs.rmSync(dir, { recursive: true, force: true });
          console.log(`🗑️ 清理临时目录: ${dir}`);
        } catch (error) {
          console.log(`⚠️ 清理目录失败: ${dir}`, error);
        }
      }
    });

    console.log('✅ E2E测试全局清理完成');
  } catch (error) {
    console.error('❌ 全局清理失败:', error);
  }
}

export default globalTeardown;