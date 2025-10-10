import asyncio
from pathlib import Path
from typing import List, Dict, Any

from uap_podcast.models.audio import text_to_ssml, synth, write_master
from uap_podcast.models.podcast import llm
from uap_podcast.agents.stat_agent.utils.state import STAT_INTRO, SYSTEM_STAT
from uap_podcast.agents.stat_agent.utils.tools import (
    ensure_complete_response,
    vary_opening,
    add_conversation_dynamics,
    add_emotional_reactions,
    clean_repetition,
)


class StatAgent:
    """
    ✅ StatAgent — Responsible for data validation, statistical integrity, and grounded responses.
    It represents a 'skeptical quant partner' who:
      - Speaks with precision and caution
      - Challenges or confirms Reco's recommendations
      - Anchors the conversation in data accuracy and measurement principles
    """

    def __init__(self):
        self.script_lines: List[str] = []
        self.audio_segments: List[str] = []
        self.conversation_history: List[str] = []
        self.last_openings: Dict[str, str] = {}
        self.last_speaker: str = ""

    async def speak_intro(self) -> None:
        """Speak the fixed Stat introduction."""
        self.script_lines.append(f"Agent Stat: {STAT_INTRO}")
        ssml = text_to_ssml(STAT_INTRO, "STAT")
        audio = synth(ssml)
        self.audio_segments.append(audio)

    async def respond(
        self,
        context: str,
        nexus_intro: str,
        reco_response: str,
        turn_index: int
    ) -> str:
        """
        Generate and speak Stat's response based on Reco's previous message and context.

        Flow:
        - Build a system + user prompt to guide LLM response
        - Post-process with humanization, dynamics, emotional emphasis
        - Convert to SSML & synthesize audio
        """
        prompt = (
            f"Context: {context}\n\n"
            f"Nexus introduced: {nexus_intro}\n\n"
            f"Reco just said: {reco_response}\n\n"
            f"Previous conversation: "
            f"{self.conversation_history[-3:] if len(self.conversation_history) >= 3 else 'None'}\n\n"
            "Respond to Reco's point focusing on data integrity and statistical reliability."
        )

        raw_response = await llm(SYSTEM_STAT, prompt)
        processed = vary_opening(raw_response, "STAT", self.last_openings)
        processed = add_conversation_dynamics(
            processed,
            "STAT",
            self.last_speaker,
            context,
            turn_index,
            self.conversation_history,
        )
        processed = add_emotional_reactions(processed, "STAT")
        processed = clean_repetition(processed)
        processed = ensure_complete_response(processed)

        self.script_lines.append(f"Agent Stat: {processed}")
        self.conversation_history.append(f"Stat: {processed}")

        ssml = text_to_ssml(processed, "STAT")
        audio = synth(ssml)
        self.audio_segments.append(audio)

        self.last_speaker = "Stat"
        return processed

    async def generate_segment(
        self,
        context: str,
        nexus_intro: str,
        reco_responses: List[str],
        output_prefix: str = "stat_segment",
    ) -> Dict[str, Any]:
        """
        🧠 Generate the full Stat segment:
          - Intro
          - Responses for each turn
          - Write final audio and script
        """
        await self.speak_intro()

        for i, reco_line in enumerate(reco_responses):
            await self.respond(context, nexus_intro, reco_line, i)

        output_file = f"{output_prefix}.wav"
        write_master(self.audio_segments, output_file)

        script_file = f"{output_prefix}_script.txt"
        Path(script_file).write_text("\n".join(self.script_lines), encoding="utf-8")

        print("✅ Stat segment generated.")
        return {
            "audio_file": output_file,
            "script_file": script_file,
            "lines": self.script_lines,
            "history": self.conversation_history,
        }


# ------------------------- Standalone Test -------------------------

if __name__ == "__main__":
    async def _demo_run():
        context = "[Demo] Sample data context"
        nexus_intro = "Today, we'll explore KPI volatility and call duration spikes."
        reco_lines = [
            "Given that ASA dropped 84%, we should smooth the data with a rolling average.",
            "To reduce risk, let's validate queue mappings before setting throughput targets."
        ]

        stat = StatAgent()
        await stat.generate_segment(context, nexus_intro, reco_lines)

    asyncio.run(_demo_run())
