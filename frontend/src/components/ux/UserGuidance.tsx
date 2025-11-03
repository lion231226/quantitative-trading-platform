'use client';

import React, { memo, useMemo, useCallback, useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import { UserGuide, UserGuideStep, UserProgress, Achievement } from '@/types/ux.types';

// 用户引导步骤组件
interface GuideStepProps {
  step: UserGuideStep;
  isActive: boolean;
  isCompleted: boolean;
  onNext: () => void;
  onPrevious: () => void;
  onSkip: () => void;
  onComplete: () => void;
  currentIndex: number;
  totalSteps: number;
}

export const GuideStep = memo<GuideStepProps>(({
  step,
  isActive,
  isCompleted,
  onNext,
  onPrevious,
  onSkip,
  onComplete,
  currentIndex,
  totalSteps,
}) => {
  const [actionCompleted, setActionCompleted] = useState(false);

  const handleAction = useCallback(() => {
    if (step.actionTarget) {
      const targetElement = document.querySelector(step.actionTarget);
      if (targetElement) {
        targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' });

        // 高亮目标元素
        targetElement.classList.add('guide-highlight');
        setTimeout(() => {
          targetElement.classList.remove('guide-highlight');
        }, 2000);

        // 模拟点击或其他操作
        if (step.actionType === 'click') {
          (targetElement as HTMLElement).click();
        }
      }
    }
    setActionCompleted(true);
  }, [step]);

  const renderPosition = () => {
    if (!step.targetSelector) return {};

    const targetElement = document.querySelector(step.targetSelector) as HTMLElement;
    if (!targetElement) return {};

    const rect = targetElement.getBoundingClientRect();
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;

    let position: React.CSSProperties = {};

    switch (step.position) {
      case 'top':
        position = {
          top: `${rect.top + scrollTop - 120}px`,
          left: `${rect.left + scrollLeft + rect.width / 2}px`,
          transform: 'translateX(-50%)',
        };
        break;
      case 'bottom':
        position = {
          top: `${rect.bottom + scrollTop + 20}px`,
          left: `${rect.left + scrollLeft + rect.width / 2}px`,
          transform: 'translateX(-50%)',
        };
        break;
      case 'left':
        position = {
          top: `${rect.top + scrollTop + rect.height / 2}px`,
          left: `${rect.left + scrollLeft - 20}px`,
          transform: 'translateY(-50%) translateX(-100%)',
        };
        break;
      case 'right':
        position = {
          top: `${rect.top + scrollTop + rect.height / 2}px`,
          left: `${rect.right + scrollLeft + 20}px`,
          transform: 'translateY(-50%)',
        };
        break;
      case 'center':
        position = {
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
        };
        break;
    }

    return position;
  };

  if (!isActive) return null;

  const position = renderPosition();

  return (
    <>
      {/* 背景遮罩 */}
      <div className="fixed inset-0 bg-black bg-opacity-50 z-40" />

      {/* 引导内容 */}
      <div
        className={cn(
          'fixed z-50 max-w-sm bg-white rounded-lg shadow-xl border border-gray-200',
          'animate-in fade-in-0 zoom-in-95 duration-200'
        )}
        style={position}
      >
        <Card className="p-6">
          {/* 进度指示器 */}
          <div className="flex justify-between items-center mb-4">
            <span className="text-sm text-gray-500">
              步骤 {currentIndex + 1} / {totalSteps}
            </span>
            <Progress value={((currentIndex + 1) / totalSteps) * 100} className="w-20" />
          </div>

          {/* 标题 */}
          <h3 className="text-lg font-semibold mb-3">{step.title}</h3>

          {/* 内容 */}
          <div className="text-gray-700 mb-4">
            {step.content}
          </div>

          {/* 图片或视频 */}
          {step.imageUrl && (
            <div className="mb-4">
              <img
                src={step.imageUrl}
                alt={step.title}
                className="w-full rounded-lg"
              />
            </div>
          )}

          {step.videoUrl && (
            <div className="mb-4">
              <video
                src={step.videoUrl}
                controls
                className="w-full rounded-lg"
              />
            </div>
          )}

          {/* 操作按钮 */}
          {step.actionRequired && !actionCompleted && (
            <div className="mb-4">
              <Button onClick={handleAction} className="w-full">
                {step.actionType === 'click' ? '点击目标元素' : '完成操作'}
              </Button>
            </div>
          )}

          {/* 导航按钮 */}
          <div className="flex justify-between items-center">
            <div>
              {currentIndex > 0 && (
                <Button variant="outline" onClick={onPrevious}>
                  上一步
                </Button>
              )}
            </div>

            <div className="flex gap-2">
              {step.skipAllowed && (
                <Button variant="ghost" onClick={onSkip}>
                  跳过
                </Button>
              )}

              {currentIndex === totalSteps - 1 ? (
                <Button onClick={onComplete}>
                  完成
                </Button>
              ) : (
                <Button
                  onClick={onNext}
                  disabled={step.actionRequired && !actionCompleted}
                >
                  下一步
                </Button>
              )}
            </div>
          </div>
        </Card>
      </div>

      {/* 高亮样式 */}
      <style jsx>{`
        .guide-highlight {
          box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.5);
          border-radius: 4px;
          transition: box-shadow 0.3s ease;
        }
      `}</style>
    </>
  );
});

GuideStep.displayName = 'GuideStep';

// 用户引导管理器
interface UserGuideManagerProps {
  guide: UserGuide;
  onStart?: () => void;
  onComplete?: () => void;
  onSkip?: () => void;
  onStepChange?: (stepIndex: number) => void;
}

export const UserGuideManager = memo<UserGuideManagerProps>(({
  guide,
  onStart,
  onComplete,
  onSkip,
  onStepChange,
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isActive, setIsActive] = useState(false);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());

  // 检查触发条件
  const checkTriggerConditions = useCallback(() => {
    const conditions = guide.triggerConditions;

    // 检查页面路径
    if (conditions.pagePath && window.location.pathname !== conditions.pagePath) {
      return false;
    }

    // 检查用户角色（如果有用户信息）
    if (conditions.userRole && !checkUserRole(conditions.userRole)) {
      return false;
    }

    // 检查页面停留时间
    if (conditions.timeOnPage) {
      const timeOnPage = performance.now() - performance.timing.navigationStart;
      if (timeOnPage < conditions.timeOnPage * 1000) {
        setTimeout(() => checkTriggerConditions(), 1000);
        return false;
      }
    }

    return true;
  }, [guide.triggerConditions]);

  // 检查用户角色（简化实现）
  const checkUserRole = (requiredRole: string): boolean => {
    // 实际实现中应该从用户状态获取角色信息
    return true;
  };

  // 自动开始引导
  useEffect(() => {
    if (guide.autoStart && checkTriggerConditions()) {
      setIsActive(true);
      onStart?.();
    }
  }, [guide.autoStart, checkTriggerConditions, onStart]);

  const handleStart = useCallback(() => {
    setIsActive(true);
    setCurrentStep(0);
    onStart?.();
  }, [onStart]);

  const handleNext = useCallback(() => {
    if (currentStep < guide.steps.length - 1) {
      const nextStep = currentStep + 1;
      setCurrentStep(nextStep);
      setCompletedSteps(prev => new Set(prev).add(currentStep));
      onStepChange?.(nextStep);
    } else {
      handleComplete();
    }
  }, [currentStep, guide.steps.length, onStepChange]);

  const handlePrevious = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
      onStepChange?.(currentStep - 1);
    }
  }, [currentStep, onStepChange]);

  const handleSkip = useCallback(() => {
    setIsActive(false);
    onSkip?.();
  }, [onSkip]);

  const handleComplete = useCallback(() => {
    setIsActive(false);
    setCompletedSteps(prev => new Set(prev).add(currentStep));
    onComplete?.();
  }, [currentStep, onComplete]);

  const currentStepData = guide.steps[currentStep];

  if (!isActive || !currentStepData) return null;

  return (
    <GuideStep
      step={currentStepData}
      isActive={isActive}
      isCompleted={completedSteps.has(currentStep)}
      onNext={handleNext}
      onPrevious={handlePrevious}
      onSkip={handleSkip}
      onComplete={handleComplete}
      currentIndex={currentStep}
      totalSteps={guide.steps.length}
    />
  );
});

