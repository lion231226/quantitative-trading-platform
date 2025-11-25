'use client'

import React, { useState, useRef, useCallback } from 'react'
import { Palette, Eye, EyeOff, RefreshCw } from 'lucide-react'
import { useTheme } from './ThemeProvider'
import { MarketColors } from '../../types/theme.types'

interface ColorPickerProps {
  className?: string
  showPreview?: boolean
  showPresets?: boolean
  onColorChange?: (color: MarketColors) => void
}

// 颜色预设
const COLOR_PRESETS = [
  {
    name: '经典红绿',
    colors: {
      bullish: '#ef4444',
      bearish: '#22c55e',
      volume: '#3b82f6',
      grid: '#e5e7eb',
      background: '#ffffff',
      text: '#1f2937',
      border: '#d1d5db'
    }
  },
  {
    name: '专业蓝橙',
    colors: {
      bullish: '#3b82f6',
      bearish: '#f97316',
      volume: '#8b5cf6',
      grid: '#e5e7eb',
      background: '#ffffff',
      text: '#1f2937',
      border: '#d1d5db'
    }
  },
  {
    name: '护眼绿黄',
    colors: {
      bullish: '#10b981',
      bearish: '#eab308',
      volume: '#06b6d4',
      grid: '#e5e7eb',
      background: '#ffffff',
      text: '#1f2937',
      border: '#d1d5db'
    }
  },
  {
    name: '高对比黑白',
    colors: {
      bullish: '#000000',
      bearish: '#ffffff',
      volume: '#666666',
      grid: '#999999',
      background: '#f9fafb',
      text: '#111827',
      border: '#6b7280'
    }
  }
]

/**
 * 颜色选择器组件
 */
