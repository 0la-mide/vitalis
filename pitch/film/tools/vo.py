"""Voices voice/script.tsv in the Davis voice (VibeVoice, same settings as the case-file host).

Run: ~/.venvs/mlx-audio/bin/python -I tools/vo.py
Each line: up to 3 takes, checked by transcription (VoiceStudio on :3900) and by fit to its slot; the best take is
trimmed of edge silence and written to voice/lines/<id>.wav. voice/takes.json records every take.
"""
import difflib, json, re, subprocess, wave
from pathlib import Path

import mlx.core as mx
from mlx_audio.tts.generate import generate_audio
from mlx_audio.tts.utils import load_model

ROOT = Path(__file__).resolve().parents[1]
V = ROOT / "voice"
OUT = V / "lines"; OUT.mkdir(parents=True, exist_ok=True)
WORK = V / "takes"; WORK.mkdir(exist_ok=True)
CFG = {"model": "mlx-community/VibeVoice-Realtime-0.5B-8bit", "voice": "en-Davis_man", "seed": 1234}
rows = [l.split("\t") for l in (V / "script.tsv").read_text().splitlines() if l.strip() and not l.startswith("#")]
norm = lambda t: re.sub(r"[^a-z0-9 ]", " ", t.lower().replace("-", " ")).split()


def seconds(p):
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


def transcribe(p):
    out = subprocess.run(["curl", "-s", "-m", "300", "-X", "POST", "http://localhost:3900/v1/audio/transcriptions",
                          "-F", "model=whisper-1", "-F", f"file=@{p}", "-F", "response_format=json"],
                         capture_output=True, text=True).stdout
    try:
        return json.loads(out).get("text", "")
    except json.JSONDecodeError:
        return ""


def trim(src, dst):
    """Cut leading/trailing silence, keep 60 ms of air each side, 48 kHz mono."""
    f = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.06,areverse,"
         "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.06,areverse")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", f, "-ar", "48000", "-ac", "1", str(dst)],
                   check=True)


model = load_model(model_path=CFG["model"])
log = {}
for lid, start, max_s, text in rows:
    dst = OUT / f"{lid}.wav"
    if dst.exists():
        continue
    want = norm(text.replace("VITALIS", "vitalis").replace("NHIA", "n h i a"))
    best = None
    for take in range(1, 4):
        prefix = f"{lid}-t{take}"
        for old in WORK.glob(prefix + "*"):
            old.unlink()
        mx.random.seed(CFG["seed"] + take - 1)
        tts = re.sub(r"([,.?!;:])\s+", "\\1\n", text)  # a break after punctuation makes VibeVoice pause there
        generate_audio(text=tts, model=model, output_path=str(WORK), file_prefix=prefix, audio_format="wav",
                       save=True, verbose=False, join_audio=True, voice=CFG["voice"])
        parts = sorted(WORK.glob(prefix + "*.wav"))
        raw = parts[0]
        cut = WORK / f"{prefix}.cut.wav"
        trim(raw, cut)
        dur = seconds(cut)
        heard = transcribe(cut)
        got = norm(heard.replace("Vitalis", "vitalis"))
        sim = difflib.SequenceMatcher(None, [w for w in want if w not in ("n", "h", "i", "a")],
                                      [w for w in got if w not in ("n", "h", "i", "a", "nhia")]).ratio()
        fits = dur <= float(max_s) * 1.05
        score = sim - (0 if fits else 0.25 + (dur - float(max_s)) * 0.1)
        log.setdefault(lid, []).append({"take": take, "seconds": round(dur, 2), "sim": round(sim, 3), "heard": heard})
        print(f"{lid} take {take}: {dur:.2f}s / {max_s}s  sim {sim:.2f}  | {heard}", flush=True)
        if best is None or score > best[0]:
            best = (score, cut)
        if sim >= 0.93 and fits:
            break
    best[1].replace(dst)
(V / "takes.json").write_text(json.dumps(log, indent=1))
print("done")
