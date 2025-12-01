import {
  COLORBLIND_PRESETS,
  ColorblindConfig,
  ColorblindMode,
  CustomColorConfig,
  DEFAULT_MARKET_COLORS,
  MarketColors,
  MarketMode,
  ThemeConfig,
  ThemeExportFormat,
  ThemeMode,
  ThemePreset,
  ThemeState,
  ThemeUpdateEvent,
  ThemeValidationResult,
} from '../types/theme.types';

// 主题管理服务类
export class ThemeService {
  private static instance: ThemeService;
  private currentTheme: ThemeConfig;
  private customThemes: Map<string, ThemeConfig> = new Map();
  private presets: Map<string, ThemePreset> = new Map();
  private listeners: Set<(event: ThemeUpdateEvent) => void> = new Set();

  // 私有构造函数实现单例模式
  private constructor() {
    this.initializeDefaultThemes();
    this.loadFromStorage();
    this.currentTheme = this.getDefaultTheme();
  }

  // 获取单例实例
  static getInstance(): ThemeService {
    if (!ThemeService.instance) {
      ThemeService.instance = new ThemeService();
    }
    return ThemeService.instance;
  }

  /**
   * 获取当前主题
   */
  getCurrentTheme(): ThemeConfig {
    return { ...this.currentTheme };
  }

  /**
   * 设置当前主题
   */
  setCurrentTheme(themeId: string): void {
    const theme = this.getThemeById(themeId);
    if (!theme) {
      throw new Error(`主题未找到: ${themeId}`);
    }

    const previousTheme = this.currentTheme;
    this.currentTheme = { ...theme };
    this.saveToStorage();

    // 发布主题变更事件
    this.publishEvent({
      type: 'theme-changed',
      payload: { previousTheme, currentTheme: this.currentTheme },
      timestamp: Date.now(),
    });
  }

  /**
   * 设置市场模式
   */
  setMarketMode(marketMode: MarketMode): void {
    if (this.currentTheme.marketMode === marketMode) return;

    const previousTheme = this.currentTheme;
    this.currentTheme = {
      ...this.currentTheme,
      marketMode,
      colors: this.getMarketColors(marketMode, this.currentTheme.mode),
    };
    this.saveToStorage();

    this.publishEvent({
      type: 'market-mode-changed',
      payload: { marketMode, colors: this.currentTheme.colors },
      timestamp: Date.now(),
    });
  }

  /**
   * 设置色盲模式
   */
  setColorblindMode(colorblindConfig: ColorblindConfig): void {
    const previousTheme = this.currentTheme;
    let updatedColors = { ...this.currentTheme.colors };

    if (colorblindConfig.enabled && colorblindConfig.mode !== 'none') {
      updatedColors = this.applyColorblindColors(
        colorblindConfig.mode,
        this.currentTheme.marketMode,
      );
    }

    this.currentTheme = {
      ...this.currentTheme,
      colorblindMode: colorblindConfig.mode,
      colors: updatedColors,
    };
    this.saveToStorage();

    this.publishEvent({
      type: 'colorblind-mode-changed',
      payload: { colorblindConfig, colors: this.currentTheme.colors },
      timestamp: Date.now(),
    });
  }

  /**
   * 应用自定义颜色
   */
  applyCustomColors(customColors: CustomColorConfig): void {
    if (!customColors.enabled) return;

    const previousTheme = this.currentTheme;
    const mergedColors = {
      ...this.currentTheme.colors,
      ...customColors.marketColors,
    };

    this.currentTheme = {
      ...this.currentTheme,
      colors: mergedColors,
    };
    this.saveToStorage();

    this.publishEvent({
      type: 'custom-colors-changed',
      payload: { customColors, colors: this.currentTheme.colors },
      timestamp: Date.now(),
    });
  }

  /**
   * 获取所有可用主题
   */
  getAllThemes(): ThemeConfig[] {
    const defaultThemes = this.getDefaultThemes();
    const customThemeArray = Array.from(this.customThemes.values());
    return [...defaultThemes, ...customThemeArray];
  }

  /**
   * 获取主题
   */
  getThemeById(themeId: string): ThemeConfig | null {
    const defaultThemes = this.getDefaultThemes();
    const theme = defaultThemes.find((t) => t.id === themeId);
    if (theme) return theme;

    return this.customThemes.get(themeId) || null;
  }

  /**
   * 添加自定义主题
   */
  addCustomTheme(theme: Omit<ThemeConfig, 'id'>): string {
    const id = `custom_${Date.now()}`;
    const fullTheme: ThemeConfig = {
      id,
      ...theme,
    };

    this.customThemes.set(id, fullTheme);
    this.saveToStorage();
    return id;
  }

  /**
   * 删除自定义主题
   */
  removeCustomTheme(themeId: string): boolean {
    if (!this.customThemes.has(themeId)) return false;

    // 如果删除的是当前主题，切换到默认主题
    if (this.currentTheme.id === themeId) {
      this.setCurrentTheme('light_chinese');
    }

    this.customThemes.delete(themeId);
    this.saveToStorage();
    return true;
  }

