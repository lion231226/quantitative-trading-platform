import {
  DEFAULT_SIGNAL_THEMES,
  MarkerShape,
  PRESET_STRATEGIES,
  SignalMarkerStyle,
  SignalType,
  StrategyConfig,
  StrategyType,
} from '../types/strategySignal.types';

// 样式主题配置
export interface StyleTheme {
  id: string;
  name: string;
  description: string;
  colors: {
    background: string;
    text: string;
    grid: string;
    border: string;
  };
  signalStyles: Record<SignalType, SignalMarkerStyle>;
}

// 用户自定义样式配置
export interface UserStyleConfig {
  strategyId: string;
  signalType: SignalType;
  style: Partial<SignalMarkerStyle>;
  enabled: boolean;
  createdAt: number;
  updatedAt: number;
}

// 样式预设
export interface StylePreset {
  id: string;
  name: string;
  description: string;
  category: 'professional' | 'educational' | 'accessibility' | 'custom';
  strategies: Record<string, Record<SignalType, SignalMarkerStyle>>;
  metadata?: {
    author?: string;
    version?: string;
    tags?: string[];
  };
}

// 样式配置服务类
export class StyleConfigService {
  private themes = new Map<string, StyleTheme>();
  private userConfigs = new Map<string, UserStyleConfig>();
  private presets = new Map<string, StylePreset>();
  private currentTheme: string = 'light';

  constructor() {
    this.initializeDefaultThemes();
    this.initializeDefaultPresets();
  }

  /**
   * 获取策略信号样式
   */
  getSignalStyle(
    strategyId: string,
    signalType: SignalType,
    confidence: number = 100,
  ): SignalMarkerStyle {
    // 1. 检查用户自定义样式
    const userConfig = this.getUserStyleConfig(strategyId, signalType);
    if (userConfig && userConfig.enabled) {
      return this.applyConfidenceAdjustment(userConfig.style, confidence);
    }

    // 2. 检查预设策略样式
    const presetStrategy = PRESET_STRATEGIES[strategyId];
    if (presetStrategy && presetStrategy.styles[signalType]) {
      return this.applyConfidenceAdjustment(
        presetStrategy.styles[signalType],
        confidence,
      );
    }

    // 3. 使用当前主题的默认样式
    const currentTheme = this.themes.get(this.currentTheme);
    if (currentTheme && currentTheme.signalStyles[signalType]) {
      return this.applyConfidenceAdjustment(
        currentTheme.signalStyles[signalType],
        confidence,
      );
    }

    // 4. 最后的回退样式
    return this.applyConfidenceAdjustment(
      DEFAULT_SIGNAL_THEMES.light[signalType],
      confidence,
    );
  }

  /**
   * 设置当前主题
   */
  setCurrentTheme(themeId: string): void {
    if (this.themes.has(themeId)) {
      this.currentTheme = themeId;
      this.saveToStorage();
    } else {
      throw new Error(`主题未找到: ${themeId}`);
    }
  }

  /**
   * 获取当前主题
   */
  getCurrentTheme(): StyleTheme | null {
    return this.themes.get(this.currentTheme) || null;
  }

  /**
   * 获取所有主题
   */
  getAllThemes(): StyleTheme[] {
    return Array.from(this.themes.values());
  }

  /**
   * 添加自定义主题
   */
  addCustomTheme(theme: Omit<StyleTheme, 'id'>): string {
    const id = `custom_${Date.now()}`;
    const fullTheme: StyleTheme = {
      id,
      ...theme,
    };

    this.themes.set(id, fullTheme);
    this.saveToStorage();
    return id;
  }

  /**
   * 更新用户样式配置
   */
  updateUserStyleConfig(
    strategyId: string,
    signalType: SignalType,
    style: Partial<SignalMarkerStyle>,
  ): void {
    const key = this.generateConfigKey(strategyId, signalType);
    const existingConfig = this.userConfigs.get(key);

    const config: UserStyleConfig = {
      strategyId,
      signalType,
      style,
      enabled: true,
      createdAt: existingConfig?.createdAt || Date.now(),
      updatedAt: Date.now(),
    };

    this.userConfigs.set(key, config);
    this.saveToStorage();
  }

  /**
   * 删除用户样式配置
   */
  removeUserStyleConfig(strategyId: string, signalType: SignalType): void {
    const key = this.generateConfigKey(strategyId, signalType);
    this.userConfigs.delete(key);
    this.saveToStorage();
  }

  /**
   * 启用/禁用用户样式配置
   */
  toggleUserStyleConfig(
    strategyId: string,
    signalType: SignalType,
    enabled: boolean,
  ): void {
    const key = this.generateConfigKey(strategyId, signalType);
    const config = this.userConfigs.get(key);

    if (config) {
      config.enabled = enabled;
      config.updatedAt = Date.now();
      this.saveToStorage();
    }
  }

  /**
   * 获取用户样式配置
   */
  getUserStyleConfig(
    strategyId: string,
    signalType: SignalType,
  ): UserStyleConfig | null {
    const key = this.generateConfigKey(strategyId, signalType);
    return this.userConfigs.get(key) || null;
  }

