import os
import uvicorn
import asyncio
import re
from google.adk.cli.fast_api import get_fast_api_app

# ── Inject Browser Notification Script into Frontend ──────────────────────
def inject_notification_script():
    try:
        import inspect
        import google.adk.cli
        adk_cli_dir = os.path.dirname(inspect.getfile(google.adk.cli))
        index_html_path = os.path.join(adk_cli_dir, "browser", "index.html")
        
        if os.path.exists(index_html_path):
            with open(index_html_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Inject only if not already present
            if "checkSession" not in content:
                script_code = """
<script>
(function() {
    console.log("ADK Notifications: Script loaded.");
    
    // Request permission immediately on load
    if (Notification.permission === "default") {
        Notification.requestPermission().then(permission => {
            console.log("ADK Notifications: Permission is", permission);
        });
    }

    let lastEventCount = 0;
    let initialLoad = true;

    function checkSession() {
        const params = new URLSearchParams(window.location.search);
        const appId = params.get('app');
        const sessionId = params.get('session');
        if (!appId || !sessionId) return;

        fetch(`/apps/${appId}/users/user/sessions/${sessionId}`)
            .then(res => res.json())
            .then(session => {
                const events = session.events || [];
                if (initialLoad) {
                    lastEventCount = events.length;
                    initialLoad = false;
                    return;
                }

                if (events.length > lastEventCount) {
                    const lastEvent = events[events.length - 1];
                    if (lastEvent && lastEvent.author !== "user") {
                        const text = lastEvent.content && lastEvent.content.parts && lastEvent.content.parts[0] && lastEvent.content.parts[0].text;
                        
                        // Blogger outputs alternative titles and hooks at the very end of the run
                        const isDone = text && (
                            text.includes("Alternate Titles") || 
                            text.includes("alternate titles") || 
                            text.includes("Tweet-length hook") ||
                            text.includes("tweet-length hook") ||
                            text.includes("Alternate titles")
                        );
                        
                        if (isDone) {
                            if (Notification.permission === "granted") {
                                new Notification("Blog Post Ready! 🎉", {
                                    body: "Your Blogger agent has completed writing and verifying your blog post.",
                                    icon: "adk_favicon.svg"
                                });
                            }
                        }
                    }
                    lastEventCount = events.length;
                }
            })
            .catch(err => console.error("Error polling session for notifications:", err));
    }

    // Poll every 5 seconds
    setInterval(checkSession, 5000);
})();
</script>
"""
                new_content = content.replace("</body>", script_code + "</body>")
                with open(index_html_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print("ADK Launch: Successfully injected browser notification script into index.html!")
            else:
                print("ADK Launch: Browser notification script is already injected.")
        else:
            print("ADK Launch WARNING: index.html not found, cannot inject notification script!")
    except Exception as e:
        print(f"ADK Launch WARNING: Failed to inject notification script: {e}")

# Run injection
inject_notification_script()
# ──────────────────────────────────────────────────────────────────────────

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
        except Exception as e:
            is_rate_limit = False
            
            # Check for standard ClientError 429
            if isinstance(e, ClientError) and e.code == 429:
                is_rate_limit = True
            # Check for API core ResourceExhausted or similar class names
            elif "ResourceExhausted" in e.__class__.__name__:
                is_rate_limit = True
            # Check for status codes
            elif getattr(e, "code", None) == 429 or getattr(e, "status_code", None) == 429:
                is_rate_limit = True
            # Check the error message string
            elif "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                is_rate_limit = True

            if is_rate_limit and attempts < 10:
                attempts += 1
                delay = 30
                # Parse wait time from error message (e.g. "retry in 15s")
                match = re.search(r"retry in ([\d\.]+)s", str(e))
                if match:
                    delay = int(float(match.group(1))) + 2
                print(f"[Rate Limiter] Gemini API 429 / ResourceExhausted hit. Retrying in {delay}s (Attempt {attempts}/10)...")
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
