/**
 * 教程系统类型定义
 * 基于Story 2.4交互式教程系统需求
 */

export interface TutorialStep {
  id: string;
  title: string;
  content: string;
  type: 'explanation' | 'animation' | 'interactive' | 'quiz';
  interactionType?: 'navigation' | 'animation' | 'parameter' | 'chart';
  completionConditions?: CompletionCondition[];
  resources?: TutorialResource[];
  estimatedTime?: number; // 预计完成时间（秒）
  isOptional?: boolean;
}

export interface CompletionCondition {
  type: 'time_spent' | 'action_completed' | 'button_clicked' | 'animation_watched' | 'quiz_passed';
  value: any;
  operator?: '>' | '<' | '=' | '>=' | '<=';
}

export interface TutorialResource {
  type: 'chart' | 'image' | 'video' | 'text' | 'parameter';
  content: any;
  label?: string;
}

export interface TutorialProgress {
  currentStep: number;
  completedSteps: number[];
  totalSteps: number;
  startTime: string;
  lastAccessTime: string;
  totalTimeSpent: number; // 总学习时间（秒）
  achievements: Achievement[];
  bookmarks: number[]; // 书签/断点位置
  skippedSteps: number[];
}

export interface Achievement {
  id: string;
  title: string;
  description: string;
  unlockedAt: string;
  icon?: string;
}

export interface TutorialSession {
  id: string;
  tutorialId: string;
  progress: TutorialProgress;
  isActive: boolean;
  deviceInfo?: string;
}

export interface Tutorial {
  id: string;
  title: string;
  description: string;
  category: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  estimatedDuration: number; // 预计总时长（分钟）
  steps: TutorialStep[];
  prerequisites?: string[]; // 前置教程ID
  tags?: string[];
}

export interface TutorialContext {
  currentStep: TutorialStep;
  progress: TutorialProgress;
  tutorial: Tutorial;
  previousStep?: TutorialStep;
  nextStep?: TutorialStep;
}

export interface TutorialTooltip {
  id: string;
  content: string;
  context: string; // 上下文标识
  position: 'top' | 'bottom' | 'left' | 'right';
  trigger: 'hover' | 'click' | 'focus';
  delay?: number;
}

export interface TutorialSearchResult {
  tutorial: Tutorial;
  step?: TutorialStep;
  relevanceScore: number;
  matchedContent: string;
}

export interface TutorialStats {
  totalTutorials: number;
  completedTutorials: number;
  totalTimeSpent: number;
  averageCompletionTime: number;
  achievementCount: number;
  currentStreak: number; // 连续学习天数
}

// API相关类型
export interface APIResponse<T = any> {
  success?: boolean;
  data?: T;
  message?: string;
  task_id?: string;
}

export interface TutorialProgressUpdate {
  stepId: string;
  action: 'start' | 'complete' | 'skip' | 'bookmark';
  timestamp: string;
  timeSpent?: number;
}

export interface TutorialUserPreferences {
  animationSpeed: number; // 0.5 - 2.0
  autoProgress: boolean;
  showHints: boolean;
  soundEnabled: boolean;
  language: string;
}

// 事件类型
export interface TutorialEvent {
  type: 'step_start' | 'step_complete' | 'tutorial_complete' | 'achievement_unlock' | 'bookmark_add' | 'skip_step';
  data: any;
  timestamp: string;
}

// 教程内容类型
export interface TutorialContent {
  id: string;
  type: 'text' | 'chart' | 'animation' | 'quiz' | 'interactive';
  title: string;
  data: any;
  metadata?: Record<string, any>;
}