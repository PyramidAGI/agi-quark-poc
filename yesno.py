"""Tiny yes/no speech recognizer trained on your own voice.

Workflow:
  1. Record a few 1-second samples of each word (5 is plenty):
         python yesno.py record yes
         python yesno.py record no
  2. Recognize:
         python yesno.py recog
     Press Enter, say "yes" or "no", and the label is printed.

Samples are stored as WAV files under ./samples/<word>/. You are not limited
to yes/no - record any short words ("stop", "go", ...) and recog mode will
pick between all words it finds in the samples folder.

How it works: each clip is trimmed to the spoken part, converted to MFCC
features (mel-frequency cepstral coefficients), and compared to every stored
sample with dynamic time warping (DTW). Nearest sample wins. No ML framework,
no internet - just numpy + sounddevice.
"""

import argparse
import sys
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

SR = 16000          # sample rate; plenty for speech
SAMPLES_DIR = Path(__file__).parent / "samples"

# ---------------------------------------------------------------- recording

def record_clip(duration, device=None):
    """Record `duration` seconds from the microphone, return float32 mono."""
    print("  recording... speak now")
    audio = sd.rec(int(duration * SR), samplerate=SR, channels=1,
                   dtype="float32", device=device)
    sd.wait()
    print("  done")
    return audio[:, 0]


def save_wav(path, audio):
    pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(pcm.tobytes())


def load_wav(path):
    with wave.open(str(path), "rb") as f:
        assert f.getframerate() == SR, f"{path}: expected {SR} Hz"
        pcm = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16)
    return pcm.astype(np.float32) / 32767.0


# ----------------------------------------------------------------- features

def trim_to_word(audio, margin_s=0.08):
    """Keep the high-energy part of the clip (the spoken word)."""
    hop = 160
    frames = len(audio) // hop
    rms = np.array([np.sqrt(np.mean(audio[i * hop:(i + 1) * hop] ** 2))
                    for i in range(frames)])
    thresh = max(rms.max() * 0.15, 1e-4)
    active = np.nonzero(rms > thresh)[0]
    if len(active) == 0:
        return audio
    margin = int(margin_s * SR)
    lo = max(active[0] * hop - margin, 0)
    hi = min((active[-1] + 1) * hop + margin, len(audio))
    return audio[lo:hi]


