# 开发者标准操作程序 (Developer SOP)

## 📋 概述

本文档定义了量化交易项目开发者的标准操作程序，确保所有开发活动符合质量保证框架要求，防止虚假声明，确保代码质量。

## 🚀 开发流程标准操作程序

### SOP-001: 开始新故事开发

**目的**: 确保故事开发前的准备工作充分，理解需求明确

**适用场景**: 开始任何新的用户故事开发之前

**操作步骤**:
1. **需求确认**
   ```bash
   # 1.1 阅读故事文件
   cat docs/stories/[story-id].md

   # 1.2 阅读故事上下文
   cat docs/stories/[story-id].context.xml

   # 1.3 阅读相关技术规范
   cat docs/tech-spec-epic-[epic-id].md
   ```

2. **环境准备**
   ```bash
   # 2.1 创建开发分支
   git checkout -b feature/[story-id]

   # 2.2 更新依赖
   cd frontend && npm install

   # 2.3 运行质量门禁确保基础环境正常
   ../scripts/quality-gate.sh --type=dev
   ```

3. **技术方案设计**
   - [ ] 设计组件架构
   - [ ] 设计API接口
   - [ ] 设计测试策略
   - [ ] 估算开发时间

4. **创建开发计划**
   ```markdown
   ## 开发计划 - [Story Name]

   ### 任务分解
   - [ ] Task 1: 任务描述 (预计X小时)
   - [ ] Task 2: 任务描述 (预计Y小时)

   ### 验收标准映射
   - AC1: 实现方案
   - AC2: 实现方案

   ### 质量保证计划
   - 单元测试: 目标覆盖率 > 80%
   - 集成测试: 关键流程覆盖
   - 代码审查: 自检清单
   ```

**质量门禁**:
- ✅ 故事文件已完整阅读
- ✅ 开发环境准备就绪
- ✅ 技术方案已设计
- ✅ 开发计划已创建

### SOP-002: 开发实现过程

**目的**: 确保开发过程中代码质量，及时发现问题

**适用场景**: 代码编写阶段

**操作步骤**:

1. **编码前检查**
   ```bash
   # 每次开始编码前运行
   cd frontend && npm run lint
   npm run test:unit
   ```

2. **增量开发**
   ```bash
   # 2.1 编写代码前先写测试
   # 2.2 小步提交，频繁验证
   git add .
   git commit -m "feat: 实现XXX功能"

   # 2.3 每次提交后运行质量检查
   ../scripts/quality-gate.sh --type=dev
   ```

3. **自检清单**
   ```yaml
   代码质量自检:
     - [ ] TypeScript编译通过
     - [ ] ESLint检查通过
     - [ ] Prettier格式正确
     - [ ] 单元测试通过
     - [ ] 代码注释充分

   功能自检:
     - [ ] 满足验收标准要求
     - [ ] 边界条件处理
     - [ ] 错误处理完善
     - [ ] 性能考虑充分
     - [ ] 安全问题检查
   ```

**质量门禁**:
- ✅ 每次提交前通过基础质量检查
- ✅ 自检清单全部完成
- ✅ 代码增量有对应测试

### SOP-003: 功能验证和测试

**目的**: 确保功能正确实现，测试覆盖充分

**适用场景**: 功能开发完成后

**操作步骤**:

1. **完整功能测试**
   ```bash
   # 1.1 运行完整测试套件
   cd frontend && npm run test

   # 1.2 生成覆盖率报告
   npm run test:coverage

   # 1.3 构建验证
   npm run build
   ```

2. **验收标准验证**
   ```bash
   # 2.1 对每个验收标准进行验证测试
   # 创建验收标准验证脚本
   cat > verify-ac.sh << 'EOF'
   #!/bin/bash
   echo "验证AC1: 参数调整滑块和输入框"
   # 运行相关测试
   npm run test -- --testNamePattern="ParameterControls"

   echo "验证AC2: 实时更新策略回测结果"
   # 运行相关测试
   npm run test -- --testNamePattern="RealTimeUpdate"
   EOF

   chmod +x verify-ac.sh
   ./verify-ac.sh
   ```

3. **手动功能测试**
   - [ ] 启动应用 `npm run dev`
   - [ ] 逐个验证验收标准
   - [ ] 记录测试结果和截图
   - [ ] 测试边界情况和异常场景

4. **性能验证**
   ```bash
   # 4.1 检查关键性能指标
   # 运行性能测试脚本
   npm run test:performance

   # 4.2 检查bundle大小
   npm run build
   du -sh .next/static/chunks/
   ```

