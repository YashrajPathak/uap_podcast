"""
tools.py — Utility functions for NexusAgent.

This file contains small, stateless helper functions that:
- Clean or format LLM outputs
- Add conversational variety
- Ensure sentence completeness
- Provide small text post-processing utilities
"""

import re
import random
from typing import Dict

# ---------- Sentence Quality & Formatting ----------

def ensure_complete_sentence(text: str) -> str:
    """
    Ensure the text ends as a proper sentence with punctuation.
    Removes stray formatting artifacts from LLM responses.
    """
    t = re.sub(r'[`*_#>]+', ' ', text).strip()
    t = re.sub(r'\s{2,}', ' ', t)
    if t and t[-1] not in {'.', '!', '?'}:
        t += '.'
    return t


def clean_repetition(text: str) -> str:
    """
    Clean obvious repetitive phrases or names that sometimes leak into generated text.
    """
    text = re.sub(r'\b(Nexus),\s+\1,?\s+', r'\1, ', text)
    text = re.sub(r'\b(\w+)\s+\1\b', r'\1', text)
    return text


# ---------- Conversational Style Enhancers ----------

FORBIDDEN_OPENERS = {"well", "okay", "so", "look", "right", "you know", "hey", "actually"}

def strip_forbidden_openers(text: str) -> str:
    """
    Remove common filler words from the beginning of a sentence.
    """
    low = text.lower().strip()
    for w in sorted(FORBIDDEN_OPENERS, key=lambda x: -len(x)):
        if low.startswith(w + " "):
            return text[len(w):].lstrip(" ,.-–—")
    return text


OPENERS = [
    "Given that", "Looking at this", "From this perspective",
    "Based on the data", "Considering the context", "If we step back"
]

def vary_opening(text: str, last_open: Dict[str, str]) -> str:
    """
    Add variety to how Nexus starts sentences.
    Ensures we don’t repeat the same opener twice in a row.
    """
    t = strip_forbidden_openers(text)
    first = (t.split()[:1] or [""])[0].lower()

    if first in FORBIDDEN_OPENERS or not first or random.random() < 0.4:
        cand = random.choice(OPENERS)
        if last_open.get("NEXUS") == cand:
            pool = [c for c in OPENERS if c != cand]
            cand = random.choice(pool) if pool else cand
        last_open["NEXUS"] = cand
        return f"{cand}, {t}"
    return t


# ---------- Emotion / Reaction Layer ----------

def add_emotional_reactions(text: str) -> str:
    """
    Add occasional emotional emphasis for natural-sounding Nexus narration.
    """
    emotional_triggers = {
        "dramatic": ["That's quite a dramatic shift! ", "This is significant! "],
        "concerning": ["This is concerning. ", "We should keep an eye on this. "],
        "positive": ["That's encouraging! ", "This is positive news. "],
        "surprising": ["That's surprising! ", "I didn't expect that result. "]
    }

    for trigger, reactions in emotional_triggers.items():
        if trigger in text.lower() and random.random() < 0.4:
            reaction = random.choice(reactions)
            if ',' in text:
                parts = text.split(',', 1)
                text = f"{parts[0]}, {reaction}{parts[1].lstrip()}"
            else:
                text = f"{reaction}{text}"
            break

    return text
