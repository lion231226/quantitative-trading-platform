# Sentry Performance Monitoring Setup Guide

## Overview

This guide walks you through setting up Sentry Performance Monitoring for the quantitative trading platform as part of Story 4.4: Performance Optimization and Monitoring.

## Prerequisites

- A Sentry account (free tier available for small projects)
- Your project URL and repository information

## Step 1: Create Sentry Project

1. Go to [sentry.io](https://sentry.io) and sign up/sign in
2. Create a new project
3. Select **React** or **Next.js** as the platform
4. Give your project a name (e.g., "quant-trading-frontend")
5. Choose your team (if applicable)

## Step 2: Get Your DSN

1. In your Sentry project, go to **Settings** → **Client Keys (DSN)**
2. Copy your **DSN** value (looks like: `https://your-dsn@sentry.io/project-id`)

## Step 3: Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp frontend/.env.production.example frontend/.env.production
   ```

2. Edit `frontend/.env.production` and replace:
   ```
   NEXT_PUBLIC_SENTRY_DSN=https://your-dsn@sentry.io/project-id
   ```
   with your actual DSN from Step 2.

3. Update other variables as needed:
   - `NEXT_PUBLIC_VERSION`: Your application version
   - `NEXT_PUBLIC_COMMIT_SHA`: Git commit hash (optional)
   - `SENTRY_TRACES_SAMPLE_RATE`: Percentage of transactions to sample (0.0-1.0)

## Step 4: Verify Configuration

The monitoring service is already integrated in your application:

```typescript
// frontend/src/services/monitoringService.ts
import { monitoringService } from './monitoringService';

// Initialize in your app (already done automatically)
monitoringService.initialize({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  tracesSampleRate: 0.1, // 10% of transactions
});
```

## Step 5: Build and Deploy

1. Build your application:
   ```bash
   cd frontend
   npm run build:prod
   ```

2. Deploy to your hosting platform

## Step 6: Verify Monitoring

After deployment, you should see:

1. **Error tracking**: Automatic JavaScript error collection
2. **Performance data**: Page load times, API response times
3. **Web Vitals**: Core Web Vitals metrics (LCP, FID, CLS)
4. **User sessions**: Real user monitoring data

## Monitoring Dashboard Features

### Performance Metrics
- **Core Web Vitals**: LCP, FID, CLS scores
- **Custom metrics**: API response times, render performance
- **Memory usage**: Heap size monitoring
- **Long tasks**: Main thread blocking detection

### Error Tracking
- **JavaScript errors**: Automatic error capture
- **API failures**: Request/response error tracking
- **User context**: Session information and user actions

### Performance Insights
- **Release comparison**: Performance changes between versions
- **Browser/device breakdown**: Performance by platform
- **Geographic distribution**: Performance by region

## Configuration Options

### Sampling Rates
Adjust based on your needs and Sentry plan limits:

```typescript
// In monitoringService.ts initialization
tracesSampleRate: 0.1,    // 10% of transactions
profilesSampleRate: 0.1,  // 10% of user profiles
```

### Custom Tags
Add context to your monitoring data:

```typescript
monitoringService.setTags({
  environment: 'production',
  version: '1.0.0',
  feature: 'dashboard'
});
```

### Custom Metrics
Track application-specific performance:

```typescript
import { webVitalsService } from './webVitalsService';

// Track custom performance metric
webVitalsService.trackCustomMetric('chart_render_time', 150, {
  chart_type: 'candlestick',
  data_points: '1000'
});
```

## Troubleshooting

### No Data in Sentry
1. Check that `NEXT_PUBLIC_SENTRY_DSN` is correctly set
2. Verify your build process includes the environment variables
3. Check browser console for any Sentry initialization errors

### Performance Data Missing
1. Ensure `tracesSampleRate` is set > 0
2. Verify you're on a paid Sentry plan for performance monitoring
3. Check that your browser supports required APIs

### Too Much Data
1. Reduce sampling rates:
   ```typescript
   tracesSampleRate: 0.05, // Reduce to 5%
   ```
2. Add filters to ignore specific errors

## Best Practices

1. **Environment-specific DSNs**: Use different DSNs for development, staging, and production
2. **Version tracking**: Always include version information for release comparison
3. **Sampling**: Adjust sampling rates based on your traffic and Sentry plan
4. **Privacy**: Avoid sending sensitive user data or PII to Sentry

## Security Notes

- The monitoring service automatically filters out sensitive data
- Chrome extensions errors are ignored by default
- Local file URLs are denied for security
- Personal user information should not be sent to Sentry

## Cost Considerations

- **Free tier**: Includes error tracking and limited performance monitoring
- **Performance monitoring**: Requires a paid plan
- **Data volume**: Adjust sampling rates to control costs
- **Retention**: Configure data retention policies in Sentry

## Support

For Sentry-specific issues:
- [Sentry Documentation](https://docs.sentry.io/)
- [Sentry Support](https://sentry.io/support/)

For application integration issues:
- Check the implementation in `frontend/src/services/monitoringService.ts`
- Review the Web Vitals service in `frontend/src/services/webVitalsService.ts`
- Verify environment variable configuration