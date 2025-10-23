"""LiveKit + MCP integration for UAP Podcast.

This module wires a voice agent that runs fully locally using the LiveKit CLI simulator
and integrates Azure STT/TTS, Azure OpenAI LLM, and MCP tool calling. It is designed to
co-exist with the existing LangGraph-based workflow without altering the agents.

Usage (CLI simulate):
    python -m livekit.agents.cli simulate  # then this module provides the worker entrypoint

Programmatic:
    from src.uap_podcast.livekit_agent import run_cli, entrypoint
    run_cli()  # starts the worker; use LiveKit CLI simulate for the room
"""

import logging
import os
from typing import Optional

from dotenv import load_dotenv

# LiveKit Agents & plugins
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli, mcp
from livekit.plugins import deepgram, openai, silero, azure  # noqa: F401 (deepgram kept for parity)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.plugins import langchain as lk_langchain  # noqa: F401 (available for extensions)

# LangChain MCP client (tools exposure)
from langchain_mcp_adapters.client import MultiServerMCPClient  # noqa: F401 (available for extensions)

# Optional: LangGraph prebuilt (kept for parity and future routing)
from langgraph.prebuilt import create_react_agent  # noqa: F401

# Optional Azure LLM wrapper if needed alongside livekit.plugins.openai
from langchain_openai import AzureChatOpenAI  # noqa: F401

logger = logging.getLogger("uap_podcast.livekit")

# Load env from project root .env if present
load_dotenv()


class MyAgent(Agent):
    """Voice-first agent that can interact with MCP tools via the LiveKit session."""

    def __init__(self):
        super().__init__(
            instructions=(
                "You are MCP Sentinel, a voice-based agent that interacts with the MCP server. "
                "You can retrieve data via the MCP server. The interface is voice-based: "
                "accept spoken user queries and respond with synthesized speech."
            ),
        )

    async def on_enter(self):
        # Kick off an initial reply (e.g., greeting)
        await self.session.generate_reply()


async def entrypoint(ctx: JobContext):
    """LiveKit worker entrypoint used by the CLI simulator or an external worker process."""
    # Pull env vars (must be present in existing .env)
    speech_region = os.getenv("AZURE_SPEECH_REGION") or os.getenv("SPEECH_REGION")
    speech_auth_token = os.getenv("AZURE_SPEECH_AUTH_TOKEN")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-01-preview")

    mcp_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp/")
    mcp_auth = os.getenv("MCP_AUTH_TOKEN")

    if not (speech_region and speech_auth_token and azure_endpoint and api_key):
        logger.warning("Missing Azure env vars for LiveKit session; ensure .env is loaded.")

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=azure.STT(
            speech_region=speech_region,
            speech_auth_token=speech_auth_token,
        ),
        llm=openai.LLM.with_azure(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            api_version=api_version,
        ),
        tts=azure.TTS(
            speech_region=speech_region,
            speech_auth_token=speech_auth_token,
        ),
        turn_detection=MultilingualModel(),
        mcp_servers=[
            mcp.MCPServerHTTP(
                url=mcp_url,
                headers={"Authorization": f"Bearer {mcp_auth}"} if mcp_auth else None,
                timeout=60,
                client_session_timeout_seconds=60,
            )
        ],
    )

    # Start the voice session in the provided room context
    await session.start(agent=MyAgent(), room=ctx.room)


def run_cli():
    """Start a worker process suitable for use with the LiveKit CLI simulate command."""
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))


# Convenience alias for external runners
run_app = run_cli

if __name__ == "__main__":
    run_cli()
