"""Local speech-to-text for think-aloud recordings (faster-whisper).

Usage:
  uv run python transcribe.py recordings/two-sum.m4a --slug two-integer-sum
  uv run python transcribe.py recordings/x.mp4 --model small        # smaller/faster model
  uv run python transcribe.py --latest [--slug <slug>]              # newest file in recordings/

Output: transcripts/<slug>_<YYYY-MM-DD_HHMM>.md with [MM:SS] segments, a header (duration, total
silence) and [PAUSE m:ss] markers for gaps longer than 15 s. Re-running on the same audio (by file
hash) prints the existing transcript path and exits.

Device: CUDA float16, falling back to CPU int8 if CUDA is unavailable or fails.
Decoding of m4a/mp3/wav/webm/mp4 is handled by PyAV (bundled with faster-whisper), no ffmpeg needed.
"""
import argparse, datetime as dt, hashlib, json, os, pathlib, sys, time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REC = pathlib.Path("recordings")
OUT = pathlib.Path("transcripts")
CACHE = OUT / ".cache.json"
PAUSE_S = 15.0
SILENCE_GAP_S = 2.0   # gaps between segments longer than this count toward "total silence"
EXTS = {".m4a", ".mp3", ".wav", ".webm", ".mp4", ".ogg", ".flac", ".aac", ".mov"}


def _add_cuda_dlls():
    """ctranslate2 on Windows needs cuBLAS/cuDNN DLLs; the nvidia-*-cu12 wheels ship them."""
    if os.name != "nt":
        return
    try:
        import nvidia  # namespace package
        for base in nvidia.__path__:
            for sub in ("cublas", "cudnn"):
                b = pathlib.Path(base) / sub / "bin"
                if b.is_dir():
                    os.add_dll_directory(str(b))
                    os.environ["PATH"] = str(b) + os.pathsep + os.environ.get("PATH", "")
    except Exception:
        pass


def file_hash(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mmss(t: float) -> str:
    t = int(round(t)); return f"{t // 60:02d}:{t % 60:02d}"


def load_model(name: str):
    from faster_whisper import WhisperModel
    _add_cuda_dlls()
    try:
        m = WhisperModel(name, device="cuda", compute_type="float16")
        # force CUDA init now so a broken CUDA setup fails here, not mid-transcription
        import numpy as np
        list(m.transcribe(np.zeros(16000, dtype=np.float32), language="en", beam_size=1)[0])
        return m, "cuda/float16"
    except Exception as e:
        print(f"CUDA unavailable ({str(e).splitlines()[0][:120]}); falling back to CPU int8", file=sys.stderr)
        return WhisperModel(name, device="cpu", compute_type="int8"), "cpu/int8"


def decode_audio(path: pathlib.Path, sr: int = 16000):
    """Decode any audio/video file to mono float32 at 16 kHz with PyAV.
    (faster-whisper's own decoder calls av.open(..., metadata_errors=...) which newer PyAV rejects.)"""
    import av, numpy as np
    chunks = []
    with av.open(str(path)) as container:
        stream = next(s for s in container.streams if s.type == "audio")
        resampler = av.AudioResampler(format="flt", layout="mono", rate=sr)
        for frame in container.decode(stream):
            for out in resampler.resample(frame):
                chunks.append(out.to_ndarray().reshape(-1))
        for out in resampler.resample(None):  # flush
            chunks.append(out.to_ndarray().reshape(-1))
    audio = np.concatenate(chunks).astype(np.float32) if chunks else np.zeros(0, dtype=np.float32)
    return audio, len(audio) / sr


def newest_recording():
    files = [p for p in REC.iterdir() if p.suffix.lower() in EXTS] if REC.exists() else []
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def transcribe(path: pathlib.Path, slug: str, model_name: str, force: bool = False) -> pathlib.Path:
    OUT.mkdir(exist_ok=True)
    cache = json.load(open(CACHE, encoding="utf-8")) if CACHE.exists() else {}
    h = file_hash(path)
    if not force and h in cache and pathlib.Path(cache[h]).exists():
        print(f"already transcribed: {cache[h]}")
        return pathlib.Path(cache[h])

    model, device = load_model(model_name)
    t0 = time.time()
    audio, audio_len = decode_audio(path)
    duration = audio_len
    # Silence and pauses come from the VAD speech chunks, not from Whisper's segment timestamps
    # (which stretch across silence).
    from faster_whisper.vad import VadOptions, get_speech_timestamps
    speech = get_speech_timestamps(audio, VadOptions(min_silence_duration_ms=500))
    gaps, cursor = [], 0.0
    for ch in speech:
        s, e = ch["start"] / 16000, ch["end"] / 16000
        if s - cursor > SILENCE_GAP_S:
            gaps.append((cursor, s))
        cursor = max(cursor, e)
    if duration - cursor > SILENCE_GAP_S:
        gaps.append((cursor, duration))
    silence = sum(e - s for s, e in gaps)
    pauses = [(s, e) for s, e in gaps if e - s > PAUSE_S]
    n_pauses = len(pauses)

    segments, info = model.transcribe(audio, language="en", beam_size=5, vad_filter=True,
                                      vad_parameters={"min_silence_duration_ms": 500})
    lines, pi = [], 0
    for seg in segments:
        while pi < len(pauses) and pauses[pi][1] <= seg.start + 0.5:
            g = pauses[pi][1] - pauses[pi][0]
            lines.append(f"[PAUSE {int(g) // 60}:{int(g) % 60:02d}]"); pi += 1
        text = seg.text.strip()
        if text:
            lines.append(f"[{mmss(seg.start)}] {text}")
    for s, e in pauses[pi:]:
        lines.append(f"[PAUSE {int(e - s) // 60}:{int(e - s) % 60:02d}]")

    mtime = dt.datetime.fromtimestamp(path.stat().st_mtime)
    stamp = mtime.strftime("%Y-%m-%d_%H%M")
    out = OUT / f"{slug}_{stamp}.md"
    header = [f"# Think-aloud transcript: {slug}", "",
              f"- Recording: {path.name}", f"- Recorded: {mtime.strftime('%Y-%m-%d %H:%M')}",
              f"- Duration: {mmss(duration)}   Total silence: {mmss(silence)} ({silence / max(duration, 1):.0%})   Pauses >{int(PAUSE_S)}s: {n_pauses}",
              f"- Model: {model_name} on {device}, transcribed in {time.time() - t0:.0f}s", ""]
    out.write_text("\n".join(header + lines) + "\n", encoding="utf-8")
    cache[h] = str(out)
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), indent=1)
    print(f"wrote {out}  ({len(lines)} lines, {mmss(duration)} audio, {device})")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?", help="audio/video file")
    ap.add_argument("--latest", action="store_true", help="use the newest file in recordings/")
    ap.add_argument("--slug", help="problem slug for the transcript name (default: file stem)")
    ap.add_argument("--model", default="large-v3", help="faster-whisper model (large-v3, medium, small, base, tiny)")
    ap.add_argument("--force", action="store_true", help="re-transcribe even if cached")
    args = ap.parse_args()
    path = pathlib.Path(args.file) if args.file else (newest_recording() if args.latest else None)
    if not path or not path.exists():
        sys.exit("no recording given/found. Usage: transcribe.py <file> [--slug s] or --latest")
    slug = args.slug or path.stem
    transcribe(path, slug, args.model, args.force)


if __name__ == "__main__":
    main()
