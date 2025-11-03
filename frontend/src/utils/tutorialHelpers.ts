import {
  Tutorial,
  TutorialStep,
  TutorialProgress,
  TutorialContext,
  CompletionCondition,
  Achievement,
  TutorialEvent,
} from '@/types/tutorial.types';

/**
 * 教程辅助函数集合
 * 提供教程系统常用的工具函数和逻辑处理
 */

/**
 * 检查步骤完成条件是否满足
 */
export function checkCompletionConditions(
  conditions: CompletionCondition[],
  context: {
    timeSpent: number;
    actionsCompleted: string[];
    animationWatched: boolean;
    quizPassed: boolean;
  }
): boolean {
  if (!conditions || conditions.length === 0) {
    return true; // 无条件时默认完成
  }

  return conditions.every(condition => {
    const { type, value, operator = '=' } = condition;

    switch (type) {
      case 'time_spent':
        return compareNumbers(context.timeSpent, value as number, operator);

      case 'action_completed':
        return context.actionsCompleted.includes(value as string);

      case 'animation_watched':
        return context.animationWatched === (value as boolean);

      case 'quiz_passed':
        return context.quizPassed === (value as boolean);

      default:
        return false;
    }
  });
}

/**
 * 数字比较辅助函数
 */
function compareNumbers(actual: number, expected: number, operator: string): boolean {
  switch (operator) {
    case '>': return actual > expected;
    case '<': return actual < expected;
    case '>=': return actual >= expected;
    case '<=': return actual <= expected;
    case '=': return actual === expected;
    default: return false;
  }
}

/**
 * 计算教程完成百分比
 */
export function calculateCompletionPercentage(progress: TutorialProgress): number {
  if (progress.totalSteps === 0) return 0;
  return Math.round((progress.completedSteps.length / progress.totalSteps) * 100);
}

/**
 * 计算预计剩余时间（秒）
 */
export function calculateEstimatedTimeRemaining(
  tutorial: Tutorial,
  progress: TutorialProgress
): number {
  const remainingSteps = tutorial.steps.filter(
    (_, index) => !progress.completedSteps.includes(index)
  );

  return remainingSteps.reduce((total, step) => {
    return total + (step.estimatedTime || 60); // 默认60秒每步
  }, 0);
}

/**
 * 格式化时间显示
 */
export function formatTime(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (hours > 0) {
    return `${hours}小时${minutes}分钟`;
  } else if (minutes > 0) {
    return `${minutes}分钟${secs}秒`;
  } else {
    return `${secs}秒`;
  }
}

/**
 * 生成成就徽章
 */
export function generateAchievement(
  type: 'first_step' | 'complete_tutorial' | 'speed_learner' | 'explorer',
  tutorialTitle: string,
  data?: any
): Achievement {
  const now = new Date().toISOString();

  switch (type) {
    case 'first_step':
      return {
        id: `first_step_${tutorialTitle}`,
        title: '初学者',
        description: `完成了《${tutorialTitle}》的第一步`,
        unlockedAt: now,
        icon: '🎯',
      };

    case 'complete_tutorial':
      return {
        id: `complete_${tutorialTitle}`,
        title: '教程完成者',
        description: `成功完成了《${tutorialTitle}》教程`,
        unlockedAt: now,
        icon: '🎉',
      };

    case 'speed_learner':
      return {
        id: `speed_${tutorialTitle}`,
        title: '快速学习者',
        description: `快速完成了《${tutorialTitle}》教程`,
        unlockedAt: now,
        icon: '⚡',
      };

    case 'explorer':
      return {
        id: `explorer_${tutorialTitle}`,
        title: '探索者',
        description: `探索了《${tutorialTitle}》的所有功能`,
        unlockedAt: now,
        icon: '🔍',
      };

    default:
      return {
        id: `unknown_${tutorialTitle}`,
        title: '神秘成就',
        description: '获得了神秘成就',
        unlockedAt: now,
        icon: '❓',
      };
  }
}

/**
 * 验证步骤跳转是否允许
 */
export function canSkipStep(step: TutorialStep, progress: TutorialProgress): boolean {
  // 必需步骤不能跳过
  if (!step.isOptional) {
    return false;
  }

  // 已完成的步骤不需要跳过
  if (progress.completedSteps.includes(parseInt(step.id))) {
    return false;
  }

  return true;
}

/**
 * 获取步骤导航信息
 */
