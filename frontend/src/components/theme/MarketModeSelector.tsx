'use client'

import React, { useState } from 'react'
import { Globe, TrendingUp } from 'lucide-react'
import { useTheme } from './ThemeProvider'
import { MarketMode } from '../../types/theme.types'

interface MarketModeSelectorProps {
  className?: string
  showLabel?: boolean
  size?: 'sm' | 'md' | 'lg'
  variant?: 'default' | 'compact' | 'detailed'
}

export const MarketModeSelector: React.FC<MarketModeSelectorProps> = ({
  className = '',
  showLabel = true,
  size = 'md',
  variant = 'default'
}) => {
  const { marketMode, setMarketMode } = useTheme()
  const [isOpen, setIsOpen] = useState(false)

  // 市场模式选项
  const marketModes = [
    {
      value: 'chinese' as MarketMode,
      label: '中国市场',
      description: '红涨绿跌',
      icon: '🇨🇳',
      colors: {
        bullish: '#ef4444', // 红色
        bearish: '#22c55e'  // 绿色
      }
    },
    {
      value: 'international' as MarketMode,
      label: '国际市场',
      description: '绿涨红跌',
      icon: '🌍',
      colors: {
        bullish: '#22c55e', // 绿色
        bearish: '#ef4444'  // 红色
      }
    }
  ]

  // 当前选择的市场模式
  const currentMode = marketModes.find(mode => mode.value === marketMode)

  // 尺寸样式映射
  const sizeClasses = {
    sm: {
      container: 'px-3 py-1.5 text-sm',
      dropdown: 'text-xs',
      preview: 'w-4 h-4'
    },
    md: {
      container: 'px-4 py-2 text-sm',
      dropdown: 'text-sm',
      preview: 'w-5 h-5'
    },
    lg: {
      container: 'px-5 py-3 text-base',
      dropdown: 'text-base',
      preview: 'w-6 h-6'
    }
  }[size]

  // 变体样式
  const variantClasses = {
    default: 'bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50',
    compact: 'bg-transparent border border-gray-300 rounded hover:bg-gray-50',
    detailed: 'bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100'
  }[variant]

  const handleModeChange = (mode: MarketMode) => {
    setMarketMode(mode)
    setIsOpen(false)
  }

  if (variant === 'compact') {
    return (
      <div className={`relative ${className}`}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className={`flex items-center space-x-2 ${sizeClasses.container} ${variantClasses} transition-colors duration-200`}
        >
          <span className="text-lg">{currentMode?.icon}</span>
          {showLabel && (
            <span className="font-medium text-gray-700">
              {currentMode?.label}
            </span>
          )}
          <svg
            className={`w-4 h-4 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {isOpen && (
          <>
            <div
              className="fixed inset-0 z-10"
              onClick={() => setIsOpen(false)}
            />
            <div className="absolute top-full left-0 mt-1 w-56 bg-white border border-gray-300 rounded-lg shadow-lg z-20">
              <div className="p-2">
                {marketModes.map((mode) => (
                  <button
                    key={mode.value}
                    onClick={() => handleModeChange(mode.value)}
                    className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md transition-colors duration-150 ${
                      mode.value === marketMode
                        ? 'bg-blue-50 text-blue-700'
                        : 'hover:bg-gray-50 text-gray-700'
                    }`}
                  >
                    <span className="text-lg">{mode.icon}</span>
                    <div className="flex-1 text-left">
                      <div className="font-medium">{mode.label}</div>
                      <div className="text-xs text-gray-500">{mode.description}</div>
                    </div>
                    <div className="flex space-x-1">
                      <div
                        className={sizeClasses.preview}
                        style={{ backgroundColor: mode.colors.bullish }}
                        title="涨颜色"
                      />
                      <div
                        className={sizeClasses.preview}
                        style={{ backgroundColor: mode.colors.bearish }}
                        title="跌颜色"
                      />
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    )
  }

  return (
    <div className={`relative ${className}`}>
      {showLabel && (
        <label className="block text-sm font-medium text-gray-700 mb-2">
          <Globe className="inline-block w-4 h-4 mr-1" />
          市场模式
        </label>
      )}

      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center justify-between w-full ${sizeClasses.container} ${variantClasses} transition-colors duration-200`}
      >
        <div className="flex items-center space-x-3">
          <span className="text-xl">{currentMode?.icon}</span>
          <div>
            <div className="font-medium text-gray-900">
              {currentMode?.label}
            </div>
            {variant === 'detailed' && (
              <div className="text-xs text-gray-500">
                {currentMode?.description}
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <div className="flex space-x-1">
            <div
              className={sizeClasses.preview}
              style={{ backgroundColor: currentMode?.colors.bullish }}
              title="涨颜色"
            />
            <div
              className={sizeClasses.preview}
              style={{ backgroundColor: currentMode?.colors.bearish }}
              title="跌颜色"
            />
          </div>
          <svg
            className={`w-4 h-4 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full left-0 mt-1 w-80 bg-white border border-gray-300 rounded-lg shadow-lg z-20">
            <div className="p-4">
              <div className="flex items-center space-x-2 mb-3">
                <TrendingUp className="w-4 h-4 text-gray-600" />
                <h3 className="text-sm font-semibold text-gray-900">选择市场模式</h3>
              </div>

              <div className="space-y-2">
                {marketModes.map((mode) => (
                  <button
                    key={mode.value}
                    onClick={() => handleModeChange(mode.value)}
                    className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors duration-150 ${
                      mode.value === marketMode
                        ? 'bg-blue-50 text-blue-700 border-2 border-blue-200'
                        : 'hover:bg-gray-50 text-gray-700 border-2 border-transparent'
                    }`}
                  >
                    <span className="text-2xl">{mode.icon}</span>
                    <div className="flex-1 text-left">
                      <div className="font-medium text-base">{mode.label}</div>
                      <div className="text-sm text-gray-500">{mode.description}</div>
                    </div>
                    <div className="flex flex-col items-center space-y-1">
                      <div className="flex items-center space-x-1">
                        <div className="w-4 h-4 rounded" style={{ backgroundColor: mode.colors.bullish }} />
                        <span className="text-xs text-gray-600">涨</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <div className="w-4 h-4 rounded" style={{ backgroundColor: mode.colors.bearish }} />
                        <span className="text-xs text-gray-600">跌</span>
                      </div>
                    </div>
                  </button>
                ))}
              </div>

              {variant === 'detailed' && (
                <div className="mt-4 pt-3 border-t border-gray-200">
                  <p className="text-xs text-gray-500">
                    💡 市场模式决定涨跌颜色：中国股市习惯红涨绿跌，国际市场习惯绿涨红跌。
                    选择符合您使用习惯的模式可获得更好的视觉体验。
                  </p>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default MarketModeSelector