import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any

from uap_podcast.models.audio import text_to_ssml, synth, write_master
from uap_podcast.models.podcast import llm
from uap_podcast.agents.nexus_agent.utils.state import NEXUS_INTRO, NEXUS_OUTRO, SYSTEM_NEXUS
from uap_podcast.agents.nexus_agent.utils.nodes import generate_nexus_topic_intro
from uap_podcast.agents.nexus_agent.utils.tools import ensure_complete_response

class NexusAgent:
    """
    ✅ NexusAgent orchestrates the podcast introduction, topic setup, and closing.
    It handles:
      - Speaking the intro and outro
      - Generating and speaking topic introductions dynamically
      - Managing the conversation flow for the Nexus role
    """

    def __init__(self):
        self.script_lines: List[str] = []
        self.audio_segments: List[str] = []
        self.conversation_history: List[str] = []

    async def speak_intro(self) -> None:
        """Speak the fixed Nexus introduction."""
        self.script_lines.append(f"Agent Nexus: {NEXUS_INTRO}")
        ssml = text_to_ssml(NEXUS_INTRO, "NEXUS")
        audio = synth(ssml)
        self.audio_segments.append(audio)

    async def speak_topic_intro(self, context: str) -> str:
        """
        Dynamically generate and speak the Nexus topic introduction 
        based on the data context.
        """
        print("🎙️ Generating Nexus topic introduction...")
        topic_intro = await generate_nexus_topic_intro(context)
        topic_intro = ensure_complete_response(topic_intro)

        self.script_lines.append(f"Agent Nexus: {topic_intro}")
        ssml = text_to_ssml(topic_intro, "NEXUS")
        audio = synth(ssml)
        self.audio_segments.append(audio)
        self.conversation_history.append(f"Nexus: {topic_intro}")
        return topic_intro

    async def speak_outro(self) -> None:
        """Speak the fixed Nexus outro."""
        self.script_lines.append(f"Agent Nexus: {NEXUS_OUTRO}")
        ssml = text_to_ssml(NEXUS_OUTRO, "NEXUS")
        audio = synth(ssml)
        self.audio_segments.append(audio)

    async def generate_podcast(
        self, context: str, output_prefix: str = "podcast"
    ) -> Dict[str, Any]:
        """
        🎧 Main orchestration method — runs the complete Nexus segment:
          1. Intro
          2. Dynamic topic introduction
          3. Outro
          4. Write audio + script
        """
        await self.speak_intro()
        await self.speak_topic_intro(context)
        await self.speak_outro()

        # Final audio output
        output_file = f"{output_prefix}.wav"
        write_master(self.audio_segments, output_file)

        # Write script
        script_file = f"{output_prefix}_script.txt"
        Path(script_file).write_text("\n".join(self.script_lines), encoding="utf-8")

        print("✅ Nexus segment generated.")
        return {
            "audio_file": output_file,
            "script_file": script_file,
            "lines": self.script_lines,
            "history": self.conversation_history,
        }

# Example standalone run
if __name__ == "__main__":
    async def _run_demo():
        context = "[Demo] Sample data context loaded..."
        nexus = NexusAgent()
        await nexus.generate_podcast(context, output_prefix="nexus_demo")

    asyncio.run(_run_demo())
