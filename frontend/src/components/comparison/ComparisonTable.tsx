'use client';

import { useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { PerformanceMetrics, VarietyResult } from '@/types/comparison.types';
import { cn } from '@/lib/utils';
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  Download,
  Filter,
} from 'lucide-react';

interface ComparisonTableProps {
  results: VarietyResult[];
  sortable?: boolean;
  filterable?: boolean;
  exportable?: boolean;
  className?: string;
}

type SortField = keyof PerformanceMetrics | 'symbol' | 'sector';
type SortDirection = 'asc' | 'desc';

interface ColumnConfig {
  key: SortField;
  label: string;
  formatter: (value: any, result: VarietyResult) => React.ReactNode;
  className?: string;
  sortable: boolean;
}

export function ComparisonTable({
  results,
  sortable = true,
  filterable = true,
  exportable = true,
  className,
}: ComparisonTableProps) {
  const [sortField, setSortField] = useState<SortField>('totalReturn');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [filterTerm, setFilterTerm] = useState('');
  const [selectedSector, setSelectedSector] = useState<string>('全部');

  // 获取所有版块
  const sectors = useMemo(() => {
    const uniqueSectors = Array.from(new Set(results.map((r) => r.sector)));
    return ['全部', ...uniqueSectors];
  }, [results]);

  // 过滤数据
  const filteredResults = useMemo(() => {
    let filtered = results;

    // 搜索过滤
    if (filterTerm.trim()) {
      const searchLower = filterTerm.toLowerCase();
      filtered = filtered.filter(
        (r) =>
          r.symbol.toLowerCase().includes(searchLower) ||
          r.name.toLowerCase().includes(searchLower) ||
          r.sector.toLowerCase().includes(searchLower),
      );
    }

    // 版块过滤
    if (selectedSector !== '全部') {
      filtered = filtered.filter((r) => r.sector === selectedSector);
    }

    return filtered;
  }, [results, filterTerm, selectedSector]);

  // 排序数据
  const sortedResults = useMemo(() => {
    if (!sortable) return filteredResults;

    return [...filteredResults].sort((a, b) => {
      let aValue: number | string;
      let bValue: number | string;

      if (sortField === 'symbol') {
        aValue = a.symbol;
        bValue = b.symbol;
      } else if (sortField === 'sector') {
        aValue = a.sector;
        bValue = b.sector;
      } else {
        aValue = a.metrics[sortField] as number;
        bValue = b.metrics[sortField] as number;
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      return sortDirection === 'asc'
        ? (aValue as number) - (bValue as number)
        : (bValue as number) - (aValue as number);
    });
  }, [filteredResults, sortField, sortDirection, sortable]);

  // 处理排序
  const handleSort = (field: SortField) => {
    if (!sortable) return;

    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  // 导出功能
  const handleExport = (format: 'csv' | 'excel') => {
    const headers = columns.map((col) => col.label).join(',');
    const rows = sortedResults
      .map((result) =>
        columns
          .map((col) => {
            if (col.key === 'symbol') return result.symbol;
            if (col.key === 'sector') return result.sector;
            return result.metrics[col.key as keyof PerformanceMetrics];
          })
          .join(','),
      )
      .join('\n');

    const csvContent = `${headers}\n${rows}`;
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `comparison_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  // 表格列配置
  const columns: ColumnConfig[] = [
    {
      key: 'symbol',
      label: '品种',
      formatter: (_, result) => (
        <div>
          <div className="font-medium">{result.symbol}</div>
          <div className="text-sm text-muted-foreground">{result.name}</div>
        </div>
      ),
      sortable: true,
    },
    {
      key: 'sector',
      label: '版块',
      formatter: (sector) => (
        <Badge variant="outline" className="text-xs">
          {sector}
        </Badge>
      ),
      sortable: true,
    },
    {
      key: 'totalReturn',
      label: '总收益率',
      formatter: (value) => (
        <span
          className={cn(
            'font-medium',
            value > 0
              ? 'text-green-600'
              : value < 0
                ? 'text-red-600'
                : 'text-gray-600',
          )}
        >
          {(value * 100).toFixed(2)}%
        </span>
      ),
      sortable: true,
    },
    {
      key: 'sharpeRatio',
      label: '夏普比率',
      formatter: (value) => (
        <span
          className={cn(
            'font-medium',
            value > 1
              ? 'text-green-600'
              : value > 0.5
                ? 'text-yellow-600'
                : 'text-red-600',
          )}
        >
          {value.toFixed(2)}
        </span>
      ),
      sortable: true,
    },
    {
      key: 'maxDrawdown',
      label: '最大回撤',
      formatter: (value) => (
        <span className="font-medium text-red-600">
          {(value * 100).toFixed(2)}%
        </span>
      ),
      sortable: true,
    },
    {
      key: 'volatility',
      label: '波动率',
      formatter: (value) => (
        <span className="font-medium">{(value * 100).toFixed(2)}%</span>
      ),
      sortable: true,
    },
    {
      key: 'winRate',
      label: '胜率',
      formatter: (value) => (
        <span
          className={cn(
            'font-medium',
            value > 0.6
              ? 'text-green-600'
              : value > 0.4
                ? 'text-yellow-600'
                : 'text-red-600',
          )}
        >
          {(value * 100).toFixed(1)}%
        </span>
      ),
      sortable: true,
    },
    {
      key: 'totalTrades',
      label: '交易次数',
      formatter: (value) => (
        <span className="font-medium">{value.toFixed(0)}</span>
      ),
      sortable: true,
    },
    {
      key: 'profitFactor',
      label: '盈亏比',
      formatter: (value) => (
        <span
          className={cn(
            'font-medium',
            value > 2
              ? 'text-green-600'
              : value > 1.5
                ? 'text-yellow-600'
                : 'text-red-600',
          )}
        >
          {value.toFixed(2)}
        </span>
      ),
      sortable: true,
    },
  ];

  // 获取排序图标
  const getSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return <ArrowUpDown className="h-4 w-4 text-muted-foreground" />;
    }
    return sortDirection === 'asc' ? (
      <ArrowUp className="h-4 w-4 text-primary" />
    ) : (
      <ArrowDown className="h-4 w-4 text-primary" />
    );
  };

  return (
    <Card className={cn('', className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>详细对比数据</CardTitle>
          {exportable && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm">
                  <Download className="h-4 w-4 mr-2" />
                  导出
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem onClick={() => handleExport('csv')}>
                  导出为 CSV
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleExport('excel')}>
                  导出为 Excel
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 过滤控件 */}
        {filterable && (
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <Input
                placeholder="搜索品种代码、名称或版块..."
                value={filterTerm}
                onChange={(e) => setFilterTerm(e.target.value)}
                className="w-full"
              />
            </div>
            <div className="flex gap-2">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline">
                    <Filter className="h-4 w-4 mr-2" />
                    {selectedSector}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  {sectors.map((sector) => (
                    <DropdownMenuItem
                      key={sector}
                      onClick={() => setSelectedSector(sector)}
                    >
                      {sector}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        )}

        {/* 数据统计 */}
        <div className="text-sm text-muted-foreground">
          显示 {sortedResults.length} / {results.length} 个品种
          {filterTerm && ` (搜索: "${filterTerm}")`}
          {selectedSector !== '全部' && ` (版块: ${selectedSector})`}
        </div>

        {/* 表格 */}
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b">
                {columns.map((column) => (
                  <th
                    key={column.key}
                    className={cn(
                      'text-left p-3 font-medium text-sm',
                      column.sortable &&
                        sortable &&
                        'cursor-pointer hover:bg-muted/50',
                      column.className,
                    )}
                    onClick={() => column.sortable && handleSort(column.key)}
                  >
                    <div className="flex items-center space-x-2">
                      <span>{column.label}</span>
                      {column.sortable && sortable && getSortIcon(column.key)}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sortedResults.map((result, index) => (
                <tr
                  key={result.symbol}
                  className={cn(
                    'border-b hover:bg-muted/30',
                    index % 2 === 0 && 'bg-muted/10',
                  )}
                >
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className={cn('p-3 text-sm', column.className)}
                    >
                      {column.formatter(
                        column.key === 'symbol'
                          ? result.symbol
                          : column.key === 'sector'
                            ? result.sector
                            : result.metrics[
                                column.key as keyof PerformanceMetrics
                              ],
                        result,
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* 空状态 */}
        {sortedResults.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            {filterTerm || selectedSector !== '全部'
              ? '没有找到匹配的品种'
              : '暂无数据'}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
