import React, { createContext, useContext, useReducer, useEffect, useCallback } from 'react';
import { TutorialProgress, Tutorial, Achievement, TutorialUserPreferences } from '@/types/tutorial.types';

/**
 * 教程持久化上下文
 * 提供进度保存、恢复、同步等功能
 */

interface TutorialPersistenceState {
  progress: Record<string, TutorialProgress>;
  achievements: Achievement[];
  userPreferences: TutorialUserPreferences;
  lastSyncTime: string | null;
  isOnline: boolean;
  syncStatus: 'idle' | 'syncing' | 'success' | 'error';
}

type TutorialPersistenceAction =
  | { type: 'LOAD_PROGRESS'; payload: Record<string, TutorialProgress> }
  | { type: 'SAVE_PROGRESS'; payload: { tutorialId: string; progress: TutorialProgress } }
  | { type: 'LOAD_ACHIEVEMENTS'; payload: Achievement[] }
  | { type: 'ADD_ACHIEVEMENT'; payload: Achievement }
  | { type: 'UPDATE_PREFERENCES'; payload: TutorialUserPreferences }
  | { type: 'SET_ONLINE_STATUS'; payload: boolean }
  | { type: 'SET_SYNC_STATUS'; payload: 'idle' | 'syncing' | 'success' | 'error' }
  | { type: 'SYNC_SUCCESS'; payload: { lastSyncTime: string } };

const initialState: TutorialPersistenceState = {
  progress: {},
  achievements: [],
  userPreferences: {
    animationSpeed: 1.0,
    autoProgress: false,
    showHints: true,
    soundEnabled: false,
    language: 'zh-CN',
  },
  lastSyncTime: null,
  isOnline: navigator.onLine,
  syncStatus: 'idle',
};

function tutorialPersistenceReducer(
  state: TutorialPersistenceState,
  action: TutorialPersistenceAction
): TutorialPersistenceState {
  switch (action.type) {
    case 'LOAD_PROGRESS':
      return {
        ...state,
        progress: action.payload,
      };

    case 'SAVE_PROGRESS':
      return {
        ...state,
        progress: {
          ...state.progress,
          [action.payload.tutorialId]: action.payload.progress,
        },
      };

    case 'LOAD_ACHIEVEMENTS':
      return {
        ...state,
        achievements: action.payload,
      };

    case 'ADD_ACHIEVEMENT':
      return {
        ...state,
        achievements: [...state.achievements, action.payload],
      };

    case 'UPDATE_PREFERENCES':
      return {
        ...state,
        userPreferences: action.payload,
      };

    case 'SET_ONLINE_STATUS':
      return {
        ...state,
        isOnline: action.payload,
      };

    case 'SET_SYNC_STATUS':
      return {
        ...state,
        syncStatus: action.payload,
      };

    case 'SYNC_SUCCESS':
      return {
        ...state,
        lastSyncTime: action.payload.lastSyncTime,
        syncStatus: 'success',
      };

    default:
      return state;
  }
}

// 本地存储键名
const STORAGE_KEYS = {
  PROGRESS: 'tutorial_progress_v2',
  ACHIEVEMENTS: 'tutorial_achievements_v2',
  PREFERENCES: 'tutorial_preferences_v2',
  SYNC_TIME: 'tutorial_last_sync_v2',
} as const;

/**
 * 教程持久化上下文
 */
const TutorialPersistenceContext = createContext<{
  state: TutorialPersistenceState;
  saveProgress: (tutorialId: string, progress: TutorialProgress) => void;
  loadProgress: (tutorialId: string) => TutorialProgress | null;
  saveAchievements: (achievements: Achievement[]) => void;
  addAchievement: (achievement: Achievement) => void;
  savePreferences: (preferences: TutorialUserPreferences) => void;
  exportData: () => string;
  importData: (data: string) => boolean;
  clearAllData: () => void;
  syncWithServer: () => Promise<void>;
} | null>(null);

/**
 * 教程持久化提供者组件
 */
