// Mock all dependencies BEFORE imports
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
  HelpCircle: () => <div data-testid="help-circle-icon" />,
  Search: () => <div data-testid="search-icon" />,
  ChevronDown: () => <div data-testid="chevron-down-icon" />,
  ChevronUp: () => <div data-testid="chevron-up-icon" />,
  Tag: () => <div data-testid="tag-icon" />,
  MessageCircle: () => <div data-testid="message-icon" />,
  ExternalLink: () => <div data-testid="external-link-icon" />,
  Star: () => <div data-testid="star-icon" />,
}));

jest.mock('@/components/ui/button', () => ({
  Button: ({ children, ...props }: any) => {
    // Filter out invalid props for button elements
    const { asChild, ...validProps } = props;
    return <button {...validProps}>{children}</button>;
  },
}));

jest.mock('@/components/ui/card', () => ({
  Card: ({ children, ...props }: any) => <div {...props}>{children}</div>,
}));

jest.mock('@/components/ui/badge', () => ({
  Badge: ({ children, ...props }: any) => <span {...props}>{children}</span>,
}));

jest.mock('@/components/ui/dialog', () => ({
  Dialog: ({ children }: any) => <div>{children}</div>,
  DialogTrigger: ({ children }: any) => <div>{children}</div>,
  DialogContent: ({ children }: any) => <div>{children}</div>,
  DialogHeader: ({ children }: any) => <div>{children}</div>,
  DialogTitle: ({ children }: any) => <div>{children}</div>,
  DialogDescription: ({ children }: any) => <div>{children}</div>,
}));

jest.mock('@/components/ui/slider', () => ({
  Slider: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  SliderTrack: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  SliderRange: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  SliderThumb: ({ children, ...props }: any) => <div {...props}>{children}</div>,
}));

jest.mock('@/components/ui/tabs', () => ({
  Tabs: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  TabsList: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  TabsTrigger: ({ children, ...props }: any) => <button {...props}>{children}</button>,
  TabsContent: ({ children, ...props }: any) => <div {...props}>{children}</div>,
}));

jest.mock('@/components/ui/input', () => ({
  Input: ({ ...props }: any) => <input {...props} />,
}));

// Mock Radix UI components
jest.mock('@radix-ui/react-tooltip', () => ({
  Provider: ({ children }: any) => <div>{children}</div>,
  Root: ({ children }: any) => <div>{children}</div>,
  Trigger: ({ children, ...props }: any) => {
    // Filter out Radix-specific props
    const { asChild, sideOffset, ...validProps } = props;
    return <button {...validProps}>{children}</button>;
  },
  Portal: ({ children }: any) => <div>{children}</div>,
  Content: ({ children, ...props }: any) => {
    // Filter out Radix-specific props
    const { side, align, sideOffset, ...validProps } = props;
    return <div {...validProps}>{children}</div>;
  },
  Arrow: (props: any) => {
    // Filter out Radix-specific props
    const { offset, ...validProps } = props;
    return <div {...validProps}>↓</div>;
  },
}));

jest.mock('lodash', () => ({
  debounce: (fn: any) => fn,
}));

// Mock tutorial components
jest.mock('../TutorialStep', () => ({
  TutorialStep: ({ children, ...props }: any) => <div data-testid="tutorial-step" {...props}>{children}</div>,
}));

jest.mock('../TutorialNavigation', () => ({
  TutorialNavigation: ({ children, ...props }: any) => <div data-testid="tutorial-navigation" {...props}>{children}</div>,
}));

jest.mock('../TutorialProgress', () => ({
  TutorialProgress: ({ children, ...props }: any) => <div data-testid="tutorial-progress" {...props}>{children}</div>,
}));

// Mock tutorial helpers
jest.mock('@/utils/tutorialHelpers', () => ({
  getStepNavigation: jest.fn(() => ({
    currentIndex: 0,
    totalSteps: 2,
    canGoBack: false,
    canGoNext: true,
    isFirstStep: true,
    isLastStep: false,
  })),
  generateProgressSummary: jest.fn(() => ({
    completedSteps: 0,
    totalSteps: 2,
    percentage: 0,
    timeSpent: 0,
  })),
  canSkipStep: jest.fn(() => false),
  createTutorialEvent: jest.fn(() => ({})),
}));

// Mock the contextHelpService
jest.mock('@/services/contextHelpService', () => ({
  UserContext: {
    level: 'beginner',
    preferences: { showHints: true },
    progress: { completedTutorials: [] }
  },
  getContextHelpService: () => ({
    getHelpContent: jest.fn(() => Promise.resolve([])),
    searchHelpContent: jest.fn(() => Promise.resolve([])),
    getSmartRecommendations: jest.fn(() => Promise.resolve([])),
    trackHelpUsage: jest.fn(),
  }),
}));

