"""Translate text to audible Morse code.

Plays the code through the speakers (and/or writes it to a WAV file) and
prints the dots and dashes while it sounds.

Examples:
    python morse.py "hello world"
    python morse.py --wpm 12 --freq 550 "sos sos"
    python morse.py --output message.wav --no-play "meet at dawn"
    echo secret text | python morse.py -

Timing follows the standard: dah = 3 dits, gap between symbols = 1 dit,
between letters = 3 dits, between words = 7 dits, dit = 1.2/WPM seconds.
"""

import argparse
import sys
import wave

import numpy as np

SR = 44100

MORSE = {
    "a": ".-", "b": "-...", "c": "-.-.", "d": "-..", "e": ".", "f": "..-.",
    "g": "--.", "h": "....", "i": "..", "j": ".---", "k": "-.-", "l": ".-..",
    "m": "--", "n": "-.", "o": "---", "p": ".--.", "q": "--.-", "r": ".-.",
    "s": "...", "t": "-", "u": "..-", "v": "...-", "w": ".--", "x": "-..-",
    "y": "-.--", "z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
    ".": ".-.-.-", ",": "--..--", "?": "..--..", "'": ".----.", "!": "-.-.--",
    "/": "-..-.", "(": "-.--.", ")": "-.--.-", "&": ".-...", ":": "---...",
    ";": "-.-.-.", "=": "-...-", "+": ".-.-.", "-": "-....-", "_": "..--.-",
    '"': ".-..-.", "$": "...-..-", "@": ".--.-.",
}


def tone(dur_s, freq, volume):
    """A sine beep with 5 ms ramps so the keying doesn't click."""
    n = int(dur_s * SR)
    t = np.arange(n) / SR
    beep = volume * np.sin(2 * np.pi * freq * t)
    ramp = min(int(0.005 * SR), n // 2)
    beep[:ramp] *= np.linspace(0, 1, ramp)
    beep[-ramp:] *= np.linspace(1, 0, ramp)
    return beep


def silence(dur_s):
    return np.zeros(int(dur_s * SR))


def encode(text, wpm, freq, volume):
    """Return (audio, transcript) for the whole message."""
    dit = 1.2 / wpm
    parts, lines = [], []
    for word in text.lower().split():
        letters = []
        for ch in word:
            code = MORSE.get(ch)
            if code is None:
                continue  # silently skip untranslatable characters
            for i, sym in enumerate(code):
                parts.append(tone(dit if sym == "." else 3 * dit, freq, volume))
                if i < len(code) - 1:
                    parts.append(silence(dit))
            parts.append(silence(3 * dit))
            letters.append(f"{ch} {code}")
        if letters:
            parts.append(silence(4 * dit))  # 3 already added -> 7 total
            lines.append("   ".join(letters))
    if not parts:
        sys.exit("nothing translatable in the input text")
    return np.concatenate(parts), "\n".join(lines)


def save_wav(path, audio):
    pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(pcm.tobytes())


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("text", nargs="+",
                   help="text to translate; use '-' to read from stdin")
    p.add_argument("--wpm", type=float, default=18.0,
                   help="speed in words per minute (default 18)")
    p.add_argument("--freq", type=float, default=700.0,
                   help="tone frequency in Hz (default 700, the classic pitch)")
    p.add_argument("--volume", type=float, default=0.6, help="0-1 (default 0.6)")
    p.add_argument("--output", help="also save the audio to this WAV file")
    p.add_argument("--no-play", action="store_true",
                   help="don't play through the speakers (use with --output)")
    args = p.parse_args()

    text = " ".join(args.text)
    if text.strip() == "-":
        text = sys.stdin.read()

    audio, transcript = encode(text, args.wpm, args.freq, args.volume)
    print(transcript)
    print(f"({len(audio) / SR:.1f}s at {args.wpm:g} wpm)")

    if args.output:
        save_wav(args.output, audio)
        print(f"saved {args.output}")
    if not args.no_play:
        import sounddevice as sd
        sd.play(audio, SR)
        sd.wait()


if __name__ == "__main__":
    main()
