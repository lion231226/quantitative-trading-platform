import '@testing-library/jest-dom'

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

// Mock Lightweight Charts
jest.mock('lightweight-charts', () => ({
  createChart: jest.fn(() => ({
    addCandlestickSeries: jest.fn(() => ({
      setData: jest.fn(),
      update: jest.fn(),
      priceScale: jest.fn(),
      applyOptions: jest.fn(),
    })),
    addLineSeries: jest.fn(() => ({
      setData: jest.fn(),
      update: jest.fn(),
      priceScale: jest.fn(),
      applyOptions: jest.fn(),
    })),
    timeScale: jest.fn(() => ({
      fitContent: jest.fn(),
      scrollToPosition: jest.fn(),
      setVisibleRange: jest.fn(),
    })),
    remove: jest.fn(),
    resize: jest.fn(),
    applyOptions: jest.fn(),
  })),
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

// Suppress console warnings for tests
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