import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import TutorialSystem from '../TutorialSystem';

// Mock the useTutorialService hook
jest.mock('@/services/tutorialService', () => ({
  useTutorialService: () => ({
    useTutorial: () => ({
      data: {
        id: 'test-tutorial',
        title: 'Test Tutorial',
        description: 'Test Description',
        category: 'Test',
        difficulty: 'beginner',
        estimatedDuration: 15,
        steps: [
          {
            id: 'step-1',
            title: 'Test Step 1',
            content: 'Test content 1',
            type: 'explanation' as const,
            estimatedTime: 120,
          },
        ],
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
    useUpdateProgress: () => ({
      mutateAsync: jest.fn(),
    }),
    useUserPreferences: () => ({
      animationSpeed: 1.0,
      autoProgress: false,
      showHints: true,
      soundEnabled: false,
    }),
    progressManager: {
      createProgress: jest.fn(),
      updateStepProgress: jest.fn(),
    },
  }),
}));

describe('TutorialSystem', () => {
  it('renders tutorial introduction when not started', () => {
    render(
      <TutorialSystem
        tutorialId="test-tutorial"
        isOpen={true}
        onClose={jest.fn()}
      />,
    );

    expect(screen.getByText('Test Tutorial')).toBeInTheDocument();
    expect(screen.getByText('Test Description')).toBeInTheDocument();
    expect(screen.getByText('开始教程')).toBeInTheDocument();
  });

  it('shows tutorial content after starting', async () => {
    render(
      <TutorialSystem
        tutorialId="test-tutorial"
        isOpen={true}
        onClose={jest.fn()}
        autoStart={true}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('Test Step 1')).toBeInTheDocument();
    });
  });

  it('calls onClose when close button is clicked', () => {
    const onClose = jest.fn();
    render(
      <TutorialSystem
        tutorialId="test-tutorial"
        isOpen={true}
        onClose={onClose}
      />,
    );

    const closeButton = screen.getByLabelText('Close');
    fireEvent.click(closeButton);

    expect(onClose).toHaveBeenCalled();
  });
});
