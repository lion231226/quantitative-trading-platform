import React, { useState } from 'react';
import { ChartControlsProps } from '../../types/kline.types';

export const KlineChartControls: React.FC<ChartControlsProps> = ({
  onZoomIn,
  onZoomOut,
  onResetZoom,
  onToggleCrosshair,
  onToggleGrid,
  onExport,
  onFullscreen,
  className = '',
  showCrosshair = false,
  showGrid = true,
  disabled = false,
}) => {
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [exportFormat, setExportFormat] = useState<
    'png' | 'jpeg' | 'svg' | 'csv' | 'json'
  >('png');

  // 处理导出
  const handleExport = (format: string) => {
    onExport?.();
    setShowExportMenu(false);
  };

  // 工具提示配置
  const getTooltipText = (action: string): string => {
    const tooltips: Record<string, string> = {
      zoomIn: '放大图表 (+)',
      zoomOut: '缩小图表 (-)',
      resetZoom: '重置缩放 (R)',
      toggleCrosshair: '切换十字线 (C)',
      toggleGrid: '切换网格 (G)',
      export: '导出图表 (E)',
      fullscreen: '全屏显示 (F)',
    };
    return tooltips[action] || action;
  };

  // 按钮基础样式
  const getButtonStyles = (isActive: boolean = false) => {
    const baseStyles =
      'p-2 rounded-lg transition-all duration-200 flex items-center justify-center';

    if (disabled) {
      return `${baseStyles} text-gray-400 bg-gray-100 cursor-not-allowed`;
    }

    if (isActive) {
      return `${baseStyles} text-white bg-blue-600 shadow-md`;
    }

    return `${baseStyles} text-gray-700 bg-white border border-gray-300 hover:border-blue-400 hover:bg-blue-50 hover:text-blue-700`;
  };

  return (
    <div className={`kline-chart-controls ${className}`}>
      <div className="flex items-center gap-2 bg-white rounded-lg shadow-sm border border-gray-200 p-2">
        {/* 缩放控制 */}
        <div className="flex items-center gap-1 border-r border-gray-300 pr-2">
          <button
            onClick={onZoomIn}
            disabled={disabled}
            className={getButtonStyles()}
            title={getTooltipText('zoomIn')}
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7"
              />
            </svg>
          </button>

          <button
            onClick={onZoomOut}
            disabled={disabled}
            className={getButtonStyles()}
            title={getTooltipText('zoomOut')}
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7"
              />
            </svg>
          </button>

          <button
            onClick={onResetZoom}
            disabled={disabled}
            className={getButtonStyles()}
            title={getTooltipText('resetZoom')}
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>
        </div>

        {/* 显示控制 */}
        <div className="flex items-center gap-1 border-r border-gray-300 pr-2">
          <button
            onClick={onToggleCrosshair}
            disabled={disabled}
            className={getButtonStyles(showCrosshair)}
            title={getTooltipText('toggleCrosshair')}
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 12h14M12 5l7 7-7 7"
              />
            </svg>
          </button>

          <button
            onClick={onToggleGrid}
            disabled={disabled}
            className={getButtonStyles(showGrid)}
            title={getTooltipText('toggleGrid')}
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16M6 4v16M12 4v16M18 4v16"
              />
            </svg>
          </button>
        </div>

        {/* 导出控制 */}
        <div className="relative">
          <button
            onClick={() => setShowExportMenu(!showExportMenu)}
            disabled={disabled}
            className={getButtonStyles()}
            title={getTooltipText('export')}
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
          </button>

          {/* 导出菜单 */}
          {showExportMenu && (
            <div className="absolute top-full left-0 mt-1 w-48 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
              <div className="p-2">
                <div className="text-xs text-gray-600 mb-2">导出格式:</div>
                <div className="space-y-1">
                  {['png', 'jpeg', 'svg', 'csv', 'json'].map((format) => (
                    <button
                      key={format}
                      onClick={() => handleExport(format)}
                      className={`w-full text-left px-3 py-2 text-sm rounded transition-colors ${
                        exportFormat === format
                          ? 'bg-blue-100 text-blue-700'
                          : 'hover:bg-gray-100 text-gray-700'
                      }`}
                    >
                      {format.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 全屏控制 */}
        <button
          onClick={onFullscreen}
          disabled={disabled}
          className={getButtonStyles()}
          title={getTooltipText('fullscreen')}
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"
            />
          </svg>
        </button>
      </div>

      {/* 快捷键提示 */}
      <div className="mt-2 text-xs text-gray-500">
        快捷键: <span className="font-mono bg-gray-100 px-1 rounded">+/-</span>{' '}
        缩放
        <span className="mx-1">•</span>
        <span className="font-mono bg-gray-100 px-1 rounded">R</span> 重置
        <span className="mx-1">•</span>
        <span className="font-mono bg-gray-100 px-1 rounded">C</span> 十字线
        <span className="mx-1">•</span>
        <span className="font-mono bg-gray-100 px-1 rounded">G</span> 网格
      </div>
    </div>
  );
};

export default KlineChartControls;
