const { GlobalWindow } = require('happy-dom');
const { TestEnvironment } = require('jest-environment-node');

// Custom test environment using happy-dom
class HappyDOMEnvironment extends TestEnvironment {
  constructor(config, context) {
    super(config, context);

    // Create happy-dom window
    const happyWindow = new GlobalWindow({
      url: config.testEnvironmentOptions?.url || 'http://localhost:3000',
      resources: config.testEnvironmentOptions?.resources || 'usable',
      runScripts: config.testEnvironmentOptions?.runScripts || 'dangerously'
    });

    // Set up DOM globals properly
    this.global.window = happyWindow;
    this.global.document = happyWindow.document;
    this.global.navigator = happyWindow.navigator;
    this.global.localStorage = happyWindow.localStorage;
    this.global.sessionStorage = happyWindow.sessionStorage;
    this.global.HTMLElement = happyWindow.HTMLElement;
    this.global.HTMLInputElement = happyWindow.HTMLInputElement;
    this.global.HTMLSelectElement = happyWindow.HTMLSelectElement;
    this.global.HTMLTextAreaElement = happyWindow.HTMLTextAreaElement;
    this.global.Event = happyWindow.Event;
    this.global.EventTarget = happyWindow.EventTarget;
    this.global.MouseEvent = happyWindow.MouseEvent;
    this.global.KeyboardEvent = happyWindow.KeyboardEvent;
    this.global.FocusEvent = happyWindow.FocusEvent;
    this.global.CustomEvent = happyWindow.CustomEvent;
    this.global.Node = happyWindow.Node;
    this.global.Element = happyWindow.Element;
    this.global.NodeList = happyWindow.NodeList;
    this.global.HTMLCollection = happyWindow.HTMLCollection;
    this.global.performance = happyWindow.performance || {
      now: jest.fn(() => Date.now())
    };
  }

  async setup() {
    await super.setup();

    // Ensure proper DOM structure is available for React 18
    const { document } = this.global;

    // Ensure documentElement and basic structure
    if (!document.documentElement) {
      const htmlElement = document.createElement('html');
      const headElement = document.createElement('head');
      const bodyElement = document.createElement('body');

      document.documentElement = htmlElement;
      htmlElement.appendChild(headElement);
      htmlElement.appendChild(bodyElement);
      document.head = headElement;
      document.body = bodyElement;
    }

    // Ensure root container exists
    if (!document.getElementById('root')) {
      const rootElement = document.createElement('div');
      rootElement.id = 'root';
      document.body.appendChild(rootElement);
    }

    // Ensure DOM is ready
    if (document.readyState !== 'complete') {
      Object.defineProperty(document, 'readyState', {
        value: 'complete',
        writable: false
      });
    }
  }

  async teardown() {
    await super.teardown();
  }
}

module.exports = HappyDOMEnvironment;