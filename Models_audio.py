"""
audio.py — TTS, SSML, and audio assembly utilities

Provides:
- Azure Cognitive Services Speech setup (AAD token)
- SSML helpers: number emphasis, clause pauses, inflection jitter
- text_to_ssml(text, role) -> SSML
- synth(ssml) -> path to synthesized WAV file
- write_master(segments, out_path) -> final concatenated WAV
- wav_len(path) -> seconds
"""

import os
import re
import wave
import tempfile
import random
import datetime
from typing import List, Tuple

from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk
from azure.identity import ClientSecretCredential

# ------------------------- Env & Globals -------------------------
load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
SPEECH_REGION = os.getenv("SPEECH_REGION", "eastus")
RESOURCE_ID = os.getenv("RESOURCE_ID")  # optional; used for multi-tenant hosted resources
COG_SCOPE = "https://cognitiveservices.azure.com/.default"

if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET, SPEECH_REGION]):
    raise RuntimeError("❌ Missing AAD Speech env vars (TENANT_ID, CLIENT_ID, CLIENT_SECRET, SPEECH_REGION).")

cred = ClientSecretCredential(tenant_id=TENANT_ID, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)

def cog_token_str() -> str:
    tok = cred.get_token(COG_SCOPE).token
    return f"aad#{RESOURCE_ID}#{tok}" if RESOURCE_ID else tok

# Voices (override via env if desired)
VOICE_NEXUS = os.getenv("AZURE_VOICE_HOST", "en-US-SaraNeural")   # Host (female)
VOICE_RECO  = os.getenv("AZURE_VOICE_BA",   "en-US-JennyNeural")  # Reco (female)
VOICE_STAT  = os.getenv("AZURE_VOICE_DA",   "en-US-BrianNeural")  # Stat (male)

VOICE_PLAN = {
    "NEXUS": {"style": "friendly",  "base_pitch": "+1%", "base_rate": "-2%"},
    "RECO":  {"style": "cheerful",  "base_pitch": "+2%", "base_rate": "-3%"},
    "STAT":  {"style": "serious",   "base_pitch": "-1%", "base_rate": "-4%"},
}

# Track temp files for potential cleanup by app (optional)
TMP: List[str] = []

# ------------------------- SSML Helpers -------------------------
def _jitter(pct: str, spread: int = 3) -> str:
    m = re.match(r'([+-]?\d+)%', pct.strip())
    base = int(m.group(1)) if m else 0
    j = random.randint(-spread, spread)
    return f"{base + j}%"

def _emphasize_numbers(text: str) -> str:
    # Light emphasis on large numbers and percentages (no SSML tags inside tags again)
    def wrap(s: str) -> str:
        return f'<emphasis level="moderate">{s}</emphasis>'
    t = re.sub(r'\b\d{3,}(\.\d+)?\b', lambda m: wrap(m.group(0)), text)
    t = re.sub(r'\b-?\d+(\.\d+)?%\b', lambda m: wrap(m.group(0)), t)
    return t

def _clause_pauses(text: str) -> str:
    t = re.sub(r',\s', ',<break time="220ms"/> ', text)
    t = re.sub(r';\s', ';<break time="260ms"/> ', t)
    t = re.sub(r'\bHowever\b', 'However,<break time="220ms"/>', t, flags=re.I)
    t = re.sub(r'\bBut\b', 'But,<break time="220ms"/>', t, flags=re.I)
    return t

def _inflect(text: str, role: str) -> Tuple[str, str]:
    base_pitch = VOICE_PLAN[role]["base_pitch"]
    base_rate = VOICE_PLAN[role]["base_rate"]
    pitch = _jitter(base_pitch, 3)
    rate  = _jitter(base_rate, 2)

    # Subtle pitch adjustments by utterance type
    try:
        p = int(pitch.replace('%', ''))
    except Exception:
        p = 0
    if text.strip().endswith("?"):
        pitch = f"{p + 4}%"
    elif re.search(r'\bhowever\b|\bbut\b', text, re.I):
        pitch = f"{p - 2}%"
    elif any(word in text.lower() for word in ['surprising', 'shocking', 'unexpected', 'dramatic', 'remarkable']):
        pitch = f"{p + 3}%"
    return pitch, rate

