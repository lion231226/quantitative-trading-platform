/**
 * Image Optimization Utilities
 *
 * Provides image loading and optimization utilities for better performance
 */

/**
 * Lazy loading configuration for images
 */
export interface LazyLoadImageConfig {
  src: string;
  alt: string;
  width?: number;
  height?: number;
  loading?: 'lazy' | 'eager';
  fetchPriority?: 'high' | 'low' | 'auto';
  sizes?: string;
  srcSet?: string;
}

/**
 * Preload critical images
 */
export function preloadImage(src: string, fetchPriority: RequestInit['priority'] = 'high'): Promise<void> {
  return new Promise((resolve, reject) => {
    const link = document.createElement('link');
    link.rel = 'preload';
    link.as = 'image';
    link.href = src;

    if (fetchPriority) {
      (link as any).fetchPriority = fetchPriority;
    }

    link.onload = () => {
      document.head.removeChild(link);
      resolve();
    };

    link.onerror = () => {
      document.head.removeChild(link);
      reject(new Error(`Failed to preload image: ${src}`));
    };

    document.head.appendChild(link);
  });
}

/**
 * Create responsive image srcSet
 */
export function createSrcSet(
  baseUrl: string,
  sizes: number[],
  format?: 'webp' | 'avif' | 'auto'
): string {
  return sizes
    .map(size => {
      const url = new URL(baseUrl, window.location.origin);
      const extension = format === 'auto' ?
        (url.pathname.match(/\.(jpg|jpeg|png|webp|avif)$/i)?.[1] || 'jpg') :
        format;

      // Replace extension with optimized version
      const optimizedUrl = baseUrl.replace(/\.(jpg|jpeg|png)$/i, `.${size}w.${extension}`);
      return `${optimizedUrl} ${size}w`;
    })
    .join(', ');
}

/**
 * Generate image sizes attribute
 */
export function generateSizes(breakpoints: { [key: string]: number }[]): string {
  return breakpoints
    .map(({ width }) => `(max-width: ${width}px) ${width}px`)
    .join(', ') + ', 100vw';
}

/**
 * Optimize image loading with intersection observer
 */
export class ImageLazyLoader {
  private observer: IntersectionObserver | null = null;
  private loadedImages = new Set<string>();

  constructor() {
    if (typeof IntersectionObserver !== 'undefined') {
      this.observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              const img = entry.target as HTMLImageElement;
              this.loadImage(img);
            }
          });
        },
        {
          rootMargin: '50px 0px', // Start loading 50px before entering viewport
          threshold: 0.01,
        }
      );
    }
  }

  /**
   * Observe an image element for lazy loading
   */
  public observe(img: HTMLImageElement): void {
    if (this.observer && !this.loadedImages.has(img.src)) {
      this.observer.observe(img);
    } else if (!this.observer) {
      // Fallback for browsers without IntersectionObserver
      this.loadImage(img);
    }
  }

  /**
   * Load an image immediately
   */
  private loadImage(img: HTMLImageElement): void {
    if (this.loadedImages.has(img.src)) {
      return;
    }

    const tempImage = new Image();

    tempImage.onload = () => {
      img.src = tempImage.src;
      img.classList.add('loaded');
      this.loadedImages.add(img.src);
      this.observer?.unobserve(img);
    };

    tempImage.onerror = () => {
      img.classList.add('error');
      this.observer?.unobserve(img);
    };

    // Start loading
    tempImage.src = img.dataset.src || img.src;
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
 * Progressive image loading component utilities
 */
export function createProgressiveImageLoader(
  lowQualitySrc: string,
  highQualitySrc: string
): {
  loadLowQuality: () => Promise<HTMLImageElement>;
  loadHighQuality: () => Promise<HTMLImageElement>;
} {
  return {
    loadLowQuality: () => new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = lowQualitySrc;
    }),

    loadHighQuality: () => new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = highQualitySrc;
    }),
  };
}

/**
 * WebP format support detection
 */
