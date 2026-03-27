import { ThinkingIndicator } from "./ThinkingIndicator"
import { ChatMessage } from "@/hooks/useChat"
import ReactMarkdown from "react-markdown"

interface MessageBubbleProps {
  message: ChatMessage
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user"
  const isStreaming = message.status === "streaming"
  const isError = message.status === "error"

  if (isStreaming && !message.content) {
    return (
      <div className="flex justify-start px-4 py-2">
        <ThinkingIndicator />
      </div>
    )
  }

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} px-4 py-2`}>
      <div className={`flex flex-col gap-1 max-w-[80%] ${isUser ? "items-end" : "items-start"}`}>

        {/* Role label */}
        <span
          style={{
            fontSize: "11px",
            fontWeight: 500,
            padding: "2px 8px",
            borderRadius: "9999px",
            backgroundColor: isUser ? "#1a1a1a" : "#e5e7eb",
            color: isUser ? "#ffffff" : "#374151",
          }}
        >
          {isUser ? "You" : "Claude"}
        </span>

        {/* Message content */}
        <div
          className={`
            rounded-lg px-4 py-3 text-sm leading-relaxed
            ${isUser
              ? "bg-primary text-primary-foreground"
              : isError
                ? "border"
                : "bg-muted text-foreground"
            }
          `}
          style={isError ? {
            backgroundColor: "rgba(220,38,38,0.1)",
            color: "rgb(220,38,38)",
            borderColor: "rgba(220,38,38,0.2)"
          } : {}}
        >
          {isUser ? (
            <span className="whitespace-pre-wrap">{message.content}</span>
          ) : (
            <ReactMarkdown
              components={{
                p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                ul: ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-1">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-1">{children}</ol>,
                li: ({ children }) => <li>{children}</li>,
                code: ({ children }) => <code className="rounded px-1 py-0.5 font-mono text-xs" style={{backgroundColor: "rgba(0,0,0,0.08)"}}>{children}</code>,
              }}
            >
              {message.content}
            </ReactMarkdown>
          )}
          {isStreaming && (
            <span className="inline-block w-0.5 h-4 bg-current ml-0.5 animate-pulse" />
          )}
        </div>

      </div>
    </div>
  )
}
