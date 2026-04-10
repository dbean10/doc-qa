// Claude Sonnet pricing as of Week 6
// Make these env vars so they survive a pricing change without a redeploy
const INPUT_COST_PER_M =
  parseFloat(process.env.COST_PER_INPUT_TOKEN_PER_M ?? '3.00')
const OUTPUT_COST_PER_M =
  parseFloat(process.env.COST_PER_OUTPUT_TOKEN_PER_M ?? '15.00')

export const ALERT_THRESHOLD_USD =
  parseFloat(process.env.COST_ALERT_THRESHOLD_USD ?? '1.00')

export function estimateCost(
  inputTokens: number,
  outputTokens: number
): number {
  const inputCost = (inputTokens / 1_000_000) * INPUT_COST_PER_M
  const outputCost = (outputTokens / 1_000_000) * OUTPUT_COST_PER_M
  return inputCost + outputCost
}

export function formatCost(usd: number): string {
  if (usd < 0.01) return `$${(usd * 100).toFixed(4)}¢`
  return `$${usd.toFixed(4)}`
}