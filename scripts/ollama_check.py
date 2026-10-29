"""Check Ollama structured output: python scripts\\ollama_check.py [model]"""
import sys

import httpx

model = sys.argv[1] if len(sys.argv) > 1 else "gemma4:e4b"
body = {
    "model": model,
    "stream": False,
    "think": False,  # skip the model's reasoning pass; we only want the JSON
    "messages": [{"role": "user", "content": "Reply with a JSON object with key ok set to true."}],
    # The same mechanism P6 will use: a JSON schema in the format field
    "format": {
        "type": "object",
        "properties": {"ok": {"type": "boolean"}},
        "required": ["ok"],
    },
    # optional 2nd arg: number of GPU layers; 0 forces CPU-only
    "options": {"temperature": 0, **({"num_gpu": int(sys.argv[2])} if len(sys.argv) > 2 else {})},
}
# The first call can take a while because the model has to load into memory
r = httpx.post("http://localhost:11434/api/chat", json=body, timeout=180)
print(r.status_code)
print(r.text)