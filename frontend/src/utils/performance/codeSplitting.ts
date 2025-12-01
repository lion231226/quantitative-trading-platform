/**
 * Code Splitting and Lazy Loading Utilities
 *
 * Provides utilities for dynamic imports and code splitting optimization
 */

import { lazy, ComponentType, Suspense } from 'react';

/**
 * Lazy loading configuration
 */
export interface LazyComponentConfig {
  fallback?: React.ComponentType;
  errorComponent?: React.ComponentType<{ error: Error; retry: () => void }>;
  preload?: boolean;
  timeout?: number;
}

/**
 * Enhanced lazy component wrapper with error boundaries and preload capabilities
 */
export function createLazyComponent<T extends ComponentType<any>>(
  importFunc: () => Promise<{ default: T }>,
  config: LazyComponentConfig = {}
): T {
  const LazyComponent = lazy(importFunc);

  // Preload if requested
  if (config.preload) {
    importFunc();
  }

  // Return enhanced component
  return LazyComponent as T;
}

/**
 * Error boundary component for lazy loaded components
 */
export interface LazyLoadErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

export class LazyLoadErrorBoundary extends React.Component<
  {
    fallback?: React.ComponentType<{ error?: Error; retry?: () => void }>;
    children: React.ReactNode;
    onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  },
  LazyLoadErrorBoundaryState
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): LazyLoadErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Lazy loading error:', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  retry = () => {
    this.setState({ hasError: false, error: undefined });
  };

  render() {
    if (this.state.hasError) {
      const FallbackComponent = this.props.fallback;
      if (FallbackComponent) {
        return <FallbackComponent error={this.state.error} retry={this.retry} />;
      }
      return (
        <div className="p-4 border border-red-200 bg-red-50 rounded-lg">
          <h3 className="text-red-800 font-medium">组件加载失败</h3>
          <p className="text-red-600 text-sm mt-1">
            {this.state.error?.message || '未知错误'}
          </p>
          <button
            onClick={this.retry}
            className="mt-2 px-3 py-1 bg-red-500 text-white rounded text-sm hover:bg-red-600"
          >
            重试
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Suspense wrapper with custom fallback
 */
export function LazyWrapper({
  children,
  fallback = (
    <div className="flex items-center justify-center p-8">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      <span className="ml-2 text-gray-600">加载中...</span>
    </div>
  ),
}: {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  return <Suspense fallback={fallback}>{children}</Suspense>;
}

/**
 * Dynamic import with timeout
 */
export function dynamicImportWithTimeout<T>(
  importFunc: () => Promise<T>,
  timeoutMs: number = 5000
): Promise<T> {
  return Promise.race([
    importFunc(),
    new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error(`Module load timeout after ${timeoutMs}ms`)), timeoutMs)
    ),
  ]);
}

/**
 * Preload route components
 */
export class RoutePreloader {
  private preloadPromises = new Map<string, Promise<any>>();

  /**
   * Preload a route component
   */
  public preloadRoute(routeKey: string, importFunc: () => Promise<any>): void {
    if (!this.preloadPromises.has(routeKey)) {
      const promise = dynamicImportWithTimeout(importFunc, 10000)
        .catch(error => {
          console.warn(`Failed to preload route ${routeKey}:`, error);
          this.preloadPromises.delete(routeKey);
          throw error;
        });

      this.preloadPromises.set(routeKey, promise);
    }
  }

  /**
   * Get preloaded route component
   */
  public async getPreloadedRoute(routeKey: string): Promise<any> {
    const promise = this.preloadPromises.get(routeKey);
    if (promise) {
      try {
        return await promise;
      } catch (error) {
        this.preloadPromises.delete(routeKey);
        throw error;
      }
    }
    throw new Error(`Route ${routeKey} not preloaded`);
  }

  /**
   * Preload multiple routes
   */
  public preloadRoutes(routes: Record<string, () => Promise<any>>): void {
    Object.entries(routes).forEach(([routeKey, importFunc]) => {
      // Use requestIdleCallback to avoid blocking main thread
      if (typeof requestIdleCallback !== 'undefined') {
        requestIdleCallback(() => this.preloadRoute(routeKey, importFunc));
      } else {
        // Fallback for browsers without requestIdleCallback
        setTimeout(() => this.preloadRoute(routeKey, importFunc), 0);
      }
    });
  }

  /**
   * Clear preloaded routes
   */
  public clearPreloadedRoutes(): void {
    this.preloadPromises.clear();
  }
}

/**
 * Intersection Observer based preloading for route components
 */
export class IntersectionRoutePreloader {
  private observer: IntersectionObserver | null = null;
  private preloader = new RoutePreloader();

  constructor() {
    if (typeof IntersectionObserver !== 'undefined') {
      this.observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              const routeKey = entry.target.getAttribute('data-route-key');
              const importFunc = entry.target.getAttribute('data-import-func');
              if (routeKey && importFunc) {
                try {
                  const func = new Function(`return ${importFunc}`)() as () => Promise<any>;
                  this.preloader.preloadRoute(routeKey, func);
                } catch (error) {
                  console.warn(`Failed to parse import function for route ${routeKey}:`, error);
                }
              }
            }
          });
        },
        {
          rootMargin: '100px', // Start preloading 100px before element enters viewport
        }
      );
    }
  }

  /**
   * Observe an element for route preloading
   */
  public observe(element: HTMLElement, routeKey: string, importFunc: () => Promise<any>): void {
    element.setAttribute('data-route-key', routeKey);
    element.setAttribute('data-import-func', importFunc.toString());
    this.observer?.observe(element);
  }

  /**
   * Disconnect the observer
   */
  public disconnect(): void {
    this.observer?.disconnect();
    this.observer = null;
  }
}

