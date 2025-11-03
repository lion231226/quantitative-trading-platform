import React, { useState, useCallback, useMemo } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Home,
  BookOpen,
  CheckCircle,
  Circle,
  SkipForward,
  RotateCcw,
  List,
  Map,
  Navigation,
} from 'lucide-react';
import {
  Tutorial,
  TutorialProgress,
  TutorialStep,
} from '@/types/tutorial.types';
import {
  canSkipStep,
  getStepNavigation,
  calculateCompletionPercentage,
} from '@/utils/tutorialHelpers';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';

interface TutorialNavigationProps {
  tutorial: Tutorial;
  progress: TutorialProgress;
  currentStep: TutorialStep;
  onNavigate: (stepIndex: number) => void;
  onNext: () => void;
  onPrevious: () => void;
  onComplete: () => void;
  onSkip: () => void;
  onRestart: () => void;
  showMap?: boolean;
  compact?: boolean;
  disabled?: boolean;
}

/**
 * 教程导航组件
 * 提供步骤导航、跳转、地图视图等功能
 */
export function TutorialNavigation({
  tutorial,
  progress,
  currentStep,
  onNavigate,
  onNext,
  onPrevious,
  onComplete,
  onSkip,
  onRestart,
  showMap = true,
  compact = false,
  disabled = false,
}: TutorialNavigationProps) {
  const [isMapOpen, setIsMapOpen] = useState(false);
  const [selectedStepIndex, setSelectedStepIndex] = useState<number | null>(null);

  const navigation = useMemo(() => {
    return getStepNavigation({
      currentStep,
      progress,
      tutorial,
    });
  }, [currentStep, progress, tutorial]);

  const completionPercentage = useMemo(() => {
    return calculateCompletionPercentage(progress);
  }, [progress]);

  const canSkip = useMemo(() => {
    return canSkipStep(currentStep, progress);
  }, [currentStep, progress]);

  // 处理步骤跳转
  const handleStepSelect = useCallback((stepIndex: number) => {
    if (disabled) return;

    // 检查是否可以跳转到目标步骤
    if (stepIndex >= 0 && stepIndex < tutorial.steps.length) {
      onNavigate(stepIndex);
      setSelectedStepIndex(null);
      setIsMapOpen(false);
    }
  }, [disabled, onNavigate, tutorial.steps.length]);

  // 处理快速导航
  const handleQuickNavigate = useCallback((direction: 'first' | 'last' | 'next-uncompleted') => {
    if (disabled) return;

    switch (direction) {
      case 'first':
        onNavigate(0);
        break;
      case 'last':
        onNavigate(tutorial.steps.length - 1);
        break;
      case 'next-uncompleted':
        const nextUncompleted = tutorial.steps.findIndex((_, index) =>
          !progress.completedSteps.includes(index)
        );
        if (nextUncompleted >= 0) {
          onNavigate(nextUncompleted);
        }
        break;
    }
  }, [disabled, onNavigate, tutorial.steps, progress.completedSteps]);

  // 获取步骤状态
  const getStepStatus = useCallback((stepIndex: number) => {
    if (progress.completedSteps.includes(stepIndex)) {
      return 'completed';
    } else if (progress.skippedSteps.includes(stepIndex)) {
      return 'skipped';
    } else if (progress.bookmarks.includes(stepIndex)) {
      return 'bookmarked';
    } else if (stepIndex === progress.currentStep) {
      return 'current';
    } else {
      return 'pending';
    }
  }, [progress]);

  // 获取步骤图标
  const getStepIcon = useCallback((stepIndex: number) => {
    const status = getStepStatus(stepIndex);

    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'skipped':
        return <SkipForward className="h-4 w-4 text-gray-400" />;
      case 'current':
        return <Circle className="h-4 w-4 text-blue-600" />;
      default:
        return <Circle className="h-4 w-4 text-gray-300" />;
    }
  }, [getStepStatus]);

  // 渲染步骤地图
  const renderStepMap = () => {
    return (
      <div className="space-y-4">
        {/* 快速导航 */}
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium text-gray-700">快速导航:</span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleQuickNavigate('first')}
          >
            <Home className="h-3 w-3 mr-1" />
            第一步
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleQuickNavigate('next-uncompleted')}
          >
            <Navigation className="h-3 w-3 mr-1" />
            下一个未完成
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleQuickNavigate('last')}
          >
            <BookOpen className="h-3 w-3 mr-1" />
            最后一步
          </Button>
        </div>

        {/* 步骤列表 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {tutorial.steps.map((step, index) => {
            const status = getStepStatus(index);
            const isSelectable = status !== 'completed' || index <= progress.currentStep + 1;

            return (
              <Card
                key={step.id}
                className={`p-4 cursor-pointer transition-all ${
                  index === progress.currentStep
                    ? 'ring-2 ring-blue-500 bg-blue-50'
                    : isSelectable
                    ? 'hover:bg-gray-50'
                    : 'opacity-50 cursor-not-allowed'
                }`}
                onClick={() => isSelectable && onNavigateToStep(index)}
              >
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 mt-1">
                    {status === 'completed' ? (
                      <CheckCircle className="h-5 w-5 text-green-600" />
                    ) : status === 'current' ? (
                      <PlayCircle className="h-5 w-5 text-blue-600" />
                    ) : status === 'skipped' ? (
                      <SkipForward className="h-5 w-5 text-yellow-600" />
                    ) : (
                      <Circle className="h-5 w-5 text-gray-300" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-medium text-gray-900 truncate">
                      {step.title}
                    </h4>
                    <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                      {step.content.substring(0, 100)}...
                    </p>
                    <div className="flex items-center space-x-2 mt-2">
                      <Badge variant={step.type === 'interactive' ? 'default' : 'secondary'} className="text-xs">
                        {step.type === 'explanation' ? '解释' :
                         step.type === 'animation' ? '动画' :
                         step.type === 'interactive' ? '交互' : '测验'}
                      </Badge>
                      {step.isOptional && (
                        <Badge variant="outline" className="text-xs">
                          可选
                        </Badge>
                      )}
                      {progress.bookmarks.includes(index) && (
                        <Bookmark className="h-3 w-3 text-yellow-600" />
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>

        {/* 进度统计 */}
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold text-green-600">
                {progress.completedSteps.length}
              </p>
              <p className="text-xs text-gray-600">已完成</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-blue-600">
                {progress.skippedSteps.length}
              </p>
              <p className="text-xs text-gray-600">已跳过</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-yellow-600">
                {progress.bookmarks.length}
              </p>
              <p className="text-xs text-gray-600">书签</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-purple-600">
                {completionPercentage}%
              </p>
              <p className="text-xs text-gray-600">完成率</p>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // 渲染紧凑模式导航
  if (compact) {
    return (
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={onPrevious}
            disabled={disabled || !navigation.canGoBack}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>

          <span className="text-sm text-gray-600 px-2">
            {navigation.currentIndex + 1} / {navigation.totalSteps}
          </span>

          <Button
            variant="ghost"
            size="sm"
            onClick={navigation.isLastStep ? onComplete : onNext}
            disabled={disabled}
          >
            {navigation.isLastStep ? (
              <CheckCircle className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </Button>
        </div>

        {showMap && (
          <Dialog open={isMapOpen} onOpenChange={setIsMapOpen}>
            <DialogTrigger asChild>
              <Button variant="ghost" size="sm" disabled={disabled}>
                <Map className="h-4 w-4" />
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>教程地图</DialogTitle>
                <DialogDescription>
                  查看所有教程步骤并快速导航
                </DialogDescription>
              </DialogHeader>
              {renderStepMap()}
            </DialogContent>
          </Dialog>
        )}
      </div>
    );
  }
    return (
      <div className="space-y-4">
        {/* 快速导航 */}
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium text-gray-700">快速导航:</span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleQuickNavigate('first')}
          >
            <Home className="h-3 w-3 mr-1" />
            第一步
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleQuickNavigate('next-uncompleted')}
          >
            <Navigation className="h-3 w-3 mr-1" />
            下一个未完成
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleQuickNavigate('last')}
          >
            <BookOpen className="h-3 w-3 mr-1" />
            最后一步
          </Button>
        </div>

        {/* 步骤列表 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {tutorial.steps.map((step, index) => {
            const status = getStepStatus(index);
            const isSelectable = status !== 'completed' || index <= progress.currentStep + 1;

            return (
              <Card
                key={step.id}
                className={`p-4 cursor-pointer transition-all hover:shadow-md ${
                  !isSelectable ? 'opacity-50 cursor-not-allowed' : ''
                } ${
                  index === progress.currentStep
                    ? 'ring-2 ring-blue-500 bg-blue-50'
                    : status === 'completed'
                    ? 'bg-green-50 border-green-200'
                    : 'hover:bg-gray-50'
                }`}
                onClick={() => isSelectable && handleStepSelect(index)}
              >
                <div className="flex items-start space-x-3">
                  <div className="mt-1">
                    {getStepIcon(index)}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <h4 className="font-medium text-gray-900 truncate">
                        步骤 {index + 1}: {step.title}
                      </h4>
                      <div className="flex items-center space-x-1">
                        {step.isOptional && (
                          <Badge variant="outline" className="text-xs">
                            可选
                          </Badge>
                        )}
                        {progress.bookmarks.includes(index) && (
                          <Badge variant="secondary" className="text-xs">
                            书签
                          </Badge>
                        )}
                      </div>
                    </div>

                    <p className="text-sm text-gray-600 line-clamp-2">
                      {step.content.substring(0, 100)}...
                    </p>

                    <div className="flex items-center justify-between mt-2">
                      <span className="text-xs text-gray-500">
                        类型: {step.type}
                        {step.estimatedTime && ` • ${step.estimatedTime}秒`}
                      </span>

                      {index === progress.currentStep && (
                        <Badge variant="default" className="text-xs">
                          当前
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>

        {/* 进度统计 */}
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold text-green-600">
                {progress.completedSteps.length}
              </p>
              <p className="text-xs text-gray-600">已完成</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-blue-600">
                {progress.skippedSteps.length}
              </p>
              <p className="text-xs text-gray-600">已跳过</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-yellow-600">
                {progress.bookmarks.length}
              </p>
              <p className="text-xs text-gray-600">书签</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-purple-600">
                {completionPercentage}%
              </p>
              <p className="text-xs text-gray-600">完成率</p>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="bg-white border rounded-lg p-4">
      {/* 主要导航控制 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <Button
            variant="outline"
            onClick={onPrevious}
            disabled={disabled || !navigation.canGoBack}
          >
            <ChevronLeft className="h-4 w-4 mr-2" />
            上一步
          </Button>

          {canSkip && (
            <Button
              variant="outline"
              onClick={onSkip}
              disabled={disabled}
            >
              <SkipForward className="h-4 w-4 mr-2" />
              跳过
            </Button>
          )}

          <Button
            variant="outline"
            onClick={onRestart}
            disabled={disabled}
          >
            <RotateCcw className="h-4 w-4 mr-2" />
            重新开始
          </Button>
        </div>

        <div className="flex items-center space-x-3">
          <span className="text-sm text-gray-600">
            进度: {navigation.currentIndex + 1} / {navigation.totalSteps}
          </span>

          {showMap && (
            <Dialog open={isMapOpen} onOpenChange={setIsMapOpen}>
              <DialogTrigger asChild>
                <Button variant="outline" disabled={disabled}>
                  <Map className="h-4 w-4 mr-2" />
                  教程地图
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle>教程地图</DialogTitle>
                  <DialogDescription>
                    查看所有教程步骤并快速导航
                  </DialogDescription>
                </DialogHeader>
                {renderStepMap()}
              </DialogContent>
            </Dialog>
          )}

          <Button
            onClick={navigation.isLastStep ? onComplete : onNext}
            disabled={disabled}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {navigation.isLastStep ? (
              <>
                <CheckCircle className="h-4 w-4 mr-2" />
                完成教程
              </>
            ) : (
              <>
                下一步
                <ChevronRight className="h-4 w-4 ml-2" />
              </>
            )}
          </Button>
        </div>
      </div>

      {/* 进度条 */}
      <div className="mb-4">
        <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
          <span>整体进度</span>
          <span className="font-medium">{completionPercentage}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${completionPercentage}%` }}
          ></div>
        </div>
      </div>

      {/* 步缩略图导航 */}
      <div className="flex items-center space-x-2 overflow-x-auto pb-2">
        {tutorial.steps.map((step, index) => {
          const status = getStepStatus(index);
          const isActive = index === navigation.currentIndex;

          return (
            <button
              key={step.id}
              onClick={() => handleStepSelect(index)}
              disabled={disabled || (status === 'completed' && index > navigation.currentIndex + 1)}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg border transition-all whitespace-nowrap ${
                isActive
                  ? 'bg-blue-100 border-blue-300 text-blue-800'
                  : status === 'completed'
                  ? 'bg-green-100 border-green-300 text-green-800'
                  : 'bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100'
              } ${
                disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
              }`}
            >
              {getStepIcon(index)}
              <span className="text-xs font-medium">
                {index + 1}
              </span>
            </button>
          );
        })}
      </div>

      {/* 当前步骤信息 */}
      <div className="mt-4 p-3 bg-blue-50 rounded-lg">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="font-medium text-blue-900">
              当前步骤: {currentStep.title}
            </h4>
            <p className="text-sm text-blue-700 mt-1">
              类型: {currentStep.type}
              {currentStep.estimatedTime && ` • 预计时间: ${currentStep.estimatedTime}秒`}
            </p>
          </div>
          <div className="flex items-center space-x-2">
            {currentStep.isOptional && (
              <Badge variant="outline">可选步骤</Badge>
            )}
            {progress.bookmarks.includes(navigation.currentIndex) && (
              <Badge variant="secondary">已加书签</Badge>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default TutorialNavigation;
  );
}
export default TutorialNavigation;
