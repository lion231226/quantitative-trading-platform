import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  ParameterChangeEvent,
  ParameterGroup,
  ParameterValidationResult,
  StrategyParameters,
  StrategyResult,
} from '@/types/parameter.types';
import {
  DEBOUNCE_CONFIG,
  ParameterChangeDetector,
  ParameterServicePreloader,
  useOptimizationSuggestions,
  useParameterComparison as useParameterComparisonService,
  useParameterValidation,
  useRealTimeStrategyResults,
} from '@/services/parameterService';
import { validateAllParameters } from '@/utils/parameterHelpers';

interface UseRealTimeParametersOptions {
  symbol: string
  startDate: string
  endDate: string
  initialParameters?: StrategyParameters
  onParametersChange?: (parameters: StrategyParameters) => void
  onParameterChange?: (event: ParameterChangeEvent) => void
  onValidationError?: (validation: ParameterValidationResult) => void
  onResultUpdate?: (result: StrategyResult | null) => void
  debounceDelay?: number
  enableRealTime?: boolean
}

interface RealTimeParametersState {
  parameters: StrategyParameters
  isLoading: boolean
  isUpdating: boolean
  error: string | null
  validationResult: ParameterValidationResult | null
  strategyResult: StrategyResult | null
  lastUpdate: Date | null
}

export function useRealTimeParameters({
  symbol,
  startDate,
  endDate,
  initialParameters,
  onParametersChange,
  onParameterChange,
  onValidationError,
  onResultUpdate,
  debounceDelay = DEBOUNCE_CONFIG.delay,
  enableRealTime = true,
}: UseRealTimeParametersOptions) {
  const queryClient = useQueryClient();
  const changeDetectorRef = useRef<ParameterChangeDetector>();
  const preloaderRef = useRef<any>();

  // 状态管理
  const [state, setState] = useState<RealTimeParametersState>({
    parameters: initialParameters || {
      movingAveragePeriod: 20,
      stopLoss: 5.0,
      takeProfit: 10.0,
    },
    isLoading: false,
    isUpdating: false,
    error: null,
    validationResult: null,
    strategyResult: null,
    lastUpdate: null,
  });

  const [isRealTimeEnabled, setIsRealTimeEnabled] = useState(enableRealTime);

  // 初始化服务
  useEffect(() => {
    if (!changeDetectorRef.current) {
      changeDetectorRef.current = new ParameterChangeDetector(
        (params) => {
          setState(prev => ({
            ...prev,
            parameters: params,
            isUpdating: true,
            error: null,
            lastUpdate: new Date(),
          }));

          onParametersChange?.(params);
        },
        debounceDelay,
      );
    }

    if (!preloaderRef.current && ParameterServicePreloader) {
      try {
        preloaderRef.current = new ParameterServicePreloader(queryClient);
      } catch (error) {
        console.warn('ParameterServicePreloader not available:', error);
      }
    }

    return () => {
      changeDetectorRef.current?.destroy();
    };
  }, [debounceDelay, onParametersChange, queryClient]);

  // 参数验证查询
  const validationQuery = useParameterValidation(state.parameters);

  // 实时策略结果查询
  const strategyResultQuery = useRealTimeStrategyResults(
    symbol,
    state.parameters,
    startDate,
    endDate,
    {
      enabled: isRealTimeEnabled,
    },
  );

  // 处理验证结果
  useEffect(() => {
    if (validationQuery.data) {
      setState(prev => ({ ...prev, validationResult: validationQuery.data }));
      onValidationError?.(validationQuery.data);
    }
  }, [validationQuery.data, onValidationError]);

  // 处理策略结果
  useEffect(() => {
    if (strategyResultQuery.data) {
      setState(prev => ({
        ...prev,
        strategyResult: strategyResultQuery.data,
        isUpdating: false,
        error: null,
      }));
      onResultUpdate?.(strategyResultQuery.data);
    }
  }, [strategyResultQuery.data, onResultUpdate]);

  // 处理策略结果错误
  useEffect(() => {
    if (strategyResultQuery.error) {
      setState(prev => ({
        ...prev,
        error: strategyResultQuery.error?.message || '策略分析失败',
        isUpdating: false,
      }));
    }
  }, [strategyResultQuery.error]);

  // 更新参数
  const updateParameters = useCallback((newParameters: StrategyParameters) => {
    if (changeDetectorRef.current) {
      const hasChanged = changeDetectorRef.current.detectChange(newParameters);

      if (hasChanged && onParameterChange) {
        // 通知参数变化事件
        const changedKey = Object.keys(newParameters).find(
          key => newParameters[key as keyof StrategyParameters] !== state.parameters[key as keyof StrategyParameters],
        ) as keyof StrategyParameters;

        if (changedKey) {
          onParameterChange({
            parameter: changedKey,
            value: newParameters[changedKey],
            previousValue: state.parameters[changedKey],
          });
        }
      }
    }
  }, [state.parameters, onParameterChange]);

  // 立即更新参数（跳过防抖）
  const updateParametersImmediate = useCallback((newParameters: StrategyParameters) => {
    if (changeDetectorRef.current) {
      changeDetectorRef.current.detectChange(newParameters, true);
    }
  }, []);

  // 重置参数
  const resetParameters = useCallback(() => {
    const defaultParameters = {
      movingAveragePeriod: 20,
      stopLoss: 5.0,
      takeProfit: 10.0,
    };
    updateParametersImmediate(defaultParameters);
  }, [updateParametersImmediate]);

  // 切换实时更新
  const toggleRealTime = useCallback(() => {
    setIsRealTimeEnabled(prev => !prev);
  }, []);

  // 强制刷新
  const forceRefresh = useCallback(() => {
    if (changeDetectorRef.current) {
      changeDetectorRef.current.flush();
    }
    strategyResultQuery.refetch();
  }, [strategyResultQuery]);

  // 预加载参数组合
  const preloadParameters = useCallback((parameters: StrategyParameters) => {
    if (preloaderRef.current) {
      preloaderRef.current.preloadStrategyResults(symbol, parameters, startDate, endDate);
    }
  }, [symbol, startDate, endDate]);

  // 清除缓存
  const clearCache = useCallback(() => {
    if (preloaderRef.current) {
      preloaderRef.current.clearStrategyCache(symbol);
    }
    queryClient.invalidateQueries({
      queryKey: ['strategyResults', symbol],
    });
  }, [symbol, queryClient]);

  // 手动验证参数
  const validateParameters = useCallback(() => {
    const validation = validateAllParameters(state.parameters);
    setState(prev => ({ ...prev, validationResult: validation }));
    return validation;
  }, [state.parameters]);

  // 获取参数描述
  const getParameterDescription = useCallback(() => {
    const { movingAveragePeriod, stopLoss, takeProfit } = state.parameters;

    let description = `使用${movingAveragePeriod}日移动平均线`;

    if (stopLoss > 0 && takeProfit > 0) {
      description += `，设置${stopLoss.toFixed(1)}%止损和${takeProfit.toFixed(1)}%止盈`;
    } else if (stopLoss > 0) {
      description += `，设置${stopLoss.toFixed(1)}%止损`;
    } else if (takeProfit > 0) {
      description += `，设置${takeProfit.toFixed(1)}%止盈`;
    }

    return description;
  }, [state.parameters]);

  // 检查参数有效性
  const isParametersValid = useMemo(() => {
    return state.validationResult?.isValid ?? false;
  }, [state.validationResult]);

  // 获取错误信息
  const getErrorMessage = useCallback(() => {
    if (state.error) return state.error;
    if (state.validationResult && !state.validationResult.isValid) {
      return state.validationResult.errors.join(', ');
    }
    return null;
  }, [state.error, state.validationResult]);

  // 状态汇总
  const isLoading = state.isLoading || validationQuery.isLoading || strategyResultQuery.isLoading;
  const isUpdating = state.isUpdating || strategyResultQuery.isFetching;

  return {
    // 状态
    parameters: state.parameters,
    isLoading,
    isUpdating,
    error: getErrorMessage(),
    validationResult: state.validationResult,
    strategyResult: state.strategyResult,
    lastUpdate: state.lastUpdate,
    isRealTimeEnabled,
    isParametersValid,

    // 操作方法
    updateParameters,
    updateParametersImmediate,
    resetParameters,
    toggleRealTime,
    forceRefresh,
    preloadParameters,
    clearCache,
    validateParameters,

    // 辅助方法
    getParameterDescription,
    getErrorMessage,

    // 查询状态
    validationQuery,
    strategyResultQuery,
  };
}

