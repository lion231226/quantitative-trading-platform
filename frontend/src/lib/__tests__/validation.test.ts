import {
  formatValidationErrors,
  validateDate,
  validateDateRange,
  validateStrategyForm,
  validateStrategyParams,
  validateSymbol,
} from '../validation';

describe('Validation Functions', () => {
  describe('validateDate', () => {
    it('validates correct date format', () => {
      expect(validateDate('2024-01-01')).toBe(true);
      expect(validateDate('2023-12-31')).toBe(true);
    });

    it('rejects invalid date format', () => {
      expect(validateDate('2024/01/01')).toBe(false);
      expect(validateDate('01-01-2024')).toBe(false);
      expect(validateDate('2024-13-01')).toBe(false);
      expect(validateDate('invalid-date')).toBe(false);
    });
  });

  describe('validateDateRange', () => {
    it('validates correct date range', () => {
      const result = validateDateRange('2024-01-01', '2024-01-31');
      expect(result.isValid).toBe(true);
    });

    it('rejects invalid dates', () => {
      let result = validateDateRange('invalid', '2024-01-31');
      expect(result.isValid).toBe(false);
      expect(result.error).toBe('开始日期格式无效');

      result = validateDateRange('2024-01-01', 'invalid');
      expect(result.isValid).toBe(false);
      expect(result.error).toBe('结束日期格式无效');
    });

    it('rejects start date >= end date', () => {
      const result = validateDateRange('2024-01-31', '2024-01-01');
      expect(result.isValid).toBe(false);
      expect(result.error).toBe('开始日期必须早于结束日期');
    });

    it('rejects end date in future', () => {
      const futureDate = new Date();
      futureDate.setDate(futureDate.getDate() + 1);
      const futureStr = futureDate.toISOString().split('T')[0];

      const result = validateDateRange('2024-01-01', futureStr);
      expect(result.isValid).toBe(false);
      expect(result.error).toBe('结束日期不能晚于今天');
    });

    it('rejects date range too long', () => {
      const result = validateDateRange('2020-01-01', '2024-01-01');
      expect(result.isValid).toBe(false);
      expect(result.error).toBe('日期范围不能超过2年');
    });

    it('rejects date range too short', () => {
      const result = validateDateRange('2024-01-01', '2024-01-05');
      expect(result.isValid).toBe(false);
      expect(result.error).toBe('日期范围至少需要7天');
    });
  });

  describe('validateSymbol', () => {
    it('validates correct symbol format', () => {
      expect(validateSymbol('RB')).toBe(true);
      expect(validateSymbol('CU')).toBe(true);
      expect(validateSymbol('HC2401')).toBe(true);
      expect(validateSymbol('CU2402')).toBe(true);
    });

    it('rejects invalid symbol format', () => {
      expect(validateSymbol('rb')).toBe(false); // lowercase
      expect(validateSymbol('RB000001')).toBe(false); // too long (7 chars)
      expect(validateSymbol('')).toBe(false); // empty
      expect(validateSymbol('R')).toBe(false); // too short (1 char)
    });
  });

  describe('validateStrategyParams', () => {
    it('validates correct parameters', () => {
      const result = validateStrategyParams({
        window_size: 20,
        initial_capital: 100000,
      });
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('rejects invalid window_size', () => {
      let result = validateStrategyParams({
        window_size: 3, // too small
        initial_capital: 100000,
      });
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('均线周期必须在5-200天之间');

      result = validateStrategyParams({
        window_size: 250, // too large
        initial_capital: 100000,
      });
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('均线周期必须在5-200天之间');
    });

    it('rejects invalid initial_capital', () => {
      let result = validateStrategyParams({
        window_size: 20,
        initial_capital: 500, // too small
      });
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('初始资金必须大于1000元');

      result = validateStrategyParams({
        window_size: 20,
        initial_capital: 20000000, // too large
      });
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('初始资金不能超过1000万元');
    });
  });

  describe('validateStrategyForm', () => {
    it('validates complete correct form', () => {
      const result = validateStrategyForm({
        symbol: 'RB',
        startDate: '2024-01-01',
        endDate: '2024-01-31',
        params: {
          window_size: 20,
          initial_capital: 100000,
        },
      });
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('accumulates multiple validation errors', () => {
      const result = validateStrategyForm({
        symbol: 'rb', // invalid format
        startDate: '2024-01-31', // start after end
        endDate: '2024-01-01',
        params: {
          window_size: 3, // too small
          initial_capital: 500, // too small
        },
      });
      expect(result.isValid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(2);
    });
  });

  describe('formatValidationErrors', () => {
    it('formats single error', () => {
      const result = formatValidationErrors(['Error message']);
      expect(result).toBe('Error message');
    });

    it('formats multiple errors', () => {
      const result = formatValidationErrors(['Error 1', 'Error 2', 'Error 3']);
      expect(result).toBe('1. Error 1\n2. Error 2\n3. Error 3');
    });

    it('handles empty errors array', () => {
      const result = formatValidationErrors([]);
      expect(result).toBe('');
    });
  });
});
