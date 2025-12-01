'use client';

import React, { useState } from 'react';
import {
  Download,
  Moon,
  Palette,
  RotateCcw,
  Settings,
  Sun,
  Upload,
} from 'lucide-react';
import { useTheme } from './ThemeProvider';
import { MarketModeSelector } from './MarketModeSelector';
import { ColorblindMode, ThemeMode } from '../../types/theme.types';

interface ThemeControllerProps {
  className?: string;
  variant?: 'default' | 'compact' | 'minimal';
  showMarketMode?: boolean;
  showColorblindMode?: boolean;
  showCustomColors?: boolean;
  showImportExport?: boolean;
}

export const ThemeController: React.FC<ThemeControllerProps> = ({
  className = '',
  variant = 'default',
  showMarketMode = true,
  showColorblindMode = true,
  showCustomColors = true,
  showImportExport = true,
}) => {
  const {
    currentTheme,
    themeMode,
    setThemeMode,
    marketMode,
    setMarketMode,
    colorblindConfig,
    setColorblindMode,
    exportThemes,
    importThemes,
    resetToDefaults,
  } = useTheme();

  const [showAdvanced, setShowAdvanced] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);

  // 主题模式选项
  const themeModes = [
    {
      value: 'light' as ThemeMode,
      label: '浅色',
      icon: <Sun className="w-4 h-4" />,
    },
    {
      value: 'dark' as ThemeMode,
      label: '深色',
      icon: <Moon className="w-4 h-4" />,
    },
  ];

  // 色盲模式选项
  const colorblindModes = [
    { value: 'none' as ColorblindMode, label: '无', description: '正常视觉' },
    {
      value: 'protanopia' as ColorblindMode,
      label: '红色盲',
      description: '无法感知红色',
    },
    {
      value: 'deuteranopia' as ColorblindMode,
      label: '绿色盲',
      description: '无法感知绿色',
    },
    {
      value: 'tritanopia' as ColorblindMode,
      label: '蓝色盲',
      description: '无法感知蓝色',
    },
    {
      value: 'achromatopsia' as ColorblindMode,
      label: '全色盲',
      description: '只有灰度视觉',
    },
  ];

  // 处理导入
  const handleImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      try {
        await importThemes(file);
        alert('主题配置导入成功');
      } catch (error) {
        console.error('导入失败:', error);
        alert('主题配置导入失败，请检查文件格式');
      }
      event.target.value = ''; // 清空输入
    }
  };

  // 处理色盲模式切换
  const handleColorblindModeChange = (mode: ColorblindMode) => {
    setColorblindMode({
      ...colorblindConfig,
      enabled: mode !== 'none',
      mode,
    });
  };

  // 变体样式
  const variantClasses = {
    default: 'bg-white border border-gray-200 rounded-lg shadow-sm p-4',
    compact: 'bg-white border border-gray-200 rounded-md p-3',
    minimal: 'bg-transparent p-0',
  }[variant];

  if (variant === 'minimal') {
    return (
      <div className={`flex items-center space-x-4 ${className}`}>
        {showMarketMode && <MarketModeSelector variant="compact" />}
        <div className="flex items-center space-x-2">
          {themeModes.map((mode) => (
            <button
              key={mode.value}
              onClick={() => setThemeMode(mode.value)}
              className={`p-2 rounded-md transition-colors ${
                themeMode === mode.value
                  ? 'bg-blue-100 text-blue-700'
                  : 'hover:bg-gray-100 text-gray-600'
              }`}
              title={mode.label}
            >
              {mode.icon}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={`theme-controller ${variantClasses} ${className}`}>
      {/* 头部 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Palette className="w-5 h-5 text-gray-600" />
          <h3 className="text-lg font-semibold text-gray-900">主题设置</h3>
        </div>
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center space-x-1 text-sm text-gray-600 hover:text-gray-900"
        >
          <Settings className="w-4 h-4" />
          <span>{showAdvanced ? '简化' : '高级'}</span>
        </button>
      </div>

      <div className="space-y-4">
        {/* 市场模式选择 */}
        {showMarketMode && <MarketModeSelector />}

        {/* 主题模式选择 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            主题模式
          </label>
          <div className="flex space-x-2">
            {themeModes.map((mode) => (
              <button
                key={mode.value}
                onClick={() => setThemeMode(mode.value)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg border transition-colors ${
                  themeMode === mode.value
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                }`}
              >
                {mode.icon}
                <span>{mode.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* 高级选项 */}
        {showAdvanced && (
          <>
            {/* 色盲模式 */}
            {showColorblindMode && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  色盲辅助
                </label>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {colorblindModes.map((mode) => (
                    <button
                      key={mode.value}
                      onClick={() => handleColorblindModeChange(mode.value)}
                      className={`p-2 text-xs rounded-lg border transition-colors ${
                        colorblindConfig.mode === mode.value
                          ? 'border-blue-500 bg-blue-50 text-blue-700'
                          : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      <div className="font-medium">{mode.label}</div>
                      <div className="text-gray-500">{mode.description}</div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* 当前颜色预览 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                当前颜色配置
              </label>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries({
                  涨: currentTheme.colors.bullish,
                  跌: currentTheme.colors.bearish,
                  成交量: currentTheme.colors.volume,
                  背景: currentTheme.colors.background,
                }).map(([label, color]) => (
                  <div key={label} className="flex items-center space-x-2">
                    <div
                      className="w-6 h-6 rounded border border-gray-300"
                      style={{ backgroundColor: color }}
                    />
                    <span className="text-sm text-gray-600">{label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* 导入导出 */}
            {showImportExport && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  配置管理
                </label>
                <div className="flex space-x-2">
                  <button
                    onClick={exportThemes}
                    className="flex items-center space-x-1 px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
                  >
                    <Download className="w-4 h-4" />
                    <span>导出配置</span>
                  </button>

                  <label className="flex items-center space-x-1 px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50 cursor-pointer">
                    <Upload className="w-4 h-4" />
                    <span>导入配置</span>
                    <input
                      type="file"
                      accept=".json"
                      onChange={handleImport}
                      className="hidden"
                    />
                  </label>

                  <button
                    onClick={resetToDefaults}
                    className="flex items-center space-x-1 px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
                  >
                    <RotateCcw className="w-4 h-4" />
                    <span>重置默认</span>
                  </button>
                </div>
              </div>
            )}
          </>
        )}

        {/* 主题信息 */}
        <div className="pt-3 border-t border-gray-200">
          <div className="text-xs text-gray-500">
            当前主题: {currentTheme.name} ({currentTheme.marketMode})
            {colorblindConfig.enabled &&
              ` | 色盲模式: ${colorblindConfig.mode}`}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ThemeController;