  /**
   * 获取所有预设
   */
  getAllPresets(): ThemePreset[] {
    return Array.from(this.presets.values());
  }

  /**
   * 应用预设
   */
  applyPreset(presetId: string): void {
    const preset = this.presets.get(presetId);
    if (!preset) {
      throw new Error(`预设未找到: ${presetId}`);
    }

    this.currentTheme = { ...preset.theme };
    this.saveToStorage();

    this.publishEvent({
      type: 'theme-changed',
      payload: { preset, currentTheme: this.currentTheme },
      timestamp: Date.now(),
    });
  }

  /**
   * 创建预设
   */
  createPreset(
    name: string,
    description: string,
    category: ThemePreset['category'],
    metadata?: ThemePreset['metadata'],
  ): string {
    const id = `preset_${Date.now()}`;
    const preset: ThemePreset = {
      id,
      name,
      description,
      category,
      theme: this.currentTheme,
      colorblindSupport: true,
      metadata,
    };

    this.presets.set(id, preset);
    this.saveToStorage();
    return id;
  }

  /**
   * 验证主题
   */
  validateTheme(theme: ThemeConfig): ThemeValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    // 颜色格式验证
    const colorRegex = /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/;
    const requiredColors: (keyof MarketColors)[] = [
      'bullish',
      'bearish',
      'volume',
      'grid',
      'background',
      'text',
      'border',
    ];

    for (const colorKey of requiredColors) {
      if (!colorRegex.test(theme.colors[colorKey])) {
        errors.push(`无效的颜色格式: ${colorKey} = ${theme.colors[colorKey]}`);
      }
    }

    // WCAG对比度检查
    const contrastResults = this.calculateWCAGContrast(theme.colors);
    const wcagCompliance = {
      normalText: contrastResults.normalText,
      largeText: contrastResults.largeText,
      graphicalObjects: contrastResults.graphicalObjects,
    };

