import os
from pathlib import Path
from uap_podcast.models.audio import text_to_ssml, synth, write_master, wav_len
from uap_podcast.models.podcast import llm
import pytest
import asyncio

def test_text_to_ssml_generation():
    ssml = text_to_ssml("Hello world", "NEXUS")
    assert "<mstts:express-as" in ssml or "<speak" in ssml

def test_audio_synthesis_and_length():
    ssml = text_to_ssml("Testing audio synthesis", "RECO")
    audio_file = synth(ssml)
    assert os.path.exists(audio_file)
    assert wav_len(audio_file) > 0

def test_write_master_merges_files(tmp_path):
    ssml1 = text_to_ssml("Hello", "NEXUS")
    ssml2 = text_to_ssml("World", "RECO")
    audio1 = synth(ssml1)
    audio2 = synth(ssml2)
    merged = write_master([audio1, audio2], tmp_path / "merged.wav")
    assert os.path.exists(merged)

@pytest.mark.asyncio
async def test_llm_returns_text():
    response = await llm("You are a helpful AI", "Say hello", max_tokens=10)
    assert isinstance(response, str)
    assert len(response) > 0
