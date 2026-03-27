// src/app/api/chat/route.ts
import Anthropic from "@anthropic-ai/sdk"
import { NextRequest } from "next/server"
import { sanitizeMessages, validateMessages } from "@/lib/sanitize"

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
})

const SYSTEM_PROMPT = `You are a helpful AI writing assistant. You help users draft, 
edit, and improve their writing. Be specific and constructive in your suggestions. 
When asked to edit, show what changed and why. Keep responses focused and concise.`

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()

    // Validate shape before touching anything
    if (!validateMessages(body.messages)) {
      return new Response("Invalid request", { status: 400 })
    }

    // Sanitize before the model sees it
    const sanitized = sanitizeMessages(body.messages)

    const stream = anthropic.messages.stream({
      model: "claude-sonnet-4-6",
      max_tokens: 1024,
      system: SYSTEM_PROMPT,
      messages: sanitized,
    })

    return new Response(stream.toReadableStream(), {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      },
    })
  } catch (error) {
    console.error("Chat API error:", error)
    return new Response("Internal server error", { status: 500 })
  }
}