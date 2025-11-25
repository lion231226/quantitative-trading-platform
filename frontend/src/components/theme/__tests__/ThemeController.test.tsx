import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ThemeProvider, useTheme } from '../ThemeProvider'
import { ThemeController } from '../ThemeController'
import { MarketMode, ThemeMode, ColorblindMode } from '../../../types/theme.types'

// 测试组件，用于Hook测试
const TestComponent: React.FC = () => {
  const {
    currentTheme,
    marketMode,
    setMarketMode,
    themeMode,
    setThemeMode,
    colorblindConfig,
    setColorblindMode
  } = useTheme()

  return (
    <div>
      <div data-testid="current-theme">{currentTheme.name}</div>
      <div data-testid="market-mode">{marketMode}</div>
      <div data-testid="theme-mode">{themeMode}</div>
      <div data-testid="colorblind-enabled">{colorblindConfig.enabled.toString()}</div>
      <button onClick={() => setMarketMode('international')} data-testid="switch-market">
        Switch Market
      </button>
      <button onClick={() => setThemeMode('dark')} data-testid="switch-theme">
        Switch Theme
      </button>
      <button onClick={() => setColorblindMode({
        enabled: true,
        mode: 'protanopia',
        usePatterns: true,
        useShapes: true,
        textureIntensity: 0.7
      })} data-testid="enable-colorblind">
        Enable Colorblind
      </button>
    </div>
  )
}

