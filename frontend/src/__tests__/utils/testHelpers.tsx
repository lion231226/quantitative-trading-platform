import { RenderOptions, render, screen } from '@testing-library/react';
import { ReactElement } from 'react';

/**
 * Test helper to avoid DOM API compatibility issues with role queries
 * Use this when getByRole causes "Cannot read properties of undefined (reading 'getPropertyValue')" errors
 */
export const getByTextOrRole = (text: string, role?: string) => {
  try {
    // Try getByText first (more reliable)
    return screen.getByText(text);
  } catch (error) {
    if (role) {
      // Fallback to getByRole if text doesn't work
      return screen.getByRole(role as any, { name: new RegExp(text, 'i') });
    }
    throw error;
  }
};

/**
 * Custom render function with DOM compatibility fixes
 */
export const renderWithCompat = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>,
) => {
  // Add any DOM compatibility fixes here if needed
  return render(ui, options);
};

/**
 * Wait for element with fallback strategies
 */
export const waitForElement = async (
  textOrRole: { text?: string; role?: string },
  timeout = 5000,
) => {
  const { text, role } = textOrRole;

  if (text) {
    try {
      return await screen.findByText(text, {}, { timeout });
    } catch (error) {
      if (role) {
        return await screen.findByRole(
          role as any,
          { name: new RegExp(text || '', 'i') },
          { timeout },
        );
      }
      throw error;
    }
  }

  if (role) {
    return await screen.findByRole(role as any, {}, { timeout });
  }

  throw new Error('Either text or role must be provided');
};
