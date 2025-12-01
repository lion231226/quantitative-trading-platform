'use client';

import React, { useCallback, useMemo, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  TrendingUp,
  Zap,
} from 'lucide-react';

interface MovingAverageSliderProps {
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
  showAdvanced?: boolean;
  className?: string;
}

// 移动平均线类型描述
const MA_DESCRIPTIONS = {
  5: {
    type: '超短期',
    description: '剥头皮交易，对价格变化极其敏感',
    risk: '极高',
  },
  10: { type: '短期', description: '快速交易，适合高波动性市场', risk: '高' },
  20: { type: '中短期', description: '平衡信号频率和稳定性', risk: '中等' },
  50: { type: '中期', description: '稳定信号，减少噪音干扰', risk: '中等偏低' },
  100: { type: '中长期', description: '趋势跟踪，适合趋势市场', risk: '低' },
  200: {
    type: '长期',
    description: '主要趋势判断，信号较少但可靠',
    risk: '低',
  },
};

// 快速选择预设
const QUICK_PRESETS = [
  { label: '5日', value: 5, icon: Zap },
  { label: '10日', value: 10, icon: Activity },
  { label: '20日', value: 20, icon: BarChart3 },
  { label: '50日', value: 50, icon: TrendingUp },
  { label: '100日', value: 100, icon: TrendingUp },
  { label: '200日', value: 200, icon: TrendingUp },
];

