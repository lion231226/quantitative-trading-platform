'use client';

import React, { useCallback, useMemo, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  AlertTriangle,
  CheckCircle,
  Shield,
  Target,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';

interface PercentageInputProps {
  label: string
  value: number
  onChange: (value: number) => void
  min?: number
  max?: number
  step?: number
  precision?: number
  disabled?: boolean
  type?: 'stopLoss' | 'takeProfit'
  showAdvanced?: boolean
  className?: string
}

// 常用的百分比预设
const COMMON_PRESETS = [1, 2, 3, 5, 8, 10, 15, 20, 25, 30];

// 止损/止盈建议配置
const RISK_CONFIG = {
  stopLoss: {
    conservative: { label: '保守', range: [1, 3], color: 'green', description: '严格风险控制' },
    moderate: { label: '适中', range: [3, 7], color: 'blue', description: '平衡风险收益' },
    aggressive: { label: '激进', range: [7, 15], color: 'orange', description: '较高风险承受' },
  },
  takeProfit: {
    conservative: { label: '保守', range: [5, 10], color: 'green', description: '稳健收益目标' },
    moderate: { label: '适中', range: [10, 20], color: 'blue', description: '合理收益预期' },
    aggressive: { label: '激进', range: [20, 50], color: 'orange', description: '高收益目标' },
  },
};

export function PercentageInput({
  label,
  value,
  onChange,
  min = 0,
  max = 50,
  step = 0.1,
  precision = 1,
  disabled = false,
  type = 'stopLoss',
  showAdvanced = false,
  className = '',
}: PercentageInputProps) {
  const [inputValue, setInputValue] = useState(value.toString());
  const [isFocused, setIsFocused] = useState(false);

  // 同步外部值变化
  React.useEffect(() => {
    setInputValue(value.toFixed(precision));
  }, [value, precision]);

  // 获取图标
  const getIcon = useCallback(() => {
    switch (type) {
      case 'stopLoss':
        return Shield;
      case 'takeProfit':
        return Target;
      default:
        return Shield;
    }
  }, [type]);

  // 获取风险等级
  const getRiskLevel = useCallback((val: number) => {
    const config = RISK_CONFIG[type];

    for (const [level, settings] of Object.entries(config)) {
      const [minRange, maxRange] = settings.range;
      if (val >= minRange && val <= maxRange) {
        return { level, ...settings };
      }
    }

    return { level: 'custom', color: 'gray', description: '自定义设置', label: '自定义' };
  }, [type]);

  // 验证输入值
  const validateInput = useCallback((input: string): number | null => {
    const num = parseFloat(input);

    if (isNaN(num)) return null;
    if (num < min || num > max) return null;

    // 应用步进和精度
    const stepped = Math.round(num / step) * step;
    const precisioned = Math.round(stepped * Math.pow(10, precision)) / Math.pow(10, precision);

    return Math.max(min, Math.min(max, precisioned));
  }, [min, max, step, precision]);

  // 处理输入变化
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setInputValue(newValue);

    const validatedValue = validateInput(newValue);
    if (validatedValue !== null) {
      onChange(validatedValue);
    }
  }, [validateInput, onChange]);

  // 处理焦点事件
  const handleFocus = useCallback(() => {
    setIsFocused(true);
  }, []);

  const handleBlur = useCallback(() => {
    setIsFocused(false);
    const validatedValue = validateInput(inputValue);
    if (validatedValue !== null) {
      setInputValue(validatedValue.toFixed(precision));
      onChange(validatedValue);
    } else {
      setInputValue(value.toFixed(precision));
    }
  }, [inputValue, value, precision, validateInput, onChange]);

  // 处理预设选择
  const handlePresetClick = useCallback((preset: number) => {
    setInputValue(preset.toFixed(precision));
    onChange(preset);
  }, [onChange, precision]);

  // 处理增加/减少
  const handleStep = useCallback((direction: 'increase' | 'decrease') => {
    const newValue = direction === 'increase' ? value + step : value - step;
    const clampedValue = Math.max(min, Math.min(max, newValue));
    const precisionedValue = Math.round(clampedValue * Math.pow(10, precision)) / Math.pow(10, precision);

    setInputValue(precisionedValue.toFixed(precision));
    onChange(precisionedValue);
  }, [value, step, min, max, precision, onChange]);

  const Icon = getIcon();
  const riskLevel = getRiskLevel(value);

  // 检查是否有输入错误
  const hasError = !isFocused && validateInput(inputValue) === null;

  return (
    <Card className={className}>
      <CardContent className="p-6">
        {/* 标题和当前值 */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <Icon className="h-5 w-5 text-blue-600" />
            <div>
              <h3 className="text-lg font-semibold">{label}</h3>
              <p className="text-sm text-muted-foreground">
                {type === 'stopLoss' ? '当价格下跌超过此百分比时卖出' : '当价格上涨超过此百分比时卖出'}
              </p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-blue-600">{value.toFixed(precision)}%</div>
            <div className="text-sm text-muted-foreground">
              <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${
                riskLevel.color === 'green' ? 'bg-green-100 text-green-800' :
                riskLevel.color === 'blue' ? 'bg-blue-100 text-blue-800' :
                riskLevel.color === 'orange' ? 'bg-orange-100 text-orange-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {riskLevel.label}
              </span>
            </div>
          </div>
        </div>

        {/* 数字输入和步进按钮 */}
        <div className="space-y-4">
          <div className="flex items-center space-x-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleStep('decrease')}
              disabled={disabled || value <= min}
              className="px-3"
            >
              -
            </Button>

            <div className="relative flex-1">
              <input
                type="text"
                value={inputValue}
                onChange={handleInputChange}
                onFocus={handleFocus}
                onBlur={handleBlur}
                disabled={disabled}
                className={`w-full text-center text-lg font-semibold border rounded-lg px-3 py-2 ${
                  hasError ? 'border-red-500 text-red-600' : 'border-gray-300'
                } focus:outline-none focus:ring-2 focus:ring-blue-500`}
                placeholder="0.0"
              />
              <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500">
                %
              </span>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => handleStep('increase')}
              disabled={disabled || value >= max}
              className="px-3"
            >
              +
            </Button>
          </div>

          {/* 滑块输入 */}
          <div className="space-y-2">
            <input
              type="range"
              min={min}
              max={max}
              step={step}
              value={value}
              onChange={(e) => onChange(parseFloat(e.target.value))}
              disabled={disabled}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
              style={{
                background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${((value - min) / (max - min)) * 100}%, #e5e7eb ${((value - min) / (max - min)) * 100}%, #e5e7eb 100%)`,
              }}
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{min}%</span>
              <span>{(max / 2).toFixed(precision)}%</span>
              <span>{max}%</span>
            </div>
          </div>
        </div>

        {/* 快速预设 */}
        <div className="mt-6 space-y-3">
          <p className="text-sm font-medium text-muted-foreground">快速选择</p>
          <div className="flex flex-wrap gap-2">
            {COMMON_PRESETS
              .filter(preset => preset >= min && preset <= max)
              .map((preset) => (
                <Button
                  key={preset}
                  variant={Math.abs(value - preset) < 0.01 ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => handlePresetClick(preset)}
                  disabled={disabled}
                  className="min-w-[3rem]"
                >
                  {preset}%
                </Button>
              ))}
          </div>
        </div>

        {/* 高级信息 */}
        {showAdvanced && (
          <div className="mt-6 pt-6 border-t space-y-4">
            {/* 风险配置 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Object.entries(RISK_CONFIG[type]).map(([level, config]) => {
                const isActive = riskLevel.level === level;
                const [minRange, maxRange] = config.range;

                return (
                  <Card key={level} className={`p-3 ${isActive ? 'ring-2 ring-blue-500' : ''}`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-sm">{config.label}</span>
                      {isActive && <CheckCircle className="h-4 w-4 text-blue-600" />}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {minRange}% - {maxRange}%
                    </div>
                    <div className="text-xs text-gray-600 mt-1">
                      {config.description}
                    </div>
                  </Card>
                );
              })}
            </div>

            {/* 使用建议 */}
            <Card className="bg-blue-50 border-blue-200">
              <CardContent className="p-4">
                <div className="flex items-start space-x-3">
                  {type === 'stopLoss' ? (
                    <TrendingDown className="h-5 w-5 text-blue-600 mt-0.5" />
                  ) : (
                    <TrendingUp className="h-5 w-5 text-blue-600 mt-0.5" />
                  )}
                  <div>
                    <h4 className="font-medium text-blue-900 mb-2">
                      {type === 'stopLoss' ? '止损设置建议' : '止盈设置建议'}
                    </h4>
                    <ul className="text-sm text-blue-800 space-y-1">
                      {type === 'stopLoss' ? (
                        <>
                          <li>• <strong>1-3%:</strong> 适合高频交易，严格控制单笔损失</li>
                          <li>• <strong>3-7%:</strong> 平衡策略，给策略一定波动空间</li>
                          <li>• <strong>7-15%:</strong> 适合趋势跟踪，容忍较大波动</li>
                          <li>• <strong>建议:</strong> 根据个人风险承受能力和交易频率调整</li>
                        </>
                      ) : (
                        <>
                          <li>• <strong>5-10%:</strong> 保守收益目标，稳定增长</li>
                          <li>• <strong>10-20%:</strong> 平衡收益预期，适合大多数市场</li>
                          <li>• <strong>20-50%:</strong> 激进收益目标，适合趋势市场</li>
                          <li>• <strong>建议:</strong> 止盈/止损比例建议保持在2:1以上</li>
                        </>
                      )}
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* 风险提示 */}
            {(value < (type === 'stopLoss' ? 2 : 5)) && (
              <Card className="bg-yellow-50 border-yellow-200">
                <CardContent className="p-4">
                  <div className="flex items-start space-x-3">
                    <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5" />
                    <div>
                      <h4 className="font-medium text-yellow-900 mb-1">风险提示</h4>
                      <p className="text-sm text-yellow-800">
                        {type === 'stopLoss' ? (
                          `止损设置过低（${value.toFixed(precision)}%）可能导致：频繁止损、增加交易成本、错过反弹机会`
                        ) : (
                          `止盈设置过低（${value.toFixed(precision)}%）可能导致：利润过早锁定、错过大趋势机会、降低整体收益`
                        )}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* 错误提示 */}
        {hasError && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center space-x-2 text-red-800">
              <AlertTriangle className="h-4 w-4" />
              <span className="text-sm">
                请输入有效的百分比数值（{min}% - {max}%）
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default PercentageInput;
