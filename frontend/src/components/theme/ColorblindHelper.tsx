'use client';

import React, { useCallback, useState } from 'react';
import { Eye, EyeOff, Info, Settings } from 'lucide-react';
import { useTheme } from './ThemeProvider';
import { ColorblindMode } from '../../types/theme.types';

interface ColorblindHelperProps {
  className?: string;
  showPreview?: boolean;
  showControls?: boolean;
  variant?: 'default' | 'compact' | 'overlay';
}

/**
 * 色盲辅助组件
 * 提供色盲友好的视觉区分和配置功能
 */
export const ColorblindHelper: React.FC<ColorblindHelperProps> = ({
  className = '',
  showPreview = true,
  showControls = true,
  variant = 'default',
}) => {
  const { colorblindConfig, setColorblindMode, currentTheme, marketMode } =
    useTheme();

  const [showSettings, setShowSettings] = useState(false);

  // 色盲模式选项
  const colorblindModes = [
    {
      value: 'none' as ColorblindMode,
      label: '无辅助',
      description: '正常色彩视觉',
      icon: '👁️',
    },
    {
      value: 'protanopia' as ColorblindMode,
      label: '红色盲辅助',
      description: '使用形状和纹理区分涨跌',
      icon: '🔴',
    },
    {
      value: 'deuteranopia' as ColorblindMode,
      label: '绿色盲辅助',
      description: '使用蓝色和紫色区分信号',
      icon: '🟢',
    },
    {
      value: 'tritanopia' as ColorblindMode,
      label: '蓝色盲辅助',
      description: '使用红绿色系区分信号',
      icon: '🔵',
    },
    {
      value: 'achromatopsia' as ColorblindMode,
      label: '全色盲辅助',
      description: '使用高对比度灰度',
      icon: '⚫',
    },
  ];

  // 生成涨跌图案预览
  const generatePatternPreview = useCallback(
    (type: 'bullish' | 'bearish') => {
      const patterns = {
        protanopia: {
          bullish: '▲', // 三角形
          bearish: '▼', // 倒三角
        },
        deuteranopia: {
          bullish: '◆', // 菱形
          bearish: '●', // 圆形
        },
        tritanopia: {
          bullish: '■', // 方形
          bearish: '⬟', // 六边形
        },
        achromatopsia: {
          bullish: '━', // 粗线
          bearish: '┃', // 粗线
        },
      };

      if (colorblindConfig.mode === 'none') {
        return null;
      }

      return patterns[colorblindConfig.mode]?.[type] || null;
    },
    [colorblindConfig.mode],
  );

  // 切换色盲模式
  const handleModeChange = (mode: ColorblindMode) => {
    setColorblindMode({
      ...colorblindConfig,
      enabled: mode !== 'none',
      mode,
      usePatterns: mode !== 'none',
      useShapes: mode !== 'none',
      textureIntensity: 0.7,
    });
  };

  // 更新色盲配置
  const updateConfig = (updates: Partial<typeof colorblindConfig>) => {
    setColorblindMode({
      ...colorblindConfig,
      ...updates,
    });
  };

  // 变体样式
  const variantClasses = {
    default: 'bg-white border border-gray-200 rounded-lg shadow-sm p-4',
    compact: 'bg-white border border-gray-200 rounded-md p-3',
    overlay:
      'bg-white/95 backdrop-blur-sm border border-gray-200 rounded-lg shadow-lg p-4 fixed top-4 right-4 z-50 max-w-sm',
  }[variant];

  const currentMode = colorblindModes.find(
    (mode) => mode.value === colorblindConfig.mode,
  );

  if (variant === 'overlay') {
    return (
      <div
        className={`colorblind-helper-overlay ${variantClasses} ${className}`}
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            <Eye className="w-4 h-4 text-blue-600" />
            <h4 className="text-sm font-semibold text-gray-900">色盲辅助</h4>
          </div>
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="p-1 rounded hover:bg-gray-100"
          >
            <Settings className="w-4 h-4 text-gray-600" />
          </button>
        </div>

        {showSettings ? (
          <div className="space-y-3">
            {colorblindModes.map((mode) => (
              <button
                key={mode.value}
                onClick={() => handleModeChange(mode.value)}
                className={`w-full flex items-center space-x-3 p-2 rounded-lg text-left transition-colors ${
                  colorblindConfig.mode === mode.value
                    ? 'bg-blue-50 text-blue-700 border-2 border-blue-200'
                    : 'hover:bg-gray-50 text-gray-700 border-2 border-transparent'
                }`}
              >
                <span className="text-lg">{mode.icon}</span>
                <div className="flex-1">
                  <div className="font-medium text-sm">{mode.label}</div>
                  <div className="text-xs text-gray-500">
                    {mode.description}
                  </div>
                </div>
              </button>
            ))}
          </div>
        ) : (
          <div className="text-center">
            <div className="text-lg mb-2">{currentMode?.icon}</div>
            <div className="text-sm font-medium text-gray-900">
              {currentMode?.label}
            </div>
            <div className="text-xs text-gray-500">
              {currentMode?.description}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`colorblind-helper ${variantClasses} ${className}`}>
      {/* 头部 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          {colorblindConfig.enabled ? (
            <Eye className="w-5 h-5 text-blue-600" />
          ) : (
            <EyeOff className="w-5 h-5 text-gray-400" />
          )}
          <h3 className="text-lg font-semibold text-gray-900">色盲辅助</h3>
        </div>
        <div className="flex items-center space-x-2">
          <div
            className={`w-2 h-2 rounded-full ${
              colorblindConfig.enabled ? 'bg-green-500' : 'bg-gray-300'
            }`}
          />
          <span className="text-sm text-gray-600">
            {colorblindConfig.enabled ? '已启用' : '未启用'}
          </span>
        </div>
      </div>

      {/* 模式选择 */}
      {showControls && (
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              辅助模式
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {colorblindModes.map((mode) => (
                <button
                  key={mode.value}
                  onClick={() => handleModeChange(mode.value)}
                  className={`flex items-center space-x-3 p-3 rounded-lg border transition-colors ${
                    colorblindConfig.mode === mode.value
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <span className="text-xl">{mode.icon}</span>
                  <div className="text-left">
                    <div className="font-medium text-sm">{mode.label}</div>
                    <div className="text-xs text-gray-500">
                      {mode.description}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* 辅助选项 */}
          {colorblindConfig.enabled && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                辅助选项
              </label>
              <div className="space-y-2">
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={colorblindConfig.usePatterns}
                    onChange={(e) =>
                      updateConfig({ usePatterns: e.target.checked })
                    }
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm text-gray-700">
                    使用图案纹理区分
                  </span>
                </label>
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={colorblindConfig.useShapes}
                    onChange={(e) =>
                      updateConfig({ useShapes: e.target.checked })
                    }
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm text-gray-700">
                    使用形状符号区分
                  </span>
                </label>
              </div>

              {/* 纹理强度调节 */}
              {colorblindConfig.usePatterns && (
                <div className="mt-3">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    纹理强度:{' '}
                    {Math.round(colorblindConfig.textureIntensity * 100)}%
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={colorblindConfig.textureIntensity * 100}
                    onChange={(e) =>
                      updateConfig({
                        textureIntensity: Number(e.target.value) / 100,
                      })
                    }
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                  />
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* 颜色预览 */}
      {showPreview && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            颜色预览
          </label>
          <div className="grid grid-cols-2 gap-4">
            {/* 涨颜色 */}
            <div className="text-center">
              <div
                className="w-full h-16 rounded-lg border-2 border-gray-300 flex items-center justify-center text-2xl font-bold"
                style={{
                  backgroundColor: currentTheme.colors.bullish,
                  color: marketMode === 'chinese' ? 'white' : 'black',
                }}
              >
                {generatePatternPreview('bullish') || '涨'}
              </div>
              <div className="mt-1 text-xs text-gray-600">涨颜色</div>
              <div className="text-xs text-gray-500">
                {currentTheme.colors.bullish}
              </div>
            </div>

            {/* 跌颜色 */}
            <div className="text-center">
              <div
                className="w-full h-16 rounded-lg border-2 border-gray-300 flex items-center justify-center text-2xl font-bold"
                style={{
                  backgroundColor: currentTheme.colors.bearish,
                  color: marketMode === 'chinese' ? 'black' : 'white',
                }}
              >
                {generatePatternPreview('bearish') || '跌'}
              </div>
              <div className="mt-1 text-xs text-gray-600">跌颜色</div>
              <div className="text-xs text-gray-500">
                {currentTheme.colors.bearish}
              </div>
            </div>
          </div>

          {/* 说明文字 */}
          <div className="mt-3 flex items-start space-x-2">
            <Info className="w-4 h-4 text-blue-600 mt-0.5" />
            <div className="text-xs text-gray-600">
              {colorblindConfig.enabled
                ? '色盲辅助已启用，使用形状和图案帮助区分涨跌信号。'
                : '色盲辅助未启用，仅使用颜色区分涨跌信号。'}
              {colorblindConfig.enabled && colorblindConfig.mode !== 'none' && (
                <div className="mt-1">当前模式: {currentMode?.description}</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ColorblindHelper;
