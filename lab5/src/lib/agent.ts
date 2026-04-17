// lab5/src/lib/agent.ts
/**
 * ReAct agent loop — Week 7.
 *
 * Pattern: Plan → Act → Observe → repeat until end_turn or loop limit.
 *
 * Contracts established in design:
 *   - MAX_AGENT_LOOPS from env var, default 5 (never hardcoded)
 *   - Tool failure handled by system prompt instructions, not loop code
 *   - Loop code owns the ceiling; model operates within it
 *   - Every step emitted as a structured AgentStep for UI + observability
 */

import Anthropic from "@anthropic-ai/sdk";
import { MessageParam } from "@anthropic-ai/sdk/resources/messages";
import { AGENT_TOOLS, executeTool, ToolResult } from "./tools";

const client = new Anthropic();

// ---------------------------------------------------------------------------
// Config — env var with safe default. Never hardcoded (design decision #2).
// ---------------------------------------------------------------------------
const MAX_AGENT_LOOPS = parseInt(
  process.env.MAX_AGENT_LOOPS ?? "5",
  10
);

// ---------------------------------------------------------------------------
// System prompt — owns the failure protocol (design decision #3).
// Tool criticality tiering lives here, not in loop code.
// ---------------------------------------------------------------------------
const AGENT_SYSTEM_PROMPT = `You are a research assistant with access to tools.
Your job is to answer the user's question thoroughly using the available tools,
then synthesize a clear, structured response.

## Tools available
- search_documents: Search the company knowledge base. Use for any question
  about company policies, procedures, or documentation.
- get_current_weather: Get weather for a location.
- save_reminder: Save a reminder for the user.

## Research process
1. Identify which tools are relevant to the user's question.
2. Call the relevant tools to gather information.
3. When you have enough information, stop calling tools and write your response.
4. Do not call the same tool with the same arguments twice.
5. Do not call more tools than necessary — stop when you have what you need.

## Stopping condition
When stop_reason is end_turn, you are done. Write your final response.
Do not keep calling tools if you already have the information needed.

## Tool Failure Protocol

TIER 1 — CORE (search_documents):
If search_documents returns {"error": true}, immediately stop research.
Do not substitute other tools. Respond:
"I was unable to complete this research task. The document search tool is
currently unavailable. Please try again later."
Do not fabricate information that would have come from search.

TIER 2 — SUPPLEMENTARY (get_current_weather):
If get_current_weather returns {"error": true}, note the limitation and
continue with the rest of the task. Include: "Note: weather data was
unavailable for this query."

TIER 3 — WRITE (save_reminder):
If save_reminder returns {"error": true}, complete the research task normally
and note the reminder failure briefly at the end.

In all cases: never present information as retrieved if it was not.
An honest partial result is always preferred over a fabricated complete result.`;

// ---------------------------------------------------------------------------
// Types — structured step output for UI and observability (Taylor + Casey)
// ---------------------------------------------------------------------------
export type AgentStepType =
  | "planning"      // first message sent, no tool call yet
  | "tool_call"     // model called a tool
  | "tool_result"   // tool returned a result
  | "synthesizing"  // model has all info, writing final response
  | "complete"      // final response ready
  | "loop_limit"    // terminated at MAX_AGENT_LOOPS with partial result
  | "error";        // unexpected error in the loop itself

export interface AgentStep {
  type: AgentStepType;
  toolName?: string;
  toolInput?: Record<string, unknown>;
  toolResult?: ToolResult;
  text?: string;
  loopIndex?: number;
  maxLoops?: number;
  durationMs?: number;
}

export interface AgentResult {
  steps: AgentStep[];
  finalResponse: string;
  loopsUsed: number;
  maxLoops: number;
  terminatedEarly: boolean;
}

