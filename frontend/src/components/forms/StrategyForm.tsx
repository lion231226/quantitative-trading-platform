'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Loading } from '@/components/ui/loading';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { strategyAPI } from '@/lib/api';
import { formatValidationErrors } from '@/lib/validation';
import {
  StrategyType,
  SingleMovingAverageParams,
  StrategyParameterMeta
} from '@/types/strategy';
import { StrategyConfig } from '@/types/api';
import {
  DEFAULT_STRATEGY_PARAMS,
  STRATEGY_PARAMETER_META,
  STRATEGY_PRESETS,
  validateStrategyParams,
  formatParamValue,
  getParametersByCategory,
  safeGetValue
} from '@/utils/strategyParams';
import {
  STRATEGY_TYPES,
  getStrategyConfig
} from '@/constants/strategyTypes';
import { cn } from '@/lib/utils';
import { ParameterInput } from './ParameterInput';
import { StrategyTypeSelectorSimple } from './StrategyTypeSelectorSimple';

interface StrategyFormProps {
  onParamsChange: (strategyType: StrategyType, params: SingleMovingAverageParams) => void
  initialStrategyType?: StrategyType
  initialParams?: SingleMovingAverageParams
  className?: string
}

export function StrategyForm({
  onParamsChange,
  initialStrategyType = 'single_ma',
  initialParams,
  className
}: StrategyFormProps) {
  const [strategies, setStrategies] = useState<StrategyConfig[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<StrategyType>(initialStrategyType);
  const [params, setParams] = useState<SingleMovingAverageParams>(
    initialParams || DEFAULT_STRATEGY_PARAMS
  );
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<string>('basic');

  useEffect(() => {
    loadStrategies();
  }, []);

  useEffect(() => {
    onParamsChange(selectedStrategy, params);
  }, [selectedStrategy, params]); // 移除onParamsChange依赖避免无限循环

  const loadStrategies = async () => {
    try {
      setLoading(true);
      const data = await strategyAPI.getStrategies();
      setStrategies(data);
      setErrors([]);
    } catch (err) {
      setErrors([err instanceof Error ? err.message : '加载策略列表失败']);
      console.error('Failed to load strategies:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleParamChange = (key: keyof SingleMovingAverageParams, value: any) => {
    const newParams = { ...params, [key]: value };
    setParams(newParams);

    // 实时验证
    const validation = validateStrategyParams(newParams);
    if (!validation.isValid) {
      setErrors(validation.errors);
    } else {
      setErrors([]);
    }

    onParamsChange(selectedStrategy, newParams);
  };

  const handleStrategySelect = (strategyType: StrategyType) => {
    setSelectedStrategy(strategyType);
    // 根据策略类型设置默认参数
    const defaultParams = { ...DEFAULT_STRATEGY_PARAMS };
    setParams(defaultParams);
    onParamsChange(strategyType, defaultParams);
  };

  const handlePresetSelect = (presetKey: keyof typeof STRATEGY_PRESETS) => {
    const preset = STRATEGY_PRESETS[presetKey];
    setParams(preset.params);
    onParamsChange(selectedStrategy, preset.params);
    setErrors([]);
  };

  const handleQuickParam = (key: keyof SingleMovingAverageParams, value: any) => {
    handleParamChange(key, value);
  };

  if (loading) {
    return (
      <Card className={cn('', className)}>
        <CardHeader>
          <CardTitle>策略参数配置</CardTitle>
          <CardDescription>配置策略参数以进行回测分析</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loading text="加载策略配置..." />
          </div>
        </CardContent>
      </Card>
    );
  }

  const { categories, categorizedParams } = getParametersByCategory();

  return (
    <Card className={cn('', className)}>
      <CardHeader>
        <CardTitle>策略参数配置</CardTitle>
        <CardDescription>选择策略类型并配置参数以进行回测分析</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* 策略类型选择 */}
        <StrategyTypeSelectorSimple
          selectedStrategy={selectedStrategy}
          onStrategyChange={handleStrategySelect}
          className="mb-6"
        />

        {/* 策略预设选择（仅在可用策略时显示） */}
        {selectedStrategy === 'single_ma' && (
          <div>
            <label className="text-sm font-medium mb-2 block">策略预设</label>
            <Select value="custom" onValueChange={(value) => {
              if (value !== "custom") {
                handlePresetSelect(value as keyof typeof STRATEGY_PRESETS);
              }
            }}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="选择策略预设" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="custom">自定义参数</SelectItem>
                {Object.entries(STRATEGY_PRESETS).map(([key, preset]) => (
                  <SelectItem key={key} value={key}>
                    <div className="flex flex-col items-start">
                      <span className="font-medium">{preset.name}</span>
                      <span className="text-xs text-muted-foreground">
                        {preset.description}
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        {/* 参数配置（仅在策略可用时显示） */}
        {selectedStrategy === 'single_ma' ? (
          <div>
            <label className="text-sm font-medium mb-2 block">参数配置</label>
            <Select value={activeTab} onValueChange={setActiveTab}>
              <SelectTrigger className="w-full mb-4">
                <SelectValue placeholder="选择参数分类" />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(categories).map(([key, category]) => (
                  <SelectItem key={key} value={key}>
                    <div className="flex flex-col items-start">
                      <span className="font-medium">{category.name}</span>
                      <span className="text-xs text-muted-foreground">
                        {category.description}
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* 当前分类的参数配置 */}
            <div className="space-y-4">
              {categorizedParams[activeTab].map(({ key, meta }) => (
                <ParameterInput
                  key={key}
                  key_name={key}
                  value={params[key]}
                  meta={meta}
                  onChange={handleParamChange}
                />
              ))}
            </div>
          </div>
        ) : (
          <Alert>
            <AlertDescription>
              {selectedStrategy === 'dual_ma' && '双均线策略正在开发中，敬请期待！将支持快慢双均线交叉策略配置。'}
              {selectedStrategy === 'rsi' && 'RSI策略正在开发中，敬请期待！将支持RSI超买超卖策略配置。'}
              {selectedStrategy === 'macd' && 'MACD策略正在实验阶段，敬请期待！将支持MACD动量策略配置。'}
            </AlertDescription>
          </Alert>
        )}

        {/* 当前参数摘要 */}
        <div className="text-sm text-muted-foreground p-3 bg-muted rounded-md">
          <div className="font-medium mb-2">当前参数摘要:</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
            <div>均线周期: {params.ma_period || 20}天 ({params.ma_type || 'SMA'})</div>
            <div>初始资金: ¥{(params.initial_capital || 100000).toLocaleString()}</div>
            <div>止损: {((params.stop_loss_pct || 0.02) * 100).toFixed(1)}%</div>
            <div>止盈: {((params.take_profit_pct || 0.05) * 100).toFixed(1)}%</div>
            <div>最大仓位: {((params.max_position_size || 1.0) * 100).toFixed(0)}%</div>
            <div>确认周期: {params.confirmation_periods || 1}天</div>
            <div>每日信号: {params.max_signals_per_day || 10}个</div>
            <div>冷却时间: {params.signal_cooldown || 300}秒</div>
          </div>
        </div>

        {/* 错误提示 */}
        {errors.length > 0 && (
          <div className="text-sm text-red-600 p-3 bg-red-50 border border-red-200 rounded-md">
            <div className="font-medium mb-1">参数验证失败:</div>
            <div className="whitespace-pre-line">{formatValidationErrors(errors)}</div>
          </div>
        )}

        {/* 参数说明 */}
        <div className="text-sm text-muted-foreground p-3 bg-muted rounded-md">
          <div className="font-medium mb-1">参数说明:</div>
          <div>• 基础参数: 策略的核心配置，影响信号生成的基本逻辑</div>
          <div>• 信号确认: 确保交易信号的质量，减少假信号</div>
          <div>• 风险管理: 控制交易风险，保护资金安全</div>
          <div>• 信号过滤: 限制交易频率，避免过度交易</div>
        </div>
      </CardContent>
    </Card>
  );
}
