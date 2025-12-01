'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { BarChart3, Edit2, Play, Plus, TrendingUp, X } from 'lucide-react';
import {
  ColorConfig,
  ParameterGroup,
  StrategyParameters,
  StrategyResult,
} from '@/types/parameter.types';
import { parameterService } from '@/services/parameterService';
import { generateId } from '@/utils/parameterHelpers';

interface ParameterComparisonProps {
  symbol: string;
  startDate: string;
  endDate: string;
  onParameterSelect?: (group: ParameterGroup) => void;
  maxGroups?: number;
}

// 参数组颜色配置
const GROUP_COLORS = [
  {
    bg: 'bg-blue-100',
    border: 'border-blue-300',
    text: 'text-blue-800',
    chart: '#3B82F6',
  },
  {
    bg: 'bg-green-100',
    border: 'border-green-300',
    text: 'text-green-800',
    chart: '#10B981',
  },
  {
    bg: 'bg-purple-100',
    border: 'border-purple-300',
    text: 'text-purple-800',
    chart: '#8B5CF6',
  },
  {
    bg: 'bg-orange-100',
    border: 'border-orange-300',
    text: 'text-orange-800',
    chart: '#F97316',
  },
];

const DEFAULT_PARAMETERS: StrategyParameters = {
  movingAveragePeriod: 20,
  stopLoss: 5.0,
  takeProfit: 10.0,
};

// 辅助函数：获取颜色配置
const getColorConfig = (color?: ColorConfig | string): ColorConfig => {
  if (!color) {
    return GROUP_COLORS[0]; // 默认颜色
  }

  if (typeof color === 'string') {
    // 如果是字符串，查找对应的颜色配置
    const colorConfig = GROUP_COLORS.find((c) => c.chart === color);
    return colorConfig || GROUP_COLORS[0];
  }

  return color; // 已经是ColorConfig类型
};

