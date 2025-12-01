/**
 * 输入验证和安全清理工具
 *
 * 功能:
 * 1. 实现所有API端点的输入参数验证
 * 2. 配置XSS防护和数据清理机制
 * 3. SQL注入防护
 * 4. 建立输入验证的单元测试
 */

import { z } from 'zod';

// 输入清理函数
export const sanitizeInput = (input: string): string => {
  if (typeof input !== 'string') {
    return '';
  }

  return input
    // 移除潜在危险字符
    .replace(/[<>]/g, '')
    // 移除JavaScript事件处理器
    .replace(/on\w+\s*=/gi, '')
    // 移除JavaScript协议
    .replace(/javascript:/gi, '')
    // 移除data URL
    .replace(/data:(.*?);base64,/gi, '')
    // 标准化空白字符
    .trim()
    // 限制长度
    .substring(0, 1000);
};

// XSS防护函数
export const escapeHtml = (unsafe: string): string => {
  if (typeof unsafe !== 'string') {
    return '';
  }

  return unsafe
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
    .replace(/\//g, '&#x2F;');
};

// SQL注入防护函数
export const escapeSql = (input: string): string => {
  if (typeof input !== 'string') {
    return '';
  }

  return input
    .replace(/'/g, "''")
    .replace(/"/g, '""')
    .replace(/;/g, '')
    .replace(/--/g, '')
    .replace(/\/\*/g, '')
    .replace(/\*\//g, '')
    .replace(/xp_/gi, '')
    .replace(/sp_/gi, '');
};

// 通用验证规则
export const commonValidations = {
  // 邮箱验证
  email: z.string()
    .email('邮箱格式不正确')
    .max(254, '邮箱长度不能超过254个字符')
    .transform(sanitizeInput),

  // 用户名验证
  username: z.string()
    .min(3, '用户名至少3个字符')
    .max(50, '用户名不能超过50个字符')
    .regex(/^[a-zA-Z0-9_-]+$/, '用户名只能包含字母、数字、下划线和连字符')
    .transform(sanitizeInput),

  // 密码验证
  password: z.string()
    .min(8, '密码至少8个字符')
    .max(128, '密码不能超过128个字符')
    .regex(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/, '密码必须包含大小写字母和数字'),

  // ID验证
  id: z.string()
    .regex(/^[a-zA-Z0-9_-]+$/, 'ID格式不正确')
    .max(100, 'ID长度不能超过100个字符')
    .transform(sanitizeInput),

  // 分页参数验证
  page: z.coerce.number()
    .int('页码必须是整数')
    .min(1, '页码必须大于0')
    .max(1000, '页码不能超过1000'),

  limit: z.coerce.number()
    .int('每页数量必须是整数')
    .min(1, '每页数量必须大于0')
    .max(100, '每页数量不能超过100'),

  // 排序参数验证
  sortBy: z.enum([
    'createdAt', 'updatedAt', 'name', 'id', 'status', 'priority'
  ], { errorMap: () => ({ message: '无效的排序字段' }) }),

  sortOrder: z.enum(['asc', 'desc'], {
    errorMap: () => ({ message: '排序顺序必须是 asc 或 desc' })
  }),

  // 搜索关键词验证
  searchQuery: z.string()
    .min(1, '搜索关键词不能为空')
    .max(200, '搜索关键词不能超过200个字符')
    .transform(sanitizeInput),

  // URL验证
  url: z.string()
    .url('URL格式不正确')
    .max(2048, 'URL长度不能超过2048个字符')
    .transform(sanitizeInput),

  // 文本内容验证
  textContent: z.string()
    .min(1, '内容不能为空')
    .max(10000, '内容长度不能超过10000个字符')
    .transform(escapeHtml),

  // JSON验证
  jsonString: z.string()
    .refine((val) => {
      try {
        JSON.parse(val);
        return true;
      } catch {
        return false;
      }
    }, '无效的JSON格式')
    .transform((val) => JSON.parse(val)),

  // 日期验证
  date: z.string()
    .datetime('日期格式不正确')
    .transform((val) => new Date(val)),

  // 布尔值验证
  boolean: z.coerce.boolean(),

  // 数组验证
  stringArray: z.array(z.string().transform(sanitizeInput))
    .max(100, '数组长度不能超过100'),

  // 数字范围验证
  positiveNumber: z.coerce.number()
    .min(0, '数字必须大于等于0'),

  percentage: z.coerce.number()
    .min(0, '百分比不能小于0')
    .max(100, '百分比不能大于100'),

  // 价格验证
  price: z.coerce.number()
    .min(0, '价格不能小于0')
    .max(999999.99, '价格不能超过999999.99'),

  // 股票代码验证
  stockSymbol: z.string()
    .regex(/^[A-Z0-9.-]+$/, '股票代码格式不正确')
    .min(1, '股票代码不能为空')
    .max(20, '股票代码长度不能超过20个字符')
    .toUpperCase()
    .transform(sanitizeInput)
};

// API端点验证模式
export const apiSchemas = {
  // 策略相关
  createStrategy: z.object({
    name: commonValidations.username,
    description: z.string()
      .min(10, '策略描述至少10个字符')
      .max(1000, '策略描述不能超过1000个字符')
      .transform(escapeHtml),
    parameters: z.record(z.any()).optional(),
    isActive: commonValidations.boolean.optional()
  }),

  updateStrategy: z.object({
    name: commonValidations.username.optional(),
    description: z.string()
      .min(10, '策略描述至少10个字符')
      .max(1000, '策略描述不能超过1000个字符')
      .transform(escapeHtml)
      .optional(),
    parameters: z.record(z.any()).optional(),
    isActive: commonValidations.boolean.optional()
  }),

  // 市场数据相关
  getMarketData: z.object({
    symbol: commonValidations.stockSymbol,
    interval: z.enum(['1m', '5m', '15m', '30m', '1h', '4h', '1d']),
    limit: commonValidations.limit.optional(),
    startDate: commonValidations.date.optional(),
    endDate: commonValidations.date.optional()
  }),

  // 回测相关
  createBacktest: z.object({
    strategyId: commonValidations.id,
    symbol: commonValidations.stockSymbol,
    startDate: commonValidations.date,
    endDate: commonValidations.date,
    initialCapital: commonValidations.price,
    parameters: z.record(z.any()).optional()
  }),

  // 用户认证相关
  login: z.object({
    username: commonValidations.username,
    password: z.string().min(1, '密码不能为空')
  }),

  register: z.object({
    username: commonValidations.username,
    email: commonValidations.email,
    password: commonValidations.password,
    confirmPassword: z.string()
  }).refine((data) => data.password === data.confirmPassword, {
    message: '确认密码不匹配',
    path: ['confirmPassword']
  }),

  // 分页查询
  paginatedQuery: z.object({
    page: commonValidations.page.optional(),
    limit: commonValidations.limit.optional(),
    sortBy: commonValidations.sortBy.optional(),
    sortOrder: commonValidations.sortOrder.optional(),
    search: commonValidations.searchQuery.optional()
  })
};

// 验证中间件工厂函数
export const validateInput = <T>(schema: z.ZodSchema<T>) => {
  return async (data: unknown): Promise<{ success: true; data: T } | { success: false; errors: string[] }> => {
    try {
      const validatedData = await schema.parseAsync(data);
      return { success: true, data: validatedData };
    } catch (error) {
      if (error instanceof z.ZodError) {
        const errors = error.errors.map(err => `${err.path.join('.')}: ${err.message}`);
        return { success: false, errors };
      }
      return { success: false, errors: ['验证失败'] };
    }
  };
};

// 批量验证函数
export const validateBatch = async <T>(
  items: unknown[],
  schema: z.ZodSchema<T>
): Promise<{ valid: T[]; invalid: Array<{ index: number; errors: string[] }> }> => {
  const valid: T[] = [];
  const invalid: Array<{ index: number; errors: string[] }> = [];

  for (let i = 0; i < items.length; i++) {
    const result = await validateInput(schema)(items[i]);
    if (result.success) {
      valid.push(result.data);
    } else {
      invalid.push({ index: i, errors: result.errors });
    }
  }

  return { valid, invalid };
};

// 安全过滤函数
export const securityFilter = {
  // 过滤掉潜在的XSS攻击
  xss: (input: string): string => {
    return escapeHtml(sanitizeInput(input));
  },

  // 过滤掉潜在的SQL注入
  sql: (input: string): string => {
    return escapeSql(sanitizeInput(input));
  },

  // 过滤掉脚本标签
  scripts: (input: string): string => {
    return input.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
  },

  // 过滤掉样式标签
  styles: (input: string): string => {
    return input.replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '');
  },

  // 移除所有HTML标签
  stripHtml: (input: string): string => {
    return input.replace(/<[^>]*>/g, '');
  },

  // 只保留允许的HTML标签
  allowedTags: (input: string, allowedTags: string[]): string => {
    const tagPattern = allowedTags.map(tag => `<${tag}[^>]*>|<\/${tag}>`).join('|');
    const regex = new RegExp(`<(?!\/?(?:${tagPattern})[^>]*>)[^>]*>`, 'gi');
    return input.replace(regex, '');
  }
};

// 输入验证工具类
export class InputValidator {
  private errors: string[] = [];

  /**
   * 验证字符串
   */
  string(value: unknown, options: {
    required?: boolean;
    minLength?: number;
    maxLength?: number;
    pattern?: RegExp;
    sanitize?: boolean;
  } = {}): string | null {
    if (typeof value !== 'string') {
      if (options.required) {
        this.errors.push('值必须是字符串');
        return null;
      }
      return '';
    }

    let processedValue = value;

    // 应用清理
    if (options.sanitize !== false) {
      processedValue = sanitizeInput(processedValue);
    }

    // 长度检查
    if (options.minLength && processedValue.length < options.minLength) {
      this.errors.push(`字符串长度不能少于${options.minLength}个字符`);
      return null;
    }

    if (options.maxLength && processedValue.length > options.maxLength) {
      this.errors.push(`字符串长度不能超过${options.maxLength}个字符`);
      return null;
    }

    // 模式匹配
    if (options.pattern && !options.pattern.test(processedValue)) {
      this.errors.push('字符串格式不正确');
      return null;
    }

    return processedValue;
  }

  /**
   * 验证数字
   */
  number(value: unknown, options: {
    required?: boolean;
    min?: number;
    max?: number;
    integer?: boolean;
  } = {}): number | null {
    const num = Number(value);

    if (isNaN(num)) {
      if (options.required) {
        this.errors.push('值必须是数字');
        return null;
      }
      return 0;
    }

    // 范围检查
    if (options.min !== undefined && num < options.min) {
      this.errors.push(`数字不能小于${options.min}`);
      return null;
    }

    if (options.max !== undefined && num > options.max) {
      this.errors.push(`数字不能大于${options.max}`);
      return null;
    }

    // 整数检查
    if (options.integer && !Number.isInteger(num)) {
      this.errors.push('值必须是整数');
      return null;
    }

    return num;
  }

  /**
   * 验证邮箱
   */
  email(value: unknown): string | null {
    const result = this.string(value, {
      required: true,
      maxLength: 254
    });

    if (!result) return null;

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(result)) {
      this.errors.push('邮箱格式不正确');
      return null;
    }

    return result;
  }

  /**
   * 验证URL
   */
  url(value: unknown): string | null {
    const result = this.string(value, {
      required: true,
      maxLength: 2048
    });

    if (!result) return null;

    try {
      new URL(result);
      return result;
    } catch {
      this.errors.push('URL格式不正确');
      return null;
    }
  }

  /**
   * 验证数组
   */
  array<T>(value: unknown, validator: (item: unknown) => T | null): T[] | null {
    if (!Array.isArray(value)) {
      this.errors.push('值必须是数组');
      return null;
    }

    const result: T[] = [];
    for (const item of value) {
      const validatedItem = validator(item);
      if (validatedItem !== null) {
        result.push(validatedItem);
      }
    }

    return result;
  }

  /**
   * 验证对象
   */
  object(value: unknown, schema: Record<string, (value: unknown) => any>): Record<string, any> | null {
    if (typeof value !== 'object' || value === null) {
      this.errors.push('值必须是对象');
      return null;
    }

    const result: Record<string, any> = {};
    const obj = value as Record<string, unknown>;

    for (const [key, validator] of Object.entries(schema)) {
      const validatedValue = validator(obj[key]);
      if (validatedValue !== null) {
        result[key] = validatedValue;
      }
    }

    return result;
  }

  /**
   * 获取验证错误
   */
  getErrors(): string[] {
    return [...this.errors];
  }

  /**
   * 清除错误
   */
  clearErrors(): void {
    this.errors = [];
  }

  /**
   * 检查是否有错误
   */
  hasErrors(): boolean {
    return this.errors.length > 0;
  }
}

// 导出默认验证器实例
export const defaultValidator = new InputValidator();

// 自定义错误类型
export class ValidationError extends Error {
  public errors: string[];

  constructor(errors: string[]) {
    super('输入验证失败');
    this.name = 'ValidationError';
    this.errors = errors;
  }
}