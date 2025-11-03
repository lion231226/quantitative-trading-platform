import { render, screen } from '@testing-library/react';
import { Loading, LoadingSpinner } from '../loading';

describe('Loading Components', () => {
  describe('Loading', () => {
    it('renders with default props', () => {
      render(<Loading />);
      expect(screen.getByRole('status')).toBeInTheDocument();
      expect(screen.getByText('加载中...')).toBeInTheDocument();
    });

    it('renders with custom text', () => {
      render(<Loading text="自定义加载文本" />);
      expect(screen.getByText('自定义加载文本')).toBeInTheDocument();
    });

    it('renders with different sizes', () => {
      const { rerender } = render(<Loading size="sm" />);
      const spinnerElement = screen.getByRole('status').querySelector('[aria-hidden="true"]');
      expect(spinnerElement).toHaveClass('w-4 h-4');

      rerender(<Loading size="lg" />);
      const lgSpinnerElement = screen.getByRole('status').querySelector('[aria-hidden="true"]');
      expect(lgSpinnerElement).toHaveClass('w-8 h-8');
    });

    it('applies custom className', () => {
      render(<Loading className="custom-class" />);
      expect(screen.getByRole('status')).toHaveClass('custom-class');
    });
  });

  describe('LoadingSpinner', () => {
    it('renders spinner without text', () => {
      render(<LoadingSpinner />);
      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('renders with different sizes', () => {
      const { rerender } = render(<LoadingSpinner size="sm" />);
      expect(screen.getByRole('status')).toHaveClass('w-4 h-4');

      rerender(<LoadingSpinner size="lg" />);
      expect(screen.getByRole('status')).toHaveClass('w-8 h-8');
    });

    it('applies custom className', () => {
      render(<LoadingSpinner className="custom-spinner" />);
      expect(screen.getByRole('status')).toHaveClass('custom-spinner');
    });
  });
});