// ---------------------------------------------------------------------------
// runAgent — the ReAct loop.
// ---------------------------------------------------------------------------
export async function runAgent(userQuery: string): Promise<AgentResult> {
  const steps: AgentStep[] = [];
  const messages: MessageParam[] = [
    { role: "user", content: userQuery },
  ];

  let loopsUsed = 0;
  let terminatedEarly = false;
  let finalResponse = "";

  // Emit planning step — agent has received the task
  steps.push({ type: "planning", text: userQuery });

  // -------------------------------------------------------------------------
  // ReAct loop
  // -------------------------------------------------------------------------
  while (loopsUsed < MAX_AGENT_LOOPS) {
    loopsUsed++;
    const loopStart = Date.now();

    // Determine step type — synthesizing if we've already done tool calls
    const hasToolCalls = steps.some((s) => s.type === "tool_call");
    if (hasToolCalls) {
      steps.push({
        type: "synthesizing",
        loopIndex: loopsUsed,
        maxLoops: MAX_AGENT_LOOPS,
      });
    }

    // Call Claude
    const response = await client.messages.create({
      model: "claude-sonnet-4-6",
      max_tokens: 4096,
      system: AGENT_SYSTEM_PROMPT,
      tools: AGENT_TOOLS,
      messages,
    });

    const durationMs = Date.now() - loopStart;

    // Add assistant response to conversation history
    messages.push({ role: "assistant", content: response.content });

    // ------------------------------------------------------------------
    // Case 1: Model is done — end_turn with no tool calls
    // ------------------------------------------------------------------
    if (response.stop_reason === "end_turn") {
      const textBlock = response.content.find((b) => b.type === "text");
      finalResponse = textBlock?.type === "text" ? textBlock.text : "";

      steps.push({
        type: "complete",
        text: finalResponse,
        loopIndex: loopsUsed,
        durationMs,
      });
      break;
    }

    // ------------------------------------------------------------------
    // Case 2: Model called one or more tools
    // ------------------------------------------------------------------
    if (response.stop_reason === "tool_use") {
      const toolUseBlocks = response.content.filter(
        (b) => b.type === "tool_use"
      );

      // Execute each tool call and collect results
      const toolResults = [];

      for (const block of toolUseBlocks) {
        if (block.type !== "tool_use") continue;

        const toolCallStart = Date.now();

        // Emit tool_call step (Casey's UI state)
        steps.push({
          type: "tool_call",
          toolName: block.name,
          toolInput: block.input as Record<string, unknown>,
          loopIndex: loopsUsed,
        });

        // Execute the tool via HTTP to Python backend
        const result = await executeTool(
          block.name,
          block.input as Record<string, unknown>
        );

        // Emit tool_result step
        steps.push({
          type: "tool_result",
          toolName: block.name,
          toolResult: result,
          loopIndex: loopsUsed,
          durationMs: Date.now() - toolCallStart,
        });

        // Collect for conversation history
        toolResults.push({
          type: "tool_result" as const,
          tool_use_id: block.id,
          content: JSON.stringify(result),
        });
      }

      // Add tool results to conversation history so model can observe them
      messages.push({ role: "user", content: toolResults });
      continue;
    }

    // ------------------------------------------------------------------
    // Case 3: Unexpected stop reason — treat as complete
    // ------------------------------------------------------------------
    const textBlock = response.content.find((b) => b.type === "text");
    finalResponse = textBlock?.type === "text" ? textBlock.text : "";
    steps.push({ type: "complete", text: finalResponse, loopIndex: loopsUsed });
    break;
  }

  // -------------------------------------------------------------------------
  // Loop limit reached — terminate gracefully with partial result
  // Jordan: hard ceiling enforced here, never in the model
  // -------------------------------------------------------------------------
  if (loopsUsed >= MAX_AGENT_LOOPS && finalResponse === "") {
    terminatedEarly = true;
    finalResponse =
      "I was unable to complete this research task within the allowed " +
      `number of steps (${MAX_AGENT_LOOPS}). Here is what I found so far: ` +
      steps
        .filter((s) => s.type === "tool_result")
        .map((s) => JSON.stringify(s.toolResult))
        .join("\n");

    steps.push({
      type: "loop_limit",
      text: finalResponse,
      loopIndex: loopsUsed,
      maxLoops: MAX_AGENT_LOOPS,
    });
  }

  return { steps, finalResponse, loopsUsed, maxLoops: MAX_AGENT_LOOPS, terminatedEarly };
}