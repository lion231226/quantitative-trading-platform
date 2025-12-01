'use client';

import React, {
  memo,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { UXError, UserFeedback } from '@/types/ux.types';

// 错误严重级别枚举
export type ErrorSeverity = 'low' | 'medium' | 'high' | 'critical';

// 错误类型枚举
export type ErrorType =
  | 'javascript_error'
  | 'network_error'
  | 'api_error'
  | 'render_error'
  | 'user_error'
  | 'validation_error'
  | 'permission_error'
  | 'timeout_error';

// 增强的错误边界组件
interface EnhancedErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<{
    error: Error;
    errorInfo: React.ErrorInfo;
    reset: () => void;
  }>;
  onError?: (
    error: Error,
    errorInfo: React.ErrorInfo,
    errorData: UXError,
  ) => void;
  enableErrorReporting?: boolean;
  maxRetries?: number;
  retryDelay?: number;
}

interface EnhancedErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: React.ErrorInfo;
  retryCount: number;
  errorId?: string;
}

export const EnhancedErrorBoundary = memo<EnhancedErrorBoundaryProps>(
  ({
    children,
    fallback,
    onError,
    enableErrorReporting = true,
    maxRetries = 3,
    retryDelay = 1000,
  }) => {
    const [state, setState] = useState<EnhancedErrorBoundaryState>({
      hasError: false,
      retryCount: 0,
    });

    const retryTimeoutRef = useRef<NodeJS.Timeout>();

    const generateErrorId = useCallback(() => {
      return `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }, []);

    const createUXError = useCallback(
      (
        error: Error,
        errorInfo: React.ErrorInfo,
        errorType: ErrorType = 'render_error',
      ): UXError => {
        const errorId = generateErrorId();

        return {
          id: errorId,
          timestamp: new Date().toISOString(),
          componentName:
            errorInfo.componentStack.split('\n')[1]?.trim() || 'Unknown',
          errorType,
          message: error.message,
          stack: error.stack,
          userAgent: navigator.userAgent,
          pagePath: window.location.pathname,
          sessionId: getSessionId(),
          metadata: {
            componentStack: errorInfo.componentStack,
            retryCount: state.retryCount,
            url: window.location.href,
            referrer: document.referrer,
          },
          resolved: false,
        };
      },
      [generateErrorId, state.retryCount],
    );

    const getSessionId = useCallback(() => {
      let sessionId = sessionStorage.getItem('ux_session_id');
      if (!sessionId) {
        sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        sessionStorage.setItem('ux_session_id', sessionId);
      }
      return sessionId;
    }, []);

    const reportError = useCallback(
      async (errorData: UXError) => {
        if (!enableErrorReporting) return;

        try {
          // 这里可以发送到错误监控服务如Sentry
          console.error('[Error Reporting]', errorData);

          // 模拟API调用
          if (process.env.NODE_ENV === 'production') {
            // await errorReportingService.report(errorData);
          }
        } catch (reportingError) {
          console.error('Failed to report error:', reportingError);
        }
      },
      [enableErrorReporting],
    );

    const handleError = useCallback(
      (
        error: Error,
        errorInfo: React.ErrorInfo,
        errorType: ErrorType = 'render_error',
      ) => {
        const errorData = createUXError(error, errorInfo, errorType);

        setState((prev) => ({
          ...prev,
          hasError: true,
          error,
          errorInfo,
          errorId: errorData.id,
        }));

        // 报告错误
        reportError(errorData);

        // 通知外部错误处理器
        onError?.(error, errorInfo, errorData);
      },
      [createUXError, reportError, onError],
    );

    const handleReset = useCallback(() => {
      if (state.retryCount >= maxRetries) {
        console.warn('Max retries reached, not attempting to recover');
        return;
      }

      setState((prev) => ({
        ...prev,
        hasError: false,
        error: undefined,
        errorInfo: undefined,
        retryCount: prev.retryCount + 1,
      }));
    }, [state.retryCount, maxRetries]);

    // 自动重试逻辑
    useEffect(() => {
      if (state.hasError && state.retryCount < maxRetries) {
        retryTimeoutRef.current = setTimeout(
          () => {
            handleReset();
          },
          retryDelay * Math.pow(2, state.retryCount),
        ); // 指数退避

        return () => {
          if (retryTimeoutRef.current) {
            clearTimeout(retryTimeoutRef.current);
          }
        };
      }
    }, [state.hasError, state.retryCount, maxRetries, retryDelay, handleReset]);

    // 处理同步错误
    const staticGetDerivedStateFromError = (
      error: Error,
    ): Partial<EnhancedErrorBoundaryState> => ({
      hasError: true,
      error,
    });

    // 处理异步错误和错误报告
    const staticComponentDidCatch = (
      error: Error,
      errorInfo: React.ErrorInfo,
    ) => {
      handleError(error, errorInfo);
    };

    // 使用class组件来兼容React的错误边界
    return (
      <ErrorBoundaryClass
        state={state}
        setState={setState}
        fallback={fallback}
        handleError={handleError}
        handleReset={handleReset}
        maxRetries={maxRetries}
      >
        {children}
      </ErrorBoundaryClass>
    );
  },
);

EnhancedErrorBoundary.displayName = 'EnhancedErrorBoundary';

// Class组件用于实际的错误边界
class ErrorBoundaryClass extends React.Component<
  {
    state: EnhancedErrorBoundaryState;
    setState: React.Dispatch<React.SetStateAction<EnhancedErrorBoundaryState>>;
    fallback?: React.ComponentType<{
      error: Error;
      errorInfo: React.ErrorInfo;
      reset: () => void;
    }>;
    handleError: (error: Error, errorInfo: React.ErrorInfo) => void;
    handleReset: () => void;
    maxRetries: number;
    children: React.ReactNode;
  },
  EnhancedErrorBoundaryState
> {
  constructor(props: any) {
    super(props);
    this.state = props.state;
  }

  static getDerivedStateFromError(
    error: Error,
  ): Partial<EnhancedErrorBoundaryState> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.props.handleError(error, errorInfo);
  }

  componentDidUpdate(prevProps: any) {
    if (prevProps.state !== this.props.state) {
      this.setState(this.props.state);
    }
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        const FallbackComponent = this.props.fallback;
        return (
          <FallbackComponent
            error={this.state.error!}
            errorInfo={this.state.errorInfo!}
            reset={this.props.handleReset}
          />
        );
      }

      return (
        <DefaultErrorFallback
          error={this.state.error!}
          errorInfo={this.state.errorInfo!}
          reset={this.props.handleReset}
          retryCount={this.state.retryCount}
          maxRetries={this.props.maxRetries}
        />
      );
    }

    return this.props.children;
  }
}

// 默认错误回退组件
interface DefaultErrorFallbackProps {
  error: Error;
  errorInfo: React.ErrorInfo;
  reset: () => void;
  retryCount: number;
  maxRetries: number;
}

function DefaultErrorFallback({
  error,
  errorInfo,
  reset,
  retryCount,
  maxRetries,
}: DefaultErrorFallbackProps) {
  const canRetry = retryCount < maxRetries;

  return (
    <div className="min-h-[400px] flex items-center justify-center p-4">
      <Card className="max-w-2xl w-full p-6">
        <div className="text-center">
          <div className="text-6xl mb-4">😅</div>

          <Alert className="mb-6" variant="destructive">
            <AlertTitle className="text-lg font-semibold mb-2">
              应用程序遇到错误
            </AlertTitle>
            <AlertDescription className="text-sm text-gray-600">
              很抱歉，应用程序遇到了意外错误。我们已经记录了这个问题，正在努力修复。
            </AlertDescription>
          </Alert>

          <div className="flex flex-col sm:flex-row gap-3 justify-center mb-6">
            {canRetry && (
              <Button onClick={reset} variant="default">
                重试 ({retryCount + 1}/{maxRetries})
              </Button>
            )}
            <Button onClick={() => window.location.reload()} variant="outline">
              刷新页面
            </Button>
            <Button onClick={() => window.history.back()} variant="ghost">
              返回上页
            </Button>
          </div>

          {process.env.NODE_ENV === 'development' && (
            <details className="text-left">
              <summary className="cursor-pointer text-sm text-gray-500 hover:text-gray-700 mb-2">
                查看错误详情 (仅开发环境)
              </summary>
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-xs text-left overflow-auto max-h-60">
                <div className="font-semibold mb-2">错误信息:</div>
                <div className="text-red-600 mb-3 break-all">
                  {error.message}
                </div>

                {error.stack && (
                  <>
                    <div className="font-semibold mb-2">堆栈跟踪:</div>
                    <pre className="whitespace-pre-wrap text-gray-600 mb-3 text-xs">
                      {error.stack}
                    </pre>
                  </>
                )}

                {errorInfo.componentStack && (
                  <>
                    <div className="font-semibold mb-2">组件堆栈:</div>
                    <pre className="whitespace-pre-wrap text-gray-600 text-xs">
                      {errorInfo.componentStack}
                    </pre>
                  </>
                )}
              </div>
            </details>
          )}

          <div className="text-xs text-gray-500">
            错误ID: {error.message.slice(0, 20)}...
            {Date.now().toString().slice(-6)}
          </div>
        </div>
      </Card>
    </div>
  );
}

// 网络错误处理组件
interface NetworkErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<{ error: Error; reset: () => void }>;
  onNetworkError?: (error: Error) => void;
}

export function NetworkErrorBoundary({
  children,
  fallback,
  onNetworkError,
}: NetworkErrorBoundaryProps) {
  const [networkError, setNetworkError] = useState<Error | null>(null);

  useEffect(() => {
    const handleOnline = () => setNetworkError(null);
    const handleOffline = () => {
      const error = new Error('网络连接已断开');
      setNetworkError(error);
      onNetworkError?.(error);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [onNetworkError]);

  const handleReset = useCallback(() => {
    setNetworkError(null);
  }, []);

  if (networkError) {
    if (fallback) {
      const FallbackComponent = fallback;
      return <FallbackComponent error={networkError} reset={handleReset} />;
    }

    return (
      <div className="min-h-[200px] flex items-center justify-center p-4">
        <Card className="max-w-md w-full p-6 text-center">
          <div className="text-4xl mb-4">📡</div>
          <h3 className="text-lg font-semibold mb-2">网络连接问题</h3>
          <p className="text-gray-600 mb-4">{networkError.message}</p>
          <Button onClick={handleReset} variant="default">
            重试
          </Button>
        </Card>
      </div>
    );
  }

  return <>{children}</>;
}

// 用户反馈组件
interface UserFeedbackProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (
    feedback: Omit<UserFeedback, 'id' | 'timestamp' | 'sessionId'>,
  ) => void;
  defaultErrorInfo?: string;
}

export function UserFeedbackModal({
  isOpen,
  onClose,
  onSubmit,
  defaultErrorInfo,
}: UserFeedbackProps) {
  const [feedback, setFeedback] = useState({
    feedbackType: 'bug_report' as UserFeedback['feedbackType'],
    category: 'functionality' as UserFeedback['category'],
    title: '',
    description: '',
    email: '',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!feedback.title.trim() || !feedback.description.trim()) {
        return;
      }

      setIsSubmitting(true);

      try {
        await onSubmit({
          ...feedback,
          pagePath: window.location.pathname,
          userAgent: navigator.userAgent,
          metadata: {
            errorInfo: defaultErrorInfo,
            timestamp: new Date().toISOString(),
          },
          status: 'pending',
          priority: feedback.category === 'error' ? 'high' : 'medium',
        });

        setFeedback({
          feedbackType: 'bug_report',
          category: 'functionality',
          title: '',
          description: '',
          email: '',
        });

        onClose();
      } catch (error) {
        console.error('Failed to submit feedback:', error);
      } finally {
        setIsSubmitting(false);
      }
    },
    [feedback, defaultErrorInfo, onSubmit, onClose],
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <Card className="max-w-lg w-full p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">用户反馈</h3>
          <Button variant="ghost" size="sm" onClick={onClose}>
            ✕
          </Button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">反馈类型</label>
            <select
              value={feedback.feedbackType}
              onChange={(e) =>
                setFeedback((prev) => ({
                  ...prev,
                  feedbackType: e.target.value as any,
                }))
              }
              className="w-full p-2 border rounded-md"
            >
              <option value="bug_report">问题报告</option>
              <option value="feature_request">功能请求</option>
              <option value="general_feedback">一般反馈</option>
              <option value="usability_issue">可用性问题</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">分类</label>
            <select
              value={feedback.category}
              onChange={(e) =>
                setFeedback((prev) => ({
                  ...prev,
                  category: e.target.value as any,
                }))
              }
              className="w-full p-2 border rounded-md"
            >
              <option value="functionality">功能问题</option>
              <option value="performance">性能问题</option>
              <option value="ui_ux">界面问题</option>
              <option value="error">错误报告</option>
              <option value="other">其他</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">标题</label>
            <input
              type="text"
              value={feedback.title}
              onChange={(e) =>
                setFeedback((prev) => ({ ...prev, title: e.target.value }))
              }
              className="w-full p-2 border rounded-md"
              placeholder="简要描述问题"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">详细描述</label>
            <textarea
              value={feedback.description}
              onChange={(e) =>
                setFeedback((prev) => ({
                  ...prev,
                  description: e.target.value,
                }))
              }
              className="w-full p-2 border rounded-md h-24"
              placeholder="请详细描述您遇到的问题或建议"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              邮箱（可选）
            </label>
            <input
              type="email"
              value={feedback.email}
              onChange={(e) =>
                setFeedback((prev) => ({ ...prev, email: e.target.value }))
              }
              className="w-full p-2 border rounded-md"
              placeholder="如需回复请留下邮箱"
            />
          </div>

          {defaultErrorInfo && (
            <div className="bg-gray-50 p-3 rounded-md">
              <p className="text-sm text-gray-600">
                错误信息已自动附加到反馈中
              </p>
            </div>
          )}

          <div className="flex gap-3 pt-4">
            <Button
              type="submit"
              disabled={
                isSubmitting ||
                !feedback.title.trim() ||
                !feedback.description.trim()
              }
              className="flex-1"
            >
              {isSubmitting ? '提交中...' : '提交反馈'}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="flex-1"
            >
              取消
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

// 错误通知组件
interface ErrorNotificationProps {
  error: UXError;
  onDismiss: () => void;
  onReport?: () => void;
}

export function ErrorNotification({
  error,
  onDismiss,
  onReport,
}: ErrorNotificationProps) {
  const severity = useMemo(() => {
    switch (error.errorType) {
      case 'javascript_error':
      case 'render_error':
        return 'high';
      case 'network_error':
      case 'api_error':
        return 'medium';
      default:
        return 'low';
    }
  }, [error.errorType]);

  const severityColors = {
    low: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    medium: 'bg-orange-100 text-orange-800 border-orange-200',
    high: 'bg-red-100 text-red-800 border-red-200',
    critical: 'bg-red-200 text-red-900 border-red-300',
  };

  return (
    <Alert className={cn('mb-4', severityColors[severity])}>
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <AlertTitle className="text-sm font-medium mb-1">
            {error.componentName} 发生错误
          </AlertTitle>
          <AlertDescription className="text-sm">
            {error.message}
          </AlertDescription>
          <div className="flex items-center gap-2 mt-2">
            <Badge variant="outline" className="text-xs">
              {error.errorType}
            </Badge>
            <span className="text-xs text-gray-500">
              {new Date(error.timestamp).toLocaleTimeString()}
            </span>
          </div>
        </div>
        <div className="flex gap-2 ml-4">
          {onReport && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onReport}
              className="text-xs"
            >
              报告
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={onDismiss}
            className="text-xs"
          >
            ✕
          </Button>
        </div>
      </div>
    </Alert>
  );
}

export default {
  EnhancedErrorBoundary,
  NetworkErrorBoundary,
  UserFeedbackModal,
  ErrorNotification,
};
