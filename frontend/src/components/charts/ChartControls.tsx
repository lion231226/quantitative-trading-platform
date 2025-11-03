'use client';

import React, { useState } from 'react';
import { ChartConfig, ExportFormat } from '@/types/chart.types';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  ChevronLeft,
  ChevronRight,
  Download,
  Maximize2,
  Move,
  Palette,
  RotateCcw,
  Settings,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';

interface ChartControlsProps {
  config: ChartConfig
  onConfigChange: (config: Partial<ChartConfig>) => void
  onReset: () => void
  onZoomIn?: () => void
  onZoomOut?: () => void
  onZoomReset?: () => void
  onPanToggle?: () => void
  onExport?: (format: ExportFormat) => void
  onToggleFullscreen?: () => void
  onNavigatePrevious?: () => void
  onNavigateNext?: () => void
  disabled?: boolean
  isPanning?: boolean
  isFullscreen?: boolean
  showNavigation?: boolean
  showExport?: boolean
  showZoom?: boolean
  compact?: boolean
}

export function ChartControls({
  config,
  onConfigChange,
  onReset,
  onZoomIn,
  onZoomOut,
  onZoomReset,
  onPanToggle,
  onExport,
  onToggleFullscreen,
  onNavigatePrevious,
  onNavigateNext,
  disabled = false,
  isPanning = false,
  isFullscreen = false,
  showNavigation = false,
  showExport = true,
  showZoom = true,
  compact = false,
}: ChartControlsProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [exportFormat, setExportFormat] = useState<ExportFormat>('png');
  const handleExport = () => {
    if (onExport) {
      onExport(exportFormat);
    }
  };

  if (compact) {
    return (
      <div className="flex items-center space-x-2 p-2 bg-background border rounded-lg">
        {showZoom && (
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={onZoomIn}
              disabled={disabled}
              title="放大"
            >
              <ZoomIn className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onZoomOut}
              disabled={disabled}
              title="缩小"
            >
              <ZoomOut className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onZoomReset}
              disabled={disabled}
              title="重置缩放"
            >
              <RotateCcw className="h-4 w-4" />
            </Button>
          </>
        )}

        {onPanToggle && (
          <Button
            variant={isPanning ? 'default' : 'ghost'}
            size="sm"
            onClick={onPanToggle}
            disabled={disabled}
            title="拖拽模式"
          >
            <Move className="h-4 w-4" />
          </Button>
        )}

        {showNavigation && (
          <div className="flex items-center space-x-1 border-l pl-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={onNavigatePrevious}
              disabled={disabled}
              title="上一个"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onNavigateNext}
              disabled={disabled}
              title="下一个"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        )}

        {showExport && (
          <div className="flex items-center space-x-1 border-l pl-2">
            <select
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value as ExportFormat)}
              className="text-xs border rounded px-1 py-0.5"
              disabled={disabled}
            >
              <option value="png">PNG</option>
              <option value="csv">CSV</option>
              <option value="json">JSON</option>
            </select>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleExport}
              disabled={disabled}
              title="导出"
            >
              <Download className="h-4 w-4" />
            </Button>
          </div>
        )}

        {onToggleFullscreen && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onToggleFullscreen}
            disabled={disabled}
            title={isFullscreen ? '退出全屏' : '全屏'}
          >
            <Maximize2 className="h-4 w-4" />
          </Button>
        )}
      </div>
    );
  }

  return (
    <Card className="mb-4">
      <CardContent className="p-4">
        {/* 主要控制栏 */}
        <div className="flex flex-wrap gap-4 items-center mb-4">
          {/* 显示控制 */}
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="show-signals"
                checked={config.showSignals}
                onChange={(e) => onConfigChange({ showSignals: e.target.checked })}
                disabled={disabled}
                className="rounded"
              />
              <label htmlFor="show-signals" className="text-sm font-medium">
                显示交易信号
              </label>
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="show-ma"
                checked={config.showMovingAverages}
                onChange={(e) => onConfigChange({ showMovingAverages: e.target.checked })}
                disabled={disabled}
                className="rounded"
              />
              <label htmlFor="show-ma" className="text-sm font-medium">
                显示移动平均线
              </label>
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="show-volume"
                checked={config.showVolume}
                onChange={(e) => onConfigChange({ showVolume: e.target.checked })}
                disabled={disabled}
                className="rounded"
              />
              <label htmlFor="show-volume" className="text-sm font-medium">
                显示成交量
              </label>
            </div>
          </div>

          {/* 缩放控制 */}
          {showZoom && (
            <div className="flex items-center space-x-2 border-l pl-4">
              <span className="text-sm font-medium">缩放:</span>
              <Button
                variant="outline"
                size="sm"
                onClick={onZoomIn}
                disabled={disabled || !onZoomIn}
              >
                <ZoomIn className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={onZoomOut}
                disabled={disabled || !onZoomOut}
              >
                <ZoomOut className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={onZoomReset}
                disabled={disabled || !onZoomReset}
              >
                <RotateCcw className="h-4 w-4" />
              </Button>

              {onPanToggle && (
                <Button
                  variant={isPanning ? 'default' : 'outline'}
                  size="sm"
                  onClick={onPanToggle}
                  disabled={disabled}
                >
                  <Move className="h-4 w-4 mr-1" />
                  拖拽
                </Button>
              )}
            </div>
          )}

          {/* 导出控制 */}
          {showExport && (
            <div className="flex items-center space-x-2 border-l pl-4">
              <span className="text-sm font-medium">导出:</span>
              <select
                value={exportFormat}
                onChange={(e) => setExportFormat(e.target.value as ExportFormat)}
                className="border rounded px-2 py-1 text-sm"
                disabled={disabled}
              >
                <option value="png">PNG</option>
                <option value="csv">CSV</option>
                <option value="json">JSON</option>
              </select>
              <Button
                variant="outline"
                size="sm"
                onClick={handleExport}
                disabled={disabled || !onExport}
              >
                <Download className="h-4 w-4 mr-1" />
                导出
              </Button>
            </div>
          )}

          {/* 其他控制 */}
          <div className="flex items-center space-x-2 border-l pl-4">
            {onToggleFullscreen && (
              <Button
                variant="outline"
                size="sm"
                onClick={onToggleFullscreen}
                disabled={disabled}
              >
                <Maximize2 className="h-4 w-4 mr-1" />
                {isFullscreen ? '退出全屏' : '全屏'}
              </Button>
            )}

            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowAdvanced(!showAdvanced)}
              disabled={disabled}
            >
              <Settings className="h-4 w-4 mr-1" />
              高级设置
            </Button>

            <Button variant="outline" size="sm" onClick={onReset} disabled={disabled}>
              重置
            </Button>
          </div>
        </div>

        {/* 高级设置面板 */}
        {showAdvanced && (
          <div className="border-t pt-4 space-y-4">
            {/* 移动平均线配置 */}
            {config.showMovingAverages && (
              <div className="flex items-center space-x-4">
                <h4 className="text-sm font-medium text-muted-foreground">移动平均线:</h4>
                <div className="flex items-center space-x-2">
                  <label htmlFor="ma-type" className="text-sm">
                    类型:
                  </label>
                  <select
                    id="ma-type"
                    value={config.movingAverageType}
                    onChange={(e) => onConfigChange({ movingAverageType: e.target.value as 'SMA' | 'EMA' })}
                    disabled={disabled}
                    className="border rounded px-2 py-1 text-sm"
                  >
                    <option value="SMA">SMA</option>
                    <option value="EMA">EMA</option>
                  </select>
                </div>

                <div className="flex items-center space-x-2">
                  <label htmlFor="ma-period" className="text-sm">
                    周期:
                  </label>
                  <input
                    id="ma-period"
                    type="number"
                    value={config.movingAveragePeriod}
                    onChange={(e) => onConfigChange({ movingAveragePeriod: parseInt(e.target.value) || 20 })}
                    disabled={disabled}
                    min="5"
                    max="200"
                    className="border rounded px-2 py-1 w-20 text-sm"
                  />
                </div>
              </div>
            )}

            {/* 动画控制 */}
            <div className="flex items-center space-x-4">
              <h4 className="text-sm font-medium text-muted-foreground">动画:</h4>
              <div className="flex items-center space-x-2">
                <label htmlFor="animation" className="text-sm">
                  时长(ms):
                </label>
                <input
                  id="animation"
                  type="number"
                  value={config.animationDuration}
                  onChange={(e) => onConfigChange({ animationDuration: parseInt(e.target.value) || 1000 })}
                  disabled={disabled}
                  min="0"
                  max="5000"
                  step="100"
                  className="border rounded px-2 py-1 w-24 text-sm"
                />
              </div>
            </div>

            {/* 导航控制 */}
            {showNavigation && (
              <div className="flex items-center space-x-4">
                <h4 className="text-sm font-medium text-muted-foreground">导航:</h4>
                <div className="flex items-center space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onNavigatePrevious}
                    disabled={disabled || !onNavigatePrevious}
                  >
                    <ChevronLeft className="h-4 w-4 mr-1" />
                    上一个
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onNavigateNext}
                    disabled={disabled || !onNavigateNext}
                  >
                    下一个
                    <ChevronRight className="h-4 w-4 ml-1" />
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
