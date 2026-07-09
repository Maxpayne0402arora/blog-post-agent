import os
import uvicorn
from google.adk.cli.fast_api import get_fast_api_app

# Port is dynamically assigned by the hosting provider (e.g., Render)
port = int(os.environ.get("PORT", 8000))

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
