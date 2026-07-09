import os
import uvicorn
import asyncio
import re
from google.adk.cli.fast_api import get_fast_api_app

# ── Monkeypatch ADK Gemini model to handle 429 Rate Limits automatically ──
from google.adk.models.google_llm import Gemini
from google.genai.errors import ClientError

original_generate_content_async = Gemini.generate_content_async

async def patched_generate_content_async(self, llm_request, stream=False):
    attempts = 0
    while True:
        try:
            # Consume and yield from the original async generator
            async for response in original_generate_content_async(self, llm_request, stream):
                yield response
            break
        except ClientError as e:
            if e.code == 429 and attempts < 5:
                attempts += 1
                delay = 30
                # Parse wait time from error message (e.g. "retry in 15.7s")
                match = re.search(r"retry in ([\d\.]+)s", str(e))
                if match:
                    delay = int(float(match.group(1))) + 2
                print(f"[Rate Limiter] Gemini API 429 Rate Limit hit. Retrying in {delay}s (Attempt {attempts}/5)...")
                await asyncio.sleep(delay)
            else:
                raise e

# Apply the patch to the Gemini class
Gemini.generate_content_async = patched_generate_content_async
# ──────────────────────────────────────────────────────────────────────────

# Port is dynamically assigned by the hosting provider (e.g., Render)
port = int(os.environ.get("PORT", 8000))

# Diagnostic check for API key
if "GEMINI_API_KEY" in os.environ:
    print("ADK Launch: GEMINI_API_KEY is successfully detected in the environment.")
else:
    print("ADK Launch WARNING: GEMINI_API_KEY is NOT detected in the environment!")

# Initialize the FastAPI app with the relative path to our agents directory
app = get_fast_api_app(
    agents_dir="agents",
    web=True,
    allow_origins=["*"],
    host="0.0.0.0",
    port=port
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=port)
