"""
token_tracker.py — Tracks token usage and cost per turn and per session.

Jordan Rivera: "Log everything. Per turn, not averaged. You cannot
diagnose unexpected cost spikes from averages — you need the per-call
data. Taylor reads this in Week 6 to build the cost dashboard."

Sam Park: "Pricing constants live here, not scattered across lab code.
When Anthropic changes pricing, you change one file."
"""

import json
import time
from dataclasses import dataclass
from pathlib import Path

# ─── Pricing — claude-sonnet-4-6 as of March 2026 ────────────────────────────
# Update here if pricing changes. All values in USD per million tokens.
INPUT_PRICE_PER_M: float = 3.00
OUTPUT_PRICE_PER_M: float = 15.00


def _cost_usd(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1_000_000 * INPUT_PRICE_PER_M) + (
        output_tokens / 1_000_000 * OUTPUT_PRICE_PER_M
    )


@dataclass
class TurnLog:
    """Single turn record. Maps directly to JSONL log schema."""
    turn: int
    input_tokens: int
    output_tokens: int
    first_token_ms: float | None
    total_ms: float
    cost_usd: float
    call_type: str          # "chat" | "summarize" | "warmup"
    timestamp_utc: str


class TokenTracker:
    def __init__(self, log_dir: str = "lab3/results"):
        self.session_input_tokens: int = 0
        self.session_output_tokens: int = 0
        self.session_cost_usd: float = 0.0
        self.turn_count: int = 0
        self.logs: list[TurnLog] = []

        # Set up log file
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        self.log_path = Path(log_dir) / f"run_{run_id}.jsonl"

    def log_turn(
        self,
        input_tokens: int,
        output_tokens: int,
        first_token_ms: float | None,
        total_ms: float,
        call_type: str = "chat",
    ) -> TurnLog:
        """
        Record a completed turn. Writes to JSONL immediately.
        Jordan Rivera: "Write on every turn, not at session end.
        If the process crashes mid-session, you still have the data."
        """
        self.turn_count += 1
        cost = _cost_usd(input_tokens, output_tokens)

        self.session_input_tokens += input_tokens
        self.session_output_tokens += output_tokens
        self.session_cost_usd += cost

        log = TurnLog(
            turn=self.turn_count,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            first_token_ms=round(first_token_ms, 1) if first_token_ms else None,
            total_ms=round(total_ms, 1),
            cost_usd=round(cost, 6),
            call_type=call_type,
            timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        self.logs.append(log)
        self._write(log)
        return log

    def _write(self, log: TurnLog) -> None:
        with open(self.log_path, "a") as f:
            f.write(json.dumps(log.__dict__) + "\n")

    def print_turn_summary(self, log: TurnLog) -> None:
        ftok = f"{log.first_token_ms:.0f}ms" if log.first_token_ms else "n/a"
        print(
            f"  ↳ tokens in={log.input_tokens} out={log.output_tokens} "
            f"| first={ftok} total={log.total_ms:.0f}ms "
            f"| ${log.cost_usd:.5f}"
        )

    def print_session_summary(self) -> None:
        print("\n" + "─" * 50)
        print("Session summary")
        print(f"  Turns:         {self.turn_count}")
        print(f"  Input tokens:  {self.session_input_tokens:,}")
        print(f"  Output tokens: {self.session_output_tokens:,}")
        print(f"  Total cost:    ${self.session_cost_usd:.4f}")
        print(f"  Log:           {self.log_path}")
        print("─" * 50)