**质量门禁**:
- ✅ 所有测试100%通过
- ✅ 测试覆盖率 >= 80%
- ✅ 所有验收标准已验证
- ✅ 性能指标达标
- ✅ 功能演示可执行

### SOP-004: 代码提交和故事完成

**目的**: 确保提交的代码质量达标，故事完成声明真实

**适用场景**: 准备提交代码和完成故事

**操作步骤**:

1. **最终质量检查**
   ```bash
   # 1.1 运行完整质量门禁
   ./scripts/quality-gate.sh --type=review docs/stories/[story-id].md

   # 1.2 如果有失败项，修复后重新运行
   # 直到所有检查通过
   ```

2. **文档更新**
   ```markdown
   # 更新故事文件
   ## Dev Agent Record

   ### Completion Notes
   - Task 1: 具体完成情况描述
   - Task 2: 具体完成情况描述

   ### File List
   - 新增文件: 列表
   - 修改文件: 列表

   ### Test Results
   - 单元测试: XX/XX 通过
   - 集成测试: XX/XX 通过
   - 覆盖率: XX%
   ```

3. **质量声明**
   ```typescript
   // 创建质量声明文件
   const qualityDeclaration = {
     developerName: "your-name",
     storyId: "story-id",
     declarationDate: new Date(),
     checksCompleted: [
       {
         type: "compilation",
         status: "passed",
         details: "TypeScript编译通过，0错误"
       },
       {
         type: "unit-test",
         status: "passed",
         details: "单元测试XX/XX通过，覆盖率XX%"
       },
       {
         type: "acceptance-criteria",
         status: "passed",
         details: "所有验收标准已验证通过"
       }
     ],
     evidence: [
       {
         type: "test-report",
         description: "完整测试报告",
         filePath: "reports/test-report-[timestamp].html"
       },
       {
         type: "coverage-report",
         description: "覆盖率报告",
         filePath: "reports/coverage-[timestamp].txt"
       }
     ]
   };

   // 保存质量声明
   fs.writeFileSync('quality-declaration.json', JSON.stringify(qualityDeclaration, null, 2));
   ```

4. **代码提交**
   ```bash
   # 4.1 添加所有文件
   git add .

   # 4.2 提交代码
   git commit -m "feat: 完成[story-name]实现

   - 实现所有验收标准
   - 测试覆盖率XX%
   - 通过质量门禁检查

   质量声明见: quality-declaration.json"

   # 4.3 推送代码
   git push origin feature/[story-id]
   ```

5. **更新故事状态**
   ```bash
   # 5.1 更新故事状态为 "review"
   # 编辑 docs/stories/[story-id].md
   # 将 Status: in-progress 改为 Status: review

   # 5.2 更新sprint状态
   # 编辑 docs/sprint-status.yaml
   # 将对应故事状态更新为 "review"
   ```

**质量门禁**:
- ✅ 完整质量门禁检查通过
- ✅ 所有文档已更新
- ✅ 质量声明已创建
- ✅ 代码已提交推送
- ✅ 故事状态已正确更新

## 🔍 代码审查标准操作程序

### SOP-005: 代码审查准备

**目的**: 确保审查前准备充分，审查过程高效

**适用场景**: 代码审查员开始审查前

**操作步骤**:

1. **接收审查任务**
   - 确认故事已标记为 "review" 状态
   - 检查质量声明文件是否存在
   - 确认开发者已完成自检

2. **环境准备**
   ```bash
   # 2.1 切换到审查分支
   git checkout origin/feature/[story-id]

   # 2.2 运行质量门禁验证
   ./scripts/quality-gate.sh --type=review docs/stories/[story-id].md

   # 2.3 检查测试状态
   cd frontend && npm run test
   ```

3. **审查材料准备**
   - [ ] 故事文件完整阅读
   - [ ] 故事上下文文件阅读
   - [ ] 技术规范文件阅读
   - [ ] 质量声明文件审查
   - [ ] 变更代码预览

**质量门禁**:
- ✅ 审查环境准备就绪
- ✅ 质量门禁初步验证通过
- ✅ 审查材料准备完整

### SOP-006: 系统性代码审查

**目的**: 确保审查全面、深入，不遗漏任何问题

**适用场景**: 进行代码审查时

**操作步骤**:

1. **自动化验证**
   ```bash
   # 1.1 重新运行所有检查
   ./scripts/quality-gate.sh --type=review docs/stories/[story-id].md

   # 1.2 验证测试结果
   cd frontend && npm run test:coverage

   # 1.3 验证构建成功
   npm run build
   ```

