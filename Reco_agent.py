import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any

from uap_podcast.models.audio import text_to_ssml, synth, write_master
from uap_podcast.models.podcast import llm
from uap_podcast.agents.reco_agent.utils.state import RECO_INTRO, SYSTEM_RECO
from uap_podcast.agents.reco_agent.utils.nodes import generate_reco_turn
from uap_podcast.agents.reco_agent.utils.tools import (
    ensure_complete_response,
    vary_opening,
    add_conversation_dynamics,
    add_emotional_reactions,
    clean_repetition,
)

class RecoAgent:
    """
    🎯 RecoAgent manages the recommendation agent's part of the podcast.
    Responsibilities:
      - Speak Reco's intro
      - Generate dynamic responses based on context and conversation state
      - Maintain script & audio segments for Reco
    """

    def __init__(self):
        self.script_lines: List[str] = []
        self.audio_segments: List[str] = []
        self.conversation_history: List[str] = []
        self.last_openings: Dict[str, str] = {}
        self.last_speaker: str = ""

    async def speak_intro(self) -> None:
        """🎙️ Speak the fixed Reco introduction."""
        self.script_lines.append(f"Agent Reco: {RECO_INTRO}")
        ssml = text_to_ssml(RECO_INTRO, "RECO")
        audio = synth(ssml)
        self.audio_segments.append(audio)

    async def generate_turn(
        self,
        context: str,
        nexus_intro: str,
        previous_history: List[str],
        turn_index: int,
    ) -> str:
        """
        🤖 Generate a single Reco turn based on:
          - context
          - Nexus topic intro
          - previous conversation state
        """
        print(f"💡 Generating Reco turn {turn_index + 1}...")
        reco_prompt = f"""
        Context: {context}

        Nexus introduced these topics: {nexus_intro}

        Previous conversation: {previous_history[-2:] if len(previous_history) > 1 else 'None'}

        Provide your recommendation based on the data and topics introduced.
        """

        response = await generate_reco_turn(SYSTEM_RECO, reco_prompt)

        # --- Conversation polishing ---
        response = vary_opening(response, "RECO", self.last_openings)
        response = add_conversation_dynamics(
            response, "RECO", self.last_speaker, context, turn_index, previous_history
        )
        response = add_emotional_reactions(response, "RECO")
        response = clean_repetition(response)
        response = ensure_complete_response(response)

        # Save script + audio
        self.script_lines.append(f"Agent Reco: {response}")
        ssml = text_to_ssml(response, "RECO")
        audio = synth(ssml)
        self.audio_segments.append(audio)

        # Update history
        self.conversation_history.append(f"Reco: {response}")
        self.last_speaker = "Reco"
        return response

    async def generate_segment(
        self,
        context: str,
        nexus_intro: str,
        turns: int = 3,
        output_prefix: str = "reco_segment",
    ) -> Dict[str, Any]:
        """
        🎧 Generate the entire Reco segment flow:
          1. Intro
          2. Multiple recommendation turns
          3. Write output audio + script
        """
        await self.speak_intro()

        for turn in range(turns):
            await self.generate_turn(
                context, nexus_intro, self.conversation_history, turn
            )
            time.sleep(0.2)

        # Write audio output
        output_file = f"{output_prefix}.wav"
        write_master(self.audio_segments, output_file)

        # Write script
        script_file = f"{output_prefix}_script.txt"
        Path(script_file).write_text("\n".join(self.script_lines), encoding="utf-8")

        print("✅ Reco segment generated.")
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
        nexus_intro = "[Demo] Sample topic intro..."
        reco = RecoAgent()
        await reco.generate_segment(context, nexus_intro, turns=3, output_prefix="reco_demo")

    asyncio.run(_run_demo())
