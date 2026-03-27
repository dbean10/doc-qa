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

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return

    setError(null)

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
      // Build history for the API — only role + content
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
        throw new Error(`API error: ${response.status}`)
      }

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let accumulated = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })

        // Each chunk may contain multiple JSON lines
        for (const line of chunk.split("\n")) {
          const trimmed = line.trim()
          if (!trimmed) continue

          try {
            const event = JSON.parse(trimmed)
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
          } catch {
            // Skip malformed lines — SSE can split across chunks
          }
        }
      }

      // Mark complete
      setMessages(prev =>
        prev.map(m =>
          m.id === assistantMsg.id ? { ...m, status: "complete" } : m
        )
      )
    } catch (err: unknown) {
      const isAbort = err instanceof Error && err.name === "AbortError"
      const errorText = isAbort
        ? "Cancelled."
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
  }, [])

  return { messages, isLoading, error, sendMessage, cancelStream, clearMessages }
}