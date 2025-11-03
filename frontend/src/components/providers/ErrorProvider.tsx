'use client';

import ErrorBoundary from '@/components/ui/error-boundary';

interface ErrorProviderProps {
  children: React.ReactNode
}

export function ErrorProvider({ children }: ErrorProviderProps) {
  return (
    <ErrorBoundary>
      {children}
    </ErrorBoundary>
  );
}
