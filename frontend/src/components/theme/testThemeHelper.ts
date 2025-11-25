import { ThemeConfig } from '../../types/theme.types'

// 测试用的默认主题配置
export const testTheme: ThemeConfig = {
  id: 'test-light',
  name: '测试浅色主题',
  description: '用于测试的浅色主题',
  mode: 'light',
  marketMode: 'chinese',
  colorblindMode: {
    enabled: false,
    mode: 'none',
    usePatterns: true,
    useShapes: true,
    textureIntensity: 0.7
  },
  colors: {
    bullish: '#10B981',
    bearish: '#EF4444',
    background: '#FFFFFF',
    grid: '#E5E7EB',
    text: '#1F2937',
    border: '#D1D5DB',
    crosshair: '#6B7280',
    volume: '#9CA3AF'
  }
}

export const testThemeDark: ThemeConfig = {
  ...testTheme,
  id: 'test-dark',
  name: '测试深色主题',
  mode: 'dark',
  colors: {
    bullish: '#10B981',
    bearish: '#EF4444',
    background: '#1F2937',
    grid: '#374151',
    text: '#F9FAFB',
    border: '#4B5563',
    crosshair: '#6B7280',
    volume: '#9CA3AF'
  }
}