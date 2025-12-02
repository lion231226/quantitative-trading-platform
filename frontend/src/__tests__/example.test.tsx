/**
 * Example test file to verify Jest configuration
 */

import { render, screen } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';

// Extend Jest matchers
expect.extend(toHaveNoViolations);

// Example component for testing
const ExampleComponent = () => {
  return (
    <div>
      <h1>Hello World</h1>
      <button>Click me</button>
    </div>
  );
};

describe('Example Component Tests', () => {
  it('renders without crashing', () => {
    render(<ExampleComponent />);
    expect(screen.getByText('Hello World')).toBeInTheDocument();
  });

  it('renders button', () => {
    render(<ExampleComponent />);
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<ExampleComponent />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should pass basic assertions', () => {
    expect(true).toBe(true);
    expect(1 + 1).toBe(2);
    expect({}).toEqual({});
  });
});

describe('Utility Tests', () => {
  it('should handle async operations', async () => {
    const promise = Promise.resolve('test');
    const result = await promise;
    expect(result).toBe('test');
  });

  it('should handle mocking', () => {
    const mockFn = jest.fn();
    mockFn('test');
    expect(mockFn).toHaveBeenCalledWith('test');
    expect(mockFn).toHaveBeenCalledTimes(1);
  });
});