/**
 * Chunk loading utilities
 */
export class ChunkOptimizer {
  private loadedChunks = new Set<string>();

  /**
   * Load a specific chunk
   */
  public async loadChunk(chunkName: string): Promise<void> {
    if (this.loadedChunks.has(chunkName)) {
      return;
    }

    try {
      // Dynamically import the chunk
      await import(/* webpackChunkName: "[request]" */ `@/chunks/${chunkName}`);
      this.loadedChunks.add(chunkName);
    } catch (error) {
      console.error(`Failed to load chunk ${chunkName}:`, error);
      throw error;
    }
  }

  /**
   * Preload chunks for better performance
   */
  public preloadChunks(chunkNames: string[]): void {
    chunkNames.forEach(chunkName => {
      if (!this.loadedChunks.has(chunkName)) {
        if (typeof requestIdleCallback !== 'undefined') {
          requestIdleCallback(() => this.loadChunk(chunkName));
        } else {
          setTimeout(() => this.loadChunk(chunkName), 0);
        }
      }
    });
  }

  /**
   * Check if a chunk is loaded
   */
  public isChunkLoaded(chunkName: string): boolean {
    return this.loadedChunks.has(chunkName);
  }
}

/**
 * Third-party library lazy loader
 */
export function createThirdPartyLoader<T>(
  libraryName: string,
  importFunc: () => Promise<T>,
  config: {
    version?: string;
    cdn?: string;
    fallback?: () => T;
  } = {}
): () => Promise<T> {
  let cachedPromise: Promise<T> | null = null;

  return () => {
    if (cachedPromise) {
      return cachedPromise;
    }

    cachedPromise = (async () => {
      try {
        // Try dynamic import first
        return await importFunc();
      } catch (error) {
        console.warn(`Failed to load ${libraryName} from bundle, trying CDN...`);

        // Fallback to CDN if specified
        if (config.cdn) {
          const script = document.createElement('script');
          script.src = config.cdn;
          script.async = true;

          return new Promise((resolve, reject) => {
            script.onload = () => resolve((window as any)[libraryName] as T);
            script.onerror = () => {
              console.warn(`Failed to load ${libraryName} from CDN, using fallback...`);
              if (config.fallback) {
                resolve(config.fallback());
              } else {
                reject(new Error(`Failed to load ${libraryName}`));
              }
            };
            document.head.appendChild(script);
          });
        }

        // Final fallback
        if (config.fallback) {
          return config.fallback();
        }

        throw error;
      }
    })();

    return cachedPromise;
  };
}

/**
 * Web Worker loader for performance optimization
 */
export class WebWorkerLoader {
  private workers = new Map<string, Worker>();

  /**
   * Load a Web Worker
   */
  public async loadWorker(
    workerName: string,
    workerPath: string,
    options?: WorkerOptions
  ): Promise<Worker> {
    if (this.workers.has(workerName)) {
      return this.workers.get(workerName)!;
    }

    try {
      const worker = new Worker(workerPath, options);
      this.workers.set(workerName, worker);
      return worker;
    } catch (error) {
      console.error(`Failed to load worker ${workerName}:`, error);
      throw error;
    }
  }

  /**
   * Terminate a Web Worker
   */
  public terminateWorker(workerName: string): void {
    const worker = this.workers.get(workerName);
    if (worker) {
      worker.terminate();
      this.workers.delete(workerName);
    }
  }

  /**
   * Terminate all workers
   */
  public terminateAllWorkers(): void {
    this.workers.forEach(worker => worker.terminate());
    this.workers.clear();
  }
}

// Export singleton instances
export const routePreloader = new RoutePreloader();
export const intersectionRoutePreloader = new IntersectionRoutePreloader();
export const chunkOptimizer = new ChunkOptimizer();
export const webWorkerLoader = new WebWorkerLoader();

// Re-export commonly used components
export {
  LazyLoadErrorBoundary,
  LazyWrapper,
};

// Export types
export type {
  LazyComponentConfig,
  LazyLoadErrorBoundaryState,
};