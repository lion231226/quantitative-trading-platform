/**
 * 可访问性测试配置
 * 用于配置axe-core的规则和阈值
 */

export const a11yConfig = {
  // 全局axe配置
  globalOptions: {
    rules: {
      // 启用WCAG 2.1 AA级别规则
      'color-contrast': { enabled: true },
      'keyboard-navigation': { enabled: true },
      'aria-labels': { enabled: true },
      'focus-management': { enabled: true },
      'heading-order': { enabled: true },
      'landmark-roles': { enabled: true },
      'link-in-text-block': { enabled: true },
      'list-item': { enabled: true },
      'skip-link': { enabled: true },
      'tab-index': { enabled: true },

      // 针对测试环境禁用某些规则
      'bypass': { enabled: false }, // 跳过链接在单元测试中可能不适用
      'document-title': { enabled: false }, // 测试中可能不需要完整文档标题
      'html-has-lang': { enabled: false }, // 测试环境可能不包含完整HTML结构
    },
  },

  // 组件特定配置
  componentConfig: {
    // 按钮组件
    Button: {
      rules: {
        'button-name': { enabled: true },
        'focus-order-semantics': { enabled: true },
      },
    },

    // 表单组件
    Form: {
      rules: {
        'label-title-only': { enabled: true },
        'form-field-multiple-labels': { enabled: true },
        'input-button-name': { enabled: true },
      },
    },

    // 图表组件
    Chart: {
      rules: {
        'image-redundant-alt': { enabled: false }, // 图表可能有替代文本
        'img-alt': { enabled: false }, // Canvas元素可能不需要alt
      },
    },
  },

  // 颜色对比度阈值
  contrastThresholds: {
    AA: {
      normal: 4.5,
      large: 3.0,
      graphical: 3.0,
    },
    AAA: {
      normal: 7.0,
      large: 4.5,
      graphical: 4.5,
    },
  },

  // 测试覆盖率要求
  coverageRequirements: {
    components: 100, // 所有组件必须通过可访问性测试
    keyboardNavigation: 100, // 所有交互元素必须支持键盘导航
    colorContrast: 100, // 所有文本必须达到AA对比度
    screenReader: 100, // 所有功能必须对屏幕阅读器可访问
  },
};