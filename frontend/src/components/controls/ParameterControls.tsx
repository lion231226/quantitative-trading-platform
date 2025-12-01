'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  ParameterChangeEvent,
  ParameterPreset,
  ParameterValidationResult,
  StrategyParameters,
  UserPreferences,
} from '@/types/parameter.types';
import {
  DEFAULT_PARAMETERS,
  formatParameterValue,
  getParameterRiskAssessment,
  validateAllParameters,
} from '@/utils/parameterHelpers';
import MovingAverageSlider from './MovingAverageSlider';
import PercentageInput from './PercentageInput';
import ParameterPresets from './ParameterPresets';
import {
  ChevronDown,
  ChevronUp,
  RotateCcw,
  Save,
  Settings,
  Shield,
  Sliders,
  Target,
  TrendingUp,
  Zap,
} from 'lucide-react';

interface ParameterControlsProps {
  parameters: StrategyParameters;
  onParametersChange: (parameters: StrategyParameters) => void;
  onParameterChange?: (event: ParameterChangeEvent) => void;
  onReset?: () => void;
  onSave?: (parameters: StrategyParameters) => void;
  disabled?: boolean;
  showPresets?: boolean;
  showAdvanced?: boolean;
  compact?: boolean;
  allowCustomPresets?: boolean;
  className?: string;
}

// 导出默认参数值供其他组件使用
export { DEFAULT_PARAMETERS };

// 预设参数配置
const PARAMETER_PRESETS: ParameterPreset[] = [
  {
    id: 'conservative',
    name: '保守策略',
    description: '长期均线，严格风险控制',
    parameters: {
      movingAveragePeriod: 50,
      stopLoss: 3.0,
      takeProfit: 6.0,
    },
  },
  {
    id: 'balanced',
    name: '平衡策略',
    description: '中等周期，平衡风险收益',
    parameters: {
      movingAveragePeriod: 20,
      stopLoss: 5.0,
      takeProfit: 10.0,
    },
  },
  {
    id: 'aggressive',
    name: '激进策略',
    description: '短期均线，高风险高收益',
    parameters: {
      movingAveragePeriod: 10,
      stopLoss: 2.0,
      takeProfit: 15.0,
    },
  },
  {
    id: 'scalping',
    name: '剥头皮策略',
    description: '超短期，快速交易',
    parameters: {
      movingAveragePeriod: 5,
      stopLoss: 1.0,
      takeProfit: 2.0,
    },
  },
];

