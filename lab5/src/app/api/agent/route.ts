// lab5/src/app/api/agent/route.ts
import { NextRequest } from "next/server";
import { randomUUID } from "crypto";
import { runAgent } from "@/lib/agent";
import { scrubPII } from "@/lib/pii";
import { logRequest, hashIP } from "@/lib/logger";

export const dynamic = "force-dynamic";

// Agent system prompt hash — same pattern as /api/chat
const AGENT_SYSTEM_PROMPT_SENTINEL =
  "agent-v1-research-react-loop";

export async function POST(req: NextRequest) {
  const startTime = Date.now();

  try {
    const body = await req.json();
    const query = body.query?.trim() ?? "";

    if (!query) {
      return new Response(JSON.stringify({ error: "query is required" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    // Get IP for rate limit audit — hashed before storage
    const ip =
      req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ??
      "unknown";

    // Run the ReAct loop
    const result = await runAgent(query);
    const durationMs = Date.now() - startTime;

    // Log to Turso — match exact LogEntry shape from logger.ts
    try {
      await logRequest({
        requestId: randomUUID(),
        model: "claude-sonnet-4-6",
        inputTokens: 0,        // multi-turn — token sum deferred to Week 8
        outputTokens: 0,
        latencyMs: durationMs,
        systemPrompt: AGENT_SYSTEM_PROMPT_SENTINEL,
        ipHash: hashIP(ip),
        scrubbedInput: scrubPII(query),
        scrubbedOutput: scrubPII(result.finalResponse),
        rateLimited: false,
        error: result.terminatedEarly ? "loop_limit_reached" : undefined,
      });
    } catch (logErr) {
      // Logger errors never crash the request
      console.error("[agent] log error:", logErr);
    }

    return new Response(JSON.stringify(result), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });

  } catch (err) {
    console.error("[agent] error:", err);
    return new Response(
      JSON.stringify({
        error: "Agent loop failed",
        detail: err instanceof Error ? err.message : "Unknown error",
      }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
}
