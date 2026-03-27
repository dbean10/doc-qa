// src/lib/sanitize.ts

export interface Message {
    role: "user" | "assistant"
    content: string
  }
  
  // Known prompt injection patterns — belt layer
  // Real defense is role isolation (user content never interpolated into system prompt)
  const INJECTION_PATTERNS = [
    /ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)/gi,
    /you\s+are\s+now\s+/gi,
    /act\s+as\s+(a\s+)?(?!writing|an?\s+writing)/gi,
    /pretend\s+(you\s+are|to\s+be)/gi,
    /<\s*system\s*>/gi,
    /\[INST\]/gi,
    /###\s*instruction/gi,
  ]
  
  const MAX_MESSAGE_LENGTH = 4000  // chars per message
  const MAX_HISTORY_TURNS = 20     // messages in conversation
  
  export function sanitizeMessages(messages: Message[]): Message[] {
    // 1. Enforce history limit — controls cost and injection surface area
    const trimmed = messages.slice(-MAX_HISTORY_TURNS)
  
    // 2. Sanitize each message
    return trimmed.map(msg => ({
      role: msg.role,
      content: sanitizeContent(msg.content),
    }))
  }
  
  function sanitizeContent(content: string): string {
    // 3. Truncate oversized messages
    let sanitized = content.slice(0, MAX_MESSAGE_LENGTH)
  
    // 4. Strip known injection patterns
    for (const pattern of INJECTION_PATTERNS) {
      sanitized = sanitized.replace(pattern, "[removed]")
    }
  
    return sanitized.trim()
  }
  
  // Validate message shape before it touches the API
  export function validateMessages(messages: unknown): messages is Message[] {
    if (!Array.isArray(messages)) return false
    if (messages.length === 0) return false
    return messages.every(
      m =>
        typeof m === "object" &&
        m !== null &&
        (m as Message).role === "user" || (m as Message).role === "assistant" &&
        typeof (m as Message).content === "string"
    )
  }