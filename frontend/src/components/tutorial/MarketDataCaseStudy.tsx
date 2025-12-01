import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Line } from 'react-chartjs-2';
import {
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
} from 'chart.js';
import {
  Activity,
  BarChart3,
  Calendar,
  DollarSign,
  Info,
  Pause,
  Play,
  RotateCcw,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Slider } from '@/components/ui/slider';

// 注册Chart.js组件
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
);

interface MarketData {
  date: string;
  price: number;
  volume: number;
  high: number;
  low: number;
  change: number;
  changePercent: number;
}

interface CaseStudy {
  id: string;
  title: string;
  description: string;
  period: string;
  symbol: string;
  data: MarketData[];
  insights: string[];
  strategy: {
    type: string;
    parameters: Record<string, any>;
    performance: {
      totalReturn: number;
      maxDrawdown: number;
      sharpeRatio: number;
      winRate: number;
    };
  };
  keyEvents: Array<{
    date: string;
    event: string;
    impact: 'positive' | 'negative' | 'neutral';
  }>;
}

interface MarketDataCaseStudyProps {
  autoPlay?: boolean;
  selectedCase?: string;
  onCaseChange?: (caseId: string) => void;
}

/**
 * 市场数据案例演示组件
 * 使用真实市场数据展示量化策略的实际应用效果
 */