/**
 * 参数对比Hook
 */
export function useParameterComparison(
  groups: ParameterGroup[],
  symbol: string,
  startDate: string,
  endDate: string,
) {
  const comparisonQuery = useParameterComparison(groups, symbol, startDate, endDate);

  const addComparisonGroup = useCallback((newGroup: ParameterGroup) => {
    const updatedGroups = [...groups, newGroup];
    // 触发重新查询
    comparisonQuery.refetch();
    return updatedGroups;
  }, [groups, comparisonQuery]);

  const removeComparisonGroup = useCallback((groupId: string) => {
    const updatedGroups = groups.filter(group => group.id !== groupId);
    comparisonQuery.refetch();
    return updatedGroups;
  }, [groups, comparisonQuery]);

  const updateComparisonGroup = useCallback((groupId: string, updates: Partial<ParameterGroup>) => {
    const updatedGroups = groups.map(group =>
      group.id === groupId ? { ...group, ...updates } : group,
    );
    comparisonQuery.refetch();
    return updatedGroups;
  }, [groups, comparisonQuery]);

  return {
    ...comparisonQuery,
    addComparisonGroup,
    removeComparisonGroup,
    updateComparisonGroup,
  };
}

/**
 * 参数优化建议Hook
 */
export function useParameterOptimization(
  baseParameters: StrategyParameters,
  symbol: string,
  startDate: string,
  endDate: string,
) {
  const suggestionsQuery = useOptimizationSuggestions(symbol, baseParameters, startDate, endDate);

  const applySuggestion = useCallback((suggestion: any) => {
    return suggestion.parameters;
  }, []);

  const dismissSuggestion = useCallback((suggestionId: string) => {
    // 可以在本地存储中记录已忽略的建议
    if (typeof window !== 'undefined') {
      const dismissed = JSON.parse(localStorage.getItem('dismissed_suggestions') || '[]');
      dismissed.push(suggestionId);
      localStorage.setItem('dismissed_suggestions', JSON.stringify(dismissed));
    }
  }, []);

  return {
    ...suggestionsQuery,
    applySuggestion,
    dismissSuggestion,
  };
}
