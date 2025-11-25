'use client'

import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react'
import { themeService } from '../../services/themeService'
import {
  ThemeConfig,
  ThemeUpdateEvent,
  MarketMode,
  ThemeMode,
  ColorblindMode,
  ColorblindConfig,
  CustomColorConfig,
  ThemeState,
  DEFAULT_MARKET_COLORS
} from '../../types/theme.types'

// 主题上下文接口
export interface ThemeContextType {
  // 当前状态
  currentTheme: ThemeConfig
  marketMode: MarketMode
  themeMode: ThemeMode
  colorblindConfig: ColorblindConfig
  customColors: CustomColorConfig
  availableThemes: ThemeConfig[]

  // 主题操作
  setTheme: (themeId: string) => void
  setMarketMode: (mode: MarketMode) => void
  setThemeMode: (mode: ThemeMode) => void
  setColorblindMode: (config: ColorblindConfig) => void
  applyCustomColors: (colors: CustomColorConfig) => void

  // 主题管理
  addCustomTheme: (theme: Omit<ThemeConfig, 'id'>) => string
  removeCustomTheme: (themeId: string) => boolean
  resetToDefaults: () => void

  // 导入导出
  exportThemes: () => void
  importThemes: (file: File) => Promise<void>
}

// 创建主题上下文
const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

// 主题提供者属性
interface ThemeProviderProps {
  children: ReactNode
  defaultTheme?: string
  defaultMarketMode?: MarketMode
}

