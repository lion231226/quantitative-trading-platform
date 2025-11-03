'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { BarChart3, Check, Info, Lightbulb, Loader2, Shield, TrendingUp, X } from 'lucide-react';
import { OptimizationSuggestion, StrategyParameters, StrategyResult } from '@/types/parameter.types';
import { parameterService } from '@/services/parameterService';

interface OptimizationSuggestionsProps {
  symbol: string
  currentParameters: StrategyParameters
  startDate: string
  endDate: string
  onApplySuggestion?: (suggestion: OptimizationSuggestion) => void
  className?: string
}

// 建议类型配置
const SUGGESTION_TYPES = {
  risk: {
    icon: Shield,
    label: '风险优化',
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    description: '基于风险控制的参数优化建议',
  },
  performance: {
    icon: TrendingUp,
    label: '收益优化',
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    description: '基于收益最大化的参数优化建议',
  },
  trend: {
    icon: BarChart3,
    label: '趋势优化',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    description: '基于市场趋势的参数优化建议',
  },
  volatility: {
    icon: TrendingUp,
    label: '波动优化',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
    description: '基于波动率分析的参数优化建议',
  },
};

// 可信度等级配置
const CONFIDENCE_LEVELS = {
  high: { min: 80, label: '高可信度', color: 'text-green-600', bgColor: 'bg-green-100' },
  medium: { min: 60, label: '中可信度', color: 'text-yellow-600', bgColor: 'bg-yellow-100' },
  low: { min: 40, label: '低可信度', color: 'text-red-600', bgColor: 'bg-red-100' },
};

