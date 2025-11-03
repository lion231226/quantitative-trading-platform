import React from 'react';
import { render, screen } from '@testing-library/react';

// Mock all dependencies BEFORE imports
jest.mock('lucide-react', () => ({
  Search: () => <div data-testid="search-icon" />,
  HelpCircle: () => <div data-testid="help-circle-icon" />,
  X: () => <div data-testid="x-icon" />,
  BookOpen: () => <div data-testid="book-open-icon" />,
  Lightbulb: () => <div data-testid="lightbulb-icon" />,
}));

jest.mock('@/services/contextHelpService', () => ({
  UserContext: {},
  HelpContent: {},
  getContextHelpService: () => ({
    getHelpContent: jest.fn(() => Promise.resolve([])),
    searchHelpContent: jest.fn(() => Promise.resolve([])),
    getSmartRecommendations: jest.fn(() => Promise.resolve([])),
    trackHelpUsage: jest.fn(),
  }),
}));

jest.mock('@radix-ui/react-tooltip', () => ({
  Provider: ({ children }: any) => <div>{children}</div>,
  Root: ({ children }: any) => <div>{children}</div>,
  Trigger: ({ children, ...props }: any) => <button {...props}>{children}</button>,
  Portal: ({ children }: any) => <div>{children}</div>,
  Content: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  Arrow: (props: any) => <div {...props}>↓</div>,
}));

jest.mock('lodash', () => ({
  debounce: (fn: any) => fn,
}));

// Now import the component
import TutorialTooltip from '../TutorialTooltip';

describe('TutorialTooltip Isolated Test', () => {
  it('should render without errors', () => {
    render(
      <TutorialTooltip
        context={{ tutorialId: 'test-tutorial', stepId: 'step-1' }}
      />
    );

    // Check that the tooltip renders by looking for specific text
    expect(screen.getByText('智能帮助')).toBeInTheDocument();
  });
});