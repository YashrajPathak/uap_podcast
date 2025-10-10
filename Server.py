"""
server.py — FastAPI service for UAP Podcast Generation

This module serves as the HTTP interface to your multi-agent podcast system.
It exposes endpoints for:
- Generating AI responses
- Synthesizing audio from text
- Running a full podcast orchestration
- Health and readiness checks
"""

import os
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

# ✅ Import core components
from uap_podcast.models.podcast import llm
from uap_podcast.models.audio import text_to_ssml, synth
from uap_podcast.agents.nexus_agent.agent import NexusAgent
from uap_podcast.agents.reco_agent.agent import RecoAgent
from uap_podcast.agents.stat_agent.agent import StatAgent

# Initialize FastAPI
app = FastAPI(
    title="UAP Podcast API",
    description="🚀 Multi-Agent Podcast Generator API",
    version="1.0.0",
)

# ----------------------- Request Models -----------------------

class GenerateRequest(BaseModel):
    system_prompt: str
    user_prompt: str
    max_tokens: Optional[int] = 150
    temperature: Optional[float] = 0.45


class AudioRequest(BaseModel):
    text: str
    voice: str  # e.g., "NEXUS", "RECO", or "STAT"


class PodcastRequest(BaseModel):
    context: str
    turns: Optional[int] = 3
    output_prefix: Optional[str] = "podcast_output"

# ----------------------- API Endpoints -----------------------

@app.post("/generate-response")
async def generate_response(request: GenerateRequest):
    """
    🤖 Generate a text response using the LLM.
    """
    try:
        response = await llm(
            request.system_prompt,
            request.user_prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )
        return {"text": response, "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-audio")
async def generate_audio_endpoint(request: AudioRequest):
    """
    🔊 Convert text into synthesized speech audio.
    """
    try:
        ssml = text_to_ssml(request.text, request.voice)
        audio_file = synth(ssml)
        return {"audio_url": f"/audio/{os.path.basename(audio_file)}", "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-podcast")
async def generate_podcast_endpoint(request: PodcastRequest):
    """
    🎙️ Run a full multi-agent podcast generation sequence.
    - Nexus speaks intro & topic
    - Reco and Stat converse dynamically
    - Nexus closes
    """
    try:
        nexus = NexusAgent()
        reco = RecoAgent()
        stat = StatAgent()

        # 1. Nexus Segment
        nexus_output = await nexus.generate_podcast(
            context=request.context,
            output_prefix=f"{request.output_prefix}_nexus"
        )

        # 2. Reco Segment
        reco_output = await reco.generate_segment(
            context=request.context,
            nexus_intro=nexus_output["lines"][1] if len(nexus_output["lines"]) > 1 else "",
            turns=request.turns,
            output_prefix=f"{request.output_prefix}_reco"
        )

        # 3. Stat Segment
        stat_output = await stat.generate_segment(
            context=request.context,
            nexus_intro=nexus_output["lines"][1] if len(nexus_output["lines"]) > 1 else "",
            reco_history=reco_output["history"],
            turns=request.turns,
            output_prefix=f"{request.output_prefix}_stat"
        )

        return {
            "success": True,
            "nexus_output": nexus_output,
            "reco_output": reco_output,
            "stat_output": stat_output,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """
    ✅ Health check endpoint — confirms API readiness.
    """
    return {"status": "healthy", "service": "podcast-engine", "version": "1.0.0"}

# ----------------------- Entry Point -----------------------

if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting UAP Podcast FastAPI server on http://0.0.0.0:8001 ...")
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=True)
