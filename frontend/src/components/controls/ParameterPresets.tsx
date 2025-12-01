'use client';

import React, { useCallback, useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ParameterPreset, StrategyParameters } from '@/types/parameter.types';
import {
  Activity,
  BarChart3,
  Check,
  Copy,
  Edit,
  Plus,
  Shield,
  Star,
  Trash2,
  TrendingUp,
  Zap,
} from 'lucide-react';

interface ParameterPresetsProps {
  parameters: StrategyParameters;
  onPresetSelect: (preset: ParameterPreset) => void;
  onPresetSave?: (preset: ParameterPreset) => void;
  onPresetDelete?: (presetId: string) => void;
  onPresetEdit?: (preset: ParameterPreset) => void;
  disabled?: boolean;
  allowCustomPresets?: boolean;
  showBuiltIn?: boolean;
  showCustom?: boolean;
  className?: string;
}

// 内置预设配置
const BUILTIN_PRESETS: ParameterPreset[] = [
  {
    id: 'conservative',
    name: '保守策略',
    description: '长期均线，严格风险控制，适合新手',
    parameters: {
      movingAveragePeriod: 50,
      stopLoss: 3.0,
      takeProfit: 6.0,
    },
  },
  {
    id: 'balanced',
    name: '平衡策略',
    description: '中等周期，平衡风险收益，适合大多数投资者',
    parameters: {
      movingAveragePeriod: 20,
      stopLoss: 5.0,
      takeProfit: 10.0,
    },
  },
  {
    id: 'aggressive',
    name: '激进策略',
    description: '短期均线，高风险高收益，适合经验丰富的投资者',
    parameters: {
      movingAveragePeriod: 10,
      stopLoss: 2.0,
      takeProfit: 15.0,
    },
  },
  {
    id: 'scalping',
    name: '剥头皮策略',
    description: '超短期，快速交易，需要密切监控',
    parameters: {
      movingAveragePeriod: 5,
      stopLoss: 1.0,
      takeProfit: 2.0,
    },
  },
  {
    id: 'trend-following',
    name: '趋势跟踪',
    description: '长期趋势跟踪，耐心等待大趋势机会',
    parameters: {
      movingAveragePeriod: 100,
      stopLoss: 5.0,
      takeProfit: 25.0,
    },
  },
  {
    id: 'mean-reversion',
    name: '均值回归',
    description: '中期均线，基于价格回归均线的策略',
    parameters: {
      movingAveragePeriod: 30,
      stopLoss: 4.0,
      takeProfit: 8.0,
    },
  },
];

// 预设类别
const PRESET_CATEGORIES = {
  conservative: {
    name: '保守型',
    icon: Shield,
    color: 'green',
    description: '低风险，稳健收益',
  },
  balanced: {
    name: '平衡型',
    icon: BarChart3,
    color: 'blue',
    description: '中等风险，平衡收益',
  },
  aggressive: {
    name: '激进型',
    icon: TrendingUp,
    color: 'orange',
    description: '高风险，高收益',
  },
  specialized: {
    name: '专业型',
    icon: Activity,
    color: 'purple',
    description: '特定市场条件优化',
  },
};

// 根据参数推断预设类别
function categorizePreset(
  preset: ParameterPreset,
): keyof typeof PRESET_CATEGORIES {
  const { movingAveragePeriod, stopLoss, takeProfit } = preset.parameters;

  if (movingAveragePeriod >= 50 && stopLoss <= 3 && takeProfit <= 10) {
    return 'conservative';
  } else if (
    movingAveragePeriod >= 20 &&
    movingAveragePeriod <= 30 &&
    stopLoss >= 3 &&
    stopLoss <= 6
  ) {
    return 'balanced';
  } else if (movingAveragePeriod <= 15 || (stopLoss <= 2 && takeProfit >= 15)) {
    return 'aggressive';
  } else {
    return 'specialized';
  }
}