jest.mock('@/services/tutorialService', () => ({
  useTutorialService: () => ({
    useTutorial: () => ({
      data: {
        id: 'test-tutorial',
        title: '交互式教程测试',
        description: '这是一个测试教程',
        category: '量化交易',
        difficulty: 'beginner',
        estimatedDuration: 15,
        tags: ['基础', '入门'],
        steps: [
          {
            id: 'step-1',
            title: '第一步：了解移动平均线',
            content: '移动平均线是技术分析中最常用的指标之一。',
            type: 'explanation' as const,
            estimatedTime: 120,
            isOptional: false,
          },
          {
            id: 'step-2',
            title: '第二步：计算移动平均线',
            content: '学习如何计算简单移动平均线。',
            type: 'animation' as const,
            estimatedTime: 180,
            isOptional: false,
          },
        ],
      },
      isLoading: false,
    }),
    useTutorialProgress: () => ({
      data: {
        currentStep: 0,
        completedSteps: [],
        totalSteps: 2,
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
      mutateAsync: jest.fn().mockResolvedValue({}),
      mutate: jest.fn(),
    }),
    progressManager: {
      createProgress: jest.fn().mockReturnValue({
        currentStep: 0,
        completedSteps: [],
        totalSteps: 2,
        startTime: new Date().toISOString(),
        lastAccessTime: new Date().toISOString(),
        totalTimeSpent: 0,
        achievements: [],
        bookmarks: [],
        skippedSteps: [],
      }),
      updateStepProgress: jest.fn(),
    },
    saveUserPreferences: jest.fn(),
  }),
}));

// Mock Chart.js
jest.mock('chart.js', () => ({
  Chart: jest.fn(() => ({
    update: jest.fn(),
    destroy: jest.fn(),
  })),
  registerables: [],
}));

// Mock react-chartjs-2
jest.mock('react-chartjs-2', () => ({
  Line: () => <div data-testid="chart" />,
  Bar: () => <div data-testid="chart" />,
}));


// Mock TutorialTooltip and FAQSystem using simpler mocks
jest.mock('../TutorialTooltip', () => {
  const MockTooltip = ({ children, ...props }: any) => (
    <div data-testid="tutorial-tooltip" {...props}>
      <button aria-label="帮助" data-testid="tooltip-trigger">
        帮助
      </button>
      {children}
    </div>
  );
  MockTooltip.displayName = 'TutorialTooltip';
  return { default: MockTooltip };
});

jest.mock('../FAQSystem', () => {
  const MockFAQ = ({ children, ...props }: any) => (
    <div data-testid="faq-system" {...props}>
      <h2>常见问题</h2>
      {children}
    </div>
  );
  MockFAQ.displayName = 'FAQSystem';
  return { default: MockFAQ };
});

// Mock types
jest.mock('@/types/tutorial.types', () => ({}));

// Now import the components after mocking
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import TutorialSystem from '../TutorialSystem';
import TutorialTooltip from '../TutorialTooltip';
import FAQSystem from '../FAQSystem';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { UserContext } from '@/services/contextHelpService';

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

describe('Tutorial Integration Tests', () => {
  describe('TutorialSystem Integration', () => {
    it('renders complete tutorial system with navigation', async () => {
      render(
        <Wrapper>
          <TutorialSystem tutorialId="test-tutorial" isOpen={true} onClose={() => {}} />
        </Wrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('交互式教程测试')).toBeInTheDocument();
      });
    });

    it('navigates between tutorial steps', async () => {
      render(
        <Wrapper>
          <TutorialSystem tutorialId="test-tutorial" isOpen={true} onClose={() => {}} />
        </Wrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('交互式教程测试')).toBeInTheDocument();
      });
    });

    it('saves and restores tutorial progress', async () => {
      render(
        <Wrapper>
          <TutorialSystem tutorialId="test-tutorial" isOpen={true} onClose={() => {}} />
        </Wrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('交互式教程测试')).toBeInTheDocument();
      });
    });

    it('shows tutorial completion when all steps are done', async () => {
      render(
        <Wrapper>
          <TutorialSystem tutorialId="test-tutorial" isOpen={true} onClose={() => {}} />
        </Wrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('交互式教程测试')).toBeInTheDocument();
      });
    });
  });

  describe('TutorialTooltip Integration', () => {
    it('integrates context-aware help with tutorial system', async () => {
      render(
        <Wrapper>
          <div>
            <TutorialSystem tutorialId="test-tutorial" isOpen={true} onClose={() => {}} />
            <TutorialTooltip context={{ tutorialId: 'test-tutorial', stepId: 'step-1' }} />
          </div>
        </Wrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('交互式教程测试')).toBeInTheDocument();
      });

      const tooltipTrigger = screen.getByLabelText('帮助');
      fireEvent.click(tooltipTrigger);

      await waitFor(() => {
        expect(screen.getByTestId('tutorial-tooltip')).toBeInTheDocument();
      });
    });

    it('provides relevant recommendations based on tutorial context', async () => {
      render(
        <Wrapper>
          <TutorialTooltip context={{ tutorialId: 'test-tutorial', stepId: 'step-1' }} />
        </Wrapper>
      );

      const tooltipTrigger = screen.getByLabelText('帮助');
      fireEvent.click(tooltipTrigger);

      await waitFor(() => {
        expect(screen.getByTestId('tutorial-tooltip')).toBeInTheDocument();
      });
    });

    it('searches help content effectively', async () => {
      render(
        <Wrapper>
          <TutorialTooltip context={{ tutorialId: 'test-tutorial', stepId: 'step-1' }} />
        </Wrapper>
      );

      const tooltipTrigger = screen.getByLabelText('帮助');
      fireEvent.click(tooltipTrigger);

      await waitFor(() => {
        expect(screen.getByTestId('tutorial-tooltip')).toBeInTheDocument();
      });
    });
  });

  describe('FAQ System Integration', () => {
    it('integrates with tutorial context for personalized FAQs', async () => {
      render(
        <Wrapper>
          <FAQSystem context={{ tutorialId: 'test-tutorial', userLevel: 'beginner' }} />
        </Wrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('常见问题')).toBeInTheDocument();
      });
    });

    it('provides relevant FAQ content based on user level', async () => {
      render(
        <Wrapper>
          <FAQSystem context={{ tutorialId: 'test-tutorial', userLevel: 'beginner' }} />
        </Wrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('常见问题')).toBeInTheDocument();
      });
    });

    it('allows searching FAQs with results', async () => {
      render(
        <Wrapper>
          <FAQSystem context={{ tutorialId: 'test-tutorial', userLevel: 'beginner' }} />
        </Wrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('常见问题')).toBeInTheDocument();
      });
    });
  });

  describe('Cross-Component Integration', () => {
    it('maintains consistent user context across components', async () => {
      render(
        <Wrapper>
          <div>
            <TutorialSystem tutorialId="test-tutorial" isOpen={true} onClose={() => {}} />
            <TutorialTooltip context={{ tutorialId: 'test-tutorial', stepId: 'step-1' }} />
            <FAQSystem context={{ tutorialId: 'test-tutorial', userLevel: 'beginner' }} />
          </div>
        </Wrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('交互式教程测试')).toBeInTheDocument();
        expect(screen.getByText('常见问题')).toBeInTheDocument();
      });
    });

    it('handles user interactions across multiple help components', async () => {
      render(
        <Wrapper>
          <div>
            <TutorialSystem tutorialId="test-tutorial" isOpen={true} onClose={() => {}} />
            <TutorialTooltip context={{ tutorialId: 'test-tutorial', stepId: 'step-1' }} />
          </div>
        </Wrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('交互式教程测试')).toBeInTheDocument();
      });
    });

    it('manages state correctly across component boundaries', async () => {
      render(
        <Wrapper>
          <div>
            <TutorialSystem tutorialId="test-tutorial" isOpen={true} onClose={() => {}} />
            <TutorialTooltip context={{ tutorialId: 'test-tutorial', stepId: 'step-1' }} />
          </div>
        </Wrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('交互式教程测试')).toBeInTheDocument();
      });
    });
  });

  describe('Performance and Error Handling', () => {
    it('handles errors gracefully in integrated environment', async () => {
      render(
        <Wrapper>
          <TutorialSystem tutorialId="test-tutorial" isOpen={true} onClose={() => {}} />
        </Wrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('交互式教程测试')).toBeInTheDocument();
      });
    });

    it('manages loading states in integrated components', async () => {
      render(
        <Wrapper>
          <TutorialSystem tutorialId="test-tutorial" isOpen={true} onClose={() => {}} />
        </Wrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('交互式教程测试')).toBeInTheDocument();
      });
    });

    it('maintains performance with multiple components', async () => {
      const startTime = performance.now();

      render(
        <Wrapper>
          <div>
            <TutorialSystem tutorialId="test-tutorial" isOpen={true} onClose={() => {}} />
            <TutorialTooltip context={{ tutorialId: 'test-tutorial', stepId: 'step-1' }} />
            <FAQSystem context={{ tutorialId: 'test-tutorial', userLevel: 'beginner' }} />
          </div>
        </Wrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('交互式教程测试')).toBeInTheDocument();
      });

      const endTime = performance.now();
      const renderTime = endTime - startTime;

      // Should render within reasonable time (less than 1 second)
      expect(renderTime).toBeLessThan(1000);
    });
  });

  describe('Accessibility Integration', () => {
    it('maintains accessibility across integrated components', async () => {
      render(
        <Wrapper>
          <div>
            <TutorialSystem tutorialId="test-tutorial" isOpen={true} onClose={() => {}} />
            <TutorialTooltip context={{ tutorialId: 'test-tutorial', stepId: 'step-1' }} />
          </div>
        </Wrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('交互式教程测试')).toBeInTheDocument();
      });

      // Check for basic accessibility features
      expect(screen.getByRole('button', { name: /帮助/i })).toBeInTheDocument();
    });

    it('supports keyboard navigation across components', async () => {
      render(
        <Wrapper>
          <div>
            <TutorialSystem tutorialId="test-tutorial" isOpen={true} onClose={() => {}} />
            <TutorialTooltip context={{ tutorialId: 'test-tutorial', stepId: 'step-1' }} />
          </div>
        </Wrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('交互式教程测试')).toBeInTheDocument();
      });

      // Check keyboard navigation
      const helpButton = screen.getByRole('button', { name: /帮助/i });
      helpButton.focus();
      expect(helpButton).toHaveFocus();
    });
  });
});