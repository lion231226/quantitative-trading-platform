import '@testing-library/jest-dom'

// Fix DOM environment for React 18
Object.defineProperty(window, 'document', {
  value: document,
  writable: true,
});

// Ensure body exists with proper structure
if (!document.body) {
  document.body = document.createElement('body');
}

// Ensure head exists
if (!document.head) {
  document.head = document.createElement('head');
  document.documentElement.appendChild(document.head);
}

// Ensure documentElement exists and is properly configured
if (!document.documentElement) {
  const htmlElement = document.createElement('html');
  htmlElement.appendChild(document.head);
  htmlElement.appendChild(document.body);
  document.documentElement = htmlElement;
}

// Ensure proper DOM structure for React 18 createRoot
if (!document.getElementById('root')) {
  const rootElement = document.createElement('div');
  rootElement.id = 'root';
  document.body.appendChild(rootElement);
}

// Mock getComputedStyle for better DOM compatibility
const createComputedStyleMock = () => ({
  getPropertyValue: jest.fn((prop) => {
    const styleMap = {
      'pointer-events': 'auto',
      'z-index': '0',
      'opacity': '1',
      'color': 'black',
      'background-color': 'white',
      'display': 'block',
      'position': 'static',
      'width': 'auto',
      'height': 'auto',
      'top': '0px',
      'left': '0px',
      'visibility': 'visible',
      'cursor': 'pointer',
      'text-align': 'left',
      'font-size': '16px',
      'line-height': '1.5',
      'margin': '0px',
      'padding': '0px',
      'border': '0px',
      'box-sizing': 'border-box',
      'flex-direction': 'row',
      'align-items': 'center',
      'justify-content': 'flex-start',
      'gap': '0px',
      'grid-template-columns': 'none',
      'grid-template-rows': 'none',
      'visibility': 'visible'
    };
    return styleMap[prop] || '';
  }),
  zIndex: '0',
  opacity: '1',
  color: 'black',
  backgroundColor: 'white',
  display: 'block',
  position: 'static',
  width: 'auto',
  height: 'auto',
  top: '0px',
  left: '0px',
  visibility: 'visible',
  cursor: 'pointer',
  pointerEvents: 'auto',
  textAlign: 'left',
  fontSize: '16px',
  lineHeight: '1.5',
  margin: '0px',
  padding: '0px',
  border: '0px',
  borderStyle: 'solid',
  borderColor: 'black',
  borderWidth: '0px',
  borderRadius: '0px',
  boxSizing: 'border-box',
  flexDirection: 'row',
  alignItems: 'center',
  justifyContent: 'flex-start',
  gap: '0px',
  gridTemplateColumns: 'none',
  gridTemplateRows: 'none'
});

// Enhanced getComputedStyle mock that never returns undefined
const getComputedStyleMock = jest.fn((element) => {
  // Always return a valid style object, never undefined
  return createComputedStyleMock();
});

Object.defineProperty(window, 'getComputedStyle', {
  value: getComputedStyleMock,
  configurable: true
});

// Also ensure global.getComputedStyle exists for non-window contexts
if (typeof global !== 'undefined') {
  global.getComputedStyle = getComputedStyleMock;
}

// Also patch the global scope directly for dom-accessibility-api
if (typeof globalThis !== 'undefined') {
  globalThis.getComputedStyle = getComputedStyleMock;
}

// Mock getBoundingClientRect for DOM measurements
Element.prototype.getBoundingClientRect = jest.fn(() => ({
  width: 1024,
  height: 768,
  top: 0,
  left: 0,
  bottom: 768,
  right: 1024,
  x: 0,
  y: 0,
  toJSON: jest.fn(),
}));

