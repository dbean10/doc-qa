"""
message_history.py — Manages the messages[] array for multi-turn conversations.

Alex Chen: "This class owns the context window. Nothing outside it
should append to or read from messages[] directly."

Morgan Blake: "add_user() is the injection boundary. It does one thing:
append {role: user, content: raw_input} to messages. If you find
yourself building an f-string with user content anywhere other than
here, stop."
"""


class MessageHistory:
    def __init__(self):
        self.messages: list[dict] = []
        self.turn_count: int = 0

    def add_user(self, content: str) -> None:
        """
        Append a user message to history.
        Raw user input goes here and nowhere else — never into system prompt.
        """
        self.messages.append({"role": "user", "content": content})
        self.turn_count += 1

    def add_assistant(self, content: str) -> None:
        """
        Append an assembled assistant response to history.
        Call this after the stream is complete, not during.
        """
        self.messages.append({"role": "assistant", "content": content})

    def get_messages(self) -> list[dict]:
        """
        Return a defensive copy of the messages list.
        Prevents external code from mutating history state through
        the returned reference.
        """
        return self.messages.copy()

    def replace_with_summary(self, summary: str, keep_last_n: int = 4) -> None:
        """
        Replace old history with a summary message, keeping the
        most recent N messages intact for conversational continuity.

        Alex Chen: "keep_last_n=4 means 2 full turns (user+assistant).
        Enough for continuity. Too many and you defeat the compression."
        """
        recent = (
            self.messages[-keep_last_n:]
            if len(self.messages) > keep_last_n
            else self.messages
        )
        turns_compressed = self.turn_count - (len(recent) // 2)
        summary_message = {
            "role": "user",
            "content": (
                f"[Conversation summary — {turns_compressed} earlier turns]: "
                f"{summary}"
            ),
        }
        self.messages = [summary_message] + recent

    def token_estimate(self) -> int:
        """
        Quick local estimate of current history size in tokens.
        Uses the same ~3 chars/token approximation as config.count_tokens().
        Use count_tokens() from config for exact counts in GCP mode.
        """
        total_chars = sum(len(m["content"]) for m in self.messages)
        return total_chars // 3

    def __len__(self) -> int:
        return len(self.messages)

    def __repr__(self) -> str:
        return (
            f"MessageHistory(turns={self.turn_count}, "
            f"messages={len(self.messages)}, "
            f"~{self.token_estimate()} tokens)"
        )