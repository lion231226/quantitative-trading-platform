import { expect } from '@testing-library/jest-dom';

/**
 * Custom matchers for DOM compatibility
 * Add these to your test setup or import in test files
 */

// Enhanced toBeInTheDocument with DOM error handling
const toBeInTheDocumentCompat = async (
  element: HTMLElement | null,
  timeout = 1000,
) => {
  if (!element) {
    return {
      message: () => 'Expected element to be in the document, but it was null',
      pass: false,
    };
  }

  // Check if element is actually attached to DOM
  if (!document.contains(element)) {
    return {
      message: () => 'Expected element to be attached to the document',
      pass: false,
    };
  }

  return {
    message: () => 'Expected element to be in the document',
    pass: true,
  };
};

// Custom matcher for role queries with fallback
const toHaveRoleCompat = async (element: HTMLElement, expectedRole: string) => {
  try {
    const actualRole =
      element.getAttribute('role') || element.tagName.toLowerCase();
    const pass =
      actualRole === expectedRole || actualRole.includes(expectedRole);

    return {
      message: () =>
        pass
          ? `Expected element not to have role "${expectedRole}"`
          : `Expected element to have role "${expectedRole}", but found "${actualRole}"`,
      pass,
    };
  } catch (error) {
    return {
      message: () => `Error checking element role: ${error}`,
      pass: false,
    };
  }
};

// Export custom matchers
export const customMatchers = {
  toBeInTheDocumentCompat,
  toHaveRoleCompat,
};

// Extend Jest's matchers
expect.extend(customMatchers as any);

// Types for TypeScript
declare global {
  namespace jest {
    interface Matchers<R> {
      toBeInTheDocumentCompat(timeout?: number): R;
      toHaveRoleCompat(expectedRole: string): R;
    }
  }
}
