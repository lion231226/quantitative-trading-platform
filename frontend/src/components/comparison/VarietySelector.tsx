'use client';

import { useEffect, useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Loading } from '@/components/ui/loading';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { marketDataAPI } from '@/lib/api';
import { Symbol } from '@/types/api';
import { cn } from '@/lib/utils';

interface VarietySelectorProps {
  onVarietiesSelect: (varieties: string[]) => void;
  selectedVarieties?: string[];
  maxSelection?: number;
  className?: string;
}

export function VarietySelector({
  onVarietiesSelect,
  selectedVarieties = [],
  maxSelection = 10,
  className,
}: VarietySelectorProps) {
  const [symbols, setSymbols] = useState<Symbol[]>([]);
  const [sectors, setSectors] = useState<string[]>([]);
  const [selectedSector, setSelectedSector] = useState<string>('全部');
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    loadSymbols();
  }, []);

  const loadSymbols = async () => {
    try {
      setLoading(true);
      const data = await marketDataAPI.getSymbols();
      setSymbols(data);

      // 提取所有版块
      const uniqueSectors = Array.from(new Set(data.map((s) => s.sector)));
      setSectors(['全部', ...uniqueSectors]);

      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载期货品种失败');
      console.error('Failed to load symbols:', err);
    } finally {
      setLoading(false);
    }
  };

  // 过滤逻辑：版块筛选 + 搜索筛选
  const filteredSymbols = useMemo(() => {
    let filtered = symbols;

    // 版块筛选
    if (selectedSector !== '全部') {
      filtered = filtered.filter((s) => s.sector === selectedSector);
    }

    // 搜索筛选
    if (searchTerm.trim()) {
      const searchLower = searchTerm.toLowerCase();
      filtered = filtered.filter(
        (s) =>
          s.symbol.toLowerCase().includes(searchLower) ||
          s.name.toLowerCase().includes(searchLower) ||
          s.exchange.toLowerCase().includes(searchLower),
      );
    }

    return filtered;
  }, [symbols, selectedSector, searchTerm]);

  // 版块颜色映射
  const sectorColors: Record<string, string> = {
    能源: 'bg-blue-100 text-blue-800 border-blue-200',
    金属: 'bg-gray-100 text-gray-800 border-gray-200',
    农产品: 'bg-green-100 text-green-800 border-green-200',
    化工: 'bg-purple-100 text-purple-800 border-purple-200',
    其他: 'bg-orange-100 text-orange-800 border-orange-200',
  };

  const getSectorColor = (sector: string) => {
    return sectorColors[sector] || sectorColors['其他'];
  };

  // 处理品种选择/取消选择
  const handleVarietyToggle = (symbol: string) => {
    const isSelected = selectedVarieties.includes(symbol);

    if (isSelected) {
      // 取消选择
      const newSelection = selectedVarieties.filter((v) => v !== symbol);
      onVarietiesSelect(newSelection);
    } else {
      // 检查是否达到最大选择数量
      if (selectedVarieties.length >= maxSelection) {
        return; // 可以添加用户提示
      }
      // 添加选择
      const newSelection = [...selectedVarieties, symbol];
      onVarietiesSelect(newSelection);
    }
  };

  // 快速选择功能
  const handleQuickSelect = (sector: string) => {
    if (sector === '全部') {
      const allSymbols = symbols.map((s) => s.symbol).slice(0, maxSelection);
      onVarietiesSelect(allSymbols);
    } else {
      const sectorSymbols = symbols
        .filter((s) => s.sector === sector)
        .map((s) => s.symbol)
        .slice(0, maxSelection);
      onVarietiesSelect(sectorSymbols);
    }
  };

  // 清空选择
  const handleClearSelection = () => {
    onVarietiesSelect([]);
  };

  // 获取品种信息
  const getSymbolInfo = (symbol: string) => {
    return symbols.find((s) => s.symbol === symbol);
  };

  if (loading) {
    return (
      <Card className={cn('', className)}>
        <CardHeader>
          <CardTitle>多品种选择</CardTitle>
          <CardDescription>
            选择要对比分析的期货品种（最多{maxSelection}个）
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loading text="加载期货品种..." />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={cn('', className)}>
        <CardHeader>
          <CardTitle>多品种选择</CardTitle>
          <CardDescription>
            选择要对比分析的期货品种（最多{maxSelection}个）
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <div className="text-red-600 mb-4">{error}</div>
            <Button onClick={loadSymbols} variant="outline">
              重新加载
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn('', className)}>
      <CardHeader>
        <CardTitle>多品种选择</CardTitle>
        <CardDescription>
          选择要对比分析的期货品种（已选择 {selectedVarieties.length}/
          {maxSelection} 个）
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 已选择的品种展示 */}
        {selectedVarieties.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">已选择的品种：</span>
              <Button
                onClick={handleClearSelection}
                variant="outline"
                size="sm"
              >
                清空选择
              </Button>
            </div>
            <div className="flex flex-wrap gap-2">
              {selectedVarieties.map((symbol) => {
                const info = getSymbolInfo(symbol);
                return (
                  <Badge
                    key={symbol}
                    variant="secondary"
                    className="cursor-pointer hover:bg-red-100 hover:text-red-800"
                    onClick={() => handleVarietyToggle(symbol)}
                  >
                    {symbol}
                    <span className="ml-1 text-xs">×</span>
                  </Badge>
                );
              })}
            </div>
          </div>
        )}

        {/* 搜索框 */}
        <div>
          <Input
            placeholder="搜索期货品种代码或名称..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full"
          />
        </div>

        {/* 版块筛选和快速选择 */}
        <div className="space-y-2">
          <div className="text-sm font-medium">版块筛选：</div>
          <div className="flex flex-wrap gap-2">
            {sectors.map((sector) => (
              <div key={sector} className="flex gap-1">
                <Button
                  variant={selectedSector === sector ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSelectedSector(sector)}
                >
                  {sector}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleQuickSelect(sector)}
                  title={`快速选择${sector}品种`}
                >
                  +
                </Button>
              </div>
            ))}
          </div>
        </div>

        {/* 期货品种列表 */}
        <div className="space-y-2">
          <div className="text-sm font-medium">
            可选品种（{filteredSymbols.length}个）：
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 max-h-80 overflow-y-auto custom-scrollbar">
            {filteredSymbols.map((symbol) => {
              const isSelected = selectedVarieties.includes(symbol.symbol);
              const isDisabled =
                !isSelected && selectedVarieties.length >= maxSelection;

              return (
                <Button
                  key={symbol.symbol}
                  variant={isSelected ? 'default' : 'outline'}
                  className={cn(
                    'justify-start h-auto p-3 text-left relative',
                    isDisabled && 'opacity-50 cursor-not-allowed',
                  )}
                  onClick={() =>
                    !isDisabled && handleVarietyToggle(symbol.symbol)
                  }
                  disabled={isDisabled}
                >
                  <div className="w-full">
                    <div className="flex items-center justify-between">
                      <div className="font-medium">{symbol.symbol}</div>
                      {isSelected && (
                        <div className="text-xs bg-primary text-primary-foreground px-1 rounded">
                          ✓
                        </div>
                      )}
                    </div>
                    <div className="text-xs opacity-70">{symbol.name}</div>
                    <div className="flex items-center justify-between mt-1">
                      <Badge
                        variant="outline"
                        className={cn('text-xs', getSectorColor(symbol.sector))}
                      >
                        {symbol.sector}
                      </Badge>
                      <div className="text-xs opacity-50">
                        {symbol.exchange}
                      </div>
                    </div>
                  </div>
                </Button>
              );
            })}
          </div>

          {filteredSymbols.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              {searchTerm ? '未找到匹配的期货品种' : '该版块暂无期货品种'}
            </div>
          )}
        </div>

        {/* 选择提示 */}
        {selectedVarieties.length === 0 && (
          <div className="text-center py-4 text-muted-foreground text-sm">
            请选择至少1个期货品种进行对比分析
          </div>
        )}
      </CardContent>
    </Card>
  );
}
