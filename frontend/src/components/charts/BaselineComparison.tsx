'use client';

import React, { useCallback, useMemo, useState } from 'react';
import { FundCurveData, PerformanceMetrics } from '../../types/kline.types';
import { useTheme } from '../theme/ThemeProvider';
import { fundCurveService } from '../../services/fundCurveService';

interface BaselineComparisonProps {
  strategyCurve: FundCurveData;
  priceData: Array<{ timestamp: number; price: number }>;
  onBaselineUpdate?: (
    baselineCurve: FundCurveData,
    metrics: PerformanceMetrics,
  ) => void;
  className?: string;
}

/**
 * 基准比较组件
 * 提供买入持有基准计算和对比功能
 */
const BaselineComparison: React.FC<BaselineComparisonProps> = ({
  strategyCurve,
  priceData,
  onBaselineUpdate,
  className = '',
}) => {
  const { currentTheme } = useTheme();
  const [baselineEnabled, setBaselineEnabled] = useState(true);
  const [customBaseline, setCustomBaseline] = useState<'buy-hold' | 'custom'>(
    'buy-hold',
  );
  const [customReturn, setCustomReturn] = useState(8.0); // 默认8%年化收益

  // 计算买入持有基准
  const buyAndHoldBaseline = useMemo(() => {
    if (priceData.length === 0 || !baselineEnabled) return null;

    const initialPrice = priceData[0].price;
    const initialCapital = 100000;

    const baselineData = fundCurveService.calculateBuyAndHoldBaseline(
      initialPrice,
      priceData,
      initialCapital,
    );

    return fundCurveService.createFundCurveData(
      'buy-hold-baseline',
      '买入持有基准',
      baselineData,
      `${currentTheme.colors.text}80`, // 添加透明度
      'baseline',
    );
  }, [priceData, baselineEnabled, currentTheme.colors.text]);

  // 计算自定义基准
  const customBaselineCurve = useMemo(() => {
    if (!baselineEnabled || customBaseline !== 'custom') return null;

    const startDate = Math.min(...strategyCurve.data.map((d) => d.timestamp));
    const endDate = Math.max(...strategyCurve.data.map((d) => d.timestamp));
    const daysDiff = (endDate - startDate) / (1000 * 60 * 60 * 24);

    const initialCapital = 100000;
    const annualReturn = customReturn / 100;
    const periodReturn = Math.pow(1 + annualReturn, daysDiff / 365) - 1;
    const finalValue = initialCapital * (1 + periodReturn);

    const baselineData = [
      {
        timestamp: startDate,
        value: initialCapital,
      },
      {
        timestamp: endDate,
        value: finalValue,
      },
    ];

    return fundCurveService.createFundCurveData(
      'custom-baseline',
      `自定义基准 (${customReturn}%年化)`,
      baselineData,
      `${currentTheme.colors.text}80`,
      'baseline',
    );
  }, [
    strategyCurve.data,
    baselineEnabled,
    customBaseline,
    customReturn,
    currentTheme.colors.text,
  ]);

  // 获取当前激活的基准曲线
  const activeBaseline =
    customBaseline === 'buy-hold' ? buyAndHoldBaseline : customBaselineCurve;

  // 计算相对性能指标
  const relativeMetrics = useMemo(() => {
    if (!activeBaseline) return null;

    const strategyMetrics = fundCurveService.calculateMetrics(
      strategyCurve.data,
    );
    const baselineMetrics = fundCurveService.calculateMetrics(
      activeBaseline.data,
    );

    return fundCurveService.calculateRelativeMetrics(
      strategyMetrics,
      baselineMetrics,
    );
  }, [strategyCurve.data, activeBaseline]);

  // 通知父组件基准更新
  const handleBaselineUpdate = useCallback(() => {
    if (activeBaseline) {
      const metrics = fundCurveService.calculateMetrics(activeBaseline.data);
      onBaselineUpdate?.(activeBaseline, metrics);
    }
  }, [activeBaseline, onBaselineUpdate]);

  // 当基准发生变化时，通知父组件
  React.useEffect(() => {
    handleBaselineUpdate();
  }, [handleBaselineUpdate]);

  // 格式化百分比
  const formatPercent = (value: number, decimals: number = 2): string => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`;
  };

  // 获取指标颜色
  const getMetricColor = (
    value: number,
    isHigherBetter: boolean = true,
  ): string => {
    if (value === 0) return currentTheme.colors.text;

    if (isHigherBetter) {
      return value > 0
        ? currentTheme.colors.bullish
        : currentTheme.colors.bearish;
    } else {
      return value > 0
        ? currentTheme.colors.bearish
        : currentTheme.colors.bullish;
    }
  };

  if (!activeBaseline) {
    return null;
  }

  return (
    <div
      className={`baseline-comparison ${className}`}
      style={{
        backgroundColor: currentTheme.colors.background,
        borderColor: currentTheme.colors.grid,
        color: currentTheme.colors.text,
      }}
    >
      <div
        className="p-4 border-b"
        style={{ borderColor: currentTheme.colors.grid }}
      >
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold">基准比较</h3>
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              checked={baselineEnabled}
              onChange={(e) => setBaselineEnabled(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm">启用基准</span>
          </label>
        </div>

        {/* 基准类型选择 */}
        <div className="flex space-x-4">
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="radio"
              name="baseline-type"
              value="buy-hold"
              checked={customBaseline === 'buy-hold'}
              onChange={(e) =>
                setCustomBaseline(e.target.value as 'buy-hold' | 'custom')
              }
              disabled={!baselineEnabled}
              className="border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm">买入持有</span>
          </label>
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="radio"
              name="baseline-type"
              value="custom"
              checked={customBaseline === 'custom'}
              onChange={(e) =>
                setCustomBaseline(e.target.value as 'buy-hold' | 'custom')
              }
              disabled={!baselineEnabled}
              className="border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm">自定义</span>
          </label>
        </div>

        {/* 自定义基准设置 */}
        {customBaseline === 'custom' && (
          <div className="mt-3 flex items-center space-x-2">
            <label className="text-sm">年化收益率:</label>
            <input
              type="number"
              value={customReturn}
              onChange={(e) => setCustomReturn(parseFloat(e.target.value) || 0)}
              min="-50"
              max="100"
              step="0.1"
              disabled={!baselineEnabled}
              className="w-20 px-2 py-1 text-sm border rounded"
              style={{
                borderColor: currentTheme.colors.grid,
                backgroundColor: currentTheme.colors.background,
                color: currentTheme.colors.text,
              }}
            />
            <span className="text-sm">%</span>
          </div>
        )}
      </div>

      {/* 相对性能指标 */}
      {relativeMetrics && (
        <div className="p-4">
          <h4 className="text-sm font-medium mb-3">相对表现</h4>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Alpha:</span>
              <span style={{ color: getMetricColor(relativeMetrics.alpha) }}>
                {formatPercent(relativeMetrics.alpha)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Beta:</span>
              <span style={{ color: currentTheme.colors.text }}>
                {relativeMetrics.beta.toFixed(3)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">信息比率:</span>
              <span
                style={{
                  color: getMetricColor(relativeMetrics.informationRatio),
                }}
              >
                {relativeMetrics.informationRatio.toFixed(3)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">跟踪误差:</span>
              <span style={{ color: currentTheme.colors.text }}>
                {formatPercent(relativeMetrics.trackingError)}
              </span>
            </div>
          </div>

          {/* 基准说明 */}
          <div className="mt-4 text-xs text-gray-500">
            <div className="mb-1">
              <strong>Alpha:</strong> 策略相对于基准的超额收益
            </div>
            <div className="mb-1">
              <strong>Beta:</strong> 策略相对于基准的波动性比率
            </div>
            <div className="mb-1">
              <strong>信息比率:</strong> 单位跟踪风险的超额收益
            </div>
            <div>
              <strong>跟踪误差:</strong> 策略与基准收益率的偏差
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export { BaselineComparison };
export default BaselineComparison;
