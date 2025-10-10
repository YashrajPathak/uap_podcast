"""
tools.py — Utility functions for RecoAgent.

This module handles:
- Response cleaning and formatting
- Opener variation
- Conversation dynamics and emotional reactions
- Repetition removal
"""

import re
import random
from typing import Dict, List

# ------------------------ Forbidden Openers & Options ------------------------

FORBIDDEN = {
    "RECO": {
        "absolutely", "well", "look", "sure", "okay", "so", "listen",
        "hey", "you know", "hold on", "right", "great point"
    },
    "STAT": {
        "hold on", "actually", "well", "look", "so", "right", "okay",
        "absolutely", "you know", "listen", "wait"
    },
}

OPENERS = {
    "RECO": [
        "Given that", "Looking at this", "From that signal", "On those figures",
        "Based on the last month", "If we take the trend", "Against YTD context", "From a planning view"
    ],
    "STAT": [
        "Data suggests", "From the integrity check", "The safer interpretation", "Statistically speaking",
        "Given the variance profile", "From the control limits", "Relative to seasonality", "From the timestamp audit"
    ],
}


# ------------------------- Sentence Cleaning Utilities -------------------------

def ensure_complete_response(text: str) -> str:
    """Ensure the response ends as a complete sentence."""
    text = text.strip()
    if text and text[-1] not in {".", "!", "?"}:
        text += "."
    return text


# ------------------------- Opening Variation Logic -------------------------

def strip_forbidden(text: str, role: str) -> str:
    """Remove forbidden opener words from the beginning of a response."""
    low = text.strip().lower()
    for w in sorted(FORBIDDEN[role], key=lambda x: -len(x)):
        if low.startswith(w + " ") or low == w:
            return text[len(w):].lstrip(" ,.-–—")
    return text


def vary_opening(text: str, role: str, last_open: Dict[str, str]) -> str:
    """
    Randomize the opening of a sentence to make conversation feel more natural.
    Avoids repetition and filler words.
    """
    t = strip_forbidden(text, role)
    first = (t.split()[:1] or [""])[0].strip(",. ").lower()

    if first in FORBIDDEN[role] or not first or random.random() < 0.4:
        cand = random.choice(OPENERS[role])
        if last_open.get(role) == cand:
            pool = [c for c in OPENERS[role] if c != cand]
            cand = random.choice(pool) if pool else cand
        last_open[role] = cand
        return f"{cand}, {t}"
    return t


# ----------------------- Conversation Dynamics Enhancers -----------------------

INTERRUPTION_CHANCE = 0.25
AGREE_DISAGREE_RATIO = 0.6

def add_conversation_dynamics(
    text: str,
    role: str,
    last_speaker: str,
    context: str,
    turn_count: int,
    conversation_history: List[str]
) -> str:
    """
    Adds strategic conversation elements (acknowledgments, interruptions, disagreements)
    to make dialogue more natural and human-like.
    """
    other_agent = "Stat" if role == "RECO" else "Reco" if role == "STAT" else ""
    added_element = False

    # 🔥 Name usage in impactful moments
    should_use_name = (
        any(word in text.lower() for word in ['important', 'crucial', 'critical', 'significant', 'essential']) or
        any(word in text.lower() for word in ['but', 'however', 'although', 'disagree', 'challenge', 'contrary']) or
        (turn_count > 2 and random.random() < 0.3) or
        any(word in text.lower() for word in ['surprising', 'shocking', 'unexpected', 'dramatic', 'remarkable']) or
        (len(conversation_history) > 2 and "alternative" in text.lower()) or
        (random.random() < 0.2 and any(word in text.lower() for word in ['agree', 'right', 'correct', 'valid']))
    )

    if other_agent and should_use_name and random.random() < 0.7 and not added_element:
        address_formats = [f"{other_agent}, ", f"You know, {other_agent}, "]
        text = f"{random.choice(address_formats)}{text.lower()}"
        added_element = True

    # 😲 Emotional emphasis for surprises
    surprise_words = ['surprising', 'shocking', 'unexpected', 'dramatic', 'remarkable', 'concerning']
    if not added_element and random.random() < 0.25 and any(word in text.lower() for word in surprise_words):
        emphatics = ["Surprisingly, ", "Interestingly, ", "Remarkably, ", "Unexpectedly, "]
        text = f"{random.choice(emphatics)}{text}"
        added_element = True

    # 🧠 Interruptions and acknowledgments
    if not added_element and random.random() < INTERRUPTION_CHANCE and role != "NEXUS" and last_speaker and turn_count > 1:
        if random.random() < 0.5:
            acknowledgments = [
                "I see what you're saying, ",
                "That's a good point, ",
                "I understand your perspective, ",
                "You make a valid observation, "
            ]
            text = f"{random.choice(acknowledgments)}{text.lower()}"
        else:
            interruptions = [
                "If I might add, ",
                "Building on that, ",
                "To expand on your point, ",
                "Another way to look at this is "
            ]
            text = f"{random.choice(interruptions)}{text}"
        added_element = True

    # ✅ Agreement or disagreement with natural phrasing
    if not added_element and random.random() < 0.35 and role != "NEXUS" and turn_count > 1:
        if random.random() < AGREE_DISAGREE_RATIO:
            agreements = [
                "I agree with that approach, ",
                "That makes sense, ",
                "You're right about that, ",
                "That's a solid recommendation, "
            ]
            text = f"{random.choice(agreements)}{text.lower()}"
        else:
            disagreements = [
                "I have a slightly different view, ",
                "Another perspective to consider, ",
                "We might approach this differently, ",
                "Let me offer an alternative take, "
            ]
            text = f"{random.choice(disagreements)}{text.lower()}"

    return text


# ----------------------- Emotional Reactions Enhancer -----------------------

def add_emotional_reactions(text: str, role: str) -> str:
    """Inject occasional emotional reactions for human-like expression."""
    emotional_triggers = {
        "dramatic": ["That's quite a dramatic shift! ", "This is significant! ", "What a substantial change! "],
        "concerning": ["This is concerning. ", "That worries me slightly. ", "We should keep an eye on this. "],
        "positive": ["That's encouraging! ", "This is positive news. ", "I'm pleased to see this improvement. "],
        "surprising": ["That's surprising! ", "I didn't expect that result. ", "This is unexpected. "],
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


# ----------------------- Repetition Cleaning -----------------------

def clean_repetition(text: str) -> str:
    """Clean up repeated words, agent names, and redundant phrases."""
    text = re.sub(r'\b(Reco|Stat),\s+\1,?\s+', r'\1, ', text)
    text = re.sub(r'\b(\w+)\s+\1\b', r'\1', text)
    text = re.sub(r'\b(Given that|If we|The safer read|The safer interpretation),\s+\1', r'\1', text)
    return text


# ----------------------- Standalone Test -----------------------

if __name__ == "__main__":
    sample = "Well this is surprising data"
    print("Processed:", vary_opening(sample, "RECO", {}))
