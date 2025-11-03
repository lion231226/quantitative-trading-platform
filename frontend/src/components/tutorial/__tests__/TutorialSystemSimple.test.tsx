import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock everything first before any imports
jest.mock('@/services/tutorialService', () => ({
  useTutorialService: () => ({
    useTutorial: () => ({
      data: {
        id: 'test-tutorial',
        title: '测试教程',
        description: '这是一个测试教程',
        steps: [
          {
            id: 'step-1',
            title: '第一步',
            content: '测试内容',
            type: 'explanation',
            estimatedTime: 60,
            isOptional: false,
          }
        ]
      },
      isLoading: false,
    }),
    useTutorialProgress: () => ({
      data: {
        currentStep: 0,
        completedSteps: [],
        totalSteps: 1,
        startTime: new Date().toISOString(),
        lastAccessTime: new Date().toISOString(),
        totalTimeSpent: 0,
        achievements: [],
        bookmarks: [],
        skippedSteps: [],
      },
      isLoading: false,
    }),
    useUpdateProgress: () => ({ mutateAsync: jest.fn() }),
    saveUserPreferences: () => ({ mutateAsync: jest.fn() }),
    progressManager: { currentStep: 0 }
  }),
}));

jest.mock('@/utils/tutorialHelpers', () => ({
  getStepNavigation: () => ({ previousStep: null, nextStep: null }),
  generateProgressSummary: () => ({ completedSteps: 0, totalSteps: 1, progressPercentage: 0 }),
  canSkipStep: () => true,
  createTutorialEvent: () => ({ type: 'test', timestamp: Date.now() })
}));

jest.mock('@/components/ui/button', () => ({
  Button: ({ children, ...props }: any) => <button data-testid="button" {...props}>{children}</button>,
}));

jest.mock('@/components/ui/card', () => ({
  Card: ({ children, ...props }: any) => <div data-testid="card" {...props}>{children}</div>,
}));

jest.mock('@/components/ui/badge', () => ({
  Badge: ({ children, ...props }: any) => <span data-testid="badge" {...props}>{children}</span>,
}));

jest.mock('lucide-react', () => ({
  ChevronLeft: () => <div data-testid="chevron-left-icon" />,
  ChevronRight: () => <div data-testid="chevron-right-icon" />,
  X: () => <div data-testid="x-icon" />,
  Bookmark: () => <div data-testid="bookmark-icon" />,
  BookOpen: () => <div data-testid="book-open-icon" />,
  PlayCircle: () => <div data-testid="play-circle-icon" />,
  CheckCircle: () => <div data-testid="check-circle-icon" />,
  Clock: () => <div data-testid="clock-icon" />,
  Award: () => <div data-testid="award-icon" />,
}));

// Mock types
jest.mock('@/types/tutorial.types', () => ({}));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
});

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    {children}
  </QueryClientProvider>
);

describe('TutorialSystem Simple Tests', () => {
  it('should render without crashing', async () => {
    const { default: TutorialSystem } = await import('../TutorialSystem');

    render(
      <Wrapper>
        <TutorialSystem
          tutorialId="test-tutorial"
          isOpen={true}
          onClose={() => {}}
        />
      </Wrapper>
    );

    expect(screen.getByTestId('card')).toBeInTheDocument();
  });
});