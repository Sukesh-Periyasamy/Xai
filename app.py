import os
import sys
import json
import requests

def load_dotenv(path='.env'):
  """Very small .env loader: reads KEY=VALUE lines and sets os.environ for missing keys."""
  if not os.path.exists(path):
    return
  try:
    with open(path, 'r', encoding='utf-8') as f:
      for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
          continue
        if '=' not in line:
          continue
        k, v = line.split('=', 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and not os.getenv(k):
          os.environ[k] = v
  except Exception:
    # Best-effort loader; do not crash on parse errors
    pass

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
  print("ERROR: OPENROUTER_API_KEY is not set in environment (or .env).", file=sys.stderr)
  sys.exit(1)

url = "https://openrouter.ai/api/v1/chat/completions"

payload = {
  "model": "x-ai/grok-4-fast",
  "messages": [
    {"role": "user", "content": "Please think step by step: which is larger, 9.9 or 9.11?"}
  ],
  "max_tokens": 500,
  "temperature": 1.0,
  # Enable reasoning tokens:
  "reasoning": {
    "effort": "high",     # "low" / "medium" / "high"
    "exclude": False      # set True if you don’t want reasoning text in response
  }
}

headers = {
  "Authorization": f"Bearer {API_KEY}",
  "Content-Type": "application/json",
}

# Optionally include Referer / X-Title if provided via env (do not hardcode secrets here)
site_url = os.getenv("OPENROUTER_SITE_URL")
site_title = os.getenv("OPENROUTER_SITE_TITLE")
if site_url:
  headers["Referer"] = site_url
if site_title:
  headers["X-Title"] = site_title

try:
  resp = requests.post(url, headers=headers, json=payload, timeout=30)
except requests.exceptions.RequestException as e:
  print("Request failed:", e, file=sys.stderr)
  if hasattr(e, 'response') and e.response is not None:
    try:
      print("Status:", e.response.status_code, file=sys.stderr)
      print(e.response.text, file=sys.stderr)
    except Exception:
      pass
  sys.exit(1)

# Parse JSON
try:
  data = resp.json()
except ValueError:
  data = None

if resp.status_code == 200 and data:
  try:
    msg = data["choices"][0]["message"]

    # Assistant reply
    print("\nASSISTANT:\n", msg.get("content"))

    # Reasoning (if returned)
    if msg.get("reasoning"):
      print("\nREASONING (string):\n", msg["reasoning"])

    if msg.get("reasoning_details"):
      print("\nREASONING DETAILS (structured):\n", json.dumps(msg["reasoning_details"], indent=2))

  except Exception:
    print(json.dumps(data, indent=2))
else:
  if data is not None:
    print("Error:", resp.status_code, json.dumps(data, indent=2))
  else:
    print("Error:", resp.status_code, resp.text)
  sys.exit(1)