export function getStepNavigation(context: TutorialContext) {
  const { currentStep, progress, tutorial } = context;
  const currentIndex = tutorial.steps.findIndex(step => step.id === currentStep.id);

  return {
    currentIndex,
    isFirstStep: currentIndex === 0,
    isLastStep: currentIndex === tutorial.steps.length - 1,
    canGoBack: currentIndex > 0,
    canGoForward: currentIndex < tutorial.steps.length - 1,
    totalSteps: tutorial.steps.length,
    completedSteps: progress.completedSteps.length,
  };
}

/**
 * 生成教程进度摘要
 */
export function generateProgressSummary(progress: TutorialProgress, tutorial: Tutorial): {
  status: 'not_started' | 'in_progress' | 'completed';
  percentage: number;
  timeSpent: string;
  estimatedRemaining: string;
  nextStep?: TutorialStep;
} {
  const percentage = calculateCompletionPercentage(progress);
  const timeSpent = formatTime(progress.totalTimeSpent);
  const estimatedRemaining = formatTime(calculateEstimatedTimeRemaining(tutorial, progress));

  let status: 'not_started' | 'in_progress' | 'completed';
  if (percentage === 0) {
    status = 'not_started';
  } else if (percentage === 100) {
    status = 'completed';
  } else {
    status = 'in_progress';
  }

  const nextStep = status === 'in_progress' && progress.currentStep < tutorial.steps.length
    ? tutorial.steps[progress.currentStep]
    : undefined;

  return {
    status,
    percentage,
    timeSpent,
    estimatedRemaining,
    nextStep,
  };
}

/**
 * 解析教程内容中的变量
 */
export function parseTutorialContent(content: string, variables: Record<string, any> = {}): string {
  return content.replace(/\{\{(\w+)\}\}/g, (match, key) => {
    return variables[key] || match;
  });
}

/**
 * 验证教程数据完整性
 */
export function validateTutorial(tutorial: Tutorial): {
  isValid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  if (!tutorial.id) {
    errors.push('教程ID不能为空');
  }

  if (!tutorial.title) {
    errors.push('教程标题不能为空');
  }

  if (!tutorial.steps || tutorial.steps.length === 0) {
    errors.push('教程必须包含至少一个步骤');
  } else {
    tutorial.steps.forEach((step, index) => {
      if (!step.id) {
        errors.push(`步骤${index + 1}的ID不能为空`);
      }
      if (!step.title) {
        errors.push(`步骤${index + 1}的标题不能为空`);
      }
      if (!step.content) {
        errors.push(`步骤${index + 1}的内容不能为空`);
      }
    });
  }

  if (tutorial.estimatedDuration <= 0) {
    errors.push('预计时长必须大于0');
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

/**
 * 生成教程事件
 */
export function createTutorialEvent(
  type: TutorialEvent['type'],
  data: any,
  tutorialId?: string
): TutorialEvent {
  return {
    type,
    data: tutorialId ? { ...data, tutorialId } : data,
    timestamp: new Date().toISOString(),
  };
}

/**
 * 计算学习统计
 */
export function calculateLearningStats(
  allProgress: TutorialProgress[],
  tutorials: Tutorial[]
): {
  totalTutorials: number;
  completedTutorials: number;
  averageCompletionRate: number;
  totalTimeSpent: number;
  mostStudiedCategory: string;
  achievements: number;
} {
  const completedTutorials = allProgress.filter(
    progress => progress.completedSteps.length >= tutorials.find(t => t.steps.length === progress.totalSteps)?.steps.length
  ).length;

  const totalCompletionRate = allProgress.reduce((sum, progress, index) => {
    const tutorial = tutorials[index];
    const rate = tutorial ? (progress.completedSteps.length / tutorial.steps.length) * 100 : 0;
    return sum + rate;
  }, 0);

  const averageCompletionRate = allProgress.length > 0 ? totalCompletionRate / allProgress.length : 0;

  const totalTimeSpent = allProgress.reduce((sum, progress) => sum + progress.totalTimeSpent, 0);

  const achievements = allProgress.reduce((sum, progress) => sum + progress.achievements.length, 0);

  // 简化统计：假设所有教程都是同一个类别
  const mostStudiedCategory = '量化交易策略';

  return {
    totalTutorials: tutorials.length,
    completedTutorials,
    averageCompletionRate: Math.round(averageCompletionRate),
    totalTimeSpent,
    mostStudiedCategory,
    achievements,
  };
}