describe('Theme System', () => {
  beforeEach(() => {
    // 清除localStorage
    localStorage.clear()
  })

  describe('ThemeProvider', () => {
    it('应该提供默认主题状态', () => {
      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      )

      expect(screen.getByTestId('current-theme')).toHaveTextContent('浅色主题（中国市场）')
      expect(screen.getByTestId('market-mode')).toHaveTextContent('chinese')
      expect(screen.getByTestId('theme-mode')).toHaveTextContent('light')
      expect(screen.getByTestId('colorblind-enabled')).toHaveTextContent('false')
    })

    it('应该能够切换市场模式', async () => {
      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      )

      fireEvent.click(screen.getByTestId('switch-market'))

      await waitFor(() => {
        expect(screen.getByTestId('market-mode')).toHaveTextContent('international')
      })
    })

    it('应该能够切换主题模式', async () => {
      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      )

      fireEvent.click(screen.getByTestId('switch-theme'))

      await waitFor(() => {
        expect(screen.getByTestId('theme-mode')).toHaveTextContent('dark')
      })
    })

    it('应该能够启用色盲模式', async () => {
      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      )

      fireEvent.click(screen.getByTestId('enable-colorblind'))

      await waitFor(() => {
        expect(screen.getByTestId('colorblind-enabled')).toHaveTextContent('true')
      })
    })

    it('应该持久化主题配置到localStorage', async () => {
      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      )

      // 切换市场模式
      fireEvent.click(screen.getByTestId('switch-market'))

      await waitFor(() => {
        expect(screen.getByTestId('market-mode')).toHaveTextContent('international')
      })

      // 检查localStorage
      const storedTheme = localStorage.getItem('themeService')
      expect(storedTheme).toBeTruthy()

      const themeData = JSON.parse(storedTheme!)
      expect(themeData.currentTheme.marketMode).toBe('international')
    })
  })

  describe('ThemeController', () => {
    it('应该渲染主题控制器', () => {
      render(
        <ThemeProvider>
          <ThemeController />
        </ThemeProvider>
      )

      expect(screen.getByText('主题设置')).toBeInTheDocument()
      expect(screen.getByText('市场模式')).toBeInTheDocument()
      expect(screen.getByText('主题模式')).toBeInTheDocument()
    })

    it('应该显示高级选项', () => {
      render(
        <ThemeProvider>
          <ThemeController />
        </ThemeProvider>
      )

      // 点击高级选项
      fireEvent.click(screen.getByText('高级'))

      expect(screen.getByText('色盲辅助')).toBeInTheDocument()
      expect(screen.getByText('当前颜色配置')).toBeInTheDocument()
    })

    it('应该紧凑模式渲染', () => {
      render(
        <ThemeProvider>
          <ThemeController variant="compact" />
        </ThemeProvider>
      )

      // 紧凑模式不应有高级选项按钮
      expect(screen.queryByText('高级')).not.toBeInTheDocument()
    })
  })

  describe('市场模式切换 (AC1)', () => {
    it('应该支持中国市场模式', () => {
      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      )

      const currentTheme = useTheme()
      expect(currentTheme.currentTheme.marketMode).toBe('chinese')
      expect(currentTheme.currentTheme.colors.bullish).toBe('#ef4444') // 红色涨
      expect(currentTheme.currentTheme.colors.bearish).toBe('#22c55e') // 绿色跌
    })

    it('应该支持国际市场模式', async () => {
      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      )

      fireEvent.click(screen.getByTestId('switch-market'))

      await waitFor(() => {
        const currentTheme = useTheme()
        expect(currentTheme.currentTheme.marketMode).toBe('international')
        expect(currentTheme.currentTheme.colors.bullish).toBe('#22c55e') // 绿色涨
        expect(currentTheme.currentTheme.colors.bearish).toBe('#ef4444') // 红色跌
      })
    })
  })

  describe('色盲辅助功能 (AC2)', () => {
    it('应该支持多种色盲模式', async () => {
      const colorblindModes: ColorblindMode[] = [
        'protanopia', 'deuteranopia', 'tritanopia', 'achromatopsia'
      ]

      render(
        <ThemeProvider>
          <ThemeController variant="default" showColorblindMode={true} />
        </ThemeProvider>
      )

      // 点击高级选项以显示色盲辅助
      fireEvent.click(screen.getByText('高级'))

      colorblindModes.forEach((mode) => {
        expect(screen.getByText(
          mode === 'protanopia' ? '红色盲' :
          mode === 'deuteranopia' ? '绿色盲' :
          mode === 'tritanopia' ? '蓝色盲' :
          '全色盲'
        )).toBeInTheDocument()
      })
    })
  })

  describe('自定义颜色配置 (AC3)', () => {
    it('应该提供颜色选择器', () => {
      render(
        <ThemeProvider>
          <ThemeController variant="default" showCustomColors={true} />
        </ThemeProvider>
      )

      // 点击高级选项
      fireEvent.click(screen.getByText('高级'))

      expect(screen.getByText('当前颜色配置')).toBeInTheDocument()
    })
  })

  describe('主题切换系统 (AC4)', () => {
    it('应该支持浅色/深色主题切换', async () => {
      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      )

      // 初始应为浅色主题
      expect(screen.getByTestId('theme-mode')).toHaveTextContent('light')

      // 切换到深色主题
      fireEvent.click(screen.getByTestId('switch-theme'))

      await waitFor(() => {
        expect(screen.getByTestId('theme-mode')).toHaveTextContent('dark')
      })
    })
  })

  describe('配置导入导出 (AC5)', () => {
    it('应该提供导出配置功能', () => {
      const mockCreateObjectURL = jest.fn()
      const mockRevokeObjectURL = jest.fn()
      global.URL.createObjectURL = mockCreateObjectURL
      global.URL.revokeObjectURL = mockRevokeObjectURL

      // 模拟document.createElement和click
      const mockLink = {
        href: '',
        download: '',
        click: jest.fn(),
        style: { display: '' }
      }
      jest.spyOn(document, 'createElement').mockReturnValue(mockLink as any)
      jest.spyOn(document.body, 'appendChild').mockImplementation()
      jest.spyOn(document.body, 'removeChild').mockImplementation()

      render(
        <ThemeProvider>
          <ThemeController variant="default" showImportExport={true} />
        </ThemeProvider>
      )

      // 点击高级选项
      fireEvent.click(screen.getByText('高级'))

      // 点击导出按钮
      fireEvent.click(screen.getByText('导出配置'))

      expect(mockCreateObjectURL).toHaveBeenCalled()
      expect(mockLink.click).toHaveBeenCalled()
    })
  })
})