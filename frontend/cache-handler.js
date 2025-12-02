const fs = require('fs');
const path = require('path');

class IncrementalCache {
  constructor() {
    this.cacheDir = path.join(process.cwd(), '.next/cache/incremental');
    this.ensureCacheDir();
  }

  ensureCacheDir() {
    if (!fs.existsSync(this.cacheDir)) {
      fs.mkdirSync(this.cacheDir, { recursive: true });
    }
  }

  async get(key) {
    try {
      const cacheFile = path.join(this.cacheDir, key + '.json');
      if (fs.existsSync(cacheFile)) {
        const content = fs.readFileSync(cacheFile, 'utf8');
        const data = JSON.parse(content);

        // Check if cache is still valid (24 hours)
        if (Date.now() - data.timestamp < 24 * 60 * 60 * 1000) {
          return data.value;
        }
      }
    } catch (error) {
      console.warn('Cache get error:', error);
    }
    return null;
  }

  async set(key, value) {
    try {
      const cacheFile = path.join(this.cacheDir, key + '.json');
      const data = {
        timestamp: Date.now(),
        value,
      };
      fs.writeFileSync(cacheFile, JSON.stringify(data, null, 2));
    } catch (error) {
      console.warn('Cache set error:', error);
    }
  }
}

module.exports = new IncrementalCache();
