# 可访问性开发指南

本指南提供在量化交易平台中实现WCAG 2.1 AA标准可访问性的最佳实践和规范。

## 目录
1. [核心原则](#核心原则)
2. [组件开发规范](#组件开发规范)
3. [测试指南](#测试指南)
4. [常见问题解决方案](#常见问题解决方案)
5. [工具和资源](#工具和资源)

## 核心原则

### POUR原则
- **Perceivable (可感知性)**: 信息必须以用户能够感知的方式呈现
- **Operable (可操作性)**: UI组件和导航必须是可操作的
- **Understandable (可理解性)**: 信息和UI操作必须是可理解的
- **Robust (健壮性)**: 内容必须足够健壮，能够被各种辅助技术解析

### WCAG 2.1 AA要求
- 颜色对比度：正常文本4.5:1，大文本3:1
- 键盘导航：所有功能必须通过键盘可访问
- 焦点管理：清晰的焦点指示器和逻辑的Tab顺序
- 屏幕阅读器：适当的ARIA标签和语义化HTML

## 组件开发规范

### 按钮组件
```tsx
// ✅ 正确示例
<button
  onClick={handleClick}
  aria-label="关闭对话框"
  aria-describedby="close-help"
>
  <CloseIcon />
</button>

// ❌ 错误示例
<div onClick={handleClick}>关闭</div> // 缺少语义化标签
```

### 表单组件
```tsx
// ✅ 正确示例
<label htmlFor="email">
  邮箱地址
  <span className="required" aria-label="必填">*</span>
</label>
<input
  id="email"
  type="email"
  required
  aria-describedby="email-help email-error"
  aria-invalid={hasError}
/>
<div id="email-help" className="sr-only">
  请输入有效的邮箱地址
</div>
{hasError && (
  <div id="email-error" role="alert" aria-live="polite">
    {errorMessage}
  </div>
)}
```

### 图表组件
```tsx
// ✅ 正确示例 - Chart.js可访问性
<div className="chart-container">
  <canvas
    ref={chartRef}
    role="img"
    aria-label="价格走势图表"
    aria-describedby="chart-description"
  />
  <div id="chart-description" className="sr-only">
    显示2023年1月至12月的价格走势，包含最高价、最低价和收盘价数据
  </div>

  <!-- 键盘导航支持 -->
  <button
    className="chart-next"
    onClick={nextDataPoint}
    aria-label="下一个数据点"
  >
    →
  </button>
</div>
```

### 通知和动态内容
```tsx
// ✅ 正确示例
<div
  role="status"
  aria-live="polite"
  aria-atomic="true"
  className="notification"
>
  数据已成功更新
</div>
```

## 测试指南

### 自动化测试配置
```tsx
// 在测试文件中使用
import { expectAccessible } from '@/utils/accessibility/test-utils';

describe('组件可访问性测试', () => {
  it('应该无障碍', async () => {
    const { container } = render(<MyComponent />);
    await expectAccessible(container);
  });
});
```

### 键盘导航测试
```tsx
import { testKeyboardNavigation } from '@/utils/accessibility/test-utils';

it('应该支持键盘导航', () => {
  const { getByRole } = render(<MyComponent />);
  const element = getByRole('button');
  testKeyboardNavigation(element);
});
```

### ARIA属性测试
```tsx
import { testAriaAttributes } from '@/utils/accessibility/test-utils';

it('应该有正确的ARIA属性', () => {
  const { getByRole } = render(
    <button aria-label="保存文件" aria-expanded="false">
      <SaveIcon />
    </button>
  );

  const button = getByRole('button');
  testAriaAttributes(button, {
    'aria-label': '保存文件',
    'aria-expanded': 'false',
  });
});
```

## 常见问题解决方案

### 1. 焦点管理问题
**问题**: 自定义组件失去焦点
**解决**: 使用ref和focus管理
```tsx
const CustomButton = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ children, ...props }, ref) => (
    <button ref={ref} {...props}>
      {children}
    </button>
  )
);
```

### 2. 颜色对比度问题
**问题**: 文本和背景对比度不足
**解决**: 使用可访问的颜色系统
```css
/* 使用设计令牌确保对比度 */
.text-primary {
  color: var(--text-primary); /* 确保与背景对比度 >= 4.5:1 */
}
```

### 3. 图标按钮问题
**问题**: 图标按钮没有文本描述
**解决**: 添加aria-label
```tsx
<button aria-label="删除项目" onClick={handleDelete}>
  <TrashIcon />
</button>
```

### 4. 动态内容问题
**问题**: 屏幕阅读器无法感知动态更新的内容
**解决**: 使用aria-live区域
```tsx
<div aria-live="polite" aria-atomic="true">
  {statusMessage}
</div>
```

## 工具和资源

### 开发工具
- **React Developer Tools**: 检查组件结构和props
- **axe DevTools**: 浏览器扩展，实时检查可访问性
- **Color Contrast Analyzer**: 检查颜色对比度
- **WAVE**: Web可访问性评估工具

### 测试工具
- **jest-axe**: 自动化可访问性测试
- **@axe-core/react**: React可访问性测试
- **eslint-plugin-jsx-a11y**: 代码linting规则

### 验证工具
- **NVDA/JAWS/VoiceOver**: 屏幕阅读器测试
- **键盘导航测试**: 仅使用键盘操作应用
- **高对比度模式**: 测试高对比度主题

### 在线资源
- [WCAG 2.1 指南](https://www.w3.org/WAI/WCAG21/quickref/)
- [React 可访问性指南](https://react.dev/learn/accessibility)
- [WebAIM 可访问性检查清单](https://webaim.org/standards/wcag/checklist)
- [ARIA 实践指南](https://www.w3.org/TR/wai-aria-practices-1.1/)

## 代码审查清单

在提交代码前，确保检查以下项目：

### HTML结构
- [ ] 使用语义化HTML标签
- [ ] 正确的标题层级结构 (h1-h6)
- [ ] 图片有适当的alt文本
- [ ] 表单控件有相关联的标签

### ARIA属性
- [ ] 使用适当的role属性
- [ ] 交互元素有aria-label或aria-labelledby
- [ ] 状态属性正确设置 (aria-expanded, aria-selected等)
- [ ] 动态内容更新使用aria-live

### 键盘导航
- [ ] 所有交互元素可通过Tab键访问
- [ ] 有清晰的焦点指示器
- [ ] Tab顺序逻辑清晰
- [ ] 支持Enter和Space键激活

### 颜色和视觉
- [ ] 文本和背景对比度 >= 4.5:1
- [ ] 信息不仅依赖颜色传达
- [ ] 状态变化有视觉和非视觉指示

### 测试
- [ ] 通过自动化axe测试
- [ ] 进行键盘导航测试
- [ ] 屏幕阅读器测试通过
- [ ] 无可访问性ESLint错误