export function ParameterControls({
  parameters = DEFAULT_PARAMETERS,
  onParametersChange,
  onParameterChange,
  onReset,
  onSave,
  disabled = false,
  showPresets = true,
  showAdvanced = false,
  compact = false,
  allowCustomPresets = false,
  className = '',
}: ParameterControlsProps) {
  const [localParameters, setLocalParameters] =
    useState<StrategyParameters>(parameters);
  const [showAdvancedSettings, setShowAdvancedSettings] =
    useState(showAdvanced);
  const [isDirty, setIsDirty] = useState(false);

  // 同步外部参数变化
  useEffect(() => {
    setLocalParameters(parameters);
    setIsDirty(false);
  }, [parameters]);

  // 使用外部验证工具
  const validation = useMemo(
    () => validateAllParameters(localParameters),
    [localParameters],
  );

  // 获取风险评估
  const riskAssessment = useMemo(
    () => getParameterRiskAssessment(localParameters),
    [localParameters],
  );

  // 处理参数变化
  const handleParameterChange = useCallback(
    (parameter: keyof StrategyParameters, value: number) => {
      const previousValue = localParameters[parameter];

      const newParameters = {
        ...localParameters,
        [parameter]: value,
      };

      setLocalParameters(newParameters);
      setIsDirty(true);

      // 通知父组件
      onParametersChange(newParameters);

      onParameterChange?.({
        parameter,
        value,
        previousValue,
      });
    },
    [localParameters, onParametersChange, onParameterChange],
  );

  // 应用预设
  const applyPreset = useCallback(
    (preset: ParameterPreset) => {
      setLocalParameters(preset.parameters);
      setIsDirty(true);
      onParametersChange(preset.parameters);
    },
    [onParametersChange],
  );

  // 重置参数
  const handleReset = useCallback(() => {
    setLocalParameters(DEFAULT_PARAMETERS);
    setIsDirty(true);
    onParametersChange(DEFAULT_PARAMETERS);
    onReset?.();
  }, [onParametersChange, onReset]);

  // 保存参数
  const handleSave = useCallback(() => {
    if (validation.isValid) {
      setIsDirty(false);
      onSave?.(localParameters);
    }
  }, [localParameters, validation, onSave]);

  if (compact) {
    return (
      <div
        className={`flex items-center space-x-4 p-4 bg-background border rounded-lg ${className}`}
      >
        <div className="flex items-center space-x-2">
          <Sliders className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">策略参数</span>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <label className="text-xs text-muted-foreground">周期:</label>
            <span className="text-sm font-mono">
              {localParameters.movingAveragePeriod}
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <label className="text-xs text-muted-foreground">止损:</label>
            <span className="text-sm font-mono">
              {localParameters.stopLoss}%
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <label className="text-xs text-muted-foreground">止盈:</label>
            <span className="text-sm font-mono">
              {localParameters.takeProfit}%
            </span>
          </div>
        </div>

        {isDirty && (
          <Button
            size="sm"
            variant="outline"
            onClick={handleSave}
            disabled={disabled || !validation.isValid}
          >
            <Save className="h-3 w-3 mr-1" />
            保存
          </Button>
        )}
      </div>
    );
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center space-x-2">
            <Sliders className="h-5 w-5" />
            <span>策略参数配置</span>
          </CardTitle>
          <div className="flex items-center space-x-2">
            {isDirty && (
              <Button
                size="sm"
                variant="outline"
                onClick={handleSave}
                disabled={disabled || !validation.isValid}
              >
                <Save className="h-4 w-4 mr-1" />
                保存
              </Button>
            )}
            <Button
              size="sm"
              variant="ghost"
              onClick={handleReset}
              disabled={disabled}
            >
              <RotateCcw className="h-4 w-4 mr-1" />
              重置
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* 参数预设管理 */}
        {showPresets && (
          <ParameterPresets
            parameters={localParameters}
            onPresetSelect={applyPreset}
            disabled={disabled}
            allowCustomPresets={allowCustomPresets}
          />
        )}

        {/* 参数控制组件 */}
        <div className="space-y-6">
          {/* 移动平均周期滑块 */}
          <MovingAverageSlider
            value={localParameters.movingAveragePeriod}
            onChange={(value) =>
              handleParameterChange('movingAveragePeriod', value)
            }
            disabled={disabled}
            showAdvanced={showAdvancedSettings}
          />

          {/* 止损输入 */}
          <PercentageInput
            label="止损设置"
            value={localParameters.stopLoss}
            onChange={(value) => handleParameterChange('stopLoss', value)}
            min={0}
            max={50}
            step={0.1}
            precision={1}
            disabled={disabled}
            type="stopLoss"
            showAdvanced={showAdvancedSettings}
          />

          {/* 止盈输入 */}
          <PercentageInput
            label="止盈设置"
            value={localParameters.takeProfit}
            onChange={(value) => handleParameterChange('takeProfit', value)}
            min={0}
            max={50}
            step={0.1}
            precision={1}
            disabled={disabled}
            type="takeProfit"
            showAdvanced={showAdvancedSettings}
          />
        </div>

        {/* 高级设置 */}
        <div className="space-y-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowAdvancedSettings(!showAdvancedSettings)}
            disabled={disabled}
            className="flex items-center space-x-2"
          >
            <Settings className="h-4 w-4" />
            <span>高级设置</span>
            {showAdvancedSettings ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>

          {showAdvancedSettings && (
            <div className="border rounded-lg p-4 space-y-6">
              {/* 风险评估 */}
              <div className="space-y-3">
                <h4 className="text-sm font-medium flex items-center space-x-2">
                  <Target className="h-4 w-4" />
                  <span>风险评估</span>
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Card
                    className={`p-3 ${
                      riskAssessment.level === 'low'
                        ? 'border-green-200 bg-green-50'
                        : riskAssessment.level === 'medium'
                          ? 'border-yellow-200 bg-yellow-50'
                          : riskAssessment.level === 'high'
                            ? 'border-orange-200 bg-orange-50'
                            : 'border-red-200 bg-red-50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">风险等级</span>
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${
                          riskAssessment.level === 'low'
                            ? 'bg-green-100 text-green-800'
                            : riskAssessment.level === 'medium'
                              ? 'bg-yellow-100 text-yellow-800'
                              : riskAssessment.level === 'high'
                                ? 'bg-orange-100 text-orange-800'
                                : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {riskAssessment.level === 'low'
                          ? '低风险'
                          : riskAssessment.level === 'medium'
                            ? '中等风险'
                            : riskAssessment.level === 'high'
                              ? '高风险'
                              : '极高风险'}
                      </span>
                    </div>
                    <div className="text-lg font-semibold">
                      {riskAssessment.score}/100
                    </div>
                  </Card>

                  <Card className="p-3">
                    <div className="text-sm font-medium mb-2">参数配置</div>
                    <div className="space-y-1 text-sm text-muted-foreground">
                      <div>均线: {localParameters.movingAveragePeriod}天</div>
                      <div>止损: {localParameters.stopLoss}%</div>
                      <div>止盈: {localParameters.takeProfit}%</div>
                    </div>
                  </Card>

                  <Card className="p-3">
                    <div className="text-sm font-medium mb-2">收益风险比</div>
                    <div className="text-lg font-semibold text-blue-600">
                      {localParameters.stopLoss > 0
                        ? (
                            localParameters.takeProfit /
                            localParameters.stopLoss
                          ).toFixed(2)
                        : 'N/A'}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {localParameters.stopLoss > 0 &&
                      localParameters.takeProfit / localParameters.stopLoss >= 2
                        ? '良好'
                        : '建议2:1以上'}
                    </div>
                  </Card>
                </div>

                {riskAssessment.factors.length > 0 && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                    <div className="flex items-start space-x-2">
                      <Target className="h-4 w-4 text-yellow-600 mt-0.5" />
                      <div className="text-sm text-yellow-800">
                        <p className="font-medium mb-1">风险因素</p>
                        <ul className="space-y-1">
                          {riskAssessment.factors.map((factor, index) => (
                            <li key={index}>• {factor}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* 参数说明 */}
              <div className="text-sm text-muted-foreground space-y-2">
                <p>
                  • <strong>移动平均周期:</strong> 计算均线所用的历史数据天数
                </p>
                <p>
                  • <strong>止损:</strong> 当价格下跌超过此百分比时卖出
                </p>
                <p>
                  • <strong>止盈:</strong> 当价格上涨超过此百分比时卖出
                </p>
              </div>
            </div>
          )}
        </div>

        {/* 验证错误和警告 */}
        {!validation.isValid && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <div className="text-sm text-red-800">
              <p className="font-medium mb-1">参数错误:</p>
              <ul className="list-disc list-inside space-y-1">
                {validation.errors.map((error, index) => (
                  <li key={index}>{error}</li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {validation.warnings.length > 0 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
            <div className="text-sm text-yellow-800">
              <p className="font-medium mb-1">参数建议:</p>
              <ul className="list-disc list-inside space-y-1">
                {validation.warnings.map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default ParameterControls;
