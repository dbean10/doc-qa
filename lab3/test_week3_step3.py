# test_week3_step3.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import count_tokens

messages = [
    {"role": "user", "content": "My name is David."},
    {"role": "assistant", "content": "Hello David, nice to meet you."},
    {"role": "user", "content": "What is my name?"},
]

count = count_tokens(messages, system="You are a helpful assistant.")
print(f"Token count: {count}")
print(f"Step 1 actual was: 59")
print(f"Difference: {abs(count - 59)}")