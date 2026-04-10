// src/hooks/useChat.ts
"use client"

import { useState, useRef, useCallback } from "react"
import { Message } from "@/lib/sanitize"

export type MessageStatus = "complete" | "streaming" | "error"

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  status: MessageStatus
}

export interface TokenUsage {
  inputTokens: number
  outputTokens: number
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tokenUsage, setTokenUsage] = useState<TokenUsage | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return

    setError(null)
    setTokenUsage(null)

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: content.trim(),
      status: "complete",
    }

    const assistantMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      status: "streaming",
    }

    setMessages(prev => [...prev, userMsg, assistantMsg])
    setIsLoading(true)

    abortRef.current = new AbortController()

    try {
      const history: Message[] = [...messages, userMsg].map(m => ({
        role: m.role,
        content: m.content,
      }))

      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: history }),
        signal: abortRef.current.signal,
      })

      if (!response.ok) {
        // Surface rate limit clearly
        if (response.status === 429) {
          const resetAt = response.headers.get('X-RateLimit-Reset')
          const resetMsg = resetAt
            ? ` Try again after ${new Date(resetAt).toLocaleTimeString()}.`
            : ''
          throw new Error(`Rate limit exceeded.${resetMsg}`)
        }
        throw new Error(`API error: ${response.status}`)
      }

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let accumulated = ""
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        // Buffer chunks — SSE events can split across read() boundaries
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")

        // Keep the last incomplete line in the buffer
        buffer = lines.pop() ?? ""

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed) continue
        
          // Handle both raw JSON (Anthropic SDK) and SSE format (data: prefix)
          const jsonStr = trimmed.startsWith("data:")
            ? trimmed.slice("data:".length).trim()
            : trimmed
          if (jsonStr === "[DONE]") continue

          try {
            const event = JSON.parse(jsonStr)

            // Content delta — append text to the assistant message
            if (
              event.type === "content_block_delta" &&
              event.delta?.type === "text_delta" &&
              event.delta?.text
            ) {
              accumulated += event.delta.text
              setMessages(prev =>
                prev.map(m =>
                  m.id === assistantMsg.id
                    ? { ...m, content: accumulated }
                    : m
                )
              )
            }

            // Message delta — carries final token usage
            if (
              event.type === "message_delta" &&
              event.usage?.output_tokens
            ) {
              // input_tokens is on message_start, output_tokens on message_delta
              // We capture both here from the cumulative usage object
              setTokenUsage(prev => ({
                inputTokens: prev?.inputTokens ?? 0,
                outputTokens: event.usage.output_tokens,
              }))
            }

            // Message start — carries input token count
            if (
              event.type === "message_start" &&
              event.message?.usage?.input_tokens
            ) {
              setTokenUsage({
                inputTokens: event.message.usage.input_tokens,
                outputTokens: 0,
              })
            }

          } catch {
            // Skip malformed lines
          }
        }
      }

      setMessages(prev =>
        prev.map(m =>
          m.id === assistantMsg.id ? { ...m, status: "complete" } : m
        )
      )
    } catch (err: unknown) {
      const isAbort = err instanceof Error && err.name === "AbortError"
      const errorText = isAbort
        ? "Cancelled."
        : err instanceof Error
          ? err.message
          : "Something went wrong. Your message is saved — try again."

      setMessages(prev =>
        prev.map(m =>
          m.id === assistantMsg.id
            ? { ...m, content: errorText, status: "error" }
            : m
        )
      )

      if (!isAbort) setError(errorText)
    } finally {
      setIsLoading(false)
    }
  }, [messages, isLoading])

  const cancelStream = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
    setError(null)
    setTokenUsage(null)
  }, [])

  return {
    messages,
    isLoading,
    error,
    tokenUsage,
    sendMessage,
    cancelStream,
    clearMessages,
  }
}