import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Line } from 'react-chartjs-2';
import {
  AnimationOptions,
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
  Maximize2,
  Minimize2,
  Pause,
  Play,
  RotateCcw,
  Settings,
  SkipForward,
  Volume2,
  VolumeX,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';

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

interface TutorialAnimationProps {
  type: 'moving-average' | 'golden-cross' | 'death-cross' | 'signal-generation';
  data?: any[];
  speed?: number;
  autoPlay?: boolean;
  showControls?: boolean;
  onStepChange?: (step: number, total: number) => void;
  onComplete?: () => void;
  width?: number;
  height?: number;
}

interface AnimationState {
  isPlaying: boolean;
  currentStep: number;
  totalSteps: number;
  speed: number;
  isMuted: boolean;
  isFullscreen: boolean;
  showSettings: boolean;
}

/**
 * 教程动画演示组件
 * 支持移动平均线计算、金叉死叉等策略原理动画演示
 */
export function TutorialAnimation({
  type,
  data = [],
  speed = 1.0,
  autoPlay = false,
  showControls = true,
  onStepChange,
  onComplete,
  width = 800,
  height = 400,
}: TutorialAnimationProps) {
  const [animationState, setAnimationState] = useState<AnimationState>({
    isPlaying: autoPlay,
    currentStep: 0,
    totalSteps: 100,
    speed,
    isMuted: false,
    isFullscreen: false,
    showSettings: false,
  });

  const [chartData, setChartData] = useState<any>(null);
  const [animationData, setAnimationData] = useState<any[]>([]);
  const intervalRef = useRef<NodeJS.Timeout>();
  const chartRef = useRef<any>(null);

  // 生成示例数据
  const generateSampleData = useCallback(() => {
    if (data.length > 0) {
      return data;
    }

    const points = [];
    let basePrice = 100;

    for (let i = 0; i < 50; i++) {
      // 生成模拟价格数据
      const change = (Math.random() - 0.5) * 4;
      basePrice += change;
      basePrice = Math.max(80, Math.min(120, basePrice)); // 限制价格范围

      points.push({
        index: i,
        price: basePrice,
        date: `Day ${i + 1}`,
        volume: Math.random() * 1000000 + 500000,
      });
    }

    return points;
  }, [data]);

  // 计算移动平均线
  const calculateMovingAverage = useCallback(
    (data: any[], period: number, currentIndex: number) => {
      if (currentIndex < period - 1) return null;

      const sum = data
        .slice(currentIndex - period + 1, currentIndex + 1)
        .reduce((acc, point) => acc + point.price, 0);

      return sum / period;
    },
    [],
  );

  // 检测金叉死叉
  const detectCross = useCallback(
    (data: any[], currentIndex: number) => {
      if (currentIndex < 1) return null;

      const shortMA10 = calculateMovingAverage(data, 10, currentIndex);
      const shortMA10Prev = calculateMovingAverage(data, 10, currentIndex - 1);
      const longMA20 = calculateMovingAverage(data, 20, currentIndex);
      const longMA20Prev = calculateMovingAverage(data, 20, currentIndex - 1);

      if (!shortMA10 || !shortMA10Prev || !longMA20 || !longMA20Prev) {
        return null;
      }

      // 金叉：短期均线上穿长期均线
      if (shortMA10Prev <= longMA20Prev && shortMA10 > longMA20) {
        return {
          type: 'golden-cross',
          price: data[currentIndex].price,
          index: currentIndex,
        };
      }

      // 死叉：短期均线下穿长期均线
      if (shortMA10Prev >= longMA20Prev && shortMA10 < longMA20) {
        return {
          type: 'death-cross',
          price: data[currentIndex].price,
          index: currentIndex,
        };
      }

      return null;
    },
    [calculateMovingAverage],
  );

  // 准备动画数据
  const prepareAnimationData = useCallback(() => {
    const sampleData = generateSampleData();
    const animationSteps = [];

    for (let i = 0; i < sampleData.length; i++) {
      const step = {
        ...sampleData[i],
        ma10: calculateMovingAverage(sampleData, 10, i),
        ma20: calculateMovingAverage(sampleData, 20, i),
        cross: detectCross(sampleData, i),
      };
      animationSteps.push(step);
    }

    setAnimationData(animationSteps);
    setAnimationState((prev) => ({
      ...prev,
      totalSteps: animationSteps.length,
    }));
  }, [generateSampleData, calculateMovingAverage, detectCross]);

  // 更新图表数据
  const updateChartData = useCallback(
    (stepIndex: number) => {
      if (animationData.length === 0) return;

      const currentData = animationData.slice(0, stepIndex + 1);
      const labels = currentData.map((d) => d.date);
      const prices = currentData.map((d) => d.price);
      const ma10 = currentData.map((d) => d.ma10);
      const ma20 = currentData.map((d) => d.ma20);

      // 找到交叉点
      const crossPoints = currentData
        .filter((d) => d.cross)
        .map((d) => ({
          x: d.date,
          y: d.price,
          type: d.cross?.type,
        }));

      const newChartData = {
        labels,
        datasets: [
          {
            label: '价格',
            data: prices,
            borderColor: 'rgb(59, 130, 246)',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.1,
            pointRadius: currentData.length <= 10 ? 4 : 2,
            pointHoverRadius: 6,
          },
          {
            label: 'MA10',
            data: ma10,
            borderColor: 'rgb(239, 68, 68)',
            backgroundColor: 'transparent',
            borderWidth: 2,
            fill: false,
            tension: 0.1,
            pointRadius: 0,
            pointHoverRadius: 4,
          },
          {
            label: 'MA20',
            data: ma20,
            borderColor: 'rgb(34, 197, 94)',
            backgroundColor: 'transparent',
            borderWidth: 2,
            fill: false,
            tension: 0.1,
            pointRadius: 0,
            pointHoverRadius: 4,
          },
          // 交叉点标记
          {
            label: '金叉',
            data: crossPoints
              .filter((p) => p.type === 'golden-cross')
              .map((p) => ({ x: p.x, y: p.y })),
            borderColor: 'rgb(34, 197, 94)',
            backgroundColor: 'rgb(34, 197, 94)',
            pointStyle: 'triangle',
            rotation: 0,
            radius: 8,
            pointHoverRadius: 10,
            showLine: false,
          },
          {
            label: '死叉',
            data: crossPoints
              .filter((p) => p.type === 'death-cross')
              .map((p) => ({ x: p.x, y: p.y })),
            borderColor: 'rgb(239, 68, 68)',
            backgroundColor: 'rgb(239, 68, 68)',
            pointStyle: 'triangle',
            rotation: 180,
            radius: 8,
            pointHoverRadius: 10,
            showLine: false,
          },
        ],
      };

      setChartData(newChartData);
    },
    [animationData],
  );

  // 动画播放控制
  useEffect(() => {
    if (animationState.isPlaying) {
      intervalRef.current = setInterval(() => {
        setAnimationState((prev) => {
          const nextStep = Math.min(prev.currentStep + 1, prev.totalSteps - 1);

          if (nextStep === prev.totalSteps - 1) {
            // 动画完成
            onComplete?.();
            return { ...prev, isPlaying: false, currentStep: nextStep };
          }

          return { ...prev, currentStep: nextStep };
        });
      }, 1000 / animationState.speed);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [
    animationState.isPlaying,
    animationState.speed,
    animationState.totalSteps,
    onComplete,
  ]);

  // 步骤变化时更新图表
  useEffect(() => {
    updateChartData(animationState.currentStep);
    onStepChange?.(animationState.currentStep, animationState.totalSteps);
  }, [animationState.currentStep, updateChartData, onStepChange]);

  // 初始化数据
  useEffect(() => {
    prepareAnimationData();
  }, [prepareAnimationData]);

  // 控制函数
  const handlePlay = () => {
    setAnimationState((prev) => ({ ...prev, isPlaying: true }));
  };

  const handlePause = () => {
    setAnimationState((prev) => ({ ...prev, isPlaying: false }));
  };

  const handleReset = () => {
    setAnimationState((prev) => ({
      ...prev,
      currentStep: 0,
      isPlaying: false,
    }));
  };

  const handleStepForward = () => {
    setAnimationState((prev) => ({
      ...prev,
      currentStep: Math.min(prev.currentStep + 1, prev.totalSteps - 1),
    }));
  };

  const handleSpeedChange = (newSpeed: number[]) => {
    setAnimationState((prev) => ({ ...prev, speed: newSpeed[0] }));
  };

  const handleStepChange = (newStep: number[]) => {
    setAnimationState((prev) => ({ ...prev, currentStep: newStep[0] }));
  };

  // Chart.js 配置
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      duration: animationState.isPlaying ? 500 : 0,
      easing: 'easeInOutQuart' as const,
    },
    interaction: {
      intersect: false,
      mode: 'index' as const,
    },
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          usePointStyle: true,
          padding: 20,
        },
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: '#fff',
        bodyColor: '#fff',
        padding: 12,
        borderColor: 'rgba(255, 255, 255, 0.1)',
        borderWidth: 1,
        displayColors: true,
        callbacks: {
          label(context: any) {
            let label = context.dataset.label || '';
            if (label) {
              label += ': ';
            }
            if (context.parsed.y !== null) {
              label += context.parsed.y.toFixed(2);
            }
            return label;
          },
        },
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
            return `¥${value.toFixed(0)}`;
          },
        },
      },
    },
  };

  // 渲染动画内容
  const renderAnimationContent = () => {
    if (!chartData) {
      return (
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
            <p className="text-gray-600">正在准备动画...</p>
          </div>
        </div>
      );
    }

    switch (type) {
      case 'moving-average':
        return (
          <MovingAverageAnimation data={chartData} options={chartOptions} />
        );
      case 'golden-cross':
        return <GoldenCrossAnimation data={chartData} options={chartOptions} />;
      case 'death-cross':
        return <DeathCrossAnimation data={chartData} options={chartOptions} />;
      case 'signal-generation':
        return (
          <SignalGenerationAnimation data={chartData} options={chartOptions} />
        );
      default:
        return <Line ref={chartRef} data={chartData} options={chartOptions} />;
    }
  };

  return (
    <div
      className={`bg-white rounded-lg ${animationState.isFullscreen ? 'fixed inset-0 z-50' : ''}`}
    >
      <Card className="h-full">
        {/* 顶部工具栏 */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center space-x-3">
            <h3 className="font-semibold text-gray-900">
              {type === 'moving-average' && '移动平均线计算'}
              {type === 'golden-cross' && '金叉信号演示'}
              {type === 'death-cross' && '死叉信号演示'}
              {type === 'signal-generation' && '交易信号生成'}
            </h3>
            <Badge variant="outline">
              步骤 {animationState.currentStep + 1} /{' '}
              {animationState.totalSteps}
            </Badge>
          </div>

          <div className="flex items-center space-x-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                setAnimationState((prev) => ({
                  ...prev,
                  isMuted: !prev.isMuted,
                }))
              }
            >
              {animationState.isMuted ? (
                <VolumeX className="h-4 w-4" />
              ) : (
                <Volume2 className="h-4 w-4" />
              )}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                setAnimationState((prev) => ({
                  ...prev,
                  showSettings: !prev.showSettings,
                }))
              }
            >
              <Settings className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                setAnimationState((prev) => ({
                  ...prev,
                  isFullscreen: !prev.isFullscreen,
                }))
              }
            >
              {animationState.isFullscreen ? (
                <Minimize2 className="h-4 w-4" />
              ) : (
                <Maximize2 className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>

        {/* 动画区域 */}
        <div
          className="relative"
          style={{
            height: animationState.isFullscreen
              ? 'calc(100vh - 200px)'
              : height,
          }}
        >
          {renderAnimationContent()}
        </div>

        {/* 控制面板 */}
        {showControls && (
          <div className="p-4 border-t bg-gray-50">
            <div className="space-y-4">
              {/* 播放控制 */}
              <div className="flex items-center justify-center space-x-3">
                <Button variant="outline" size="sm" onClick={handleReset}>
                  <RotateCcw className="h-4 w-4" />
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  onClick={animationState.isPlaying ? handlePause : handlePlay}
                >
                  {animationState.isPlaying ? (
                    <Pause className="h-4 w-4" />
                  ) : (
                    <Play className="h-4 w-4" />
                  )}
                </Button>
                <Button variant="outline" size="sm" onClick={handleStepForward}>
                  <SkipForward className="h-4 w-4" />
                </Button>
              </div>

              {/* 进度条 */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm text-gray-600">
                  <span>进度</span>
                  <span>
                    {animationState.currentStep + 1} /{' '}
                    {animationState.totalSteps}
                  </span>
                </div>
                <Slider
                  value={[animationState.currentStep]}
                  onValueChange={handleStepChange}
                  max={animationState.totalSteps - 1}
                  step={1}
                  className="w-full"
                />
              </div>

              {/* 速度控制 */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm text-gray-600">
                  <span>播放速度</span>
                  <span>{animationState.speed}x</span>
                </div>
                <Slider
                  value={[animationState.speed]}
                  onValueChange={handleSpeedChange}
                  min={0.5}
                  max={3.0}
                  step={0.5}
                  className="w-full"
                />
              </div>
            </div>
          </div>
        )}

        {/* 设置面板 */}
        {animationState.showSettings && (
          <div className="absolute top-16 right-4 bg-white border rounded-lg shadow-lg p-4 z-10">
            <h4 className="font-medium text-gray-900 mb-3">动画设置</h4>
            <div className="space-y-3">
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={animationState.isMuted}
                  onChange={(e) =>
                    setAnimationState((prev) => ({
                      ...prev,
                      isMuted: e.target.checked,
                    }))
                  }
                  className="rounded"
                />
                <span className="text-sm text-gray-700">静音</span>
              </label>
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  defaultChecked={true}
                  className="rounded"
                />
                <span className="text-sm text-gray-700">显示标签</span>
              </label>
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  defaultChecked={true}
                  className="rounded"
                />
                <span className="text-sm text-gray-700">显示网格</span>
              </label>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

// 移动平均线动画组件
function MovingAverageAnimation({
  data,
  options,
}: {
  data: any;
  options: any;
}) {
  return (
    <div className="relative h-full">
      <Line data={data} options={options} />
      <div className="absolute top-4 left-4 bg-blue-50 border border-blue-200 rounded-lg p-3">
        <h4 className="font-medium text-blue-900 mb-1">移动平均线计算</h4>
        <p className="text-sm text-blue-700">MA = (P1 + P2 + ... + Pn) / n</p>
        <p className="text-xs text-blue-600 mt-1">
          红线: 10日均线 | 绿线: 20日均线
        </p>
      </div>
    </div>
  );
}

// 金叉动画组件
function GoldenCrossAnimation({ data, options }: { data: any; options: any }) {
  return (
    <div className="relative h-full">
      <Line data={data} options={options} />
      <div className="absolute top-4 left-4 bg-green-50 border border-green-200 rounded-lg p-3">
        <h4 className="font-medium text-green-900 mb-1">金叉信号 📈</h4>
        <p className="text-sm text-green-700">短期均线上穿长期均线</p>
        <p className="text-xs text-green-600 mt-1">买入信号 - 看涨趋势</p>
      </div>
    </div>
  );
}

// 死叉动画组件
function DeathCrossAnimation({ data, options }: { data: any; options: any }) {
  return (
    <div className="relative h-full">
      <Line data={data} options={options} />
      <div className="absolute top-4 left-4 bg-red-50 border border-red-200 rounded-lg p-3">
        <h4 className="font-medium text-red-900 mb-1">死叉信号 📉</h4>
        <p className="text-sm text-red-700">短期均线下穿长期均线</p>
        <p className="text-xs text-red-600 mt-1">卖出信号 - 看跌趋势</p>
      </div>
    </div>
  );
}

// 交易信号生成动画组件
function SignalGenerationAnimation({
  data,
  options,
}: {
  data: any;
  options: any;
}) {
  return (
    <div className="relative h-full">
      <Line data={data} options={options} />
      <div className="absolute top-4 left-4 bg-purple-50 border border-purple-200 rounded-lg p-3">
        <h4 className="font-medium text-purple-900 mb-1">交易信号生成</h4>
        <p className="text-sm text-purple-700">基于均线交叉的自动信号</p>
        <p className="text-xs text-purple-600 mt-1">
          绿三角: 金叉买入 | 红三角: 死叉卖出
        </p>
      </div>
    </div>
  );
}
