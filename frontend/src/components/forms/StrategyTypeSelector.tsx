'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { StrategyType, StrategyTypeConfig } from '@/types/strategy';
import {
  STRATEGY_CATEGORY_LABELS,
  STRATEGY_STATUS_LABELS,
  STRATEGY_TYPES,
  getAvailableStrategies,
  getStrategiesByCategory,
} from '@/constants/strategyTypes';

interface StrategyTypeSelectorProps {
  selectedStrategy: StrategyType;
  onStrategyChange: (strategyType: StrategyType) => void;
  className?: string;
}

export function StrategyTypeSelector({
  selectedStrategy,
  onStrategyChange,
  className,
}: StrategyTypeSelectorProps) {
  const [viewMode, setViewMode] = useState<'all' | 'category'>('all');
  const { categories, categorizedStrategies } = getStrategiesByCategory();

  const handleStrategySelect = (strategyType: StrategyType) => {
    const strategy = STRATEGY_TYPES.find((s) => s.id === strategyType);
    if (strategy?.status === 'available') {
      onStrategyChange(strategyType);
    }
  };

  const renderStrategyCard = (strategy: StrategyTypeConfig) => {
    const isSelected = selectedStrategy === strategy.id;
    const statusConfig = STRATEGY_STATUS_LABELS[strategy.status];
    const categoryConfig = STRATEGY_CATEGORY_LABELS[strategy.category];
    const isAvailable = strategy.status === 'available';

    return (
      <Card
        key={strategy.id}
        className={`
          relative cursor-pointer transition-all duration-200 hover:shadow-md
          ${isSelected ? 'ring-2 ring-blue-500 border-blue-200' : 'border-gray-200'}
          ${!isAvailable ? 'opacity-75 cursor-not-allowed' : 'hover:border-blue-300'}
        `}
        onClick={() => isAvailable && handleStrategySelect(strategy.id)}
      >
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <CardTitle className="text-lg flex items-center gap-2">
                {strategy.name}
                {isSelected && (
                  <div className="w-2 h-2 bg-blue-500 rounded-full" />
                )}
              </CardTitle>
              <CardDescription className="text-sm mt-1">
                {strategy.description}
              </CardDescription>
            </div>
            <div className="flex flex-col gap-2 ml-4">
              <Badge
                variant="secondary"
                className={`
                  ${statusConfig.color}
                  ${statusConfig.borderColor}
                  border
                  text-xs
                `}
              >
                {statusConfig.text}
              </Badge>
              <Badge
                variant="outline"
                className={`${categoryConfig.color} text-xs`}
              >
                {categoryConfig.text}
              </Badge>
            </div>
          </div>
        </CardHeader>

        {strategy.status !== 'available' && (
          <CardContent className="pt-0">
            <div className="text-xs text-gray-500 bg-gray-50 p-2 rounded">
              {strategy.status === 'coming-soon' &&
                '此策略正在开发中，敬请期待！'}
              {strategy.status === 'experimental' &&
                '此策略为实验性功能，建议谨慎使用。'}
            </div>
          </CardContent>
        )}
      </Card>
    );
  };

  return (
    <div className={className}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold">策略类型选择</h3>
          <p className="text-sm text-gray-600">选择适合您交易风格的策略类型</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant={viewMode === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setViewMode('all')}
          >
            全部策略
          </Button>
          <Button
            variant={viewMode === 'category' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setViewMode('category')}
          >
            分类浏览
          </Button>
        </div>
      </div>

      {viewMode === 'all' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {STRATEGY_TYPES.map(renderStrategyCard)}
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(categorizedStrategies).map(
            ([categoryKey, strategies]) => (
              <div key={categoryKey}>
                <div className="flex items-center gap-2 mb-3">
                  <Badge
                    variant="outline"
                    className={
                      STRATEGY_CATEGORY_LABELS[
                        categoryKey as keyof typeof STRATEGY_CATEGORY_LABELS
                      ].color
                    }
                  >
                    {categories[categoryKey as keyof typeof categories].name}
                  </Badge>
                  <span className="text-sm text-gray-600">
                    {
                      categories[categoryKey as keyof typeof categories]
                        .description
                    }
                  </span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 ml-4">
                  {strategies.map(renderStrategyCard)}
                </div>
              </div>
            ),
          )}
        </div>
      )}

      <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-start gap-2">
          <div className="w-5 h-5 text-blue-600 mt-0.5">
            <svg fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="flex-1">
            <h4 className="text-sm font-medium text-blue-900 mb-1">
              策略选择建议
            </h4>
            <ul className="text-xs text-blue-800 space-y-1">
              <li>
                • <strong>初学者</strong>：建议从单均线策略开始，简单易懂
              </li>
              <li>
                • <strong>进阶用户</strong>：可尝试双均线策略，信号更稳定
              </li>
              <li>
                • <strong>专业用户</strong>：RSI和MACD策略适合震荡市场
              </li>
              <li>
                • <strong>实验性功能</strong>：请在充分理解风险后使用
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
