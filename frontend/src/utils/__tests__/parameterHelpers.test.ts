import {
  DEFAULT_PARAMETERS,
  PARAMETER_RULES,
  applyParameterConstraints,
  areParametersEqual,
  calculateParameterSimilarity,
  formatParameterValue,
  generateParameterDescription,
  getParameterLabel,
  getParameterRiskAssessment,
  getParameterUnit,
  validateAllParameters,
  validateParameter,
  validateParameterGroup,
} from '../parameterHelpers';
import { ParameterGroup, StrategyParameters } from '@/types/parameter.types';

describe('parameterHelpers', () => {
  describe('validateParameter', () => {
    it('应该验证有效的移动平均周期', () => {
      const result = validateParameter('movingAveragePeriod', 20);
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('应该拒绝无效的移动平均周期范围', () => {
      const result = validateParameter('movingAveragePeriod', 3); // 小于最小值5
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('移动平均周期 不能小于 5');
    });

    it('应该验证有效的止损百分比', () => {
      const result = validateParameter('stopLoss', 5.5);
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('应该拒绝超出范围的止损百分比', () => {
      const result = validateParameter('stopLoss', 60); // 大于最大值50
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('止损百分比 不能大于 50');
    });

    it('应该检测止损止盈不合理组合', () => {
      const result = validateParameter('stopLoss', 10, {
        otherParameters: { takeProfit: 5 },
      });
      expect(result.isValid).toBe(true);
      expect(result.warnings).toContain('止损值不应大于或等于止盈值');
    });

    it('应该检测止盈止损不合理组合', () => {
      const result = validateParameter('takeProfit', 3, {
        otherParameters: { stopLoss: 5 },
      });
      expect(result.isValid).toBe(true);
      expect(result.warnings).toContain('止盈值应大于止损值');
    });

    it('应该提供短期均线的警告', () => {
      const result = validateParameter('movingAveragePeriod', 8);
      expect(result.warnings).toContain('短期均线可能产生较多噪音信号');
    });

    it('应该提供长期均线的警告', () => {
      const result = validateParameter('movingAveragePeriod', 150);
      expect(result.warnings).toContain('长期均线可能响应较慢，错过短期机会');
    });

    it('应该检测严格的止损设置', () => {
      const result = validateParameter('stopLoss', 0.5);
      expect(result.warnings).toContain('止损设置过严可能导致频繁止损');
    });
  });

  describe('validateAllParameters', () => {
    it('应该验证所有有效参数', () => {
      const parameters: StrategyParameters = {
        movingAveragePeriod: 20,
        stopLoss: 5.0,
        takeProfit: 10.0,
      };
      const result = validateAllParameters(parameters);
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('应该收集所有验证错误', () => {
      const parameters: StrategyParameters = {
        movingAveragePeriod: 3, // 无效
        stopLoss: 60, // 无效
        takeProfit: 80, // 无效
      };
      const result = validateAllParameters(parameters);
      expect(result.isValid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });

    it('应该提供风险收益比例警告', () => {
      const parameters: StrategyParameters = {
        movingAveragePeriod: 20,
        stopLoss: 10,
        takeProfit: 5, // 止盈小于止损
      };
      const result = validateAllParameters(parameters);
      expect(result.warnings).toContain('建议止盈/止损比例保持在1:1以上');
    });

    it('应该提供良好的风险收益比例建议', () => {
      const parameters: StrategyParameters = {
        movingAveragePeriod: 20,
        stopLoss: 5,
        takeProfit: 15, // 3:1 比例
      };
      const result = validateAllParameters(parameters);
      expect(result.warnings).not.toContain('建议止盈/止损比例保持在1:1以上');
    });
  });

  describe('validateParameterGroup', () => {
    it('应该验证有效的参数组', () => {
      const group: ParameterGroup = {
        id: 'test-group',
        name: '测试组',
        parameters: DEFAULT_PARAMETERS,
        isActive: true,
      };
      const result = validateParameterGroup(group);
      expect(result.isValid).toBe(true);
    });

    it('应该拒绝空名称的参数组', () => {
      const group: ParameterGroup = {
        id: 'test-group',
        name: '',
        parameters: DEFAULT_PARAMETERS,
        isActive: true,
      };
      const result = validateParameterGroup(group);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('参数组名称不能为空');
    });

    it('应该警告过长的参数组名称', () => {
      const longName = 'a'.repeat(60);
      const group: ParameterGroup = {
        id: 'test-group',
        name: longName,
        parameters: DEFAULT_PARAMETERS,
        isActive: true,
      };
      const result = validateParameterGroup(group);
      expect(result.warnings).toContain('参数组名称过长，建议控制在50字符以内');
    });
  });

  describe('applyParameterConstraints', () => {
    it('应该应用最小值约束', () => {
      const result = applyParameterConstraints('movingAveragePeriod', 3);
      expect(result).toBe(5); // 最小值
    });

    it('应该应用最大值约束', () => {
      const result = applyParameterConstraints('stopLoss', 60);
      expect(result).toBe(50); // 最大值
    });

    it('应该应用步进约束', () => {
      const result = applyParameterConstraints('stopLoss', 5.15);
      expect(result).toBe(5.2); // 步进0.1，5.15四舍五入到5.2
    });

    it('应该应用精度约束', () => {
      const result = applyParameterConstraints('stopLoss', 5.16);
      expect(result).toBe(5.2); // 精度1位小数
    });

    it('应该处理无效输入', () => {
      const result = applyParameterConstraints('movingAveragePeriod', NaN);
      expect(result).toBe(5); // 默认最小值
    });
  });

  describe('formatParameterValue', () => {
    it('应该格式化整数参数', () => {
      const result = formatParameterValue('movingAveragePeriod', 20);
      expect(result).toBe('20');
    });

    it('应该格式化小数参数', () => {
      const result = formatParameterValue('stopLoss', 5.5);
      expect(result).toBe('5.5');
    });

    it('应该保持精度格式', () => {
      const result = formatParameterValue('takeProfit', 10.0);
      expect(result).toBe('10.0');
    });
  });

  describe('getParameterLabel', () => {
    it('应该返回正确的中文标签', () => {
      expect(getParameterLabel('movingAveragePeriod')).toBe('移动平均周期');
      expect(getParameterLabel('stopLoss')).toBe('止损百分比');
      expect(getParameterLabel('takeProfit')).toBe('止盈百分比');
    });
  });

  describe('getParameterUnit', () => {
    it('应该返回正确的单位', () => {
      expect(getParameterUnit('movingAveragePeriod')).toBe('天');
      expect(getParameterUnit('stopLoss')).toBe('%');
      expect(getParameterUnit('takeProfit')).toBe('%');
    });
  });

  describe('calculateParameterSimilarity', () => {
    it('应该计算相同参数的相似度为1', () => {
      const params1: StrategyParameters = DEFAULT_PARAMETERS;
      const params2: StrategyParameters = { ...DEFAULT_PARAMETERS };
      const similarity = calculateParameterSimilarity(params1, params2);
      expect(similarity).toBe(1);
    });

    it('应该计算不同参数的相似度', () => {
      const params1: StrategyParameters = DEFAULT_PARAMETERS;
      const params2: StrategyParameters = {
        movingAveragePeriod: 40, // 差异较大
        stopLoss: 5.0,
        takeProfit: 10.0,
      };
      const similarity = calculateParameterSimilarity(params1, params2);
      expect(similarity).toBeGreaterThan(0);
      expect(similarity).toBeLessThan(1);
    });

    it('应该计算完全不同参数的相似度为0', () => {
      const params1: StrategyParameters = {
        movingAveragePeriod: 5, // 最小值
        stopLoss: 0, // 最小值
        takeProfit: 0, // 最小值
      };
      const params2: StrategyParameters = {
        movingAveragePeriod: 200, // 最大值
        stopLoss: 50, // 最大值
        takeProfit: 50, // 最大值
      };
      const similarity = calculateParameterSimilarity(params1, params2);
      expect(similarity).toBe(0);
    });
  });

  describe('generateParameterDescription', () => {
    it('应该生成完整的参数描述', () => {
      const parameters: StrategyParameters = {
        movingAveragePeriod: 20,
        stopLoss: 5.0,
        takeProfit: 10.0,
      };
      const description = generateParameterDescription(parameters);
      expect(description).toBe('使用20日移动平均线，设置5.0%止损和10.0%止盈');
    });

    it('应该生成只有止损的描述', () => {
      const parameters: StrategyParameters = {
        movingAveragePeriod: 20,
        stopLoss: 5.0,
        takeProfit: 0,
      };
      const description = generateParameterDescription(parameters);
      expect(description).toBe('使用20日移动平均线，设置5.0%止损');
    });

    it('应该生成只有止盈的描述', () => {
      const parameters: StrategyParameters = {
        movingAveragePeriod: 20,
        stopLoss: 0,
        takeProfit: 10.0,
      };
      const description = generateParameterDescription(parameters);
      expect(description).toBe('使用20日移动平均线，设置10.0%止盈');
    });

    it('应该生成基本均线描述', () => {
      const parameters: StrategyParameters = {
        movingAveragePeriod: 20,
        stopLoss: 0,
        takeProfit: 0,
      };
      const description = generateParameterDescription(parameters);
      expect(description).toBe('使用20日移动平均线');
    });
  });

  describe('areParametersEqual', () => {
    it('应该检测相同的参数', () => {
      const params1: StrategyParameters = DEFAULT_PARAMETERS;
      const params2: StrategyParameters = { ...DEFAULT_PARAMETERS };
      expect(areParametersEqual(params1, params2)).toBe(true);
    });

    it('应该检测不同的参数', () => {
      const params1: StrategyParameters = DEFAULT_PARAMETERS;
      const params2: StrategyParameters = {
        ...DEFAULT_PARAMETERS,
        movingAveragePeriod: 30,
      };
      expect(areParametersEqual(params1, params2)).toBe(false);
    });

    it('应该考虑精度容差', () => {
      const params1: StrategyParameters = {
        ...DEFAULT_PARAMETERS,
        stopLoss: 5.0,
      };
      const params2: StrategyParameters = {
        ...DEFAULT_PARAMETERS,
        stopLoss: 5.001,
      };
      expect(areParametersEqual(params1, params2)).toBe(true);
    });
  });

  describe('getParameterRiskAssessment', () => {
    it('应该评估低风险参数', () => {
      const parameters: StrategyParameters = {
        movingAveragePeriod: 50,
        stopLoss: 5,
        takeProfit: 15,
      };
      const assessment = getParameterRiskAssessment(parameters);
      expect(['low', 'medium']).toContain(assessment.level);
      expect(assessment.score).toBeLessThan(50);
    });

    it('应该评估高风险参数', () => {
      const parameters: StrategyParameters = {
        movingAveragePeriod: 5,
        stopLoss: 1,
        takeProfit: 50,
      };
      const assessment = getParameterRiskAssessment(parameters);
      expect(['high', 'very_high']).toContain(assessment.level);
      expect(assessment.score).toBeGreaterThan(50);
    });

    it('应该包含风险因素', () => {
      const parameters: StrategyParameters = {
        movingAveragePeriod: 5,
        stopLoss: 20,
        takeProfit: 10,
      };
      const assessment = getParameterRiskAssessment(parameters);
      expect(assessment.factors.length).toBeGreaterThan(0);
      expect(assessment.factors.some(factor =>
        factor.includes('短期均线') ||
        factor.includes('止盈') ||
        factor.includes('止损'),
      )).toBe(true);
    });

    it('应该提供风险等级中文标签', () => {
      const parameters: StrategyParameters = {
        movingAveragePeriod: 20,
        stopLoss: 5,
        takeProfit: 10,
      };
      const assessment = getParameterRiskAssessment(parameters);
      expect(['low', 'medium', 'high', 'very_high']).toContain(assessment.level);
    });
  });

  describe('常量', () => {
    it('应该导出正确的参数规则', () => {
      expect(PARAMETER_RULES.movingAveragePeriod.min).toBe(5);
      expect(PARAMETER_RULES.movingAveragePeriod.max).toBe(200);
      expect(PARAMETER_RULES.stopLoss.min).toBe(0);
      expect(PARAMETER_RULES.stopLoss.max).toBe(50);
    });

    it('应该导出正确的默认参数', () => {
      expect(DEFAULT_PARAMETERS.movingAveragePeriod).toBe(20);
      expect(DEFAULT_PARAMETERS.stopLoss).toBe(5.0);
      expect(DEFAULT_PARAMETERS.takeProfit).toBe(10.0);
    });
  });
});
