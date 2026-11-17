"""Local music bed with MusicGen (facebook/musicgen-small), no account needed.

Run: ~/.venvs/musicgen/bin/python -I tools/music.py
Generates two ~28 s takes from one mood prompt and writes assets/music/take-<n>.wav (32 kHz mono).
mix.sh then builds the 62 s bed from the better take (crossfaded loop, fades, loudness).
"""
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from transformers import AutoProcessor, MusicgenForConditionalGeneration

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "music"
OUT.mkdir(parents=True, exist_ok=True)
PROMPT = ("calm hopeful cinematic underscore for a healthcare product film, warm felt piano, soft string pads, "
          "gentle steady pulse, light afrobeat-inspired percussion, rising and reassuring, major key, 100 bpm, "
          "clean modern mix, no vocals")

device = "mps" if torch.backends.mps.is_available() else "cpu"
proc = AutoProcessor.from_pretrained("facebook/musicgen-small")
model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small").to(device)
sr = model.config.audio_encoder.sampling_rate
for n in (1, 2):
    torch.manual_seed(100 + n)
    inputs = proc(text=[PROMPT], padding=True, return_tensors="pt").to(device)
    audio = model.generate(**inputs, do_sample=True, guidance_scale=3.0, max_new_tokens=1400)  # ~28 s at 50 tok/s
    wav = audio[0, 0].float().cpu().numpy()
    wav = wav / max(1e-6, float(np.abs(wav).max())) * 0.9
    sf.write(OUT / f"take-{n}.wav", wav, sr)
    print("wrote", OUT / f"take-{n}.wav", round(len(wav) / sr, 1), "s", flush=True)
