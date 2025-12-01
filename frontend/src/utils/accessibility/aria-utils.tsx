/**
 * ARIA工具库
 * 提供标准化的ARIA属性和模式实现
 */

/**
 * ARIA角色定义
 */
export const ARIA_ROLES = {
  // 地标角色
  MAIN: 'main',
  NAVIGATION: 'navigation',
  BANNER: 'banner',
  COMPLEMENTARY: 'complementary',
  CONTENTINFO: 'contentinfo',
  SEARCH: 'search',
  FORM: 'form',
  REGION: 'region',

  // 交互组件角色
  BUTTON: 'button',
  LINK: 'link',
  CHECKBOX: 'checkbox',
  RADIO: 'radio',
  RADIOGROUP: 'radiogroup',
  TABLIST: 'tablist',
  TAB: 'tab',
  TABPANEL: 'tabpanel',
  LISTBOX: 'listbox',
  OPTION: 'option',
  COMBOBOX: 'combobox',
  MENU: 'menu',
  MENUITEM: 'menuitem',
  MENUBAR: 'menubar',
  TREE: 'tree',
  TREEITEM: 'treeitem',
  GRID: 'grid',
  GRIDCELL: 'gridcell',
  DIALOG: 'dialog',
  ALERT: 'alert',
  ALERTDIALOG: 'alertdialog',
  TOOLTIP: 'tooltip',
  PROGRESSBAR: 'progressbar',
  SPINBUTTON: 'spinbutton',
  SLIDER: 'slider',
  SWITCH: 'switch',
} as const;

/**
 * ARIA状态属性
 */
export const ARIA_STATES = {
  // 状态
  BUSY: 'aria-busy',
  CHECKED: 'aria-checked',
  DISABLED: 'aria-disabled',
  EXPANDED: 'aria-expanded',
  GRABBED: 'aria-grabbed',
  HIDDEN: 'aria-hidden',
  INVALID: 'aria-invalid',
  PRESSED: 'aria-pressed',
  SELECTED: 'aria-selected',

  // 属性
  ACTIVEDESCENDANT: 'aria-activedescendant',
  ATOMIC: 'aria-atomic',
  AUTOCOMPLETE: 'aria-autocomplete',
  COLCOUNT: 'aria-colcount',
  COLINDEX: 'aria-colindex',
  COLSPAN: 'aria-colspan',
  CONTROLS: 'aria-controls',
  DESCRIBEDBY: 'aria-describedby',
  DROPEFFECT: 'aria-dropeffect',
  FLOWTO: 'aria-flowto',
  HASPOPUP: 'aria-haspopup',
  LABEL: 'aria-label',
  LABELLEDBY: 'aria-labelledby',
  LEVEL: 'aria-level',
  LIVE: 'aria-live',
  MODAL: 'aria-modal',
  MULTILINE: 'aria-multiline',
  MULTISELECTABLE: 'aria-multiselectable',
  ORIENTATION: 'aria-orientation',
  OWNS: 'aria-owns',
  POSINSET: 'aria-posinset',
  READONLY: 'aria-readonly',
  RELEVANT: 'aria-relevant',
  REQUIRED: 'aria-required',
  ROWCOUNT: 'aria-rowcount',
  ROWINDEX: 'aria-rowindex',
  ROWSPAN: 'aria-rowspan',
  SETSIZE: 'aria-setsize',
  SORT: 'aria-sort',
  VALUEMAX: 'aria-valuemax',
  VALUEMIN: 'aria-valuemin',
  VALUENOW: 'aria-valuenow',
  VALUETEXT: 'aria-valuetext',
} as const;

/**
 * ARIA属性值定义
 */
export const ARIA_VALUES = {
  BOOLEAN: {
    TRUE: 'true',
    FALSE: 'false',
    UNDEFINED: undefined,
  },

  LIVE_REGIONS: {
    POLITE: 'polite',
    ASSERTIVE: 'assertive',
    OFF: 'off',
  },

  ORIENTATION: {
    HORIZONTAL: 'horizontal',
    VERTICAL: 'vertical',
  },

  AUTOCOMPLETE: {
    INLINE: 'inline',
    LIST: 'list',
    BOTH: 'both',
    NONE: 'none',
  },

  HASPOPUP: {
    TRUE: 'true',
    FALSE: 'false',
    MENU: 'menu',
    LISTBOX: 'listbox',
    TREE: 'tree',
    GRID: 'grid',
    DIALOG: 'dialog',
  },

  SORT: {
    ASCENDING: 'ascending',
    DESCENDING: 'descending',
    NONE: 'none',
    OTHER: 'other',
  },
} as const;

/**
 * 生成唯一ID的工具函数
 */
