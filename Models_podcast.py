"""
podcast.py — Central LLM orchestration module

This module is responsible for:
- Setting up Azure OpenAI client
- Performing safe LLM calls with retries and fallbacks
- Ensuring responses are clean, safe, and complete
- Providing a single async interface (`llm`) for all agents to use
"""

import os
import re
import asyncio
from dotenv import load_dotenv
from typing import Optional
from openai import AzureOpenAI, BadRequestError

# ------------------------- Load Environment -------------------------
load_dotenv()

AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY") or os.getenv("OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION", "2024-05-01-preview")

if not all([AZURE_OPENAI_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT, OPENAI_API_VERSION]):
    raise RuntimeError("❌ Missing Azure OpenAI environment variables.")

# ------------------------- Client Setup -------------------------
oai = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version=OPENAI_API_VERSION
)

# ------------------------- Core Sync Call -------------------------
def _llm_sync(system: str, user: str, max_tokens: int, temperature: float) -> str:
    """Direct synchronous call to Azure OpenAI."""
    r = oai.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        max_tokens=max_tokens,
        temperature=temperature
    )
    return (r.choices[0].message.content or "").strip()

# ------------------------- Text Softening -------------------------
def _soften(text: str) -> str:
    """Softens strict or unsafe wording in prompts."""
    t = text
    t = re.sub(r'\b[Ss]ole factual source\b', 'primary context', t)
    t = re.sub(r'\b[Dd]o not\b', 'please avoid', t)
    t = re.sub(r"\b[Dd]on't\b", 'please avoid', t)
    t = re.sub(r'\b[Ii]gnore\b', 'do not rely on', t)
    t = t.replace("debate", "discussion").replace("Debate", "Discussion")
    return t

def _looks_ok(text: str) -> bool:
    """Check if the LLM output looks valid and safe."""
    return (
        bool(text and len(text.strip()) >= 8) and
        text.count(".") <= 3 and
        not text.isupper() and
        not re.search(r'http[s]?://', text)
    )

def ensure_complete_sentence(text: str) -> str:
    """Ensure response ends with a proper sentence terminator."""
    t = re.sub(r'[`*_#>]+', ' ', text).strip()
    t = re.sub(r'\s{2,}', ' ', t)
    if t and t[-1] not in {'.', '!', '?'}:
        t += '.'
    return t

# ------------------------- Safe LLM Wrapper -------------------------
def llm_safe(system: str, user: str, max_tokens: int, temperature: float) -> str:
    """
    Safe wrapper around Azure OpenAI LLM calls.
    Includes validation, retries, softening, and fallbacks.
    """
    try:
        out = _llm_sync(system, user, max_tokens, temperature)
        if not _looks_ok(out):
            out = _llm_sync(
                system, user,
                max_tokens=max(80, max_tokens // 2),
                temperature=min(0.8, temperature + 0.1)
            )
        return ensure_complete_sentence(out)

    except BadRequestError:
        # Softened retry
        soft_sys = _soften(system) + " Always keep a professional, neutral tone and comply with safety policies."
        soft_user = _soften(user)
        try:
            out = _llm_sync(
                soft_sys, soft_user,
                max_tokens=max(80, max_tokens - 20),
                temperature=max(0.1, temperature - 0.2)
            )
            return ensure_complete_sentence(out)
        except Exception:
            # Final fallback (safe minimum)
            minimal_system = (
                "You are a professional assistant; produce one safe, neutral, evidence-based sentence "
                "grounded in the provided context."
            )
            minimal_user = (
                "Summarize key metric insights and propose one safe, low-regret action in one sentence."
            )
            out = _llm_sync(minimal_system, minimal_user, max_tokens=100, temperature=0.2)
            return ensure_complete_sentence(out)

# ------------------------- Async Wrapper (Public API) -------------------------
async def llm(
    system: str,
    user: str,
    max_tokens: int = 130,
    temperature: float = 0.45
) -> str:
    """
    Async wrapper around `llm_safe`, used by all agents.

    Args:
        system: System-level instruction defining the agent persona.
        user: User prompt / context.
        max_tokens: Maximum tokens to generate.
        temperature: Sampling temperature (0.0–1.0).

    Returns:
        str: Clean, safe, complete LLM response.
    """
    return await asyncio.to_thread(llm_safe, system, user, max_tokens, temperature)

# ------------------------- Standalone Test -------------------------
if __name__ == "__main__":
    async def _test():
        system_prompt = "You are a concise podcast assistant."
        user_prompt = "Summarize the top 2 trends from the given data."
        print(await llm(system_prompt, user_prompt))

    asyncio.run(_test())