// Create a comprehensive style mock that handles all property access
const createStyleMock = () => {
  const style = {};
  const properties = [
    'pointerEvents', 'zIndex', 'opacity', 'color', 'backgroundColor',
    'display', 'position', 'width', 'height', 'top', 'left', 'visibility',
    'cursor', 'textAlign', 'fontSize', 'lineHeight', 'margin', 'padding',
    'border', 'boxSizing', 'transform', 'transition', 'animation'
  ];

  properties.forEach(prop => {
    Object.defineProperty(style, prop, {
      value: prop === 'pointerEvents' ? 'auto' : 'initial',
      writable: true,
      configurable: true
    });
  });

  style.setProperty = jest.fn();
  style.getPropertyValue = jest.fn(() => '');
  style.removeProperty = jest.fn(() => '');

  return style;
};

// Mock element style properties
Object.defineProperty(HTMLElement.prototype, 'style', {
  get() {
    if (!this._styleMock) {
      this._styleMock = createStyleMock();
    }
    return this._styleMock;
  },
  configurable: true
});

// Mock closest method for elements
Element.prototype.closest = jest.fn(function(selector) {
  // Mock basic closest functionality for common cases
  if (selector === 'button' && this.tagName === 'BUTTON') return this;
  if (selector === 'div' && this.tagName === 'DIV') return this;
  if (selector === 'body' && this.tagName === 'BODY') return this;
  return null;
});

// Mock offsetParent and other positioning properties
Object.defineProperty(HTMLElement.prototype, 'offsetParent', {
  value: document.body,
  writable: true,
});

Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
  value: 200,
  writable: true,
});

Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
  value: 30,
  writable: true,
});

// Mock next/router
jest.mock('next/router', () => ({
  useRouter() {
    return {
      route: '/',
      pathname: '/',
      query: '',
      asPath: '',
      push: jest.fn(),
      pop: jest.fn(),
      reload: jest.fn(),
      back: jest.fn(),
      prefetch: jest.fn().mockResolvedValue(undefined),
      beforePopState: jest.fn(),
      events: {
        on: jest.fn(),
        off: jest.fn(),
        emit: jest.fn(),
      },
    }
  },
}))

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter() {
    return {
      push: jest.fn(),
      replace: jest.fn(),
      refresh: jest.fn(),
      back: jest.fn(),
      forward: jest.fn(),
      prefetch: jest.fn(),
    }
  },
  useSearchParams() {
    return new URLSearchParams()
  },
  usePathname() {
    return '/'
  },
}))

// Mock Chart.js
jest.mock('chart.js', () => ({
  Chart: {
    register: jest.fn(),
    defaults: {
      global: {
        defaultFont: {
          family: 'sans-serif',
        },
      },
    },
  },
  registerables: [],
}))


// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
}

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
}

// Mock Network Information API for mobile tests
Object.defineProperty(navigator, 'connection', {
  writable: true,
  value: {
    effectiveType: '4g',
    downlink: 10,
    rtt: 50,
    saveData: false,
    type: 'wifi',
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
  },
})

// Mock online/offline events
Object.defineProperty(navigator, 'onLine', {
  writable: true,
  value: true,
})

// Mock Touch events for mobile testing
Object.defineProperty(window, 'ontouchstart', {
  writable: true,
  value: jest.fn(),
})

Object.defineProperty(window, 'ontouchend', {
  writable: true,
  value: jest.fn(),
})

Object.defineProperty(window, 'ontouchmove', {
  writable: true,
  value: jest.fn(),
})

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
})

// Mock DOM methods for file operations
global.URL.createObjectURL = jest.fn(() => 'mocked-url')
global.URL.revokeObjectURL = jest.fn()

// Mock File and FileReader
global.File = class File {
  constructor(chunks, filename, options = {}) {
    this.chunks = chunks
    this.name = filename
    this.type = options.type || ''
    this.size = chunks.reduce((acc, chunk) => acc + chunk.length, 0)
  }
}

global.FileReader = class FileReader {
  constructor() {
    this.readyState = 0
    this.result = null
  }

  readAsText() {
    setTimeout(() => {
      this.readyState = 2
      this.result = '{"test": "data"}'
      this.onload && this.onload()
    }, 0)
  }

  readAsDataURL() {
    setTimeout(() => {
      this.readyState = 2
      this.result = 'data:application/json;base64,mocked'
      this.onload && this.onload()
    }, 0)
  }
}