const idCounter = 0;
export const generateAriaId = (prefix: string = 'aria'): string => {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

/**
 * 创建关联的ID
 */
export const createAssociatedIds = (...prefixes: string[]): Record<string, string> => {
  const ids: Record<string, string> = {};
  prefixes.forEach(prefix => {
    ids[prefix] = generateAriaId(prefix);
  });
  return ids;
};

/**
 * ARIA属性构建器
 */
export class AriaAttributeBuilder {
  private attributes: Record<string, string | undefined> = {};

  constructor() {
    this.attributes = {};
  }

  /**
   * 设置aria-label
   */
  label(label: string): this {
    this.attributes[ARIA_STATES.LABEL] = label;
    return this;
  }

  /**
   * 设置aria-labelledby
   */
  labelledBy(id: string): this {
    this.attributes[ARIA_STATES.LABELLEDBY] = id;
    return this;
  }

  /**
   * 设置aria-describedby
   */
  describedBy(id: string): this {
    this.attributes[ARIA_STATES.DESCRIBEDBY] = id;
    return this;
  }

  /**
   * 设置aria-expanded
   */
  expanded(expanded: boolean): this {
    this.attributes[ARIA_STATES.EXPANDED] = expanded ? ARIA_VALUES.BOOLEAN.TRUE : ARIA_VALUES.BOOLEAN.FALSE;
    return this;
  }

  /**
   * 设置aria-selected
   */
  selected(selected: boolean): this {
    this.attributes[ARIA_STATES.SELECTED] = selected ? ARIA_VALUES.BOOLEAN.TRUE : ARIA_VALUES.BOOLEAN.FALSE;
    return this;
  }

  /**
   * 设置aria-checked
   */
  checked(checked: boolean): this {
    this.attributes[ARIA_STATES.CHECKED] = checked ? ARIA_VALUES.BOOLEAN.TRUE : ARIA_VALUES.BOOLEAN.FALSE;
    return this;
  }

  /**
   * 设置aria-pressed
   */
  pressed(pressed: boolean): this {
    this.attributes[ARIA_STATES.PRESSED] = pressed ? ARIA_VALUES.BOOLEAN.TRUE : ARIA_VALUES.BOOLEAN.FALSE;
    return this;
  }

  /**
   * 设置aria-disabled
   */
  disabled(disabled: boolean): this {
    this.attributes[ARIA_STATES.DISABLED] = disabled ? ARIA_VALUES.BOOLEAN.TRUE : ARIA_VALUES.BOOLEAN.FALSE;
    return this;
  }

  /**
   * 设置aria-required
   */
  required(required: boolean): this {
    this.attributes[ARIA_STATES.REQUIRED] = required ? ARIA_VALUES.BOOLEAN.TRUE : ARIA_VALUES.BOOLEAN.FALSE;
    return this;
  }

  /**
   * 设置aria-invalid
   */
  invalid(invalid: boolean): this {
    this.attributes[ARIA_STATES.INVALID] = invalid ? ARIA_VALUES.BOOLEAN.TRUE : ARIA_VALUES.BOOLEAN.FALSE;
    return this;
  }

  /**
   * 设置aria-hidden
   */
  hidden(hidden: boolean): this {
    this.attributes[ARIA_STATES.HIDDEN] = hidden ? ARIA_VALUES.BOOLEAN.TRUE : ARIA_VALUES.BOOLEAN.FALSE;
    return this;
  }

  /**
   * 设置aria-live
   */
  live(politeness: 'polite' | 'assertive' | 'off'): this {
    this.attributes[ARIA_STATES.LIVE] = politeness;
    return this;
  }

  /**
   * 设置aria-atomic
   */
  atomic(atomic: boolean): this {
    this.attributes[ARIA_STATES.ATOMIC] = atomic ? ARIA_VALUES.BOOLEAN.TRUE : ARIA_VALUES.BOOLEAN.FALSE;
    return this;
  }

  /**
   * 设置aria-orientation
   */
  orientation(orientation: 'horizontal' | 'vertical'): this {
    this.attributes[ARIA_STATES.ORIENTATION] = orientation;
    return this;
  }

  /**
   * 设置aria-haspopup
   */
  hasPopup(type: 'true' | 'false' | 'menu' | 'listbox' | 'tree' | 'grid' | 'dialog'): this {
    this.attributes[ARIA_STATES.HASPOPUP] = type;
    return this;
  }

  /**
   * 设置aria-modal
   */
  modal(modal: boolean): this {
    this.attributes[ARIA_STATES.MODAL] = modal ? ARIA_VALUES.BOOLEAN.TRUE : ARIA_VALUES.BOOLEAN.FALSE;
    return this;
  }

  /**
   * 设置滑块值属性
   */
  sliderValue(value: number, min: number, max: number, text?: string): this {
    this.attributes[ARIA_STATES.VALUENOW] = value.toString();
    this.attributes[ARIA_STATES.VALUEMIN] = min.toString();
    this.attributes[ARIA_STATES.VALUEMAX] = max.toString();
    if (text) {
      this.attributes[ARIA_STATES.VALUETEXT] = text;
    }
    return this;
  }

  /**
   * 设置列表项属性
   */
  listOption(position: number, setSize: number): this {
    this.attributes[ARIA_STATES.POSINSET] = position.toString();
    this.attributes[ARIA_STATES.SETSIZE] = setSize.toString();
    return this;
  }

  /**
   * 设置表格单元格属性
   */
  tableCell(colIndex: number, rowIndex: number, colSpan?: number, rowSpan?: number): this {
    this.attributes[ARIA_STATES.COLINDEX] = colIndex.toString();
    this.attributes[ARIA_STATES.ROWINDEX] = rowIndex.toString();
    if (colSpan && colSpan > 1) {
      this.attributes[ARIA_STATES.COLSPAN] = colSpan.toString();
    }
    if (rowSpan && rowSpan > 1) {
      this.attributes[ARIA_STATES.ROWSPAN] = rowSpan.toString();
    }
    return this;
  }

  /**
   * 构建ARIA属性对象
   */
  build(): Record<string, string | undefined> {
    return { ...this.attributes };
  }

  /**
   * 重置构建器
   */
  reset(): this {
    this.attributes = {};
    return this;
  }
}

/**
 * 便捷函数：创建ARIA属性
 */
export const createAriaProps = (): AriaAttributeBuilder => {
  return new AriaAttributeBuilder();
};

/**
 * 常用ARIA模式预设
 */
export const ARIA_PATTERNS = {
  /**
   * 按钮模式
   */
  button: (label: string, pressed?: boolean, disabled?: boolean) =>
    createAriaProps()
      .label(label)
      .role(ARIA_ROLES.BUTTON)
      .pressed(pressed || false)
      .disabled(disabled || false)
      .build(),

  /**
   * 链接模式
   */
  link: (label: string) =>
    createAriaProps()
      .role(ARIA_ROLES.LINK)
      .label(label)
      .build(),

  /**
   * 选项卡模式
   */
  tab: (label: string, selected: boolean, controls: string, panelId: string) =>
    createAriaProps()
      .role(ARIA_ROLES.TAB)
      .label(label)
      .selected(selected)
      .controls(controls)
      .build(),

  /**
   * 选项卡面板模式
   */
  tabPanel: (labelledBy: string, hidden?: boolean) =>
    createAriaProps()
      .role(ARIA_ROLES.TABPANEL)
      .labelledBy(labelledBy)
      .hidden(hidden !== false)
      .build(),

  /**
   * 滑块模式
   */
  slider: (label: string, value: number, min: number, max: number, valueText?: string) =>
    createAriaProps()
      .role(ARIA_ROLES.SLIDER)
      .label(label)
      .sliderValue(value, min, max, valueText)
      .build(),

  /**
   * 复选框模式
   */
  checkbox: (label: string, checked: boolean, required?: boolean) =>
    createAriaProps()
      .role(ARIA_ROLES.CHECKBOX)
      .label(label)
      .checked(checked)
      .required(required || false)
      .build(),

  /**
   * 单选按钮模式
   */
  radioButton: (label: string, checked: boolean, name: string) =>
    createAriaProps()
      .role(ARIA_ROLES.RADIO)
      .label(label)
      .checked(checked)
      .build(),

  /**
   * 对话框模式
   */
  dialog: (label: string, labelledBy?: string) =>
    createAriaProps()
      .role(ARIA_ROLES.DIALOG)
      .label(label)
      .labelledBy(labelledBy || '')
      .modal(true)
      .build(),

  /**
   * 警告模式
   */
  alert: (message: string) =>
    createAriaProps()
      .role(ARIA_ROLES.ALERT)
      .live(ARIA_VALUES.LIVE_REGIONS.ASSERTIVE)
      .atomic(true)
      .build(),

  /**
   * Live区域模式
   */
  liveRegion: (politeness: 'polite' | 'assertive' | 'off' = 'polite', atomic = false) =>
    createAriaProps()
      .live(politeness)
      .atomic(atomic)
      .build(),

  /**
   * 列表框模式
   */
  listBox: (label: string, multiSelectable = false) =>
    createAriaProps()
      .role(ARIA_ROLES.LISTBOX)
      .label(label)
      .multiSelectable(multiSelectable)
      .build(),

  /**
   * 列表选项模式
   */
  listBoxOption: (label: string, selected: boolean, position: number, setSize: number) =>
    createAriaProps()
      .role(ARIA_ROLES.OPTION)
      .label(label)
      .selected(selected)
      .listOption(position, setSize)
      .build(),

  /**
   * 菜单模式
   */
  menu: (label: string) =>
    createAriaProps()
      .role(ARIA_ROLES.MENU)
      .label(label)
      .build(),

  /**
   * 菜单项模式
   */
  menuItem: (label: string, disabled = false) =>
    createAriaProps()
      .role(ARIA_ROLES.MENUITEM)
      .label(label)
      .disabled(disabled)
      .build(),
} as const;