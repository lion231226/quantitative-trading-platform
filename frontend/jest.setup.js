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
Object.defineProperty(window, 'getComputedStyle', {
  value: jest.fn(() => ({
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
        'box-sizing': 'border-box'
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
    boxSizing: 'border-box'
  })),
});

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

// Note: JSDOM event handling fixes are no longer needed with happy-dom
// The Event class and event handling are now provided by happy-dom

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
beforeAll(() => {
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

afterAll(() => {
  console.error = originalError
})