import asyncio
import os
import sys
from google.genai import types
from google.adk.apps.app import App
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
from google.adk.utils.context_utils import Aclosing

# Load environment variables (done in main as well)
from main import root_agent

async def run_agent(topic: str):
    app_name = "agents"
    user_id = "user1"
    
    app = App(name=app_name, root_agent=root_agent)
    
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    credential_service = InMemoryCredentialService()
    
    runner = Runner(
        app=app,
        artifact_service=artifact_service,
        session_service=session_service,
        credential_service=credential_service
    )
    
    session = await session_service.create_session(
        app_name=app_name, user_id=user_id
    )
    
    query = f"Write a blog post about: {topic}"
    print(f"\n\033[1;34m[User]:\033[0m {query}\n")
    
    content = types.Content(role="user", parts=[types.Part(text=query)])
    
    async with Aclosing(
        runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=content
        )
    ) as agen:
        async for event in agen:
            if event.content and event.content.parts:
                text = ''.join(part.text or '' for part in event.content.parts)
                if text:
                    # Let's print the agent name colorfully
                    if event.author == "Blogger":
                        color = "\033[1;32m" # Green
                    elif "Planner" in event.author:
                        color = "\033[1;36m" # Cyan
                    elif "Writer" in event.author:
                        color = "\033[1;35m" # Magenta
                    else:
                        color = "\033[1;33m" # Yellow
                    print(f"{color}[{event.author}]:\033[0m {text}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run.py <topic>")
        sys.exit(1)
        
    topic = " ".join(sys.argv[1:])
    asyncio.run(run_agent(topic))
