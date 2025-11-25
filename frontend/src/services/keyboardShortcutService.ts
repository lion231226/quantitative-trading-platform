import {
  KeyboardShortcutConfig,
  KlineChartEvent
} from '../types/kline.types'

/**
 * 快捷键动作类型
 */
export type ShortcutAction =
  | 'zoomIn'
  | 'zoomOut'
  | 'resetZoom'
  | 'panLeft'
  | 'panRight'
  | 'toggleCrosshair'
  | 'toggleGrid'
  | 'nextPeriod'
  | 'prevPeriod'
  | 'exportChart'
  | 'fullscreen'
  | 'togglePerformance'
  | 'custom'

/**
 * 快捷键定义
 */
export interface ShortcutDefinition {
  id: string
  action: ShortcutAction
  keys: string[]
  description: string
  enabled: boolean
  preventDefault?: boolean
  handler?: (event: KeyboardEvent) => void
}

/**
 * 键盘快捷键服务
 */
export class KeyboardShortcutService {
  private shortcuts: Map<string, ShortcutDefinition> = new Map()
  private config: KeyboardShortcutConfig
  private listeners: Map<ShortcutAction, ((event: KeyboardEvent) => void)[]> = new Map()
  private isEnabled: boolean = true

  constructor(config?: Partial<KeyboardShortcutConfig>) {
    this.config = {
      enabled: true,
      shortcuts: {
        panLeft: ['ArrowLeft'],
        panRight: ['ArrowRight'],
        zoomIn: ['+', '=', '='],
        zoomOut: ['-', '_'],
        resetZoom: ['r', 'R'],
        toggleCrosshair: ['c', 'C'],
        toggleGrid: ['g', 'G'],
        nextPeriod: ['k', 'K'],
        prevPeriod: ['Shift+K'],
        export: ['e', 'E'],
        fullscreen: ['f', 'F']
      },
      ...config
    }

    this.initializeDefaultShortcuts()
    this.setupKeyboardListener()
  }

  /**
   * 初始化默认快捷键
   */
  private initializeDefaultShortcuts(): void {
    const defaultShortcuts: ShortcutDefinition[] = [
      {
        id: 'zoomIn',
        action: 'zoomIn',
        keys: this.config.shortcuts.zoomIn,
        description: '放大图表',
        enabled: true,
        preventDefault: true
      },
      {
        id: 'zoomOut',
        action: 'zoomOut',
        keys: this.config.shortcuts.zoomOut,
        description: '缩小图表',
        enabled: true,
        preventDefault: true
      },
      {
        id: 'resetZoom',
        action: 'resetZoom',
        keys: this.config.shortcuts.resetZoom,
        description: '重置缩放',
        enabled: true,
        preventDefault: true
      },
      {
        id: 'panLeft',
        action: 'panLeft',
        keys: this.config.shortcuts.panLeft,
        description: '向左平移',
        enabled: true,
        preventDefault: true
      },
      {
        id: 'panRight',
        action: 'panRight',
        keys: this.config.shortcuts.panRight,
        description: '向右平移',
        enabled: true,
        preventDefault: true
      },
      {
        id: 'toggleCrosshair',
        action: 'toggleCrosshair',
        keys: this.config.shortcuts.toggleCrosshair,
        description: '切换十字线',
        enabled: true,
        preventDefault: false
      },
      {
        id: 'toggleGrid',
        action: 'toggleGrid',
        keys: this.config.shortcuts.toggleGrid,
        description: '切换网格',
        enabled: true,
        preventDefault: false
      },
      {
        id: 'nextPeriod',
        action: 'nextPeriod',
        keys: this.config.shortcuts.nextPeriod,
        description: '下一个时间周期',
        enabled: true,
        preventDefault: true
      },
      {
        id: 'prevPeriod',
        action: 'prevPeriod',
        keys: this.config.shortcuts.prevPeriod,
        description: '上一个时间周期',
        enabled: true,
        preventDefault: true
      },
      {
        id: 'exportChart',
        action: 'exportChart',
        keys: this.config.shortcuts.export,
        description: '导出图表',
        enabled: true,
        preventDefault: true
      },
      {
        id: 'fullscreen',
        action: 'fullscreen',
        keys: this.config.shortcuts.fullscreen,
        description: '全屏显示',
        enabled: true,
        preventDefault: true
      },
      {
        id: 'togglePerformance',
        action: 'togglePerformance',
        keys: ['p', 'P'],
        description: '显示/隐藏性能监控',
        enabled: true,
        preventDefault: false
      }
    ]

    defaultShortcuts.forEach(shortcut => {
      this.shortcuts.set(shortcut.id, shortcut)
    })
  }