def mel_filterbank(n_filters=26, n_fft=512):
    """Triangular mel filters spanning 0 .. SR/2."""
    def to_mel(f):
        return 2595 * np.log10(1 + f / 700)

    def from_mel(m):
        return 700 * (10 ** (m / 2595) - 1)

    pts = from_mel(np.linspace(to_mel(0), to_mel(SR / 2), n_filters + 2))
    bins = np.floor((n_fft + 1) * pts / SR).astype(int)
    fb = np.zeros((n_filters, n_fft // 2 + 1))
    for i in range(n_filters):
        a, b, c = bins[i], bins[i + 1], bins[i + 2]
        if b > a:
            fb[i, a:b] = (np.arange(a, b) - a) / (b - a)
        if c > b:
            fb[i, b:c] = (c - np.arange(b, c)) / (c - b)
    return fb


def mfcc(audio, n_coeffs=13, n_fft=512, win=400, hop=160):
    """MFCC sequence: (frames, n_coeffs), mean-normalized over time."""
    audio = np.append(audio[0], audio[1:] - 0.97 * audio[:-1])  # pre-emphasis
    n_frames = max(1 + (len(audio) - win) // hop, 1)
    idx = np.arange(win)[None, :] + hop * np.arange(n_frames)[:, None]
    frames = audio[np.minimum(idx, len(audio) - 1)] * np.hamming(win)
    power = np.abs(np.fft.rfft(frames, n_fft)) ** 2 / n_fft
    fb = mel_filterbank(n_fft=n_fft)
    logmel = np.log(power @ fb.T + 1e-10)
    n_filters = fb.shape[0]
    k = np.arange(n_coeffs)[:, None]
    dct = np.cos(np.pi * k * (2 * np.arange(n_filters) + 1) / (2 * n_filters))
    feats = logmel @ dct.T
    return feats - feats.mean(axis=0)  # cepstral mean normalization


def dtw_distance(a, b):
    """Dynamic-time-warping distance between two MFCC sequences."""
    n, m = len(a), len(b)
    dist = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2)
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0.0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i, j] = dist[i - 1, j - 1] + min(D[i - 1, j], D[i, j - 1],
                                               D[i - 1, j - 1])
    return D[n, m] / (n + m)  # length-normalized


# ----------------------------------------------------------------- commands

def cmd_record(args):
    word_dir = SAMPLES_DIR / args.word
    word_dir.mkdir(parents=True, exist_ok=True)
    existing = len(list(word_dir.glob("*.wav")))
    print(f"Recording {args.count} sample(s) of '{args.word}' "
          f"({existing} already stored).")
    for i in range(args.count):
        input(f"[{i + 1}/{args.count}] Press Enter, then say '{args.word}': ")
        audio = record_clip(args.duration, args.device)
        if np.abs(audio).max() < 0.01:
            print("  ! barely any signal - check your microphone, retrying")
            continue
        existing += 1
        path = word_dir / f"{args.word}_{existing:02d}.wav"
        save_wav(path, audio)
        print(f"  saved {path}")


def load_templates():
    """Load all stored samples as {word: [mfcc, ...]}."""
    templates = {}
    for word_dir in sorted(SAMPLES_DIR.glob("*")):
        if word_dir.is_dir():
            feats = [mfcc(trim_to_word(load_wav(p)))
                     for p in sorted(word_dir.glob("*.wav"))]
            if feats:
                templates[word_dir.name] = feats
    return templates


def cmd_recog(args):
    templates = load_templates()
    if len(templates) < 2:
        sys.exit("Need samples of at least 2 words first, e.g.:\n"
                 "  python yesno.py record yes\n  python yesno.py record no")
    counts = ", ".join(f"'{w}' x{len(t)}" for w, t in templates.items())
    print(f"Loaded templates: {counts}")
    print("Press Enter, then speak. Ctrl+C to quit.")
    while True:
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            print("bye")
            return
        audio = record_clip(args.duration, args.device)
        if np.abs(audio).max() < 0.01:
            print("  ? heard nothing")
            continue
        feats = mfcc(trim_to_word(audio))
        scores = {w: min(dtw_distance(feats, t) for t in temps)
                  for w, temps in templates.items()}
        ranked = sorted(scores, key=scores.get)
        best, runner_up = ranked[0], ranked[1]
        margin = scores[runner_up] - scores[best]
        if scores[best] > args.reject:
            print(f"  ? not sure (best guess {best}, distance "
                  f"{scores[best]:.1f} > {args.reject})")
        else:
            print(f"  >>> {best.upper()}   "
                  f"(distance {scores[best]:.1f}, margin +{margin:.1f})")


def cmd_devices(_args):
    print(sd.query_devices())


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--duration", type=float, default=1.0,
                   help="clip length in seconds (default 1.0)")
    p.add_argument("--device", type=int, default=None,
                   help="input device index (see: python yesno.py devices)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("record", help="record training samples of one word")
    pr.add_argument("word", help="the word to record, e.g. yes")
    pr.add_argument("--count", type=int, default=5,
                    help="how many samples to record (default 5)")
    pr.set_defaults(func=cmd_record)

    pg = sub.add_parser("recog", help="recognize spoken words")
    pg.add_argument("--reject", type=float, default=18.0,
                    help="distance above which the result is '? not sure'")
    pg.set_defaults(func=cmd_recog)

    pd = sub.add_parser("devices", help="list audio devices")
    pd.set_defaults(func=cmd_devices)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
