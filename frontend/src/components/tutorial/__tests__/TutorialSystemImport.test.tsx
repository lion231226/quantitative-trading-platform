import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock all dependencies first
jest.mock('@/services/tutorialService', () => ({
  useTutorialService: () => ({
    useTutorial: () => ({ data: null, isLoading: false }),
    useTutorialProgress: () => ({ data: null, isLoading: false }),
    useUpdateProgress: () => ({ mutateAsync: jest.fn() }),
    saveUserPreferences: () => ({ mutateAsync: jest.fn() }),
    progressManager: { currentStep: 0 },
  }),
}));

jest.mock('@/utils/tutorialHelpers', () => ({
  getStepNavigation: () => ({ previousStep: null, nextStep: null }),
  generateProgressSummary: () => ({
    completedSteps: 0,
    totalSteps: 1,
    progressPercentage: 0,
  }),
  canSkipStep: () => true,
  createTutorialEvent: () => ({ type: 'test', timestamp: Date.now() }),
}));

jest.mock('@/components/ui/button', () => ({
  Button: ({ children, ...props }: any) => (
    <button {...props}>{children}</button>
  ),
}));

jest.mock('@/components/ui/card', () => ({
  Card: ({ children, ...props }: any) => <div {...props}>{children}</div>,
}));

jest.mock('@/components/ui/badge', () => ({
  Badge: ({ children, ...props }: any) => <span {...props}>{children}</span>,
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

// Mock tutorial types
jest.mock('@/types/tutorial.types', () => ({}));

describe('TutorialSystem Import Test', () => {
  it('should import TutorialSystem without errors', async () => {
    const { default: TutorialSystem } = await import('../TutorialSystem');

    expect(TutorialSystem).toBeDefined();
    expect(typeof TutorialSystem).toBe('function');
  });

  it('should render TutorialSystem without errors', async () => {
    const { default: TutorialSystem } = await import('../TutorialSystem');

    render(
      <TutorialSystem
        tutorialId="test-tutorial"
        isOpen={true}
        onClose={() => {}}
      />,
    );
  });
});