  /**
   * 设置键盘监听器
   */
  private setupKeyboardListener(): void {
    document.addEventListener('keydown', this.handleKeyDown.bind(this))
  }

  /**
   * 处理键盘事件
   */
  private handleKeyDown(event: KeyboardEvent): void {
    if (!this.isEnabled || this.isInputElement(event.target)) {
      return
    }

    const pressedKey = this.formatKeyEvent(event)
    const shortcut = this.findShortcut(pressedKey)

    if (shortcut && shortcut.enabled) {
      if (shortcut.preventDefault) {
        event.preventDefault()
        event.stopPropagation()
      }

      // 执行自定义处理器或通知监听器
      if (shortcut.handler) {
        shortcut.handler(event)
      } else {
        this.notifyListeners(shortcut.action, event)
      }
    }
  }

  /**
   * 格式化键盘事件为字符串
   */
  private formatKeyEvent(event: KeyboardEvent): string {
    const parts: string[] = []

    if (event.ctrlKey) parts.push('Ctrl')
    if (event.altKey) parts.push('Alt')
    if (event.shiftKey) parts.push('Shift')
    if (event.metaKey) parts.push('Meta')

    parts.push(event.key)

    return parts.join('+')
  }

  /**
   * 查找匹配的快捷键
   */
  private findShortcut(keyEvent: string): ShortcutDefinition | null {
    for (const shortcut of this.shortcuts.values()) {
      if (shortcut.keys.some(key => this.isKeyMatch(key, keyEvent))) {
        return shortcut
      }
    }
    return null
  }

  /**
   * 检查按键是否匹配
   */
  private isKeyMatch(shortcutKey: string, eventKey: string): boolean {
    // 处理大小写不敏感
    if (!shortcutKey.includes('Shift')) {
      return shortcutKey.toLowerCase() === eventKey.toLowerCase()
    }
    return shortcutKey === eventKey
  }

  /**
   * 检查是否为输入元素
   */
  private isInputElement(target: EventTarget): boolean {
    const element = target as HTMLElement
    if (!element) return false

    const tagName = element.tagName.toLowerCase()
    const inputTypes = ['input', 'textarea', 'select']

    return inputTypes.includes(tagName) || element.isContentEditable
  }

  /**
   * 添加快捷键
   */
  addShortcut(shortcut: Omit<ShortcutDefinition, 'id'>): string {
    const id = `custom_${Date.now()}_${Math.random()}`
    const fullShortcut: ShortcutDefinition = {
      id,
      ...shortcut
    }

    this.shortcuts.set(id, fullShortcut)
    return id
  }

  /**
   * 移除快捷键
   */
  removeShortcut(id: string): boolean {
    return this.shortcuts.delete(id)
  }

  /**
   * 更新快捷键
   */
  updateShortcut(id: string, updates: Partial<ShortcutDefinition>): boolean {
    const shortcut = this.shortcuts.get(id)
    if (!shortcut) return false

    const updatedShortcut = { ...shortcut, ...updates }
    this.shortcuts.set(id, updatedShortcut)
    return true
  }

  /**
   * 启用/禁用快捷键
   */
  setShortcutEnabled(id: string, enabled: boolean): boolean {
    const shortcut = this.shortcuts.get(id)
    if (!shortcut) return false

    shortcut.enabled = enabled
    return true
  }

  /**
   * 启用/禁用所有快捷键
   */
  setEnabled(enabled: boolean): void {
    this.isEnabled = enabled
    this.config.enabled = enabled
  }

  /**
   * 获取快捷键列表
   */
  getShortcuts(): ShortcutDefinition[] {
    return Array.from(this.shortcuts.values())
  }

  /**
   * 获取启用的快捷键列表
   */
  getEnabledShortcuts(): ShortcutDefinition[] {
    return this.getShortcuts().filter(shortcut => shortcut.enabled)
  }

