'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Zap,
  Eye,
  EyeOff,
  Volume2,
  VolumeX,
  Monitor,
  Smartphone,
  Accessibility,
  Timer,
  Settings,
  ChevronDown,
  ChevronUp,
  Sun,
  Moon,
  Palette,
  Type,
  RotateCcw
} from 'lucide-react';

// 用户偏好设置
interface UserPreferences {
  theme: 'light' | 'dark' | 'auto';
  fontSize: 'small' | 'medium' | 'large' | 'extra-large';
  animationsEnabled: boolean;
  soundEnabled: boolean;
  autoPlay: boolean;
  readingSpeed: 'slow' | 'normal' | 'fast';
  language: string;
  highContrast: boolean;
  reducedMotion: boolean;
  screenReaderOptimized: boolean;
  keyboardNavigation: boolean;
  showProgressIndicators: boolean;
  autoSaveInterval: number; // minutes
  prefetchContent: boolean;
  dataSaver: boolean;
}

// 性能指标
interface PerformanceMetrics {
  averageResponseTime: number;
  errorRate: number;
  completionRate: number;
  userSatisfaction: number;
  sessionDuration: number;
  interactionFrequency: number;
}

// 用户体验优化建议
interface OptimizationSuggestion {
  id: string;
  type: 'performance' | 'accessibility' | 'engagement' | 'navigation';
  priority: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  action: {
    type: 'setting' | 'behavior' | 'technical';
    label: string;
    action: () => void;
  };
  impact: string;
}

interface UserExperienceOptimizerProps {
  /** 当前用户偏好 */
  currentPreferences?: Partial<UserPreferences>;
  /** 性能指标 */
  performanceMetrics?: PerformanceMetrics;
  /** 是否显示性能面板 */
  showPerformancePanel?: boolean;
  /** 是否显示快速设置 */
  showQuickSettings?: boolean;
  /** 偏好更新回调 */
  onPreferencesUpdate?: (preferences: UserPreferences) => void;
  /** 自定义样式类名 */
  className?: string;
}

const DEFAULT_PREFERENCES: UserPreferences = {
  theme: 'auto',
  fontSize: 'medium',
  animationsEnabled: true,
  soundEnabled: false,
  autoPlay: false,
  readingSpeed: 'normal',
  language: 'zh-CN',
  highContrast: false,
  reducedMotion: false,
  screenReaderOptimized: false,
  keyboardNavigation: true,
  showProgressIndicators: true,
  autoSaveInterval: 5,
  prefetchContent: true,
  dataSaver: false,
};

