// src/components/chat/InputBar.tsx
"use client"

import { useState, useRef, KeyboardEvent } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

interface InputBarProps {
  onSend: (message: string) => void
  onCancel: () => void
  isLoading: boolean
}

export function InputBar({ onSend, onCancel, isLoading }: InputBarProps) {
  const [value, setValue] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSend = () => {
    if (!value.trim() || isLoading) return
    onSend(value)
    setValue("")
    textareaRef.current?.focus()
  }

  // Submit on Enter, newline on Shift+Enter
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex gap-2 p-4 border-t bg-background">
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={e => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask Claude to help with your writing… (Enter to send, Shift+Enter for newline)"
        className="min-h-[60px] max-h-[200px] resize-none text-sm"
        disabled={isLoading}
      />
      <div className="flex flex-col gap-2">
        {isLoading ? (
          <Button variant="outline" size="sm" onClick={onCancel} className="h-full">
            Stop
          </Button>
        ) : (
          <Button size="sm" onClick={handleSend} disabled={!value.trim()} className="h-full">
            Send
          </Button>
        )}
      </div>
    </div>
  )
}