2. **验收标准验证**
   ```yaml
   验收标准审查清单:
     AC1: 实现参数调整滑块和输入框
       - [ ] 代码实现存在: ParameterControls.tsx
       - [ ] 功能正确验证: 测试通过
       - [ ] 用户体验良好: 界面友好
       - [ ] 边界条件处理: 输入验证

     AC2: 实时更新策略回测结果
       - [ ] 响应时间达标: <500ms
       - [ ] 防抖机制实现: parameterService.ts
       - [ ] 缓存策略合理: React Query配置
       - [ ] 错误处理完善: 异常情况处理
   ```

3. **任务完成验证**
   ```yaml
   任务完成审查清单:
     Task 1: 参数控制组件开发
       - [ ] 声称完成: 是
       - [ ] 实际验证: 文件存在，功能正常
       - [ ] 测试覆盖: 单元测试通过
       - [ ] 代码质量: ESLint通过
       - [ ] 结论: VERIFIED COMPLETE
   ```

4. **代码质量审查**
   ```yaml
   代码质量审查清单:
     架构设计:
       - [ ] 组件结构合理
       - [ ] 职责分离清晰
       - [ ] 依赖关系正确
       - [ ] 可扩展性良好

     代码实现:
       - [ ] 命名规范一致
       - [ ] 注释充分准确
       - [ ] 错误处理完善
       - [ ] 性能考虑充分

     测试质量:
       - [ ] 测试覆盖充分
       - [ ] 测试用例合理
       - [ ] 边界条件测试
       - [ ] 集成测试完整
   ```

5. **安全性审查**
   ```yaml
   安全性审查清单:
     输入验证:
       - [ ] 参数验证完整
       - [ ] 类型检查正确
       - [ ] 范围限制合理
       - [ ] 特殊字符处理

     数据安全:
       - [ ] 敏感信息保护
       - [ ] 本地存储安全
       - [ ] API调用安全
       - [ ] 错误信息安全
   ```

**质量门禁**:
- ✅ 自动化验证全部通过
- ✅ 验收标准全部验证
- ✅ 任务完成真实性确认
- ✅ 代码质量达标
- ✅ 安全性审查通过

### SOP-007: 审查结论和反馈

**目的**: 确保审查结论准确，反馈清晰可执行

**适用场景**: 完成代码审查后

**操作步骤**:

1. **生成审查报告**
   ```markdown
   ## Senior Developer Review (AI)

   ### Reviewer: [审查员姓名]
   ### Date: [审查日期]
   ### Outcome: [APPROVE/CHANGES_REQUESTED/BLOCKED]

   ### Summary
   [审查摘要，主要发现和结论]

   ### Acceptance Criteria Coverage
   | AC# | Description | Status | Evidence |
   |-----|-------------|--------|----------|

   ### Task Completion Validation
   | Task | Marked As | Verified As | Evidence |
   |------|-----------|--------------|----------|

   ### Action Items
   - [ ] [High] 修复TypeScript编译错误 (AC #1) [file: path:line]
   - [ ] [Medium] 添加单元测试覆盖 [file: path]
   ```

2. **更新故事文件**
   ```bash
   # 将审查报告追加到故事文件
   cat review-report.md >> docs/stories/[story-id].md
   ```

3. **更新状态**
   ```yaml
   根据审查结果更新状态:
     APPROVE:
       - 故事状态: done
       - Sprint状态: done

     CHANGES_REQUESTED:
       - 故事状态: in-progress
       - Sprint状态: in-progress

     BLOCKED:
       - 故事状态: review
       - Sprint状态: review
   ```

4. **反馈沟通**
   - [ ] 通知开发者审查结果
   - [ ] 解释具体问题和建议
   - [ ] 协助制定修复计划
   - [ ] 确认修复时间预期

**质量门禁**:
- ✅ 审查报告完整准确
- ✅ 故事文件已更新
- ✅ 状态更新正确
- ✅ 反馈沟通已完成

## ⚠️ 违规处理程序

### SOP-008: 虚假声明处理

**目的**: 严肃处理虚假声明行为，维护开发诚信

**适用场景**: 发现虚假声明时

**操作步骤**:

1. **发现虚假声明**
   - 审查员发现声称完成但实际未完成
   - 自动化检查发现质量问题
   - 测试验证发现功能缺失