// Enhanced localStorage mock with full API support
const createLocalStorageMock = () => {
  let store = {};
  const listeners = new Map();

  const notifyListeners = (key, oldValue, newValue) => {
    const event = {
      key,
      oldValue,
      newValue,
      storageArea: store,
      url: 'http://localhost'
    };

    if (key === null) {
      // notify all listeners for clear
      listeners.forEach((callback) => {
        try {
          callback(event);
        } catch (error) {
          console.warn('localStorage listener error:', error);
        }
      });
    } else {
      // notify specific key listeners
      const keyListeners = listeners.get(key) || [];
      keyListeners.forEach((callback) => {
        try {
          callback(event);
        } catch (error) {
          console.warn('localStorage listener error:', error);
        }
      });
    }
  };

  return {
    getItem: jest.fn((key) => {
      return store[key] !== undefined ? store[key] : null;
    }),

    setItem: jest.fn((key, value) => {
      const oldValue = store[key];
      store[key] = String(value);

      // Check storage quota (simulate 5MB limit)
      const totalSize = JSON.stringify(store).length;
      if (totalSize > 5 * 1024 * 1024) {
        delete store[key];
        throw new Error('QuotaExceededError: localStorage quota exceeded');
      }

      notifyListeners(key, oldValue, String(value));
    }),

    removeItem: jest.fn((key) => {
      const oldValue = store[key];
      delete store[key];
      notifyListeners(key, oldValue, null);
    }),

    clear: jest.fn(() => {
      store = {};
      notifyListeners(null, null, null);
    }),

    get length() {
      return Object.keys(store).length;
    },

    key: jest.fn((index) => {
      const keys = Object.keys(store);
      return index < keys.length ? keys[index] : null;
    }),

    // Storage event listeners
    addEventListener: jest.fn((event, callback) => {
      if (event === 'storage') {
        if (!listeners.has('storage')) {
          listeners.set('storage', []);
        }
        listeners.get('storage').push(callback);
      }
    }),

    removeEventListener: jest.fn((event, callback) => {
      if (event === 'storage') {
        const storageListeners = listeners.get('storage') || [];
        const index = storageListeners.indexOf(callback);
        if (index > -1) {
          storageListeners.splice(index, 1);
        }
      }
    }),

    // Direct access for testing
    _getStore: jest.fn(() => ({ ...store })),
    _setStore: jest.fn((newStore) => {
      store = { ...newStore };
    })
  };
};

// Create and assign localStorage mock
const localStorageMock = createLocalStorageMock();
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
});

