import { Injectable } from '@nestjs/common';
import Redis from 'ioredis';
import { ISessionActivity } from '../../domain/ports/session-activity.port';

const ACTIVITY_PREFIX = 'last_activity:';
const WARNING_PREFIX = 'warning_sent:';
const ACTIVITY_TTL_SECONDS = 86400;
const WARNING_TTL_SECONDS = 120;

@Injectable()
export class RedisSessionActivityAdapter implements ISessionActivity {
  private readonly redis: Redis;

  constructor() {
    const url = this.buildUrl(
      process.env.REDIS_URL ?? 'redis://localhost:6379',
      process.env.REDIS_PASSWORD,
    );
    this.redis = new Redis(url, { lazyConnect: true });
    this.redis.on('error', (err) =>
      console.warn('[RedisSessionActivityAdapter] Redis error:', err.message),
    );
  }

  private buildUrl(rawUrl: string, password?: string): string {
    if (!password) return rawUrl;
    const parsed = new URL(rawUrl);
    parsed.username = parsed.username || 'default';
    parsed.password = password;
    return parsed.toString();
  }

  async updateLastActivity(sessionId: string): Promise<void> {
    await this.redis.setex(`${ACTIVITY_PREFIX}${sessionId}`, ACTIVITY_TTL_SECONDS, Date.now().toString());
    await this.redis.del(`${WARNING_PREFIX}${sessionId}`);
  }

  async getInactiveSessions(minInactiveMinutes: number): Promise<string[]> {
    const threshold = minInactiveMinutes * 60 * 1000;
    const now = Date.now();
    const inactive: string[] = [];

    let cursor = '0';
    do {
      const [nextCursor, keys] = await this.redis.scan(cursor, 'MATCH', `${ACTIVITY_PREFIX}*`, 'COUNT', 100);
      cursor = nextCursor;

      if (keys.length > 0) {
        const values = await this.redis.mget(...keys);
        for (let i = 0; i < keys.length; i++) {
          const ts = values[i];
          if (ts && now - parseInt(ts, 10) >= threshold) {
            inactive.push(keys[i].replace(ACTIVITY_PREFIX, ''));
          }
        }
      }
    } while (cursor !== '0');

    return inactive;
  }

  async markWarningSent(sessionId: string): Promise<void> {
    await this.redis.setex(`${WARNING_PREFIX}${sessionId}`, WARNING_TTL_SECONDS, '1');
  }

  async isWarningSent(sessionId: string): Promise<boolean> {
    const exists = await this.redis.exists(`${WARNING_PREFIX}${sessionId}`);
    return exists === 1;
  }

  async clearActivityKeys(sessionId: string): Promise<void> {
    await this.redis.del(`${ACTIVITY_PREFIX}${sessionId}`, `${WARNING_PREFIX}${sessionId}`);
  }
}
