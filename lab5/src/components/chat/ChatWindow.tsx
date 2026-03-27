// src/components/chat/ChatWindow.tsx
"use client"

import { useEffect, useRef } from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { MessageBubble } from "./MessageBubble"
import { InputBar } from "./InputBar"
import { useChat } from "@/hooks/useChat"

export function ChatWindow() {
  const { messages, isLoading, sendMessage, cancelStream } = useChat()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  return (
    <div className="flex flex-col h-full overflow-hidden">

      <ScrollArea className="flex-1 h-0">
        <div className="py-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 gap-3 text-muted-foreground">
              <p className="text-lg font-medium">AI Writing Assistant</p>
              <p className="text-sm text-center max-w-sm">
                Ask me to help draft, edit, or improve your writing.
                I can suggest edits, fix grammar, adjust tone, or help you start from scratch.
              </p>
            </div>
          ) : (
            messages.map(message => (
              <MessageBubble key={message.id} message={message} />
            ))
          )}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      <InputBar
        onSend={sendMessage}
        onCancel={cancelStream}
        isLoading={isLoading}
      />
    </div>
  )
}