export function supportsWebP(): Promise<boolean> {
  return new Promise((resolve) => {
    const webP = new Image();
    webP.onload = webP.onerror = () => {
      resolve(webP.height === 2);
    };
    webP.src = 'data:image/webp;base64,UklGRjoAAABXRUJQVlA4IC4AAACyAgCdASoCAAIALmk0mk0iIiIiIgBoSygABc6WWgAA/veff/0PP8bA//LwYAAA';
  });
}

/**
 * AVIF format support detection
 */
export function supportsAVIF(): Promise<boolean> {
  return new Promise((resolve) => {
    const avif = new Image();
    avif.onload = avif.onerror = () => {
      resolve(avif.height === 2);
    };
    avif.src = 'data:image/avif;base64,AAAAIGZ0eXBhdmlmAAAAAGF2aWZtaWYxbWlhZk1BMUIAAADybWV0YQAAAAAAAAAoaGRscgAAAAAAAAAAcGljdAAAAAAAAAAAAAAAAGxpYmF2aWYAAAAADnBpdG0AAAAAAAEAAAAeaWxvYwAAAABEAAABAAEAAAABAAABGgAAAB0AAAAoaWluZgAAAAAAAQAAABppbmZlAgAAAAABAABhdjAxQ29sb3IAAAAAamlwcnAAAABLaXBjbwAAABRpc3BlAAAAAAAAAAEAAAABAAAAEHBpeGkAAAAAAwgICAAAAAxhdjFDgQ0MAAAAABNjb2xybmNseAACAAIAAYAAAAAXaXBtYQAAAAAAAAABAAEEAQKDBAAAACVtZGF0EgAKCBgANogQEAwgMgZn8AAAAAAAABAAAAAAAAAAAAAgAAAAIAAAACAAAAAgAAAAIAAAACAAAAAgAAAAIAAAACAAAAAgAAAAIAAAACAAAAAgAAAAIAAAACAAAAAgAAAAIAAAACAAAAAgAAAAIAAAACAAAAAgAAAAIAAAACAAAAAgAAAAIAAAACAAAAAgAAAAIAAAACAAAAAgAAAAIAAAACAAAAAgAAAAIAAAACAAAAAgAAAAIAAAACAAAAAgAAAAIAAAACAAAAAgAAAAIA';
  });
}

/**
 * Get optimal image format based on browser support
 */
export async function getOptimalImageFormat(): Promise<'avif' | 'webp' | 'original'> {
  if (await supportsAVIF()) {
    return 'avif';
  }
  if (await supportsWebP()) {
    return 'webp';
  }
  return 'original';
}

/**
 * Create optimized image URL with format and size parameters
 */
export async function createOptimizedImageUrl(
  originalUrl: string,
  width?: number,
  height?: number,
  quality: number = 80
): Promise<string> {
  const format = await getOptimalImageFormat();
  const url = new URL(originalUrl, window.location.origin);

  // Add size parameters if provided
  if (width) {
    url.searchParams.set('w', width.toString());
  }
  if (height) {
    url.searchParams.set('h', height.toString());
  }

  // Add quality parameter
  url.searchParams.set('q', quality.toString());

  // Add format parameter if not original
  if (format !== 'original') {
    url.searchParams.set('f', format);
  }

  return url.toString();
}

/**
 * Critical image preloader for above-the-fold content
 */
export class CriticalImagePreloader {
  private preloadedImages = new Set<string>();

  /**
   * Preload critical images for immediate display
   */
  public async preloadCriticalImages(imageUrls: string[]): Promise<void> {
    const preloadPromises = imageUrls
      .filter(url => !this.preloadedImages.has(url))
      .map(url => this.preloadImage(url));

    await Promise.allSettled(preloadPromises);
  }

  private async preloadImage(url: string): Promise<void> {
    try {
      await preloadImage(url, 'high');
      this.preloadedImages.add(url);
    } catch (error) {
      console.warn(`Failed to preload critical image: ${url}`, error);
    }
  }
}

// Export singleton instances
export const imageLazyLoader = new ImageLazyLoader();
export const criticalImagePreloader = new CriticalImagePreloader();