'use client';

import { useState } from 'react';
import { Layout } from '@/components/layout/Layout';
import { MarketSelectorWithChart } from '@/components/forms/MarketSelectorWithChart';
import { DateRangePicker } from '@/components/forms/DateRangePicker';
import { StrategyForm } from '@/components/forms/StrategyForm';
import { ResultsDisplay } from '@/components/results/ResultsDisplay';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Loading } from '@/components/ui/loading';
import { strategyAPI } from '@/lib/api';
import { validateStrategyForm } from '@/lib/validation';
import {
  DualMovingAverageParams,
  MACDStrategyParams,
  MarketSelectionForm,
  RSIStrategyParams,
  SingleMovingAverageParams,
  StrategyConfigForm,
  StrategyParams,
  StrategyRun,
  StrategySubmissionForm,
  StrategyType,
} from '@/types/strategy';

export default function StrategyPage() {
  const [marketSelection, setMarketSelection] = useState<MarketSelectionForm>({
    symbol: '',
    startDate: '',
    endDate: '',
  });

  const [strategyConfig, setStrategyConfig] = useState<StrategyConfigForm>({
    strategyType: 'single_ma',
    params: {
      ma_period: 20,
      ma_type: 'SMA',
      initial_capital: 100000,
      min_cross_percentage: 0.001,
      confirmation_periods: 1,
      stop_loss_pct: 0.02,
      take_profit_pct: 0.05,
      max_position_size: 1.0,
      max_signals_per_day: 10,
      signal_cooldown: 300,
    } as SingleMovingAverageParams,
  });

  const [currentRun, setCurrentRun] = useState<StrategyRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');

  const handleSymbolSelect = (symbol: string) => {
    setMarketSelection((prev) => ({ ...prev, symbol }));
  };

  const handleDateRangeChange = (startDate: string, endDate: string) => {
    setMarketSelection((prev) => ({ ...prev, startDate, endDate }));
  };

  const handleParamsChange = (
    strategyType: StrategyType,
    params: StrategyParams,
  ) => {
    setStrategyConfig((prev) => ({ ...prev, strategyType, params }));
  };

  const canRunStrategy = () => {
    const formData: StrategySubmissionForm = {
      ...marketSelection,
      strategyType: strategyConfig.strategyType,
      params: strategyConfig.params,
    };
    const validation = validateStrategyForm(formData);
    return validation.isValid && !loading;
  };

  const runStrategy = async () => {
    if (!canRunStrategy()) return;

    const formData: StrategySubmissionForm = {
      ...marketSelection,
      strategyType: strategyConfig.strategyType,
      params: strategyConfig.params,
    };

    const validation = validateStrategyForm(formData);
    if (!validation.isValid) {
      setError(validation.errors.join('\n'));
      return;
    }

    try {
      setLoading(true);
      setError('');

      // 类型安全的策略参数提取函数
      const getStrategyParameters = (
        strategyType: StrategyType,
        params: StrategyParams,
      ) => {
        switch (strategyType) {
          case 'single_ma':
            const singleParams = params as SingleMovingAverageParams;
            return {
              ma_period: singleParams.ma_period,
              ma_type: singleParams.ma_type,
              initial_capital: singleParams.initial_capital,
              min_cross_percentage: singleParams.min_cross_percentage,
              confirmation_periods: singleParams.confirmation_periods,
              stop_loss_pct: singleParams.stop_loss_pct,
              take_profit_pct: singleParams.take_profit_pct,
              max_position_size: singleParams.max_position_size,
              max_signals_per_day: singleParams.max_signals_per_day,
              signal_cooldown: singleParams.signal_cooldown,
            };
          case 'dual_ma':
            const dualParams = params as DualMovingAverageParams;
            return {
              short_ma_period: dualParams.short_ma_period,
              long_ma_period: dualParams.long_ma_period,
              short_ma_type: dualParams.short_ma_type,
              long_ma_type: dualParams.long_ma_type,
              initial_capital: dualParams.initial_capital,
              min_cross_percentage: dualParams.min_cross_percentage,
              confirmation_periods: dualParams.confirmation_periods,
              stop_loss_pct: dualParams.stop_loss_pct,
              take_profit_pct: dualParams.take_profit_pct,
              max_position_size: dualParams.max_position_size,
              max_signals_per_day: dualParams.max_signals_per_day,
              signal_cooldown: dualParams.signal_cooldown,
            };
          case 'rsi':
            const rsiParams = params as RSIStrategyParams;
            return {
              rsi_period: rsiParams.rsi_period,
              rsi_overbought: rsiParams.rsi_overbought,
              rsi_oversold: rsiParams.rsi_oversold,
              initial_capital: rsiParams.initial_capital,
              confirmation_periods: rsiParams.confirmation_periods,
              stop_loss_pct: rsiParams.stop_loss_pct,
              take_profit_pct: rsiParams.take_profit_pct,
              max_position_size: rsiParams.max_position_size,
              max_signals_per_day: rsiParams.max_signals_per_day,
              signal_cooldown: rsiParams.signal_cooldown,
            };
          case 'macd':
            const macdParams = params as MACDStrategyParams;
            return {
              macd_fast_period: macdParams.macd_fast_period,
              macd_slow_period: macdParams.macd_slow_period,
              macd_signal_period: macdParams.macd_signal_period,
              initial_capital: macdParams.initial_capital,
              confirmation_periods: macdParams.confirmation_periods,
              stop_loss_pct: macdParams.stop_loss_pct,
              take_profit_pct: macdParams.take_profit_pct,
              max_position_size: macdParams.max_position_size,
              max_signals_per_day: macdParams.max_signals_per_day,
              signal_cooldown: macdParams.signal_cooldown,
            };
          default:
            throw new Error(`Unsupported strategy type: ${strategyType}`);
        }
      };

      // 运行策略 - 直接发送完整的策略请求
      const runRequest = {
        symbol: marketSelection.symbol,
        strategy_type: strategyConfig.strategyType,
        start_date: marketSelection.startDate,
        end_date: marketSelection.endDate,
        parameters: getStrategyParameters(
          strategyConfig.strategyType,
          strategyConfig.params,
        ),
      };

      const response = await strategyAPI.run(runRequest);

      // 创建策略运行对象 - 检查响应数据结构
      console.log('Strategy run response:', response);

      const strategyId =
        (response as any).strategy_id ||
        (response as any).task_id ||
        (response as any).data?.strategy_id ||
        (response as any).data?.task_id;

      if (!strategyId) {
        throw new Error('策略运行失败：未获取到策略ID');
      }

      const strategyRun: StrategyRun = {
        id: strategyId,
        status: 'pending',
        created_at: new Date().toISOString(),
      };

      setCurrentRun(strategyRun);

      // 开始轮询任务状态
      pollTaskStatus(strategyId);
    } catch (err) {
      setError(err instanceof Error ? err.message : '策略运行失败');
      console.error('Failed to run strategy:', err);
    } finally {
      setLoading(false);
    }
  };

  const pollTaskStatus = async (taskId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const status = await strategyAPI.getTaskStatus(taskId);
        console.log('Task status response:', status);

        setCurrentRun((prev) =>
          prev
            ? {
                ...prev,
                status: status.status,
                progress: status.progress
                  ? Math.round(status.progress * 100)
                  : 0,
                result: status.result,
                error: status.error,
              }
            : null,
        );

        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(pollInterval);
        }
      } catch (err) {
        console.error('Failed to get task status:', err);
        clearInterval(pollInterval);
      }
    }, 2000);
  };

  const resetStrategy = () => {
    setCurrentRun(null);
    setError('');
  };

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">策略分析</h1>
          <p className="text-lg text-gray-600">配置参数并运行策略回测</p>
        </div>

        {error && (
          <Card className="mb-6 border-red-200 bg-red-50">
            <CardContent className="pt-6">
              <div className="text-red-800">
                <div className="font-medium mb-1">配置错误:</div>
                <div className="text-sm whitespace-pre-line">{error}</div>
              </div>
            </CardContent>
          </Card>
        )}

        {!currentRun ? (
          <div className="space-y-6">
            <MarketSelectorWithChart
              onSymbolSelect={handleSymbolSelect}
              selectedSymbol={marketSelection.symbol}
            />

            <div className="grid lg:grid-cols-2 gap-6">
              <div className="space-y-6">
                <DateRangePicker
                  onDateRangeChange={handleDateRangeChange}
                  startDate={marketSelection.startDate}
                  endDate={marketSelection.endDate}
                />

                <StrategyForm
                  onParamsChange={handleParamsChange}
                  initialParams={strategyConfig.params}
                />
              </div>

              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle>策略配置摘要</CardTitle>
                    <CardDescription>当前选择的参数</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* 基础信息 */}
                    <div className="space-y-3">
                      <div>
                        <div className="text-sm font-medium">期货品种</div>
                        <div className="text-sm text-gray-600">
                          {marketSelection.symbol || '未选择'}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm font-medium">时间范围</div>
                        <div className="text-sm text-gray-600">
                          {marketSelection.startDate && marketSelection.endDate
                            ? `${marketSelection.startDate} 至 ${marketSelection.endDate}`
                            : '未选择'}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm font-medium">策略类型</div>
                        <div className="text-sm text-gray-600">
                          {strategyConfig.strategyType === 'single_ma' &&
                            '单均线策略'}
                          {strategyConfig.strategyType === 'dual_ma' &&
                            '双均线策略'}
                          {strategyConfig.strategyType === 'rsi' && 'RSI策略'}
                          {strategyConfig.strategyType === 'macd' && 'MACD策略'}
                        </div>
                      </div>
                    </div>

                    {/* 策略参数详情 */}
                    {strategyConfig.strategyType === 'single_ma' &&
                      (() => {
                        const params =
                          strategyConfig.params as SingleMovingAverageParams;
                        return (
                          <div className="border-t pt-3">
                            <div className="text-sm font-medium mb-2">
                              策略参数
                            </div>
                            <div className="space-y-2">
                              <div className="flex justify-between text-xs">
                                <span className="text-gray-600">均线周期:</span>
                                <span className="font-medium">
                                  {params.ma_period}天 ({params.ma_type})
                                </span>
                              </div>
                              <div className="flex justify-between text-xs">
                                <span className="text-gray-600">初始资金:</span>
                                <span className="font-medium">
                                  ¥{params.initial_capital.toLocaleString()}
                                </span>
                              </div>
                              <div className="flex justify-between text-xs">
                                <span className="text-gray-600">
                                  最小交叉幅度:
                                </span>
                                <span className="font-medium">
                                  {(params.min_cross_percentage * 100).toFixed(
                                    2,
                                  )}
                                  %
                                </span>
                              </div>
                              <div className="flex justify-between text-xs">
                                <span className="text-gray-600">确认周期:</span>
                                <span className="font-medium">
                                  {params.confirmation_periods}天
                                </span>
                              </div>
                            </div>
                          </div>
                        );
                      })()}

                    {/* 风险管理参数 */}
                    {(() => {
                      const params = strategyConfig.params;
                      const commonParams = params as SingleMovingAverageParams;
                      return (
                        <div className="border-t pt-3">
                          <div className="text-sm font-medium mb-2">
                            风险管理
                          </div>
                          <div className="space-y-2">
                            <div className="flex justify-between text-xs">
                              <span className="text-gray-600">止损比例:</span>
                              <span className="font-medium text-red-600">
                                {(commonParams.stop_loss_pct * 100).toFixed(1)}%
                              </span>
                            </div>
                            <div className="flex justify-between text-xs">
                              <span className="text-gray-600">止盈比例:</span>
                              <span className="font-medium text-green-600">
                                {(commonParams.take_profit_pct * 100).toFixed(
                                  1,
                                )}
                                %
                              </span>
                            </div>
                            <div className="flex justify-between text-xs">
                              <span className="text-gray-600">最大仓位:</span>
                              <span className="font-medium">
                                {(commonParams.max_position_size * 100).toFixed(
                                  0,
                                )}
                                %
                              </span>
                            </div>
                            <div className="flex justify-between text-xs">
                              <span className="text-gray-600">
                                每日最大信号:
                              </span>
                              <span className="font-medium">
                                {commonParams.max_signals_per_day}个
                              </span>
                            </div>
                            <div className="flex justify-between text-xs">
                              <span className="text-gray-600">
                                信号冷却时间:
                              </span>
                              <span className="font-medium">
                                {commonParams.signal_cooldown}秒
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    })()}
                  </CardContent>
                </Card>

                <Button
                  onClick={runStrategy}
                  disabled={!canRunStrategy()}
                  className="w-full"
                  size="lg"
                >
                  {loading ? (
                    <>
                      <Loading size="sm" />
                      <span className="ml-2">运行中...</span>
                    </>
                  ) : (
                    '开始策略分析'
                  )}
                </Button>

                <div className="text-xs text-gray-500 text-center">
                  策略运行可能需要几分钟时间，请耐心等待
                </div>
              </div>
            </div>
          </div>
        ) : (
          <ResultsDisplay strategyRun={currentRun} onReset={resetStrategy} />
        )}
      </div>
    </Layout>
  );
}
