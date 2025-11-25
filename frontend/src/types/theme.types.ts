// 主题配置相关类型定义

export type MarketMode = 'chinese' | 'international'
export type ThemeMode = 'light' | 'dark' | 'custom'
export type ColorblindMode = 'none' | 'protanopia' | 'deuteranopia' | 'tritanopia' | 'achromatopsia'

// 市场颜色配置
export interface MarketColors {
  bullish: string    // 涨颜色
  bearish: string    // 跌颜色
  volume: string    // 成交量颜色
  grid: string      // 网格颜色
  background: string // 背景颜色
  text: string      // 文字颜色
  border: string    // 边框颜色
}

// 主题配置接口
export interface ThemeConfig {
  id: string
  name: string
  description?: string
  mode: ThemeMode
  marketMode: MarketMode
  colors: MarketColors
  colorblindMode: ColorblindMode
  customCSS?: string
}

// 色盲友好配置
export interface ColorblindConfig {
  enabled: boolean
  mode: ColorblindMode
  usePatterns: boolean    // 使用图案区分
  useShapes: boolean      // 使用形状区分
  textureIntensity: number // 纹理强度 (0-1)
}

// 用户自定义颜色配置
export interface CustomColorConfig {
  enabled: boolean
  marketColors: Partial<MarketColors>
  signalColors?: Record<string, string>
  gradientColors?: string[]
}

// 主题预设接口
export interface ThemePreset {
  id: string
  name: string
  description: string
  category: 'default' | 'professional' | 'accessibility' | 'custom'
  theme: ThemeConfig
  colorblindSupport?: boolean
  preview?: string
}

// 主题切换状态
export interface ThemeState {
  currentTheme: string
  marketMode: MarketMode
  themeMode: ThemeMode
  colorblindConfig: ColorblindConfig
  customColors: CustomColorConfig
  availableThemes: ThemeConfig[]
  customThemes: ThemeConfig[]
}

// 主题更新事件
export interface ThemeUpdateEvent {
  type: 'theme-changed' | 'market-mode-changed' | 'colorblind-mode-changed' | 'custom-colors-changed'
  payload: any
  timestamp: number
}

// 主题验证结果
export interface ThemeValidationResult {
  isValid: boolean
  errors: string[]
  warnings: string[]
  wcagCompliance?: {
    normalText: number    // 正常文本对比度
    largeText: number     // 大文本对比度
    graphicalObjects: number // 图形对象对比度
  }
}

// 导出/导入配置格式
export interface ThemeExportFormat {
  version: string
  timestamp: string
  themes: ThemeConfig[]
  presets: ThemePreset[]
  userPreferences: {
    currentTheme: string
    marketMode: MarketMode
    colorblindConfig: ColorblindConfig
    customColors: CustomColorConfig
  }
  metadata?: {
    author?: string
    description?: string
    tags?: string[]
  }
}

// 默认主题配置
export const DEFAULT_MARKET_COLORS = {
  chinese: {
    bullish: '#ef4444',    // 红色涨
    bearish: '#22c55e',    // 绿色跌
    volume: '#3b82f6',     // 蓝色成交量
    grid: '#e5e7eb',       // 浅灰网格
    background: '#ffffff', // 白色背景
    text: '#1f2937',       // 深色文字
    border: '#d1d5db'      // 灰色边框
  },
  international: {
    bullish: '#22c55e',    // 绿色涨
    bearish: '#ef4444',    // 红色跌
    volume: '#3b82f6',     // 蓝色成交量
    grid: '#e5e7eb',       // 浅灰网格
    background: '#ffffff', // 白色背景
    text: '#1f2937',       // 深色文字
    border: '#d1d5db'      // 灰色边框
  }
} as const

// 色盲模式配置
export const COLORBLIND_PRESETS = {
  protanopia: {
    // 红色盲：使用蓝绿色系
    bullish: '#10b981',
    bearish: '#3b82f6',
    volume: '#8b5cf6'
  },
  deuteranopia: {
    // 绿色盲：使用蓝紫色系
    bullish: '#3b82f6',
    bearish: '#8b5cf6',
    volume: '#ec4899'
  },
  tritanopia: {
    // 蓝色盲：使用红绿色系
    bullish: '#ef4444',
    bearish: '#22c55e',
    volume: '#f59e0b'
  },
  achromatopsia: {
    // 全色盲：使用高对比度灰度
    bullish: '#000000',
    bearish: '#ffffff',
    volume: '#666666'
  }
} as const