// 主题提供者组件
export const ThemeProvider: React.FC<ThemeProviderProps> = ({
  children,
  defaultTheme,
  defaultMarketMode = 'chinese'
}) => {
  const [currentTheme, setCurrentTheme] = useState<ThemeConfig>(() =>
    themeService.getCurrentTheme()
  )
  const [availableThemes, setAvailableThemes] = useState<ThemeConfig[]>(() =>
    themeService.getAllThemes()
  )
  const [colorblindConfig, setColorblindConfigState] = useState<ColorblindConfig>({
    enabled: false,
    mode: 'none',
    usePatterns: true,
    useShapes: true,
    textureIntensity: 0.7
  })
  const [customColors, setCustomColorsState] = useState<CustomColorConfig>({
    enabled: false,
    marketColors: {}
  })

  // 处理主题更新事件
  const handleThemeUpdate = useCallback((event: ThemeUpdateEvent) => {
    switch (event.type) {
      case 'theme-changed':
      case 'market-mode-changed':
      case 'colorblind-mode-changed':
        setCurrentTheme(themeService.getCurrentTheme())
        break
      case 'custom-colors-changed':
        setCurrentTheme(themeService.getCurrentTheme())
        break
    }
  }, [])

  // 初始化时订阅主题事件
  useEffect(() => {
    const unsubscribe = themeService.subscribe(handleThemeUpdate)

    // 如果指定了默认主题，则应用
    if (defaultTheme) {
      try {
        themeService.setCurrentTheme(defaultTheme)
        setCurrentTheme(themeService.getCurrentTheme())
      } catch (error) {
        console.warn('无法设置默认主题:', error)
      }
    }

    // 如果指定了默认市场模式，则应用
    if (defaultMarketMode !== 'chinese') {
      themeService.setMarketMode(defaultMarketMode)
      setCurrentTheme(themeService.getCurrentTheme())
    }

    // 更新可用主题列表
    setAvailableThemes(themeService.getAllThemes())

    return unsubscribe
  }, [defaultTheme, defaultMarketMode, handleThemeUpdate])

  // 设置主题
  const setTheme = useCallback((themeId: string) => {
    try {
      themeService.setCurrentTheme(themeId)
      setCurrentTheme(themeService.getCurrentTheme())
    } catch (error) {
      console.error('设置主题失败:', error)
      throw error
    }
  }, [])

  // 设置市场模式
  const setMarketMode = useCallback((mode: MarketMode) => {
    try {
      themeService.setMarketMode(mode)
      setCurrentTheme(themeService.getCurrentTheme())
    } catch (error) {
      console.error('设置市场模式失败:', error)
      throw error
    }
  }, [])

  // 设置主题模式（浅色/深色）
  const setThemeMode = useCallback((mode: ThemeMode) => {
    try {
      // 找到对应模式和当前市场模式的主题
      const targetTheme = availableThemes.find(theme =>
        theme.mode === mode && theme.marketMode === currentTheme.marketMode
      )

      if (targetTheme) {
        themeService.setCurrentTheme(targetTheme.id)
        setCurrentTheme(themeService.getCurrentTheme())
      } else {
        // 如果没有找到，创建一个新的主题
        const newTheme: Omit<ThemeConfig, 'id'> = {
          name: mode === 'light' ? '浅色主题' : '深色主题',
          description: `自定义${mode === 'light' ? '浅色' : '深色'}主题`,
          mode,
          marketMode: currentTheme.marketMode,
          colorblindMode: currentTheme.colorblindMode,
          colors: {
            ...DEFAULT_MARKET_COLORS[currentTheme.marketMode],
            background: mode === 'light' ? '#ffffff' : '#1f2937',
            text: mode === 'light' ? '#1f2937' : '#f9fafb',
            grid: mode === 'light' ? '#e5e7eb' : '#374151',
            border: mode === 'light' ? '#d1d5db' : '#4b5563'
          }
        }

        themeService.setCurrentTheme(newTheme.id)
        setCurrentTheme(themeService.getCurrentTheme())
        setAvailableThemes(themeService.getAllThemes())
      }
    } catch (error) {
      console.error('设置主题模式失败:', error)
      throw error
    }
  }, [availableThemes, currentTheme.marketMode, currentTheme.colorblindMode])

  // 设置色盲模式
  const setColorblindMode = useCallback((config: ColorblindConfig) => {
    try {
      setColorblindConfigState(config)
      themeService.setColorblindMode(config)
      setCurrentTheme(themeService.getCurrentTheme())
    } catch (error) {
      console.error('设置色盲模式失败:', error)
      throw error
    }
  }, [])

  // 应用自定义颜色
  const applyCustomColors = useCallback((colors: CustomColorConfig) => {
    try {
      setCustomColorsState(colors)
      themeService.applyCustomColors(colors)
      setCurrentTheme(themeService.getCurrentTheme())
    } catch (error) {
      console.error('应用自定义颜色失败:', error)
      throw error
    }
  }, [])

  // 添加自定义主题
  const addCustomTheme = useCallback((theme: Omit<ThemeConfig, 'id'>) => {
    const themeId = themeService.addCustomTheme(theme)
    setAvailableThemes(themeService.getAllThemes())
    return themeId
  }, [])

  // 删除自定义主题
  const removeCustomTheme = useCallback((themeId: string) => {
    const success = themeService.removeCustomTheme(themeId)
    if (success) {
      setCurrentTheme(themeService.getCurrentTheme())
      setAvailableThemes(themeService.getAllThemes())
    }
    return success
  }, [])

  // 重置为默认设置
  const resetToDefaults = useCallback(() => {
    try {
      themeService.setCurrentTheme('light_chinese')
      setColorblindConfigState({
        enabled: false,
        mode: 'none',
        usePatterns: true,
        useShapes: true,
        textureIntensity: 0.7
      })
      setCustomColorsState({
        enabled: false,
        marketColors: {}
      })
      setCurrentTheme(themeService.getCurrentTheme())
    } catch (error) {
      console.error('重置主题失败:', error)
      throw error
    }
  }, [])

  // 导出主题配置
  const exportThemes = useCallback(() => {
    try {
      const exportData = themeService.exportThemes()
      const blob = new Blob([JSON.stringify(exportData, null, 2)], {
        type: 'application/json'
      })

      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `theme-config-${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('导出主题失败:', error)
      throw error
    }
  }, [])

  // 导入主题配置
  const importThemes = useCallback(async (file: File) => {
    try {
      const text = await file.text()
      const importData = JSON.parse(text)
      themeService.importThemes(importData)
      setCurrentTheme(themeService.getCurrentTheme())
      setAvailableThemes(themeService.getAllThemes())
    } catch (error) {
      console.error('导入主题失败:', error)
      throw error
    }
  }, [])

  // 构建上下文值
  const contextValue: ThemeContextType = {
    currentTheme,
    marketMode: currentTheme.marketMode,
    themeMode: currentTheme.mode,
    colorblindConfig,
    customColors,
    availableThemes,
    setTheme,
    setMarketMode,
    setThemeMode,
    setColorblindMode,
    applyCustomColors,
    addCustomTheme,
    removeCustomTheme,
    resetToDefaults,
    exportThemes,
    importThemes
  }

  return (
    <ThemeContext.Provider value={contextValue}>
      {children}
    </ThemeContext.Provider>
  )
}

// 使用主题的Hook
export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}

// 导出上下文
export default ThemeContext