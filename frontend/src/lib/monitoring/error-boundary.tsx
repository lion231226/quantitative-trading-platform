/**
 * Enhanced Error Boundary Component
 * Comprehensive error handling with Sentry integration and user feedback
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { monitoringService } from '@/services/monitoringService';
import { sentryClient } from './sentry-client';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  enableUserFeedback?: boolean;
  showRetryButton?: boolean;
  maxRetries?: number;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  retryCount: number;
  showFeedback: boolean;
  feedbackSubmitted: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  private maxRetries: number;

  constructor(props: Props) {
    super(props);

    this.maxRetries = props.maxRetries || 3;
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: 0,
      showFeedback: false,
      feedbackSubmitted: false,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Update state with error information
    this.setState({
      error,
      errorInfo,
    });

    // Capture error in Sentry with detailed context
    const eventId = this.captureErrorWithSentry(error, errorInfo);

    // Track error context
    this.trackErrorContext(error, errorInfo, eventId);

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Log error for debugging
    console.group('🚨 Error Boundary - Error Caught');
    console.error('Error:', error);
    console.error('Error Info:', errorInfo);
    console.groupEnd();
  }

  /**
   * Capture error in Sentry with enhanced context
   */
  private captureErrorWithSentry(error: Error, errorInfo: ErrorInfo): string | undefined {
    try {
      const eventId = sentryClient.captureError(error, {
        tags: {
          component: 'ErrorBoundary',
          type: 'react-error',
          retryCount: this.state.retryCount.toString(),
        },
        extra: {
          componentStack: errorInfo.componentStack,
          errorBoundary: true,
          retryCount: this.state.retryCount,
          maxRetries: this.maxRetries,
        },
      });

      return eventId;
    } catch (sentryError) {
      console.warn('Failed to capture error in Sentry:', sentryError);
      return undefined;
    }
  }

  /**
   * Track error context and user journey
   */
  private trackErrorContext(error: Error, errorInfo: ErrorInfo, eventId?: string): void {
    // Add breadcrumb for error tracking
    monitoringService.addBreadcrumb({
      category: 'error',
      message: 'React error boundary caught error',
      level: 'error',
      data: {
        errorMessage: error.message,
        errorType: error.name,
        componentStack: errorInfo.componentStack,
        eventId,
      },
    });

    // Track user context if available
    try {
      const userInfo = this.getUserContext();
      if (userInfo) {
        monitoringService.setUser(userInfo);
      }
    } catch (e) {
      // Ignore user context errors
    }
  }

  /**
   * Get user context for error reporting
   */
  private getUserContext(): any {
    // This would integrate with your authentication system
    return {
      // Add user information here
      // id: user?.id,
      // email: user?.email,
      // role: user?.role,
    };
  }

  /**
   * Handle retry action
   */
  private handleRetry = (): void => {
    if (this.state.retryCount < this.maxRetries) {
      this.setState(prevState => ({
        hasError: false,
        error: null,
        errorInfo: null,
        retryCount: prevState.retryCount + 1,
        showFeedback: false,
        feedbackSubmitted: false,
      }));

      // Track retry attempt
      monitoringService.addBreadcrumb({
        category: 'user',
        message: 'Error boundary retry attempted',
        level: 'info',
        data: {
          retryCount: this.state.retryCount + 1,
          maxRetries: this.maxRetries,
        },
      });

      // Track retry in Sentry
      sentryClient.captureMessage(
        `Error boundary retry attempt ${this.state.retryCount + 1}/${this.maxRetries}`,
        'info',
        {
          tags: {
            component: 'ErrorBoundary',
            action: 'retry',
          },
        }
      );
    }
  };

  /**
   * Handle user feedback toggle
   */
  private toggleFeedback = (): void => {
    this.setState(prevState => ({
      showFeedback: !prevState.showFeedback,
    }));
  };

  /**
   * Handle user feedback submission
   */
  private handleFeedbackSubmit = (feedback: { email?: string; comments: string }): void => {
    try {
      const eventId = sentryClient.captureUserFeedback({
        email: feedback.email,
        comments: feedback.comments,
        name: 'Error Boundary User',
        eventId: this.state.errorInfo ? 'error-boundary-event' : undefined,
      });

      this.setState({
        feedbackSubmitted: true,
        showFeedback: false,
      });

      // Track feedback submission
      monitoringService.addBreadcrumb({
        category: 'user',
        message: 'User feedback submitted',
        level: 'info',
        data: {
          hasEmail: !!feedback.email,
          commentLength: feedback.comments.length,
          eventId,
        },
      });

    } catch (error) {
      console.warn('Failed to submit user feedback:', error);
    }
  };

  /**
   * Render fallback UI when error occurs
   */
  private renderFallbackUI(): ReactNode {
    if (this.props.fallback) {
      return this.props.fallback;
    }

    const { error, errorInfo, retryCount, showFeedback, feedbackSubmitted } = this.state;
    const canRetry = retryCount < this.maxRetries;

    return (
      <div className=\"min-h-screen flex items-center justify-center bg-gray-50 px-4\">
        <div className=\"max-w-md w-full bg-white rounded-lg shadow-lg p-6 text-center\">
          <div className=\"mb-4\">
            <div className=\"mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4\">
              <svg
                className=\"h-6 w-6 text-red-600\"
                fill=\"none\"
                viewBox=\"0 0 24 24\"
                stroke=\"currentColor\"
              >
                <path
                  strokeLinecap=\"round\"
                  strokeLinejoin=\"round\"
                  strokeWidth={2}
                  d=\"M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.314 16.5c-.77.833.192 2.5 1.732 2.5z\"
                />
              </svg>
            </div>
            <h2 className=\"text-xl font-semibold text-gray-900 mb-2\">
              应用程序遇到错误
            </h2>
            <p className=\"text-gray-600 mb-4\">
              抱歉，应用程序遇到了意外错误。我们已经记录了这个问题，正在努力修复。
            </p>
          </div>

          {error && (
            <div className=\"mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-left\">
              <p className=\"text-sm font-medium text-red-800 mb-1\">
                错误详情：
              </p>
              <p className=\"text-xs text-red-700 font-mono break-all\">
                {error.message}
              </p>
              {retryCount > 0 && (
                <p className=\"text-xs text-red-600 mt-2\">
                  重试次数：{retryCount}/{this.maxRetries}
                </p>
              )}
            </div>
          )}

          <div className=\"space-y-3\">
            {this.props.showRetryButton && canRetry && (
              <button
                onClick={this.handleRetry}
                className=\"w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors\"
              >
                重试 ({this.maxRetries - retryCount} 次机会剩余)
              </button>
            )}

            {this.props.enableUserFeedback && !showFeedback && !feedbackSubmitted && (
              <button
                onClick={this.toggleFeedback}
                className=\"w-full bg-gray-600 hover:bg-gray-700 text-white font-medium py-2 px-4 rounded-md transition-colors\"
              >
                报告问题
              </button>
            )}

            {showFeedback && (
              <FeedbackForm
                onSubmit={this.handleFeedbackSubmit}
                onCancel={this.toggleFeedback}
              />
            )}

            {feedbackSubmitted && (
              <div className=\"p-3 bg-green-50 border border-green-200 rounded-md\">
                <p className=\"text-sm text-green-800\">
                  ✅ 感谢您的反馈！我们会尽快处理这个问题。
                </p>
              </div>
            )}

            <button
              onClick={() => window.location.reload()}
              className=\"w-full border border-gray-300 hover:bg-gray-50 text-gray-700 font-medium py-2 px-4 rounded-md transition-colors\"
            >
              刷新页面
            </button>
          </div>
        </div>
      </div>
    );
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return this.renderFallbackUI();
    }

    return this.props.children;
  }
}

