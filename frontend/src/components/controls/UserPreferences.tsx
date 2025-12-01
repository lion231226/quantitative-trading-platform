'use client';

import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertCircle,
  Check,
  Download,
  RotateCcw,
  Save,
  Settings,
  Upload,
  X,
} from 'lucide-react';
import {
  StrategyParameters,
  UserPreferences as UserPreferencesType,
} from '@/types/parameter.types';

// localStorage wrapper for testability
const getLocalStorage = () => {
  if (typeof window !== 'undefined' && window.localStorage) {
    return window.localStorage;
  }
  // Fallback for SSR or missing localStorage
  return {
    getItem: () => null,
    setItem: () => {},
    removeItem: () => {},
    clear: () => {},
    length: 0,
    key: () => null,
  };
};

interface UserPreferencesProps {
  currentParameters: StrategyParameters;
  onParametersChange?: (parameters: StrategyParameters) => void;
  className?: string;
}

// 默认配置
const DEFAULT_PREFERENCES: UserPreferencesType = {
  defaultParameters: {
    movingAveragePeriod: 20,
    stopLoss: 5.0,
    takeProfit: 10.0,
  },
  favoritePresets: [],
  autoSave: true,
  showAdvanced: false,
  chartPreferences: {
    showGrid: true,
    showVolume: false,
    animationDuration: 300,
  },
};

// 本地存储键
const STORAGE_KEYS = {
  PREFERENCES: 'strategy_user_preferences',
  PARAMETERS_BACKUP: 'strategy_parameters_backup',
  LAST_USED: 'strategy_last_used_parameters',
};

