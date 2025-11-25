# Story 3.3: 个性化颜色配置与可访问性支持

Status: drafted

## Story

作为用户,
我希望 能够根据个人习惯调整图表颜色和样式,
以便 获得舒适且符合使用习惯的视觉体验.

## Acceptance Criteria

1. 支持中国市场模式（红涨绿跌）和国际市场模式（绿涨红跌）
2. 实现色盲友好模式，使用形状和纹理区分涨跌
3. 提供用户自定义颜色配置功能
4. 支持明暗主题切换
5. 实现配色方案的保存和导入功能

## Tasks / Subtasks

- [ ] Task 1: 市场颜色模式配置系统 (AC: 1)
  - [ ] Subtask 1.1: 创建市场模式颜色配置数据模型和类型定义
  - [ ] Subtask 1.2: 实现中国市场模式（红涨绿跌）颜色配置
  - [ ] Subtask 1.3: 实现国际市场模式（绿涨红跌）颜色配置
  - [ ] Subtask 1.4: 集成Lightweight Charts颜色主题切换功能

- [ ] Task 2: 色盲友好可访问性支持 (AC: 2)
  - [ ] Subtask 2.1: 设计色盲友好的视觉区分系统
  - [ ] Subtask 2.2: 实现基于形状的涨跌区分（三角形、圆形等）
  - [ ] Subtask 2.3: 实现基于纹理图案的涨跌区分（条纹、点阵等）
  - [ ] Subtask 2.4: 实现色盲模式的自动检测和推荐

- [ ] Task 3: 用户自定义颜色配置界面 (AC: 3)
  - [ ] Subtask 3.1: 创建颜色选择器和配置面板组件
  - [ ] Subtask 3.2: 实现实时颜色预览和应用功能
  - [ ] Subtask 3.3: 支持HSL、RGB、HEX多种颜色格式
  - [ ] Subtask 3.4: 提供颜色和谐度和对比度检查

- [ ] Task 4: 明暗主题切换系统 (AC: 4)
  - [ ] Subtask 4.1: 设计明暗主题的颜色方案
  - [ ] Subtask 4.2: 实现主题切换动画和过渡效果
  - [ ] Subtask 4.3: 集成系统主题自动检测功能
  - [ ] Subtask 4.4: 优化主题切换的用户体验和性能

- [ ] Task 5: 配色方案持久化管理 (AC: 5)
  - [ ] Subtask 5.1: 实现本地存储的颜色配置持久化
  - [ ] Subtask 5.2: 支持配色方案的导出功能（JSON格式）
  - [ ] Subtask 5.3: 支持配色方案的导入和应用功能
  - [ ] Subtask 5.4: 提供预设配色方案库和分享功能

## Dev Notes

**个性化颜色配置核心需求:**
基于Epic 3目标，在Lightweight Charts高性能K线图基础上，实现完整的个性化颜色配置和可访问性支持系统。通过市场模式、色盲友好、自定义配置、主题切换和持久化管理，为不同需求的用户提供舒适、专业的视觉体验。

**技术架构对齐:**
- 基于故事3.2的styleConfigService.ts架构进行扩展
- 集成现有Lightweight Charts 5.0.9颜色配置API
- 复用现有TypeScript类型系统和性能优化策略
- 扩展现有React hooks模式，保持状态管理一致性
- 遵循WCAG 2.1可访问性标准和最佳实践

### Learnings from Previous Story

**From Story 3.2 (Status: done)**

- **StyleConfigService经验**: 已有899行样式配置服务可直接扩展为颜色管理系统
- **Lightweight Charts颜色API**: addMarker、setColor、setTheme等API使用经验可直接应用
- **TypeScript类型系统**: 已建立的完整类型定义可扩展为颜色配置类型系统
- **React状态管理**: useState、useEffect、useCallback的最佳实践可用于颜色配置状态
- **性能优化策略**: 智能缓存、批量操作、防抖优化可用于颜色配置性能管理

