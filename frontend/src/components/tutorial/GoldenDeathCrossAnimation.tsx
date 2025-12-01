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
  ArrowDownRight,
  ArrowUpRight,
  Eye,
  EyeOff,
  Pause,
  Play,
  RotateCcw,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
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

interface GoldenDeathCrossAnimationProps {
  autoPlay?: boolean;
  showGoldenCross?: boolean;
  showDeathCross?: boolean;
  onCrossDetected?: (type: 'golden' | 'death', data: any) => void;
  onComplete?: () => void;
}

interface CrossSignal {
  type: 'golden' | 'death';
  day: number;
  price: number;
  ma10: number;
  ma20: number;
  description: string;
}

interface AnimationStep {
  day: number;
  price: number;
  ma10: number | null;
  ma20: number | null;
  cross?: CrossSignal;
  isCrossPoint?: boolean;
}

/**
 * 金叉死叉交易信号动画演示组件
 * 展示金叉死叉的形成过程和交易含义
 */
export function GoldenDeathCrossAnimation({
  autoPlay = false,
  showGoldenCross = true,
  showDeathCross = true,
  onCrossDetected,
  onComplete,
}: GoldenDeathCrossAnimationProps) {
  const [isPlaying, setIsPlaying] = useState(autoPlay);
  const [currentStep, setCurrentStep] = useState(0);
  const [animationSteps, setAnimationSteps] = useState<AnimationStep[]>([]);
  const [chartData, setChartData] = useState<any>(null);
  const [detectedCrosses, setDetectedCrosses] = useState<CrossSignal[]>([]);
  const [showMAs, setShowMAs] = useState({ ma10: true, ma20: true });
  const [speed, setSpeed] = useState(1.0);
  const intervalRef = useRef<NodeJS.Timeout>();

  // 生成价格数据
  const generatePriceData = useCallback(() => {
    const prices = [];
    let basePrice = 100;
    let trend = 0; // 趋势方向

    for (let i = 0; i < 60; i++) {
      // 创建趋势变化以便形成金叉死叉
      if (i === 15) trend = 0.8; // 上升趋势
      if (i === 35) trend = -0.6; // 下降趋势

      const change = (Math.random() - 0.5 + trend * 0.3) * 3;
      basePrice += change;
      basePrice = Math.max(80, Math.min(120, basePrice));
      prices.push(parseFloat(basePrice.toFixed(2)));
    }

    return prices;
  }, []);

  // 计算移动平均线
  const calculateMovingAverage = useCallback(
    (data: number[], period: number, index: number) => {
      if (index < period - 1) return null;

      const window = data.slice(index - period + 1, index + 1);
      return window.reduce((sum, val) => sum + val, 0) / period;
    },
    [],
  );

  // 检测金叉死叉
  const detectCross = useCallback(
    (
      data: number[],
      index: number,
      ma10: number | null,
      ma20: number | null,
      prevMa10: number | null,
      prevMa20: number | null,
    ): CrossSignal | null => {
      if (!ma10 || !ma20 || !prevMa10 || !prevMa20) return null;

      const currentDiff = ma10 - ma20;
      const prevDiff = prevMa10 - prevMa20;

      // 金叉：短期均线上穿长期均线
      if (prevDiff <= 0 && currentDiff > 0 && showGoldenCross) {
        return {
          type: 'golden',
          day: index,
          price: data[index],
          ma10,
          ma20,
          description: `金叉形成！短期均线(¥${ma10.toFixed(2)})上穿长期均线(¥${ma20.toFixed(2)})`,
        };
      }

      // 死叉：短期均线下穿长期均线
      if (prevDiff >= 0 && currentDiff < 0 && showDeathCross) {
        return {
          type: 'death',
          day: index,
          price: data[index],
          ma10,
          ma20,
          description: `死叉形成！短期均线(¥${ma10.toFixed(2)})下穿长期均线(¥${ma20.toFixed(2)})`,
        };
      }

      return null;
    },
    [showGoldenCross, showDeathCross],
  );

  // 准备动画步骤
  const prepareAnimationSteps = useCallback(() => {
    const prices = generatePriceData();
    const steps: AnimationStep[] = [];
    const crosses: CrossSignal[] = [];

    for (let i = 0; i < prices.length; i++) {
      const ma10 = calculateMovingAverage(prices, 10, i);
      const ma20 = calculateMovingAverage(prices, 20, i);
      const prevMa10 = i > 0 ? calculateMovingAverage(prices, 10, i - 1) : null;
      const prevMa20 = i > 0 ? calculateMovingAverage(prices, 20, i - 1) : null;

      const cross = detectCross(prices, i, ma10, ma20, prevMa10, prevMa20);

      if (cross) {
        crosses.push(cross);
      }

      steps.push({
        day: i,
        price: prices[i],
        ma10,
        ma20,
        cross,
        isCrossPoint: !!cross,
      });
    }

    setAnimationSteps(steps);
    setDetectedCrosses(crosses);
  }, [generatePriceData, calculateMovingAverage, detectCross]);

  // 更新图表数据
  const updateChartData = useCallback(
    (stepIndex: number) => {
      if (animationSteps.length === 0) return;

      const currentSteps = animationSteps.slice(0, stepIndex + 1);
      const labels = currentSteps.map((step) => `Day ${step.day + 1}`);
      const prices = currentSteps.map((step) => step.price);
      const ma10Data = currentSteps.map((step) => step.ma10);
      const ma20Data = currentSteps.map((step) => step.ma20);

      // 找到交叉点
      const goldenCrossPoints = currentSteps
        .filter((step) => step.cross?.type === 'golden')
        .map((step) => ({
          x: step.day + 1,
          y: step.price,
        }));

      const deathCrossPoints = currentSteps
        .filter((step) => step.cross?.type === 'death')
        .map((step) => ({
          x: step.day + 1,
          y: step.price,
        }));

      const datasets = [
        {
          label: '价格',
          data: prices,
          borderColor: 'rgb(59, 130, 246)',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderWidth: 2,
          fill: false,
          tension: 0.1,
          pointRadius: 2,
          pointHoverRadius: 6,
        },
      ];

      // 添加移动平均线
      if (showMAs.ma10) {
        datasets.push({
          label: 'MA10 (短期)',
          data: ma10Data,
          borderColor: 'rgb(239, 68, 68)',
          backgroundColor: 'transparent',
          borderWidth: 3,
          fill: false,
          tension: 0.1,
          pointRadius: 0,
          pointHoverRadius: 6,
        });
      }

      if (showMAs.ma20) {
        datasets.push({
          label: 'MA20 (长期)',
          data: ma20Data,
          borderColor: 'rgb(34, 197, 94)',
          backgroundColor: 'transparent',
          borderWidth: 3,
          fill: false,
          tension: 0.1,
          pointRadius: 0,
          pointHoverRadius: 6,
        });
      }

      // 添加交叉点标记
      if (showGoldenCross && goldenCrossPoints.length > 0) {
        datasets.push({
          label: '金叉',
          data: goldenCrossPoints,
          borderColor: 'rgb(34, 197, 94)',
          backgroundColor: 'rgb(34, 197, 94)',
          pointStyle: 'triangle',
          rotation: 0,
          radius: 12,
          pointHoverRadius: 15,
          showLine: false,
        });
      }

      if (showDeathCross && deathCrossPoints.length > 0) {
        datasets.push({
          label: '死叉',
          data: deathCrossPoints,
          borderColor: 'rgb(239, 68, 68)',
          backgroundColor: 'rgb(239, 68, 68)',
          pointStyle: 'triangle',
          rotation: 180,
          radius: 12,
          pointHoverRadius: 15,
          showLine: false,
        });
      }

      const newChartData = {
        labels,
        datasets,
      };

      setChartData(newChartData);
    },
    [animationSteps, showMAs, showGoldenCross, showDeathCross],
  );

  // 动画播放控制
  useEffect(() => {
    if (isPlaying) {
      intervalRef.current = setInterval(() => {
        setCurrentStep((prev) => {
          const nextStep = prev + 1;

          if (nextStep >= animationSteps.length) {
            setIsPlaying(false);
            onComplete?.();
            return prev;
          }

          const currentAnimation = animationSteps[nextStep];
          if (currentAnimation?.cross) {
            onCrossDetected?.(
              currentAnimation.cross.type,
              currentAnimation.cross,
            );
          }

          return nextStep;
        });
      }, 1000 / speed);
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
  }, [isPlaying, animationSteps, speed, onCrossDetected, onComplete]);

  // 步骤变化时更新图表
  useEffect(() => {
    if (animationSteps.length > 0) {
      updateChartData(currentStep);
    }
  }, [currentStep, animationSteps, updateChartData]);

  // 初始化数据
  useEffect(() => {
    prepareAnimationSteps();
  }, [prepareAnimationSteps]);

  // 控制函数
  const handlePlay = () => setIsPlaying(true);
  const handlePause = () => setIsPlaying(false);
  const handleReset = () => {
    setCurrentStep(0);
    setIsPlaying(false);
    setDetectedCrosses([]);
  };
  const handleNext = () => {
    if (currentStep < animationSteps.length - 1) {
      setCurrentStep((prev) => prev + 1);
    }
  };
  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1);
    }
  };

  const currentAnimation = animationSteps[currentStep];

  // Chart.js 配置
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      duration: isPlaying ? 500 : 0,
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
          padding: 15,
          font: {
            size: 12,
          },
        },
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: '#fff',
        bodyColor: '#fff',
        padding: 12,
        displayColors: true,
        callbacks: {
          afterLabel(context: any) {
            const index = context.dataIndex;
            if (index < animationSteps.length) {
              const step = animationSteps[index];
              if (step.cross) {
                return step.cross.description;
              }
            }
            return '';
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
          font: {
            size: 10,
          },
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
          font: {
            size: 10,
          },
        },
      },
    },
  };

  return (
    <div className="space-y-6">
      {/* 标题和统计 */}
      <div className="text-center">
        <h3 className="text-2xl font-bold text-gray-900 mb-2">
          金叉死叉信号演示
        </h3>
        <p className="text-gray-600 mb-4">观察短期均线和长期均线的交叉信号</p>

        <div className="flex justify-center space-x-6">
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-green-500 rotate-45 transform"></div>
            <span className="text-sm font-medium text-gray-700">
              金叉 (买入)
            </span>
            <Badge variant="outline" className="text-green-600">
              {detectedCrosses.filter((c) => c.type === 'golden').length} 次
            </Badge>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-red-500 rotate-45 transform"></div>
            <span className="text-sm font-medium text-gray-700">
              死叉 (卖出)
            </span>
            <Badge variant="outline" className="text-red-600">
              {detectedCrosses.filter((c) => c.type === 'death').length} 次
            </Badge>
          </div>
        </div>
      </div>

      {/* 当前交叉信号 */}
      {currentAnimation?.cross && (
        <Card
          className={`p-4 border-2 ${
            currentAnimation.cross.type === 'golden'
              ? 'border-green-300 bg-green-50'
              : 'border-red-300 bg-red-50'
          }`}
        >
          <div className="flex items-center space-x-3">
            {currentAnimation.cross.type === 'golden' ? (
              <ArrowUpRight className="h-6 w-6 text-green-600" />
            ) : (
              <ArrowDownRight className="h-6 w-6 text-red-600" />
            )}
            <div>
              <h4
                className={`font-semibold ${
                  currentAnimation.cross.type === 'golden'
                    ? 'text-green-800'
                    : 'text-red-800'
                }`}
              >
                {currentAnimation.cross.type === 'golden'
                  ? '金叉信号！'
                  : '死叉信号！'}
              </h4>
              <p
                className={`text-sm ${
                  currentAnimation.cross.type === 'golden'
                    ? 'text-green-700'
                    : 'text-red-700'
                }`}
              >
                {currentAnimation.cross.description}
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* 图表区域 */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h4 className="font-semibold text-gray-900">价格走势图</h4>
          <div className="flex items-center space-x-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                setShowMAs((prev) => ({ ...prev, ma10: !prev.ma10 }))
              }
              className={showMAs.ma10 ? 'text-red-600' : 'text-gray-400'}
            >
              <Eye className="h-4 w-4 mr-1" />
              MA10
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                setShowMAs((prev) => ({ ...prev, ma20: !prev.ma20 }))
              }
              className={showMAs.ma20 ? 'text-green-600' : 'text-gray-400'}
            >
              <Eye className="h-4 w-4 mr-1" />
              MA20
            </Button>
          </div>
        </div>

        <div style={{ height: '400px' }}>
          {chartData && <Line data={chartData} options={chartOptions} />}
        </div>

        {/* 当前数据显示 */}
        {currentAnimation && (
          <div className="mt-4 grid grid-cols-4 gap-4">
            <div className="text-center">
              <p className="text-sm text-gray-600">价格</p>
              <p className="text-lg font-bold text-blue-600">
                ¥{currentAnimation.price}
              </p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-600">MA10</p>
              <p className="text-lg font-bold text-red-600">
                {currentAnimation.ma10
                  ? `¥${currentAnimation.ma10.toFixed(2)}`
                  : '---'}
              </p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-600">MA20</p>
              <p className="text-lg font-bold text-green-600">
                {currentAnimation.ma20
                  ? `¥${currentAnimation.ma20.toFixed(2)}`
                  : '---'}
              </p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-600">差值</p>
              <p
                className={`text-lg font-bold ${
                  currentAnimation.ma10 && currentAnimation.ma20
                    ? currentAnimation.ma10 > currentAnimation.ma20
                      ? 'text-red-600'
                      : 'text-green-600'
                    : 'text-gray-400'
                }`}
              >
                {currentAnimation.ma10 && currentAnimation.ma20
                  ? `¥${(currentAnimation.ma10 - currentAnimation.ma20).toFixed(2)}`
                  : '---'}
              </p>
            </div>
          </div>
        )}
      </Card>

      {/* 控制面板 */}
      <Card className="p-4">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Button
                variant="outline"
                size="sm"
                onClick={handlePrevious}
                disabled={currentStep === 0}
              >
                上一步
              </Button>
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
              <Button
                variant="outline"
                size="sm"
                onClick={handleNext}
                disabled={currentStep === animationSteps.length - 1}
              >
                下一步
              </Button>
            </div>

            <div className="text-sm text-gray-600">
              Day {currentStep + 1} / {animationSteps.length}
            </div>
          </div>

          {/* 速度控制 */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm text-gray-600">
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

          {/* 进度条 */}
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{
                width: `${((currentStep + 1) / animationSteps.length) * 100}%`,
              }}
            ></div>
          </div>
        </div>
      </Card>
    </div>
  );
}