const UserExperienceOptimizer: React.FC<UserExperienceOptimizerProps> = ({
  currentPreferences = {},
  performanceMetrics,
  showPerformancePanel = true,
  showQuickSettings = true,
  onPreferencesUpdate,
  className = '',
}) => {
  const [preferences, setPreferences] = useState<UserPreferences>({
    ...DEFAULT_PREFERENCES,
    ...currentPreferences,
  });
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<'settings' | 'performance' | 'optimizations'>('settings');
  const [suggestions, setSuggestions] = useState<OptimizationSuggestion[]>([]);
  const performanceRef = useRef<PerformanceMetrics>();

  // 加载保存的偏好设置
  useEffect(() => {
    try {
      const saved = localStorage.getItem('tutorial_user_preferences');
      if (saved) {
        const savedPreferences = JSON.parse(saved);
        setPreferences({ ...DEFAULT_PREFERENCES, ...savedPreferences, ...currentPreferences });
      }
    } catch (error) {
      console.warn('Failed to load user preferences:', error);
    }
  }, [currentPreferences]);

  // 检测系统主题偏好
  useEffect(() => {
    if (preferences.theme === 'auto') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = (e: MediaQueryListEvent) => {
        document.documentElement.classList.toggle('dark', e.matches);
      };

      // 设置初始主题
      document.documentElement.classList.toggle('dark', mediaQuery.matches);

      // 监听主题变化
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    } else {
      document.documentElement.classList.toggle('dark', preferences.theme === 'dark');
    }
  }, [preferences.theme]);

  // 应用字体大小
  useEffect(() => {
    const root = document.documentElement;
    const fontSizeMap = {
      'small': '14px',
      'medium': '16px',
      'large': '18px',
      'extra-large': '20px',
    };
    root.style.fontSize = fontSizeMap[preferences.fontSize];
  }, [preferences.fontSize]);

  // 应用动画设置
  useEffect(() => {
    const root = document.documentElement;
    if (preferences.reducedMotion || !preferences.animationsEnabled) {
      root.style.setProperty('--animation-duration', '0.01ms');
    } else {
      root.style.removeProperty('--animation-duration');
    }
  }, [preferences.animationsEnabled, preferences.reducedMotion]);

  // 应用高对比度
  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle('high-contrast', preferences.highContrast);
  }, [preferences.highContrast]);

  // 保存偏好设置
  const savePreferences = useCallback((newPreferences: UserPreferences) => {
    setPreferences(newPreferences);
    onPreferencesUpdate?.(newPreferences);

    try {
      localStorage.setItem('tutorial_user_preferences', JSON.stringify(newPreferences));
    } catch (error) {
      console.warn('Failed to save user preferences:', error);
    }
  }, [onPreferencesUpdate]);

  // 更新偏好设置
  const updatePreference = useCallback(<K extends keyof UserPreferences>(
    key: K,
    value: UserPreferences[K]
  ) => {
    const newPreferences = { ...preferences, [key]: value };
    savePreferences(newPreferences);
  }, [preferences, savePreferences]);

  // 生成优化建议
  const generateOptimizationSuggestions = useCallback(() => {
    const newSuggestions: OptimizationSuggestion[] = [];

    // 基于性能指标的建议
    if (performanceMetrics) {
      if (performanceMetrics.averageResponseTime > 1000) {
        newSuggestions.push({
          id: 'perf-response-time',
          type: 'performance',
          priority: 'high',
          title: '优化响应时间',
          description: '当前响应时间较慢，建议启用数据节省模式或减少动画效果',
          action: {
            type: 'setting',
            label: '启用数据节省',
            action: () => updatePreference('dataSaver', true),
          },
          impact: '可提升30-50%的响应速度',
        });
      }

      if (performanceMetrics.completionRate < 0.6) {
        newSuggestions.push({
          id: 'engagement-completion',
          type: 'engagement',
          priority: 'medium',
          title: '提升完成率',
          description: '当前完成率较低，建议调整阅读速度或增加自动播放',
          action: {
            type: 'setting',
            label: '调整阅读速度',
            action: () => updatePreference('readingSpeed', 'slow'),
          },
          impact: '预计提升20-30%的完成率',
        });
      }

      if (performanceMetrics.errorRate > 0.1) {
        newSuggestions.push({
          id: 'accessibility-errors',
          type: 'accessibility',
          priority: 'high',
          title: '减少错误率',
          description: '当前错误率较高，建议启用高对比度或屏幕阅读器优化',
          action: {
            type: 'setting',
            label: '启用高对比度',
            action: () => updatePreference('highContrast', true),
          },
          impact: '显著减少用户操作错误',
        });
      }
    }

    // 基于当前设置的建议
    if (!preferences.animationsEnabled && !preferences.reducedMotion) {
      newSuggestions.push({
        id: 'animations-recommendation',
        type: 'engagement',
        priority: 'low',
        title: '启用动画效果',
        description: '启用动画可以提升用户体验和交互理解',
        action: {
          type: 'setting',
          label: '启用动画',
          action: () => updatePreference('animationsEnabled', true),
        },
        impact: '提升视觉体验和交互理解',
      });
    }

    if (!preferences.keyboardNavigation) {
      newSuggestions.push({
        id: 'keyboard-navigation',
        type: 'accessibility',
        priority: 'medium',
        title: '启用键盘导航',
        description: '键盘导航可以提升无障碍访问性和操作效率',
        action: {
          type: 'setting',
          label: '启用键盘导航',
          action: () => updatePreference('keyboardNavigation', true),
        },
        impact: '提升无障碍访问性',
      });
    }

    setSuggestions(newSuggestions);
  }, [performanceMetrics, preferences, updatePreference]);

  // 生成优化建议
  useEffect(() => {
    generateOptimizationSuggestions();
  }, [generateOptimizationSuggestions]);

  // 重置为默认设置
  const resetToDefaults = useCallback(() => {
    savePreferences(DEFAULT_PREFERENCES);
  }, [savePreferences]);

  // 渲染设置面板
  const renderSettingsPanel = () => (
    <div className="space-y-6">
      {/* 外观设置 */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">外观设置</h3>
        <div className="space-y-4">
          {/* 主题选择 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {preferences.theme === 'dark' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
              <span className="text-sm font-medium">主题</span>
            </div>
            <select
              value={preferences.theme}
              onChange={(e) => updatePreference('theme', e.target.value as UserPreferences['theme'])}
              className="px-3 py-1 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="light">浅色</option>
              <option value="dark">深色</option>
              <option value="auto">跟随系统</option>
            </select>
          </div>

          {/* 字体大小 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Type className="w-4 h-4" />
              <span className="text-sm font-medium">字体大小</span>
            </div>
            <select
              value={preferences.fontSize}
              onChange={(e) => updatePreference('fontSize', e.target.value as UserPreferences['fontSize'])}
              className="px-3 py-1 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="small">小</option>
              <option value="medium">中</option>
              <option value="large">大</option>
              <option value="extra-large">特大</option>
            </select>
          </div>

          {/* 高对比度 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Eye className="w-4 h-4" />
              <span className="text-sm font-medium">高对比度</span>
            </div>
            <button
              onClick={() => updatePreference('highContrast', !preferences.highContrast)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                preferences.highContrast ? 'bg-blue-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  preferences.highContrast ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>
      </div>

      {/* 交互设置 */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">交互设置</h3>
        <div className="space-y-4">
          {/* 动画效果 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4" />
              <span className="text-sm font-medium">动画效果</span>
            </div>
            <button
              onClick={() => updatePreference('animationsEnabled', !preferences.animationsEnabled)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                preferences.animationsEnabled ? 'bg-blue-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  preferences.animationsEnabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* 声音效果 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {preferences.soundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
              <span className="text-sm font-medium">声音效果</span>
            </div>
            <button
              onClick={() => updatePreference('soundEnabled', !preferences.soundEnabled)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                preferences.soundEnabled ? 'bg-blue-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  preferences.soundEnabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* 自动播放 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Timer className="w-4 h-4" />
              <span className="text-sm font-medium">自动播放</span>
            </div>
            <button
              onClick={() => updatePreference('autoPlay', !preferences.autoPlay)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                preferences.autoPlay ? 'bg-blue-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  preferences.autoPlay ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* 阅读速度 */}
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">阅读速度</span>
            <select
              value={preferences.readingSpeed}
              onChange={(e) => updatePreference('readingSpeed', e.target.value as UserPreferences['readingSpeed'])}
              className="px-3 py-1 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="slow">慢</option>
              <option value="normal">正常</option>
              <option value="fast">快</option>
            </select>
          </div>
        </div>
      </div>

      {/* 无障碍设置 */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">无障碍设置</h3>
        <div className="space-y-4">
          {/* 减少动画 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <EyeOff className="w-4 h-4" />
              <span className="text-sm font-medium">减少动画</span>
            </div>
            <button
              onClick={() => updatePreference('reducedMotion', !preferences.reducedMotion)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                preferences.reducedMotion ? 'bg-blue-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  preferences.reducedMotion ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* 键盘导航 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Monitor className="w-4 h-4" />
              <span className="text-sm font-medium">键盘导航</span>
            </div>
            <button
              onClick={() => updatePreference('keyboardNavigation', !preferences.keyboardNavigation)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                preferences.keyboardNavigation ? 'bg-blue-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  preferences.keyboardNavigation ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* 屏幕阅读器优化 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Accessibility className="w-4 h-4" />
              <span className="text-sm font-medium">屏幕阅读器优化</span>
            </div>
            <button
              onClick={() => updatePreference('screenReaderOptimized', !preferences.screenReaderOptimized)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                preferences.screenReaderOptimized ? 'bg-blue-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  preferences.screenReaderOptimized ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>
      </div>

      {/* 性能设置 */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">性能设置</h3>
        <div className="space-y-4">
          {/* 数据节省 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Smartphone className="w-4 h-4" />
              <span className="text-sm font-medium">数据节省</span>
            </div>
            <button
              onClick={() => updatePreference('dataSaver', !preferences.dataSaver)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                preferences.dataSaver ? 'bg-blue-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  preferences.dataSaver ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* 预取内容 */}
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">预取内容</span>
            <button
              onClick={() => updatePreference('prefetchContent', !preferences.prefetchContent)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                preferences.prefetchContent ? 'bg-blue-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  preferences.prefetchContent ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* 自动保存间隔 */}
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">自动保存间隔</span>
            <select
              value={preferences.autoSaveInterval}
              onChange={(e) => updatePreference('autoSaveInterval', parseInt(e.target.value))}
              className="px-3 py-1 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={1}>1分钟</option>
              <option value={5}>5分钟</option>
              <option value={10}>10分钟</option>
              <option value={30}>30分钟</option>
            </select>
          </div>
        </div>
      </div>

      {/* 重置按钮 */}
      <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={resetToDefaults}
          className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white transition-colors"
        >
          <RotateCcw className="w-4 h-4" />
          重置为默认设置
        </button>
      </div>
    </div>
  );

  // 渲染性能面板
  const renderPerformancePanel = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">性能指标</h3>

      {performanceMetrics ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {Math.round(performanceMetrics.averageResponseTime)}ms
            </div>
            <div className="text-sm text-blue-800 dark:text-blue-200">平均响应时间</div>
          </div>

          <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
              {Math.round(performanceMetrics.completionRate * 100)}%
            </div>
            <div className="text-sm text-green-800 dark:text-green-200">完成率</div>
          </div>

          <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">
              {Math.round(performanceMetrics.errorRate * 100)}%
            </div>
            <div className="text-sm text-red-800 dark:text-red-200">错误率</div>
          </div>

          <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
              {Math.round(performanceMetrics.userSatisfaction * 100)}%
            </div>
            <div className="text-sm text-purple-800 dark:text-purple-200">用户满意度</div>
          </div>
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">
          暂无性能数据
        </div>
      )}

      {/* 性能建议 */}
      <div>
        <h4 className="text-md font-semibold text-gray-900 dark:text-white mb-3">性能优化建议</h4>
        <div className="space-y-2">
          {preferences.dataSaver ? (
            <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg text-sm text-green-800 dark:text-green-200">
              ✓ 数据节省模式已启用，有助于提升性能
            </div>
          ) : (
            <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg text-sm text-yellow-800 dark:text-yellow-200">
              ⚠ 启用数据节省模式可以提升性能
            </div>
          )}

          {preferences.animationsEnabled ? (
            <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg text-sm text-yellow-800 dark:text-yellow-200">
              ⚠ 关闭动画效果可以提升性能
            </div>
          ) : (
            <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg text-sm text-green-800 dark:text-green-200">
              ✓ 动画效果已关闭，有助于提升性能
            </div>
          )}
        </div>
      </div>
    </div>
  );

  // 渲染优化建议
  const renderOptimizations = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">优化建议</h3>

      {suggestions.length > 0 ? (
        <div className="space-y-3">
          {suggestions.map(suggestion => (
            <div
              key={suggestion.id}
              className={`p-4 rounded-lg border ${
                suggestion.priority === 'high'
                  ? 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800'
                  : suggestion.priority === 'medium'
                  ? 'bg-yellow-50 border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-800'
                  : 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <h4 className="font-medium text-gray-900 dark:text-white mb-1">
                    {suggestion.title}
                  </h4>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                    {suggestion.description}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-500">
                    预期效果: {suggestion.impact}
                  </p>
                </div>
                <button
                  onClick={suggestion.action.action}
                  className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                >
                  {suggestion.action.label}
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">
          <Settings className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>当前设置已优化，无额外建议</p>
        </div>
      )}
    </div>
  );

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <Settings className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">用户体验优化</h2>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
        >
          {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>
      </div>

      {/* Quick Settings */}
      {showQuickSettings && !isExpanded && (
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => updatePreference('theme', preferences.theme === 'dark' ? 'light' : 'dark')}
              className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            >
              {preferences.theme === 'dark' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
            </button>
            <button
              onClick={() => updatePreference('animationsEnabled', !preferences.animationsEnabled)}
              className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            >
              <Zap className="w-4 h-4" />
            </button>
            <button
              onClick={() => updatePreference('fontSize',
                preferences.fontSize === 'medium' ? 'large' :
                preferences.fontSize === 'large' ? 'small' : 'medium'
              )}
              className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            >
              <Type className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Expanded Content */}
      {isExpanded && (
        <div className="p-4">
          {/* Tab Navigation */}
          <div className="flex gap-1 mb-6 p-1 bg-gray-100 dark:bg-gray-700 rounded-lg">
            <button
              onClick={() => setActiveTab('settings')}
              className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'settings'
                  ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              设置
            </button>
            {showPerformancePanel && (
              <button
                onClick={() => setActiveTab('performance')}
                className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                  activeTab === 'performance'
                    ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                性能
              </button>
            )}
            <button
              onClick={() => setActiveTab('optimizations')}
              className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'optimizations'
                  ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              优化建议
            </button>
          </div>

          {/* Tab Content */}
          <div className="min-h-[400px]">
            {activeTab === 'settings' && renderSettingsPanel()}
            {activeTab === 'performance' && renderPerformancePanel()}
            {activeTab === 'optimizations' && renderOptimizations()}
          </div>
        </div>
      )}
    </div>
  );
};

export default UserExperienceOptimizer;