export function MovingAverageSlider({
  value,
  onChange,
  disabled = false,
  showAdvanced = false,
  className = '',
}: MovingAverageSliderProps) {
  const [isDragging, setIsDragging] = useState(false);

  // 获取当前值的描述
  const currentDescription = useMemo(() => {
    const nearestValue = Object.keys(MA_DESCRIPTIONS)
      .map(Number)
      .reduce((prev, curr) =>
        Math.abs(curr - value) < Math.abs(prev - value) ? curr : prev,
      );

    return (
      MA_DESCRIPTIONS[nearestValue as keyof typeof MA_DESCRIPTIONS] || {
        type: '自定义',
        description: '根据市场条件自定义设置',
        risk: '中等',
      }
    );
  }, [value]);

  // 获取风险等级颜色
  const getRiskColor = useCallback((risk: string) => {
    switch (risk) {
      case '极高':
        return 'text-red-600 bg-red-50';
      case '高':
        return 'text-orange-600 bg-orange-50';
      case '中等':
        return 'text-yellow-600 bg-yellow-50';
      case '中等偏低':
        return 'text-blue-600 bg-blue-50';
      case '低':
        return 'text-green-600 bg-green-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  }, []);

  // 处理滑块变化
  const handleChange = useCallback(
    (newValue: number) => {
      const roundedValue = Math.round(newValue);
      onChange(roundedValue);
    },
    [onChange],
  );

  // 处理快速选择
  const handleQuickSelect = useCallback(
    (presetValue: number) => {
      onChange(presetValue);
    },
    [onChange],
  );

  // 计算滑块位置百分比
  const sliderPercentage = ((value - 5) / (200 - 5)) * 100;

  return (
    <Card className={className}>
      <CardContent className="p-6">
        {/* 标题和当前值 */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <TrendingUp className="h-5 w-5 text-blue-600" />
            <div>
              <h3 className="text-lg font-semibold">移动平均周期</h3>
              <p className="text-sm text-muted-foreground">
                计算移动平均线所用的历史数据天数
              </p>
            </div>
          </div>
          <div className="text-right">
            <div
              data-testid="current-value"
              className="text-2xl font-bold text-blue-600"
            >
              {value}
            </div>
            <div className="text-sm text-muted-foreground">天</div>
          </div>
        </div>

        {/* 主滑块 */}
        <div className="space-y-4">
          <div className="relative">
            <input
              type="range"
              min="5"
              max="200"
              step="1"
              value={value}
              onChange={(e) => handleChange(parseInt(e.target.value))}
              onMouseDown={() => setIsDragging(true)}
              onMouseUp={() => setIsDragging(false)}
              onTouchStart={() => setIsDragging(true)}
              onTouchEnd={() => setIsDragging(false)}
              disabled={disabled}
              className="w-full h-3 bg-gray-200 rounded-lg appearance-none cursor-pointer slider-thumb"
              style={{
                background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${sliderPercentage}%, #e5e7eb ${sliderPercentage}%, #e5e7eb 100%)`,
              }}
            />

            {/* 滑块刻度 */}
            <div className="flex justify-between text-xs text-muted-foreground mt-2">
              <span>5</span>
              <span>50</span>
              <span>100</span>
              <span>150</span>
              <span>200</span>
            </div>
          </div>

          {/* 快速选择按钮 */}
          <div className="space-y-3">
            <p className="text-sm font-medium text-muted-foreground">
              快速选择
            </p>
            <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
              {QUICK_PRESETS.map((preset) => {
                const Icon = preset.icon;
                const isActive = value === preset.value;
                return (
                  <Button
                    key={preset.value}
                    variant={isActive ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => handleQuickSelect(preset.value)}
                    disabled={disabled}
                    className="flex flex-col items-center space-y-1 h-auto py-3"
                  >
                    <Icon className="h-4 w-4" />
                    <span className="text-xs">{preset.label}</span>
                  </Button>
                );
              })}
            </div>
          </div>
        </div>

        {/* 高级信息 */}
        {showAdvanced && (
          <div className="mt-6 pt-6 border-t space-y-4">
            {/* 当前设置说明 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="p-4">
                <div className="flex items-center space-x-2 mb-2">
                  <BarChart3 className="h-4 w-4 text-blue-600" />
                  <span className="font-medium text-sm">类型</span>
                </div>
                <div className="text-lg font-semibold">
                  {currentDescription.type}
                </div>
                <div className="text-sm text-muted-foreground mt-1">
                  {currentDescription.description}
                </div>
              </Card>

              <Card className="p-4">
                <div className="flex items-center space-x-2 mb-2">
                  <AlertTriangle className="h-4 w-4 text-orange-600" />
                  <span className="font-medium text-sm">风险等级</span>
                </div>
                <div
                  className={`inline-flex px-3 py-1 rounded-full text-sm font-medium ${getRiskColor(currentDescription.risk)}`}
                >
                  {currentDescription.risk}
                </div>
              </Card>

              <Card className="p-4">
                <div className="flex items-center space-x-2 mb-2">
                  <Activity className="h-4 w-4 text-green-600" />
                  <span className="font-medium text-sm">预期信号</span>
                </div>
                <div className="text-lg font-semibold">
                  {value <= 10 ? '频繁' : value <= 50 ? '中等' : '稀少'}
                </div>
                <div className="text-sm text-muted-foreground mt-1">
                  基于{value}日周期的信号频率
                </div>
              </Card>
            </div>

            {/* 使用建议 */}
            <Card className="bg-blue-50 border-blue-200">
              <CardContent className="p-4">
                <div className="flex items-start space-x-3">
                  <TrendingUp className="h-5 w-5 text-blue-600 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-blue-900 mb-2">使用建议</h4>
                    <ul className="text-sm text-blue-800 space-y-1">
                      <li>
                        • <strong>5-10日:</strong> 适合短线交易和高频交易策略
                      </li>
                      <li>
                        • <strong>20-50日:</strong> 平衡策略，适合大多数市场条件
                      </li>
                      <li>
                        • <strong>100-200日:</strong> 长期趋势跟踪，降低交易频率
                      </li>
                      <li>
                        • <strong>建议:</strong>{' '}
                        新手建议从20-50日开始，根据经验调整
                      </li>
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* 性能提示 */}
            {value < 20 && (
              <Card className="bg-yellow-50 border-yellow-200">
                <CardContent className="p-4">
                  <div className="flex items-start space-x-3">
                    <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5" />
                    <div>
                      <h4 className="font-medium text-yellow-900 mb-1">
                        性能提示
                      </h4>
                      <p className="text-sm text-yellow-800">
                        短期均线（{value}日）会产生更多交易信号，可能增加：
                      </p>
                      <ul className="text-sm text-yellow-800 mt-2 space-y-1">
                        <li>• 交易成本（手续费、滑点）</li>
                        <li>• 市场噪音干扰的风险</li>
                        <li>• 过度交易的可能性</li>
                      </ul>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default MovingAverageSlider;
