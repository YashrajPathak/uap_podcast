"""
tools.py — Utility functions for StatAgent response refinement.

This module handles:
- Sentence completion and formatting
- Conversational opener variation
- Dynamic conversational behaviors (interruptions, agreements, name usage)
- Emotional reactions for more human-like responses
- Cleaning repetitive text for clarity
"""

import re
import random
from typing import Dict, List

# ------------------------- Sentence Finalization -------------------------

def ensure_complete_response(text: str) -> str:
    """✅ Ensure the response ends as a complete sentence."""
    text = text.strip()
    if text and text[-1] not in {".", "!", "?"}:
        text += "."
    return text


# ------------------------- Opener Variation -------------------------

FORBIDDEN = {
    "STAT": {
        "hold on", "actually", "well", "look", "so", "right", "okay",
        "absolutely", "you know", "listen", "wait"
    }
}

OPENERS = {
    "STAT": [
        "The data implies",
        "I'd confirm",
        "One risk is",
        "Before we adopt that, test",
        "Evidence for that would be",
        "The safer read is",
        "Statistically speaking",
        "From the variance profile"
    ]
}

def strip_forbidden(text: str, role: str) -> str:
    """🚫 Remove forbidden filler words from the start of a response."""
    low = text.strip().lower()
    for w in sorted(FORBIDDEN[role], key=lambda x: -len(x)):
        if low.startswith(w + " ") or low == w:
            return text[len(w):].lstrip(" ,.-–—")
    return text

def vary_opening(text: str, role: str, last_openings: Dict[str, str]) -> str:
    """🔄 Add variation to sentence openers to avoid repetition."""
    t = strip_forbidden(text, role)
    first = (t.split()[:1] or [""])[0].strip(",. ").lower()
    if first in FORBIDDEN[role] or not first or random.random() < 0.4:
        cand = random.choice(OPENERS[role])
        if last_openings.get(role) == cand:
            pool = [c for c in OPENERS[role] if c != cand]
            cand = random.choice(pool) if pool else cand
        last_openings[role] = cand
        return f"{cand}, {t}"
    return t


# ------------------------- Conversational Dynamics -------------------------

INTERRUPTION_CHANCE = 0.25
AGREE_DISAGREE_RATIO = 0.5  # Stat slightly more likely to challenge

def add_conversation_dynamics(
    text: str,
    role: str,
    last_speaker: str,
    context: str,
    turn_count: int,
    conversation_history: List[str]
) -> str:
    """
    🧠 Inject conversational behaviors:
    - Name usage at key points
    - Interruptions, agreements, disagreements
    - Emotional emphasis and transitional phrases
    """
    other_agent = "Reco" if role == "STAT" else ""
    added = False

    # Strategic name usage
    should_use_name = (
        any(word in text.lower() for word in ["critical", "essential", "important", "significant"]) or
        any(word in text.lower() for word in ["but", "however", "although", "disagree", "challenge"]) or
        (turn_count > 2 and random.random() < 0.3) or
        any(word in text.lower() for word in ["surprising", "shocking", "unexpected", "remarkable"]) or
        (len(conversation_history) > 2 and "alternative" in text.lower()) or
        (random.random() < 0.2 and any(word in text.lower() for word in ["agree", "right", "valid"]))
    )

    if other_agent and should_use_name and random.random() < 0.7 and not added:
        address_formats = [f"{other_agent}, ", f"You know, {other_agent}, "]
        text = f"{random.choice(address_formats)}{text.lower()}"
        added = True

    # Emotional emphasis (surprise, shock, etc.)
    surprise_words = ["surprising", "shocking", "unexpected", "dramatic", "remarkable", "concerning"]
    if not added and random.random() < 0.25 and any(word in text.lower() for word in surprise_words):
        emphatics = ["Surprisingly, ", "Interestingly, ", "Remarkably, ", "Unexpectedly, "]
        text = f"{random.choice(emphatics)}{text}"
        added = True

    # Interruptions & acknowledgments
    if not added and random.random() < INTERRUPTION_CHANCE and role != "NEXUS" and last_speaker and turn_count > 1:
        if random.random() < 0.5:
            acknowledgments = [
                "I see what you're saying, ",
                "That's a valid observation, ",
                "I understand your concern, ",
                "That's a solid point, "
            ]
            text = f"{random.choice(acknowledgments)}{text.lower()}"
        else:
            interruptions = [
                "If I might add, ",
                "Building on that, ",
                "To expand on that point, ",
                "Another angle here is "
            ]
            text = f"{random.choice(interruptions)}{text}"
        added = True

    # Agreement / disagreement
    if not added and random.random() < 0.35 and role != "NEXUS" and turn_count > 1:
        if random.random() < AGREE_DISAGREE_RATIO:
            agreements = [
                "I agree with that reasoning, ",
                "That logic makes sense, ",
                "You're right about that, ",
                "That's a sound conclusion, "
            ]
            text = f"{random.choice(agreements)}{text.lower()}"
        else:
            disagreements = [
                "I see it differently, ",
                "One alternative interpretation is, ",
                "We should consider another angle, ",
                "I'd approach it differently, "
            ]
            text = f"{random.choice(disagreements)}{text.lower()}"

    return text


# ------------------------- Emotional Reactions -------------------------

def add_emotional_reactions(text: str, role: str) -> str:
    """🎭 Add emotional tone to specific words or patterns."""
    emotional_triggers = {
        "dramatic": ["That's quite a dramatic shift! ", "This is significant! "],
        "concerning": ["This is concerning. ", "We should examine this closely. "],
        "positive": ["That's encouraging! ", "This is a positive indicator. "],
        "surprising": ["That's surprising! ", "I didn't expect that result. "],
    }

    for trigger, reactions in emotional_triggers.items():
        if trigger in text.lower() and random.random() < 0.4:
            reaction = random.choice(reactions)
            if "," in text:
                parts = text.split(",", 1)
                text = f"{parts[0]}, {reaction}{parts[1].lstrip()}"
            else:
                text = f"{reaction}{text}"
            break
    return text


# ------------------------- Cleanup Helpers -------------------------

def clean_repetition(text: str) -> str:
    """🧹 Remove repetitive words or phrases."""
    text = re.sub(r"\b(Reco|Stat),\s+\1,?\s+", r"\1, ", text)
    text = re.sub(r"\b(\w+)\s+\1\b", r"\1", text)
    text = re.sub(r"\b(The safer read|The data implies),\s+\1", r"\1", text)
    return text
