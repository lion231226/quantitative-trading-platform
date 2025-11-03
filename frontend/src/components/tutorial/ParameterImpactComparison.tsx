import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import {
  Settings,
  TrendingUp,
  TrendingDown,
  BarChart3,
  ArrowUpDown,
  RefreshCw,
  Info,
  AlertTriangle,
  CheckCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Slider } from '@/components/ui/slider';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

// 注册Chart.js组件
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface StrategyParameters {
  shortMA: number;
  longMA: number;
  stopLoss: number;
  takeProfit: number;
  positionSize: number;
}

interface PerformanceMetrics {
  totalReturn: number;
  maxDrawdown: number;
  sharpeRatio: number;
  winRate: number;
  profitFactor: number;
  maxConsecutiveLosses: number;
  totalTrades: number;
}

interface ParameterImpactComparisonProps {
  onParametersChange?: (parameters: StrategyParameters) => void;
  defaultParameters?: StrategyParameters;
  showAdvanced?: boolean;
}

/**
 * 参数影响对比组件
 * 实时展示不同参数设置对策略性能的影响
 */
export function ParameterImpactComparison({
  onParametersChange,
  defaultParameters = {
    shortMA: 10,
    longMA: 20,
    stopLoss: 0.05,
    takeProfit: 0.15,
    positionSize: 0.1,
  },
  showAdvanced = true,
}: ParameterImpactComparisonProps) {
  const [parameters, setParameters] = useState<StrategyParameters>(defaultParameters);
  const [isCalculating, setIsCalculating] = useState(false);
  const [activeTab, setActiveTab] = useState('comparison');
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([
    'totalReturn', 'maxDrawdown', 'sharpeRatio', 'winRate'
  ]);

  // 参数范围配置
  const parameterRanges = {
    shortMA: { min: 5, max: 50, step: 1, label: '短期均线周期' },
    longMA: { min: 10, max: 100, step: 1, label: '长期均线周期' },
    stopLoss: { min: 0.01, max: 0.2, step: 0.01, label: '止损比例' },
    takeProfit: { min: 0.05, max: 0.5, step: 0.01, label: '止盈比例' },
    positionSize: { min: 0.01, max: 0.5, step: 0.01, label: '仓位大小' },
  };

  // 生成模拟性能数据
  const generatePerformanceData = useCallback((params: StrategyParameters): PerformanceMetrics => {
    // 模拟参数对性能的影响逻辑
    const maRatio = params.shortMA / params.longMA;
    const riskRewardRatio = params.takeProfit / params.stopLoss;

    // 基于参数生成性能指标
    let totalReturn = 0.15; // 基础收益率15%
    let maxDrawdown = 0.08; // 基础最大回撤8%
    let sharpeRatio = 1.2; // 基础夏普比率
    let winRate = 0.55; // 基础胜率55%

    // 短期/长期均线比例影响
    if (maRatio > 0.8) {
      // 均线比例较接近，信号较少但质量较高
      totalReturn += 0.05;
      sharpeRatio += 0.3;
      winRate += 0.1;
    } else if (maRatio < 0.3) {
      // 均线比例差异大，信号频繁但质量较低
      totalReturn -= 0.08;
      sharpeRatio -= 0.4;
      winRate -= 0.15;
      maxDrawdown += 0.05;
    }

    // 风险回报比影响
    if (riskRewardRatio > 3) {
      // 较好的风险回报比
      totalReturn += 0.03;
      sharpeRatio += 0.2;
    } else if (riskRewardRatio < 1.5) {
      // 风险回报比较差
      totalReturn -= 0.05;
      maxDrawdown += 0.03;
    }

    // 止损设置影响
    if (params.stopLoss > 0.1) {
      // 宽止损，减少被止损概率但增加单次损失
      maxDrawdown += 0.02;
      winRate += 0.05;
    } else if (params.stopLoss < 0.02) {
      // 紧止损，增加止损概率但控制单次损失
      maxDrawdown -= 0.02;
      winRate -= 0.08;
    }

    // 仓位大小影响
    if (params.positionSize > 0.2) {
      // 大仓位，放大收益和风险
      totalReturn *= 1.2;
      maxDrawdown *= 1.5;
      sharpeRatio *= 0.9;
    } else if (params.positionSize < 0.05) {
      // 小仓位，降低收益和风险
      totalReturn *= 0.7;
      maxDrawdown *= 0.6;
      sharpeRatio *= 1.1;
    }

    // 添加一些随机性
    const randomFactor = 0.95 + Math.random() * 0.1;
    totalReturn *= randomFactor;

    return {
      totalReturn: Math.round(totalReturn * 10000) / 10000,
      maxDrawdown: Math.round(maxDrawdown * 10000) / 10000,
      sharpeRatio: Math.round(sharpeRatio * 100) / 100,
      winRate: Math.round(winRate * 10000) / 10000,
      profitFactor: Math.round((1 + totalReturn / Math.abs(maxDrawdown)) * 100) / 100,
      maxConsecutiveLosses: Math.floor(Math.random() * 5) + 3,
      totalTrades: Math.floor(Math.random() * 100) + 50,
    };
  }, []);

  // 计算当前参数的性能
  const currentPerformance = useMemo(() => {
    return generatePerformanceData(parameters);
  }, [parameters, generatePerformanceData]);

  // 生成对比数据
  const comparisonData = useMemo(() => {
    const baseParams = defaultParameters;
    const variations: Array<{ label: string; params: StrategyParameters; performance: PerformanceMetrics }> = [];

    // 生成参数变化对比
    ['shortMA', 'longMA', 'stopLoss', 'takeProfit'].forEach(param => {
      const range = parameterRanges[param as keyof typeof parameterRanges];

      // 低值
      const lowParams = { ...baseParams };
      lowParams[param as keyof StrategyParameters] = range.min;
      variations.push({
        label: `${range.label} (低)`,
        params: lowParams,
        performance: generatePerformanceData(lowParams),
      });

      // 高值
      const highParams = { ...baseParams };
      highParams[param as keyof StrategyParameters] = range.max;
      variations.push({
        label: `${range.label} (高)`,
        params: highParams,
        performance: generatePerformanceData(highParams),
      });
    });

    // 保守策略
    const conservativeParams = { ...baseParams };
    conservativeParams.stopLoss = 0.02;
    conservativeParams.takeProfit = 0.08;
    conservativeParams.positionSize = 0.05;
    variations.push({
      label: '保守策略',
      params: conservativeParams,
      performance: generatePerformanceData(conservativeParams),
    });

    // 激进策略
    const aggressiveParams = { ...baseParams };
    aggressiveParams.stopLoss = 0.08;
    aggressiveParams.takeProfit = 0.25;
    aggressiveParams.positionSize = 0.2;
    variations.push({
      label: '激进策略',
      params: aggressiveParams,
      performance: generatePerformanceData(aggressiveParams),
    });

    return variations;
  }, [defaultParameters, parameterRanges, generatePerformanceData]);

  // 处理参数变化
  const handleParameterChange = useCallback((param: keyof StrategyParameters, value: number) => {
    const newParams = { ...parameters, [param]: value };
    setParameters(newParams);
    onParametersChange?.(newParams);
    setIsCalculating(true);

    // 模拟计算延迟
    setTimeout(() => setIsCalculating(false), 300);
  }, [parameters, onParametersChange]);

  // 重置参数
  const handleReset = useCallback(() => {
    setParameters(defaultParameters);
    onParametersChange?.(defaultParameters);
  }, [defaultParameters, onParametersChange]);

  // 图表数据准备
  const chartData = useMemo(() => {
    const labels = ['当前策略', ...comparisonData.map(v => v.label)];
    const datasets = selectedMetrics.map(metric => {
      const metricConfig = {
        totalReturn: { label: '总收益率', color: 'rgb(59, 130, 246)', format: (v: number) => `${(v * 100).toFixed(1)}%` },
        maxDrawdown: { label: '最大回撤', color: 'rgb(239, 68, 68)', format: (v: number) => `${(v * 100).toFixed(1)}%` },
        sharpeRatio: { label: '夏普比率', color: 'rgb(34, 197, 94)', format: (v: number) => v.toFixed(2) },
        winRate: { label: '胜率', color: 'rgb(168, 85, 247)', format: (v: number) => `${(v * 100).toFixed(0)}%` },
        profitFactor: { label: '盈亏比', color: 'rgb(251, 146, 60)', format: (v: number) => v.toFixed(2) },
      }[metric];

      const data = [
        currentPerformance[metric as keyof PerformanceMetrics],
        ...comparisonData.map(v => v.performance[metric as keyof PerformanceMetrics])
      ];

      return {
        label: metricConfig.label,
        data,
        borderColor: metricConfig.color,
        backgroundColor: metricConfig.color.replace('rgb', 'rgba').replace(')', ', 0.1)'),
        borderWidth: 2,
        fill: false,
        tension: 0.1,
      };
    });

    return {
      labels,
      datasets,
    };
  }, [currentPerformance, comparisonData, selectedMetrics]);

  // Chart.js 配置
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      intersect: false,
      mode: 'index' as const,
    },
    plugins: {
      legend: {
        position: 'top' as const,
      },
      tooltip: {
        callbacks: {
          label: function(context: any) {
            const datasetLabel = context.dataset.label || '';
            const value = context.parsed.y;
            const metric = selectedMetrics[context.datasetIndex];
            const metricConfig = {
              totalReturn: (v: number) => `${(v * 100).toFixed(1)}%`,
              maxDrawdown: (v: number) => `${(v * 100).toFixed(1)}%`,
              sharpeRatio: (v: number) => v.toFixed(2),
              winRate: (v: number) => `${(v * 100).toFixed(0)}%`,
              profitFactor: (v: number) => v.toFixed(2),
            }[metric];

            return `${datasetLabel}: ${metricConfig ? metricConfig(value) : value}`;
          },
        },
      },
    },
    scales: {
      y: {
        beginAtZero: false,
        grid: {
          color: 'rgba(0, 0, 0, 0.05)',
        },
      },
      x: {
        grid: {
          display: false,
        },
      },
    },
  };

  // 获取性能等级
  const getPerformanceGrade = (metric: keyof PerformanceMetrics, value: number) => {
    const thresholds = {
      totalReturn: { excellent: 0.2, good: 0.1, poor: 0 },
      maxDrawdown: { excellent: 0.05, good: 0.1, poor: 0.15 },
      sharpeRatio: { excellent: 2, good: 1, poor: 0.5 },
      winRate: { excellent: 0.6, good: 0.5, poor: 0.4 },
      profitFactor: { excellent: 2, good: 1.5, poor: 1 },
      maxConsecutiveLosses: { excellent: 2, good: 4, poor: 6 },
    };

    const threshold = thresholds[metric];
    if (!threshold) return 'medium';

    if (metric === 'maxDrawdown' || metric === 'maxConsecutiveLosses') {
      // 越小越好的指标
      if (value <= threshold.excellent) return 'excellent';
      if (value <= threshold.good) return 'good';
      return 'poor';
    } else {
      // 越大越好的指标
      if (value >= threshold.excellent) return 'excellent';
      if (value >= threshold.good) return 'good';
      return 'poor';
    }
  };

  const getGradeBadge = (grade: string) => {
    const config = {
      excellent: { label: '优秀', variant: 'default' as const, icon: CheckCircle },
      good: { label: '良好', variant: 'secondary' as const, icon: TrendingUp },
      poor: { label: '需改进', variant: 'destructive' as const, icon: AlertTriangle },
    };

    return config[grade as keyof typeof config] || config.good;
  };

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          参数影响对比分析
        </h2>
        <p className="text-gray-600">
          实时调整策略参数，观察对性能指标的影响
        </p>
      </div>

      {/* 参数调整面板 */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="font-semibold text-gray-900">策略参数设置</h3>
          <div className="flex items-center space-x-2">
            {isCalculating && (
              <div className="flex items-center space-x-2 text-blue-600">
                <RefreshCw className="h-4 w-4 animate-spin" />
                <span className="text-sm">计算中...</span>
              </div>
            )}
            <Button variant="outline" size="sm" onClick={handleReset}>
              重置默认
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Object.entries(parameterRanges).map(([key, config]) => (
            <div key={key} className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-gray-700">
                  {config.label}
                </label>
                <span className="text-sm font-bold text-blue-600">
                  {key === 'shortMA' || key === 'longMA' ? parameters[key as keyof StrategyParameters] :
                   key === 'positionSize' ? `${(parameters[key as keyof StrategyParameters] * 100).toFixed(0)}%` :
                   `${(parameters[key as keyof StrategyParameters] * 100).toFixed(1)}%`}
                </span>
              </div>
              <Slider
                value={[parameters[key as keyof StrategyParameters]]}
                onValueChange={(value) => handleParameterChange(key as keyof StrategyParameters, value[0])}
                min={config.min}
                max={config.max}
                step={config.step}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>{key === 'shortMA' || key === 'longMA' ? config.min : `${(config.min * 100).toFixed(0)}%`}</span>
                <span>{key === 'shortMA' || key === 'longMA' ? config.max : `${(config.max * 100).toFixed(0)}%`}</span>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* 分析结果标签页 */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="comparison">性能对比</TabsTrigger>
          <TabsTrigger value="analysis">详细分析</TabsTrigger>
          <TabsTrigger value="recommendations">优化建议</TabsTrigger>
        </TabsList>

        <TabsContent value="comparison" className="space-y-4">
          {/* 指标选择 */}
          <Card className="p-4">
            <h4 className="font-medium text-gray-900 mb-3">选择显示指标</h4>
            <div className="flex flex-wrap gap-2">
              {[
                { key: 'totalReturn', label: '总收益率' },
                { key: 'maxDrawdown', label: '最大回撤' },
                { key: 'sharpeRatio', label: '夏普比率' },
                { key: 'winRate', label: '胜率' },
                { key: 'profitFactor', label: '盈亏比' },
              ].map(metric => (
                <Button
                  key={metric.key}
                  variant={selectedMetrics.includes(metric.key) ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => {
                    setSelectedMetrics(prev =>
                      prev.includes(metric.key)
                        ? prev.filter(m => m !== metric.key)
                        : [...prev, metric.key]
                    );
                  }}
                >
                  {metric.label}
                </Button>
              ))}
            </div>
          </Card>

          {/* 对比图表 */}
          <Card className="p-6">
            <h3 className="font-semibold text-gray-900 mb-4">性能对比图</h3>
            <div style={{ height: '400px' }}>
              <Line data={chartData} options={chartOptions} />
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="analysis" className="space-y-4">
          <Card className="p-6">
            <h3 className="font-semibold text-gray-900 mb-4">当前策略详细分析</h3>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {Object.entries(currentPerformance).map(([metric, value]) => {
                const grade = getPerformanceGrade(metric as keyof PerformanceMetrics, value);
                const gradeConfig = getGradeBadge(grade);
                const isBetter = grade === 'excellent' || grade === 'good';

                return (
                  <Card key={metric} className={`p-4 ${isBetter ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}>
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium text-gray-900">
                        {metric === 'totalReturn' && '总收益率'}
                        {metric === 'maxDrawdown' && '最大回撤'}
                        {metric === 'sharpeRatio' && '夏普比率'}
                        {metric === 'winRate' && '胜率'}
                        {metric === 'profitFactor' && '盈亏比'}
                        {metric === 'maxConsecutiveLosses' && '最大连续亏损'}
                        {metric === 'totalTrades' && '总交易次数'}
                      </h4>
                      <gradeConfig.icon className={`h-4 w-4 ${
                        grade === 'excellent' ? 'text-green-600' :
                        grade === 'good' ? 'text-blue-600' : 'text-red-600'
                      }`} />
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="text-2xl font-bold text-gray-900">
                        {metric === 'totalReturn' && `${(value * 100).toFixed(1)}%`}
                        {metric === 'maxDrawdown' && `${(value * 100).toFixed(1)}%`}
                        {metric === 'sharpeRatio' && value.toFixed(2)}
                        {metric === 'winRate' && `${(value * 100).toFixed(0)}%`}
                        {metric === 'profitFactor' && value.toFixed(2)}
                        {metric === 'maxConsecutiveLosses' && value}
                        {metric === 'totalTrades' && value}
                      </div>
                      <Badge {...gradeConfig.variant}>
                        {gradeConfig.label}
                      </Badge>
                    </div>

                    <div className="mt-3 text-xs text-gray-600">
                      {metric === 'totalReturn' && '策略在测试期间的总收益表现'}
                      {metric === 'maxDrawdown' && '策略从高点到低点的最大跌幅'}
                      {metric === 'sharpeRatio' && '风险调整后的收益率指标'}
                      {metric === 'winRate' && '盈利交易占总交易的比例'}
                      {metric === 'profitFactor' && '总盈利与总亏损的比值'}
                      {metric === 'maxConsecutiveLosses' && '最大连续亏损次数'}
                      {metric === 'totalTrades' && '策略执行的总交易次数'}
                    </div>
                  </Card>
                );
              })}
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="recommendations" className="space-y-4">
          <Card className="p-6">
            <h3 className="font-semibold text-gray-900 mb-4">参数优化建议</h3>

            <div className="space-y-4">
              {/* 基于当前性能的建议 */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start space-x-3">
                  <Info className="h-5 w-5 text-blue-600 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-blue-900 mb-2">当前参数评估</h4>
                    <ul className="space-y-2 text-sm text-blue-800">
                      <li>• 均线周期比例: {parameters.shortMA}/{parameters.longMA} = {(parameters.shortMA / parameters.longMA).toFixed(2)}</li>
                      <li>• 风险回报比: {(parameters.takeProfit / parameters.stopLoss).toFixed(1)}:1</li>
                      <li>• 仓位控制: {(parameters.positionSize * 100).toFixed(0)}%</li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* 优化建议 */}
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-start space-x-3">
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-green-900 mb-2">优化建议</h4>
                    <ul className="space-y-2 text-sm text-green-800">
                      {currentPerformance.maxDrawdown > 0.12 && (
                        <li>• 考虑降低止损比例或仓位大小，以控制最大回撤</li>
                      )}
                      {currentPerformance.winRate < 0.45 && (
                        <li>• 调整均线周期比例，减少假信号频率</li>
                      )}
                      {currentPerformance.sharpeRatio < 1.0 && (
                        <li>• 提高风险回报比，改善风险调整后收益</li>
                      )}
                      {parameters.takeProfit / parameters.stopLoss < 2.0 && (
                        <li>• 建议风险回报比至少为2:1，提高策略稳定性</li>
                      )}
                      {parameters.shortMA / parameters.longMA > 0.8 && (
                        <li>• 均线周期较接近，可考虑增加差距以获得更多信号</li>
                      )}
                      {parameters.shortMA / parameters.longMA < 0.3 && (
                        <li>• 均线周期差距较大，可能产生过多假信号</li>
                      )}
                    </ul>
                  </div>
                </div>
              </div>

              {/* 风险提示 */}
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="flex items-start space-x-3">
                  <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-yellow-900 mb-2">风险提示</h4>
                    <ul className="space-y-2 text-sm text-yellow-800">
                      <li>• 历史表现不代表未来结果，实际交易可能存在差异</li>
                      <li>• 参数优化可能存在过度拟合风险，建议进行样本外测试</li>
                      <li>• 市场环境变化可能影响策略有效性，需要定期回顾调整</li>
                      <li>• 建议结合多种分析方法，不要仅依赖单一指标</li>
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