def _ssml(voice: str, style: str | None, rate: str, pitch: str, inner: str) -> str:
    if style:
        return f"""<speak version="1.0" xml:lang="en-US" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts">
  <voice name="{voice}">
    <mstts:express-as style="{style}">
      <prosody rate="{rate}" pitch="{pitch}">{inner}</prosody>
    </mstts:express-as>
  </voice>
</speak>"""
    else:
        return f"""<speak version="1.0" xml:lang="en-US" xmlns="http://www.w3.org/2001/10/synthesis">
  <voice name="{voice}">
    <prosody rate="{rate}" pitch="{pitch}">{inner}</prosody>
  </voice>
</speak>"""

def text_to_ssml(text: str, role: str) -> str:
    """
    Convert plain text into styled SSML based on role: NEXUS | RECO | STAT
    """
    plan  = VOICE_PLAN[role]
    voice = VOICE_NEXUS if role == "NEXUS" else VOICE_RECO if role == "RECO" else VOICE_STAT

    t = text.strip()
    t = _emphasize_numbers(t)
    t = _clause_pauses(t)
    t = f"{t}<break time=\"320ms\"/>"  # final breathing room

    pitch, rate = _inflect(text, role)
    return _ssml(voice, plan["style"], rate, pitch, t)

# ------------------------- Synthesis & Audio I/O -------------------------
def synth(ssml: str) -> str:
    """
    Synthesize SSML to a temporary mono 24kHz 16-bit PCM WAV file and return its path.
    """
    cfg = speechsdk.SpeechConfig(auth_token=cog_token_str(), region=SPEECH_REGION)
    cfg.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
    )
    fd, tmp = tempfile.mkstemp(prefix="seg_", suffix=".wav")
    os.close(fd)
    TMP.append(tmp)

    out = speechsdk.audio.AudioOutputConfig(filename=tmp)
    spk = speechsdk.SpeechSynthesizer(speech_config=cfg, audio_config=out)

    r = spk.speak_ssml_async(ssml).get()
    if r.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return tmp

    # Fallback once with plain text
    plain = re.sub(r'<[^>]+>', ' ', ssml)
    spk = speechsdk.SpeechSynthesizer(speech_config=cfg, audio_config=out)
    r = spk.speak_text_async(plain).get()
    if r.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return tmp

    try:
        os.remove(tmp)
    except Exception:
        pass
    raise RuntimeError("TTS failed")

def wav_len(path: str) -> float:
    with wave.open(path, "rb") as r:
        fr = r.getframerate() or 24000
        return r.getnframes() / float(fr)

def write_master(segments: List[str], out_path: str, rate: int = 24000) -> str:
    """
    Concatenate mono 24kHz 16-bit PCM WAV segments into a single WAV at out_path.
    """
    fd, tmp = tempfile.mkstemp(prefix="final_", suffix=".wav")
    os.close(fd)
    try:
        with wave.open(tmp, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            for seg in segments:
                with wave.open(seg, "rb") as r:
                    if (r.getframerate(), r.getnchannels(), r.getsampwidth()) != (rate, 1, 2):
                        raise RuntimeError(f"Segment format mismatch: {seg}")
                    w.writeframes(r.readframes(r.getnframes()))

        try:
            os.replace(tmp, out_path)
        except PermissionError:
            base, ext = os.path.splitext(out_path)
            alt = f"{base}{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            os.replace(tmp, alt)
            print(f"⚠️ Output was locked; wrote to {alt}")
            return alt
        return out_path
    except Exception:
        try:
            os.remove(tmp)
        except Exception:
            pass
        raise

# ------------------------- Quick Self-Test -------------------------
if __name__ == "__main__":
    demo = "Welcome to our metrics discussion; ASA improved sharply, however we must confirm queue mapping."
    ssml = text_to_ssml(demo, role="NEXUS")
    path = synth(ssml)
    print("Synth path:", path, "length(s):", round(wav_len(path), 2))
```0
