'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { cn, formatDate } from '@/lib/utils';

interface DateRangePickerProps {
  onDateRangeChange: (startDate: string, endDate: string) => void;
  startDate?: string;
  endDate?: string;
  className?: string;
}

// 快速日期范围选项
const quickRanges = [
  { label: '最近7天', days: 7 },
  { label: '最近30天', days: 30 },
  { label: '最近90天', days: 90 },
  { label: '最近180天', days: 180 },
  { label: '最近一年', days: 365 },
];

export function DateRangePicker({
  onDateRangeChange,
  startDate,
  endDate,
  className,
}: DateRangePickerProps) {
  const [internalStartDate, setInternalStartDate] = useState(startDate || '');
  const [internalEndDate, setInternalEndDate] = useState(endDate || '');

  const handleStartDateChange = (date: string) => {
    setInternalStartDate(date);
    if (internalEndDate) {
      onDateRangeChange(date, internalEndDate);
    }
  };

  const handleEndDateChange = (date: string) => {
    setInternalEndDate(date);
    if (internalStartDate) {
      onDateRangeChange(internalStartDate, date);
    }
  };

  const handleQuickRange = (days: number) => {
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - days);

    const startDateStr = start.toISOString().split('T')[0];
    const endDateStr = end.toISOString().split('T')[0];

    setInternalStartDate(startDateStr);
    setInternalEndDate(endDateStr);
    onDateRangeChange(startDateStr, endDateStr);
  };

  const handleQuickRangeChange = (days: number) => {
    handleQuickRange(days);
  };

  return (
    <Card className={cn('', className)}>
      <CardHeader>
        <CardTitle>日期范围选择</CardTitle>
        <CardDescription>选择数据分析的时间范围</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 快速选择 */}
        <div>
          <label className="text-sm font-medium mb-2 block">快速选择</label>
          <div className="flex flex-wrap gap-2">
            {quickRanges.map((range) => (
              <Button
                key={range.label}
                variant="outline"
                size="sm"
                onClick={() => handleQuickRangeChange(range.days)}
              >
                {range.label}
              </Button>
            ))}
          </div>
        </div>

        {/* 自定义日期选择 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium mb-2 block">开始日期</label>
            <input
              type="date"
              value={internalStartDate}
              onChange={(e) => handleStartDateChange(e.target.value)}
              max={internalEndDate || new Date().toISOString().split('T')[0]}
              className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
            />
          </div>
          <div>
            <label className="text-sm font-medium mb-2 block">结束日期</label>
            <input
              type="date"
              value={internalEndDate}
              onChange={(e) => handleEndDateChange(e.target.value)}
              min={internalStartDate}
              max={new Date().toISOString().split('T')[0]}
              className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
            />
          </div>
        </div>

        {/* 显示当前选择的日期范围 */}
        {internalStartDate && internalEndDate && (
          <div className="text-sm text-muted-foreground p-3 bg-muted rounded-md">
            已选择：{formatDate(internalStartDate)} 至{' '}
            {formatDate(internalEndDate)}
            <div className="text-xs mt-1">
              共{' '}
              {Math.ceil(
                (new Date(internalEndDate).getTime() -
                  new Date(internalStartDate).getTime()) /
                  (1000 * 60 * 60 * 24),
              )}{' '}
              天
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
