// src/app/api/chat/route.ts
import Anthropic from "@anthropic-ai/sdk"
import { NextRequest } from "next/server"
import { randomUUID } from "crypto"
import { sanitizeMessages, validateMessages } from "@/lib/sanitize"
import { scrubPII } from "@/lib/pii"
import { checkRateLimit } from "@/lib/rateLimit"
import { logRequest, hashIP } from "@/lib/logger"

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
})

const SYSTEM_PROMPT = `You are a helpful AI writing assistant. You help users draft, 
edit, and improve their writing. Be specific and constructive in your suggestions. 
When asked to edit, show what changed and why. Keep responses focused and concise.`

const MODEL = "claude-sonnet-4-6"

export async function POST(req: NextRequest) {
  const requestId = randomUUID()
  const startTime = Date.now()

  // Derive IP hash for rate limiting and logging — never store raw IP
  const rawIP =
    req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ??
    req.headers.get("x-real-ip") ??
    "unknown"
  const ipHash = hashIP(rawIP)

  try {
    const body = await req.json()

    // 1. Validate shape before touching anything
    if (!validateMessages(body.messages)) {
      return new Response("Invalid request", { status: 400 })
    }

    // 2. Sanitize (existing injection defense)
    const sanitized = sanitizeMessages(body.messages)

    // 3. PII scrub before the API call — content must be clean
    //    before it leaves our trust boundary
    const scrubbed = sanitized.map((msg) => ({
      ...msg,
      content:
        typeof msg.content === "string"
          ? scrubPII(msg.content)
          : msg.content,
    }))

    // 4. Rate limit check — Turso-backed, accurate across invocations
    const { allowed, remaining, resetAt } = await checkRateLimit(ipHash)

    if (!allowed) {
      await logRequest({
        requestId,
        model: MODEL,
        inputTokens: 0,
        outputTokens: 0,
        latencyMs: Date.now() - startTime,
        systemPrompt: SYSTEM_PROMPT,
        ipHash,
        scrubbedInput: scrubbed.at(-1)?.content as string | undefined,
        rateLimited: true,
      })

      return new Response("Rate limit exceeded", {
        status: 429,
        headers: {
          "Retry-After": resetAt,
          "X-RateLimit-Remaining": "0",
          "X-RateLimit-Reset": resetAt,
        },
      })
    }

    // 5. Call Anthropic — content is scrubbed and validated
    const stream = anthropic.messages.stream({
      model: MODEL,
      max_tokens: 1024,
      system: SYSTEM_PROMPT,
      messages: scrubbed,
    })

    // 6. Log after stream completes — captures real token counts and latency
    stream.on("finalMessage", async (message) => {
      const scrubbedOutput =
        message.content[0]?.type === "text"
          ? scrubPII(message.content[0].text)
          : undefined

      await logRequest({
        requestId,
        model: MODEL,
        inputTokens: message.usage.input_tokens,
        outputTokens: message.usage.output_tokens,
        latencyMs: Date.now() - startTime,
        systemPrompt: SYSTEM_PROMPT,
        ipHash,
        scrubbedInput: scrubbed.at(-1)?.content as string | undefined,
        scrubbedOutput,
        rateLimited: false,
      })
    })  

    // 7. Return stream to client — rate limit headers included
    return new Response(stream.toReadableStream(), {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-RateLimit-Remaining": remaining.toString(),
        "X-RateLimit-Reset": resetAt,
      },
    })
  } catch (error) {
    // Log the error before returning 500
    await logRequest({
      requestId,
      model: MODEL,
      inputTokens: 0,
      outputTokens: 0,
      latencyMs: Date.now() - startTime,
      systemPrompt: SYSTEM_PROMPT,
      ipHash,
      rateLimited: false,
      error: error instanceof Error ? error.message : String(error),
    })

    console.error("Chat API error:", error)
    return new Response("Internal server error", { status: 500 })
  }
}