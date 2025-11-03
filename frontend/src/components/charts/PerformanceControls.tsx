'use client';

import React, { useState, useCallback } from 'react';
import { Calendar, Download, Filter, RefreshCw, Settings, TrendingUp } from 'lucide-react';
import { PerformanceControlsProps } from '@/types/performance.types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from '@/components/ui/dropdown-menu';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Calendar as CalendarComponent } from '@/components/ui/calendar';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { cn } from '@/lib/utils';

interface TimeRangeOption {
  label: string;
  value: string;
  days: number;
}

const TIME_RANGES: TimeRangeOption[] = [
  { label: '最近1个月', value: '1m', days: 30 },
  { label: '最近3个月', value: '3m', days: 90 },
  { label: '最近6个月', value: '6m', days: 180 },
  { label: '最近1年', value: '1y', days: 365 },
  { label: '最近3年', value: '3y', days: 1095 },
  { label: '全部历史', value: 'all', days: 0 },
];

const BENCHMARK_OPTIONS = [
  { id: '', label: '无基准' },
  { id: 'sh000001', label: '沪深300指数' },
  { id: 'sz399001', label: '深证成指' },
  { id: 'sz399006', label: '创业板指' },
];

export const PerformanceControls: React.FC<PerformanceControlsProps> = ({
  strategyId,
  onTimeRangeChange,
  onBenchmarkChange,
  onExport,
  className = '',
}) => {
  const [selectedTimeRange, setSelectedTimeRange] = useState<string>('1y');
  const [selectedBenchmark, setSelectedBenchmark] = useState<string>('');
  const [customStartDate, setCustomStartDate] = useState<Date | undefined>();
  const [customEndDate, setCustomEndDate] = useState<Date | undefined>();
  const [showCustomDateRange, setShowCustomDateRange] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  // 计算日期范围
  const getDateRange = useCallback(() => {
    if (showCustomDateRange && customStartDate && customEndDate) {
      return {
        startDate: format(customStartDate, 'yyyy-MM-dd'),
        endDate: format(customEndDate, 'yyyy-MM-dd'),
      };
    }

    const selectedRange = TIME_RANGES.find((r) => r.value === selectedTimeRange);
    if (!selectedRange || selectedRange.value === 'all') {
      return {
        startDate: undefined,
        endDate: undefined,
      };
    }

    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - selectedRange.days);

    return {
      startDate: format(startDate, 'yyyy-MM-dd'),
      endDate: format(endDate, 'yyyy-MM-dd'),
    };
  }, [selectedTimeRange, customStartDate, customEndDate, showCustomDateRange]);

  // 处理时间范围变化
  const handleTimeRangeChange = useCallback(
    (rangeValue: string) => {
      setSelectedTimeRange(rangeValue);
      if (rangeValue !== 'custom') {
        setShowCustomDateRange(false);
      }
      const dateRange = getDateRange();
      onTimeRangeChange?.(dateRange.startDate || '', dateRange.endDate || '');
    },
    [getDateRange, onTimeRangeChange]
  );

  // 处理基准变化
  const handleBenchmarkChange = useCallback(
    (benchmarkId: string) => {
      setSelectedBenchmark(benchmarkId);
      onBenchmarkChange?.(benchmarkId);
    },
    [onBenchmarkChange]
  );

  // 处理导出
  const handleExport = useCallback(
    async (format: 'pdf' | 'csv' | 'excel' | 'png') => {
      setIsExporting(true);
      try {
        await onExport?.(format);
      } catch (error) {
        console.error('Export failed:', error);
      } finally {
        setIsExporting(false);
      }
    },
    [onExport]
  );

  // 处理自定义日期范围
  const handleCustomDateRange = useCallback(() => {
    const dateRange = getDateRange();
    onTimeRangeChange?.(dateRange.startDate || '', dateRange.endDate || '');
  }, [getDateRange, onTimeRangeChange]);

  const dateRange = getDateRange();

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center text-lg">
          <Settings className="mr-2 h-5 w-5" />
          绩效控制面板
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 时间范围选择 */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
            <Calendar className="h-4 w-4" />
            <span>时间范围</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {TIME_RANGES.map((range) => (
              <Badge
                key={range.value}
                variant={selectedTimeRange === range.value ? 'default' : 'outline'}
                className="cursor-pointer"
                onClick={() => handleTimeRangeChange(range.value)}
              >
                {range.label}
              </Badge>
            ))}
            <Badge
              variant={showCustomDateRange ? 'default' : 'outline'}
              className="cursor-pointer"
              onClick={() => setShowCustomDateRange(!showCustomDateRange)}
            >
              自定义
            </Badge>
          </div>

          {/* 自定义日期范围 */}
          {showCustomDateRange && (
            <div className="flex items-center gap-2 mt-2">
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className={cn(
                      'w-[180px] justify-start text-left font-normal',
                      !customStartDate && 'text-muted-foreground'
                    )}
                  >
                    <Calendar className="mr-2 h-4 w-4" />
                    {customStartDate ? format(customStartDate, 'yyyy-MM-dd', { locale: zhCN }) : '开始日期'}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <CalendarComponent
                    mode="single"
                    selected={customStartDate}
                    onSelect={setCustomStartDate}
                  />
                </PopoverContent>
              </Popover>

              <span className="text-gray-500">至</span>

              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className={cn(
                      'w-[180px] justify-start text-left font-normal',
                      !customEndDate && 'text-muted-foreground'
                    )}
                  >
                    <Calendar className="mr-2 h-4 w-4" />
                    {customEndDate ? format(customEndDate, 'yyyy-MM-dd', { locale: zhCN }) : '结束日期'}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <CalendarComponent
                    mode="single"
                    selected={customEndDate}
                    onSelect={setCustomEndDate}
                  />
                </PopoverContent>
              </Popover>

              <Button
                size="sm"
                onClick={handleCustomDateRange}
                disabled={!customStartDate || !customEndDate}
              >
                应用
              </Button>
            </div>
          )}
        </div>

        {/* 当前选择的日期范围显示 */}
        {(dateRange.startDate || dateRange.endDate) && (
          <div className="flex items-center gap-2 p-2 bg-blue-50 rounded-md text-sm">
            <TrendingUp className="h-4 w-4 text-blue-600" />
            <span className="text-blue-700">
              {dateRange.startDate} 至 {dateRange.endDate}
            </span>
          </div>
        )}

        {/* 基准选择 */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
            <Filter className="h-4 w-4" />
            <span>基准指数</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {BENCHMARK_OPTIONS.map((benchmark) => (
              <Badge
                key={benchmark.id}
                variant={selectedBenchmark === benchmark.id ? 'default' : 'outline'}
                className="cursor-pointer"
                onClick={() => handleBenchmarkChange(benchmark.id)}
              >
                {benchmark.label}
              </Badge>
            ))}
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="flex items-center justify-between pt-4 border-t">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.location.reload()}
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              刷新
            </Button>
          </div>

          {/* 导出菜单 */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button size="sm" disabled={isExporting}>
                <Download className="mr-2 h-4 w-4" />
                {isExporting ? '导出中...' : '导出报告'}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>选择导出格式</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => handleExport('pdf')}>
                <Download className="mr-2 h-4 w-4" />
                PDF 报告
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleExport('excel')}>
                <Download className="mr-2 h-4 w-4" />
                Excel 表格
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleExport('csv')}>
                <Download className="mr-2 h-4 w-4" />
                CSV 数据
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleExport('png')}>
                <Download className="mr-2 h-4 w-4" />
                PNG 图片
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardContent>
    </Card>
  );
};

export default PerformanceControls;