// Create sessionStorage mock with similar implementation
const createSessionStorageMock = () => {
  let store = {};
  return {
    getItem: jest.fn((key) => {
      return store[key] !== undefined ? store[key] : null;
    }),
    setItem: jest.fn((key, value) => {
      store[key] = String(value);
    }),
    removeItem: jest.fn((key) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: jest.fn((index) => {
      const keys = Object.keys(store);
      return index < keys.length ? keys[index] : null;
    })
  };
};

Object.defineProperty(window, 'sessionStorage', {
  value: createSessionStorageMock(),
  writable: true,
});

// Note: JSDOM event handling fixes are no longer needed with happy-dom
// The Event class and event handling are now provided by happy-dom

// Fix happy-dom dispatchEvent issue more comprehensively
// This fixes the "Cannot read properties of undefined (reading 'dispatchEvent')" error

// Override HTMLElement.prototype.click to prevent dispatchEvent errors
Object.defineProperty(HTMLElement.prototype, 'click', {
  value: jest.fn(function() {
    // Mock click behavior without dispatchEvent
    if (this.onclick && typeof this.onclick === 'function') {
      try {
        this.onclick.call(this, { type: 'click', target: this });
      } catch (error) {
        console.warn('Mock click error:', error.message);
      }
    }
  }),
  writable: true,
  configurable: true
});

// Ensure all elements have dispatchEvent method
const ensureDispatchEvent = (element) => {
  if (!element.dispatchEvent) {
    element.dispatchEvent = jest.fn(() => true);
  }
};

// Override document.createElement to ensure all elements have dispatchEvent
const originalCreateElement = document.createElement;
document.createElement = function(tagName) {
  const element = originalCreateElement.call(this, tagName);
  ensureDispatchEvent(element);
  return element;
};

// Also ensure existing elements have dispatchEvent
if (typeof Element !== 'undefined') {
  Object.defineProperty(Element.prototype, 'dispatchEvent', {
    value: jest.fn(() => true),
    writable: true,
    configurable: true
  });
}

// Mock HTMLCanvasElement for chart-related tests
global.HTMLCanvasElement = class HTMLCanvasElement {
  constructor() {
    this.width = 0
    this.height = 0
    this.getContext = jest.fn(() => ({
      fillRect: jest.fn(),
      clearRect: jest.fn(),
      getImageData: jest.fn(() => ({ data: new Array(4) })),
      putImageData: jest.fn(),
      createImageData: jest.fn(() => ({ data: new Array(4) })),
      setTransform: jest.fn(),
      drawImage: jest.fn(),
      save: jest.fn(),
      fillText: jest.fn(),
      restore: jest.fn(),
      beginPath: jest.fn(),
      moveTo: jest.fn(),
      lineTo: jest.fn(),
      closePath: jest.fn(),
      stroke: jest.fn(),
      translate: jest.fn(),
      scale: jest.fn(),
      rotate: jest.fn(),
      arc: jest.fn(),
      fill: jest.fn(),
      measureText: jest.fn(() => ({ width: 0 })),
      transform: jest.fn(),
      rect: jest.fn(),
      clip: jest.fn(),
    }))
    this.toDataURL = jest.fn(() => 'data:image/png;base64,mocked')
    this.dispatchEvent = jest.fn(() => true);
  }
}

// Mock requestAnimationFrame and cancelAnimationFrame for animation tests
global.requestAnimationFrame = jest.fn((callback) => {
  return setTimeout(callback, 16)
})

global.cancelAnimationFrame = jest.fn((id) => {
  clearTimeout(id)
})

// Mock performance.now for timing tests (only if not already defined)
if (!global.performance.now || typeof global.performance.now !== 'function') {
  Object.defineProperty(global.performance, 'now', {
    value: jest.fn(() => Date.now()),
    configurable: true,
  });
}

// Suppress console warnings for tests (only React deprecation warnings remain)
const originalError = console.error

// Global DOM compatibility fixes for testing
beforeAll(() => {
  // Ensure getComputedStyle is properly mocked
  // Use the already defined getComputedStyleMock

  // Also patch Element.prototype.getComputedStyle if it exists
  if (typeof Element !== 'undefined' && !Element.prototype.getComputedStyle) {
    Element.prototype.getComputedStyle = getComputedStyleMock;
  }

  console.error = (...args) => {
    if (
      typeof args[0] === 'string' &&
      args[0].includes('Warning: ReactDOM.render is deprecated')
    ) {
      return
    }
    originalError.call(console, ...args)
  }
})

// Additional DOM compatibility for role-based queries
beforeEach(() => {
  // Ensure getComputedStyle is always available for each test
  if (typeof window !== 'undefined' && !window.getComputedStyle) {
    window.getComputedStyle = getComputedStyleMock;
  }

  // Also patch global scope
  if (typeof global !== 'undefined' && !global.getComputedStyle) {
    global.getComputedStyle = getComputedStyleMock;
  }

  // And globalThis for modern environments
  if (typeof globalThis !== 'undefined' && !globalThis.getComputedStyle) {
    globalThis.getComputedStyle = getComputedStyleMock;
  }
})

afterAll(() => {
  console.error = originalError
})