// src/app/page.tsx
import { ChatWindow } from "@/components/chat/ChatWindow"

export default function Home() {
  return (
    <main className="flex flex-col h-screen max-w-3xl mx-auto">
      <header className="flex items-center justify-between px-6 py-4 border-b">
        <div>
          <h1 className="text-lg font-semibold">AI Writing Assistant</h1>
          <p className="text-xs text-muted-foreground">Powered by Claude · Week 5</p>
        </div>
      </header>
      <div className="flex-1 overflow-hidden">
        <ChatWindow />
      </div>
    </main>
  )
}