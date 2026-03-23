# test_week3_step2.py
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import make_stream_call

# warmup call — drains Ollama cold start, never measure this
print("Warming up...", end="", flush=True)
for _ in make_stream_call([{"role": "user", "content": "hi"}]):
    pass
print(" done\n")

# real test
messages = [{"role": "user", "content": "Count from 1 to 10, one number per line."}]

start = time.time()
first_token_ms = None
chunks_received = 0

print("Streaming response:")
for chunk in make_stream_call(messages):
    if first_token_ms is None:
        first_token_ms = (time.time() - start) * 1000
    print(chunk, end="", flush=True)
    chunks_received += 1

total_ms = (time.time() - start) * 1000
print(f"\n\nFirst token: {first_token_ms:.0f}ms")
print(f"Total time:  {total_ms:.0f}ms")
print(f"Chunks received: {chunks_received}")