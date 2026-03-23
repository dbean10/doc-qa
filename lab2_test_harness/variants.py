# lab2/variants.py
# The 5 prompt variants — one per technique.
# Task: classify a user message as a question, command, or statement.
# (Simple enough to reason about, complex enough to show technique differences.)

from harness import PromptVariant

VARIANTS: list[PromptVariant] = [

    PromptVariant(
        name="zero_shot",
        technique="zero_shot",
        system_prompt="""Classify the user's message as one of: question, command, statement.
Respond with a JSON object: {"classification": "<type>", "confidence": <0.0-1.0>}""",
    ),

    PromptVariant(
        name="few_shot_3",
        technique="few_shot",
        system_prompt="""Classify user messages as: question, command, or statement.

Examples:
User: "What time is it?"
{"classification": "question", "confidence": 0.99}

User: "Open the settings menu."
{"classification": "command", "confidence": 0.97}

User: "The meeting starts at 3pm."
{"classification": "statement", "confidence": 0.95}

Respond only with the JSON object. No explanation.""",
    ),

    PromptVariant(
        name="cot_json",
        technique="cot",
        system_prompt="""Classify user messages as question, command, or statement.

First, think through the classification step by step in a <reasoning> tag.
Then provide your final answer as JSON.

Format:
<reasoning>
[your step-by-step reasoning here]
</reasoning>
{"classification": "<type>", "confidence": <0.0-1.0>}""",
    ),

    PromptVariant(
        name="role_expert",
        technique="role",
        system_prompt="""You are a computational linguist specialising in intent classification.
You have published research on distinguishing interrogatives, imperatives, and declaratives
across natural language inputs, including ambiguous and adversarial cases.

Classify the user's message as: question, command, or statement.
When a message is ambiguous, explain why and pick the most likely intent.
Respond with: {"classification": "<type>", "confidence": <0.0-1.0>, "ambiguous": <bool>}""",
    ),

    PromptVariant(
        name="structured_strict",
        technique="structured",
        system_prompt="""You are a classification API endpoint. You receive text and return JSON.

OUTPUT RULES:
- Respond ONLY with a valid JSON object
- No preamble, no explanation, no markdown
- Required fields: classification (string), confidence (float 0-1), reasoning (string ≤ 20 words)
- classification must be exactly one of: "question" | "command" | "statement"
- If uncertain, pick the closest match and set confidence below 0.6

{"classification": "...", "confidence": 0.0, "reasoning": "..."}""",
    ),
]