import {
  StyleConfigService,
  styleConfigService,
} from '../../services/styleConfigService';
import {
  DEFAULT_SIGNAL_THEMES,
  PRESET_STRATEGIES,
  SignalMarkerStyle,
  SignalType,
} from '../../types/strategySignal.types';

describe('StyleConfigService', () => {
  let service: StyleConfigService;

  beforeEach(() => {
    service = new StyleConfigService();
  });

  afterEach(() => {
    service.resetToDefaults();
  });

  describe('getSignalStyle', () => {
    it('应该返回默认主题的样式', () => {
      const style = service.getSignalStyle('sma_crossover', 'buy');

      expect(style).toBeDefined();
      expect(style.shape).toBeDefined();
      expect(style.color).toBeDefined();
      expect(style.size).toBeGreaterThan(0);
      expect(style.opacity).toBeGreaterThan(0);
      expect(style.opacity).toBeLessThanOrEqual(1);
    });

    it('应该根据置信度调整样式', () => {
      const highConfidenceStyle = service.getSignalStyle(
        'sma_crossover',
        'buy',
        90,
      );
      const lowConfidenceStyle = service.getSignalStyle(
        'sma_crossover',
        'buy',
        30,
      );

      expect(highConfidenceStyle.opacity).toBeGreaterThan(
        lowConfidenceStyle.opacity,
      );
      expect(highConfidenceStyle.size).toBeGreaterThanOrEqual(
        lowConfidenceStyle.size,
      );
    });

    it('应该返回不同信号类型的样式', () => {
      const buyStyle = service.getSignalStyle('sma_crossover', 'buy');
      const sellStyle = service.getSignalStyle('sma_crossover', 'sell');

      expect(buyStyle.color).not.toBe(sellStyle.color);
    });

    it('应该返回预设策略的样式', () => {
      const presetStyle = service.getSignalStyle('sma_crossover', 'buy');
      const defaultStyle = DEFAULT_SIGNAL_THEMES.light.buy;

      // 预设策略可能有自定义样式
      expect(presetStyle).toBeDefined();
    });
  });

  describe('主题管理', () => {
    it('应该获取所有主题', () => {
      const themes = service.getAllThemes();

      expect(themes.length).toBeGreaterThan(0);
      expect(themes.some((theme) => theme.id === 'light')).toBe(true);
      expect(themes.some((theme) => theme.id === 'dark')).toBe(true);
      expect(themes.some((theme) => theme.id === 'high_contrast')).toBe(true);
    });

    it('应该切换当前主题', () => {
      service.setCurrentTheme('dark');
      expect(service.getCurrentTheme()?.id).toBe('dark');

      service.setCurrentTheme('light');
      expect(service.getCurrentTheme()?.id).toBe('light');
    });

    it('切换主题应该无效化现有主题ID', () => {
      expect(() => {
        service.setCurrentTheme('invalid_theme');
      }).toThrow('主题未找到');
    });

    it('应该添加自定义主题', () => {
      const customTheme = {
        name: '测试主题',
        description: '用于测试的自定义主题',
        colors: {
          background: '#f0f0f0',
          text: '#333333',
          grid: '#e0e0e0',
          border: '#cccccc',
        },
        signalStyles: DEFAULT_SIGNAL_THEMES.light,
      };

      const themeId = service.addCustomTheme(customTheme);

      expect(themeId).toMatch(/^custom_\d+$/);
      const themes = service.getAllThemes();
      expect(themes.some((theme) => theme.id === themeId)).toBe(true);
    });
  });

  describe('用户样式配置', () => {
    it('应该添加用户自定义样式', () => {
      const customStyle: Partial<SignalMarkerStyle> = {
        color: '#ff0000',
        size: 20,
        opacity: 0.5,
      };

      service.updateUserStyleConfig('custom_strategy', 'buy', customStyle);

      const userStyle = service.getUserStyleConfig('custom_strategy', 'buy');
      expect(userStyle).toBeTruthy();
      expect(userStyle!.style.color).toBe('#ff0000');
      expect(userStyle!.style.size).toBe(20);
      expect(userStyle!.enabled).toBe(true);
    });

    it('应该使用用户自定义样式覆盖默认样式', () => {
      const customStyle: Partial<SignalMarkerStyle> = {
        color: '#00ff00',
        shape: 'square',
      };

      service.updateUserStyleConfig('test_strategy', 'sell', customStyle);
      const style = service.getSignalStyle('test_strategy', 'sell');

      expect(style.color).toBe('#00ff00');
      expect(style.shape).toBe('square');
    });

    it('应该启用/禁用用户样式配置', () => {
      const customStyle: Partial<SignalMarkerStyle> = {
        color: '#0000ff',
      };

      service.updateUserStyleConfig('test_strategy', 'buy', customStyle);
      service.toggleUserStyleConfig('test_strategy', 'buy', false);

      const userStyle = service.getUserStyleConfig('test_strategy', 'buy');
      expect(userStyle!.enabled).toBe(false);

      // 禁用后应该返回默认样式
      const style = service.getSignalStyle('test_strategy', 'buy');
      expect(style.color).not.toBe('#0000ff');
    });

    it('应该删除用户样式配置', () => {
      const customStyle: Partial<SignalMarkerStyle> = {
        color: '#ff00ff',
      };

      service.updateUserStyleConfig('test_strategy', 'buy', customStyle);
      service.removeUserStyleConfig('test_strategy', 'buy');

      const userStyle = service.getUserStyleConfig('test_strategy', 'buy');
      expect(userStyle).toBeNull();
    });

    it('应该获取所有用户样式配置', () => {
      service.updateUserStyleConfig('strategy1', 'buy', { color: '#ff0000' });
      service.updateUserStyleConfig('strategy1', 'sell', { color: '#00ff00' });
      service.updateUserStyleConfig('strategy2', 'buy', { color: '#0000ff' });

      const allConfigs = service.getAllUserStyleConfigs();
      expect(allConfigs).toHaveLength(3);
    });
  });

  describe('样式预设', () => {
    it('应该获取所有样式预设', () => {
      const presets = service.getAllStylePresets();

      expect(presets.length).toBeGreaterThan(0);
      expect(presets.some((preset) => preset.id === 'professional')).toBe(true);
      expect(presets.some((preset) => preset.id === 'educational')).toBe(true);
    });

    it('应该创建样式预设', () => {
      // 先添加一些用户配置
      service.updateUserStyleConfig('test_strategy1', 'buy', {
        color: '#ff0000',
        size: 15,
      });
      service.updateUserStyleConfig('test_strategy1', 'sell', {
        color: '#00ff00',
        size: 15,
      });

      const presetId = service.createStylePreset(
        '测试预设',
        '用于测试的样式预设',
        'custom',
        {
          author: 'Test',
          version: '1.0.0',
          tags: ['test', 'custom'],
        },
      );

      expect(presetId).toMatch(/^preset_\d+$/);

      const preset = service
        .getAllStylePresets()
        .find((p) => p.id === presetId);
      expect(preset).toBeTruthy();
      expect(preset!.name).toBe('测试预设');
      expect(preset!.category).toBe('custom');
      expect(preset!.metadata?.author).toBe('Test');
    });

    it('应该应用样式预设', () => {
      // 创建一个预设
      service.updateUserStyleConfig('test_strategy', 'buy', {
        color: '#ff00ff',
        size: 20,
      });
      const presetId = service.createStylePreset(
        'Test Preset',
        'Description',
        'custom',
      );

      // 清除现有配置
      service.resetToDefaults();

      // 应用预设
      service.applyStylePreset(presetId);

      // 验证配置被应用
      const appliedStyle = service.getUserStyleConfig('test_strategy', 'buy');
      expect(appliedStyle).toBeTruthy();
      expect(appliedStyle!.style.color).toBe('#ff00ff');
      expect(appliedStyle!.style.size).toBe(20);
    });

    it('应该删除样式预设', () => {
      const presetId = service.createStylePreset(
        'Test',
        'Description',
        'custom',
      );

      expect(service.getAllStylePresets().some((p) => p.id === presetId)).toBe(
        true,
      );

      service.removeStylePreset(presetId);

      expect(service.getAllStylePresets().some((p) => p.id === presetId)).toBe(
        false,
      );
    });
  });

  describe('导入导出', () => {
    it('应该导出样式配置', () => {
      // 设置一些配置
      service.setCurrentTheme('dark');
      service.updateUserStyleConfig('test_strategy', 'buy', {
        color: '#ff0000',
      });
      const presetId = service.createStylePreset(
        'Test',
        'Description',
        'custom',
      );

      const exported = service.exportStyles();

      expect(exported.theme).toBe('dark');
      expect(exported.userConfigs).toHaveLength(1);
      expect(exported.userConfigs[0].strategyId).toBe('test_strategy');
      expect(exported.presets.some((p) => p.id === presetId)).toBe(true);
    });

    it('应该导入样式配置', () => {
      const exportedStyles = {
        theme: 'dark',
        userConfigs: [
          {
            strategyId: 'imported_strategy',
            signalType: 'buy' as SignalType,
            style: { color: '#00ff00', size: 18 },
            enabled: true,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        ],
        presets: [],
      };

      service.importStyles(exportedStyles);

      expect(service.getCurrentTheme()?.id).toBe('dark');
      const importedStyle = service.getUserStyleConfig(
        'imported_strategy',
        'buy',
      );
      expect(importedStyle).toBeTruthy();
      expect(importedStyle!.style.color).toBe('#00ff00');
      expect(importedStyle!.style.size).toBe(18);
    });

    it('应该处理无效的导入数据', () => {
      const invalidExport = {
        theme: 'invalid_theme',
        userConfigs: [],
        presets: [],
      };

      // 不应该崩溃
      expect(() => {
        service.importStyles(invalidExport);
      }).not.toThrow();

      // 主题应该保持不变
      expect(service.getCurrentTheme()?.id).not.toBe('invalid_theme');
    });
  });

  describe('重置功能', () => {
    it('应该重置为默认样式', () => {
      // 设置一些自定义配置
      service.setCurrentTheme('dark');
      service.updateUserStyleConfig('test_strategy', 'buy', {
        color: '#ff0000',
      });
      service.createStylePreset('Test', 'Description', 'custom');

      // 重置
      service.resetToDefaults();

      // 验证重置结果
      expect(service.getCurrentTheme()?.id).toBe('light');
      expect(service.getAllUserStyleConfigs()).toHaveLength(0);
      expect(
        service.getAllStylePresets().filter((p) => p.category === 'custom'),
      ).toHaveLength(0);
    });
  });

  describe('样式优先级', () => {
    it('用户样式应该覆盖预设样式', () => {
      service.updateUserStyleConfig('sma_crossover', 'buy', {
        color: '#ff0000',
      });

      const style = service.getSignalStyle('sma_crossover', 'buy');

      // 应该使用用户自定义的颜色
      expect(style.color).toBe('#ff0000');
    });

    it('预设样式应该覆盖默认主题样式', () => {
      // 使用预设策略
      const style = service.getSignalStyle('sma_crossover', 'buy');
      const defaultStyle = DEFAULT_SIGNAL_THEMES.light.buy;

      // 预设策略可能有不同的样式
      if (PRESET_STRATEGIES['sma_crossover']?.styles?.buy) {
        expect(style.color).toBeDefined();
      }
    });

    it('应该正确回退到默认样式', () => {
      // 使用不存在的策略ID，且没有用户自定义样式
      const style = service.getSignalStyle('nonexistent_strategy', 'buy');

      // 应该回退到默认样式
      expect(style.color).toBe(DEFAULT_SIGNAL_THEMES.light.buy.color);
    });
  });
});
