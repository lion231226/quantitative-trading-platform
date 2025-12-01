import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Award,
  BookOpen,
  Bookmark,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  Clock,
  PlayCircle,
  X,
} from 'lucide-react';
import { useTutorialService } from '@/services/tutorialService';
import {
  Achievement,
  Tutorial,
  TutorialContext,
  TutorialProgress,
  TutorialProgressUpdate,
  TutorialStep,
  TutorialUserPreferences,
} from '@/types/tutorial.types';
import {
  canSkipStep,
  createTutorialEvent,
  generateProgressSummary,
  getStepNavigation,
} from '@/utils/tutorialHelpers';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface TutorialSystemProps {
  tutorialId: string;
  isOpen: boolean;
  onClose: () => void;
  onComplete?: (tutorialId: string) => void;
  autoStart?: boolean;
}

/**
 * 教程系统主组件
 * 负责教程流程控制、导航和状态管理
 */
function TutorialSystem({
  tutorialId,
  isOpen,
  onClose,
  onComplete,
  autoStart = false,
}: TutorialSystemProps) {
  const {
    useTutorial,
    useTutorialProgress,
    useUpdateProgress,
    saveUserPreferences,
    progressManager,
  } = useTutorialService();

  const [isStarted, setIsStarted] = useState(autoStart);
  const [stepStartTime, setStepStartTime] = useState<number>(Date.now());
  const [showAchievement, setShowAchievement] = useState<Achievement | null>(
    null,
  );
  const [userPreferences, setUserPreferences] =
    useState<TutorialUserPreferences>(() => {
      // 在初始化时直接设置用户偏好，避免 useEffect 的问题
      try {
        const stored = localStorage.getItem('tutorial_preferences');
        return stored ? JSON.parse(stored) : {};
      } catch (error) {
        console.error('Failed to load user preferences:', error);
        return {};
      }
    });

  // 获取教程数据
  const tutorial = useTutorial(tutorialId, {
    enabled: isOpen,
    queryKey: ['tutorial', tutorialId],
  });

  // 获取教程进度
  const progress = useTutorialProgress(tutorialId, {
    enabled: isOpen,
    queryKey: ['tutorial-progress', tutorialId],
  });

  // 更新进度的变更钩子
  const updateProgress = useUpdateProgress();

  // 用户偏好已在组件初始化时加载

  // 当前步骤计时器
  const stepTimerRef = useRef<NodeJS.Timeout>();

  // 教程上下文
  const tutorialContext: TutorialContext | null = React.useMemo(() => {
    if (!tutorial.data || !progress.data) return null;

    const currentStep = tutorial.data.steps[progress.data.currentStep];
    const previousStep =
      progress.data.currentStep > 0
        ? tutorial.data.steps[progress.data.currentStep - 1]
        : undefined;
    const nextStep =
      progress.data.currentStep < tutorial.data.steps.length - 1
        ? tutorial.data.steps[progress.data.currentStep + 1]
        : undefined;

    return {
      currentStep,
      progress: progress.data,
      tutorial: tutorial.data,
      previousStep,
      nextStep,
    };
  }, [tutorial.data, progress.data]);

  // 初始化教程进度
  useEffect(() => {
    if (tutorial.data && !progress.data && isOpen) {
      const newProgress = progressManager.createProgress(
        tutorialId,
        tutorial.data.steps.length,
      );
      // 使用正确的 React Query mutation 方式更新进度
      updateProgress.mutate({
        tutorialId,
        stepIndex: 0,
        action: {
          stepId: tutorial.data.steps[0].id,
          action: 'start',
          timestamp: new Date().toISOString(),
        },
      });
    }
  }, [tutorial.data, progress.data, tutorialId, isOpen, updateProgress]);

  // 用户偏好已在 useState 初始化函数中加载，移除有问题的 useEffect

  // 开始步骤计时
  const startStepTimer = useCallback(() => {
    setStepStartTime(Date.now());

    // 清除之前的计时器
    if (stepTimerRef.current) {
      clearInterval(stepTimerRef.current);
    }

    // 每秒更新一次时间
    stepTimerRef.current = setInterval(() => {
      // 可以在这里添加实时时间更新逻辑
    }, 1000);
  }, []);

  // 完成当前步骤
  const completeCurrentStep = useCallback(async () => {
    if (!tutorialContext || !progress.data) return;

    const timeSpent = Math.floor((Date.now() - stepStartTime) / 1000);
    const stepIndex = tutorialContext.progress.currentStep;

    // 更新进度
    await updateProgress.mutateAsync({
      tutorialId,
      stepIndex,
      action: {
        stepId: tutorialContext.currentStep.id,
        action: 'complete',
        timestamp: new Date().toISOString(),
        timeSpent,
      },
    });

    // 检查是否解锁成就
    checkAndUnlockAchievements(stepIndex);

    // 检查是否完成整个教程
    if (stepIndex === tutorialContext.tutorial.steps.length - 1) {
      handleTutorialComplete();
    } else {
      // 开始下一步计时
      startStepTimer();
    }
  }, [
    tutorialContext,
    progress.data,
    tutorialId,
    updateProgress,
    stepStartTime,
    startStepTimer,
  ]);

  // 跳过当前步骤
  const skipCurrentStep = useCallback(async () => {
    if (!tutorialContext) return;

    const stepIndex = tutorialContext.progress.currentStep;
    const currentStep = tutorialContext.currentStep;

    if (!canSkipStep(currentStep, tutorialContext.progress)) {
      return; // 不能跳过此步骤
    }

    await updateProgress.mutateAsync({
      tutorialId,
      stepIndex,
      action: {
        stepId: currentStep.id,
        action: 'skip',
        timestamp: new Date().toISOString(),
      },
    });

    // 推进到下一步
    if (stepIndex < tutorialContext.tutorial.steps.length - 1) {
      startStepTimer();
    }
  }, [tutorialContext, tutorialId, updateProgress, startStepTimer]);

  // 添加书签
  const addBookmark = useCallback(async () => {
    if (!tutorialContext) return;

    const stepIndex = tutorialContext.progress.currentStep;

    await updateProgress.mutateAsync({
      tutorialId,
      stepIndex,
      action: {
        stepId: tutorialContext.currentStep.id,
        action: 'bookmark',
        timestamp: new Date().toISOString(),
      },
    });
  }, [tutorialContext, tutorialId, updateProgress]);

  // 导航到指定步骤
  const navigateToStep = useCallback(
    async (stepIndex: number) => {
      if (
        !tutorialContext ||
        stepIndex < 0 ||
        stepIndex >= tutorialContext.tutorial.steps.length
      ) {
        return;
      }

      await updateProgress.mutateAsync({
        tutorialId,
        stepIndex,
        action: {
          stepId: tutorialContext.tutorial.steps[stepIndex].id,
          action: 'start',
          timestamp: new Date().toISOString(),
        },
      });

      startStepTimer();
    },
    [tutorialContext, tutorialId, updateProgress, startStepTimer],
  );

  // 后退到上一步
  const goToPreviousStep = useCallback(() => {
    if (!tutorialContext) return;
    const previousIndex = tutorialContext.progress.currentStep - 1;
    if (previousIndex >= 0) {
      navigateToStep(previousIndex);
    }
  }, [tutorialContext, navigateToStep]);

  // 前进到下一步
  const goToNextStep = useCallback(() => {
    if (!tutorialContext) return;
    const nextIndex = tutorialContext.progress.currentStep + 1;
    if (nextIndex < tutorialContext.tutorial.steps.length) {
      navigateToStep(nextIndex);
    }
  }, [tutorialContext, navigateToStep]);

  // 检查并解锁成就
  const checkAndUnlockAchievements = useCallback(
    (stepIndex: number) => {
      if (!tutorial.data || !progress.data) return;

      // 第一步完成成就
      if (stepIndex === 0 && progress.data.completedSteps.length === 1) {
        const achievement = {
          id: `first_step_${tutorialId}`,
          title: '初学者',
          description: `完成了《${tutorial.data.title}》的第一步`,
          unlockedAt: new Date().toISOString(),
          icon: '🎯',
        };
        unlockAchievement(achievement);
      }

      // 教程完成成就
      if (stepIndex === tutorial.data.steps.length - 1) {
        const achievement = {
          id: `complete_${tutorialId}`,
          title: '教程完成者',
          description: `成功完成了《${tutorial.data.title}》教程`,
          unlockedAt: new Date().toISOString(),
          icon: '🎉',
        };
        unlockAchievement(achievement);
      }
    },
    [tutorial.data, progress.data, tutorialId],
  );

  // 解锁成就
  const unlockAchievement = useCallback((achievement: Achievement) => {
    setShowAchievement(achievement);
    setTimeout(() => setShowAchievement(null), 3000); // 3秒后隐藏
  }, []);

  // 教程完成处理
  const handleTutorialComplete = useCallback(() => {
    if (onComplete) {
      onComplete(tutorialId);
    }

    // 可以添加完成动画或提示
    setTimeout(() => {
      onClose();
    }, 2000);
  }, [tutorialId, onComplete, onClose]);

  // 开始教程
  const startTutorial = useCallback(() => {
    setIsStarted(true);
    startStepTimer();
  }, [startStepTimer]);

  // 重新开始教程
  const restartTutorial = useCallback(() => {
    if (tutorial.data) {
      // 使用 mutation 重新开始教程
      updateProgress.mutate({
        tutorialId,
        stepIndex: 0,
        action: {
          stepId: tutorial.data.steps[0].id,
          action: 'start',
          timestamp: new Date().toISOString(),
        },
      });
      setIsStarted(true);
      startStepTimer();
    }
  }, [tutorial.data, tutorialId, updateProgress, startStepTimer]);

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      if (stepTimerRef.current) {
        clearInterval(stepTimerRef.current);
      }
    };
  }, []);

  if (!isOpen) return null;

  if (tutorial.isLoading || progress.isLoading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">正在加载教程...</p>
        </div>
      </div>
    );
  }

  if (tutorial.error || progress.error) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <Card className="p-6 max-w-md">
          <h3 className="text-lg font-semibold text-red-600 mb-2">加载失败</h3>
          <p className="text-gray-600 mb-4">无法加载教程内容，请稍后重试。</p>
          <Button onClick={onClose}>关闭</Button>
        </Card>
      </div>
    );
  }

  if (!tutorial.data || !progress.data) {
    return null;
  }

  const navigation = tutorialContext
    ? getStepNavigation(tutorialContext)
    : null;
  const progressSummary = progress.data
    ? generateProgressSummary(progress.data, tutorial.data)
    : null;

  // 键盘导航处理（在navigation定义之后）
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!isOpen) return;

      // ESC键关闭教程
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }

      // 当教程开始后，支持步骤导航
      if (isStarted && tutorialContext) {
        switch (event.key) {
          case 'ArrowLeft':
            event.preventDefault();
            goToPreviousStep();
            break;
          case 'ArrowRight':
            event.preventDefault();
            goToNextStep();
            break;
          case 'Home':
            event.preventDefault();
            // 跳转到第一步
            if (progress && tutorialContext) {
              navigateToStep(0);
            }
            break;
          case 'End':
            event.preventDefault();
            // 跳转到最后一步
            if (progress && navigation) {
              navigateToStep(navigation.totalSteps - 1);
            }
            break;
        }
      }
    },
    [
      isOpen,
      isStarted,
      onClose,
      goToPreviousStep,
      goToNextStep,
      navigateToStep,
      progress,
      navigation,
      tutorialContext,
    ],
  );

  // 键盘事件监听
  useEffect(() => {
    if (!isOpen) return;

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, handleKeyDown]);

  // 教程介绍页面
  if (!isStarted) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <Card className="p-8 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                {tutorial.data.title}
              </h2>
              <p className="text-gray-600">{tutorial.data.description}</p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="text-center">
              <Clock className="h-6 w-6 mx-auto mb-1 text-blue-600" />
              <p className="text-sm text-gray-600">
                {tutorial.data.estimatedDuration}分钟
              </p>
            </div>
            <div className="text-center">
              <BookOpen className="h-6 w-6 mx-auto mb-1 text-green-600" />
              <p className="text-sm text-gray-600">
                {tutorial.data.steps.length}个步骤
              </p>
            </div>
            <div className="text-center">
              <Badge
                variant={
                  tutorial.data.difficulty === 'beginner'
                    ? 'default'
                    : 'secondary'
                }
              >
                {tutorial.data.difficulty === 'beginner'
                  ? '初级'
                  : tutorial.data.difficulty === 'intermediate'
                    ? '中级'
                    : '高级'}
              </Badge>
            </div>
            <div className="text-center">
              <span className="text-sm text-gray-600">
                {tutorial.data.category}
              </span>
            </div>
          </div>

          {tutorial.data.tags && tutorial.data.tags.length > 0 && (
            <div className="mb-6">
              <h4 className="text-sm font-medium text-gray-700 mb-2">标签</h4>
              <div className="flex flex-wrap gap-2">
                {tutorial.data.tags.map((tag) => (
                  <Badge key={tag} variant="outline" className="text-xs">
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          <div className="flex justify-end space-x-3">
            <Button
              variant="outline"
              onClick={onClose}
              aria-label="稍后学习并关闭教程"
            >
              稍后学习
            </Button>
            <Button
              onClick={startTutorial}
              className="bg-blue-600 hover:bg-blue-700"
              aria-label="开始教程"
            >
              <PlayCircle className="h-4 w-4 mr-2" aria-hidden="true" />
              开始教程
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  // 教程主界面
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div
        className="bg-white rounded-lg w-full max-w-4xl h-[80vh] flex flex-col"
        role="dialog"
        aria-modal="true"
        aria-labelledby="tutorial-title"
        aria-describedby="tutorial-progress"
      >
        {/* 顶部导航栏 */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center space-x-4">
            <h3 id="tutorial-title" className="text-lg font-semibold">
              {tutorial.data.title}
            </h3>
            {progressSummary && (
              <div
                id="tutorial-progress"
                className="flex items-center space-x-2 text-sm text-gray-600"
                aria-live="polite"
                aria-atomic="true"
              >
                <span>
                  {progress.data.completedSteps.length}/{navigation?.totalSteps}{' '}
                  步骤
                </span>
                <span>•</span>
                <span>{progressSummary.percentage}%</span>
              </div>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={addBookmark}
              aria-label="添加书签"
            >
              <Bookmark className="h-4 w-4" aria-hidden="true" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={restartTutorial}
              aria-label="重新开始教程"
            >
              重新开始
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              aria-label="关闭教程"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
        </div>

        {/* 进度条 */}
        {progressSummary && (
          <div className="px-4 py-2 bg-gray-50">
            <div
              className="w-full bg-gray-200 rounded-full h-2"
              role="progressbar"
              aria-valuenow={progressSummary.percentage}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`教程进度：${progressSummary.percentage}% 完成`}
            >
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progressSummary.percentage}%` }}
              ></div>
            </div>
          </div>
        )}

        {/* 主要内容区域 */}
        <div className="flex-1 overflow-hidden flex">
          {/* 教程内容 */}
          <main
            className="flex-1 p-6 overflow-y-auto"
            role="main"
            aria-label="教程内容"
          >
            {tutorialContext && (
              <article className="max-w-3xl mx-auto">
                <header>
                  <h2 className="text-xl font-semibold mb-4" id="step-title">
                    {tutorialContext.currentStep.title}
                  </h2>
                </header>
                <div className="prose max-w-none" aria-labelledby="step-title">
                  {/* 这里将根据步骤类型渲染不同的内容 */}
                  <section
                    className="bg-gray-50 p-6 rounded-lg"
                    aria-label="步骤内容"
                  >
                    <p className="text-gray-700">
                      {tutorialContext.currentStep.content}
                    </p>
                    <footer className="mt-4 text-sm text-gray-500">
                      <span
                        aria-label={`步骤类型: ${tutorialContext.currentStep.type}`}
                      >
                        步骤类型: {tutorialContext.currentStep.type}
                      </span>
                      {tutorialContext.currentStep.estimatedTime && (
                        <span
                          aria-label={`预计时间: ${tutorialContext.currentStep.estimatedTime}秒`}
                        >
                          • 预计时间:{' '}
                          {tutorialContext.currentStep.estimatedTime}秒
                        </span>
                      )}
                    </footer>
                  </section>
                </div>
              </article>
            )}
          </main>
        </div>

        {/* 底部控制栏 */}
        <footer
          className="flex items-center justify-between p-4 border-t bg-gray-50"
          role="contentinfo"
        >
          <nav className="flex items-center space-x-3" aria-label="步骤导航">
            <Button
              variant="outline"
              onClick={goToPreviousStep}
              disabled={!navigation?.canGoBack}
              aria-label="上一步"
              aria-describedby="step-navigation-status"
            >
              <ChevronLeft className="h-4 w-4 mr-2" aria-hidden="true" />
              上一步
            </Button>
            <Button
              variant="outline"
              onClick={skipCurrentStep}
              disabled={!tutorialContext?.currentStep.isOptional}
              aria-label="跳过当前步骤"
            >
              跳过
            </Button>
          </nav>

          <div className="flex items-center space-x-3">
            <span
              id="step-navigation-status"
              className="text-sm text-gray-600"
              aria-live="polite"
              aria-atomic="true"
            >
              第 {navigation?.currentIndex + 1} 步，共 {navigation?.totalSteps}{' '}
              步
            </span>
            <Button
              onClick={
                navigation?.isLastStep ? completeCurrentStep : goToNextStep
              }
              className="bg-blue-600 hover:bg-blue-700"
              aria-label={navigation?.isLastStep ? '完成教程' : '下一步'}
              aria-describedby="step-navigation-status"
            >
              {navigation?.isLastStep ? (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" aria-hidden="true" />
                  完成教程
                </>
              ) : (
                <>
                  下一步
                  <ChevronRight className="h-4 w-4 ml-2" aria-hidden="true" />
                </>
              )}
            </Button>
          </div>
        </footer>
      </div>

      {/* 成就通知 */}
      {showAchievement && (
        <div className="fixed top-4 right-4 bg-yellow-50 border border-yellow-200 rounded-lg p-4 shadow-lg z-50">
          <div className="flex items-center space-x-3">
            <Award className="h-6 w-6 text-yellow-600" />
            <div>
              <p className="font-semibold text-yellow-800">
                {showAchievement.title}
              </p>
              <p className="text-sm text-yellow-600">
                {showAchievement.description}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default TutorialSystem;
