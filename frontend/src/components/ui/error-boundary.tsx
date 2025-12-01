'use client';

import React from 'react';
import { Button } from './button';

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: React.ErrorInfo;
}

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<{ error: Error; reset: () => void }>;
}

class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({
      error,
      errorInfo,
    });

    // 记录错误到控制台
    console.error('ErrorBoundary caught an error:', error, errorInfo);

    // 这里可以添加错误报告服务
    this.logErrorToService(error, errorInfo);
  }

  logErrorToService = (error: Error, errorInfo: React.ErrorInfo) => {
    try {
      // 这里可以集成错误报告服务，如 Sentry
      const errorData = {
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href,
      };

      // 开发环境下直接输出到控制台
      if (process.env.NODE_ENV === 'development') {
        console.error('Error Report:', errorData);
      } else {
        // 生产环境下可以发送到错误监控服务
        // 例如：Sentry.captureException(error, { extra: errorInfo })
      }
    } catch (logError) {
      console.error('Failed to log error:', logError);
    }
  };

  handleReset = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  };

  render() {
    if (this.state.hasError) {
      // 如果提供了自定义fallback组件，使用它
      if (this.props.fallback) {
        const FallbackComponent = this.props.fallback;
        return (
          <FallbackComponent
            error={this.state.error!}
            reset={this.handleReset}
          />
        );
      }

      // 默认错误UI
      return (
        <ErrorFallback error={this.state.error!} reset={this.handleReset} />
      );
    }

    return this.props.children;
  }
}

interface ErrorFallbackProps {
  error: Error;
  reset: () => void;
}

function ErrorFallback({ error, reset }: ErrorFallbackProps) {
  return (
    <div className="min-h-[200px] flex items-center justify-center p-4">
      <div className="text-center max-w-md">
        <div className="text-6xl mb-4">😅</div>
        <h2 className="text-2xl font-semibold text-gray-900 mb-2">
          哎呀，出现了一些问题
        </h2>
        <p className="text-gray-600 mb-6">
          很抱歉，页面遇到了意外错误。请尝试刷新页面或稍后再试。
        </p>

        {process.env.NODE_ENV === 'development' && (
          <details className="mb-6 text-left">
            <summary className="cursor-pointer text-sm text-gray-500 hover:text-gray-700 mb-2">
              查看错误详情 (仅开发环境)
            </summary>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-xs text-left overflow-auto max-h-40">
              <div className="font-semibold mb-2">错误信息:</div>
              <div className="text-red-600 mb-3">{error.message}</div>
              {error.stack && (
                <>
                  <div className="font-semibold mb-2">堆栈跟踪:</div>
                  <pre className="whitespace-pre-wrap text-gray-600">
                    {error.stack}
                  </pre>
                </>
              )}
            </div>
          </details>
        )}

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button onClick={reset} variant="default">
            重试
          </Button>
          <Button onClick={() => window.location.reload()} variant="outline">
            刷新页面
          </Button>
        </div>

        <div className="mt-6 text-xs text-gray-500">
          如果问题持续存在，请联系技术支持。
        </div>
      </div>
    </div>
  );
}

// Hook形式的错误边界
export function useErrorHandler() {
  const [error, setError] = React.useState<Error | null>(null);

  const resetError = React.useCallback(() => {
    setError(null);
  }, []);

  const handleError = React.useCallback((error: Error) => {
    console.error('Error caught by error handler:', error);
    setError(error);
  }, []);

  // 抛出错误会被ErrorBoundary捕获
  React.useEffect(() => {
    if (error) {
      // 使用 setTimeout 避免同步抛出错误导致的无限循环
      setTimeout(() => {
        throw error;
      }, 0);
    }
  }, [error]);

  return { handleError, resetError };
}

// 异步错误边界组件
interface AsyncErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<{ error: Error; reset: () => void }>;
}

export function AsyncErrorBoundary({
  children,
  fallback,
}: AsyncErrorBoundaryProps) {
  const { handleError, resetError } = useErrorHandler();

  // 包装异步操作的Hook
  const withErrorHandling = React.useCallback(
    async <T,>(asyncFn: () => Promise<T>): Promise<T | null> => {
      try {
        return await asyncFn();
      } catch (error) {
        handleError(error as Error);
        return null;
      }
    },
    [handleError],
  );

  return (
    <ErrorBoundary fallback={fallback}>
      <ErrorBoundaryContext.Provider value={{ withErrorHandling, resetError }}>
        {children}
      </ErrorBoundaryContext.Provider>
    </ErrorBoundary>
  );
}

// Context for error handling
const ErrorBoundaryContext = React.createContext<{
  withErrorHandling: <T>(asyncFn: () => Promise<T>) => Promise<T | null>;
  resetError: () => void;
}>({
  withErrorHandling: async () => null,
  resetError: () => {},
});

export const useErrorBoundary = () => {
  const context = React.useContext(ErrorBoundaryContext);
  if (!context) {
    throw new Error('useErrorBoundary must be used within AsyncErrorBoundary');
  }
  return context;
};

export default ErrorBoundary;
