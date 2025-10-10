import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any

from uap_podcast.models.audio import text_to_ssml, synth, write_master
from uap_podcast.models.podcast import llm
from uap_podcast.agents.stat_agent.utils.state import STAT_INTRO, SYSTEM_STAT
from uap_podcast.agents.stat_agent.utils.nodes import generate_stat_turn
from uap_podcast.agents.stat_agent.utils.tools import (
    ensure_complete_response,
    vary_opening,
    add_conversation_dynamics,
    add_emotional_reactions,
    clean_repetition,
)

class StatAgent:
    """
    📊 StatAgent manages the statistical integrity agent's part of the podcast.
    Responsibilities:
      - Speak Stat's intro
      - Generate dynamic responses based on Reco's statements & context
      - Maintain script & audio segments for Stat
    """

    def __init__(self):
        self.script_lines: List[str] = []
        self.audio_segments: List[str] = []
        self.conversation_history: List[str] = []
        self.last_openings: Dict[str, str] = {}
        self.last_speaker: str = ""

    async def speak_intro(self) -> None:
        """🎙️ Speak the fixed Stat introduction."""
        self.script_lines.append(f"Agent Stat: {STAT_INTRO}")
        ssml = text_to_ssml(STAT_INTRO, "STAT")
        audio = synth(ssml)
        self.audio_segments.append(audio)

    async def generate_turn(
        self,
        context: str,
        nexus_intro: str,
        reco_response: str,
        previous_history: List[str],
        turn_index: int,
    ) -> str:
        """
        🧠 Generate a single Stat turn based on:
          - data context
          - Nexus topic intro
          - Reco's previous statement
          - conversation history
        """
        print(f"📊 Generating Stat turn {turn_index + 1}...")

        stat_prompt = f"""
        Context: {context}

        Nexus introduced these topics: {nexus_intro}

        Reco just said: {reco_response}

        Previous conversation: {previous_history[-3:] if len(previous_history) >= 3 else 'None'}

        Respond to Reco's point focusing on data integrity and statistical validation.
        """

        response = await generate_stat_turn(SYSTEM_STAT, stat_prompt)

        # --- Conversation polishing ---
        response = vary_opening(response, "STAT", self.last_openings)
        response = add_conversation_dynamics(
            response, "STAT", self.last_speaker, context, turn_index, previous_history
        )
        response = add_emotional_reactions(response, "STAT")
        response = clean_repetition(response)
        response = ensure_complete_response(response)

        # Save script + audio
        self.script_lines.append(f"Agent Stat: {response}")
        ssml = text_to_ssml(response, "STAT")
        audio = synth(ssml)
        self.audio_segments.append(audio)

        # Update history
        self.conversation_history.append(f"Stat: {response}")
        self.last_speaker = "Stat"
        return response

    async def generate_segment(
        self,
        context: str,
        nexus_intro: str,
        reco_responses: List[str],
        turns: int = 3,
        output_prefix: str = "stat_segment",
    ) -> Dict[str, Any]:
        """
        🎧 Generate the entire Stat segment flow:
          1. Intro
          2. Multiple response turns
          3. Write output audio + script
        """
        await self.speak_intro()

        for turn in range(turns):
            reco_response = (
                reco_responses[turn] if turn < len(reco_responses) else "[No Reco response provided]"
            )
            await self.generate_turn(
                context, nexus_intro, reco_response, self.conversation_history, turn
            )
            time.sleep(0.3)

        # Write audio output
        output_file = f"{output_prefix}.wav"
        write_master(self.audio_segments, output_file)

        # Write script
        script_file = f"{output_prefix}_script.txt"
        Path(script_file).write_text("\n".join(self.script_lines), encoding="utf-8")

        print("✅ Stat segment generated.")
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
        reco_responses = [
            "[Demo] Reco suggests using a rolling average to smooth volatility.",
            "[Demo] Reco recommends investigating queue routing issues.",
            "[Demo] Reco advises introducing a triage tag for complexity analysis.",
        ]

        stat = StatAgent()
        await stat.generate_segment(
            context,
            nexus_intro,
            reco_responses,
            turns=3,
            output_prefix="stat_demo"
        )

    asyncio.run(_run_demo())
