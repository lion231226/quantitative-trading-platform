'use client';

import {
  MovingAverageStrategyParams,
  StrategyParameterMeta,
} from '@/types/strategy';
import {
  STRATEGY_PARAMETER_META,
  formatParamValue,
} from '@/utils/strategyParams';
import { Button } from '@/components/ui/button';

interface ParameterInputProps {
  key_name: keyof MovingAverageStrategyParams;
  value: any;
  meta: StrategyParameterMeta;
  onChange: (key: keyof MovingAverageStrategyParams, value: any) => void;
}

export function ParameterInput({
  key_name,
  value,
  meta,
  onChange,
}: ParameterInputProps) {
  const handleChange = (newValue: any) => {
    onChange(key_name, newValue);
  };

  const renderInput = () => {
    switch (meta.type) {
      case 'select':
        return (
          <select
            value={value}
            onChange={(e) => handleChange(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {meta.options?.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        );

      case 'number':
        return (
          <div className="space-y-2">
            <input
              type="range"
              min={meta.min}
              max={meta.max}
              step={meta.step}
              value={value}
              onChange={(e) => handleChange(parseFloat(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-500">
                {meta.min} - {meta.max} {meta.unit}
              </span>
              <span className="text-sm font-medium">
                {formatParamValue(key_name, value)}
              </span>
            </div>
          </div>
        );

      case 'boolean':
        return (
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={value}
              onChange={(e) => handleChange(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm">{meta.description}</span>
          </label>
        );

      default:
        return (
          <input
            type="text"
            value={value}
            onChange={(e) => handleChange(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        );
    }
  };

  const getQuickButtons = () => {
    if (key_name === 'ma_period') {
      return (
        <div className="flex gap-2 mt-2">
          <Button variant="outline" size="sm" onClick={() => handleChange(10)}>
            短期(10天)
          </Button>
          <Button variant="outline" size="sm" onClick={() => handleChange(20)}>
            中期(20天)
          </Button>
          <Button variant="outline" size="sm" onClick={() => handleChange(60)}>
            长期(60天)
          </Button>
        </div>
      );
    }

    if (key_name === 'initial_capital') {
      return (
        <div className="flex gap-2 mt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleChange(10000)}
          >
            小额(1万)
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleChange(100000)}
          >
            中额(10万)
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleChange(500000)}
          >
            大额(50万)
          </Button>
        </div>
      );
    }

    if (key_name === 'stop_loss_pct') {
      return (
        <div className="flex gap-2 mt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleChange(0.01)}
          >
            严格(1%)
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleChange(0.02)}
          >
            标准(2%)
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleChange(0.05)}
          >
            宽松(5%)
          </Button>
        </div>
      );
    }

    if (key_name === 'take_profit_pct') {
      return (
        <div className="flex gap-2 mt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleChange(0.03)}
          >
            保守(3%)
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleChange(0.05)}
          >
            平衡(5%)
          </Button>
          <Button variant="outline" size="sm" onClick={() => handleChange(0.1)}>
            激进(10%)
          </Button>
        </div>
      );
    }

    return null;
  };

  return (
    <div className="space-y-3">
      <div>
        <label className="text-sm font-medium mb-2 block">
          {meta.description}
          {meta.unit && <span className="text-gray-500"> ({meta.unit})</span>}
        </label>
        {renderInput()}
        {getQuickButtons()}
      </div>
    </div>
  );
}
