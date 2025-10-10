"""
config.py — Centralized configuration management for the podcast generator.

This module:
- Loads environment variables from `.env`
- Provides typed, validated access to critical config values
- Centralizes constants for agents, LLM, and audio processing
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# --------------------------------------------------------------------------
# 📦 Load .env at startup
# --------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

# --------------------------------------------------------------------------
# 🔑 Azure OpenAI / GPT Settings
# --------------------------------------------------------------------------
AZURE_OPENAI_KEY: str = os.getenv("AZURE_OPENAI_KEY") or os.getenv("OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
OPENAI_API_VERSION: str = os.getenv("OPENAI_API_VERSION", "2024-05-01-preview")

# Validate essentials
if not AZURE_OPENAI_KEY or not AZURE_OPENAI_ENDPOINT:
    raise RuntimeError("❌ Missing required Azure OpenAI credentials in environment variables.")

# --------------------------------------------------------------------------
# 🧠 LLM Defaults
# --------------------------------------------------------------------------
DEFAULT_MAX_TOKENS: int = int(os.getenv("DEFAULT_MAX_TOKENS", 150))
DEFAULT_TEMPERATURE: float = float(os.getenv("DEFAULT_TEMPERATURE", 0.45))

# --------------------------------------------------------------------------
# 🔊 Azure Speech Service Settings
# --------------------------------------------------------------------------
TENANT_ID: str = os.getenv("TENANT_ID", "")
CLIENT_ID: str = os.getenv("CLIENT_ID", "")
CLIENT_SECRET: str = os.getenv("CLIENT_SECRET", "")
SPEECH_REGION: str = os.getenv("SPEECH_REGION", "eastus")
RESOURCE_ID: str = os.getenv("RESOURCE_ID", "")
COG_SCOPE: str = "https://cognitiveservices.azure.com/.default"

if not TENANT_ID or not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError("❌ Missing Azure Speech Service credentials (TENANT_ID, CLIENT_ID, CLIENT_SECRET).")

# --------------------------------------------------------------------------
# 🔈 Voice Settings
# --------------------------------------------------------------------------
VOICE_NEXUS: str = os.getenv("AZURE_VOICE_HOST", "en-US-SaraNeural")
VOICE_RECO: str = os.getenv("AZURE_VOICE_BA", "en-US-JennyNeural")
VOICE_STAT: str = os.getenv("AZURE_VOICE_DA", "en-US-BrianNeural")

VOICE_PLAN = {
    "NEXUS": {"style": "friendly", "base_pitch": "+1%", "base_rate": "-2%"},
    "RECO": {"style": "cheerful", "base_pitch": "+2%", "base_rate": "-3%"},
    "STAT": {"style": "serious", "base_pitch": "-1%", "base_rate": "-4%"},
}

# --------------------------------------------------------------------------
# 🎙️ Podcast Generation Settings
# --------------------------------------------------------------------------
DEFAULT_TURNS: int = int(os.getenv("DEFAULT_TURNS", 6))  # Number of Reco-Stat exchanges
DEFAULT_DURATION_MINUTES: float = float(os.getenv("DEFAULT_DURATION_MINUTES", 3.0))
MIN_PODCAST_DURATION: int = int(os.getenv("MIN_PODCAST_DURATION", 180))  # 3 minutes
MAX_PODCAST_DURATION: int = int(os.getenv("MAX_PODCAST_DURATION", 300))  # 5 minutes

# --------------------------------------------------------------------------
# 📁 Paths and Storage
# --------------------------------------------------------------------------
OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
# 🧪 Validation Constraints
# --------------------------------------------------------------------------
MAX_INPUT_TEXT_WORDS: int = int(os.getenv("MAX_INPUT_TEXT_WORDS", 50))
MAX_INPUT_AUDIO_LENGTH: int = int(os.getenv("MAX_INPUT_AUDIO_LENGTH", 180))  # in seconds

# --------------------------------------------------------------------------
# ✅ Utility Functions
# --------------------------------------------------------------------------
def validate_env() -> None:
    """Run a basic environment validation check."""
    required = {
        "AZURE_OPENAI_KEY": AZURE_OPENAI_KEY,
        "AZURE_OPENAI_ENDPOINT": AZURE_OPENAI_ENDPOINT,
        "TENANT_ID": TENANT_ID,
        "CLIENT_ID": CLIENT_ID,
        "CLIENT_SECRET": CLIENT_SECRET,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise RuntimeError(f"❌ Missing environment variables: {', '.join(missing)}")


# Run validation on import
validate_env()

if __name__ == "__main__":
    print("✅ Configuration loaded successfully.")
    print(f"Base Directory: {BASE_DIR}")
    print(f"Output Directory: {OUTPUT_DIR}")
