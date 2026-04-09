import { db } from './db';
import { createHash } from 'crypto';

export interface LogEntry {
  requestId: string;
  model: string;
  inputTokens: number;
  outputTokens: number;
  latencyMs: number;
  systemPrompt: string;
  ipHash: string;
  scrubbedInput?: string;
  scrubbedOutput?: string;
  rateLimited?: boolean;
  error?: string;
}

export function hashPrompt(systemPrompt: string): string {
  return createHash('sha256').update(systemPrompt).digest('hex').slice(0, 16);
}

export function hashIP(ip: string): string {
  return createHash('sha256').update(ip).digest('hex').slice(0, 16);
}

export async function logRequest(entry: LogEntry): Promise<void> {
  try {
    await db.execute({
      sql: `
        INSERT INTO request_logs (
          request_id, timestamp, model,
          input_tokens, output_tokens, latency_ms,
          prompt_hash, ip_hash,
          scrubbed_input, scrubbed_output,
          rate_limited, error
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `,
      args: [
        entry.requestId,
        new Date().toISOString(),
        entry.model,
        entry.inputTokens,
        entry.outputTokens,
        entry.latencyMs,
        hashPrompt(entry.systemPrompt),
        entry.ipHash,
        entry.scrubbedInput ?? null,
        entry.scrubbedOutput ?? null,
        entry.rateLimited ? 1 : 0,
        entry.error ?? null,
      ],
    });
  } catch (err) {
    // Logger must never crash the request — log to console, swallow the error
    console.error('[logger] Failed to write request log:', err);
  }
}