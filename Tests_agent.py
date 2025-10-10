import asyncio
import pytest
from uap_podcast.agents.nexus_agent.agent import NexusAgent
from uap_podcast.agents.reco_agent.agent import RecoAgent
from uap_podcast.agents.stat_agent.agent import StatAgent

@pytest.mark.asyncio
async def test_nexus_agent_intro_and_outro():
    nexus = NexusAgent()
    result = await nexus.generate_podcast(context="[Test] Sample context", output_prefix="test_nexus")
    assert "audio_file" in result
    assert "script_file" in result
    assert any("Nexus" in line for line in result["lines"])

@pytest.mark.asyncio
async def test_reco_agent_turn_generation():
    reco = RecoAgent()
    result = await reco.generate_segment(
        context="[Test] Data context",
        nexus_intro="[Test] Topic intro",
        turns=1,
        output_prefix="test_reco"
    )
    assert "Reco" in "\n".join(result["lines"])
    assert len(result["history"]) > 0

@pytest.mark.asyncio
async def test_stat_agent_turn_generation():
    stat = StatAgent()
    result = await stat.generate_segment(
        context="[Test] Data context",
        nexus_intro="[Test] Topic intro",
        turns=1,
        output_prefix="test_stat"
    )
    assert "Stat" in "\n".join(result["lines"])
    assert len(result["history"]) > 0
