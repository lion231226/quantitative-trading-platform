import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Maximize2,
  Minimize2,
  Pause,
  Play,
  RotateCcw,
  Volume2,
  VolumeX,
} from 'lucide-react';
import {
  CompletionCondition,
  TutorialContext,
  TutorialResource,
  TutorialStep,
} from '@/types/tutorial.types';
import { checkCompletionConditions, formatTime } from '@/utils/tutorialHelpers';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface TutorialStepProps {
  step: TutorialStep;
  context: TutorialContext;
  isActive: boolean;
  onComplete: () => void;
  onNext: () => void;
  onPrevious: () => void;
  userPreferences: {
    animationSpeed: number;
    soundEnabled: boolean;
    showHints: boolean;
  };
}

/**
 * 单个教程步骤组件
 * 根据步骤类型渲染不同的内容（解释、动画、交互、测验）
 */
export function TutorialStep({
  step,
  context,
  isActive,
  onComplete,
  onNext,
  onPrevious,
  userPreferences,
}: TutorialStepProps) {
  const [timeSpent, setTimeSpent] = useState(0);
  const [isCompleted, setIsCompleted] = useState(false);
  const [actionsCompleted, setActionsCompleted] = useState<string[]>([]);
  const [animationWatched, setAnimationWatched] = useState(false);
  const [quizPassed, setQuizPassed] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [currentHint, setCurrentHint] = useState<string | null>(null);

  const timerRef = useRef<NodeJS.Timeout>();
  const animationRef = useRef<any>(null);

  // 步骤计时器
  useEffect(() => {
    if (isActive && !isCompleted) {
      timerRef.current = setInterval(() => {
        setTimeSpent((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [isActive, isCompleted]);

  // 检查完成条件
  useEffect(() => {
    if (!step.completionConditions || step.completionConditions.length === 0) {
      setIsCompleted(true);
      return;
    }

    const isComplete = checkCompletionConditions(step.completionConditions, {
      timeSpent,
      actionsCompleted,
      animationWatched,
      quizPassed,
    });

    if (isComplete && !isCompleted) {
      setIsCompleted(true);
    }
  }, [
    timeSpent,
    actionsCompleted,
    animationWatched,
    quizPassed,
    step.completionConditions,
    isCompleted,
  ]);

  // 标记动作完成
  const markActionCompleted = useCallback(
    (actionId: string) => {
      if (!actionsCompleted.includes(actionId)) {
        setActionsCompleted((prev) => [...prev, actionId]);
      }
    },
    [actionsCompleted],
  );

  // 标记动画观看完成
  const markAnimationWatched = useCallback(() => {
    setAnimationWatched(true);
  }, []);

  // 处理测验通过
  const handleQuizPassed = useCallback(() => {
    setQuizPassed(true);
  }, []);

  // 获取提示
  const getHint = useCallback(() => {
    if (step.type === 'explanation') {
      setCurrentHint('仔细阅读内容，理解核心概念');
    } else if (step.type === 'animation') {
      setCurrentHint('观察动画演示，注意关键细节');
    } else if (step.type === 'interactive') {
      setCurrentHint('动手操作，尝试不同的参数设置');
    } else if (step.type === 'quiz') {
      setCurrentHint('回顾前面的内容，选择正确答案');
    }

    setTimeout(() => setCurrentHint(null), 3000);
  }, [step.type]);

  // 渲染步骤类型标识
  const renderStepTypeBadge = () => {
    const typeConfig = {
      explanation: {
        label: '说明',
        variant: 'default' as const,
        color: 'bg-blue-100 text-blue-800',
      },
      animation: {
        label: '动画',
        variant: 'secondary' as const,
        color: 'bg-green-100 text-green-800',
      },
      interactive: {
        label: '交互',
        variant: 'outline' as const,
        color: 'bg-purple-100 text-purple-800',
      },
      quiz: {
        label: '测验',
        variant: 'destructive' as const,
        color: 'bg-red-100 text-red-800',
      },
    };

    const config = typeConfig[step.type];
    return (
      <Badge variant={config.variant} className={config.color}>
        {config.label}
      </Badge>
    );
  };

  // 渲染解释型步骤
  const renderExplanationStep = () => (
    <div className="space-y-6">
      <div className="prose max-w-none">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-4">
            📖 学习内容
          </h3>
          <div className="text-gray-800 leading-relaxed">
            {step.content.split('\n').map((paragraph, index) => (
              <p key={index} className="mb-4">
                {paragraph}
              </p>
            ))}
          </div>
        </div>
      </div>

      {step.resources && step.resources.length > 0 && (
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-3">相关资源</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {step.resources.map((resource, index) => (
              <Card key={index} className="p-4">
                <div className="flex items-center space-x-2">
                  <Badge variant="outline">{resource.type}</Badge>
                  {resource.label && (
                    <span className="text-sm font-medium">
                      {resource.label}
                    </span>
                  )}
                </div>
                {resource.type === 'text' && (
                  <p className="text-sm text-gray-600 mt-2">
                    {resource.content}
                  </p>
                )}
              </Card>
            ))}
          </div>
        </div>
      )}

      <div className="flex justify-center">
        <Button
          onClick={() => {
            markActionCompleted('read_content');
            onComplete();
          }}
          disabled={!isCompleted}
          className="bg-blue-600 hover:bg-blue-700"
        >
          我已理解，继续下一步
        </Button>
      </div>
    </div>
  );

  // 渲染动画型步骤
  const renderAnimationStep = () => (
    <div className="space-y-6">
      <div className="bg-green-50 border border-green-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-green-900 mb-4">
          🎬 动画演示
        </h3>
        <p className="text-gray-800 mb-4">{step.content}</p>
      </div>

      <div className="bg-gray-900 rounded-lg p-8 relative">
        <div className="aspect-video bg-gray-800 rounded-lg flex items-center justify-center">
          {/* 这里将集成Chart.js动画组件 */}
          <div className="text-white text-center">
            <div className="mb-4">
              <div className="w-16 h-16 bg-blue-600 rounded-full mx-auto mb-4 flex items-center justify-center">
                <Play className="h-8 w-8 text-white" />
              </div>
            </div>
            <p className="text-lg mb-2">动画演示区域</p>
            <p className="text-sm text-gray-400">
              这里将显示
              {step.interactionType === 'chart' ? '图表动画' : '原理演示'}
            </p>
          </div>
        </div>

        {/* 动画控制栏 */}
        <div className="absolute bottom-4 left-4 right-4 bg-black bg-opacity-50 rounded-lg p-3">
          <div className="flex items-center justify-between text-white">
            <div className="flex items-center space-x-3">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsPlaying(!isPlaying)}
                className="text-white hover:text-white"
              >
                {isPlaying ? (
                  <Pause className="h-4 w-4" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setAnimationWatched(true);
                  setIsPlaying(false);
                }}
                className="text-white hover:text-white"
              >
                <RotateCcw className="h-4 w-4" />
              </Button>
            </div>

            <div className="flex items-center space-x-3">
              <span className="text-sm">
                速度: {userPreferences.animationSpeed}x
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsFullscreen(!isFullscreen)}
                className="text-white hover:text-white"
              >
                {isFullscreen ? (
                  <Minimize2 className="h-4 w-4" />
                ) : (
                  <Maximize2 className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="text-center text-sm text-gray-600">
        动画播放时长: {formatTime(timeSpent)}
      </div>

      <div className="flex justify-center">
        <Button
          onClick={() => {
            markAnimationWatched();
            onComplete();
          }}
          disabled={!isCompleted}
          className="bg-green-600 hover:bg-green-700"
        >
          观看完成，继续下一步
        </Button>
      </div>
    </div>
  );

  // 渲染交互型步骤
  const renderInteractiveStep = () => (
    <div className="space-y-6">
      <div className="bg-purple-50 border border-purple-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-purple-900 mb-4">
          🎮 交互练习
        </h3>
        <p className="text-gray-800 mb-4">{step.content}</p>
      </div>

      <div className="bg-gray-50 rounded-lg p-6">
        <h4 className="font-medium text-gray-900 mb-4">练习区域</h4>

        {/* 根据交互类型渲染不同的交互组件 */}
        {step.interactionType === 'parameter' && (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              调整参数设置，观察策略表现的变化
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card className="p-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  移动平均线周期
                </label>
                <input
                  type="range"
                  min="5"
                  max="50"
                  defaultValue="20"
                  className="w-full"
                  onChange={() => markActionCompleted('parameter_adjusted')}
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>5</span>
                  <span>20</span>
                  <span>50</span>
                </div>
              </Card>

              <Card className="p-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  移动平均线类型
                </label>
                <select
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  onChange={() => markActionCompleted('parameter_selected')}
                >
                  <option value="SMA">简单移动平均线 (SMA)</option>
                  <option value="EMA">指数移动平均线 (EMA)</option>
                </select>
              </Card>
            </div>
          </div>
        )}

        {step.interactionType === 'chart' && (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              点击图表上的交易信号，了解更多信息
            </p>
            <div className="bg-white border-2 border-dashed border-gray-300 rounded-lg h-64 flex items-center justify-center">
              <p className="text-gray-500">交互式图表组件将在这里显示</p>
            </div>
          </div>
        )}

        {step.interactionType === 'navigation' && (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              探索不同的功能区域，熟悉界面操作
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {['数据面板', '图表区域', '参数设置', '结果分析'].map((area) => (
                <Button
                  key={area}
                  variant="outline"
                  onClick={() => markActionCompleted(`area_${area}`)}
                  className="h-16"
                >
                  {area}
                </Button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="flex justify-center">
        <Button
          onClick={() => {
            markActionCompleted('interactive_completed');
            onComplete();
          }}
          disabled={!isCompleted}
          className="bg-purple-600 hover:bg-purple-700"
        >
          练习完成，继续下一步
        </Button>
      </div>
    </div>
  );

  // 渲染测验型步骤
  const renderQuizStep = () => {
    const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null);
    const [showResult, setShowResult] = useState(false);
    const [isCorrect, setIsCorrect] = useState(false);

    const quizQuestions = [
      {
        question: '什么是金叉信号？',
        options: [
          '短期均线从下方穿越长期均线',
          '长期均线从下方穿越短期均线',
          '两条均线平行移动',
          '均线方向向上',
        ],
        correct: 0,
      },
    ];

    const currentQuestion = quizQuestions[0];

    const handleAnswerSelect = (answerIndex: number) => {
      setSelectedAnswer(answerIndex);
      setShowResult(true);
      setIsCorrect(answerIndex === currentQuestion.correct);
      markActionCompleted('quiz_answered');
    };

    const handleQuizComplete = () => {
      if (isCorrect) {
        handleQuizPassed();
        onComplete();
      }
    };

    return (
      <div className="space-y-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-red-900 mb-4">
            📝 知识测验
          </h3>
          <p className="text-gray-800 mb-4">{step.content}</p>
        </div>

        <Card className="p-6">
          <h4 className="font-medium text-gray-900 mb-4">
            {currentQuestion.question}
          </h4>

          <div className="space-y-3">
            {currentQuestion.options.map((option, index) => (
              <Button
                key={index}
                variant={selectedAnswer === index ? 'default' : 'outline'}
                className={`w-full text-left justify-start h-auto p-4 ${
                  showResult && index === currentQuestion.correct
                    ? 'bg-green-100 border-green-500 text-green-800'
                    : showResult && selectedAnswer === index && !isCorrect
                      ? 'bg-red-100 border-red-500 text-red-800'
                      : ''
                }`}
                onClick={() => handleAnswerSelect(index)}
                disabled={showResult}
              >
                <span className="flex items-center">
                  <span className="w-6 h-6 rounded-full border-2 border-current flex items-center justify-center mr-3 text-sm">
                    {String.fromCharCode(65 + index)}
                  </span>
                  {option}
                </span>
              </Button>
            ))}
          </div>

          {showResult && (
            <div
              className={`mt-4 p-4 rounded-lg ${
                isCorrect
                  ? 'bg-green-50 text-green-800'
                  : 'bg-red-50 text-red-800'
              }`}
            >
              <p className="font-medium">
                {isCorrect ? '✅ 回答正确！' : '❌ 回答错误'}
              </p>
              {!isCorrect && (
                <p className="text-sm mt-1">
                  正确答案是：{currentQuestion.options[currentQuestion.correct]}
                </p>
              )}
            </div>
          )}
        </Card>

        <div className="flex justify-center">
          <Button
            onClick={handleQuizComplete}
            disabled={!isCorrect || !isCompleted}
            className="bg-red-600 hover:bg-red-700"
          >
            测验通过，继续下一步
          </Button>
        </div>
      </div>
    );
  };

  // 根据步骤类型渲染内容
  const renderStepContent = () => {
    switch (step.type) {
      case 'explanation':
        return renderExplanationStep();
      case 'animation':
        return renderAnimationStep();
      case 'interactive':
        return renderInteractiveStep();
      case 'quiz':
        return renderQuizStep();
      default:
        return (
          <div className="text-center text-gray-500">
            未知步骤类型: {step.type}
          </div>
        );
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* 步骤头部 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          {renderStepTypeBadge()}
          <h2 className="text-xl font-semibold text-gray-900">{step.title}</h2>
        </div>

        <div className="flex items-center space-x-3">
          {step.estimatedTime && (
            <span className="text-sm text-gray-500">
              ⏱️ {formatTime(step.estimatedTime)}
            </span>
          )}

          {userPreferences.showHints && (
            <Button variant="ghost" size="sm" onClick={getHint}>
              💡 提示
            </Button>
          )}
        </div>
      </div>

      {/* 提示信息 */}
      {currentHint && (
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-sm text-yellow-800">{currentHint}</p>
        </div>
      )}

      {/* 进度指示器 */}
      <div className="mb-6">
        <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
          <span>学习进度</span>
          <span>{isCompleted ? '已完成' : '进行中'}</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-300 ${
              isCompleted ? 'bg-green-600' : 'bg-blue-600'
            }`}
            style={{
              width: `${isCompleted ? 100 : Math.min(95, (timeSpent / (step.estimatedTime || 60)) * 100)}%`,
            }}
          ></div>
        </div>
      </div>

      {/* 步骤内容 */}
      <div className="flex-1 overflow-y-auto">{renderStepContent()}</div>

      {/* 导航控制 */}
      <div className="flex items-center justify-between mt-6 pt-4 border-t">
        <Button
          variant="outline"
          onClick={onPrevious}
          disabled={context.progress.currentStep === 0}
        >
          上一步
        </Button>

        <div className="text-sm text-gray-500">
          {context.progress.currentStep + 1} / {context.tutorial.steps.length}
        </div>

        {isCompleted ? (
          <Button onClick={onNext} className="bg-blue-600 hover:bg-blue-700">
            下一步
          </Button>
        ) : (
          <div className="text-sm text-gray-500">完成当前步骤后继续</div>
        )}
      </div>
    </div>
  );
}
