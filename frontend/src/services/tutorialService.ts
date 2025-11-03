import { UseQueryOptions, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import React, { useCallback, useMemo, useRef } from 'react';
import {
  Tutorial,
  TutorialProgress,
  TutorialSession,
  TutorialContext,
  TutorialStep,
  Achievement,
  TutorialStats,
  TutorialProgressUpdate,
  TutorialUserPreferences,
  APIResponse,
  TutorialEvent
} from '@/types/tutorial.types';

// 本地存储键名
const STORAGE_KEYS = {
  TUTORIAL_PROGRESS: 'tutorial_progress',
  TUTORIAL_SESSION: 'tutorial_session',
  USER_PREFERENCES: 'tutorial_preferences',
  ACHIEVEMENTS: 'tutorial_achievements',
} as const;

// 查询键常量
export const TUTORIAL_QUERY_KEYS = {
  tutorials: ['tutorials'] as const,
  tutorial: (id: string) => ['tutorial', id] as const,
  progress: (tutorialId: string) => ['tutorialProgress', tutorialId] as const,
  stats: ['tutorialStats'] as const,
  session: (sessionId: string) => ['tutorialSession', sessionId] as const,
} as const;

// 数据缓存配置
const CACHE_CONFIG = {
  tutorials: {
    staleTime: 60 * 60 * 1000, // 1 hour - 教程内容很少变化
    gcTime: 24 * 60 * 60 * 1000, // 24 hours
  },
  progress: {
    staleTime: 5 * 1000, // 5 seconds - 进度需要实时更新
    gcTime: 30 * 60 * 1000, // 30 minutes
  },
  stats: {
    staleTime: 60 * 1000, // 1 minute
    gcTime: 10 * 60 * 1000, // 10 minutes
  },
};

// 默认用户偏好设置
const DEFAULT_PREFERENCES: TutorialUserPreferences = {
  animationSpeed: 1.0,
  autoProgress: false,
  showHints: true,
  soundEnabled: false,
  language: 'zh-CN',
};

/**
 * 教程进度管理类
 * 负责教程进度的跟踪、持久化和恢复
 */
export class TutorialProgressManager {
  private queryClient = useQueryClient();
  private eventListeners: Map<string, ((event: TutorialEvent) => void)[]> = new Map();

  /**
   * 获取教程进度
   */
  getProgress(tutorialId: string): TutorialProgress | null {
    try {
      const stored = localStorage.getItem(`${STORAGE_KEYS.TUTORIAL_PROGRESS}_${tutorialId}`);
      return stored ? JSON.parse(stored) : null;
    } catch (error) {
      console.error('Failed to get tutorial progress:', error);
      return null;
    }
  }

  /**
   * 保存教程进度
   */
  saveProgress(tutorialId: string, progress: TutorialProgress): void {
    try {
      localStorage.setItem(`${STORAGE_KEYS.TUTORIAL_PROGRESS}_${tutorialId}`, JSON.stringify(progress));
      this.queryClient.setQueryData(TUTORIAL_QUERY_KEYS.progress(tutorialId), progress);

      // 触发进度更新事件
      this.emitEvent({
        type: 'step_complete',
        data: { tutorialId, progress },
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      console.error('Failed to save tutorial progress:', error);
    }
  }

  /**
   * 创建新教程进度
   */
  createProgress(tutorialId: string, totalSteps: number): TutorialProgress {
    const now = new Date().toISOString();
    const progress: TutorialProgress = {
      currentStep: 0,
      completedSteps: [],
      totalSteps,
      startTime: now,
      lastAccessTime: now,
      totalTimeSpent: 0,
      achievements: [],
      bookmarks: [],
      skippedSteps: [],
    };

    this.saveProgress(tutorialId, progress);
    return progress;
  }

  /**
   * 更新步骤进度
   */
  updateStepProgress(tutorialId: string, stepIndex: number, action: TutorialProgressUpdate): TutorialProgress | null {
    const progress = this.getProgress(tutorialId);
    if (!progress) return null;

    const now = new Date().toISOString();
    let updated = false;

    switch (action.action) {
      case 'start':
        if (progress.currentStep === stepIndex) {
          progress.lastAccessTime = now;
          updated = true;
        }
        break;

      case 'complete':
        if (!progress.completedSteps.includes(stepIndex)) {
          progress.completedSteps.push(stepIndex);
          progress.totalTimeSpent += action.timeSpent || 0;
          progress.lastAccessTime = now;

          // 自动推进到下一步
          if (stepIndex === progress.currentStep && stepIndex < progress.totalSteps - 1) {
            progress.currentStep = stepIndex + 1;
          }
          updated = true;
        }
        break;

      case 'skip':
        if (!progress.skippedSteps.includes(stepIndex)) {
          progress.skippedSteps.push(stepIndex);
          progress.lastAccessTime = now;
          updated = true;
        }
        break;

      case 'bookmark':
        if (!progress.bookmarks.includes(stepIndex)) {
          progress.bookmarks.push(stepIndex);
          progress.lastAccessTime = now;
          updated = true;
        }
        break;
    }

    if (updated) {
      this.saveProgress(tutorialId, progress);
    }

    return progress;
  }

  /**
   * 添加事件监听器
   */
  addEventListener(eventType: string, listener: (event: TutorialEvent) => void): void {
    if (!this.eventListeners.has(eventType)) {
      this.eventListeners.set(eventType, []);
    }
    this.eventListeners.get(eventType)!.push(listener);
  }

  /**
   * 触发事件
   */
  private emitEvent(event: TutorialEvent): void {
    const listeners = this.eventListeners.get(event.type) || [];
    listeners.forEach(listener => {
      try {
        listener(event);
      } catch (error) {
        console.error('Error in event listener:', error);
      }
    });
  }
}

/**
 * 教程数据服务钩子
 */
export function useTutorialService() {
  const queryClient = useQueryClient();
  const progressManagerRef = useRef(new TutorialProgressManager());

  /**
   * 获取所有教程列表
   */
  const useTutorials = (options?: UseQueryOptions<Tutorial[], Error>) => {
    return useQuery({
      queryKey: TUTORIAL_QUERY_KEYS.tutorials,
      queryFn: async (): Promise<Tutorial[]> => {
        // 模拟API调用 - 实际实现中应该调用真实的API
        const mockTutorials: Tutorial[] = [
          {
            id: 'single-moving-average-basics',
            title: '单均线策略基础',
            description: '学习单均线策略的基本原理、金叉死叉信号和实战应用',
            category: '策略基础',
            difficulty: 'beginner',
            estimatedDuration: 15,
            steps: [
              {
                id: 'intro',
                title: '什么是单均线策略',
                content: '单均线策略是最基础的技术分析策略之一...',
                type: 'explanation',
                estimatedTime: 120,
              },
              {
                id: 'moving-average-calculation',
                title: '移动平均线计算',
                content: '学习如何计算简单移动平均线和指数移动平均线',
                type: 'animation',
                interactionType: 'animation',
                estimatedTime: 180,
              },
              {
                id: 'golden-cross',
                title: '金叉信号识别',
                content: '学习识别和验证金叉买入信号',
                type: 'animation',
                interactionType: 'chart',
                estimatedTime: 240,
              },
              {
                id: 'death-cross',
                title: '死叉信号识别',
                content: '学习识别和验证死叉卖出信号',
                type: 'animation',
                interactionType: 'chart',
                estimatedTime: 240,
              },
              {
                id: 'practice',
                title: '实战练习',
                content: '通过真实数据练习单均线策略的应用',
                type: 'interactive',
                interactionType: 'parameter',
                estimatedTime: 300,
              },
            ],
            tags: ['基础', '技术分析', '均线'],
          },
        ];

        return mockTutorials;
      },
      staleTime: CACHE_CONFIG.tutorials.staleTime,
      gcTime: CACHE_CONFIG.tutorials.gcTime,
      ...options,
    });
  };

  /**
   * 获取单个教程
   */
  const useTutorial = (tutorialId: string, options?: UseQueryOptions<Tutorial, Error>) => {
    return useQuery({
      queryKey: TUTORIAL_QUERY_KEYS.tutorial(tutorialId),
      queryFn: async (): Promise<Tutorial> => {
        // 模拟API调用
        const tutorials = await queryClient.fetchQuery({
          queryKey: TUTORIAL_QUERY_KEYS.tutorials,
          queryFn: () => [],
        });

        const tutorial = tutorials.find(t => t.id === tutorialId);
        if (!tutorial) {
          throw new Error(`Tutorial ${tutorialId} not found`);
        }

        return tutorial;
      },
      staleTime: CACHE_CONFIG.tutorials.staleTime,
      gcTime: CACHE_CONFIG.tutorials.gcTime,
      ...options,
    });
  };

  /**
   * 获取教程进度
   */
  const useTutorialProgress = (tutorialId: string, options?: UseQueryOptions<TutorialProgress | null, Error>) => {
    return useQuery({
      queryKey: TUTORIAL_QUERY_KEYS.progress(tutorialId),
      queryFn: (): TutorialProgress | null => {
        return progressManagerRef.current.getProgress(tutorialId);
      },
      staleTime: CACHE_CONFIG.progress.staleTime,
      gcTime: CACHE_CONFIG.progress.gcTime,
      ...options,
    });
  };

  /**
   * 更新教程进度的变更钩子
   */
  const useUpdateProgress = () => {
    return useMutation({
      mutationFn: async ({ tutorialId, stepIndex, action }: {
        tutorialId: string;
        stepIndex: number;
        action: TutorialProgressUpdate;
      }) => {
        const progressManager = progressManagerRef.current;
        return progressManager.updateStepProgress(tutorialId, stepIndex, action);
      },
      onSuccess: (updatedProgress, variables) => {
        // 更新缓存
        queryClient.setQueryData(
          TUTORIAL_QUERY_KEYS.progress(variables.tutorialId),
          updatedProgress
        );
      },
    });
  };

  /**
   * 获取用户偏好设置
   */
  const useUserPreferences = () => {
    return useMemo(() => {
      try {
        const stored = localStorage.getItem(STORAGE_KEYS.USER_PREFERENCES);
        return { ...DEFAULT_PREFERENCES, ...(stored ? JSON.parse(stored) : {}) };
      } catch (error) {
        console.error('Failed to load user preferences:', error);
        return DEFAULT_PREFERENCES;
      }
    }, []);
  };

  /**
   * 保存用户偏好设置
   */
  const saveUserPreferences = useCallback((preferences: Partial<TutorialUserPreferences>) => {
    try {
      const current = progressManagerRef.current.constructor === TutorialProgressManager
        ? DEFAULT_PREFERENCES
        : useUserPreferences();

      const updated = { ...current, ...preferences };
      localStorage.setItem(STORAGE_KEYS.USER_PREFERENCES, JSON.stringify(updated));
      return updated;
    } catch (error) {
      console.error('Failed to save user preferences:', error);
      return null;
    }
  }, []);

  /**
   * 获取教程统计信息
   */
  const useTutorialStats = (options?: UseQueryOptions<TutorialStats, Error>) => {
    return useQuery({
      queryKey: TUTORIAL_QUERY_KEYS.stats,
      queryFn: async (): Promise<TutorialStats> => {
        // 计算所有教程的统计信息
        const tutorials = await queryClient.fetchQuery({
          queryKey: TUTORIAL_QUERY_KEYS.tutorials,
          queryFn: () => [],
        });

        let totalTimeSpent = 0;
        let completedTutorials = 0;
        let achievementCount = 0;

        for (const tutorial of tutorials) {
          const progress = progressManagerRef.current.getProgress(tutorial.id);
          if (progress) {
            totalTimeSpent += progress.totalTimeSpent;
            achievementCount += progress.achievements.length;

            if (progress.completedSteps.length === tutorial.steps.length) {
              completedTutorials++;
            }
          }
        }

        return {
          totalTutorials: tutorials.length,
          completedTutorials,
          totalTimeSpent,
          averageCompletionTime: completedTutorials > 0 ? totalTimeSpent / completedTutorials : 0,
          achievementCount,
          currentStreak: 1, // 简化实现
        };
      },
      staleTime: CACHE_CONFIG.stats.staleTime,
      gcTime: CACHE_CONFIG.stats.gcTime,
      ...options,
    });
  };

  /**
   * 获取教程上下文（当前步骤信息）
   */
  const useTutorialContext = (tutorialId: string) => {
    const tutorial = useTutorial(tutorialId);
    const progress = useTutorialProgress(tutorialId);

    return useMemo(() => {
      if (!tutorial.data || !progress.data) {
        return null;
      }

      const currentStep = tutorial.data.steps[progress.data.currentStep];
      const previousStep = progress.data.currentStep > 0
        ? tutorial.data.steps[progress.data.currentStep - 1]
        : undefined;
      const nextStep = progress.data.currentStep < tutorial.data.steps.length - 1
        ? tutorial.data.steps[progress.data.currentStep + 1]
        : undefined;

      return {
        currentStep,
        progress: progress.data,
        tutorial: tutorial.data,
        previousStep,
        nextStep,
      } as TutorialContext;
    }, [tutorial.data, progress.data]);
  };

  return {
    useTutorials,
    useTutorial,
    useTutorialProgress,
    useUpdateProgress,
    useUserPreferences,
    saveUserPreferences,
    useTutorialStats,
    useTutorialContext,
    progressManager: progressManagerRef.current,
  };
}