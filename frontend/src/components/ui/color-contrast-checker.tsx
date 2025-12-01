/**
 * 颜色对比度检查器组件
 * 用于实时检查和调整颜色对比度
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Button } from './button';
import { Card, CardContent, CardHeader, CardTitle } from './card';
import { getContrastRatio, adjustColorForContrast, getContrastRecommendations, generateHighContrastTheme, analyzeThemeColors } from '@/utils/accessibility/color-contrast';
import { AlertTriangle, CheckCircle, XCircle, Eye, EyeOff, Palette, RefreshCw } from 'lucide-react';

export interface ColorContrastCheckerProps {
  /** 前景色 */
  foregroundColor?: string;
  /** 背景色 */
  backgroundColor?: string;
  /** 是否显示建议 */
  showSuggestions?: boolean;
  /** 是否显示预览 */
  showPreview?: boolean;
  /** 自定义样式类名 */
  className?: string;
}

/**
 * 颜色对比度检查器组件
 */
export const ColorContrastChecker: React.FC<ColorContrastCheckerProps> = ({
  foregroundColor = '#000000',
  backgroundColor = '#ffffff',
  showSuggestions = true,
  showPreview = true,
  className = '',
}) => {
  const [fgColor, setFgColor] = useState(foregroundColor);
  const [bgColor, setBgColor] = useState(backgroundColor);
  const [contrastResult, setContrastResult] = useState(() => getContrastRatio(fgColor, bgColor));
  const [suggestedColors, setSuggestedColors] = useState<{
    foreground?: string;
    background?: string;
  }>({});
  const [showAdvanced, setShowAdvanced] = useState(false);

  // 计算对比度
  useEffect(() => {
    const result = getContrastRatio(fgColor, bgColor);
    setContrastResult(result);

    // 生成建议颜色
    const adjustedFg = adjustColorForContrast(fgColor, bgColor, 4.5);
    const adjustedBg = adjustColorForContrast(bgColor, fgColor, 4.5);

    setSuggestedColors({
      foreground: adjustedFg.suggestedForeground,
      background: adjustedBg.suggestedForeground, // 这里应该是背景色建议
    });
  }, [fgColor, bgColor]);

  // 应用建议颜色
  const applySuggestion = useCallback((type: 'foreground' | 'background') => {
    if (type === 'foreground' && suggestedColors.foreground) {
      setFgColor(suggestedColors.foreground);
    } else if (type === 'background' && suggestedColors.background) {
      setBgColor(suggestedColors.background);
    }
  }, [suggestedColors]);

  // 生成高对比度版本
  const generateHighContrast = useCallback(() => {
    const isDarkBg = getContrastRatio('#ffffff', bgColor).ratio < getContrastRatio('#000000', bgColor).ratio;
    const newFg = isDarkBg ? '#ffffff' : '#000000';
    const newBg = isDarkBg ? '#000000' : '#ffffff';

    setFgColor(newFg);
    setBgColor(newBg);
  }, [bgColor]);

  // 交换颜色
  const swapColors = useCallback(() => {
    setFgColor(bgColor);
    setBgColor(fgColor);
  }, [bgColor, fgColor]);

  // 获取状态图标
  const getStatusIcon = () => {
    switch (contrastResult.level) {
      case 'AAA':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'AA':
        return <CheckCircle className="h-5 w-5 text-yellow-600" />;
      default:
        return <XCircle className="h-5 w-5 text-red-600" />;
    }
  };

  // 获取状态文本
  const getStatusText = () => {
    switch (contrastResult.level) {
      case 'AAA':
        return 'WCAG AAA 级别';
      case 'AA':
        return 'WCAG AA 级别';
      default:
        return '不符合 WCAG 标准';
    }
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Palette className="h-5 w-5" />
          <span>颜色对比度检查器</span>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* 颜色输入 */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="foreground-color" className="block text-sm font-medium mb-2">
              前景色
            </label>
            <div className="flex space-x-2">
              <input
                id="foreground-color"
                type="color"
                value={fgColor}
                onChange={(e) => setFgColor(e.target.value)}
                className="h-10 w-20 border rounded"
                aria-label="前景色选择器"
              />
              <input
                type="text"
                value={fgColor}
                onChange={(e) => setFgColor(e.target.value)}
                placeholder="#000000"
                className="flex-1 px-3 py-2 border rounded"
                aria-label="前景色十六进制值"
              />
            </div>
          </div>

          <div>
            <label htmlFor="background-color" className="block text-sm font-medium mb-2">
              背景色
            </label>
            <div className="flex space-x-2">
              <input
                id="background-color"
                type="color"
                value={bgColor}
                onChange={(e) => setBgColor(e.target.value)}
                className="h-10 w-20 border rounded"
                aria-label="背景色选择器"
              />
              <input
                type="text"
                value={bgColor}
                onChange={(e) => setBgColor(e.target.value)}
                placeholder="#ffffff"
                className="flex-1 px-3 py-2 border rounded"
                aria-label="背景色十六进制值"
              />
            </div>
          </div>
        </div>

        {/* 预览 */}
        {showPreview && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium">预览</label>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowAdvanced(!showAdvanced)}
              >
                {showAdvanced ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
            </div>

            <div
              className="p-4 rounded border text-center font-medium"
              style={{
                backgroundColor: bgColor,
                color: fgColor,
              }}
            >
              示例文本 Sample Text
            </div>

            {showAdvanced && (
              <div className="mt-4 grid grid-cols-3 gap-2">
                <div
                  className="p-3 rounded border text-center text-sm"
                  style={{ backgroundColor: bgColor, color: fgColor }}
                >
                  正常文本
                </div>
                <div
                  className="p-3 rounded border text-center text-sm font-bold"
                  style={{ backgroundColor: bgColor, color: fgColor }}
                >
                  粗体文本
                </div>
                <div
                  className="p-3 rounded border text-center text-xs"
                  style={{ backgroundColor: bgColor, color: fgColor }}
                >
                  小号文本
                </div>
              </div>
            )}
          </div>
        )}

        {/* 对比度结果 */}
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-medium flex items-center space-x-2">
              {getStatusIcon()}
              <span>对比度结果</span>
            </h3>
            <div className="text-right">
              <div className="text-2xl font-bold">
                {contrastResult.ratio}:1
              </div>
              <div className="text-sm text-muted-foreground">
                {getStatusText()}
              </div>
            </div>
          </div>

          {/* 进度条 */}
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-300 ${
                contrastResult.level === 'AAA'
                  ? 'bg-green-600'
                  : contrastResult.level === 'AA'
                  ? 'bg-yellow-600'
                  : 'bg-red-600'
              }`}
              style={{
                width: `${Math.min(100, (contrastResult.ratio / 7) * 100)}%`,
              }}
            />
          </div>

          {/* 标准标记 */}
          <div className="flex justify-between mt-2 text-xs text-muted-foreground">
            <span>4.5:1 (AA)</span>
            <span>7:1 (AAA)</span>
          </div>
        </div>

        {/* 建议和操作 */}
        {showSuggestions && contrastResult.level !== 'AAA' && (
          <div className="space-y-4">
            {/* 建议 */}
            <div>
              <h3 className="font-medium mb-2 flex items-center space-x-2">
                <AlertTriangle className="h-4 w-4" />
                <span>建议</span>
              </h3>
              <ul className="text-sm space-y-1 text-muted-foreground">
                {getContrastRecommendations(contrastResult).map((recommendation, index) => (
                  <li key={index}>• {recommendation}</li>
                ))}
              </ul>
            </div>

            {/* 快速操作 */}
            <div className="flex flex-wrap gap-2">
              {suggestedColors.foreground && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => applySuggestion('foreground')}
                  className="flex items-center space-x-1"
                >
                  <RefreshCw className="h-4 w-4" />
                  <span>调整前景色</span>
                </Button>
              )}

              {suggestedColors.background && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => applySuggestion('background')}
                  className="flex items-center space-x-1"
                >
                  <RefreshCw className="h-4 w-4" />
                  <span>调整背景色</span>
                </Button>
              )}

              <Button
                variant="outline"
                size="sm"
                onClick={generateHighContrast}
                className="flex items-center space-x-1"
              >
                <Palette className="h-4 w-4" />
                <span>高对比度</span>
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={swapColors}
                className="flex items-center space-x-1"
              >
                <RefreshCw className="h-4 w-4" />
                <span>交换颜色</span>
              </Button>
            </div>
          </div>
        )}

        {/* 详细信息 */}
        <details className="border rounded-lg p-4">
          <summary className="cursor-pointer font-medium">
            详细信息
          </summary>
          <div className="mt-4 space-y-2 text-sm text-muted-foreground">
            <div>WCAG 2.1 要求:</div>
            <ul className="ml-4 space-y-1">
              <li>• AA 级别: 正常文本 4.5:1，大文本 3:1</li>
              <li>• AAA 级别: 正常文本 7:1，大文本 4.5:1</li>
              <li>• 大文本: 18pt+ 或 14pt+ 粗体</li>
            </ul>
            <div className="mt-2">
              <strong>当前状态:</strong> {contrastResult.passesAA ? '✅' : '❌'} AA 标准,
              {' '}{contrastResult.passesAAA ? '✅' : '❌'} AAA 标准
            </div>
          </div>
        </details>
      </CardContent>
    </Card>
  );
};

/**
 * 主题对比度分析器
 */
export interface ThemeContrastAnalyzerProps {
  /** 主题配置 */
  theme: Record<string, string>;
  /** 自定义样式类名 */
  className?: string;
}

export const ThemeContrastAnalyzer: React.FC<ThemeContrastAnalyzerProps> = ({
  theme,
  className = '',
}) => {
  const [analyses, setAnalyses] = useState(() => analyzeThemeColors(theme));
  const [highContrastTheme, setHighContrastTheme] = useState(() => generateHighContrastTheme(theme));

  useEffect(() => {
    setAnalyses(analyzeThemeColors(theme));
    setHighContrastTheme(generateHighContrastTheme(theme));
  }, [theme]);

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>主题对比度分析</CardTitle>
      </CardHeader>

      <CardContent>
        <div className="space-y-4">
          {/* 分析结果 */}
          <div>
            <h3 className="font-medium mb-3">当前主题分析</h3>
            <div className="space-y-2">
              {analyses.map((analysis, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 border rounded"
                >
                  <div className="flex items-center space-x-3">
                    <div
                      className="w-8 h-8 rounded border"
                      style={{
                        backgroundColor: analysis.background,
                        color: analysis.foreground,
                      }}
                    />
                    <div>
                      <div className="font-medium">{analysis.name}</div>
                      <div className="text-sm text-muted-foreground">
                        {analysis.foreground} / {analysis.background}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`font-bold ${
                      analysis.result.level === 'AAA'
                        ? 'text-green-600'
                        : analysis.result.level === 'AA'
                        ? 'text-yellow-600'
                        : 'text-red-600'
                    }`}>
                      {analysis.result.ratio}:1
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {analysis.result.level}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 高对比度主题 */}
          <div>
            <h3 className="font-medium mb-3">高对比度版本</h3>
            <div className="p-4 border rounded bg-gray-50 dark:bg-gray-900">
              <div className="grid grid-cols-2 gap-4 text-sm">
                {Object.entries(highContrastTheme).slice(0, 8).map(([key, value]) => (
                  <div key={key} className="flex items-center space-x-2">
                    <div
                      className="w-6 h-6 rounded border"
                      style={{ backgroundColor: value }}
                    />
                    <div>
                      <div className="font-medium">{key}</div>
                      <div className="text-muted-foreground">{value}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 统计信息 */}
          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
            <h3 className="font-medium mb-2">统计信息</h3>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {analyses.filter(a => a.result.passesAAA).length}
                </div>
                <div className="text-muted-foreground">AAA 级别</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-600">
                  {analyses.filter(a => a.result.passesAA).length}
                </div>
                <div className="text-muted-foreground">AA 级别</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">
                  {analyses.filter(a => !a.result.passesAA).length}
                </div>
                <div className="text-muted-foreground">需改进</div>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default ColorContrastChecker;