  /**
   * 获取所有用户样式配置
   */
  getAllUserStyleConfigs(): UserStyleConfig[] {
    return Array.from(this.userConfigs.values());
  }

  /**
   * 应用样式预设
   */
  applyStylePreset(presetId: string): void {
    const preset = this.presets.get(presetId);
    if (!preset) {
      throw new Error(`样式预设未找到: ${presetId}`);
    }

    // 清除现有的用户配置
    this.userConfigs.clear();

    // 应用预设配置
    for (const [strategyId, signalStyles] of Object.entries(
      preset.strategies,
    )) {
      for (const [signalType, style] of Object.entries(signalStyles)) {
        this.updateUserStyleConfig(strategyId, signalType as SignalType, style);
      }
    }

    this.saveToStorage();
  }

  /**
   * 创建样式预设
   */
  createStylePreset(
    name: string,
    description: string,
    category: StylePreset['category'],
    metadata?: StylePreset['metadata'],
  ): string {
    const id = `preset_${Date.now()}`;
    const strategies: Record<
      string,
      Record<SignalType, SignalMarkerStyle>
    > = {};

    // 从当前用户配置创建预设
    for (const config of this.userConfigs.values()) {
      if (!strategies[config.strategyId]) {
        strategies[config.strategyId] = {} as Record<
          SignalType,
          SignalMarkerStyle
        >;
      }
      strategies[config.strategyId][config.signalType] =
        config.style as SignalMarkerStyle;
    }

    const preset: StylePreset = {
      id,
      name,
      description,
      category,
      strategies,
      metadata,
    };

    this.presets.set(id, preset);
    this.saveToStorage();
    return id;
  }

  /**
   * 获取所有样式预设
   */
  getAllStylePresets(): StylePreset[] {
    return Array.from(this.presets.values());
  }

  /**
   * 删除样式预设
   */
  removeStylePreset(presetId: string): void {
    this.presets.delete(presetId);
    this.saveToStorage();
  }

  /**
   * 重置为默认样式
   */
  resetToDefaults(): void {
    this.userConfigs.clear();
    // 清除所有自定义预设（保留默认预设）
    const defaultPresetIds = new Set(['default_light', 'default_dark']);
    for (const [id, preset] of this.presets.entries()) {
      if (!defaultPresetIds.has(id) && preset.category === 'custom') {
        this.presets.delete(id);
      }
    }
    this.currentTheme = 'light';
    this.saveToStorage();
  }

  /**
   * 导出样式配置
   */
  exportStyles(): {
    theme: string;
    userConfigs: UserStyleConfig[];
    presets: StylePreset[];
  } {
    return {
      theme: this.currentTheme,
      userConfigs: this.getAllUserStyleConfigs(),
      presets: this.getAllStylePresets(),
    };
  }

  /**
   * 导入样式配置
   */
  importStyles(exportedStyles: {
    theme?: string;
    userConfigs?: UserStyleConfig[];
    presets?: StylePreset[];
  }): void {
    if (exportedStyles.theme && this.themes.has(exportedStyles.theme)) {
      this.currentTheme = exportedStyles.theme;
    }

    if (exportedStyles.userConfigs) {
      for (const config of exportedStyles.userConfigs) {
        const key = this.generateConfigKey(
          config.strategyId,
          config.signalType,
        );
        this.userConfigs.set(key, config);
      }
    }

    if (exportedStyles.presets) {
      for (const preset of exportedStyles.presets) {
        this.presets.set(preset.id, preset);
      }
    }

    this.saveToStorage();
  }

  /**
   * 私有方法：初始化默认主题
   */
  private initializeDefaultThemes(): void {
    // 浅色主题
    const lightTheme: StyleTheme = {
      id: 'light',
      name: '浅色主题',
      description: '适合白天使用的明亮主题',
      colors: {
        background: '#ffffff',
        text: '#1f2937',
        grid: '#e5e7eb',
        border: '#d1d5db',
      },
      signalStyles: DEFAULT_SIGNAL_THEMES.light,
    };

    // 深色主题
    const darkTheme: StyleTheme = {
      id: 'dark',
      name: '深色主题',
      description: '适合夜间使用的深色主题',
      colors: {
        background: '#1f2937',
        text: '#f9fafb',
        grid: '#374151',
        border: '#4b5563',
      },
      signalStyles: DEFAULT_SIGNAL_THEMES.dark,
    };

    // 高对比度主题
    const highContrastTheme: StyleTheme = {
      id: 'high_contrast',
      name: '高对比度主题',
      description: '为视力障碍用户设计的高对比度主题',
      colors: {
        background: '#000000',
        text: '#ffffff',
        grid: '#666666',
        border: '#ffffff',
      },
      signalStyles: {
        buy: {
          shape: 'arrow_up',
          color: '#00ff00',
          size: 14,
          opacity: 1,
          border: { color: '#ffffff', width: 3 },
          textColor: '#000000',
          fontSize: 12,
        },
        sell: {
          shape: 'arrow_down',
          color: '#ff0000',
          size: 14,
          opacity: 1,
          border: { color: '#ffffff', width: 3 },
          textColor: '#000000',
          fontSize: 12,
        },
        hold: {
          shape: 'square',
          color: '#ffff00',
          size: 12,
          opacity: 1,
          border: { color: '#ffffff', width: 2 },
          textColor: '#000000',
          fontSize: 10,
        },
        stop_loss: {
          shape: 'circle',
          color: '#ff9900',
          size: 12,
          opacity: 1,
          border: { color: '#ffffff', width: 2 },
          textColor: '#000000',
          fontSize: 10,
        },
        take_profit: {
          shape: 'diamond',
          color: '#00ffff',
          size: 12,
          opacity: 1,
          border: { color: '#ffffff', width: 2 },
          textColor: '#000000',
          fontSize: 10,
        },
      },
    };

    this.themes.set(lightTheme.id, lightTheme);
    this.themes.set(darkTheme.id, darkTheme);
    this.themes.set(highContrastTheme.id, highContrastTheme);
  }

