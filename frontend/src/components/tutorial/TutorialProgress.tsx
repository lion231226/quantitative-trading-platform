import React from 'react';
import { Progress } from '@/components/ui/progress';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  TutorialProgress as TutorialProgressType,
  TutorialStats,
  Achievement,
  TutorialStep,
} from '@/types/tutorial.types';
import {
  calculateCompletionPercentage,
  formatTime,
  generateProgressSummary,
} from '@/utils/tutorialHelpers';
import {
  Clock,
  BookOpen,
  Award,
  TrendingUp,
  CheckCircle,
  Circle,
  Bookmark,
  SkipForward,
} from 'lucide-react';

interface TutorialProgressProps {
  progress: TutorialProgressType;
  tutorialSteps: TutorialStep[];
  stats?: TutorialStats;
  onNavigateToStep?: (stepIndex: number) => void;
  showDetails?: boolean;
  compact?: boolean;
}

/**
 * 教程进度组件
 * 显示教程进度、统计信息和步骤导航
 */
export function TutorialProgress({
  progress,
  tutorialSteps,
  stats,
  onNavigateToStep,
  showDetails = true,
  compact = false,
}: TutorialProgressProps) {
  const completionPercentage = calculateCompletionPercentage(progress);
  const progressSummary = generateProgressSummary(progress, {
    steps: tutorialSteps,
    id: '',
    title: '',
    description: '',
    category: '',
    difficulty: 'beginner',
    estimatedDuration: 0,
    tags: [],
  });

  if (compact) {
    return (
      <div className="flex items-center space-x-4">
        <div className="flex-1">
          <Progress value={completionPercentage} className="h-2" />
        </div>
        <span className="text-sm font-medium text-gray-600">
          {completionPercentage}%
        </span>
        <div className="flex items-center space-x-1 text-sm text-gray-500">
          <Clock className="h-4 w-4" />
          <span>{formatTime(progress.totalTimeSpent)}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 总体进度 */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">学习进度</h3>
          <Badge variant={completionPercentage === 100 ? 'default' : 'secondary'}>
            {completionPercentage === 100 ? '已完成' : '进行中'}
          </Badge>
        </div>

        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
              <span>完成进度</span>
              <span className="font-medium">{completionPercentage}%</span>
            </div>
            <Progress value={completionPercentage} className="h-3" />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="flex items-center justify-center w-12 h-12 bg-blue-100 rounded-full mx-auto mb-2">
                <BookOpen className="h-6 w-6 text-blue-600" />
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {progress.completedSteps.length}/{progress.totalSteps}
              </p>
              <p className="text-xs text-gray-600">已完成步骤</p>
            </div>

            <div className="text-center">
              <div className="flex items-center justify-center w-12 h-12 bg-green-100 rounded-full mx-auto mb-2">
                <Clock className="h-6 w-6 text-green-600" />
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {formatTime(progress.totalTimeSpent)}
              </p>
              <p className="text-xs text-gray-600">学习时长</p>
            </div>

            <div className="text-center">
              <div className="flex items-center justify-center w-12 h-12 bg-purple-100 rounded-full mx-auto mb-2">
                <Award className="h-6 w-6 text-purple-600" />
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {progress.achievements.length}
              </p>
              <p className="text-xs text-gray-600">获得成就</p>
            </div>

            <div className="text-center">
              <div className="flex items-center justify-center w-12 h-12 bg-yellow-100 rounded-full mx-auto mb-2">
                <Bookmark className="h-6 w-6 text-yellow-600" />
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {progress.bookmarks.length}
              </p>
              <p className="text-xs text-gray-600">书签位置</p>
            </div>
          </div>
        </div>
      </Card>

      {/* 步骤详情 */}
      {showDetails && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">步骤详情</h3>

          <div className="space-y-2">
            {tutorialSteps.map((step, index) => {
              const isCompleted = progress.completedSteps.includes(index);
              const isCurrent = index === progress.currentStep;
              const isBookmarked = progress.bookmarks.includes(index);
              const isSkipped = progress.skippedSteps.includes(index);

              return (
                <div
                  key={step.id}
                  className={`flex items-center justify-between p-3 rounded-lg border transition-colors ${
                    isCurrent
                      ? 'border-blue-500 bg-blue-50'
                      : isCompleted
                      ? 'border-green-200 bg-green-50'
                      : isSkipped
                      ? 'border-gray-200 bg-gray-50'
                      : 'border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <div className="flex items-center space-x-2">
                      {isCompleted ? (
                        <CheckCircle className="h-5 w-5 text-green-600" />
                      ) : isSkipped ? (
                        <SkipForward className="h-5 w-5 text-gray-400" />
                      ) : (
                        <Circle className="h-5 w-5 text-gray-400" />
                      )}
                      <span className="text-sm font-medium text-gray-700">
                        步骤 {index + 1}
                      </span>
                    </div>

                    <span className="text-sm text-gray-600">{step.title}</span>

                    <div className="flex items-center space-x-1">
                      {isCurrent && (
                        <Badge variant="default" className="text-xs">
                          当前
                        </Badge>
                      )}
                      {isBookmarked && (
                        <Bookmark className="h-4 w-4 text-yellow-600" />
                      )}
                      {step.isOptional && (
                        <Badge variant="outline" className="text-xs">
                          可选
                        </Badge>
                      )}
                    </div>
                  </div>

                  {onNavigateToStep && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onNavigateToStep(index)}
                      disabled={isCurrent}
                    >
                      {isCurrent ? '当前步骤' : '跳转'}
                    </Button>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* 成就展示 */}
      {progress.achievements.length > 0 && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">获得成就</h3>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {progress.achievements.map((achievement, index) => (
              <div
                key={achievement.id}
                className="flex items-center space-x-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg"
              >
                <div className="text-2xl">{achievement.icon}</div>
                <div>
                  <p className="font-medium text-yellow-800">
                    {achievement.title}
                  </p>
                  <p className="text-xs text-yellow-600">
                    {achievement.description}
                  </p>
                  <p className="text-xs text-yellow-500 mt-1">
                    {new Date(achievement.unlockedAt).toLocaleDateString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* 统计信息 */}
      {stats && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">学习统计</h3>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="flex items-center justify-center w-12 h-12 bg-blue-100 rounded-full mx-auto mb-2">
                <TrendingUp className="h-6 w-6 text-blue-600" />
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {stats.totalTutorials}
              </p>
              <p className="text-xs text-gray-600">总教程数</p>
            </div>

            <div className="text-center">
              <div className="flex items-center justify-center w-12 h-12 bg-green-100 rounded-full mx-auto mb-2">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {stats.completedTutorials}
              </p>
              <p className="text-xs text-gray-600">已完成</p>
            </div>

            <div className="text-center">
              <div className="flex items-center justify-center w-12 h-12 bg-purple-100 rounded-full mx-auto mb-2">
                <Clock className="h-6 w-6 text-purple-600" />
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {formatTime(stats.totalTimeSpent)}
              </p>
              <p className="text-xs text-gray-600">总学习时长</p>
            </div>

            <div className="text-center">
              <div className="flex items-center justify-center w-12 h-12 bg-yellow-100 rounded-full mx-auto mb-2">
                <TrendingUp className="h-6 w-6 text-yellow-600" />
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {Math.round(stats.averageCompletionTime / 60)}分钟
              </p>
              <p className="text-xs text-gray-600">平均完成率</p>
            </div>

            <div className="text-center">
              <div className="flex items-center justify-center w-12 h-12 bg-red-100 rounded-full mx-auto mb-2">
                <Award className="h-6 w-6 text-red-600" />
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {stats.achievementCount}
              </p>
              <p className="text-xs text-gray-600">获得成就</p>
            </div>

            <div className="text-center">
              <div className="flex items-center justify-center w-12 h-12 bg-indigo-100 rounded-full mx-auto mb-2">
                <TrendingUp className="h-6 w-6 text-indigo-600" />
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {stats.currentStreak}
              </p>
              <p className="text-xs text-gray-600">连续学习</p>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}