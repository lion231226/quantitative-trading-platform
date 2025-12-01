/**
 * 可访问的图表容器组件
 * 为Chart.js图表提供ARIA支持、键盘导航和数据表替代方案
 */

import React, { useRef, useEffect, useState, ReactNode } from 'react';
import { createAriaProps, ARIA_PATTERNS } from '@/utils/accessibility/aria-utils';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { KeyboardNavigationIndicator } from '@/components/ui/keyboard-navigation-indicator';
import { ScreenReaderAnnouncer } from '@/components/ui/screen-reader-announcer';
import { Download, Eye, EyeOff, Keyboard, Table } from 'lucide-react';

export interface AccessibleChartContainerProps {
  /** 图表标题 */
  title: string;
  /** 图表描述 */
  description: string;
  /** Chart.js图表组件 */
  children: ReactNode;
  /** 数据表组件（用于屏幕阅读器替代方案） */
  dataTable?: ReactNode;
  /** 图表数据摘要 */
  dataSummary?: {
    totalPoints?: number;
    dateRange?: string;
    keyMetrics?: Record<string, string>;
  };
  /** 是否显示键盘导航指示器 */
  showKeyboardIndicator?: boolean;
  /** 自定义样式类名 */
  className?: string;
}

/**
 * 可访问的图表容器
 */