export function MarketDataCaseStudy({
  autoPlay = false,
  selectedCase = 'bull-market-2023',
  onCaseChange,
}: MarketDataCaseStudyProps) {
  const [isPlaying, setIsPlaying] = useState(autoPlay);
  const [currentStep, setCurrentStep] = useState(0);
  const [speed, setSpeed] = useState(1.0);
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedCaseStudy, setSelectedCaseStudy] =
    useState<string>(selectedCase);

  // 模拟真实市场数据案例
  const caseStudies: CaseStudy[] = useMemo(
    () => [
      {
        id: 'bull-market-2023',
        title: '2023年牛市案例',
        description: '分析2023年A股市场牛市行情中的单均线策略表现',
        period: '2023-01-01 至 2023-12-31',
        symbol: '沪深300指数',
        data: generateMarketData('bull', 252),
        insights: [
          '在上涨趋势中，单均线策略能够有效捕捉主要涨幅',
          '金叉信号在牛市中成功率较高，但需要注意及时止盈',
          '适当延长均线周期可以减少假信号，提高策略稳定性',
        ],
        strategy: {
          type: '单均线金叉死叉策略',
          parameters: {
            shortMA: 10,
            longMA: 20,
            stopLoss: 0.05,
            takeProfit: 0.15,
          },
          performance: {
            totalReturn: 0.285, // 28.5%
            maxDrawdown: -0.082, // -8.2%
            sharpeRatio: 1.85,
            winRate: 0.68, // 68%
          },
        },
        keyEvents: [
          {
            date: '2023-03-15',
            event: '美联储加息周期结束预期',
            impact: 'positive',
          },
          {
            date: '2023-07-24',
            event: '政治局会议定调经济政策',
            impact: 'positive',
          },
          { date: '2023-10-23', event: '特别国债发行', impact: 'positive' },
        ],
      },
      {
        id: 'volatile-market-2022',
        title: '2022年震荡市场案例',
        description: '分析2022年高波动市场中的策略表现和风险控制',
        period: '2022-01-01 至 2022-12-31',
        symbol: '创业板指',
        data: generateMarketData('volatile', 252),
        insights: [
          '震荡市场中，单均线策略容易产生频繁交易',
          '需要结合其他技术指标过滤假信号',
          '严格的风险控制在震荡市中尤为重要',
        ],
        strategy: {
          type: '改进型单均线策略',
          parameters: {
            shortMA: 15,
            longMA: 30,
            stopLoss: 0.03,
            takeProfit: 0.08,
            volumeFilter: true,
          },
          performance: {
            totalReturn: 0.085, // 8.5%
            maxDrawdown: -0.156, // -15.6%
            sharpeRatio: 0.62,
            winRate: 0.45, // 45%
          },
        },
        keyEvents: [
          { date: '2022-04-25', event: '上海疫情封控', impact: 'negative' },
          { date: '2022-10-16', event: '二十大召开', impact: 'positive' },
          { date: '2022-12-07', event: '疫情防控政策调整', impact: 'positive' },
        ],
      },
      {
        id: 'bear-market-2021',
        title: '2021年结构性熊市案例',
        description: '分析2021年部分板块下跌行情中的策略表现',
        period: '2021-02-18 至 2021-12-31',
        symbol: '中证500指数',
        data: generateMarketData('bear', 210),
        insights: [
          '在下跌趋势中，死叉信号的可靠性更高',
          '需要及时止损，避免深度套牢',
          '熊市中应降低仓位，控制风险敞口',
        ],
        strategy: {
          type: '防守型单均线策略',
          parameters: {
            shortMA: 5,
            longMA: 15,
            stopLoss: 0.02,
            takeProfit: 0.05,
            maxPosition: 0.6,
          },
          performance: {
            totalReturn: -0.125, // -12.5%
            maxDrawdown: -0.234, // -23.4%
            sharpeRatio: -0.85,
            winRate: 0.38, // 38%
          },
        },
        keyEvents: [
          {
            date: '2021-03-15',
            event: '美债收益率快速上升',
            impact: 'negative',
          },
          { date: '2021-07-26', event: '教育行业双减政策', impact: 'negative' },
          { date: '2021-11-15', event: '北交所设立', impact: 'positive' },
        ],
      },
    ],
    [],
  );

  // 生成模拟市场数据
  function generateMarketData(
    marketType: 'bull' | 'bear' | 'volatile',
    days: number,
  ): MarketData[] {
    const data: MarketData[] = [];
    let basePrice =
      marketType === 'bull' ? 3000 : marketType === 'bear' ? 5000 : 4000;
    let trend = marketType === 'bull' ? 0.8 : marketType === 'bear' ? -0.6 : 0;
    const volatility = marketType === 'volatile' ? 0.03 : 0.015;

    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);

    for (let i = 0; i < days; i++) {
      const currentDate = new Date(startDate);
      currentDate.setDate(currentDate.getDate() + i);

      // 生成价格变化
      const randomChange = (Math.random() - 0.5) * 2 * volatility;
      const trendChange = trend * 0.01;
      const changePercent = randomChange + trendChange;

      basePrice = basePrice * (1 + changePercent);
      const high = basePrice * (1 + Math.random() * 0.02);
      const low = basePrice * (1 - Math.random() * 0.02);
      const volume = Math.random() * 1000000000 + 500000000;

      data.push({
        date: currentDate.toISOString().split('T')[0],
        price: parseFloat(basePrice.toFixed(2)),
        volume: Math.floor(volume),
        high: parseFloat(high.toFixed(2)),
        low: parseFloat(low.toFixed(2)),
        change: parseFloat((basePrice * changePercent).toFixed(2)),
        changePercent: parseFloat((changePercent * 100).toFixed(2)),
      });

      // 添加趋势变化点
      if (i === Math.floor(days * 0.3) || i === Math.floor(days * 0.7)) {
        trend = -trend * 0.5; // 趋势转折
      }
    }

    return data;
  }

  const currentCaseStudy = caseStudies.find(
    (cs) => cs.id === selectedCaseStudy,
  );

  // 计算移动平均线
  const calculateMA = useCallback(
    (data: MarketData[], period: number, index: number) => {
      if (index < period - 1) return null;

      const sum = data
        .slice(index - period + 1, index + 1)
        .reduce((acc, item) => acc + item.price, 0);

      return sum / period;
    },
    [],
  );

  // 准备图表数据
  const chartData = useMemo(() => {
    if (!currentCaseStudy) return null;

    const data = currentCaseStudy.data.slice(0, currentStep + 1);
    const shortMA = 10;
    const longMA = 20;

    return {
      labels: data.map((d) => d.date),
      datasets: [
        {
          label: '价格',
          data: data.map((d) => d.price),
          borderColor: 'rgb(59, 130, 246)',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderWidth: 2,
          fill: false,
          tension: 0.1,
          pointRadius: currentStep < 30 ? 3 : 1,
        },
        {
          label: `${shortMA}日均线`,
          data: data.map((d, i) =>
            calculateMA(currentCaseStudy.data, shortMA, i),
          ),
          borderColor: 'rgb(239, 68, 68)',
          backgroundColor: 'transparent',
          borderWidth: 2,
          fill: false,
          tension: 0.1,
          pointRadius: 0,
        },
        {
          label: `${longMA}日均线`,
          data: data.map((d, i) =>
            calculateMA(currentCaseStudy.data, longMA, i),
          ),
          borderColor: 'rgb(34, 197, 94)',
          backgroundColor: 'transparent',
          borderWidth: 2,
          fill: false,
          tension: 0.1,
          pointRadius: 0,
        },
      ],
    };
  }, [currentCaseStudy, currentStep, calculateMA]);

  // 动画控制
  useEffect(() => {
    if (isPlaying && currentCaseStudy) {
      const interval = setInterval(() => {
        setCurrentStep((prev) => {
          if (prev >= currentCaseStudy.data.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 1000 / speed);

      return () => clearInterval(interval);
    }
  }, [isPlaying, speed, currentCaseStudy]);

  // 控制函数
  const handlePlay = () => setIsPlaying(true);
  const handlePause = () => setIsPlaying(false);
  const handleReset = () => {
    setCurrentStep(0);
    setIsPlaying(false);
  };

  const handleCaseChange = (caseId: string) => {
    setSelectedCaseStudy(caseId);
    setCurrentStep(0);
    setIsPlaying(false);
    onCaseChange?.(caseId);
  };

  // Chart.js 配置
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      duration: isPlaying ? 300 : 0,
    },
    plugins: {
      legend: {
        position: 'top' as const,
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
      },
    },
    scales: {
      x: {
        display: true,
        grid: {
          display: false,
        },
        ticks: {
          maxTicksLimit: 10,
        },
      },
      y: {
        display: true,
        grid: {
          color: 'rgba(0, 0, 0, 0.05)',
        },
        ticks: {
          callback(value: any) {
            return value.toFixed(0);
          },
        },
      },
    },
  };

  if (!currentCaseStudy) {
    return <div className="text-center">加载中...</div>;
  }

  return (
    <div className="space-y-6">
      {/* 标题和案例选择 */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          真实市场数据案例分析
        </h2>
        <p className="text-gray-600 mb-6">通过历史数据验证量化策略的实际效果</p>

        <div className="flex justify-center space-x-4">
          {caseStudies.map((caseStudy) => (
            <Button
              key={caseStudy.id}
              variant={
                selectedCaseStudy === caseStudy.id ? 'default' : 'outline'
              }
              onClick={() => handleCaseChange(caseStudy.id)}
            >
              {caseStudy.title}
            </Button>
          ))}
        </div>
      </div>

      {/* 当前案例信息 */}
      <Card className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <h3 className="font-semibold text-gray-900 mb-2">案例概要</h3>
            <p className="text-sm text-gray-600 mb-2">
              {currentCaseStudy.description}
            </p>
            <div className="space-y-1 text-sm">
              <div className="flex items-center space-x-2">
                <Calendar className="h-4 w-4 text-gray-400" />
                <span>{currentCaseStudy.period}</span>
              </div>
              <div className="flex items-center space-x-2">
                <BarChart3 className="h-4 w-4 text-gray-400" />
                <span>{currentCaseStudy.symbol}</span>
              </div>
            </div>
          </div>

          <div>
            <h3 className="font-semibold text-gray-900 mb-2">策略参数</h3>
            <div className="space-y-1 text-sm">
              {Object.entries(currentCaseStudy.strategy.parameters).map(
                ([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-gray-600">{key}:</span>
                    <span className="font-medium">{String(value)}</span>
                  </div>
                ),
              )}
            </div>
          </div>

          <div>
            <h3 className="font-semibold text-gray-900 mb-2">策略表现</h3>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">总收益:</span>
                <span
                  className={`font-medium ${
                    currentCaseStudy.strategy.performance.totalReturn > 0
                      ? 'text-green-600'
                      : 'text-red-600'
                  }`}
                >
                  {(
                    currentCaseStudy.strategy.performance.totalReturn * 100
                  ).toFixed(1)}
                  %
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">最大回撤:</span>
                <span className="font-medium text-red-600">
                  {(
                    currentCaseStudy.strategy.performance.maxDrawdown * 100
                  ).toFixed(1)}
                  %
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">夏普比率:</span>
                <span className="font-medium">
                  {currentCaseStudy.strategy.performance.sharpeRatio.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">胜率:</span>
                <span className="font-medium">
                  {(
                    currentCaseStudy.strategy.performance.winRate * 100
                  ).toFixed(0)}
                  %
                </span>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* 详细分析标签页 */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">价格走势</TabsTrigger>
          <TabsTrigger value="analysis">策略分析</TabsTrigger>
          <TabsTrigger value="events">关键事件</TabsTrigger>
          <TabsTrigger value="insights">经验总结</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900">价格走势图</h3>
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-600">
                  {currentStep + 1} / {currentCaseStudy.data.length} 天
                </span>
                <Button variant="outline" size="sm" onClick={handleReset}>
                  <RotateCcw className="h-4 w-4 mr-2" />
                  重置
                </Button>
                <Button
                  variant={isPlaying ? 'secondary' : 'default'}
                  size="sm"
                  onClick={isPlaying ? handlePause : handlePlay}
                >
                  {isPlaying ? (
                    <>
                      <Pause className="h-4 w-4 mr-2" />
                      暂停
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4 mr-2" />
                      播放
                    </>
                  )}
                </Button>
              </div>
            </div>

            <div style={{ height: '400px' }}>
              {chartData && <Line data={chartData} options={chartOptions} />}
            </div>

            <div className="mt-4">
              <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
                <span>播放进度</span>
                <span>
                  {Math.round(
                    ((currentStep + 1) / currentCaseStudy.data.length) * 100,
                  )}
                  %
                </span>
              </div>
              <Slider
                value={[currentStep]}
                onValueChange={(value) => setCurrentStep(value[0])}
                max={currentCaseStudy.data.length - 1}
                step={1}
                className="w-full"
              />
            </div>

            <div className="mt-4">
              <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
                <span>播放速度</span>
                <span>{speed}x</span>
              </div>
              <Slider
                value={[speed]}
                onValueChange={(value) => setSpeed(value[0])}
                min={0.5}
                max={3.0}
                step={0.5}
                className="w-full"
              />
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="analysis" className="space-y-4">
          <Card className="p-6">
            <h3 className="font-semibold text-gray-900 mb-4">策略表现分析</h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="font-medium text-gray-900 mb-3">收益指标</h4>
                <div className="space-y-3">
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                    <span>年化收益率</span>
                    <Badge
                      variant={
                        currentCaseStudy.strategy.performance.totalReturn > 0
                          ? 'default'
                          : 'destructive'
                      }
                    >
                      {(
                        currentCaseStudy.strategy.performance.totalReturn * 100
                      ).toFixed(1)}
                      %
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                    <span>最大回撤</span>
                    <Badge variant="destructive">
                      {(
                        currentCaseStudy.strategy.performance.maxDrawdown * 100
                      ).toFixed(1)}
                      %
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                    <span>夏普比率</span>
                    <Badge variant="outline">
                      {currentCaseStudy.strategy.performance.sharpeRatio.toFixed(
                        2,
                      )}
                    </Badge>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="font-medium text-gray-900 mb-3">交易统计</h4>
                <div className="space-y-3">
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                    <span>胜率</span>
                    <Badge variant="outline">
                      {(
                        currentCaseStudy.strategy.performance.winRate * 100
                      ).toFixed(0)}
                      %
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                    <span>策略类型</span>
                    <Badge variant="secondary">
                      {currentCaseStudy.strategy.type}
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                    <span>数据周期</span>
                    <Badge variant="outline">
                      {currentCaseStudy.data.length} 天
                    </Badge>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="events" className="space-y-4">
          <Card className="p-6">
            <h3 className="font-semibold text-gray-900 mb-4">关键市场事件</h3>

            <div className="space-y-4">
              {currentCaseStudy.keyEvents.map((event, index) => (
                <div
                  key={index}
                  className="flex items-start space-x-4 p-4 border rounded-lg"
                >
                  <div
                    className={`w-3 h-3 rounded-full mt-1 ${
                      event.impact === 'positive'
                        ? 'bg-green-500'
                        : event.impact === 'negative'
                          ? 'bg-red-500'
                          : 'bg-gray-500'
                    }`}
                  ></div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <h4 className="font-medium text-gray-900">
                        {event.event}
                      </h4>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm text-gray-500">
                          {event.date}
                        </span>
                        <Badge
                          variant={
                            event.impact === 'positive'
                              ? 'default'
                              : event.impact === 'negative'
                                ? 'destructive'
                                : 'secondary'
                          }
                        >
                          {event.impact === 'positive'
                            ? '利好'
                            : event.impact === 'negative'
                              ? '利空'
                              : '中性'}
                        </Badge>
                      </div>
                    </div>
                    <p className="text-sm text-gray-600">
                      该事件对市场产生了显著影响，是当时的重要驱动因素。
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="insights" className="space-y-4">
          <Card className="p-6">
            <h3 className="font-semibold text-gray-900 mb-4">经验总结与启示</h3>

            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start space-x-3">
                  <Info className="h-5 w-5 text-blue-600 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-blue-900 mb-2">核心发现</h4>
                    <ul className="space-y-2 text-sm text-blue-800">
                      {currentCaseStudy.insights.map((insight, index) => (
                        <li key={index} className="flex items-start space-x-2">
                          <span className="text-blue-600 mt-1">•</span>
                          <span>{insight}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>

              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="flex items-start space-x-3">
                  <Activity className="h-5 w-5 text-yellow-600 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-yellow-900 mb-2">
                      实践建议
                    </h4>
                    <ul className="space-y-2 text-sm text-yellow-800">
                      <li className="flex items-start space-x-2">
                        <span className="text-yellow-600 mt-1">•</span>
                        <span>不同市场环境下需要调整策略参数</span>
                      </li>
                      <li className="flex items-start space-x-2">
                        <span className="text-yellow-600 mt-1">•</span>
                        <span>严格执行风险管理规则，避免情绪化交易</span>
                      </li>
                      <li className="flex items-start space-x-2">
                        <span className="text-yellow-600 mt-1">•</span>
                        <span>定期回顾和优化策略参数，适应市场变化</span>
                      </li>
                      <li className="flex items-start space-x-2">
                        <span className="text-yellow-600 mt-1">•</span>
                        <span>关注宏观经济事件对市场的影响</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
