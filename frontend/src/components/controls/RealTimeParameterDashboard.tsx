'use client';

import React, { useCallback, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import ParameterControls from './ParameterControls';
import RealTimeResults from './RealTimeResults';
import { useRealTimeParameters } from '@/hooks/useRealTimeParameters';
import {
  ParameterChangeEvent,
  StrategyParameters,
} from '@/types/parameter.types';
import {
  Activity,
  Info,
  Pause,
  Play,
  RefreshCw,
  Settings,
  Zap,
} from 'lucide-react';

interface RealTimeParameterDashboardProps {
  symbol: string;
  startDate: string;
  endDate: string;
  initialParameters?: StrategyParameters;
  onParametersChange?: (parameters: StrategyParameters) => void;
  onStrategyResultUpdate?: (result: any) => void;
  showControls?: boolean;
  showResults?: boolean;
  compactResults?: boolean;
  enableAutoRefresh?: boolean;
  className?: string;
}

export function RealTimeParameterDashboard({
  symbol,
  startDate,
  endDate,
  initialParameters,
  onParametersChange,
  onStrategyResultUpdate,
  showControls = true,
  showResults = true,
  compactResults = false,
  enableAutoRefresh = true,
  className = '',
}: RealTimeParameterDashboardProps) {
  const [showAdvancedControls, setShowAdvancedControls] = useState(false);
  const [autoRefreshEnabled, setAutoRefreshEnabled] =
    useState(enableAutoRefresh);

  // 使用实时参数Hook
  const {
    parameters,
    isLoading,
    isUpdating,
    error,
    validationResult,
    strategyResult,
    lastUpdate,
    isRealTimeEnabled,
    isParametersValid,
    updateParameters,
    resetParameters,
    toggleRealTime,
    forceRefresh,
    getParameterDescription,
  } = useRealTimeParameters({
    symbol,
    startDate,
    endDate,
    initialParameters,
    onParametersChange: (params) => {
      onParametersChange?.(params);
    },
    onParameterChange: (event: ParameterChangeEvent) => {
      // 参数变化处理逻辑
    },
    onValidationError: (validation) => {
      if (!validation.isValid) {
        // 参数验证失败处理逻辑
      }
    },
    onResultUpdate: (result) => {
      onStrategyResultUpdate?.(result);
    },
    enableRealTime: autoRefreshEnabled,
  });

  // 处理参数变化
  const handleParametersChange = useCallback(
    (newParameters: StrategyParameters) => {
      updateParameters(newParameters);
    },
    [updateParameters],
  );

  // 处理参数重置
  const handleReset = useCallback(() => {
    resetParameters();
  }, [resetParameters]);

  // 切换实时更新
  const handleToggleRealTime = useCallback(() => {
    toggleRealTime();
    setAutoRefreshEnabled((prev) => !prev);
  }, [toggleRealTime]);

  // 处理强制刷新
  const handleForceRefresh = useCallback(() => {
    forceRefresh();
  }, [forceRefresh]);

  // 系统状态指示器
  const SystemStatusIndicator = () => (
    <div className="flex items-center space-x-4 p-3 bg-gray-50 rounded-lg">
      <div className="flex items-center space-x-2">
        <Activity
          className={`h-4 w-4 ${isRealTimeEnabled ? 'text-green-600' : 'text-gray-400'}`}
        />
        <span className="text-sm font-medium">实时更新</span>
        <Switch
          checked={isRealTimeEnabled}
          onCheckedChange={handleToggleRealTime}
          disabled={isLoading}
        />
      </div>

      <div className="flex items-center space-x-2">
        <div
          className={`w-2 h-2 rounded-full ${
            isUpdating
              ? 'bg-yellow-500 animate-pulse'
              : isLoading
                ? 'bg-blue-500 animate-pulse'
                : error
                  ? 'bg-red-500'
                  : isParametersValid
                    ? 'bg-green-500'
                    : 'bg-orange-500'
          }`}
        />
        <span className="text-sm text-muted-foreground">
          {isUpdating
            ? '更新中'
            : isLoading
              ? '分析中'
              : error
                ? '错误'
                : isParametersValid
                  ? '正常'
                  : '参数无效'}
        </span>
      </div>

      {lastUpdate && (
        <div className="flex items-center space-x-1 text-xs text-muted-foreground">
          <span>最后更新:</span>
          <span>{lastUpdate.toLocaleTimeString()}</span>
        </div>
      )}

      <Button
        variant="outline"
        size="sm"
        onClick={handleForceRefresh}
        disabled={isLoading || isUpdating}
        className="ml-auto"
      >
        <RefreshCw
          className={`h-4 w-4 mr-1 ${isUpdating ? 'animate-spin' : ''}`}
        />
        刷新
      </Button>
    </div>
  );

  return (
    <div className={`space-y-6 ${className}`}>
      {/* 系统状态和快速操作 */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center space-x-2">
              <Zap className="h-5 w-5 text-blue-600" />
              <span>实时策略分析</span>
              <span className="text-sm font-normal text-muted-foreground">
                {symbol} | {getParameterDescription()}
              </span>
            </CardTitle>

            <div className="flex items-center space-x-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowAdvancedControls(!showAdvancedControls)}
              >
                <Settings className="h-4 w-4 mr-1" />
                {showAdvancedControls ? '简化' : '高级'}
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          <SystemStatusIndicator />

          {/* 快速信息 */}
          <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center space-x-3 p-3 bg-blue-50 rounded-lg">
              <Activity className="h-5 w-5 text-blue-600" />
              <div>
                <p className="text-sm font-medium text-blue-900">实时模式</p>
                <p className="text-xs text-blue-700">
                  {isRealTimeEnabled ? '参数变化自动分析' : '手动刷新分析'}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-3 p-3 bg-green-50 rounded-lg">
              <Play className="h-5 w-5 text-green-600" />
              <div>
                <p className="text-sm font-medium text-green-900">响应时间</p>
                <p className="text-xs text-green-700">&lt;500ms (防抖优化)</p>
              </div>
            </div>

            <div className="flex items-center space-x-3 p-3 bg-purple-50 rounded-lg">
              <Info className="h-5 w-5 text-purple-600" />
              <div>
                <p className="text-sm font-medium text-purple-900">数据缓存</p>
                <p className="text-xs text-purple-700">智能缓存减少API调用</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 参数控制面板 */}
        {showControls && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold flex items-center space-x-2">
              <Settings className="h-5 w-5" />
              <span>参数配置</span>
              {validationResult && !validationResult.isValid && (
                <span className="text-sm text-red-600">参数有误</span>
              )}
            </h3>

            <ParameterControls
              parameters={parameters}
              onParametersChange={handleParametersChange}
              onReset={handleReset}
              disabled={isLoading}
              showPresets={true}
              showAdvanced={showAdvancedControls}
              allowCustomPresets={true}
            />

            {/* 参数验证状态 */}
            {validationResult && (
              <Card
                className={
                  validationResult.isValid
                    ? 'border-green-200'
                    : 'border-red-200'
                }
              >
                <CardContent className="p-4">
                  <div className="flex items-center space-x-2">
                    {validationResult.isValid ? (
                      <div className="w-4 h-4 rounded-full bg-green-500" />
                    ) : (
                      <div className="w-4 h-4 rounded-full bg-red-500" />
                    )}
                    <span className="text-sm font-medium">
                      {validationResult.isValid
                        ? '参数验证通过'
                        : '参数验证失败'}
                    </span>
                  </div>

                  {!validationResult.isValid &&
                    validationResult.errors.length > 0 && (
                      <div className="mt-2 text-sm text-red-700">
                        <ul className="list-disc list-inside space-y-1">
                          {validationResult.errors.map((error, index) => (
                            <li key={index}>{error}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                  {validationResult.warnings.length > 0 && (
                    <div className="mt-2 text-sm text-yellow-700">
                      <p className="font-medium">建议:</p>
                      <ul className="list-disc list-inside space-y-1">
                        {validationResult.warnings.map((warning, index) => (
                          <li key={index}>{warning}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* 实时结果展示 */}
        {showResults && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold flex items-center space-x-2">
              <Activity className="h-5 w-5" />
              <span>策略表现</span>
              {strategyResult && (
                <span className="text-sm text-muted-foreground">
                  实时分析结果
                </span>
              )}
            </h3>

            <RealTimeResults
              result={strategyResult}
              isLoading={isLoading}
              isUpdating={isUpdating}
              error={error}
              lastUpdate={lastUpdate}
              onRefresh={handleForceRefresh}
              showDetails={!compactResults}
              compact={compactResults}
            />
          </div>
        )}
      </div>

      {/* 错误提示 */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-4">
            <div className="flex items-center space-x-3">
              <div className="w-4 h-4 rounded-full bg-red-500" />
              <div>
                <p className="font-medium text-red-900">分析错误</p>
                <p className="text-sm text-red-700">{error}</p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleForceRefresh}
                  className="mt-2"
                >
                  <RefreshCw className="h-4 w-4 mr-1" />
                  重试
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 使用提示 */}
      <Card className="border-blue-200 bg-blue-50">
        <CardContent className="p-4">
          <div className="flex items-start space-x-3">
            <Info className="h-5 w-5 text-blue-600 mt-0.5" />
            <div className="text-sm text-blue-800">
              <p className="font-medium mb-2">使用提示</p>
              <ul className="space-y-1">
                <li>• 调整参数后系统会自动进行分析（响应时间&lt;500ms）</li>
                <li>• 开启实时模式可获得即时反馈</li>
                <li>• 使用预设参数可快速切换常用策略配置</li>
                <li>• 所有分析结果基于历史数据，仅供参考</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default RealTimeParameterDashboard;
