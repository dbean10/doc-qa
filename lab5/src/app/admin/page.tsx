import { db } from '@/lib/db'
import { estimateCost, formatCost, ALERT_THRESHOLD_USD } from '@/lib/costs'

interface DailyStats {
  totalRequests: number
  totalInputTokens: number
  totalOutputTokens: number
  avgLatencyMs: number
  rateLimitedCount: number
  estimatedCostUsd: number
}

interface RecentRequest {
  request_id: string
  timestamp: string
  model: string
  input_tokens: number
  output_tokens: number
  latency_ms: number
  rate_limited: number
  error: string | null
  prompt_hash: string
}

async function getDailyStats(): Promise<DailyStats> {
  const result = await db.execute(`
    SELECT
      COUNT(*)                              AS total_requests,
      COALESCE(SUM(input_tokens), 0)        AS total_input_tokens,
      COALESCE(SUM(output_tokens), 0)       AS total_output_tokens,
      COALESCE(AVG(latency_ms), 0)          AS avg_latency_ms,
      SUM(CASE WHEN rate_limited = 1 THEN 1 ELSE 0 END) AS rate_limited_count
    FROM request_logs
    WHERE timestamp >= date('now')
  `)

  const row = result.rows[0]
  const inputTokens = row.total_input_tokens as number
  const outputTokens = row.total_output_tokens as number

  return {
    totalRequests: row.total_requests as number,
    totalInputTokens: inputTokens,
    totalOutputTokens: outputTokens,
    avgLatencyMs: Math.round(row.avg_latency_ms as number),
    rateLimitedCount: row.rate_limited_count as number,
    estimatedCostUsd: estimateCost(inputTokens, outputTokens),
  }
}

async function getRecentRequests(): Promise<RecentRequest[]> {
  const result = await db.execute(`
    SELECT
      request_id, timestamp, model,
      input_tokens, output_tokens, latency_ms,
      rate_limited, error, prompt_hash
    FROM request_logs
    ORDER BY id DESC
    LIMIT 20
  `)
  return result.rows as unknown as RecentRequest[]
}

export default async function AdminPage() {
  const [stats, recent] = await Promise.all([
    getDailyStats(),
    getRecentRequests(),
  ])

  const overThreshold = stats.estimatedCostUsd >= ALERT_THRESHOLD_USD

  // Server-side cost alert — appears in Vercel function logs
  if (overThreshold) {
    console.warn(
      `[COST ALERT] Daily cost ${formatCost(stats.estimatedCostUsd)} ` +
      `exceeds threshold ${formatCost(ALERT_THRESHOLD_USD)}`
    )
  }

  return (
    <main style={{ fontFamily: 'monospace', padding: '2rem', maxWidth: '1100px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '1.25rem', marginBottom: '0.25rem' }}>
        doc-qa · Admin Dashboard
      </h1>
      <p style={{ color: '#666', fontSize: '0.8rem', marginBottom: '2rem' }}>
        Today · All times UTC · Prompt hash baseline: d05a31b469b4fe3f
      </p>

      {overThreshold && (
        <div style={{
          background: '#fff3cd', border: '1px solid #ffc107',
          borderRadius: '4px', padding: '0.75rem 1rem', marginBottom: '1.5rem',
          fontSize: '0.85rem'
        }}>
          ⚠️ Cost alert: daily spend {formatCost(stats.estimatedCostUsd)} exceeds
          threshold {formatCost(ALERT_THRESHOLD_USD)}
        </div>
      )}

      {/* Stats grid */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '1rem', marginBottom: '2rem'
      }}>
        {[
          { label: 'Requests today', value: stats.totalRequests },
          { label: 'Avg latency', value: `${stats.avgLatencyMs}ms` },
          { label: 'Est. cost today', value: formatCost(stats.estimatedCostUsd) },
          { label: 'Input tokens', value: stats.totalInputTokens.toLocaleString() },
          { label: 'Output tokens', value: stats.totalOutputTokens.toLocaleString() },
          { label: 'Rate limited', value: stats.rateLimitedCount },
        ].map(({ label, value }) => (
          <div key={label} style={{
            border: '1px solid #e0e0e0', borderRadius: '4px',
            padding: '1rem', background: '#fafafa'
          }}>
            <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.25rem' }}>
              {label}
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>
              {value}
            </div>
          </div>
        ))}
      </div>

      {/* Recent requests table */}
      <h2 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>
        Recent requests
      </h2>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e0e0e0', textAlign: 'left' }}>
              {['Time', 'Request ID', 'Prompt hash', 'In', 'Out', 'Latency', 'RL', 'Error'].map(h => (
                <th key={h} style={{ padding: '0.4rem 0.6rem', whiteSpace: 'nowrap' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {recent.map((r, i) => (
              <tr key={r.request_id} style={{
                borderBottom: '1px solid #f0f0f0',
                background: i % 2 === 0 ? '#fff' : '#fafafa'
              }}>
                <td style={{ padding: '0.4rem 0.6rem', whiteSpace: 'nowrap' }}>
                  {new Date(r.timestamp).toLocaleTimeString()}
                </td>
                <td style={{ padding: '0.4rem 0.6rem', color: '#666' }}>
                  {r.request_id.slice(0, 8)}…
                </td>
                <td style={{ padding: '0.4rem 0.6rem', color: '#666' }}>
                  {r.prompt_hash}
                </td>
                <td style={{ padding: '0.4rem 0.6rem' }}>{r.input_tokens}</td>
                <td style={{ padding: '0.4rem 0.6rem' }}>{r.output_tokens}</td>
                <td style={{ padding: '0.4rem 0.6rem' }}>{r.latency_ms}ms</td>
                <td style={{ padding: '0.4rem 0.6rem' }}>
                  {r.rate_limited ? '🚫' : '✓'}
                </td>
                <td style={{ padding: '0.4rem 0.6rem', color: '#c00' }}>
                  {r.error ?? '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  )
}