export const ParameterComparison: React.FC<ParameterComparisonProps> = ({
  symbol,
  startDate,
  endDate,
  onParameterSelect,
  maxGroups = 4,
}) => {
  const [parameterGroups, setParameterGroups] = useState<ParameterGroup[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [editingGroup, setEditingGroup] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');
  const [isRunningAll, setIsRunningAll] = useState(false);

  // 添加参数组
  const addParameterGroup = useCallback(() => {
    if (parameterGroups.length >= maxGroups) {
      return;
    }

    const newGroup: ParameterGroup = {
      id: generateId(),
      name: `参数组 ${parameterGroups.length + 1}`,
      parameters: { ...DEFAULT_PARAMETERS },
      color: GROUP_COLORS[parameterGroups.length]?.chart || '#3B82F6',
      isActive: true,
    };

    setParameterGroups((prev) => [...prev, newGroup]);
  }, [parameterGroups.length, maxGroups]);

  // 删除参数组
  const removeParameterGroup = useCallback((groupId: string) => {
    setParameterGroups((prev) => prev.filter((group) => group.id !== groupId));
  }, []);

  // 重命名参数组
  const renameGroup = useCallback((groupId: string, newName: string) => {
    setParameterGroups((prev) =>
      prev.map((group) =>
        group.id === groupId ? { ...group, name: newName } : group,
      ),
    );
    setEditingGroup(null);
    setEditingName('');
  }, []);

  // 更新参数组参数
  const updateGroupParameters = useCallback(
    (groupId: string, parameters: StrategyParameters) => {
      setParameterGroups((prev) =>
        prev.map((group) =>
          group.id === groupId ? { ...group, parameters } : group,
        ),
      );
    },
    [],
  );

  // 运行单个参数组回测
  const runSingleBacktest = useCallback(
    async (group: ParameterGroup) => {
      setIsLoading(true);

      try {
        // 标记为运行中
        setParameterGroups((prev) =>
          prev.map((g) =>
            g.id === group.id ? { ...g, results: undefined } : g,
          ),
        );

        // 调用策略服务进行回测
        const result = await parameterService.runBacktest({
          symbol,
          startDate,
          endDate,
          parameters: group.parameters,
        });

        // 更新结果
        setParameterGroups((prev) =>
          prev.map((g) => (g.id === group.id ? { ...g, results: result } : g)),
        );

        return result;
      } catch (error) {
        console.error('参数组回测失败:', error);
        throw error;
      } finally {
        setIsLoading(false);
      }
    },
    [symbol, startDate, endDate],
  );

  // 运行所有参数组回测
  const runAllBacktests = useCallback(async () => {
    setIsRunningAll(true);

    try {
      // 并行运行所有参数组
      const promises = parameterGroups.map((group) =>
        parameterService
          .runBacktest({
            symbol,
            startDate,
            endDate,
            parameters: group.parameters,
          })
          .then((result) => ({ groupId: group.id, result })),
      );

      const results = await Promise.all(promises);

      // 更新所有结果
      setParameterGroups((prev) =>
        prev.map((group) => {
          const groupResult = results.find((r) => r.groupId === group.id);
          return groupResult
            ? { ...group, results: groupResult.result }
            : group;
        }),
      );
    } catch (error) {
      console.error('批量回测失败:', error);
      throw error;
    } finally {
      setIsRunningAll(false);
    }
  }, [parameterGroups, symbol, startDate, endDate]);

  // 初始化时添加一个默认参数组
  useEffect(() => {
    if (parameterGroups.length === 0) {
      addParameterGroup();
    }
  }, [parameterGroups.length, addParameterGroup]);

  // 格式化结果数值
  const formatValue = (value: number, precision: number = 2): string => {
    return value.toFixed(precision);
  };

  return (
    <div className="space-y-6">
      {/* 头部操作区域 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <BarChart3 className="h-5 w-5 text-gray-600" />
          <h3 className="text-lg font-semibold text-gray-900">参数对比分析</h3>
          <span className="text-sm text-gray-500">
            ({parameterGroups.length}/{maxGroups})
          </span>
        </div>

        <div className="flex items-center space-x-2">
          {parameterGroups.length > 0 && (
            <button
              onClick={runAllBacktests}
              disabled={isRunningAll || isLoading}
              className="flex items-center space-x-1 px-3 py-1.5 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Play className="h-4 w-4" />
              <span>{isRunningAll ? '运行中...' : '运行全部'}</span>
            </button>
          )}

          <button
            onClick={addParameterGroup}
            disabled={parameterGroups.length >= maxGroups}
            className="flex items-center space-x-1 px-3 py-1.5 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Plus className="h-4 w-4" />
            <span>添加参数组</span>
          </button>
        </div>
      </div>

      {/* 参数组列表 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {parameterGroups.map((group, index) => {
          const colorConfig = getColorConfig(group.color);

          return (
            <div
              key={group.id}
              className={`border-2 rounded-lg p-4 transition-all ${
                colorConfig.border
              } ${group.isActive ? 'shadow-md' : 'shadow-sm'}`}
            >
              {/* 参数组头部 */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-2">
                  <div className={`w-3 h-3 rounded-full ${colorConfig.bg}`} />
                  {editingGroup === group.id ? (
                    <input
                      type="text"
                      value={editingName}
                      onChange={(e) => setEditingName(e.target.value)}
                      onBlur={() => renameGroup(group.id, editingName)}
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          renameGroup(group.id, editingName);
                        }
                      }}
                      className="px-2 py-1 text-sm font-medium border border-gray-300 rounded"
                      autoFocus
                    />
                  ) : (
                    <h4 className="text-sm font-semibold text-gray-900">
                      {group.name}
                    </h4>
                  )}
                </div>

                <div className="flex items-center space-x-1">
                  <button
                    onClick={() => {
                      setEditingGroup(group.id);
                      setEditingName(group.name);
                    }}
                    className="p-1 text-gray-400 hover:text-gray-600"
                  >
                    <Edit2 className="h-4 w-4" />
                  </button>

                  <button
                    onClick={() => removeParameterGroup(group.id)}
                    disabled={parameterGroups.length <= 1}
                    className="p-1 text-red-400 hover:text-red-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* 参数配置 */}
              <div className="space-y-3 mb-4">
                <div>
                  <label className="text-xs font-medium text-gray-700">
                    均线周期: {group.parameters.movingAveragePeriod}
                  </label>
                  <input
                    type="range"
                    min="5"
                    max="200"
                    value={group.parameters.movingAveragePeriod}
                    onChange={(e) =>
                      updateGroupParameters(group.id, {
                        ...group.parameters,
                        movingAveragePeriod: Number(e.target.value),
                      })
                    }
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs font-medium text-gray-700">
                      止损: {group.parameters.stopLoss}%
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="50"
                      step="0.1"
                      value={group.parameters.stopLoss}
                      onChange={(e) =>
                        updateGroupParameters(group.id, {
                          ...group.parameters,
                          stopLoss: Number(e.target.value),
                        })
                      }
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-medium text-gray-700">
                      止盈: {group.parameters.takeProfit}%
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="50"
                      step="0.1"
                      value={group.parameters.takeProfit}
                      onChange={(e) =>
                        updateGroupParameters(group.id, {
                          ...group.parameters,
                          takeProfit: Number(e.target.value),
                        })
                      }
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                    />
                  </div>
                </div>
              </div>

              {/* 操作按钮 */}
              <div className="flex items-center space-x-2 mb-3">
                <button
                  onClick={() => runSingleBacktest(group)}
                  disabled={isLoading}
                  className="flex-1 flex items-center justify-center space-x-1 px-2 py-1.5 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  <TrendingUp className="h-3 w-3" />
                  <span>运行回测</span>
                </button>

                {onParameterSelect && (
                  <button
                    onClick={() => onParameterSelect(group)}
                    className="flex-1 px-2 py-1.5 border border-gray-300 text-gray-700 text-xs rounded hover:bg-gray-50"
                  >
                    选择此组
                  </button>
                )}
              </div>

              {/* 结果展示 */}
              {group.results ? (
                <div className={`p-3 rounded-lg ${colorConfig.bg}`}>
                  <h5 className="text-xs font-semibold mb-2 text-gray-700">
                    回测结果
                  </h5>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-gray-600">总收益:</span>
                      <span className={`ml-1 font-medium ${colorConfig.text}`}>
                        {formatValue(group.results.totalReturn)}%
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600">夏普比率:</span>
                      <span className={`ml-1 font-medium ${colorConfig.text}`}>
                        {formatValue(group.results.sharpeRatio)}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600">最大回撤:</span>
                      <span className={`ml-1 font-medium ${colorConfig.text}`}>
                        {formatValue(group.results.maxDrawdown)}%
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600">胜率:</span>
                      <span className={`ml-1 font-medium ${colorConfig.text}`}>
                        {formatValue(group.results.winRate)}%
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600">交易次数:</span>
                      <span className={`ml-1 font-medium ${colorConfig.text}`}>
                        {group.results.totalTrades}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600">盈亏比:</span>
                      <span className={`ml-1 font-medium ${colorConfig.text}`}>
                        {formatValue(group.results.profitFactor)}
                      </span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-3 text-gray-500 text-xs">
                  {isLoading ? '运行中...' : '暂无结果'}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* 空状态 */}
      {parameterGroups.length === 0 && (
        <div className="text-center py-8">
          <BarChart3 className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <p className="text-gray-600 mb-4">还没有参数组</p>
          <button
            onClick={addParameterGroup}
            className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            <span>添加第一个参数组</span>
          </button>
        </div>
      )}

      {/* 对比分析提示 */}
      {parameterGroups.length > 1 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-blue-900 mb-2">对比分析</h4>
          <p className="text-sm text-blue-700">
            您已添加 {parameterGroups.length}{' '}
            组参数进行对比。点击"运行全部"可以并行运行所有组的回测，
            结果将显示在各组的卡片中，便于直观比较不同参数的表现差异。
          </p>
        </div>
      )}
    </div>
  );
};

export default ParameterComparison;