export const AccessibleChartContainer: React.FC<AccessibleChartContainerProps> = ({
  title,
  description,
  children,
  dataTable,
  dataSummary,
  showKeyboardIndicator = true,
  className = '',
}) => {
  const [showDataTable, setShowDataTable] = useState(false);
  const [currentDataPoint, setCurrentDataPoint] = useState<string>('');
  const chartRef = useRef<HTMLDivElement>(null);

  // 生成唯一ID
  const chartId = `chart-${title.toLowerCase().replace(/\s+/g, '-')}`;
  const descriptionId = `${chartId}-description`;
  const tableId = `${chartId}-table`;
  const summaryId = `${chartId}-summary`;

  // 处理图表数据点导航
  const handleDataPointFocus = useCallback((dataPointInfo: string) => {
    setCurrentDataPoint(dataPointInfo);
  }, []);

  // 处理键盘导航
  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    if (!chartRef.current) return;

    const focusableElements = chartRef.current.querySelectorAll(
      'button, [tabindex]:not([tabindex="-1"])'
    ) as NodeListOf<HTMLElement>;

    const currentIndex = Array.from(focusableElements).indexOf(
      document.activeElement as HTMLElement
    );

    switch (event.key) {
      case 'ArrowRight':
      case 'ArrowDown':
        event.preventDefault();
        if (currentIndex < focusableElements.length - 1) {
          focusableElements[currentIndex + 1].focus();
        }
        break;

      case 'ArrowLeft':
      case 'ArrowUp':
        event.preventDefault();
        if (currentIndex > 0) {
          focusableElements[currentIndex - 1].focus();
        }
        break;

      case 'Home':
        event.preventDefault();
        if (focusableElements.length > 0) {
          focusableElements[0].focus();
        }
        break;

      case 'End':
        event.preventDefault();
        if (focusableElements.length > 0) {
          focusableElements[focusableElements.length - 1].focus();
        }
        break;
    }
  }, []);

  return (
    <div className={`accessible-chart-container ${className}`}>
      {/* 图表容器 */}
      <Card>
        <CardHeader>
          <CardTitle id={chartId} className="flex items-center space-x-2">
            <span>{title}</span>
            {showKeyboardIndicator && <KeyboardNavigationIndicator />}
          </CardTitle>
          <div id={descriptionId} className="text-sm text-muted-foreground">
            {description}
          </div>
        </CardHeader>

        <CardContent>
          {/* 控制按钮 */}
          <div className="flex items-center space-x-2 mb-4" role="toolbar" aria-label="图表控制">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowDataTable(!showDataTable)}
              aria-expanded={showDataTable}
              aria-controls={tableId}
              className="flex items-center space-x-1"
            >
              {showDataTable ? (
                <Eye className="h-4 w-4" />
              ) : (
                <EyeOff className="h-4 w-4" />
              )}
              <span>{showDataTable ? '隐藏数据表' : '显示数据表'}</span>
            </Button>

            {dataTable && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowDataTable(true)}
                aria-controls={tableId}
                className="flex items-center space-x-1"
              >
                <Table className="h-4 w-4" />
                <span>查看数据表</span>
              </Button>
            )}
          </div>

          {/* 主要图表区域 */}
          <div
            ref={chartRef}
            role="application"
            aria-label={`${title} - 交互式图表`}
            aria-describedby={`${descriptionId} ${summaryId}`}
            tabIndex={0}
            onKeyDown={handleKeyDown}
            className="chart-wrapper"
            {...createAriaProps().label(`${title} - 交互式图表`).build()}
          >
            {/* Chart.js Canvas元素 */}
            <div
              role="img"
              aria-label={`${title}图表`}
              aria-describedby={`${descriptionId} ${summaryId}`}
              className="relative"
            >
              {children}
            </div>

            {/* 数据摘要（屏幕阅读器可访问） */}
            <div id={summaryId} className="sr-only">
              {dataSummary && (
                <div>
                  <h4>数据摘要</h4>
                  {dataSummary.totalPoints && (
                    <p>总共{dataSummary.totalPoints}个数据点</p>
                  )}
                  {dataSummary.dateRange && (
                    <p>时间范围：{dataSummary.dateRange}</p>
                  )}
                  {dataSummary.keyMetrics && (
                    <div>
                      <h5>关键指标：</h5>
                      <ul>
                        {Object.entries(dataSummary.keyMetrics).map(([key, value]) => (
                          <li key={key}>
                            {key}: {value}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* 数据表（可访问的替代方案） */}
          {dataTable && (
            <div
              id={tableId}
              role="tabpanel"
              aria-labelledby={`${chartId}-table-button`}
              hidden={!showDataTable}
              className={showDataTable ? 'mt-4' : 'sr-only'}
            >
              <div className="border rounded-lg p-4 bg-gray-50 dark:bg-gray-900">
                <h4 className="text-lg font-semibold mb-4">数据表</h4>
                <div className="text-sm text-muted-foreground mb-4">
                  此表格提供了图表中所有数据的详细视图，适用于屏幕阅读器用户。
                </div>
                {dataTable}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 屏幕阅读器通知 */}
      <ScreenReaderAnnouncer
        message={showDataTable ? '数据表已显示' : '数据表已隐藏'}
        politeness="polite"
      />

      {/* 当前数据点通知 */}
      {currentDataPoint && (
        <ScreenReaderAnnouncer
          message={currentDataPoint}
          politeness="polite"
        />
      )}
    </div>
  );
};

/**
 * 可访问图表数据点组件
 */
export interface AccessibleDataPointProps {
  /** 数据点标签 */
  label: string;
  /** 数据点值 */
  value: number | string;
  /** 数据点描述 */
  description?: string;
  /** 是否选中 */
  selected?: boolean;
  /** 位置信息 */
  position?: number;
  /** 总数 */
  total?: number;
  /** 点击回调 */
  onClick?: () => void;
  /** 键盘事件回调 */
  onKeyDown?: (event: React.KeyboardEvent) => void;
}

/**
 * 可访问的数据点组件
 */
export const AccessibleDataPoint: React.FC<AccessibleDataPointProps> = ({
  label,
  value,
  description,
  selected = false,
  position,
  total,
  onClick,
  onKeyDown,
}) => {
  return (
    <button
      type="button"
      role="button"
      aria-pressed={selected}
      aria-label={`${label}: ${value}${description ? ` - ${description}` : ''}`}
      aria-posinset={position}
      aria-setsize={total}
      className="accessible-data-point"
      onClick={onClick}
      onKeyDown={onKeyDown}
    >
      <span className="sr-only">{label}: {value}</span>
      <span aria-hidden="true">{value}</span>
    </button>
  );
};

/**
 * 图表键盘导航提供者
 */
export interface ChartKeyboardNavProviderProps {
  children: ReactNode;
  /** 数据点数组 */
  dataPoints: Array<{
    id: string;
    label: string;
    value: number;
    description?: string;
  }>;
  /** 数据点变化回调 */
  onDataPointChange?: (dataPoint: any) => void;
}

/**
 * 图表键盘导航上下文
 */
export const ChartKeyboardNavProvider: React.FC<ChartKeyboardNavProviderProps> = ({
  children,
  dataPoints,
  onDataPointChange,
}) => {
  const [currentDataPointIndex, setCurrentDataPointIndex] = useState(0);

  const handleDataPointNavigation = useCallback((direction: 'next' | 'prev' | 'first' | 'last') => {
    let newIndex = currentDataPointIndex;

    switch (direction) {
      case 'next':
        newIndex = (currentDataPointIndex + 1) % dataPoints.length;
        break;
      case 'prev':
        newIndex = currentDataPointIndex === 0 ? dataPoints.length - 1 : currentDataPointIndex - 1;
        break;
      case 'first':
        newIndex = 0;
        break;
      case 'last':
        newIndex = dataPoints.length - 1;
        break;
    }

    setCurrentDataPointIndex(newIndex);
    if (onDataPointChange) {
      onDataPointChange(dataPoints[newIndex]);
    }
  }, [currentDataPointIndex, dataPoints, onDataPointChange]);

  return (
    <div className="chart-keyboard-nav-provider">
      {React.Children.map(children, child => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child as React.ReactElement<any>, {
            chartKeyboardNav: {
              currentDataPoint: dataPoints[currentDataPointIndex],
              navigate: handleDataPointNavigation,
              currentIndex: currentDataPointIndex,
            },
          });
        }
        return child;
      })}
    </div>
  );
};

export default AccessibleChartContainer;