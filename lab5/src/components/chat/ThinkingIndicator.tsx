// src/components/chat/ThinkingIndicator.tsx
import { Skeleton } from "@/components/ui/skeleton"

export function ThinkingIndicator() {
  return (
    <div className="flex flex-col gap-2 max-w-[80%]">
      <Skeleton className="h-4 w-48" />
      <Skeleton className="h-4 w-64" />
      <Skeleton className="h-4 w-40" />
    </div>
  )
}