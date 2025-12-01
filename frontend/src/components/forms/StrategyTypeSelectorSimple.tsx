'use client';

import { useMemo } from 'react';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { StrategyType, StrategyTypeConfig } from '@/types/strategy';
import {
  STRATEGY_CATEGORY_LABELS,
  STRATEGY_STATUS_LABELS,
  STRATEGY_TYPES,
  getAvailableStrategies,
} from '@/constants/strategyTypes';

interface StrategyTypeSelectorSimpleProps {
  selectedStrategy: StrategyType;
  onStrategyChange: (strategyType: StrategyType) => void;
  className?: string;
}

export function StrategyTypeSelectorSimple({
  selectedStrategy,
  onStrategyChange,
  className,
}: StrategyTypeSelectorSimpleProps) {
  // 使用useMemo来缓存计算结果，避免重复计算
  const selectedStrategyConfig = useMemo(
    () => STRATEGY_TYPES.find((s) => s.id === selectedStrategy),
    [selectedStrategy],
  );

  const handleStrategySelect = (strategyType: StrategyType) => {
    const strategy = STRATEGY_TYPES.find((s) => s.id === strategyType);
    if (strategy?.status === 'available') {
      onStrategyChange(strategyType);
    }
  };

  return (
    <div className={className}>
      <div className="mb-4">
        <label className="text-sm font-medium mb-2 block">策略类型选择</label>
        <Select value={selectedStrategy} onValueChange={handleStrategySelect}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="选择策略类型" />
          </SelectTrigger>
          <SelectContent>
            {STRATEGY_TYPES.map((strategy) => {
              const statusConfig = STRATEGY_STATUS_LABELS[strategy.status];
              const categoryConfig =
                STRATEGY_CATEGORY_LABELS[strategy.category];
              const isAvailable = strategy.status === 'available';

              return (
                <SelectItem
                  key={strategy.id}
                  value={strategy.id}
                  disabled={!isAvailable}
                >
                  <div className="flex items-center justify-between w-full">
                    <div className="flex flex-col items-start">
                      <span className="font-medium">{strategy.name}</span>
                      <span className="text-xs text-muted-foreground">
                        {strategy.description}
                      </span>
                    </div>
                    <div className="flex gap-1 ml-2">
                      <Badge
                        variant="secondary"
                        className={`${statusConfig.color} ${statusConfig.borderColor} border text-xs`}
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
                </SelectItem>
              );
            })}
          </SelectContent>
        </Select>
      </div>

      {/* 当前选择的策略信息 */}
      {selectedStrategyConfig && (
        <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <h4 className="font-medium text-gray-900 text-sm">
                {selectedStrategyConfig.name}
              </h4>
              <p className="text-xs text-gray-600 mt-1">
                {selectedStrategyConfig.description}
              </p>
            </div>
            <div className="text-right ml-4">
              <div className="text-xs text-gray-500">状态</div>
              <Badge
                variant="secondary"
                className={`${STRATEGY_STATUS_LABELS[selectedStrategyConfig.status].color} ${STRATEGY_STATUS_LABELS[selectedStrategyConfig.status].borderColor} border text-xs mt-1`}
              >
                {STRATEGY_STATUS_LABELS[selectedStrategyConfig.status].text}
              </Badge>
            </div>
          </div>
        </div>
      )}

      {/* 策略选择建议 */}
      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-start gap-2">
          <div className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0">
            <svg fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="flex-1">
            <h4 className="text-xs font-medium text-blue-900 mb-1">
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
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