    // 检查对比度是否达到标准
    if (contrastResults.normalText < 4.5) {
      warnings.push('正常文本对比度低于WCAG 2.1 AA标准 (4.5:1)');
    }
    if (contrastResults.largeText < 3.0) {
      warnings.push('大文本对比度低于WCAG 2.1 AA标准 (3:1)');
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
      wcagCompliance,
    };
  }

  /**
   * 导出主题配置
   */
  exportThemes(): ThemeExportFormat {
    return {
      version: '1.0.0',
      timestamp: new Date().toISOString(),
      themes: this.getAllThemes(),
      presets: this.getAllPresets(),
      userPreferences: {
        currentTheme: this.currentTheme.id,
        marketMode: this.currentTheme.marketMode,
        colorblindConfig: {
          enabled: this.currentTheme.colorblindMode !== 'none',
          mode: this.currentTheme.colorblindMode,
          usePatterns: true,
          useShapes: true,
          textureIntensity: 0.7,
        },
        customColors: {
          enabled: false,
          marketColors: {},
        },
      },
      metadata: {
        author: 'User',
        description: '导出的主题配置',
        tags: ['custom', 'export'],
      },
    };
  }

  /**
   * 导入主题配置
   */
  importThemes(exportData: ThemeExportFormat): void {
    // 验证版本兼容性
    if (!exportData.version) {
      throw new Error('无效的导出文件格式');
    }

    // 导入主题
    if (exportData.themes) {
      for (const theme of exportData.themes) {
        if (theme.id.startsWith('custom_')) {
          this.customThemes.set(theme.id, theme);
        }
      }
    }

    // 导入预设
    if (exportData.presets) {
      for (const preset of exportData.presets) {
        this.presets.set(preset.id, preset);
      }
    }

    // 应用用户偏好
    if (exportData.userPreferences) {
      const { currentTheme, marketMode, colorblindConfig, customColors } =
        exportData.userPreferences;

      // 设置主题
      const theme = this.getThemeById(currentTheme);
      if (theme) {
        this.currentTheme = { ...theme };
      }

      // 设置市场模式
      if (marketMode) {
        this.setMarketMode(marketMode);
      }

      // 设置色盲模式
      if (colorblindConfig) {
        this.setColorblindMode(colorblindConfig);
      }

      // 应用自定义颜色
      if (customColors) {
        this.applyCustomColors(customColors);
      }
    }

    this.saveToStorage();
  }

  /**
   * 订阅主题变更事件
   */
  subscribe(listener: (event: ThemeUpdateEvent) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /**
   * 获取市场颜色
   */
  private getMarketColors(
    marketMode: MarketMode,
    themeMode: ThemeMode,
  ): MarketColors {
    const baseColors = DEFAULT_MARKET_COLORS[marketMode];

    if (themeMode === 'dark') {
      return {
        ...baseColors,
        background: '#1f2937',
        text: '#f9fafb',
        grid: '#374151',
        border: '#4b5563',
      };
    }

    return baseColors;
  }

  /**
   * 应用色盲颜色
   */
  private applyColorblindColors(
    colorblindMode: ColorblindMode,
    marketMode: MarketMode,
  ): MarketColors {
    const baseColors = DEFAULT_MARKET_COLORS[marketMode];
    const colorblindColors = COLORBLIND_PRESETS[colorblindMode];

    return {
      ...baseColors,
      bullish: colorblindColors.bullish,
      bearish: colorblindColors.bearish,
      volume: colorblindColors.volume,
    };
  }

  /**
   * 计算WCAG对比度
   */
  private calculateWCAGContrast(colors: MarketColors): {
    normalText: number;
    largeText: number;
    graphicalObjects: number;
  } {
    // 简化的对比度计算，实际项目中应该使用完整的WCAG计算库
    const getLuminance = (hex: string): number => {
      const rgb = this.hexToRgb(hex);
      return (0.299 * rgb.r + 0.587 * rgb.g + 0.114 * rgb.b) / 255;
    };

    const getContrast = (color1: string, color2: string): number => {
      const lum1 = getLuminance(color1);
      const lum2 = getLuminance(color2);
      const brightest = Math.max(lum1, lum2);
      const darkest = Math.min(lum1, lum2);
      return (brightest + 0.05) / (darkest + 0.05);
    };

    return {
      normalText: getContrast(colors.text, colors.background),
      largeText: getContrast(colors.text, colors.background),
      graphicalObjects: Math.max(
        getContrast(colors.bullish, colors.background),
        getContrast(colors.bearish, colors.background),
      ),
    };
  }

  /**
   * 十六进制颜色转RGB
   */
  private hexToRgb(hex: string): { r: number; g: number; b: number } {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result
      ? {
          r: parseInt(result[1], 16),
          g: parseInt(result[2], 16),
          b: parseInt(result[3], 16),
        }
      : { r: 0, g: 0, b: 0 };
  }

  /**
   * 发布事件
   */
  private publishEvent(event: ThemeUpdateEvent): void {
    this.listeners.forEach((listener) => {
      try {
        listener(event);
      } catch (error) {
        console.error('主题事件监听器错误:', error);
      }
    });
  }

  /**
   * 获取默认主题
   */
  private getDefaultTheme(): ThemeConfig {
    return this.getDefaultThemes()[0]; // 返回第一个默认主题
  }

  /**
   * 获取默认主题列表
   */
  private getDefaultThemes(): ThemeConfig[] {
    return [
      {
        id: 'light_chinese',
        name: '浅色主题（中国市场）',
        description: '适合中国用户的浅色主题，红涨绿跌',
        mode: 'light',
        marketMode: 'chinese',
        colorblindMode: 'none',
        colors: this.getMarketColors('chinese', 'light'),
      },
      {
        id: 'light_international',
        name: '浅色主题（国际市场）',
        description: '适合国际用户的浅色主题，绿涨红跌',
        mode: 'light',
        marketMode: 'international',
        colorblindMode: 'none',
        colors: this.getMarketColors('international', 'light'),
      },
      {
        id: 'dark_chinese',
        name: '深色主题（中国市场）',
        description: '适合中国用户的深色主题，红涨绿跌',
        mode: 'dark',
        marketMode: 'chinese',
        colorblindMode: 'none',
        colors: this.getMarketColors('chinese', 'dark'),
      },
      {
        id: 'dark_international',
        name: '深色主题（国际市场）',
        description: '适合国际用户的深色主题，绿涨红跌',
        mode: 'dark',
        marketMode: 'international',
        colorblindMode: 'none',
        colors: this.getMarketColors('international', 'dark'),
      },
    ];
  }

  /**
   * 初始化默认主题
   */
  private initializeDefaultThemes(): void {
    // 这里可以添加更多默认主题
  }

  /**
   * 保存到本地存储
   */
  private saveToStorage(): void {
    try {
      const data = {
        currentTheme: this.currentTheme,
        customThemes: Array.from(this.customThemes.entries()),
        presets: Array.from(this.presets.entries()),
      };
      localStorage.setItem('themeService', JSON.stringify(data));
    } catch (error) {
      console.error('保存主题配置失败:', error);
    }
  }

  /**
   * 从本地存储加载
   */
  private loadFromStorage(): void {
    try {
      const stored = localStorage.getItem('themeService');
      if (stored) {
        const data = JSON.parse(stored);

        if (data.currentTheme) {
          this.currentTheme = data.currentTheme;
        }

        if (data.customThemes) {
          this.customThemes = new Map(data.customThemes);
        }

        if (data.presets) {
          this.presets = new Map(data.presets);
        }
      }
    } catch (error) {
      console.error('加载主题配置失败:', error);
    }
  }
}

// 导出单例实例
export const themeService = ThemeService.getInstance();
