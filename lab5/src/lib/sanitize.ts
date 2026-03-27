export interface Message {
  role: "user" | "assistant"
  content: string
}

const INJECTION_PATTERNS = [
  /ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)/gi,
  /you\s+are\s+now\s+/gi,
  /act\s+as\s+(a\s+)?(?!writing|an?\s+writing)/gi,
  /pretend\s+(you\s+are|to\s+be)/gi,
  /<\s*system\s*>/gi,
  /\[INST\]/gi,
  /###\s*instruction/gi,
]

const MAX_MESSAGE_LENGTH = 4000
const MAX_HISTORY_TURNS = 20

export function sanitizeMessages(messages: Message[]): Message[] {
  const trimmed = messages.slice(-MAX_HISTORY_TURNS)
  return trimmed.map(msg => ({
    role: msg.role,
    content: sanitizeContent(msg.content),
  }))
}

function sanitizeContent(content: string): string {
  let sanitized = content.slice(0, MAX_MESSAGE_LENGTH)
  for (const pattern of INJECTION_PATTERNS) {
    sanitized = sanitized.replace(pattern, "[removed]")
  }
  return sanitized.trim()
}

export function validateMessages(messages: unknown): messages is Message[] {
  if (!Array.isArray(messages)) return false
  if (messages.length === 0) return false
  return messages.every(
    m =>
      typeof m === "object" &&
      m !== null &&
      (
        (m as Message).role === "user" ||
        (m as Message).role === "assistant"
      ) &&
      typeof (m as Message).content === "string"
  )
}
