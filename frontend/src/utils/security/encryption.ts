/**
 * 数据加密工具
 *
 * 功能:
 * 1. 敏感数据存储加密
 * 2. 数据库字段级加密
 * 3. 环境变量加密机制
 * 4. 加密密钥管理
 */

// 简化的加密实现（生产环境应使用Web Crypto API）
export class Encryption {
  private static algorithm = 'AES-GCM';
  private static keyLength = 256;

  /**
   * 生成随机密钥
   */
  static generateKey(): string {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
  }

  /**
   * 简单加密（仅用于演示，生产环境需要更强的加密）
   */
  static async encrypt(text: string, key: string): Promise<string> {
    try {
      // 在浏览器环境中使用Web Crypto API
      const encoder = new TextEncoder();
      const data = encoder.encode(text);

      // 生成IV
      const iv = crypto.getRandomValues(new Uint8Array(12));

      // 导入密钥
      const keyData = await crypto.subtle.importKey(
        'raw',
        new TextEncoder().encode(key.padEnd(32, '0').slice(0, 32)),
        { name: 'AES-GCM' },
        false,
        ['encrypt']
      );

      // 加密
      const encrypted = await crypto.subtle.encrypt(
        { name: 'AES-GCM', iv },
        keyData,
        data
      );

      // 组合IV和加密数据
      const combined = new Uint8Array(iv.length + encrypted.byteLength);
      combined.set(iv);
      combined.set(new Uint8Array(encrypted), iv.length);

      return btoa(String.fromCharCode(...combined));
    } catch (error) {
      console.error('加密失败:', error);
      throw new Error('加密失败');
    }
  }

  /**
   * 简单解密
   */
  static async decrypt(encryptedText: string, key: string): Promise<string> {
    try {
      const combined = new Uint8Array(
        atob(encryptedText).split('').map(c => c.charCodeAt(0))
      );

      const iv = combined.slice(0, 12);
      const encrypted = combined.slice(12);

      const keyData = await crypto.subtle.importKey(
        'raw',
        new TextEncoder().encode(key.padEnd(32, '0').slice(0, 32)),
        { name: 'AES-GCM' },
        false,
        ['decrypt']
      );

      const decrypted = await crypto.subtle.decrypt(
        { name: 'AES-GCM', iv },
        keyData,
        encrypted
      );

      return new TextDecoder().decode(decrypted);
    } catch (error) {
      console.error('解密失败:', error);
      throw new Error('解密失败');
    }
  }

  /**
   * 哈希密码
   */
  static async hashPassword(password: string): Promise<string> {
    const encoder = new TextEncoder();
    const data = encoder.encode(password);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }
}

// 密钥管理
export class KeyManager {
  private static readonly KEY_PREFIX = 'quant_trading_';
  private static readonly KEYS = {
    ENCRYPTION_KEY: 'ENCRYPTION_KEY',
    API_SECRET: 'API_SECRET',
    JWT_SECRET: 'JWT_SECRET'
  };

  /**
   * 获取密钥
   */
  static getKey(keyName: string): string {
    const storageKey = this.KEY_PREFIX + keyName;
    return localStorage.getItem(storageKey) || '';
  }

  /**
   * 设置密钥
   */
  static setKey(keyName: string, value: string): void {
    const storageKey = this.KEY_PREFIX + keyName;
    localStorage.setItem(storageKey, value);
  }

  /**
   * 删除密钥
   */
  static deleteKey(keyName: string): void {
    const storageKey = this.KEY_PREFIX + keyName;
    localStorage.removeItem(storageKey);
  }

  /**
   * 获取加密密钥
   */
  static getEncryptionKey(): string {
    let key = this.getKey(this.KEYS.ENCRYPTION_KEY);
    if (!key) {
      key = Encryption.generateKey();
      this.setKey(this.KEYS.ENCRYPTION_KEY, key);
    }
    return key;
  }
}

export default Encryption;