import pytest
from uap_podcast.agents.reco_agent.utils.tools import (
    ensure_complete_response,
    clean_repetition,
    add_conversation_dynamics
)

def test_ensure_complete_response_adds_period():
    text = ensure_complete_response("This is a test")
    assert text.endswith((".", "!", "?"))

def test_clean_repetition_removes_duplicates():
    result = clean_repetition("Reco, Reco, this is is a test")
    assert "Reco, Reco" not in result
    assert "is is" not in result

def test_add_conversation_dynamics_adds_elements():
    text = add_conversation_dynamics(
        "This is significant data", 
        role="RECO", 
        last_speaker="STAT", 
        context="Sample context", 
        turn_count=3, 
        conversation_history=["Stat: sample"]
    )
    assert isinstance(text, str)
    assert len(text) > 0
