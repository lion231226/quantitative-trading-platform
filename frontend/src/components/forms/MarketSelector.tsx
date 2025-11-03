'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Loading } from '@/components/ui/loading';
import { marketDataAPI } from '@/lib/api';
import { Symbol } from '@/types/api';
import { cn } from '@/lib/utils';

interface MarketSelectorProps {
  onSymbolSelect: (symbol: string) => void
  selectedSymbol?: string
  className?: string
}

export function MarketSelector({ onSymbolSelect, selectedSymbol, className }: MarketSelectorProps) {
  const [symbols, setSymbols] = useState<Symbol[]>([]);
  const [sectors, setSectors] = useState<string[]>([]);
  const [selectedSector, setSelectedSector] = useState<string>('全部');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  // 英文板块名称到中文的映射
  const sectorNameMap: Record<string, string> = {
    'energy': '能源',
    'metal': '金属',
    'agriculture': '农产品',
    'chemical': '化工'
  };

  useEffect(() => {
    loadSymbols();
  }, []);

  const loadSymbols = async () => {
    try {
      setLoading(true);
      setError('');
      console.log('开始加载期货品种...');

      const data = await marketDataAPI.getSymbols();
      console.log('成功获取期货品种数据:', data);

      setSymbols(data);

      // 提取所有版块并转换为中文
      const uniqueSectors = Array.from(new Set(data.map(s => s.sector)));
      console.log('提取的版块:', uniqueSectors);

      // 确保所有板块都有对应的中文映射
      const chineseSectors = uniqueSectors.map(sector => sectorNameMap[sector as keyof typeof sectorNameMap] || sector);
      console.log('中文版块:', chineseSectors);

      setSectors(['全部', ...chineseSectors]);
      console.log('期货品种加载成功，总数:', data.length);

    } catch (err) {
      console.error('加载期货品种失败:', err);
      const errorMessage = err instanceof Error ? err.message : '加载期货品种失败';
      setError(errorMessage);

      // 添加更详细的错误信息
      if (err instanceof Error) {
        console.error('错误详情:', {
          name: err.name,
          message: err.message,
          stack: err.stack
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredSymbols = selectedSector === '全部'
    ? symbols
    : symbols.filter(s => {
        // 找到中文显示对应的英文名称
        const englishSector = Object.keys(sectorNameMap).find(key => sectorNameMap[key] === selectedSector);
        return englishSector && s.sector === englishSector;
      });

  const handleSymbolSelect = (symbol: string) => {
    onSymbolSelect(symbol);
  };

  if (loading) {
    return (
      <Card className={cn('', className)}>
        <CardHeader>
          <CardTitle>期货品种选择</CardTitle>
          <CardDescription>请选择要分析的期货品种</CardDescription>
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
          <CardTitle>期货品种选择</CardTitle>
          <CardDescription>请选择要分析的期货品种</CardDescription>
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
        <CardTitle>期货品种选择</CardTitle>
        <CardDescription>请选择要分析的期货品种</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 版块筛选 */}
        <div className="flex flex-wrap gap-2">
          {sectors.map(sector => (
            <Button
              key={sector}
              variant={selectedSector === sector ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedSector(sector)}
            >
              {sector}
            </Button>
          ))}
        </div>

        {/* 期货品种列表 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 max-h-60 overflow-y-auto custom-scrollbar">
          {filteredSymbols.map(symbol => (
            <Button
              key={symbol.symbol}
              variant={selectedSymbol === symbol.symbol ? 'default' : 'outline'}
              className="justify-start h-auto p-3 text-left"
              onClick={() => handleSymbolSelect(symbol.symbol)}
            >
              <div className="w-full">
                <div className="font-medium">{symbol.symbol}</div>
                <div className="text-xs opacity-70">{symbol.name}</div>
                <div className="text-xs opacity-50">{symbol.exchange}</div>
              </div>
            </Button>
          ))}
        </div>

        {filteredSymbols.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            该版块暂无期货品种
          </div>
        )}
      </CardContent>
    </Card>
  );
}