export function TutorialPersistenceProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(tutorialPersistenceReducer, initialState);

  // 从本地存储加载数据
  useEffect(() => {
    try {
      // 加载进度数据
      const progressData = localStorage.getItem(STORAGE_KEYS.PROGRESS);
      if (progressData) {
        const progress = JSON.parse(progressData);
        dispatch({ type: 'LOAD_PROGRESS', payload: progress });
      }

      // 加载成就数据
      const achievementsData = localStorage.getItem(STORAGE_KEYS.ACHIEVEMENTS);
      if (achievementsData) {
        const achievements = JSON.parse(achievementsData);
        dispatch({ type: 'LOAD_ACHIEVEMENTS', payload: achievements });
      }

      // 加载用户偏好
      const preferencesData = localStorage.getItem(STORAGE_KEYS.PREFERENCES);
      if (preferencesData) {
        const preferences = JSON.parse(preferencesData);
        dispatch({ type: 'UPDATE_PREFERENCES', payload: preferences });
      }

      // 加载最后同步时间
      const syncTimeData = localStorage.getItem(STORAGE_KEYS.SYNC_TIME);
      if (syncTimeData) {
        dispatch({ type: 'SYNC_SUCCESS', payload: { lastSyncTime: syncTimeData } });
      }
    } catch (error) {
      console.error('Failed to load tutorial data from localStorage:', error);
    }
  }, []);

  // 监听在线状态
  useEffect(() => {
    const handleOnline = () => dispatch({ type: 'SET_ONLINE_STATUS', payload: true });
    const handleOffline = () => dispatch({ type: 'SET_ONLINE_STATUS', payload: false });

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // 保存进度到本地存储
  const saveProgress = useCallback((tutorialId: string, progress: TutorialProgress) => {
    try {
      const updatedProgress = { ...state.progress, [tutorialId]: progress };
      localStorage.setItem(STORAGE_KEYS.PROGRESS, JSON.stringify(updatedProgress));
      dispatch({ type: 'SAVE_PROGRESS', payload: { tutorialId, progress } });

      // 如果在线，尝试同步到服务器
      if (state.isOnline) {
        syncWithServer();
      }
    } catch (error) {
      console.error('Failed to save tutorial progress:', error);
    }
  }, [state.progress, state.isOnline]);

  // 加载单个教程进度
  const loadProgress = useCallback((tutorialId: string): TutorialProgress | null => {
    return state.progress[tutorialId] || null;
  }, [state.progress]);

  // 保存成就数据
  const saveAchievements = useCallback((achievements: Achievement[]) => {
    try {
      localStorage.setItem(STORAGE_KEYS.ACHIEVEMENTS, JSON.stringify(achievements));
      dispatch({ type: 'LOAD_ACHIEVEMENTS', payload: achievements });
    } catch (error) {
      console.error('Failed to save achievements:', error);
    }
  }, []);

  // 添加新成就
  const addAchievement = useCallback((achievement: Achievement) => {
    const exists = state.achievements.some(a => a.id === achievement.id);
    if (!exists) {
      const updatedAchievements = [...state.achievements, achievement];
      saveAchievements(updatedAchievements);
      dispatch({ type: 'ADD_ACHIEVEMENT', payload: achievement });
    }
  }, [state.achievements, saveAchievements]);

  // 保存用户偏好
  const savePreferences = useCallback((preferences: TutorialUserPreferences) => {
    try {
      localStorage.setItem(STORAGE_KEYS.PREFERENCES, JSON.stringify(preferences));
      dispatch({ type: 'UPDATE_PREFERENCES', payload: preferences });
    } catch (error) {
      console.error('Failed to save user preferences:', error);
    }
  }, []);

  // 导出数据
  const exportData = useCallback((): string => {
    const exportData = {
      progress: state.progress,
      achievements: state.achievements,
      userPreferences: state.userPreferences,
      exportTime: new Date().toISOString(),
      version: '2.0',
    };

    return JSON.stringify(exportData, null, 2);
  }, [state]);

  // 导入数据
  const importData = useCallback((data: string): boolean => {
    try {
      const importedData = JSON.parse(data);

      // 验证数据格式
      if (!importedData.version || !importedData.progress) {
        throw new Error('Invalid data format');
      }

      // 导入进度数据
      if (importedData.progress) {
        localStorage.setItem(STORAGE_KEYS.PROGRESS, JSON.stringify(importedData.progress));
        dispatch({ type: 'LOAD_PROGRESS', payload: importedData.progress });
      }

      // 导入成就数据
      if (importedData.achievements) {
        localStorage.setItem(STORAGE_KEYS.ACHIEVEMENTS, JSON.stringify(importedData.achievements));
        dispatch({ type: 'LOAD_ACHIEVEMENTS', payload: importedData.achievements });
      }

      // 导入用户偏好
      if (importedData.userPreferences) {
        localStorage.setItem(STORAGE_KEYS.PREFERENCES, JSON.stringify(importedData.userPreferences));
        dispatch({ type: 'UPDATE_PREFERENCES', payload: importedData.userPreferences });
      }

      return true;
    } catch (error) {
      console.error('Failed to import tutorial data:', error);
      return false;
    }
  }, []);

  // 清除所有数据
  const clearAllData = useCallback(() => {
    try {
      Object.values(STORAGE_KEYS).forEach(key => {
        localStorage.removeItem(key);
      });

      dispatch({ type: 'LOAD_PROGRESS', payload: {} });
      dispatch({ type: 'LOAD_ACHIEVEMENTS', payload: [] });
      dispatch({
        type: 'UPDATE_PREFERENCES',
        payload: {
          animationSpeed: 1.0,
          autoProgress: false,
          showHints: true,
          soundEnabled: false,
          language: 'zh-CN',
        },
      });
      dispatch({ type: 'SYNC_SUCCESS', payload: { lastSyncTime: null } });
    } catch (error) {
      console.error('Failed to clear tutorial data:', error);
    }
  }, []);

  // 与服务器同步
  const syncWithServer = useCallback(async (): Promise<void> => {
    if (!state.isOnline) {
      return;
    }

    dispatch({ type: 'SET_SYNC_STATUS', payload: 'syncing' });

    try {
      // 模拟服务器同步
      // 在实际实现中，这里应该调用真实的API
      await new Promise(resolve => setTimeout(resolve, 1000));

      const syncTime = new Date().toISOString();
      localStorage.setItem(STORAGE_KEYS.SYNC_TIME, syncTime);
      dispatch({ type: 'SYNC_SUCCESS', payload: { lastSyncTime: syncTime } });

      // 3秒后重置同步状态
      setTimeout(() => {
        dispatch({ type: 'SET_SYNC_STATUS', payload: 'idle' });
      }, 3000);
    } catch (error) {
      console.error('Failed to sync with server:', error);
      dispatch({ type: 'SET_SYNC_STATUS', payload: 'error' });
    }
  }, [state.isOnline]);

  const contextValue = {
    state,
    saveProgress,
    loadProgress,
    saveAchievements,
    addAchievement,
    savePreferences,
    exportData,
    importData,
    clearAllData,
    syncWithServer,
  };

  return (
    <TutorialPersistenceContext.Provider value={contextValue}>
      {children}
    </TutorialPersistenceContext.Provider>
  );
}

/**
 * 使用教程持久化上下文的钩子
 */
export function useTutorialPersistence() {
  const context = useContext(TutorialPersistenceContext);
  if (!context) {
    throw new Error('useTutorialPersistence must be used within TutorialPersistenceProvider');
  }
  return context;
}

/**
 * 进度恢复组件
 * 在应用启动时自动恢复中断的教程
 */
export function TutorialProgressRestorer({
  tutorialId,
  onRestore,
}: {
  tutorialId: string;
  onRestore: (progress: TutorialProgress | null) => void;
}) {
  const { loadProgress } = useTutorialPersistence();

  useEffect(() => {
    const progress = loadProgress(tutorialId);
    onRestore(progress);
  }, [tutorialId, loadProgress, onRestore]);

  return null;
}

/**
 * 自动保存组件
 * 定期保存教程进度
 */
export function TutorialAutoSaver({
  tutorialId,
  progress,
  interval = 30000, // 30秒
}: {
  tutorialId: string;
  progress: TutorialProgress | null;
  interval?: number;
}) {
  const { saveProgress } = useTutorialPersistence();

  useEffect(() => {
    if (!progress) return;

    const saveInterval = setInterval(() => {
      saveProgress(tutorialId, progress);
    }, interval);

    return () => clearInterval(saveInterval);
  }, [tutorialId, progress, interval, saveProgress]);

  return null;
}