2. **启动调查**
   ```bash
   # 2.1 保存证据
   mkdir -p evidence/[story-id]
   cp -r reports/ evidence/[story-id]/
   git log > evidence/[story-id]/git-log.txt

   # 2.2 记录问题详情
   cat > evidence/[story-id]/investigation.md << EOF
   ## 虚假声明调查报告

   故事ID: [story-id]
   开发者: [developer-name]
   审查员: [reviewer-name]
   发现时间: [timestamp]

   问题描述:
   - [ ] 任务声称完成但实际未完成
   - [ ] 验收标准声称满足但实际缺失
   - [ ] 测试声称通过但实际失败
   - [ ] 质量声明虚假

   证据详情:
   1. 代码检查结果
   2. 测试执行结果
   3. 质量门禁报告
   4. 功能验证截图
   EOF
   ```

3. **处理决策**
   ```yaml
   处理级别:
     第一次违规:
       - 口头警告
       - 重新培训质量保证流程
       - 要求重新完成并验证
       - 记录在开发者档案

     第二次违规:
       - 书面警告
       - 暂停开发权限1周
       - 强制参加质量培训
       - 绩效评估降级

     第三次违规:
       - 取消开发权限
       - 项目除名
       - 通知人事部门
       - 影响职业发展
   ```

4. **预防措施**
   - [ ] 加强质量保证培训
   - [ ] 完善自动化检查
   - [ ] 强化审查流程
   - [ ] 建立诚信文化

**质量门禁**:
- ✅ 违规行为已确认
- ✅ 证据已完整保存
- ✅ 处理决策已执行
- ✅ 预防措施已实施

## 📊 质量监控和报告

### SOP-009: 定期质量评估

**目的**: 持续监控项目质量，及时发现和解决问题

**适用场景**: 定期质量评估

**操作步骤**:

1. **数据收集**
   ```bash
   # 1.1 收集质量指标
   npm run test:coverage > reports/coverage-$(date +%Y%m%d).txt
   npm run lint > reports/lint-$(date +%Y%m%d).txt
   ./scripts/quality-gate.sh --type=release > reports/quality-gate-$(date +%Y%m%d).txt

   # 1.2 收集开发效率数据
   git log --since="1 month ago" --pretty=format:"%h,%an,%s" > reports/commits-$(date +%Y%m%d).csv
   ```

2. **生成质量报告**
   ```bash
   # 创建质量报告脚本
   cat > generate-quality-report.sh << 'EOF'
   #!/bin/bash

   echo "# 质量评估报告 - $(date +%Y-%m-%d)" > quality-report.md
   echo "" >> quality-report.md

   echo "## 代码质量指标" >> quality-report.md
   echo "- 测试覆盖率: $(grep 'Lines' reports/coverage-*.txt | tail -1)" >> quality-report.md
   echo "- ESLint错误: $(grep -c 'error' reports/lint-*.txt || echo '0')" >> quality-report.md
   echo "- 构建状态: $(grep '构建' reports/quality-gate-*.txt | tail -1)" >> quality-report.md
   echo "" >> quality-report.md

   echo "## 开发效率指标" >> quality-report.md
   echo "- 本月提交次数: $(wc -l < reports/commits-*.csv)" >> quality-report.md
   echo "- 活跃开发者: $(cut -d',' -f2 reports/commits-*.csv | sort -u | wc -l)" >> quality-report.md
   echo "" >> quality-report.md

   echo "## 质量趋势分析" >> quality-report.md
   echo "详细数据分析请参考附件文件" >> quality-report.md
   EOF

   chmod +x generate-quality-report.sh
   ./generate-quality-report.sh
   ```

3. **质量评审会议**
   ```yaml
   月度质量评审议程:
     1. 质量指标回顾
        - 代码覆盖率趋势
        - 缺陷密度变化
        - 开发效率分析

     2. 问题分析和解决
        - 本月质量问题总结
        - 根本原因分析
        - 改进措施制定

     3. 流程改进讨论
        - 质量保证流程优化
        - 工具和自动化改进
        - 团队培训需求

     4. 下月质量目标
        - 具体指标设定
        - 改进重点确定
        - 责任人分配
   ```

**质量门禁**:
- ✅ 质量数据已收集
- ✅ 质量报告已生成
- ✅ 评审会议已召开
- ✅ 改进计划已制定

---

**文档版本**: v1.0
**创建日期**: 2025-11-01
**作者**: Amelia (Developer Agent)
**审核人**: 项目管理团队
**生效日期**: 2025-11-01
**下次更新**: 根据实施情况定期更新

## 📚 相关文档

- [质量保证框架](quality-assurance-framework.md)
- [代码审查指南](code-review-guidelines.md)
- [测试策略文档](testing-strategy.md)
- [持续集成配置](ci-cd-setup.md)
- [开发环境设置](development-setup.md)