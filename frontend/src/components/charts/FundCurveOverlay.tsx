'use client';

import React, { useCallback, useEffect, useMemo, useRef } from 'react';
import {
  CrosshairMode,
  LineStyle,
  PriceScaleMode,
  createChart,
} from 'lightweight-charts';
import {
  DualYAxisConfig,
  FundCurveData,
  PerformanceMetrics,
} from '../../types/kline.types';
import { useTheme } from '../theme/ThemeProvider';

interface FundCurveOverlayProps {
  container: HTMLElement;
  fundCurves: FundCurveData[];
  dualYAxisConfig: DualYAxisConfig;
  onMetricsUpdate?: (metrics: PerformanceMetrics[]) => void;
  onCurveClick?: (curveId: string, point: any) => void;
}

/**
 * 资金曲线覆盖层组件
 * 在现有K线图上添加双Y轴资金曲线显示
 */
const FundCurveOverlay: React.FC<FundCurveOverlayProps> = ({
  container,
  fundCurves,
  dualYAxisConfig,
  onMetricsUpdate,
  onCurveClick,
}) => {
  const { currentTheme } = useTheme();
  const chartRef = useRef<any>(null);
  const seriesRef = useRef<Map<string, any>>(new Map());

  // 计算性能指标
  const calculateMetrics = useCallback(
    (data: FundCurveData['data']): PerformanceMetrics => {
      if (data.length < 2) {
        return {
          returnRate: 0,
          maxDrawdown: 0,
          sharpeRatio: 0,
          totalReturn: 0,
          annualizedReturn: 0,
          volatility: 0,
          winRate: 0,
          profitFactor: 0,
          maxConsecutiveWins: 0,
          maxConsecutiveLosses: 0,
        };
      }

      const values = data.map((d) => d.value);
      const firstValue = values[0];
      const lastValue = values[values.length - 1];
      const totalReturn = (lastValue - firstValue) / firstValue;
      const returnRate = totalReturn * 100;

      // 计算最大回撤
      let maxDrawdown = 0;
      let peak = values[0];
      for (let i = 1; i < values.length; i++) {
        if (values[i] > peak) {
          peak = values[i];
        }
        const drawdown = (peak - values[i]) / peak;
        if (drawdown > maxDrawdown) {
          maxDrawdown = drawdown;
        }
      }
      maxDrawdown *= 100;

      // 计算收益率（用于夏普比率）
      const returns = [];
      for (let i = 1; i < values.length; i++) {
        returns.push((values[i] - values[i - 1]) / values[i - 1]);
      }

      // 计算平均收益率和标准差
      const avgReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length;
      const variance =
        returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) /
        returns.length;
      const volatility = Math.sqrt(variance) * Math.sqrt(252) * 100; // 年化波动率

      // 简化的夏普比率（假设无风险利率为0）
      const annualizedReturn =
        Math.pow(1 + totalReturn, 252 / values.length) - 1;
      const sharpeRatio =
        volatility !== 0 ? (annualizedReturn * 100) / volatility : 0;

      return {
        returnRate,
        maxDrawdown,
        sharpeRatio,
        totalReturn,
        annualizedReturn: annualizedReturn * 100,
        volatility,
        winRate: 0, // 需要更详细的交易数据来计算
        profitFactor: 0, // 需要盈亏比数据
        maxConsecutiveWins: 0,
        maxConsecutiveLosses: 0,
      };
    },
    [],
  );

  // 创建或更新图表
  useEffect(() => {
    if (!container) return;

    // 如果图表已存在，先销毁
    if (chartRef.current) {
      chartRef.current.remove();
      seriesRef.current.clear();
    }

    // 创建图表实例
    const chart = createChart(container, {
      width: container.clientWidth,
      height: container.clientHeight,
      layout: {
        background: { color: 'transparent' },
        textColor: currentTheme.colors.text,
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { visible: false },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { visible: false },
        horzLine: { visible: false },
      },
      timeScale: {
        visible: false, // 使用主图表的时间轴
      },
      rightPriceScale: {
        visible: dualYAxisConfig.rightAxis.visible,
        borderColor: dualYAxisConfig.rightAxis.borderColor,
        textColor: dualYAxisConfig.rightAxis.textColor,
        scaleMargins: dualYAxisConfig.rightAxis.scaleMargins,
      },
      leftPriceScale: {
        visible: false, // 使用主图表的左Y轴
      },
      overlay: true, // 设置为覆盖层
    });

    chartRef.current = chart;

    return () => {
      if (chartRef.current) {
        chartRef.current.remove();
      }
    };
  }, [container, dualYAxisConfig, currentTheme]);

  // 添加资金曲线系列
  useEffect(() => {
    if (!chartRef.current || fundCurves.length === 0) return;

    const chart = chartRef.current;
    const newMetrics: PerformanceMetrics[] = [];

    fundCurves.forEach((fundCurve) => {
      if (!fundCurve.visible) return;

      // 转换数据格式
      const seriesData = fundCurve.data.map((point) => ({
        time: point.timestamp,
        value: point.value,
      }));

      // 创建线条系列
      const series = chart.addLineSeries({
        color: fundCurve.color,
        lineWidth: fundCurve.lineWidth || 2,
        lineStyle:
          fundCurve.lineType === 'dashed'
            ? LineStyle.Dashed
            : fundCurve.lineType === 'dotted'
              ? LineStyle.Dotted
              : LineStyle.Solid,
        priceScaleId: 'fund-curve',
        title: fundCurve.name,
      });

      // 设置数据
      series.setData(seriesData);

      // 保存系列引用
      seriesRef.current.set(fundCurve.id, series);

      // 计算并存储指标
      const metrics = calculateMetrics(fundCurve.data);
      newMetrics.push(metrics);

      // 点击事件处理
      if (onCurveClick) {
        series.subscribeClick((param: any) => {
          if (param.time && param.point) {
            onCurveClick(fundCurve.id, {
              time: param.time,
              value: param.seriesPrices.get(series),
              point: param.point,
            });
          }
        });
      }
    });

    // 通知指标更新
    if (onMetricsUpdate) {
      onMetricsUpdate(newMetrics);
    }

    // 清理函数
    return () => {
      seriesRef.current.forEach((series) => {
        chart.removeSeries(series);
      });
      seriesRef.current.clear();
    };
  }, [
    fundCurves,
    dualYAxisConfig,
    calculateMetrics,
    onCurveClick,
    onMetricsUpdate,
  ]);

  // 处理窗口大小变化
  useEffect(() => {
    const handleResize = () => {
      if (chartRef.current && container) {
        chartRef.current.applyOptions({
          width: container.clientWidth,
          height: container.clientHeight,
        });
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [container]);

  // 组件本身不渲染任何内容，它只是管理图表覆盖层
  return null;
};

export { FundCurveOverlay };
export default FundCurveOverlay;
