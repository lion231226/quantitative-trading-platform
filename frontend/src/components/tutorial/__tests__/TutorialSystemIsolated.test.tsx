import React from 'react';
import { render, screen } from '@testing-library/react';
import TutorialSystem from '../TutorialSystem';

// Mock all dependencies
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

jest.mock('@/components/ui/button', () => ({
  Button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
}));

jest.mock('@/components/ui/card', () => ({
  Card: ({ children, ...props }: any) => <div {...props}>{children}</div>,
}));

jest.mock('@/components/ui/badge', () => ({
  Badge: ({ children, ...props }: any) => <span {...props}>{children}</span>,
}));

jest.mock('@/services/tutorialService', () => ({
  useTutorialService: () => ({
    useTutorial: () => ({
      data: {
        id: 'test-tutorial',
        title: '测试教程',
        description: '这是一个测试教程',
        category: 'test',
        difficulty: 'beginner',
        estimatedDuration: 10,
        tags: ['test'],
        steps: [
          {
            id: 'step-1',
            title: '测试步骤',
            content: '测试内容',
            type: 'explanation' as const,
            estimatedTime: 60,
            isOptional: false,
          }
        ],
      },
      isLoading: false,
      error: null,
    }),
    useTutorialProgress: () => ({
      data: {
        currentStep: 0,
        completedSteps: [],
        totalSteps: 1,
        startTime: new Date().toISOString(),
        lastAccessTime: new Date().toISOString(),
      },
      isLoading: false,
      error: null,
    }),
    useUpdateProgress: () => ({
      mutateAsync: jest.fn(),
      isPending: false,
      error: null,
    }),
    saveUserPreferences: jest.fn(),
    progressManager: {
      saveProgress: jest.fn(),
      loadProgress: jest.fn(),
      clearProgress: jest.fn(),
    },
  }),
}));

jest.mock('@/utils/tutorialHelpers', () => ({
  getStepNavigation: jest.fn(() => ({
    currentIndex: 0,
    totalSteps: 1,
    canGoBack: false,
    canGoNext: true,
    isFirstStep: true,
    isLastStep: false,
  })),
  generateProgressSummary: jest.fn(() => ({
    completedSteps: 0,
    totalSteps: 1,
    percentage: 0,
    timeSpent: 0,
  })),
  canSkipStep: jest.fn(() => false),
  createTutorialEvent: jest.fn(() => ({})),
}));

jest.mock('@/types/tutorial.types', () => ({
  Tutorial: {},
  TutorialContext: {},
  TutorialProgress: {},
  TutorialStep: {},
  TutorialProgressUpdate: {},
  TutorialUserPreferences: {},
  Achievement: {},
}));

describe('TutorialSystem Isolated Test', () => {
  it('should render without errors', () => {
    render(
      <div>
        <TutorialSystem
          tutorialId="test-tutorial"
          isOpen={true}
          onClose={() => {}}
        />
      </div>
    );

    expect(screen.getByText('测试教程')).toBeInTheDocument();
  });
});