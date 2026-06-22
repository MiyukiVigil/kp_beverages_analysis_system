import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5vl"


def run_qwen(text):
    prompt = f"""
You are a data extraction engine.

Extract drink names and prices from this OCR text.

Return ONLY valid JSON:

[
  {{"name": "string", "price": number}}
]

Rules:
- No explanations
- No markdown
- If price missing → null
- Clean messy OCR text

TEXT:
{text}
"""

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    res = requests.post(OLLAMA_URL, json=payload).json()
    output = res["response"]

    # safe JSON parsing
    try:
        return json.loads(output)
    except:
        start = output.find("[")
        end = output.rfind("]") + 1
        return json.loads(output[start:end])