const UserPreferences: React.FC<UserPreferencesProps> = ({
  currentParameters,
  onParametersChange,
  className = '',
}) => {
  const [preferences, setPreferences] =
    useState<UserPreferencesType>(DEFAULT_PREFERENCES);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  // 显示消息
  const showMessage = useCallback((type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 3000);
  }, []);

  // 加载用户偏好
  const loadPreferences = useCallback(() => {
    try {
      const storage = getLocalStorage();
      const stored = storage.getItem(STORAGE_KEYS.PREFERENCES);
      if (stored) {
        const parsedPreferences = JSON.parse(stored);
        setPreferences({ ...DEFAULT_PREFERENCES, ...parsedPreferences });
      }
    } catch (error) {
      console.error('加载用户偏好失败:', error);
      setMessage({ type: 'error', text: '加载用户偏好失败，使用默认设置' });
      setTimeout(() => setMessage(null), 3000);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 保存用户偏好
  const savePreferences = useCallback(
    async (newPreferences: UserPreferencesType) => {
      setIsSaving(true);
      const storage = getLocalStorage();

      try {
        storage.setItem(
          STORAGE_KEYS.PREFERENCES,
          JSON.stringify(newPreferences),
        );
        setPreferences(newPreferences);

        // 自动保存当前参数
        if (newPreferences.autoSave) {
          storage.setItem(
            STORAGE_KEYS.LAST_USED,
            JSON.stringify(currentParameters),
          );
        }

        setMessage({ type: 'success', text: '偏好设置已保存' });
        setTimeout(() => setMessage(null), 3000);
      } catch (error) {
        console.error('保存用户偏好失败:', error);
        setMessage({ type: 'error', text: '保存偏好设置失败' });
        setTimeout(() => setMessage(null), 3000);
      } finally {
        setIsSaving(false);
      }
    },
    [currentParameters],
  );

  // 重置为默认设置
  const resetToDefaults = useCallback(async () => {
    if (window.confirm('确定要重置为默认设置吗？这将清除所有自定义偏好。')) {
      await savePreferences(DEFAULT_PREFERENCES);
      onParametersChange?.(DEFAULT_PREFERENCES.defaultParameters);
      setMessage({ type: 'success', text: '设置已重置为默认值' });
      setTimeout(() => setMessage(null), 3000);
    }
  }, [savePreferences, onParametersChange]);

  // 导出配置
  const exportConfiguration = useCallback(() => {
    try {
      const exportData = {
        version: '1.0',
        timestamp: new Date().toISOString(),
        preferences,
        currentParameters,
        backupHistory: getBackupHistory(),
      };

      const blob = new Blob([JSON.stringify(exportData, null, 2)], {
        type: 'application/json',
      });

      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `strategy-config-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      setMessage({ type: 'success', text: '配置已导出' });
      setTimeout(() => setMessage(null), 3000);
    } catch (error) {
      console.error('导出配置失败:', error);
      setMessage({ type: 'error', text: '导出配置失败' });
      setTimeout(() => setMessage(null), 3000);
    }
  }, [preferences, currentParameters]);

  // 导入配置
  const importConfiguration = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const content = e.target?.result as string;
          const importedData = JSON.parse(content);

          // 验证导入数据格式
          if (!importedData.preferences || !importedData.currentParameters) {
            throw new Error('无效的配置文件格式');
          }

          // 创建备份
          createBackup();

          // 应用导入的配置
          savePreferences(importedData.preferences);
          onParametersChange?.(importedData.currentParameters);

          setMessage({ type: 'success', text: '配置导入成功' });
          setTimeout(() => setMessage(null), 3000);
        } catch (error) {
          console.error('导入配置失败:', error);
          setMessage({ type: 'error', text: '导入配置失败：文件格式无效' });
          setTimeout(() => setMessage(null), 3000);
        }
      };

      reader.readAsText(file);

      // 清空文件输入
      event.target.value = '';
    },
    [savePreferences, onParametersChange],
  );

  // 创建备份
  const createBackup = useCallback(() => {
    try {
      const storage = getLocalStorage();
      const backup = {
        timestamp: new Date().toISOString(),
        preferences,
        currentParameters,
      };

      const backups = getBackupHistory();
      backups.push(backup);

      // 只保留最近10个备份
      if (backups.length > 10) {
        backups.splice(0, backups.length - 10);
      }

      storage.setItem(STORAGE_KEYS.PARAMETERS_BACKUP, JSON.stringify(backups));
    } catch (error) {
      console.error('创建备份失败:', error);
    }
  }, [preferences, currentParameters]);

  // 获取备份历史
  const getBackupHistory = useCallback(() => {
    try {
      const storage = getLocalStorage();
      const stored = storage.getItem(STORAGE_KEYS.PARAMETERS_BACKUP);
      const parsed = stored ? JSON.parse(stored) : [];
      // 确保返回的是数组
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  }, []);

  // 恢复备份
  const restoreBackup = useCallback(
    async (backup: any) => {
      if (
        window.confirm(
          `确定要恢复 ${new Date(backup.timestamp).toLocaleString()} 的备份配置吗？`,
        )
      ) {
        await savePreferences(backup.preferences);
        onParametersChange?.(backup.currentParameters);
        setMessage({
          type: 'success',
          text: `已恢复 ${new Date(backup.timestamp).toLocaleString()} 的备份配置`,
        });
        setTimeout(() => setMessage(null), 3000);
      }
    },
    [savePreferences, onParametersChange],
  );

  // 更新默认参数
  const updateDefaultParameters = useCallback(
    (field: keyof StrategyParameters, value: number) => {
      const updatedPreferences = {
        ...preferences,
        defaultParameters: {
          ...preferences.defaultParameters,
          [field]: value,
        },
      };
      savePreferences(updatedPreferences);
    },
    [preferences, savePreferences],
  );

  // 更新图表偏好
  const updateChartPreferences = useCallback(
    (field: keyof UserPreferencesType['chartPreferences'], value: any) => {
      const updatedPreferences = {
        ...preferences,
        chartPreferences: {
          ...preferences.chartPreferences,
          [field]: value,
        },
      };
      savePreferences(updatedPreferences);
    },
    [preferences, savePreferences],
  );

  // 组件挂载时加载偏好
  useEffect(() => {
    loadPreferences();
  }, [loadPreferences]);

  // 参数自动保存
  useEffect(() => {
    if (preferences.autoSave && !isLoading) {
      const timer = setTimeout(() => {
        const storage = getLocalStorage();
        storage.setItem(
          STORAGE_KEYS.LAST_USED,
          JSON.stringify(currentParameters),
        );
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [currentParameters, preferences.autoSave, isLoading]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* 消息提示 */}
      {message && (
        <div
          className={`flex items-center space-x-2 p-3 rounded-lg ${
            message.type === 'success'
              ? 'bg-green-50 text-green-700 border border-green-200'
              : 'bg-red-50 text-red-700 border border-red-200'
          }`}
        >
          {message.type === 'success' ? (
            <Check className="h-5 w-5" />
          ) : (
            <AlertCircle className="h-5 w-5" />
          )}
          <span className="text-sm font-medium">{message.text}</span>
        </div>
      )}

      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Settings className="h-5 w-5 text-gray-600" />
          <h3 className="text-lg font-semibold text-gray-900">用户偏好设置</h3>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={resetToDefaults}
            className="flex items-center space-x-1 px-3 py-1.5 text-sm border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
          >
            <RotateCcw className="h-4 w-4" />
            <span>重置默认</span>
          </button>
        </div>
      </div>

      <div className="space-y-6">
        {/* 默认参数设置 */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-md font-semibold text-gray-900 mb-4">
            默认参数设置
          </h4>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                默认均线周期:{' '}
                {preferences.defaultParameters.movingAveragePeriod}
              </label>
              <input
                type="range"
                min="5"
                max="200"
                value={preferences.defaultParameters.movingAveragePeriod}
                onChange={(e) =>
                  updateDefaultParameters(
                    'movingAveragePeriod',
                    Number(e.target.value),
                  )
                }
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                默认止损: {preferences.defaultParameters.stopLoss}%
              </label>
              <input
                type="number"
                min="0"
                max="50"
                step="0.1"
                value={preferences.defaultParameters.stopLoss}
                onChange={(e) =>
                  updateDefaultParameters('stopLoss', Number(e.target.value))
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                默认止盈: {preferences.defaultParameters.takeProfit}%
              </label>
              <input
                type="number"
                min="0"
                max="50"
                step="0.1"
                value={preferences.defaultParameters.takeProfit}
                onChange={(e) =>
                  updateDefaultParameters('takeProfit', Number(e.target.value))
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>

            <div className="flex items-end">
              <button
                onClick={() =>
                  onParametersChange?.(preferences.defaultParameters)
                }
                className="w-full px-3 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700"
              >
                应用默认参数
              </button>
            </div>
          </div>
        </div>

        {/* 图表偏好设置 */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-md font-semibold text-gray-900 mb-4">
            图表偏好设置
          </h4>

          <div className="space-y-3">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={preferences.chartPreferences.showGrid}
                onChange={(e) =>
                  updateChartPreferences('showGrid', e.target.checked)
                }
                className="rounded border-gray-300"
              />
              <span className="text-sm text-gray-700">显示图表网格</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={preferences.chartPreferences.showVolume}
                onChange={(e) =>
                  updateChartPreferences('showVolume', e.target.checked)
                }
                className="rounded border-gray-300"
              />
              <span className="text-sm text-gray-700">显示成交量</span>
            </label>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                动画持续时间: {preferences.chartPreferences.animationDuration}ms
              </label>
              <input
                type="range"
                min="0"
                max="1000"
                step="50"
                value={preferences.chartPreferences.animationDuration}
                onChange={(e) =>
                  updateChartPreferences(
                    'animationDuration',
                    Number(e.target.value),
                  )
                }
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
              />
            </div>
          </div>
        </div>

        {/* 其他偏好设置 */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-md font-semibold text-gray-900 mb-4">其他设置</h4>

          <div className="space-y-3">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={preferences.autoSave}
                onChange={(e) =>
                  savePreferences({
                    ...preferences,
                    autoSave: e.target.checked,
                  })
                }
                className="rounded border-gray-300"
              />
              <span className="text-sm text-gray-700">自动保存参数变更</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={preferences.showAdvanced}
                onChange={(e) =>
                  savePreferences({
                    ...preferences,
                    showAdvanced: e.target.checked,
                  })
                }
                className="rounded border-gray-300"
              />
              <span className="text-sm text-gray-700">显示高级选项</span>
            </label>
          </div>
        </div>

        {/* 配置管理 */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-md font-semibold text-gray-900 mb-4">配置管理</h4>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                导出配置
              </label>
              <button
                onClick={exportConfiguration}
                className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700"
              >
                <Download className="h-4 w-4" />
                <span>导出为JSON文件</span>
              </button>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                导入配置
              </label>
              <label className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 cursor-pointer">
                <Upload className="h-4 w-4" />
                <span>选择JSON文件</span>
                <input
                  type="file"
                  accept=".json"
                  onChange={importConfiguration}
                  className="hidden"
                />
              </label>
            </div>
          </div>

          {/* 备份历史 */}
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              备份历史
            </label>
            <div className="max-h-32 overflow-y-auto border border-gray-200 rounded-md">
              {(() => {
                const backups = getBackupHistory();
                return backups.length === 0 ? (
                  <div className="p-3 text-sm text-gray-500 text-center">
                    暂无备份
                  </div>
                ) : (
                  <div className="divide-y divide-gray-200">
                    {backups.map((backup: any, index: number) => (
                      <div
                        key={index}
                        className="flex items-center justify-between p-2 hover:bg-gray-100"
                      >
                        <span className="text-sm text-gray-700">
                          {new Date(backup.timestamp).toLocaleString()}
                        </span>
                        <button
                          onClick={() => restoreBackup(backup)}
                          className="text-sm text-blue-600 hover:text-blue-800"
                        >
                          恢复
                        </button>
                      </div>
                    ))}
                  </div>
                );
              })()}
            </div>
          </div>
        </div>

        {/* 保存按钮 */}
        <div className="flex justify-end">
          <button
            onClick={() => savePreferences(preferences)}
            disabled={isSaving}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            <span>{isSaving ? '保存中...' : '保存设置'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export { UserPreferences };
export default UserPreferences;