**技术债务**: 无重大技术债务 - StyleConfigService架构稳定，Lightweight Charts API成熟，React模式完善

**警告和建议**:
- 颜色配置需要考虑浏览器兼容性和色彩空间转换精度
- 色盲模式的形状和纹理设计需要保证在不同分辨率下的清晰度
- 主题切换需要确保不影响现有的图表交互性能
- 颜色对比度需要满足WCAG AA级标准（4.5:1）
- 配色方案的导出导入需要考虑数据安全和隐私保护

[Source: stories/3-2-intelligent-strategy-signal-dynamic-update-system.md#Dev-Agent-Record]

### Project Structure Notes

**文件结构扩展:**
```
frontend/src/
├── types/
│   ├── kline.types.ts                      # 已存在，需要扩展颜色配置类型
│   └── colorTheme.types.ts                 # 新增：颜色主题完整类型定义
├── services/
│   ├── styleConfigService.ts               # 已存在，需要扩展颜色管理
│   ├── colorThemeService.ts                # 新增：颜色主题管理核心服务
│   ├── accessibilityService.ts             # 新增：可访问性支持服务
│   ├── themePersistenceService.ts          # 新增：主题持久化管理服务
│   └── colorHarmonyService.ts              # 新增：颜色和谐度分析服务
├── components/themes/
│   ├── ColorThemeSelector.tsx              # 新增：颜色主题选择器组件
│   ├── ColorPickerPanel.tsx                # 新增：颜色配置面板
│   ├── ThemePreview.tsx                    # 新增：主题预览组件
│   ├── AccessibilityOptions.tsx            # 新增：可访问性选项面板
│   ├── ColorSchemeLibrary.tsx              # 新增：预设配色方案库
│   └── ThemeExportImport.tsx               # 新增：主题导出导入组件
├── hooks/
│   ├── useColorTheme.ts                    # 新增：颜色主题状态管理
│   ├── useAccessibility.ts                 # 新增：可访问性配置管理
│   └── useThemePersistence.ts              # 新增：主题持久化管理
├── utils/
│   ├── colorThemeHelpers.ts                # 新增：颜色主题工具函数
│   ├── accessibilityHelpers.ts             # 新增：可访问性辅助函数
│   ├── colorConversion.ts                  # 新增：颜色格式转换工具
│   └── wcagCompliance.ts                   # 新增：WCAG合规性检查
└── __tests__/
    ├── colorTheme/                         # 新增：颜色主题测试套件
    ├── accessibility/                      # 新增：可访问性测试
    └── themePersistence/                   # 新增：持久化测试
```

**颜色配置数据要求:**
- 主题模式：中国市场、国际市场、色盲友好、自定义
- 颜色属性：涨跌颜色、背景色、网格线、文字颜色、边框样式
- 可访问性：对比度检查、色盲模式、字体大小、交互提示
- 主题切换：明暗主题、自动检测、过渡动画、性能优化
- 持久化：本地存储、云同步、导出导入、分享功能

**性能优化要求:**
- 颜色配置切换响应时间控制在200ms以内
- 主题切换动画帧率保持在30fps以上
- 颜色预览实时更新，使用防抖优化性能
- 颜色配置缓存策略，支持增量更新
- 支持大量预设方案的高效检索和管理

### References

- [Source: docs/epics.md#Epic-3-专业K线图表与智能可视化系统] - Epic 3完整需求描述
- [Source: docs/epics.md#Story-33-个性化颜色配置与可访问性支持] - 故事原始需求
- [Source: docs/tech-spec.md] - 技术规格约束和架构要求
- [Source: stories/3-2-intelligent-strategy-signal-dynamic-update-system.md] - StyleConfigService集成经验
- [Source: frontend/src/services/styleConfigService.ts] - 现有样式配置服务模式
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/) - 可访问性标准参考
- [Lightweight Charts Color API](https://www.tradingview.com/lightweight-charts/) - 颜色配置API参考

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude-3.5-Sonnet

### Debug Log References

### Completion Notes List

### File List