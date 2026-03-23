# test_week3_step1.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import make_call_messages

messages = [
    {"role": "user", "content": "My name is David."},
    {"role": "assistant", "content": "Hello David, nice to meet you."},
    {"role": "user", "content": "What is my name?"},
]

resp = make_call_messages(messages, system="You are a helpful assistant.")
print(resp.content[0].text)
print(f"Tokens — in: {resp.usage.input_tokens}, out: {resp.usage.output_tokens}")