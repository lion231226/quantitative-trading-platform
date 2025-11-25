'use client'

import React, { useState } from 'react'
import { ThemeProvider, useTheme } from './ThemeProvider'
import { MarketModeSelector } from './MarketModeSelector'
import { ThemeController } from './ThemeController'
import { ColorblindHelper } from './ColorblindHelper'
import { ColorPicker } from './ColorPicker'
import { ThemedKlineChart } from '../charts'
import { generateMockKlineData } from '../../utils/klineHelpers'

interface ThemeDemoProps {
  className?: string
}

/**
 * 主题系统演示组件
 * 展示完整的主题切换、市场模式、色盲辅助和自定义颜色功能
 */
export const ThemeDemoContent: React.FC<ThemeDemoProps> = ({ className = '' }) => {
  const { currentTheme, setThemeMode, exportThemes } = useTheme()
  const [activeTab, setActiveTab] = useState<'market' | 'theme' | 'colorblind' | 'custom'>('market')

  // 生成模拟数据
  const mockKlineData = generateMockKlineData(100)

  // 标签页配置
  const tabs = [
    { id: 'market' as const, label: '市场模式', icon: '🌍' },
    { id: 'theme' as const, label: '主题切换', icon: '🎨' },
    { id: 'colorblind' as const, label: '色盲辅助', icon: '👁️' },
    { id: 'custom' as const, label: '自定义颜色', icon: '🎯' }
  ]

  return (
    <div className={`theme-demo ${className}`}>
      <div className="max-w-7xl mx-auto p-6">
        {/* 头部 */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            个性化颜色配置与可访问性支持
          </h1>
          <p className="text-lg text-gray-600">
            支持中国市场模式、国际市场模式、色盲友好模式和自定义颜色配置
          </p>
        </div>

        {/* 当前主题信息 */}
        <div className="mb-6 p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-blue-200">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                当前主题: {currentTheme.name}
              </h2>
              <p className="text-sm text-gray-600">
                市场模式: {currentTheme.marketMode === 'chinese' ? '中国市场 (红涨绿跌)' : '国际市场 (绿涨红跌)'}
                {currentTheme.colorblindMode !== 'none' && ` | 色盲模式: ${currentTheme.colorblindMode}`}
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-right text-sm">
                <div className="text-gray-600">涨颜色</div>
                <div
                  className="inline-block w-12 h-8 rounded border border-gray-300"
                  style={{ backgroundColor: currentTheme.colors.bullish }}
                />
              </div>
              <div className="text-right text-sm">
                <div className="text-gray-600">跌颜色</div>
                <div
                  className="inline-block w-12 h-8 rounded border border-gray-300"
                  style={{ backgroundColor: currentTheme.colors.bearish }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* 标签页导航 */}
        <div className="mb-6">
          <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 flex items-center justify-center space-x-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-white text-blue-700 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* 内容区域 */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 控制面板 */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              {activeTab === 'market' && (
                <MarketModeSelector showLabel={true} variant="detailed" />
              )}
              {activeTab === 'theme' && (
                <ThemeController showMarketMode={false} showColorblindMode={false} />
              )}
              {activeTab === 'colorblind' && (
                <ColorblindHelper showPreview={true} showControls={true} />
              )}
              {activeTab === 'custom' && (
                <ColorPicker showPreview={true} showPresets={true} />
              )}
            </div>
          </div>

          {/* 图表预览 */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="mb-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  图表预览
                </h3>
                <p className="text-sm text-gray-600">
                  实时预览主题变化对K线图的影响
                </p>
              </div>

              <ThemedKlineChart
                data={mockKlineData}
                height={400}
                autoApplyTheme={true}
              />

              {/* 主题特性说明 */}
              <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                  <h4 className="text-sm font-semibold text-green-800 mb-2">✅ 已实现功能</h4>
                  <ul className="text-sm text-green-700 space-y-1">
                    <li>• 中国市场模式（红涨绿跌）</li>
                    <li>• 国际市场模式（绿涨红跌）</li>
                    <li>• 明暗主题切换</li>
                    <li>• 色盲友好辅助</li>
                    <li>• 自定义颜色配置</li>
                    <li>• 配色方案导入导出</li>
                  </ul>
                </div>
                <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <h4 className="text-sm font-semibold text-blue-800 mb-2">🔧 技术特性</h4>
                  <ul className="text-sm text-blue-700 space-y-1">
                    <li>• React Context 状态管理</li>
                    <li>• TypeScript 类型安全</li>
                    <li>• 本地存储持久化</li>
                    <li>• WCAG 2.1 可访问性标准</li>
                    <li>• 实时主题预览</li>
                    <li>• 配置导入导出</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 快捷操作 */}
        <div className="mt-6 flex justify-center space-x-4">
          <button
            onClick={() => setThemeMode('light')}
            className="flex items-center space-x-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <span>☀️</span>
            <span>浅色主题</span>
          </button>
          <button
            onClick={() => setThemeMode('dark')}
            className="flex items-center space-x-2 px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-700"
          >
            <span>🌙</span>
            <span>深色主题</span>
          </button>
          <button
            onClick={exportThemes}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <span>💾</span>
            <span>导出配置</span>
          </button>
        </div>
      </div>
    </div>
  )
}

/**
 * 带主题提供者的完整演示组件
 */
export const ThemeDemo: React.FC<ThemeDemoProps> = (props) => {
  return (
    <ThemeProvider>
      <ThemeDemoContent {...props} />
    </ThemeProvider>
  )
}

export default ThemeDemo