  /**
   * 获取快捷键帮助信息
   */
  getShortcutHelp(): Array<{
    id: string
    action: ShortcutAction
    keys: string[]
    description: string
    enabled: boolean
  }> {
    return this.getShortcuts().map(({ id, action, keys, description, enabled }) => ({
      id,
      action,
      keys,
      description,
      enabled
    }))
  }

  /**
   * 添加动作监听器
   */
  addListener(action: ShortcutAction, callback: (event: KeyboardEvent) => void): void {
    if (!this.listeners.has(action)) {
      this.listeners.set(action, [])
    }
    this.listeners.get(action)!.push(callback)
  }

  /**
   * 移除动作监听器
   */
  removeListener(action: ShortcutAction, callback: (event: KeyboardEvent) => void): boolean {
    const callbacks = this.listeners.get(action)
    if (!callbacks) return false

    const index = callbacks.indexOf(callback)
    if (index !== -1) {
      callbacks.splice(index, 1)
      return true
    }
    return false
  }

  /**
   * 通知监听器
   */
  private notifyListeners(action: ShortcutAction, event: KeyboardEvent): void {
    const callbacks = this.listeners.get(action)
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(event)
        } catch (error) {
          console.error(`快捷键监听器错误 (${action}):`, error)
        }
      })
    }
  }

  /**
   * 执行快捷键动作
   */
  executeAction(action: ShortcutAction, event?: KeyboardEvent): boolean {
    // 触发键盘事件
    if (event) {
      this.handleKeyDown(event)
      return true
    }

    // 直接通知监听器
    const mockEvent = new KeyboardEvent('keydown', {
      key: '',
      ctrlKey: false,
      altKey: false,
      shiftKey: false,
      metaKey: false
    })

    this.notifyListeners(action, mockEvent)
    return true
  }

  /**
   * 检查快捷键是否可用
   */
  isShortcutAvailable(keys: string[]): boolean {
    const formattedKey = this.formatKeyEvent({
      key: keys[0],
      ctrlKey: false,
      altKey: false,
      shiftKey: false,
      metaKey: false,
      preventDefault: () => {}
    } as KeyboardEvent)

    return !this.findShortcut(formattedKey)
  }

  /**
   * 重置为默认快捷键
   */
  resetToDefaults(): void {
    this.shortcuts.clear()
    this.initializeDefaultShortcuts()
  }

  /**
   * 导出快捷键配置
   */
  exportConfig(): KeyboardShortcutConfig {
    const shortcuts: Record<string, string[]> = {}

    for (const shortcut of this.shortcuts.values()) {
      if (shortcut.id.startsWith('custom_')) {
        continue // 跳过自定义快捷键
      }
      shortcuts[shortcut.action] = shortcut.keys
    }

    return {
      enabled: this.config.enabled,
      shortcuts
    }
  }

  /**
   * 导入快捷键配置
   */
  importConfig(config: KeyboardShortcutConfig): void {
    this.config.enabled = config.enabled

    // 更新现有快捷键
    for (const [action, keys] of Object.entries(config.shortcuts)) {
      for (const shortcut of this.shortcuts.values()) {
        if (shortcut.action === action) {
          shortcut.keys = keys
          break
        }
      }
    }
  }

  /**
   * 获取快捷键冲突检测
   */
  detectConflicts(): Array<{
    keys: string[]
    shortcuts: ShortcutDefinition[]
  }> {
    const conflicts: Array<{ keys: string[]; shortcuts: ShortcutDefinition[] }> = []
    const keyMap = new Map<string, ShortcutDefinition[]>()

    // 构建按键到快捷键的映射
    for (const shortcut of this.shortcuts.values()) {
      if (shortcut.enabled) {
        for (const key of shortcut.keys) {
          if (!keyMap.has(key)) {
            keyMap.set(key, [])
          }
          keyMap.get(key)!.push(shortcut)
        }
      }
    }

    // 查找冲突
    for (const [key, shortcuts] of keyMap.entries()) {
      if (shortcuts.length > 1) {
        conflicts.push({
          keys: [key],
          shortcuts
        })
      }
    }

    return conflicts
  }

  /**
   * 清理资源
   */
  dispose(): void {
    document.removeEventListener('keydown', this.handleKeyDown.bind(this))
    this.shortcuts.clear()
    this.listeners.clear()
    this.isEnabled = false
  }
}

// 导出单例实例
export const keyboardShortcutService = new KeyboardShortcutService()