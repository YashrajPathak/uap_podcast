"""
uap_podcast — Unified Audio Podcast Generation Package

This package orchestrates a multi-agent conversational podcast system with:
- 🎙️ Multiple intelligent agents (Nexus, Reco, Stat)
- 🧠 LLM-based conversation generation
- 🔊 Dynamic TTS audio synthesis
- 🧩 Modular structure for scalability (agents, models, utils, tests)
"""

import os
from dotenv import load_dotenv

# ✅ 1. Load environment variables early
load_dotenv()

# ✅ 2. Initialize global logging as soon as the package is imported
from uap_podcast.utils.logging import logger, info

info("📦 Initializing UAP Podcast package...")

# ✅ 3. Expose common package metadata
__version__ = "1.0.0"
__author__ = "UAP Engineering Team"
__all__ = [
    "agents",
    "models",
    "utils",
    "tests",
]

# ✅ 4. Optional sanity check: Required environment variables
_required_envs = ["AZURE_OPENAI_KEY", "AZURE_OPENAI_ENDPOINT", "TENANT_ID", "CLIENT_ID", "CLIENT_SECRET"]
_missing = [v for v in _required_envs if not os.getenv(v)]
if _missing:
    logger.warning(f"⚠️ Missing required environment variables: {', '.join(_missing)}")

info("✅ UAP Podcast system initialized and ready.")