/**
 * User feedback form component
 */
interface FeedbackFormProps {
  onSubmit: (feedback: { email?: string; comments: string }) => void;
  onCancel: () => void;
}

const FeedbackForm: React.FC<FeedbackFormProps> = ({ onSubmit, onCancel }) => {
  const [email, setEmail] = React.useState('');
  const [comments, setComments] = React.useState('');
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (comments.trim()) {
      setIsSubmitting(true);
      try {
        await onSubmit({ email: email.trim() || undefined, comments: comments.trim() });
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  return (
    <form onSubmit={handleSubmit} className=\"space-y-3 p-3 bg-gray-50 border border-gray-200 rounded-md\">
      <div>
        <label htmlFor=\"email\" className=\"block text-sm font-medium text-gray-700 mb-1\">
          邮箱地址 (可选)
        </label>
        <input
          type=\"email\"
          id=\"email\"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className=\"w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500\"
          placeholder=\"your@email.com\"
        />
      </div>

      <div>
        <label htmlFor=\"comments\" className=\"block text-sm font-medium text-gray-700 mb-1\">
          问题描述 *
        </label>
        <textarea
          id=\"comments\"
          value={comments}
          onChange={(e) => setComments(e.target.value)}
          rows={4}
          className=\"w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500\"
          placeholder=\"请描述您遇到的问题...\"
          required
        />
      </div>

      <div className=\"flex space-x-2\">
        <button
          type=\"submit\"
          disabled={isSubmitting || !comments.trim()}
          className=\"flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium py-2 px-4 rounded-md transition-colors\"
        >
          {isSubmitting ? '提交中...' : '提交反馈'}
        </button>
        <button
          type=\"button\"
          onClick={onCancel}
          className=\"flex-1 border border-gray-300 hover:bg-gray-50 text-gray-700 font-medium py-2 px-4 rounded-md transition-colors\"
        >
          取消
        </button>
      </div>
    </form>
  );
};

export default ErrorBoundary;