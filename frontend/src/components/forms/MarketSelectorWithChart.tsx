'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Loading } from '@/components/ui/loading';
import { marketDataAPI } from '@/lib/api';
import { Symbol } from '@/types/api';
import { cn } from '@/lib/utils';
import CandlestickChart from '@/components/charts/CandlestickChart';
import { TimePeriod } from '@/types/kline.types';

interface MarketSelectorWithChartProps {
  onSymbolSelect: (symbol: string) => void;
  selectedSymbol?: string;
  className?: string;
}

interface MockKlineData {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

// 生成模拟K线数据
const generateMockKlineData = (symbol: string): MockKlineData[] => {
  const data: MockKlineData[] = [];
  const now = Date.now();
  let basePrice = 4000; // 基础价格

  // 根据品种调整基础价格
  if (symbol.includes('IF')) basePrice = 4200;
  else if (symbol.includes('IC')) basePrice = 6500;
  else if (symbol.includes('IH')) basePrice = 2800;

  for (let i = 59; i >= 0; i--) {
    const timestamp = now - i * 24 * 60 * 60 * 1000; // 每日数据
    const priceChange = (Math.random() - 0.5) * basePrice * 0.03; // ±3%变化
    const open = basePrice + priceChange;
    const close = open + (Math.random() - 0.5) * basePrice * 0.02;
    const high = Math.max(open, close) + Math.random() * basePrice * 0.01;
    const low = Math.min(open, close) - Math.random() * basePrice * 0.01;
    const volume = Math.floor(Math.random() * 100000) + 50000;

    data.push({
      timestamp,
      open,
      high,
      low,
      close,
      volume,
    });

    basePrice = close; // 下一期基于本期收盘价
  }

  return data;
};

export function MarketSelectorWithChart({
  onSymbolSelect,
  selectedSymbol,
  className,
}: MarketSelectorWithChartProps) {
  const [symbols, setSymbols] = useState<Symbol[]>([]);
  const [sectors, setSectors] = useState<string[]>([]);
  const [selectedSector, setSelectedSector] = useState<string>('全部');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [chartData, setChartData] = useState<MockKlineData[]>([]);
  const [showChart, setShowChart] = useState(false);

  // 英文板块名称到中文的映射
  const sectorNameMap: Record<string, string> = {
    index: '股指',
    energy: '能源',
    metal: '金属',
    agriculture: '农产品',
    chemical: '化工',
  };

  useEffect(() => {
    loadSymbols();
  }, []);

  useEffect(() => {
    if (selectedSymbol) {
      const data = generateMockKlineData(selectedSymbol);
      setChartData(data);
      setShowChart(true);
    } else {
      setShowChart(false);
    }
  }, [selectedSymbol]);

  const loadSymbols = async () => {
    try {
      setLoading(true);
      setError('');
      console.log('开始加载期货品种...');

      const data = await marketDataAPI.getSymbols();
      console.log('成功获取期货品种数据:', data);

      setSymbols(data);

      // 提取所有版块并转换为中文
      const uniqueSectors = Array.from(new Set(data.map((s) => s.sector)));
      console.log('提取的版块:', uniqueSectors);

      // 确保所有板块都有对应的中文映射
      const chineseSectors = uniqueSectors.map(
        (sector) =>
          sectorNameMap[sector as keyof typeof sectorNameMap] || sector,
      );
      console.log('中文版块:', chineseSectors);

      setSectors(['全部', ...chineseSectors]);
      console.log('期货品种加载成功，总数:', data.length);
    } catch (err) {
      console.error('加载期货品种失败:', err);
      const errorMessage =
        err instanceof Error ? err.message : '加载期货品种失败';
      setError(errorMessage);

      // 添加更详细的错误信息
      if (err instanceof Error) {
        console.error('错误详情:', {
          name: err.name,
          message: err.message,
          stack: err.stack,
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredSymbols =
    selectedSector === '全部'
      ? symbols
      : symbols.filter((s) => {
          // 找到中文显示对应的英文名称
          const englishSector = Object.keys(sectorNameMap).find(
            (key) => sectorNameMap[key] === selectedSector,
          );
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
    <div className={cn('space-y-6', className)}>
      <Card>
        <CardHeader>
          <CardTitle>期货品种选择</CardTitle>
          <CardDescription>请选择要分析的期货品种</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* 版块筛选 */}
          <div className="flex flex-wrap gap-2">
            {sectors.map((sector) => (
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
            {filteredSymbols.map((symbol) => (
              <Button
                key={symbol.symbol}
                variant={
                  selectedSymbol === symbol.symbol ? 'default' : 'outline'
                }
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

      {/* K线图展示 */}
      {showChart && selectedSymbol && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>{selectedSymbol} K线图</span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowChart(!showChart)}
              >
                {showChart ? '隐藏' : '显示'}图表
              </Button>
            </CardTitle>
            <CardDescription>近60个交易日价格走势（模拟数据）</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-80">
              <CandlestickChart
                data={chartData}
                config={{
                  height: 320,
                  showVolume: true,
                  showGrid: true,
                  showCrosshair: true,
                  colors: {
                    bullish: '#26a69a',
                    bearish: '#ef5350',
                    volume: '#9e9e9e',
                    grid: '#e0e0e0',
                    text: '#424242',
                    background: '#ffffff',
                    crosshair: '#757575',
                  },
                }}
                height={320}
              />
            </div>
            <div className="mt-4 text-xs text-gray-500 text-center">
              * 此为模拟演示数据，实际数据需要连接真实行情API
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
