import {
  ParameterGroup,
  ParameterValidation,
  ParameterValidationResult,
  StrategyParameters,
} from '@/types/parameter.types';

/**
 * 生成唯一ID
 */
export function generateId(): string {
  return Math.random().toString(36).substr(2, 9);
}

// 参数验证规则配置
export const PARAMETER_RULES: Record<
  keyof StrategyParameters,
  ParameterValidation
> = {
  movingAveragePeriod: {
    min: 5,
    max: 200,
    step: 1,
    precision: 0,
    required: true,
  },
  stopLoss: {
    min: 0,
    max: 50,
    step: 0.1,
    precision: 1,
    required: true,
  },
  takeProfit: {
    min: 0,
    max: 50,
    step: 0.1,
    precision: 1,
    required: true,
  },
};

// 默认参数值
export const DEFAULT_PARAMETERS: StrategyParameters = {
  movingAveragePeriod: 20,
  stopLoss: 5.0,
  takeProfit: 10.0,
};

/**
 * 验证单个参数值
 */
export function validateParameter(
  parameter: keyof StrategyParameters,
  value: number,
  context?: {
    otherParameters?: Partial<StrategyParameters>;
    groupName?: string;
  },
): ParameterValidationResult {
  const rule = PARAMETER_RULES[parameter];
  const errors: string[] = [];
  const warnings: string[] = [];

  // 基本验证
  if (
    rule.required &&
    (value === undefined || value === null || isNaN(value))
  ) {
    errors.push(`${getParameterLabel(parameter)} 是必填项`);
    return { isValid: false, errors, warnings };
  }

  if (typeof value !== 'number') {
    errors.push(`${getParameterLabel(parameter)} 必须是数字`);
    return { isValid: false, errors, warnings };
  }

  // 范围验证
  if (value < rule.min) {
    errors.push(`${getParameterLabel(parameter)} 不能小于 ${rule.min}`);
  }
  if (value > rule.max) {
    errors.push(`${getParameterLabel(parameter)} 不能大于 ${rule.max}`);
  }

  // 步进验证
  if (rule.step && value !== rule.min && value !== rule.max) {
    const decimalPlaces = rule.precision || 0;
    const steppedValue = Math.round(value / rule.step) * rule.step;
    const tolerance = Math.pow(10, -decimalPlaces) * 0.5;

    if (Math.abs(value - steppedValue) > tolerance) {
      warnings.push(
        `${getParameterLabel(parameter)} 建议使用 ${rule.step} 的步进值`,
      );
    }
  }

  // 业务逻辑验证
  if (context?.otherParameters) {
    const businessWarnings = validateBusinessLogic(
      parameter,
      value,
      context.otherParameters,
    );
    warnings.push(...businessWarnings);
  }

  // 参数特定建议
  const parameterWarnings = getParameterSpecificWarnings(parameter, value);
  warnings.push(...parameterWarnings);

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

/**
 * 验证所有参数
 */
export function validateAllParameters(
  parameters: StrategyParameters,
  groupName?: string,
): ParameterValidationResult {
  const allErrors: string[] = [];
  const allWarnings: string[] = [];

  // 验证每个参数
  Object.entries(parameters).forEach(([key, value]) => {
    const result = validateParameter(key as keyof StrategyParameters, value, {
      otherParameters: parameters,
      groupName,
    });
    allErrors.push(...result.errors);
    allWarnings.push(...result.warnings);
  });

  // 参数间关系验证
  const relationshipWarnings = validateParameterRelationships(parameters);
  allWarnings.push(...relationshipWarnings);

  return {
    isValid: allErrors.length === 0,
    errors: allErrors,
    warnings: allWarnings,
  };
}

/**
 * 验证参数组
 */
export function validateParameterGroup(
  group: ParameterGroup,
): ParameterValidationResult {
  const baseValidation = validateAllParameters(group.parameters, group.name);

  const groupErrors: string[] = [...baseValidation.errors];
  const groupWarnings: string[] = [...baseValidation.warnings];

  // 参数组特定验证
  if (!group.name || group.name.trim() === '') {
    groupErrors.push('参数组名称不能为空');
  }

  if (group.name && group.name.length > 50) {
    groupWarnings.push('参数组名称过长，建议控制在50字符以内');
  }

  return {
    isValid: groupErrors.length === 0,
    errors: groupErrors,
    warnings: groupWarnings,
  };
}

/**
 * 应用参数约束和格式化
 */
export function applyParameterConstraints(
  parameter: keyof StrategyParameters,
  value: number,
): number {
  const rule = PARAMETER_RULES[parameter];

  if (isNaN(value)) {
    return rule.min;
  }

  // 应用范围限制
  let constrainedValue = Math.max(rule.min, Math.min(rule.max, value));

  // 应用精度
  if (rule.precision !== undefined) {
    const factor = Math.pow(10, rule.precision);
    constrainedValue = Math.round(constrainedValue * factor) / factor;
  }

  // 应用步进
  if (rule.step) {
    constrainedValue = Math.round(constrainedValue / rule.step) * rule.step;
  }

  return constrainedValue;
}

/**
 * 格式化参数值显示
 */
export function formatParameterValue(
  parameter: keyof StrategyParameters,
  value: number,
): string {
  const rule = PARAMETER_RULES[parameter];

  if (rule.precision !== undefined) {
    return value.toFixed(rule.precision);
  }

  return value.toString();
}

/**
 * 获取参数显示标签
 */
export function getParameterLabel(parameter: keyof StrategyParameters): string {
  const labels = {
    movingAveragePeriod: '移动平均周期',
    stopLoss: '止损百分比',
    takeProfit: '止盈百分比',
  };

  return labels[parameter] || parameter;
}

/**
 * 获取参数单位
 */
export function getParameterUnit(parameter: keyof StrategyParameters): string {
  switch (parameter) {
    case 'movingAveragePeriod':
      return '天';
    case 'stopLoss':
    case 'takeProfit':
      return '%';
    default:
      return '';
  }
}

/**
 * 计算参数相似度
 */
export function calculateParameterSimilarity(
  params1: StrategyParameters,
  params2: StrategyParameters,
): number {
  const keys = Object.keys(params1) as (keyof StrategyParameters)[];
  let totalDifference = 0;
  let parameterCount = 0;

  for (const key of keys) {
    const rule = PARAMETER_RULES[key];
    const range = rule.max - rule.min;
    const difference = Math.abs(params1[key] - params2[key]);
    const normalizedDifference = difference / range;

    totalDifference += normalizedDifference;
    parameterCount++;
  }

  const averageDifference = totalDifference / parameterCount;
  return Math.max(0, 1 - averageDifference); // 返回0-1的相似度
}

/**
 * 生成参数描述
 */
export function generateParameterDescription(
  parameters: StrategyParameters,
): string {
  const { movingAveragePeriod, stopLoss, takeProfit } = parameters;

  let description = `使用${movingAveragePeriod}日移动平均线`;

  if (stopLoss > 0 && takeProfit > 0) {
    description += `，设置${formatParameterValue('stopLoss', stopLoss)}%止损和${formatParameterValue('takeProfit', takeProfit)}%止盈`;
  } else if (stopLoss > 0) {
    description += `，设置${formatParameterValue('stopLoss', stopLoss)}%止损`;
  } else if (takeProfit > 0) {
    description += `，设置${formatParameterValue('takeProfit', takeProfit)}%止盈`;
  }

  return description;
}

/**
 * 检查参数是否相等
 */
export function areParametersEqual(
  params1: StrategyParameters,
  params2: StrategyParameters,
  tolerance = 0.01,
): boolean {
  const keys = Object.keys(params1) as (keyof StrategyParameters)[];

  for (const key of keys) {
    const rule = PARAMETER_RULES[key];
    const actualTolerance = rule.precision
      ? Math.pow(10, -rule.precision) * 0.5
      : tolerance;

    if (Math.abs(params1[key] - params2[key]) > actualTolerance) {
      return false;
    }
  }

  return true;
}

/**
 * 验证业务逻辑
 */
function validateBusinessLogic(
  parameter: keyof StrategyParameters,
  value: number,
  otherParameters: Partial<StrategyParameters>,
): string[] {
  const warnings: string[] = [];

  switch (parameter) {
    case 'stopLoss':
      if (otherParameters.takeProfit && value >= otherParameters.takeProfit) {
        warnings.push('止损值不应大于或等于止盈值');
      }
      break;

    case 'takeProfit':
      if (otherParameters.stopLoss && value <= otherParameters.stopLoss) {
        warnings.push('止盈值应大于止损值');
      }
      break;

    case 'movingAveragePeriod':
      // 移动平均周期的业务逻辑检查
      break;
  }

  return warnings;
}

/**
 * 获取参数特定警告
 */
function getParameterSpecificWarnings(
  parameter: keyof StrategyParameters,
  value: number,
): string[] {
  const warnings: string[] = [];

  switch (parameter) {
    case 'movingAveragePeriod':
      if (value <= 10) {
        warnings.push('短期均线可能产生较多噪音信号');
      } else if (value >= 100) {
        warnings.push('长期均线可能响应较慢，错过短期机会');
      }
      break;

    case 'stopLoss':
      if (value <= 1) {
        warnings.push('止损设置过严可能导致频繁止损');
      } else if (value >= 20) {
        warnings.push('止损设置过宽可能导致单笔损失过大');
      }
      break;

    case 'takeProfit':
      if (value <= 3) {
        warnings.push('止盈设置过低可能限制收益潜力');
      } else if (value >= 30) {
        warnings.push('止盈设置过高可能导致难以达到目标');
      }
      break;
  }

  return warnings;
}

/**
 * 验证参数间关系
 */
function validateParameterRelationships(
  parameters: StrategyParameters,
): string[] {
  const warnings: string[] = [];

  const { stopLoss, takeProfit, movingAveragePeriod } = parameters;

  // 风险收益比例检查
  if (stopLoss > 0 && takeProfit > 0) {
    const ratio = takeProfit / stopLoss;
    if (ratio < 1) {
      warnings.push('建议止盈/止损比例保持在1:1以上');
    } else if (ratio > 10) {
      warnings.push('止盈/止损比例过大，可能难以达到止盈目标');
    } else if (ratio >= 2 && ratio <= 3) {
      // 这是一个好的比例，但可以作为建议信息而不是警告
    }
  }

  // 周期与风险控制的协调性检查
  if (movingAveragePeriod <= 10 && stopLoss > 10) {
    warnings.push('短期均线配合较宽止损，可能导致策略响应不及时');
  }

  if (movingAveragePeriod >= 100 && stopLoss < 2) {
    warnings.push('长期均线配合过严止损，可能导致频繁止损');
  }

  return warnings;
}

/**
 * 获取参数风险评估
 */
export function getParameterRiskAssessment(parameters: StrategyParameters): {
  level: 'low' | 'medium' | 'high' | 'very_high';
  score: number; // 0-100
  factors: string[];
} {
  let riskScore = 0;
  const factors: string[] = [];

  // 移动平均周期风险
  const { movingAveragePeriod, stopLoss, takeProfit } = parameters;

  if (movingAveragePeriod <= 10) {
    riskScore += 30;
    factors.push('短期均线增加交易频率和噪音风险');
  } else if (movingAveragePeriod <= 20) {
    riskScore += 20;
    factors.push('中短期均线存在一定噪音风险');
  } else if (movingAveragePeriod >= 100) {
    riskScore += 10;
    factors.push('长期均线可能错过短期机会');
  }

  // 止损风险
  if (stopLoss <= 2) {
    riskScore += 25;
    factors.push('止损设置过严增加止损频率');
  } else if (stopLoss >= 15) {
    riskScore += 15;
    factors.push('止损设置过宽增加单笔损失风险');
  }

  // 止盈风险
  if (takeProfit <= 5) {
    riskScore += 15;
    factors.push('止盈设置过低限制收益潜力');
  } else if (takeProfit >= 30) {
    riskScore += 10;
    factors.push('止盈设置过高降低策略成功率');
  }

  // 风险收益比例
  if (stopLoss > 0 && takeProfit > 0) {
    const ratio = takeProfit / stopLoss;
    if (ratio < 1.5) {
      riskScore += 20;
      factors.push('风险收益比例不利于长期盈利');
    } else if (ratio > 5) {
      riskScore += 5;
      factors.push('风险收益比例可能过于理想化');
    }
  }

  // 确定风险等级
  let level: 'low' | 'medium' | 'high' | 'very_high' = 'low';
  if (riskScore >= 70) {
    level = 'very_high';
  } else if (riskScore >= 50) {
    level = 'high';
  } else if (riskScore >= 30) {
    level = 'medium';
  }

  return {
    level,
    score: Math.min(100, riskScore),
    factors,
  };
}