export function ParameterPresets({
  parameters,
  onPresetSelect,
  onPresetSave,
  onPresetDelete,
  onPresetEdit,
  disabled = false,
  allowCustomPresets = false,
  showBuiltIn = true,
  showCustom = true,
  className = '',
}: ParameterPresetsProps) {
  const [customPresets, setCustomPresets] = useState<ParameterPreset[]>(() => {
    // 从localStorage加载自定义预设
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem('trading-parameter-presets');
        return saved ? JSON.parse(saved) : [];
      } catch (error) {
        console.error('Failed to load custom presets:', error);
        return [];
      }
    }
    return [];
  });

  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [newPresetName, setNewPresetName] = useState('');
  const [newPresetDescription, setNewPresetDescription] = useState('');
  const [copiedPresetId, setCopiedPresetId] = useState<string | null>(null);

  // 检查当前参数是否匹配任何预设
  const currentPreset = useMemo(() => {
    const allPresets = [...BUILTIN_PRESETS, ...customPresets];
    return allPresets.find((preset) => {
      const params = preset.parameters;
      return (
        Math.abs(params.movingAveragePeriod - parameters.movingAveragePeriod) <
          0.01 &&
        Math.abs(params.stopLoss - parameters.stopLoss) < 0.01 &&
        Math.abs(params.takeProfit - parameters.takeProfit) < 0.01
      );
    });
  }, [parameters, customPresets]);

  // 按类别分组预设
  const presetsByCategory = useMemo(() => {
    const categories: Record<string, ParameterPreset[]> = {};

    // 初始化类别
    Object.keys(PRESET_CATEGORIES).forEach((key) => {
      categories[key] = [];
    });

    // 分组内置预设
    if (showBuiltIn) {
      BUILTIN_PRESETS.forEach((preset) => {
        const category = categorizePreset(preset);
        categories[category].push(preset);
      });
    }

    // 分组自定义预设
    if (showCustom) {
      customPresets.forEach((preset) => {
        const category = categorizePreset(preset);
        categories[category].push({ ...preset, isCustom: true });
      });
    }

    return categories;
  }, [showBuiltIn, showCustom, customPresets]);

  // 保存自定义预设
  const saveCustomPreset = useCallback(() => {
    if (!newPresetName.trim()) return;

    const newPreset: ParameterPreset = {
      id: `custom_${Date.now()}`,
      name: newPresetName.trim(),
      description: newPresetDescription.trim(),
      parameters: { ...parameters },
    };

    const updatedPresets = [...customPresets, newPreset];
    setCustomPresets(updatedPresets);

    // 保存到localStorage
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem(
          'trading-parameter-presets',
          JSON.stringify(updatedPresets),
        );
      } catch (error) {
        console.error('Failed to save custom presets:', error);
      }
    }

    onPresetSave?.(newPreset);

    // 重置对话框
    setNewPresetName('');
    setNewPresetDescription('');
    setShowSaveDialog(false);
  }, [
    newPresetName,
    newPresetDescription,
    parameters,
    customPresets,
    onPresetSave,
  ]);

  // 删除自定义预设
  const deleteCustomPreset = useCallback(
    (presetId: string) => {
      const updatedPresets = customPresets.filter((p) => p.id !== presetId);
      setCustomPresets(updatedPresets);

      // 保存到localStorage
      if (typeof window !== 'undefined') {
        try {
          localStorage.setItem(
            'trading-parameter-presets',
            JSON.stringify(updatedPresets),
          );
        } catch (error) {
          console.error('Failed to save custom presets:', error);
        }
      }

      onPresetDelete?.(presetId);
    },
    [customPresets, onPresetDelete],
  );

  // 复制预设参数
  const copyPresetParameters = useCallback((preset: ParameterPreset) => {
    const paramsText = `均线: ${preset.parameters.movingAveragePeriod}天, 止损: ${preset.parameters.stopLoss}%, 止盈: ${preset.parameters.takeProfit}%`;

    if (typeof window !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(paramsText);
      setCopiedPresetId(preset.id);
      setTimeout(() => setCopiedPresetId(null), 2000);
    }
  }, []);

  return (
    <Card className={className}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center space-x-2">
            <Zap className="h-5 w-5" />
            <span>参数预设</span>
          </CardTitle>
          <div className="flex items-center space-x-2">
            {currentPreset && (
              <div className="flex items-center space-x-1 text-sm text-green-600">
                <Check className="h-4 w-4" />
                <span>当前: {currentPreset.name}</span>
              </div>
            )}
            {allowCustomPresets && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowSaveDialog(true)}
                disabled={disabled}
              >
                <Plus className="h-4 w-4 mr-1" />
                保存当前
              </Button>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* 按类别显示预设 */}
        {Object.entries(PRESET_CATEGORIES).map(([categoryKey, category]) => {
          const presets = presetsByCategory[categoryKey];
          if (presets.length === 0) return null;

          const Icon = category.icon;
          const colorClass =
            category.color === 'green'
              ? 'text-green-600 bg-green-50 border-green-200'
              : category.color === 'blue'
                ? 'text-blue-600 bg-blue-50 border-blue-200'
                : category.color === 'orange'
                  ? 'text-orange-600 bg-orange-50 border-orange-200'
                  : 'text-purple-600 bg-purple-50 border-purple-200';

          return (
            <div key={categoryKey} className="space-y-3">
              <div className="flex items-center space-x-2">
                <Icon className="h-4 w-4" />
                <h4 className="font-medium">{category.name}</h4>
                <span className="text-sm text-muted-foreground">
                  ({category.description})
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {presets.map((preset) => {
                  const isActive = currentPreset?.id === preset.id;
                  const isCustom = 'isCustom' in preset;

                  return (
                    <Card
                      key={preset.id}
                      className={`p-4 cursor-pointer transition-all ${
                        isActive
                          ? 'ring-2 ring-blue-500 bg-blue-50'
                          : 'hover:bg-gray-50'
                      }`}
                    >
                      <div className="space-y-2">
                        <div className="flex items-start justify-between">
                          <div className="flex items-center space-x-2">
                            {isCustom && (
                              <Star className="h-4 w-4 text-yellow-500" />
                            )}
                            <h5 className="font-medium">{preset.name}</h5>
                          </div>
                          <div className="flex items-center space-x-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                copyPresetParameters(preset);
                              }}
                              className="h-6 w-6 p-0"
                              title="复制参数"
                            >
                              <Copy className="h-3 w-3" />
                            </Button>
                            {isCustom && (
                              <>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    onPresetEdit?.(preset);
                                  }}
                                  className="h-6 w-6 p-0"
                                  title="编辑"
                                >
                                  <Edit className="h-3 w-3" />
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    deleteCustomPreset(preset.id);
                                  }}
                                  className="h-6 w-6 p-0 text-red-600 hover:text-red-700"
                                  title="删除"
                                >
                                  <Trash2 className="h-3 w-3" />
                                </Button>
                              </>
                            )}
                          </div>
                        </div>

                        <p className="text-sm text-muted-foreground">
                          {preset.description}
                        </p>

                        <div className="grid grid-cols-3 gap-2 text-xs">
                          <div
                            className={`text-center p-2 rounded ${colorClass}`}
                          >
                            <div className="font-medium">
                              {preset.parameters.movingAveragePeriod}
                            </div>
                            <div className="text-xs opacity-75">均线</div>
                          </div>
                          <div
                            className={`text-center p-2 rounded ${colorClass}`}
                          >
                            <div className="font-medium">
                              {preset.parameters.stopLoss}%
                            </div>
                            <div className="text-xs opacity-75">止损</div>
                          </div>
                          <div
                            className={`text-center p-2 rounded ${colorClass}`}
                          >
                            <div className="font-medium">
                              {preset.parameters.takeProfit}%
                            </div>
                            <div className="text-xs opacity-75">止盈</div>
                          </div>
                        </div>

                        <Button
                          variant={isActive ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => onPresetSelect(preset)}
                          disabled={disabled}
                          className="w-full"
                        >
                          {isActive ? '已选择' : '应用预设'}
                        </Button>

                        {copiedPresetId === preset.id && (
                          <div className="text-xs text-green-600 text-center">
                            参数已复制到剪贴板
                          </div>
                        )}
                      </div>
                    </Card>
                  );
                })}
              </div>
            </div>
          );
        })}

        {/* 保存预设对话框 */}
        {showSaveDialog && (
          <Card className="border-blue-200 bg-blue-50">
            <CardContent className="p-4">
              <h4 className="font-medium mb-3">保存当前参数为预设</h4>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium mb-1">
                    预设名称
                  </label>
                  <input
                    type="text"
                    value={newPresetName}
                    onChange={(e) => setNewPresetName(e.target.value)}
                    placeholder="输入预设名称"
                    className="w-full border rounded px-3 py-2 text-sm"
                    maxLength={50}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                    描述（可选）
                  </label>
                  <textarea
                    value={newPresetDescription}
                    onChange={(e) => setNewPresetDescription(e.target.value)}
                    placeholder="描述这个预设的特点和适用场景"
                    className="w-full border rounded px-3 py-2 text-sm"
                    rows={2}
                    maxLength={200}
                  />
                </div>
                <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                  <span>当前参数:</span>
                  <span>
                    均线{parameters.movingAveragePeriod}天, 止损
                    {parameters.stopLoss}%, 止盈{parameters.takeProfit}%
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <Button
                    variant="default"
                    onClick={saveCustomPreset}
                    disabled={!newPresetName.trim()}
                  >
                    保存
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setShowSaveDialog(false);
                      setNewPresetName('');
                      setNewPresetDescription('');
                    }}
                  >
                    取消
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </CardContent>
    </Card>
  );
}

export default ParameterPresets;
