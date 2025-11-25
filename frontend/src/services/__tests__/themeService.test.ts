import { ThemeService } from '../themeService'
import { ThemeConfig, MarketMode, ColorblindMode } from '../../types/theme.types'

// 清除localStorage模拟
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn()
}
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
})

describe('ThemeService', () => {
  let themeService: ThemeService

  beforeEach(() => {
    jest.clearAllMocks()
    // 重置单例实例
    ;(ThemeService as any).instance = undefined
    themeService = ThemeService.getInstance()
  })

  describe('基础功能', () => {
    it('应该是单例模式', () => {
      const instance1 = ThemeService.getInstance()
      const instance2 = ThemeService.getInstance()
      expect(instance1).toBe(instance2)
    })

    it('应该有默认主题', () => {
      const currentTheme = themeService.getCurrentTheme()
      expect(currentTheme).toBeDefined()
      expect(currentTheme.id).toBeDefined()
      expect(currentTheme.name).toBeDefined()
      expect(currentTheme.colors).toBeDefined()
    })

    it('应该能够获取所有可用主题', () => {
      const themes = themeService.getAllThemes()
      expect(themes).toBeDefined()
      expect(themes.length).toBeGreaterThan(0)
      expect(themes.some(theme => theme.marketMode === 'chinese')).toBe(true)
      expect(themes.some(theme => theme.marketMode === 'international')).toBe(true)
    })
  })

  describe('市场模式切换 (AC1)', () => {
    it('应该能够设置中国市场模式', () => {
      themeService.setMarketMode('chinese')
      const currentTheme = themeService.getCurrentTheme()
      expect(currentTheme.marketMode).toBe('chinese')
      expect(currentTheme.colors.bullish).toBe('#ef4444') // 红色涨
      expect(currentTheme.colors.bearish).toBe('#22c55e') // 绿色跌
    })

    it('应该能够设置国际市场模式', () => {
      themeService.setMarketMode('international')
      const currentTheme = themeService.getCurrentTheme()
      expect(currentTheme.marketMode).toBe('international')
      expect(currentTheme.colors.bullish).toBe('#22c55e') // 绿色涨
      expect(currentTheme.colors.bearish).toBe('#ef4444') // 红色跌
    })

    it('应该在市场模式切换时发布事件', (done) => {
      themeService.subscribe((event) => {
        if (event.type === 'market-mode-changed') {
          expect(event.payload.marketMode).toBe('international')
          done()
        }
      })

      themeService.setMarketMode('international')
    })
  })

  describe('主题切换 (AC4)', () => {
    it('应该能够切换到浅色主题', () => {
      themeService.setCurrentTheme('light_chinese')
      const currentTheme = themeService.getCurrentTheme()
      expect(currentTheme.mode).toBe('light')
      expect(currentTheme.colors.background).toBe('#ffffff')
    })

    it('应该能够切换到深色主题', () => {
      themeService.setCurrentTheme('dark_chinese')
      const currentTheme = themeService.getCurrentTheme()
      expect(currentTheme.mode).toBe('dark')
      expect(currentTheme.colors.background).toBe('#1f2937')
    })

    it('应该在主题切换时发布事件', (done) => {
      themeService.subscribe((event) => {
        if (event.type === 'theme-changed') {
          expect(event.payload.currentTheme.id).toBe('dark_chinese')
          done()
        }
      })

      themeService.setCurrentTheme('dark_chinese')
    })
  })

  describe('色盲辅助功能 (AC2)', () => {
    it('应该能够启用色盲模式', () => {
      const colorblindConfig = {
        enabled: true,
        mode: 'protanopia' as ColorblindMode,
        usePatterns: true,
        useShapes: true,
        textureIntensity: 0.7
      }

      themeService.setColorblindMode(colorblindConfig)
      const currentTheme = themeService.getCurrentTheme()
      expect(currentTheme.colorblindMode).toBe('protanopia')
    })

    it('应该应用色盲友好的颜色', () => {
      const colorblindConfig = {
        enabled: true,
        mode: 'protanopia' as ColorblindMode,
        usePatterns: true,
        useShapes: true,
        textureIntensity: 0.7
      }

      themeService.setColorblindMode(colorblindConfig)
      const currentTheme = themeService.getCurrentTheme()
      // 红色盲模式下，应该使用蓝绿色系
      expect(currentTheme.colors.bullish).toBe('#10b981')
    })

    it('应该能够禁用色盲模式', () => {
      const enabledConfig = {
        enabled: true,
        mode: 'protanopia' as ColorblindMode,
        usePatterns: true,
        useShapes: true,
        textureIntensity: 0.7
      }

      const disabledConfig = {
        enabled: false,
        mode: 'none' as ColorblindMode,
        usePatterns: false,
        useShapes: false,
        textureIntensity: 0
      }

      themeService.setColorblindMode(enabledConfig)
      themeService.setColorblindMode(disabledConfig)

      const currentTheme = themeService.getCurrentTheme()
      expect(currentTheme.colorblindMode).toBe('none')
    })
  })

  describe('自定义颜色配置 (AC3)', () => {
    it('应该能够应用自定义颜色', () => {
      const customColors = {
        enabled: true,
        marketColors: {
          bullish: '#ff6b6b',
          bearish: '#4ecdc4',
          volume: '#45b7d1',
          grid: '#f0f0f0',
          background: '#fafafa',
          text: '#2c3e50',
          border: '#bdc3c7'
        }
      }

      themeService.applyCustomColors(customColors)
      const currentTheme = themeService.getCurrentTheme()
      expect(currentTheme.colors.bullish).toBe('#ff6b6b')
      expect(currentTheme.colors.bearish).toBe('#4ecdc4')
    })

    it('应该能够部分更新自定义颜色', () => {
      const customColors = {
        enabled: true,
        marketColors: {
          bullish: '#ff6b6b',
          bearish: '#4ecdc4'
        }
      }

      themeService.applyCustomColors(customColors)
      const currentTheme = themeService.getCurrentTheme()
      expect(currentTheme.colors.bullish).toBe('#ff6b6b')
      expect(currentTheme.colors.bearish).toBe('#4ecdc4')
      // 其他颜色应该保持不变
      expect(currentTheme.colors.volume).toBeDefined()
      expect(currentTheme.colors.background).toBeDefined()
    })
  })

  describe('自定义主题管理', () => {
    it('应该能够添加自定义主题', () => {
      const customTheme = {
        name: '测试主题',
        description: '用于测试的自定义主题',
        mode: 'light' as const,
        marketMode: 'chinese' as const,
        colorblindMode: 'none' as const,
        colors: {
          bullish: '#ff0000',
          bearish: '#00ff00',
          volume: '#0000ff',
          grid: '#cccccc',
          background: '#ffffff',
          text: '#000000',
          border: '#666666'
        }
      }

      const themeId = themeService.addCustomTheme(customTheme)
      expect(themeId).toBeDefined()
      expect(themeId).toMatch(/^custom_\d+$/)

      const retrievedTheme = themeService.getThemeById(themeId)
      expect(retrievedTheme).toBeDefined()
      expect(retrievedTheme?.name).toBe('测试主题')
    })

    it('应该能够删除自定义主题', () => {
      const customTheme = {
        name: '临时主题',
        description: '用于删除测试',
        mode: 'light' as const,
        marketMode: 'chinese' as const,
        colorblindMode: 'none' as const,
        colors: {
          bullish: '#ff0000',
          bearish: '#00ff00',
          volume: '#0000ff',
          grid: '#cccccc',
          background: '#ffffff',
          text: '#000000',
          border: '#666666'
        }
      }

      const themeId = themeService.addCustomTheme(customTheme)
      const deleted = themeService.removeCustomTheme(themeId)
      expect(deleted).toBe(true)

      const retrievedTheme = themeService.getThemeById(themeId)
      expect(retrievedTheme).toBeNull()
    })

    it('删除当前主题应该切换到默认主题', () => {
      const customTheme = {
        name: '当前主题',
        description: '用于删除测试',
        mode: 'light' as const,
        marketMode: 'chinese' as const,
        colorblindMode: 'none' as const,
        colors: {
          bullish: '#ff0000',
          bearish: '#00ff00',
          volume: '#0000ff',
          grid: '#cccccc',
          background: '#ffffff',
          text: '#000000',
          border: '#666666'
        }
      }

      const themeId = themeService.addCustomTheme(customTheme)
      themeService.setCurrentTheme(themeId)
      themeService.removeCustomTheme(themeId)

      const currentTheme = themeService.getCurrentTheme()
      expect(currentTheme.id).not.toBe(themeId)
    })
  })

  describe('主题验证 (AC)', () => {
    it('应该验证主题颜色格式', () => {
      const invalidTheme = {
        id: 'invalid',
        name: '无效主题',
        mode: 'light' as const,
        marketMode: 'chinese' as const,
        colorblindMode: 'none' as const,
        colors: {
          bullish: 'invalid-color',
          bearish: '#00ff00',
          volume: '#0000ff',
          grid: '#cccccc',
          background: '#ffffff',
          text: '#000000',
          border: '#666666'
        }
      }

      const result = themeService.validateTheme(invalidTheme)
      expect(result.isValid).toBe(false)
      expect(result.errors).toContain('无效的颜色格式: bullish = invalid-color')
    })

    it('应该验证WCAG对比度', () => {
      const lowContrastTheme = {
        id: 'low-contrast',
        name: '低对比度主题',
        mode: 'light' as const,
        marketMode: 'chinese' as const,
        colorblindMode: 'none' as const,
        colors: {
          bullish: '#fefefe', // 几乎是白色
          bearish: '#fdfdfd', // 几乎是白色
          volume: '#0000ff',
          grid: '#cccccc',
          background: '#ffffff',
          text: '#f0f0f0', // 浅色文字在白色背景上
          border: '#666666'
        }
      }

      const result = themeService.validateTheme(lowContrastTheme)
      expect(result.warnings.length).toBeGreaterThan(0)
      expect(result.warnings.some(warning =>
        warning.includes('对比度低于WCAG')
      )).toBe(true)
    })
  })

  describe('配置导入导出 (AC5)', () => {
    it('应该导出主题配置', () => {
      const exportData = themeService.exportThemes()
      expect(exportData).toBeDefined()
      expect(exportData.version).toBeDefined()
      expect(exportData.themes).toBeDefined()
      expect(exportData.presets).toBeDefined()
      expect(exportData.userPreferences).toBeDefined()
    })

    it('应该导入主题配置', () => {
      const exportData = themeService.exportThemes()

      // 修改一些数据
      exportData.userPreferences.marketMode = 'international'

      themeService.importThemes(exportData)
      const currentTheme = themeService.getCurrentTheme()
      expect(currentTheme.marketMode).toBe('international')
    })

    it('应该验证导入数据格式', () => {
      const invalidData = { invalid: 'data' }

      expect(() => {
        themeService.importThemes(invalidData as any)
      }).toThrow()
    })
  })

  describe('事件系统', () => {
    it('应该能够订阅主题事件', (done) => {
      const unsubscribe = themeService.subscribe((event) => {
        expect(event.type).toBe('theme-changed')
        expect(event.timestamp).toBeDefined()
        done()
      })

      themeService.setCurrentTheme('dark_chinese')
      unsubscribe()
    })

    it('应该能够取消订阅', () => {
      const listener = jest.fn()
      const unsubscribe = themeService.subscribe(listener)

      unsubscribe()
      themeService.setCurrentTheme('dark_chinese')

      expect(listener).not.toHaveBeenCalled()
    })

    it('应该处理监听器错误', () => {
      const errorListener = jest.fn(() => {
        throw new Error('Listener error')
      })

      // 不应该因为监听器错误而崩溃
      expect(() => {
        themeService.subscribe(errorListener)
        themeService.setCurrentTheme('dark_chinese')
      }).not.toThrow()
    })
  })

  describe('持久化存储', () => {
    it('应该保存配置到localStorage', () => {
      themeService.setMarketMode('international')

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'themeService',
        expect.any(String)
      )
    })

    it('应该从localStorage加载配置', () => {
      const mockData = JSON.stringify({
        currentTheme: {
          id: 'dark_chinese',
          marketMode: 'chinese',
          colorblindMode: 'none'
        }
      })

      localStorageMock.getItem.mockReturnValue(mockData)

      const newService = ThemeService.getInstance()
      const currentTheme = newService.getCurrentTheme()
      expect(currentTheme.id).toBe('dark_chinese')
    })

    it('应该处理localStorage错误', () => {
      localStorageMock.setItem.mockImplementation(() => {
        throw new Error('Storage error')
      })

      expect(() => {
        themeService.setMarketMode('international')
      }).not.toThrow()
    })
  })
})