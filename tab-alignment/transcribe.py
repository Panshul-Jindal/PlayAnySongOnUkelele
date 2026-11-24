#!/usr/bin/env python3
"""When is each word sung? Vocals separated, then transcribed with word times.

1. Demucs (htdemucs, Rouard, Massa & Défossez 2023) splits the recording into
   the vocals and everything else, so the speech recogniser hears the voice
   alone. Skipped with --no-separate.
2. Whisper (Radford et al. 2022), run by faster-whisper, transcribes the
   vocals and gives each word a start and end time. No prompt by default:
   on Riptide, the tab's lyrics as Whisper's initial prompt made it skip the
   first verse (first word at 27.2 s against 9.6 s without; small.en, the
   first 60 s of the separated vocals). **[ORIGINAL]** observation.

The words are written as JSON, [{"word", "start", "end"}], in seconds. They
hold the song's lyrics, so they belong in data/preprocessed/ (git ignores it).

Usage:
    python3 tab-alignment/transcribe.py AUDIO OUT.json [--lyrics LYRICS.txt] [--no-separate]
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))

from devices import on_gpu, torch_device

#: faster-whisper model: English-only "small" runs on a CPU in about real time
MODEL = "small.en"
#: Whisper's prompt is cut to its last 224 tokens; this many characters stays under that
PROMPT_CHARS = 800


def separate(audio, out_wav):
    """Write the vocals of `audio` to `out_wav` with Demucs htdemucs; return out_wav."""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable, "-m", "demucs", "--two-stems", "vocals", "-n", "htdemucs",
                        "-d", torch_device(), "-o", tmp, audio], check=True)
        name = os.path.splitext(os.path.basename(audio))[0]
        os.makedirs(os.path.dirname(os.path.abspath(out_wav)), exist_ok=True)
        shutil.move(os.path.join(tmp, "htdemucs", name, "vocals.wav"), out_wav)
    return out_wav


def _load_cuda_libraries():
    """Load the cuBLAS and cuDNN that PyTorch's CUDA build installed (nvidia-*-cu12 packages),
    so CTranslate2, which faster-whisper runs on, finds them without LD_LIBRARY_PATH."""
    import ctypes
    import glob
    import importlib.util
    for package, pattern in (("nvidia.cublas", "libcublas*.so*"), ("nvidia.cudnn", "libcudnn*.so*")):
        spec = importlib.util.find_spec(package)
        for folder in (spec.submodule_search_locations or []) if spec else []:
            for lib in sorted(glob.glob(os.path.join(folder, "lib", pattern))):
                try:
                    ctypes.CDLL(lib, mode=ctypes.RTLD_GLOBAL)
                except OSError:
                    pass


def whisper_model(model=MODEL):
    """faster-whisper's model on the GPU (float16) when there is one, else on the CPU (int8).
    Falls back to the CPU if the GPU can't be used."""
    from faster_whisper import WhisperModel
    if on_gpu():
        try:
            _load_cuda_libraries()
            device = torch_device()
            index = int(device.split(":")[1]) if ":" in device else 0
            return WhisperModel(model, device="cuda", device_index=index, compute_type="float16")
        except Exception as e:  # noqa: BLE001  any failure: the CPU still works
            print(f"Whisper on the GPU failed ({e}); using the CPU", file=sys.stderr)
    return WhisperModel(model, device="cpu", compute_type="int8")


def transcribe(audio, prompt=None, model=MODEL):
    """[{"word", "start", "end"}] for every word Whisper hears in `audio`."""
    import librosa
    # decoded here, not by faster-whisper: its decoder breaks with av 19 (open() lost metadata_errors)
    samples, _ = librosa.load(audio, sr=16000, mono=True)
    whisper = whisper_model(model)
    segments, _ = whisper.transcribe(samples, language="en", word_timestamps=True, vad_filter=False,
                                     initial_prompt=prompt[:PROMPT_CHARS] if prompt else None,
                                     condition_on_previous_text=False)
    return [{"word": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)}
            for s in segments for w in (s.words or []) if w.word.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("audio", help="the song's recording")
    parser.add_argument("out", help="the words, e.g. data/preprocessed/asr/riptide.json")
    parser.add_argument("--lyrics", help="the tab's lyrics, as a prompt for Whisper")
    parser.add_argument("--vocals", help="where to keep the separated vocals (default: next to OUT)")
    parser.add_argument("--no-separate", action="store_true", help="transcribe the full mix")
    args = parser.parse_args()
    audio = args.audio
    if not args.no_separate:
        audio = separate(audio, args.vocals or os.path.splitext(args.out)[0] + ".vocals.wav")
    prompt = open(args.lyrics, encoding="utf-8").read().replace("\n", " ") if args.lyrics else None
    words = transcribe(audio, prompt)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(words, fh, indent=0, ensure_ascii=False)
    print(f"{len(words)} words; wrote {args.out}")


if __name__ == "__main__":
    main()
