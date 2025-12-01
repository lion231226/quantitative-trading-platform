/**
 * 数据验证工具函数
 */

// 验证日期格式
export function validateDate(dateString: string): boolean {
  const date = new Date(dateString);
  return !isNaN(date.getTime()) && !!dateString.match(/^\d{4}-\d{2}-\d{2}$/);
}

// 验证日期范围
export function validateDateRange(
  startDate: string,
  endDate: string,
): {
  isValid: boolean;
  error?: string;
} {
  if (!validateDate(startDate)) {
    return { isValid: false, error: '开始日期格式无效' };
  }

  if (!validateDate(endDate)) {
    return { isValid: false, error: '结束日期格式无效' };
  }

  const start = new Date(startDate);
  const end = new Date(endDate);
  const today = new Date();

  if (start >= end) {
    return { isValid: false, error: '开始日期必须早于结束日期' };
  }

  if (end > today) {
    return { isValid: false, error: '结束日期不能晚于今天' };
  }

  // 检查日期范围是否合理（不超过2年）
  const daysDiff = (end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24);
  if (daysDiff > 730) {
    return { isValid: false, error: '日期范围不能超过2年' };
  }

  if (daysDiff < 7) {
    return { isValid: false, error: '日期范围至少需要7天' };
  }

  return { isValid: true };
}

// 验证期货品种代码
export function validateSymbol(symbol: string): boolean {
  // 基本的期货品种代码格式验证
  return /^[A-Z0-9]{2,6}$/.test(symbol);
}

// 验证策略参数
export function validateStrategyParams(params: {
  ma_period?: number;
  window_size?: number;
  initial_capital?: number;
}): {
  isValid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  // 支持 ma_period 或 window_size 参数名
  const period = params.ma_period || params.window_size;
  if (!params || typeof period === 'undefined' || period < 5 || period > 200) {
    errors.push('均线周期必须在5-200天之间');
  }

  if (
    !params ||
    typeof params.initial_capital === 'undefined' ||
    params.initial_capital < 1000
  ) {
    errors.push('初始资金必须大于1000元');
  }

  if (params && params.initial_capital && params.initial_capital > 10000000) {
    errors.push('初始资金不能超过1000万元');
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

// 验证完整的策略提交表单
export function validateStrategyForm(form: {
  symbol: string;
  startDate: string;
  endDate: string;
  strategyType?: string;
  params: any;
}): {
  isValid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  // 验证期货品种
  if (!form.symbol || !validateSymbol(form.symbol)) {
    errors.push('请选择有效的期货品种');
  }

  // 验证日期范围
  const dateRangeValidation = validateDateRange(form.startDate, form.endDate);
  if (!dateRangeValidation.isValid) {
    errors.push(dateRangeValidation.error || '日期范围无效');
  }

  // 验证策略参数
  if (form.params) {
    // 提取通用参数进行验证
    const commonParams = {
      ma_period: form.params.ma_period || form.params.window_size,
      window_size: form.params.window_size || form.params.ma_period,
      initial_capital: form.params.initial_capital,
    };

    const paramsValidation = validateStrategyParams(commonParams);
    if (!paramsValidation.isValid) {
      errors.push(...paramsValidation.errors);
    }
  } else {
    errors.push('策略参数不能为空');
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

// 格式化错误消息
export function formatValidationErrors(errors: string[]): string {
  if (errors.length === 0) return '';
  if (errors.length === 1) return errors[0];

  return errors.map((error, index) => `${index + 1}. ${error}`).join('\n');
}
