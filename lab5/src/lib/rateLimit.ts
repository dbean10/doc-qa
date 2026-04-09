import { db } from './db';

const MAX_REQUESTS = parseInt(process.env.RATE_LIMIT_MAX ?? '20');
const WINDOW_MS = parseInt(process.env.RATE_LIMIT_WINDOW_MS ?? '60000');

export interface RateLimitResult {
  allowed: boolean;
  remaining: number;
  resetAt: string;
}

export async function checkRateLimit(ipHash: string): Promise<RateLimitResult> {
  const now = Date.now();
  const windowStart = new Date(
    Math.floor(now / WINDOW_MS) * WINDOW_MS
  ).toISOString();

  const resetAt = new Date(
    Math.floor(now / WINDOW_MS) * WINDOW_MS + WINDOW_MS
  ).toISOString();

  // Upsert: increment count if window row exists, insert with count 1 if not
  await db.execute({
    sql: `
      INSERT INTO rate_limit_windows (ip_hash, window_start, request_count)
      VALUES (?, ?, 1)
      ON CONFLICT (ip_hash, window_start)
      DO UPDATE SET request_count = request_count + 1
    `,
    args: [ipHash, windowStart],
  });

  const result = await db.execute({
    sql: `
      SELECT request_count
      FROM rate_limit_windows
      WHERE ip_hash = ? AND window_start = ?
    `,
    args: [ipHash, windowStart],
  });

  const count = result.rows[0]?.request_count as number ?? 1;
  const allowed = count <= MAX_REQUESTS;
  const remaining = Math.max(0, MAX_REQUESTS - count);

  return { allowed, remaining, resetAt };
}