export const OptimizationSuggestions: React.FC<OptimizationSuggestionsProps> = ({
  symbol,
  currentParameters,
  startDate,
  endDate,
  onApplySuggestion,
  className = '',
}) => {
  const [suggestions, setSuggestions] = useState<OptimizationSuggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [appliedSuggestions, setAppliedSuggestions] = useState<Set<string>>(new Set());

  // 获取优化建议
  const fetchSuggestions = useCallback(async () => {
    if (!symbol || !currentParameters || !startDate || !endDate) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // 调用后端的优化建议API
      const suggestions = await parameterService.getOptimizationSuggestions(
        symbol,
        currentParameters,
        startDate,
        endDate,
      );

      setSuggestions(suggestions);
    } catch (err) {
      console.error('获取优化建议失败:', err);
      setError('获取优化建议失败，请稍后重试');
    } finally {
      setIsLoading(false);
    }
  }, [symbol, currentParameters, startDate, endDate]);

  // 生成优化建议（基于简单的历史数据分析）
  const generateOptimizationSuggestions = async (
    symbol: string,
    params: StrategyParameters,
    startDate: string,
    endDate: string,
  ): Promise<OptimizationSuggestion[]> => {
    // 模拟基于历史数据分析生成建议
    const suggestions: OptimizationSuggestion[] = [];

    // 风险优化建议
    if (params.stopLoss > 3) {
      suggestions.push({
        id: `risk-${Date.now()}-1`,
        type: 'risk',
        confidence: 85,
        parameters: {
          ...params,
          stopLoss: Math.max(params.stopLoss * 0.8, 2.5),
          takeProfit: Math.min(params.takeProfit * 1.1, 15),
        },
        reasoning: `当前止损设置${params.stopLoss}%相对较高。基于历史数据分析，将止损调整为${Math.max(params.stopLoss * 0.8, 2.5).toFixed(1)}%可以降低单笔损失风险，同时将止盈调整为${Math.min(params.takeProfit * 1.1, 15).toFixed(1)}%保持合理的盈亏比。`,
        expectedImprovement: '预计降低最大回撤15%，提高风险调整后收益',
      });
    }

    // 性能优化建议
    if (params.movingAveragePeriod > 30) {
      suggestions.push({
        id: `performance-${Date.now()}-2`,
        type: 'performance',
        confidence: 72,
        parameters: {
          ...params,
          movingAveragePeriod: Math.max(params.movingAveragePeriod - 10, 15),
        },
        reasoning: `均线周期${params.movingAveragePeriod}可能过长，导致信号滞后。基于${symbol}的历史表现，缩短至${Math.max(params.movingAveragePeriod - 10, 15)}可以更及时地捕捉市场变化。`,
        expectedImprovement: '预计提高交易频率20%，增强信号时效性',
      });
    }

    // 趋势优化建议
    suggestions.push({
      id: `trend-${Date.now()}-3`,
      type: 'trend',
      confidence: 68,
      parameters: {
        ...params,
        movingAveragePeriod: params.movingAveragePeriod > 20
          ? Math.max(params.movingAveragePeriod - 5, 15)
          : Math.min(params.movingAveragePeriod + 5, 35),
      },
      reasoning: `基于当前市场趋势特征和历史数据，建议将均线周期从${params.movingAveragePeriod}调整为${params.movingAveragePeriod > 20 ? Math.max(params.movingAveragePeriod - 5, 15) : Math.min(params.movingAveragePeriod + 5, 35)}，以更好地适应市场节奏。`,
      expectedImprovement: '预计提高信号质量，减少假信号数量',
    });

    // 波动率优化建议
    if (params.takeProfit - params.stopLoss < 8) {
      suggestions.push({
        id: `volatility-${Date.now()}-4`,
        type: 'volatility',
        confidence: 76,
        parameters: {
          ...params,
          stopLoss: Math.max(params.stopLoss - 1, 2),
          takeProfit: Math.min(params.takeProfit + 2, 18),
        },
        reasoning: `当前盈亏比${(params.takeProfit / params.stopLoss).toFixed(2)}偏低。基于历史波动率分析，建议调整止损至${Math.max(params.stopLoss - 1, 2).toFixed(1)}%，止盈至${Math.min(params.takeProfit + 2, 18).toFixed(1)}%，提高盈亏比至${(Math.min(params.takeProfit + 2, 18) / Math.max(params.stopLoss - 1, 2)).toFixed(2)}。`,
        expectedImprovement: '预计提高盈亏比至2.5以上，改善长期收益稳定性',
      });
    }

    return suggestions;
  };

  // 应用建议
  const applySuggestion = useCallback((suggestion: OptimizationSuggestion) => {
    onApplySuggestion?.(suggestion);
    setAppliedSuggestions(prev => new Set(prev).add(suggestion.id));
  }, [onApplySuggestion]);

  // 忽略建议
  const dismissSuggestion = useCallback((suggestionId: string) => {
    setSuggestions(prev => prev.filter(s => s.id !== suggestionId));
  }, []);

  // 获取可信度等级
  const getConfidenceLevel = (confidence: number) => {
    if (confidence >= CONFIDENCE_LEVELS.high.min) return CONFIDENCE_LEVELS.high;
    if (confidence >= CONFIDENCE_LEVELS.medium.min) return CONFIDENCE_LEVELS.medium;
    return CONFIDENCE_LEVELS.low;
  };

  // 参数变化显示
  const formatParameterChange = (current: number, suggested: number, precision: number = 1) => {
    const change = suggested - current;
    const changePercent = ((change / current) * 100).toFixed(1);
    const direction = change > 0 ? '↑' : change < 0 ? '↓' : '→';

    return {
      current: current.toFixed(precision),
      suggested: suggested.toFixed(precision),
      change: `${direction} ${Math.abs(Number(changePercent))}%`,
    };
  };

  // 组件挂载时获取建议
  useEffect(() => {
    if (symbol && currentParameters && startDate && endDate) {
      fetchSuggestions();
    }
  }, [symbol, currentParameters, startDate, endDate]); // 移除fetchSuggestions避免无限循环

  return (
    <div className={`space-y-4 ${className}`}>
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Lightbulb className="h-5 w-5 text-yellow-500" />
          <h3 className="text-lg font-semibold text-gray-900">参数优化建议</h3>
        </div>

        <button
          onClick={fetchSuggestions}
          disabled={isLoading}
          className="flex items-center space-x-1 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          aria-label="刷新建议"
        >
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>分析中...</span>
            </>
          ) : (
            <>
              <TrendingUp className="h-4 w-4" />
              <span>刷新建议</span>
            </>
          )}
        </button>
      </div>

      {/* 错误状态 */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center space-x-2">
            <X className="h-5 w-5 text-red-500" />
            <span className="text-red-700">{error}</span>
          </div>
        </div>
      )}

      {/* 建议列表 */}
      {suggestions.length === 0 && !isLoading && !error && (
        <div className="text-center py-8 bg-gray-50 rounded-lg">
          <Lightbulb className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <p className="text-gray-600 mb-2">暂无优化建议</p>
          <p className="text-sm text-gray-500">当前参数配置已经较为合理，或正在分析您的参数...</p>
        </div>
      )}

      <div className="space-y-4">
        {suggestions.map((suggestion) => {
          const typeConfig = SUGGESTION_TYPES[suggestion.type];
          const confidenceLevel = getConfidenceLevel(suggestion.confidence);
          const isApplied = appliedSuggestions.has(suggestion.id);
          const Icon = typeConfig.icon;

          return (
            <div
              key={suggestion.id}
              className={`border-2 rounded-lg p-4 transition-all ${
                isApplied
                  ? 'border-green-300 bg-green-50'
                  : `${typeConfig.borderColor} ${typeConfig.bgColor}`
              }`}
            >
              {/* 建议头部 */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center space-x-3">
                  <div className={`p-2 rounded-lg ${typeConfig.bgColor}`}>
                    <Icon className={`h-5 w-5 ${typeConfig.color}`} />
                  </div>

                  <div>
                    <div className="flex items-center space-x-2">
                      <h4 className="font-semibold text-gray-900">{typeConfig.label}</h4>
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${confidenceLevel.bgColor} ${confidenceLevel.color}`}>
                        {confidenceLevel.label} ({suggestion.confidence}%)
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{typeConfig.description}</p>
                  </div>
                </div>

                {!isApplied && (
                  <button
                    onClick={() => dismissSuggestion(suggestion.id)}
                    className="p-1 text-gray-400 hover:text-gray-600"
                    aria-label="忽略建议"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>

              {/* 参数变化对比 */}
              <div className="bg-white rounded-lg p-3 mb-3">
                <h5 className="text-sm font-medium text-gray-700 mb-2">建议参数调整：</h5>

                <div className="grid grid-cols-1 gap-2 text-sm">
                  {/* 均线周期变化 */}
                  {suggestion.parameters.movingAveragePeriod !== currentParameters.movingAveragePeriod && (
                    <div className="flex items-center justify-between">
                      <span className="text-gray-600">均线周期:</span>
                      <div className="flex items-center space-x-2">
                        <span className="text-gray-500">
                          {formatParameterChange(
                            currentParameters.movingAveragePeriod,
                            suggestion.parameters.movingAveragePeriod,
                            0,
                          ).current}
                        </span>
                        <span className="text-blue-600 font-medium">
                          → {formatParameterChange(
                            currentParameters.movingAveragePeriod,
                            suggestion.parameters.movingAveragePeriod,
                            0,
                          ).suggested}
                        </span>
                        <span className="text-xs text-gray-500">
                          {formatParameterChange(
                            currentParameters.movingAveragePeriod,
                            suggestion.parameters.movingAveragePeriod,
                            0,
                          ).change}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* 止损变化 */}
                  {suggestion.parameters.stopLoss !== currentParameters.stopLoss && (
                    <div className="flex items-center justify-between">
                      <span className="text-gray-600">止损:</span>
                      <div className="flex items-center space-x-2">
                        <span className="text-gray-500">
                          {formatParameterChange(
                            currentParameters.stopLoss,
                            suggestion.parameters.stopLoss,
                          ).current}%
                        </span>
                        <span className="text-blue-600 font-medium">
                          → {formatParameterChange(
                            currentParameters.stopLoss,
                            suggestion.parameters.stopLoss,
                          ).suggested}%
                        </span>
                        <span className="text-xs text-gray-500">
                          {formatParameterChange(
                            currentParameters.stopLoss,
                            suggestion.parameters.stopLoss,
                          ).change}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* 止盈变化 */}
                  {suggestion.parameters.takeProfit !== currentParameters.takeProfit && (
                    <div className="flex items-center justify-between">
                      <span className="text-gray-600">止盈:</span>
                      <div className="flex items-center space-x-2">
                        <span className="text-gray-500">
                          {formatParameterChange(
                            currentParameters.takeProfit,
                            suggestion.parameters.takeProfit,
                          ).current}%
                        </span>
                        <span className="text-blue-600 font-medium">
                          → {formatParameterChange(
                            currentParameters.takeProfit,
                            suggestion.parameters.takeProfit,
                          ).suggested}%
                        </span>
                        <span className="text-xs text-gray-500">
                          {formatParameterChange(
                            currentParameters.takeProfit,
                            suggestion.parameters.takeProfit,
                          ).change}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* 建议说明 */}
              <div className="mb-3">
                <div className="flex items-center space-x-1 text-sm text-gray-700">
                  <Info className="h-4 w-4" />
                  <span className="font-medium">分析说明:</span>
                </div>
                <p className="text-sm text-gray-600 mt-1 leading-relaxed">{suggestion.reasoning}</p>
              </div>

              {/* 预期改进 */}
              {suggestion.expectedImprovement && (
                <div className="mb-3">
                  <div className="flex items-center space-x-1 text-sm text-green-700">
                    <TrendingUp className="h-4 w-4" />
                    <span className="font-medium">预期改进:</span>
                  </div>
                  <p className="text-sm text-green-600 mt-1">{suggestion.expectedImprovement}</p>
                </div>
              )}

              {/* 操作按钮 */}
              <div className="flex items-center space-x-2">
                {isApplied ? (
                  <div className="flex-1 flex items-center justify-center space-x-1 px-3 py-2 bg-green-100 text-green-700 rounded-md">
                    <Check className="h-4 w-4" />
                    <span>已应用</span>
                  </div>
                ) : (
                  <>
                    <button
                      onClick={() => applySuggestion(suggestion)}
                      className="flex-1 flex items-center justify-center space-x-1 px-3 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700"
                    >
                      <Check className="h-4 w-4" />
                      <span>应用建议</span>
                    </button>

                    <button
                      onClick={() => dismissSuggestion(suggestion.id)}
                      className="px-3 py-2 border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50"
                    >
                      忽略
                    </button>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* 底部说明 */}
      {suggestions.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start space-x-2">
            <Info className="h-5 w-5 text-blue-500 mt-0.5" />
            <div className="text-sm text-blue-700">
              <p className="font-medium mb-1">关于优化建议</p>
              <p className="leading-relaxed">
                这些建议基于历史数据分析和算法模型生成，仅供参考。实际应用时请结合当前市场环境和个人风险承受能力。
                建议在应用前进行充分的回测验证。
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OptimizationSuggestions;
