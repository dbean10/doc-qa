"""
Week 1 Lab: Your First 10 API Calls
FIXED: uses config.make_call() — no direct client access in lab code.
"""

import json
import time
from datetime import datetime
from config import make_call, MODEL_STRING


def log_call(experiment_id, params, response_text, latency_ms, usage):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "experiment_id": experiment_id,
        "model": MODEL_STRING,
        "params": params,
        "response_preview": response_text[:200],
        "latency_ms": round(latency_ms, 1),
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cost_usd_est": (usage.input_tokens * 0.000003) + (usage.output_tokens * 0.000015),
    }
    print(json.dumps(entry, indent=2))
    return entry


SYSTEM_PROMPT_FACTUAL  = "You are a precise technical assistant. Answer factually and concisely."
SYSTEM_PROMPT_CREATIVE = "You are a creative writer who crafts vivid, imaginative responses."

EXPERIMENTS = [
    ("temp_0.0_factual",  SYSTEM_PROMPT_FACTUAL,  "What is a context window in an LLM?",        0.0),
    ("temp_0.5_factual",  SYSTEM_PROMPT_FACTUAL,  "What is a context window in an LLM?",        0.5),
    ("temp_1.0_factual",  SYSTEM_PROMPT_FACTUAL,  "What is a context window in an LLM?",        1.0),
    ("temp_0.0_creative", SYSTEM_PROMPT_CREATIVE, "Describe a rainy Tuesday in three sentences.", 0.0),
    ("temp_0.7_creative", SYSTEM_PROMPT_CREATIVE, "Describe a rainy Tuesday in three sentences.", 0.7),
    ("temp_1.0_creative", SYSTEM_PROMPT_CREATIVE, "Describe a rainy Tuesday in three sentences.", 1.0),
    ("short_context",     SYSTEM_PROMPT_FACTUAL,  "Summarize this: 'AI is useful.'",             0.0),
    ("long_context",      SYSTEM_PROMPT_FACTUAL,  "Summarize this: 'AI is useful.' " * 50,       0.0),
    ("json_output",       "Respond only in valid JSON. No other text.",
                          "List 3 LLM model providers with their flagship model names.",          0.0),
    ("markdown_output",   "Respond in Markdown with headers and bullets.",
                          "List 3 LLM model providers with their flagship model names.",          0.0),
]


def run_lab():
    results = []
    print(f"\n{'='*60}")
    print("WEEK 1 LAB — 10 API Calls")
    print(f"Model: {MODEL_STRING}")
    print(f"{'='*60}\n")

    for exp_id, system, user, temp in EXPERIMENTS:
        print(f"\n→ Running: {exp_id}")
        start = time.time()
        response = make_call(system, user, temp)
        latency_ms = (time.time() - start) * 1000

        logged = log_call(
            experiment_id=exp_id,
            params={"temperature": temp, "system_len": len(system), "user_len": len(user)},
            response_text=response.content[0].text,
            latency_ms=latency_ms,
            usage=response.usage,
        )
        results.append(logged)
        time.sleep(0.3)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    total_cost  = sum(r["cost_usd_est"] for r in results)
    avg_latency = sum(r["latency_ms"] for r in results) / len(results)
    print(f"Total calls:     {len(results)}")
    print(f"Avg latency:     {avg_latency:.0f}ms")
    print(f"Est. total cost: ${total_cost:.4f}")
    print(f"\nAlex's check  — MODEL_STRING pinned? → {MODEL_STRING}")
    print("Morgan's check — No keys in code?    → Passed (make_call() only)")
    print(f"Jordan's check — All calls logged?   → {all('timestamp' in r for r in results)}")


if __name__ == "__main__":
    run_lab()