export const ColorPicker: React.FC<ColorPickerProps> = ({
  className = '',
  showPreview = true,
  showPresets = true,
  onColorChange
}) => {
  const { currentTheme, applyCustomColors } = useTheme()
  const [customColors, setCustomColors] = useState<MarketColors>(currentTheme.colors)
  const [activeColorKey, setActiveColorKey] = useState<keyof MarketColors | null>(null)
  const colorInputRef = useRef<HTMLInputElement>(null)

  // 颜色配置项
  const colorConfig = [
    { key: 'bullish' as keyof MarketColors, label: '涨颜色', description: '上涨K线颜色' },
    { key: 'bearish' as keyof MarketColors, label: '跌颜色', description: '下跌K线颜色' },
    { key: 'volume' as keyof MarketColors, label: '成交量', description: '成交量柱状图颜色' },
    { key: 'grid' as keyof MarketColors, label: '网格线', description: '图表网格线颜色' },
    { key: 'background' as keyof MarketColors, label: '背景色', description: '图表背景颜色' },
    { key: 'text' as keyof MarketColors, label: '文字色', description: '图表文字颜色' },
    { key: 'border' as keyof MarketColors, label: '边框色', description: '图表边框颜色' }
  ]

  // 处理颜色变化
  const handleColorChange = useCallback((key: keyof MarketColors, color: string) => {
    const newColors = { ...customColors, [key]: color }
    setCustomColors(newColors)
    onColorChange?.(newColors)
  }, [customColors, onColorChange])

  // 应用自定义颜色
  const handleApplyColors = useCallback(() => {
    applyCustomColors({
      enabled: true,
      marketColors: customColors
    })
  }, [customColors, applyCustomColors])

  // 重置为默认颜色
  const handleResetColors = useCallback(() => {
    const defaultColors = currentTheme.colors
    setCustomColors(defaultColors)
    onColorChange?.(defaultColors)
  }, [currentTheme.colors, onColorChange])

  // 应用预设
  const handleApplyPreset = useCallback((preset: typeof COLOR_PRESETS[0]) => {
    setCustomColors(preset.colors)
    onColorChange?.(preset.colors)
  }, [onColorChange])

  // 验证颜色格式
  const isValidColor = (color: string): boolean => {
    const colorRegex = /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/
    return colorRegex.test(color)
  }

  // 计算对比度
  const calculateContrast = (color1: string, color2: string): number => {
    // 简化的对比度计算
    const getLuminance = (hex: string): number => {
      const rgb = hexToRgb(hex)
      return (0.299 * rgb.r + 0.587 * rgb.g + 0.114 * rgb.b) / 255
    }

    const lum1 = getLuminance(color1)
    const lum2 = getLuminance(color2)
    const brightest = Math.max(lum1, lum2)
    const darkest = Math.min(lum1, lum2)
    return (brightest + 0.05) / (darkest + 0.05)
  }

  // 十六进制转RGB
  const hexToRgb = (hex: string): { r: number; g: number; b: number } => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16)
    } : { r: 0, g: 0, b: 0 }
  }

  return (
    <div className={`color-picker ${className}`}>
      {/* 头部 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Palette className="w-5 h-5 text-gray-600" />
          <h3 className="text-lg font-semibold text-gray-900">自定义颜色</h3>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleResetColors}
            className="flex items-center space-x-1 px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
          >
            <RefreshCw className="w-4 h-4" />
            <span>重置</span>
          </button>
          <button
            onClick={handleApplyColors}
            className="flex items-center space-x-1 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            <Eye className="w-4 h-4" />
            <span>应用</span>
          </button>
        </div>
      </div>

      {/* 颜色预设 */}
      {showPresets && (
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            颜色预设
          </label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {COLOR_PRESETS.map((preset) => (
              <button
                key={preset.name}
                onClick={() => handleApplyPreset(preset)}
                className="p-3 border border-gray-200 rounded-lg hover:bg-gray-50 text-left"
              >
                <div className="flex items-center space-x-2 mb-2">
                  <div className="flex space-x-1">
                    <div
                      className="w-4 h-4 rounded border border-gray-300"
                      style={{ backgroundColor: preset.colors.bullish }}
                    />
                    <div
                      className="w-4 h-4 rounded border border-gray-300"
                      style={{ backgroundColor: preset.colors.bearish }}
                    />
                    <div
                      className="w-4 h-4 rounded border border-gray-300"
                      style={{ backgroundColor: preset.colors.volume }}
                    />
                  </div>
                </div>
                <div className="text-sm font-medium text-gray-900">{preset.name}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 颜色配置 */}
      <div className="space-y-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          颜色配置
        </label>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {colorConfig.map((config) => (
            <div key={config.key} className="flex items-center space-x-3">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {config.label}
                </label>
                <div className="text-xs text-gray-500">{config.description}</div>
              </div>
              <div className="flex items-center space-x-2">
                <div
                  className="w-10 h-10 rounded-lg border-2 border-gray-300 cursor-pointer relative"
                  style={{ backgroundColor: customColors[config.key] }}
                  onClick={() => setActiveColorKey(config.key)}
                >
                  {activeColorKey === config.key && (
                    <div className="absolute inset-0 border-2 border-blue-500 rounded-lg pointer-events-none" />
                  )}
                </div>
                <input
                  ref={config.key === activeColorKey ? colorInputRef : undefined}
                  type="color"
                  value={customColors[config.key]}
                  onChange={(e) => handleColorChange(config.key, e.target.value)}
                  className="w-16 h-10 border border-gray-300 rounded cursor-pointer"
                />
                <input
                  type="text"
                  value={customColors[config.key]}
                  onChange={(e) => {
                    const value = e.target.value
                    if (value.length === 0 || isValidColor(value)) {
                      handleColorChange(config.key, value || '#000000')
                    }
                  }}
                  placeholder="#000000"
                  className="w-24 px-2 py-2 text-sm border border-gray-300 rounded-md"
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 颜色预览 */}
      {showPreview && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            颜色预览
          </label>
          <div className="grid grid-cols-2 gap-4">
            {/* 涨预览 */}
            <div>
              <div className="text-sm font-medium text-gray-700 mb-1">上涨K线</div>
              <div
                className="h-12 rounded-lg border border-gray-300 flex items-center justify-center text-white font-bold"
                style={{ backgroundColor: customColors.bullish }}
              >
                涨
              </div>
              <div className="text-xs text-gray-500 mt-1">{customColors.bullish}</div>
            </div>

            {/* 跌预览 */}
            <div>
              <div className="text-sm font-medium text-gray-700 mb-1">下跌K线</div>
              <div
                className="h-12 rounded-lg border border-gray-300 flex items-center justify-center text-white font-bold"
                style={{ backgroundColor: customColors.bearish }}
              >
                跌
              </div>
              <div className="text-xs text-gray-500 mt-1">{customColors.bearish}</div>
            </div>
          </div>

          {/* 对比度信息 */}
          <div className="mt-4 p-3 bg-gray-50 rounded-lg">
            <div className="text-sm font-medium text-gray-700 mb-2">对比度检查</div>
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <span className="text-gray-600">文字对比度: </span>
                <span className={
                  calculateContrast(customColors.text, customColors.background) >= 4.5
                    ? 'text-green-600'
                    : 'text-red-600'
                }>
                  {calculateContrast(customColors.text, customColors.background).toFixed(2)}
                  {calculateContrast(customColors.text, customColors.background) >= 4.5 ? ' ✓' : ' ⚠️'}
                </span>
              </div>
              <div>
                <span className="text-gray-600">涨跌对比度: </span>
                <span className={
                  calculateContrast(customColors.bullish, customColors.bearish) >= 3.0
                    ? 'text-green-600'
                    : 'text-red-600'
                }>
                  {calculateContrast(customColors.bullish, customColors.bearish).toFixed(2)}
                  {calculateContrast(customColors.bullish, customColors.bearish) >= 3.0 ? ' ✓' : ' ⚠️'}
                </span>
              </div>
            </div>
            <div className="text-xs text-gray-500 mt-2">
              WCAG 2.1 AA标准: 正常文本 ≥ 4.5:1, 图形对象 ≥ 3:1
            </div>
          </div>
        </div>
      )}

      {/* 提示信息 */}
      <div className="mt-4 p-3 bg-blue-50 rounded-lg">
        <div className="flex items-start space-x-2">
          <Palette className="w-4 h-4 text-blue-600 mt-0.5" />
          <div className="text-xs text-blue-700">
            <div className="font-medium mb-1">自定义颜色提示：</div>
            <ul className="list-disc list-inside space-y-1 text-blue-600">
              <li>点击颜色块或使用颜色选择器来修改颜色</li>
              <li>支持十六进制颜色格式（如 #FF0000）</li>
              <li>建议确保涨跌颜色有足够的对比度</li>
              <li>文字与背景对比度应达到4.5:1以上以符合WCAG标准</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ColorPicker