  /**
   * 私有方法：初始化默认预设
   */
  private initializeDefaultPresets(): void {
    // 专业交易员预设
    const professionalPreset: StylePreset = {
      id: 'professional',
      name: '专业交易员',
      description: '适合专业交易员的简洁、高效样式',
      category: 'professional',
      strategies: {
        sma_crossover: {
          buy: {
            shape: 'arrow_up',
            color: '#10b981',
            size: 10,
            opacity: 0.8,
            border: { color: '#059669', width: 1 },
            textColor: '#ffffff',
            fontSize: 8,
          },
          sell: {
            shape: 'arrow_down',
            color: '#ef4444',
            size: 10,
            opacity: 0.8,
            border: { color: '#dc2626', width: 1 },
            textColor: '#ffffff',
            fontSize: 8,
          },
        },
      },
      metadata: {
        author: 'System',
        version: '1.0.0',
        tags: ['professional', 'minimal', 'trading'],
      },
    };

    // 教育演示预设
    const educationalPreset: StylePreset = {
      id: 'educational',
      name: '教育演示',
      description: '适合教学和演示的清晰、醒目样式',
      category: 'educational',
      strategies: {
        sma_crossover: {
          buy: {
            shape: 'arrow_up',
            color: '#22c55e',
            size: 16,
            opacity: 1,
            border: { color: '#15803d', width: 3 },
            textColor: '#ffffff',
            fontSize: 12,
          },
          sell: {
            shape: 'arrow_down',
            color: '#ef4444',
            size: 16,
            opacity: 1,
            border: { color: '#991b1b', width: 3 },
            textColor: '#ffffff',
            fontSize: 12,
          },
        },
      },
      metadata: {
        author: 'System',
        version: '1.0.0',
        tags: ['education', 'demo', 'clear'],
      },
    };

    this.presets.set(professionalPreset.id, professionalPreset);
    this.presets.set(educationalPreset.id, educationalPreset);
  }

  /**
   * 私有方法：应用置信度调整
   */
  private applyConfidenceAdjustment(
    baseStyle: SignalMarkerStyle,
    confidence: number,
  ): SignalMarkerStyle {
    const adjustedStyle = { ...baseStyle };

    // 根据置信度调整透明度
    adjustedStyle.opacity = Math.max(
      0.3,
      Math.min(1, (confidence / 100) * 0.7 + 0.3),
    );

    // 根据置信度调整大小
    const sizeMultiplier = 0.8 + (confidence / 100) * 0.4; // 0.8-1.2倍
    adjustedStyle.size = Math.round(baseStyle.size * sizeMultiplier);

    return adjustedStyle;
  }

  /**
   * 私有方法：生成配置键
   */
  private generateConfigKey(
    strategyId: string,
    signalType: SignalType,
  ): string {
    return `${strategyId}_${signalType}`;
  }

  /**
   * 私有方法：保存到本地存储
   */
  private saveToStorage(): void {
    try {
      const data = {
        currentTheme: this.currentTheme,
        userConfigs: Array.from(this.userConfigs.entries()),
        presets: Array.from(this.presets.entries()),
      };
      localStorage.setItem('styleConfigService', JSON.stringify(data));
    } catch (error) {
      console.error('保存样式配置失败:', error);
    }
  }

  /**
   * 私有方法：从本地存储加载
   */
  private loadFromStorage(): void {
    try {
      const stored = localStorage.getItem('styleConfigService');
      if (stored) {
        const data = JSON.parse(stored);

        if (data.currentTheme) {
          this.currentTheme = data.currentTheme;
        }

        if (data.userConfigs) {
          this.userConfigs = new Map(data.userConfigs);
        }

        if (data.presets) {
          this.presets = new Map(data.presets);
        }
      }
    } catch (error) {
      console.error('加载样式配置失败:', error);
    }
  }
}

// 导出单例实例
export const styleConfigService = new StyleConfigService();
