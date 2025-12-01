/**
 * 可访问性专用ESLint配置
 * 扩展基础配置，专注于可访问性规则
 */

module.exports = {
  extends: ['.eslintrc.js'],
  plugins: ['jsx-a11y'],
  rules: {
    // 严格的可访问性规则
    'jsx-a11y/alt-text': 'error', // img必须有alt属性
    'jsx-a11y/anchor-has-content': 'error', // a标签必须有内容
    'jsx-a11y/anchor-is-valid': 'error', // a标签必须有href或disabled
    'jsx-a11y/aria-activedescendant-has-tabindex': 'error', // aria-activedescendant必须有tabindex
    'jsx-a11y/aria-props': 'error', // aria属性必须有效
    'jsx-a11y/aria-proptypes': 'error', // aria属性类型必须正确
    'jsx-a11y/aria-role': 'error', // role属性必须有效
    'jsx-a11y/aria-unsupported-elements': 'error', // 不支持的元素不能有aria属性
    'jsx-a11y/click-events-have-key-events': 'error', // 有click事件的可交互元素必须有键盘事件
    'jsx-a11y/heading-has-content': 'error', // 标题必须有内容
    'jsx-a11y/html-has-lang': 'error', // html标签必须有lang属性
    'jsx-a11y/img-redundant-alt': 'error', // img的alt文本不应冗余
    'jsx-a11y/interactive-supports-focus': 'error', // 可交互元素必须支持焦点
    'jsx-a11y/label-has-associated-control': 'error', // label必须关联表单控件
    'jsx-a11y/media-has-caption': 'error', // 媒体元素必须有字幕
    'jsx-a11y/mouse-events-have-key-events': 'error', // 有鼠标事件的元素必须有键盘事件
    'jsx-a11y/no-access-key': 'error', // 不应使用accesskey
    'jsx-a11y/no-autofocus': 'warn', // 谨慎使用autofocus
    'jsx-a11y/no-distracting-elements': 'error', // 不应使用分散注意力的元素
    'jsx-a11y/no-interactive-element-to-noninteractive-role': 'error', // 可交互元素不能设置非交互role
    'jsx-a11y/no-noninteractive-element-interactions': 'error', // 非交互元素不应有交互处理器
    'jsx-a11y/no-noninteractive-element-to-interactive-role': 'error', // 非交互元素不能设置交互role
    'jsx-a11y/no-noninteractive-tabindex': 'error', // 非交互元素不应有tabindex
    'jsx-a11y/no-redundant-roles': 'error', // 不应设置冗余的role
    'jsx-a11y/no-static-element-interactions': 'warn', // 静态元素不应有交互处理器
    'jsx-a11y/role-has-required-aria-props': 'error', // role必须有必需的aria属性
    'jsx-a11y/role-supports-aria-props': 'error', // role必须支持设置的aria属性
    'jsx-a11y/scope': 'error', // scope属性只能在th上使用
    'jsx-a11y/tabindex-no-positive': 'error', // 不应使用正的tabindex

    // 推荐的可访问性规则
    'jsx-a11y/aria-bridge': 'error', // 使用aria-bridge模式
    'jsx-a11y/control-has-associated-label': 'warn', // 表单控件应有标签
    'jsx-a11y/heading-has-content': 'error', // 标题必须有内容
    'jsx-a11y/html-has-lang': 'error', // html必须有lang属性
    'jsx-a11y/iframe-has-title': 'error', // iframe必须有title
    'jsx-a11y/img-alt-text': 'error', // img必须alt文本
    'jsx-a11y/label-has-for': 'error', // label应该有for属性
    'jsx-a11y/no-onchange': 'warn', // 谨慎使用onchange
    'jsx-a11y/no-referent-in-aria-activedescendant': 'error', // aria-activedescendant引用有效元素
    'jsx-a11y/prefer-tag-over-role': 'error', // 优先使用语义化标签而非role

    // 针对Chart.js和图表组件的特殊处理
    'jsx-a11y/no-noninteractive-tabindex': ['error', {
      allowExpressionValues: true,
      roles: ['img'], // 允许canvas图表元素使用tabindex
    }],

    // 自定义规则 - 检查WCAG 2.1 AA要求
    'jsx-a11y/color-contrast': 'off', // 需要专门的工具检查颜色对比度
  },
  overrides: [
    {
      // 测试文件的规则宽松一些
      files: ['**/*.test.{ts,tsx}', '**/*.spec.{ts,tsx}'],
      rules: {
        'jsx-a11y/no-autofocus': 'off',
        'jsx-a11y/no-static-element-interactions': 'off',
        'jsx-a11y/click-events-have-key-events': 'warn',
        'jsx-a11y/mouse-events-have-key-events': 'warn',
      },
    },
    {
      // Chart组件的特殊规则
      files: ['**/charts/**/*.{ts,tsx}'],
      rules: {
        'jsx-a11y/no-noninteractive-element-interactions': 'warn', // Canvas可能需要交互
        'jsx-a11y/no-noninteractive-element-to-interactive-role': 'warn', // Canvas可能有交互role
      },
    },
  ],
};