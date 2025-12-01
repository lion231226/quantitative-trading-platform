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
import { Calculator, Pause, Play, RotateCcw, TrendingUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
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

interface MovingAverageCalculationProps {
  period?: number;
  autoPlay?: boolean;
  onStepChange?: (step: number, calculation: any) => void;
  onComplete?: () => void;
}

interface CalculationStep {
  step: number;
  price: number;
  window: number[];
  sum: number;
  average: number;
  formula: string;
}

/**
 * 移动平均线计算过程可视化组件
 * 展示如何一步步计算移动平均线
 */
export function MovingAverageCalculation({
  period = 5,
  autoPlay = false,
  onStepChange,
  onComplete,
}: MovingAverageCalculationProps) {
  const [isPlaying, setIsPlaying] = useState(autoPlay);
  const [currentStep, setCurrentStep] = useState(0);
  const [calculationSteps, setCalculationSteps] = useState<CalculationStep[]>(
    [],
  );
  const [chartData, setChartData] = useState<any>(null);
  const intervalRef = useRef<NodeJS.Timeout>();

  // 生成示例价格数据
  const generatePriceData = useCallback(() => {
    const prices = [];
    let basePrice = 100;

    for (let i = 0; i < 20; i++) {
      const change = (Math.random() - 0.5) * 4;
      basePrice += change;
      basePrice = Math.max(80, Math.min(120, basePrice));
      prices.push(parseFloat(basePrice.toFixed(2)));
    }

    return prices;
  }, []);

  // 计算移动平均线步骤
  const calculateSteps = useCallback(
    (prices: number[]) => {
      const steps: CalculationStep[] = [];

      for (let i = 0; i < prices.length; i++) {
        const price = prices[i];

        if (i < period - 1) {
          // 数据不足，无法计算
          steps.push({
            step: i,
            price,
            window: prices.slice(0, i + 1),
            sum: 0,
            average: 0,
            formula: `需要至少${period}个数据点`,
          });
        } else {
          // 计算移动平均
          const window = prices.slice(i - period + 1, i + 1);
          const sum = window.reduce((acc, val) => acc + val, 0);
          const average = sum / period;

          const formula = `(${window.join(' + ')}) / ${period} = ${sum.toFixed(2)} / ${period} = ${average.toFixed(2)}`;

          steps.push({
            step: i,
            price,
            window,
            sum,
            average,
            formula,
          });
        }
      }

      return steps;
    },
    [period],
  );

  // 初始化数据
  useEffect(() => {
    const prices = generatePriceData();
    const steps = calculateSteps(prices);
    setCalculationSteps(steps);
  }, [generatePriceData, calculateSteps]);

  // 更新图表数据
  const updateChartData = useCallback(
    (stepIndex: number) => {
      if (calculationSteps.length === 0) return;

      const currentSteps = calculationSteps.slice(0, stepIndex + 1);
      const labels = currentSteps.map((_, index) => `Day ${index + 1}`);
      const prices = currentSteps.map((step) => step.price);
      const averages = currentSteps.map((step) => step.average);

      const newChartData = {
        labels,
        datasets: [
          {
            label: '价格',
            data: prices,
            borderColor: 'rgb(59, 130, 246)',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            borderWidth: 3,
            fill: false,
            tension: 0.1,
            pointRadius: 5,
            pointHoverRadius: 7,
          },
          {
            label: `${period}日移动平均`,
            data: averages,
            borderColor: 'rgb(239, 68, 68)',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            borderWidth: 3,
            fill: false,
            tension: 0.1,
            pointRadius: 5,
            pointHoverRadius: 7,
          },
        ],
      };

      setChartData(newChartData);
    },
    [calculationSteps, period],
  );

  // 动画播放控制
  useEffect(() => {
    if (isPlaying) {
      intervalRef.current = setInterval(() => {
        setCurrentStep((prev) => {
          const nextStep = prev + 1;

          if (nextStep >= calculationSteps.length) {
            setIsPlaying(false);
            onComplete?.();
            return prev;
          }

          return nextStep;
        });
      }, 2000); // 每2秒一步
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
  }, [isPlaying, calculationSteps.length, onComplete]);

  // 步骤变化时更新图表
  useEffect(() => {
    if (calculationSteps.length > 0) {
      updateChartData(currentStep);
      onStepChange?.(currentStep, calculationSteps[currentStep]);
    }
  }, [currentStep, calculationSteps, updateChartData, onStepChange]);

  // 控制函数
  const handlePlay = () => setIsPlaying(true);
  const handlePause = () => setIsPlaying(false);
  const handleReset = () => {
    setCurrentStep(0);
    setIsPlaying(false);
  };
  const handleNext = () => {
    if (currentStep < calculationSteps.length - 1) {
      setCurrentStep((prev) => prev + 1);
    }
  };
  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1);
    }
  };

  // Chart.js 配置
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      duration: 1000,
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
          font: {
            size: 14,
          },
        },
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: '#fff',
        bodyColor: '#fff',
        padding: 12,
        displayColors: true,
      },
    },
    scales: {
      x: {
        display: true,
        grid: {
          display: false,
        },
        ticks: {
          font: {
            size: 12,
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
            size: 12,
          },
        },
      },
    },
  };

  const currentCalculation = calculationSteps[currentStep];

  return (
    <div className="space-y-6">
      {/* 标题和说明 */}
      <div className="text-center">
        <h3 className="text-2xl font-bold text-gray-900 mb-2">
          移动平均线计算演示
        </h3>
        <p className="text-gray-600">观看移动平均线是如何一步步计算出来的</p>
      </div>

      {/* 计算过程展示 */}
      {currentCalculation && (
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-lg font-semibold text-gray-900">
              计算步骤 {currentCalculation.step + 1}
            </h4>
            <Badge variant="outline">Day {currentCalculation.step + 1}</Badge>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* 左侧：计算详情 */}
            <div className="space-y-4">
              <div>
                <h5 className="font-medium text-gray-900 mb-2">当前价格</h5>
                <div className="text-3xl font-bold text-blue-600">
                  ¥{currentCalculation.price}
                </div>
              </div>

              {currentCalculation.step >= period - 1 ? (
                <div className="space-y-3">
                  <div>
                    <h5 className="font-medium text-gray-900 mb-2">计算窗口</h5>
                    <div className="flex flex-wrap gap-2">
                      {currentCalculation.window.map((price, index) => (
                        <span
                          key={index}
                          className={`px-2 py-1 rounded text-sm font-medium ${
                            index === currentCalculation.window.length - 1
                              ? 'bg-blue-100 text-blue-800 border-2 border-blue-300'
                              : 'bg-gray-100 text-gray-700'
                          }`}
                        >
                          ¥{price}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h5 className="font-medium text-gray-900 mb-2">计算过程</h5>
                    <div className="bg-gray-50 p-3 rounded-lg font-mono text-sm">
                      {currentCalculation.formula}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <h5 className="font-medium text-gray-900 mb-1">总和</h5>
                      <div className="text-xl font-bold text-gray-700">
                        ¥{currentCalculation.sum.toFixed(2)}
                      </div>
                    </div>
                    <div>
                      <h5 className="font-medium text-gray-900 mb-1">平均值</h5>
                      <div className="text-xl font-bold text-red-600">
                        ¥{currentCalculation.average.toFixed(2)}
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <div className="flex items-center space-x-2 text-yellow-800">
                    <Calculator className="h-5 w-5" />
                    <span className="font-medium">
                      需要至少 {period} 个数据点才能计算移动平均
                    </span>
                  </div>
                  <p className="text-sm text-yellow-700 mt-2">
                    当前已收集 {currentCalculation.step + 1} 个数据点
                  </p>
                </div>
              )}
            </div>

            {/* 右侧：图表 */}
            <div className="bg-gray-50 rounded-lg p-4">
              <h5 className="font-medium text-gray-900 mb-3">价格走势图</h5>
              <div style={{ height: '300px' }}>
                {chartData && <Line data={chartData} options={chartOptions} />}
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* 控制面板 */}
      <Card className="p-4">
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
              disabled={currentStep === calculationSteps.length - 1}
            >
              下一步
            </Button>
          </div>

          <div className="flex items-center space-x-4">
            <div className="text-sm text-gray-600">
              步骤: {currentStep + 1} / {calculationSteps.length}
            </div>
            <div className="flex items-center space-x-2">
              <TrendingUp className="h-4 w-4 text-green-600" />
              <span className="text-sm font-medium text-gray-900">
                {period}日移动平均
              </span>
            </div>
          </div>
        </div>

        {/* 进度条 */}
        <div className="mt-4">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{
                width: `${((currentStep + 1) / calculationSteps.length) * 100}%`,
              }}
            ></div>
          </div>
        </div>
      </Card>
    </div>
  );
}