UserGuideManager.displayName = 'UserGuideManager';

// 用户进度跟踪组件
interface UserProgressTrackerProps {
  userId?: string;
  guideId: string;
  onProgressUpdate?: (progress: UserProgress) => void;
}

export function UserProgressTracker({
  userId,
  guideId,
  onProgressUpdate,
}: UserProgressTrackerProps) {
  const [progress, setProgress] = useState<UserProgress | null>(null);

  // 开始新的进度跟踪
  const startProgress = useCallback(() => {
    const newProgress: UserProgress = {
      id: `progress_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      userId,
      guideId,
      currentStep: 0,
      completedSteps: [],
      startTime: new Date().toISOString(),
      lastActivityTime: new Date().toISOString(),
      status: 'in_progress',
      timeSpent: 0,
      interactions: [],
    };

    setProgress(newProgress);
    onProgressUpdate?.(newProgress);
  }, [userId, guideId, onProgressUpdate]);

  // 更新进度
  const updateProgress = useCallback((stepIndex: number, action: 'start' | 'complete' | 'skip' | 'back' | 'forward' | 'close') => {
    if (!progress) return;

    const updatedProgress: UserProgress = {
      ...progress,
      currentStep: stepIndex,
      lastActivityTime: new Date().toISOString(),
      timeSpent: progress.timeSpent + 1, // 简化计算
      interactions: [
        ...progress.interactions,
        {
          id: `interaction_${Date.now()}`,
          stepId: `${guideId}_step_${stepIndex}`,
          action,
          timestamp: new Date().toISOString(),
        },
      ],
    };

    if (action === 'complete' && !updatedProgress.completedSteps.includes(`${guideId}_step_${stepIndex}`)) {
      updatedProgress.completedSteps.push(`${guideId}_step_${stepIndex}`);
    }

    if (action === 'complete' && stepIndex === updatedProgress.completedSteps.length - 1) {
      updatedProgress.status = 'completed';
      updatedProgress.completedTime = new Date().toISOString();
    }

    setProgress(updatedProgress);
    onProgressUpdate?.(updatedProgress);
  }, [progress, guideId, onProgressUpdate]);

  // 完成进度
  const completeProgress = useCallback(() => {
    if (!progress) return;

    const completedProgress: UserProgress = {
      ...progress,
      status: 'completed',
      completedTime: new Date().toISOString(),
    };

    setProgress(completedProgress);
    onProgressUpdate?.(completedProgress);
  }, [progress, onProgressUpdate]);

  return {
    progress,
    startProgress,
    updateProgress,
    completeProgress,
  };
}

// 成就系统组件
interface AchievementProps {
  achievement: Achievement;
  isUnlocked: boolean;
  progress?: number; // 0-100
  onClick?: () => void;
}

export const Achievement = memo<AchievementProps>(({
  achievement,
  isUnlocked,
  progress = 0,
  onClick,
}) => {
  return (
    <Card
      className={cn(
        'p-4 cursor-pointer transition-all hover:shadow-md',
        isUnlocked ? 'bg-gradient-to-br from-yellow-50 to-orange-50 border-yellow-200' : 'opacity-60'
      )}
      onClick={onClick}
    >
      <div className="flex items-center gap-3">
        <div className="text-3xl">{achievement.icon}</div>
        <div className="flex-1">
          <h3 className="font-semibold text-sm">{achievement.name}</h3>
          <p className="text-xs text-gray-600 mt-1">{achievement.description}</p>

          {/* 进度条 */}
          {!isUnlocked && progress > 0 && (
            <div className="mt-2">
              <Progress value={progress} className="h-2" />
              <span className="text-xs text-gray-500 mt-1">{progress}%</span>
            </div>
          )}

          {/* 积分显示 */}
          <div className="flex items-center gap-2 mt-2">
            <Badge variant="secondary" className="text-xs">
              {achievement.points} 积分
            </Badge>
            {achievement.type && (
              <Badge variant="outline" className="text-xs">
                {achievement.type}
              </Badge>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
});

Achievement.displayName = 'Achievement';

// 成就展示组件
interface AchievementShowcaseProps {
  achievements: Achievement[];
  userAchievements?: Array<{ achievementId: string; unlockedAt: string }>;
  onAchievementClick?: (achievement: Achievement) => void;
}

export function AchievementShowcase({
  achievements,
  userAchievements = [],
  onAchievementClick,
}: AchievementShowcaseProps) {
  const unlockedIds = new Set(userAchievements.map(ua => ua.achievementId));

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">成就系统</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {achievements.map(achievement => (
          <Achievement
            key={achievement.id}
            achievement={achievement}
            isUnlocked={unlockedIds.has(achievement.id)}
            onClick={() => onAchievementClick?.(achievement)}
          />
        ))}
      </div>
    </div>
  );
}

// 新手提示组件
interface TooltipGuideProps {
  content: string;
  target: string; // CSS选择器
  position?: 'top' | 'bottom' | 'left' | 'right';
  delay?: number;
  showOnce?: boolean;
}

export function TooltipGuide({
  content,
  target,
  position = 'top',
  delay = 1000,
  showOnce = true,
}: TooltipGuideProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [hasBeenShown, setHasBeenShown] = useState(false);

  useEffect(() => {
    if (showOnce && hasBeenShown) return;

    const timer = setTimeout(() => {
      setIsVisible(true);
      setHasBeenShown(true);
    }, delay);

    return () => clearTimeout(timer);
  }, [delay, showOnce, hasBeenShown]);

  const handleClose = useCallback(() => {
    setIsVisible(false);
  }, []);

  if (!isVisible) return null;

  const targetElement = document.querySelector(target) as HTMLElement;
  if (!targetElement) return null;

  const rect = targetElement.getBoundingClientRect();
  const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
  const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;

  let tooltipStyle: React.CSSProperties = {};

  switch (position) {
    case 'top':
      tooltipStyle = {
        top: `${rect.top + scrollTop - 60}px`,
        left: `${rect.left + scrollLeft + rect.width / 2}px`,
        transform: 'translateX(-50%)',
      };
      break;
    case 'bottom':
      tooltipStyle = {
        top: `${rect.bottom + scrollTop + 10}px`,
        left: `${rect.left + scrollLeft + rect.width / 2}px`,
        transform: 'translateX(-50%)',
      };
      break;
    case 'left':
      tooltipStyle = {
        top: `${rect.top + scrollTop + rect.height / 2}px`,
        left: `${rect.left + scrollLeft - 10}px`,
        transform: 'translateY(-50%) translateX(-100%)',
      };
      break;
    case 'right':
      tooltipStyle = {
        top: `${rect.top + scrollTop + rect.height / 2}px`,
        left: `${rect.right + scrollLeft + 10}px`,
        transform: 'translateY(-50%)',
      };
      break;
  }

  return (
    <div
      className={cn(
        'fixed z-50 bg-gray-900 text-white text-sm rounded-lg px-3 py-2 shadow-lg',
        'max-w-xs animate-in fade-in-0 zoom-in-95 duration-200'
      )}
      style={tooltipStyle}
    >
      <div className="relative">
        {content}
        <button
          onClick={handleClose}
          className="absolute -top-1 -right-1 w-4 h-4 bg-white text-gray-900 rounded-full text-xs flex items-center justify-center hover:bg-gray-100"
        >
          ×
        </button>
      </div>
    </div>
  );
}

// 引导入口组件
interface GuideEntryProps {
  guides: UserGuide[];
  onGuideSelect?: (guide: UserGuide) => void;
}

export function GuideEntry({ guides, onGuideSelect }: GuideEntryProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleGuideSelect = useCallback((guide: UserGuide) => {
    onGuideSelect?.(guide);
    setIsOpen(false);
  }, [onGuideSelect]);

  return (
    <div className="fixed bottom-4 right-4 z-30">
      {/* 引导按钮 */}
      <Button
        onClick={() => setIsOpen(true)}
        className="rounded-full w-12 h-12 shadow-lg"
        size="sm"
      >
        💡
      </Button>

      {/* 引导列表 */}
      {isOpen && (
        <div className="absolute bottom-16 right-0 w-64 bg-white rounded-lg shadow-xl border border-gray-200">
          <div className="p-4 border-b">
            <h3 className="font-semibold">用户引导</h3>
          </div>
          <div className="max-h-64 overflow-y-auto">
            {guides.map(guide => (
              <button
                key={guide.id}
                onClick={() => handleGuideSelect(guide)}
                className="w-full text-left p-3 hover:bg-gray-50 border-b last:border-b-0"
              >
                <div className="font-medium text-sm">{guide.name}</div>
                <div className="text-xs text-gray-600 mt-1">{guide.description}</div>
                <div className="flex items-center gap-2 mt-2">
                  <Badge variant="outline" className="text-xs">
                    {guide.category}
                  </Badge>
                  <span className="text-xs text-gray-500">
                    {guide.steps.length} 步骤
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default {
  GuideStep,
  UserGuideManager,
  UserProgressTracker,
  Achievement,
  AchievementShowcase,
  TooltipGuide,
  GuideEntry,
};