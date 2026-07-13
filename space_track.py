"""Generate a music track of weird space-like sounds and save it as a WAV file.

The track is built from four layers, all synthesized from scratch with numpy:

  * drone    - a deep, slowly-breathing chord of detuned sine waves
  * pings    - short FM "sonar" blips on a pentatonic scale, echoing away
  * sweeps   - long rising/falling chirps, like passing signals
  * whooshes - filtered-noise swells, like solar wind

Only numpy is required; audio is written with the standard-library wave module.

Examples:
    python space_track.py
    python space_track.py --duration 120 --seed 7
    python space_track.py --base-freq 45 --pings 30 --echo 0.7 --output dark.wav
    python space_track.py --sweeps 0 --whooshes 12 --brightness 400   (windy, no signals)
"""

import argparse
import wave

import numpy as np

SR = 44100  # sample rate


def env(n, attack, release):
    """Attack/release envelope of n samples (attack+release <= 1.0 as fractions)."""
    a = max(int(n * attack), 1)
    r = max(int(n * release), 1)
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, a)
    e[-r:] *= np.linspace(1, 0, r)
    return e


def place(track, sound, start_s, pan):
    """Mix a mono sound into the stereo track at start_s seconds, pan in [-1, 1]."""
    i0 = int(start_s * SR)
    i1 = min(i0 + len(sound), track.shape[1])
    if i0 >= track.shape[1]:
        return
    s = sound[: i1 - i0]
    track[0, i0:i1] += s * (1 - pan) / 2
    track[1, i0:i1] += s * (1 + pan) / 2


def drone(n, base, rng):
    """Detuned sine cluster with slow amplitude wobble - the bed of the track."""
    t = np.arange(n) / SR
    out = np.zeros(n)
    for ratio, amp in [(0.5, 0.5), (1.0, 1.0), (1.005, 0.7), (1.5, 0.35), (2.02, 0.2)]:
        f = base * ratio
        lfo = 0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(0.02, 0.08) * t
                                 + rng.uniform(0, 2 * np.pi))
        out += amp * lfo * np.sin(2 * np.pi * f * t + rng.uniform(0, 2 * np.pi))
    return out * env(n, 0.1, 0.1)


def ping(freq, dur, rng):
    """Short FM blip with an exponential decay - the 'sonar' sounds."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    mod = rng.uniform(1.5, 6.0)          # modulator ratio -> metallic weirdness
    beta = rng.uniform(2.0, 10.0)        # FM depth
    tone = np.sin(2 * np.pi * freq * t + beta * np.exp(-3 * t)
                  * np.sin(2 * np.pi * freq * mod * t))
    return tone * np.exp(-t * rng.uniform(4, 9)) * env(n, 0.005, 0.2)


def sweep(f0, f1, dur, rng):
    """Slow exponential chirp - a signal gliding across the spectrum."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f0 * (f1 / f0) ** (t / dur)
    phase = 2 * np.pi * np.cumsum(f) / SR
    vib = 1 + 0.01 * np.sin(2 * np.pi * rng.uniform(3, 7) * t)
    return np.sin(phase * vib) * env(n, 0.4, 0.4)


def whoosh(dur, cutoff, rng):
    """Low-passed noise swell - solar wind. FFT filtering, no scipy needed."""
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    spec = np.fft.rfft(noise)
    freqs = np.fft.rfftfreq(n, 1 / SR)
    c = cutoff * rng.uniform(0.5, 1.5)
    spec *= 1 / (1 + (freqs / c) ** 2)   # gentle 12 dB/oct rolloff
    out = np.fft.irfft(spec, n)
    out /= np.max(np.abs(out)) + 1e-9
    return out * env(n, 0.45, 0.45)


def add_echo(track, delay_s, feedback, repeats=6):
    """Simple feedback delay applied to the whole stereo mix."""
    d = int(delay_s * SR)
    out = track.copy()
    for k in range(1, repeats + 1):
        g = feedback ** k
        if g < 0.01 or k * d >= track.shape[1]:
            break
        # ping-pong: swap channels on each repeat
        src = track[::-1] if k % 2 else track
        out[:, k * d:] += g * src[:, : track.shape[1] - k * d]
    return out


def render(args):
    rng = np.random.default_rng(args.seed)
    n = int(args.duration * SR)
    track = np.zeros((2, n))

    # Pentatonic scale over the base -> pings sound alien but not sour.
    scale = args.base_freq * 4 * np.array([1, 9 / 8, 5 / 4, 3 / 2, 5 / 3])
    scale = np.concatenate([scale, scale * 2, scale * 4])

    if args.drone > 0:
        place(track, args.drone * drone(n, args.base_freq, rng), 0, 0.0)

    for _ in range(args.pings):
        f = rng.choice(scale) * rng.uniform(0.99, 1.01)
        place(track, 0.30 * rng.uniform(0.4, 1.0) * ping(f, rng.uniform(0.4, 1.5), rng),
              rng.uniform(0, args.duration - 2), rng.uniform(-0.9, 0.9))

    for _ in range(args.sweeps):
        f0, f1 = rng.uniform(80, 300), rng.uniform(600, 3000)
        if rng.random() < 0.5:
            f0, f1 = f1, f0   # half of them fall instead of rise
        place(track, 0.08 * sweep(f0, f1, rng.uniform(4, 10), rng),
              rng.uniform(0, args.duration - 10), rng.uniform(-0.7, 0.7))

    for _ in range(args.whooshes):
        place(track, 0.20 * whoosh(rng.uniform(3, 8), args.brightness, rng),
              rng.uniform(0, args.duration - 8), rng.uniform(-0.6, 0.6))

    if args.echo > 0:
        track = add_echo(track, delay_s=0.37, feedback=args.echo)

    # Master: soft clip, normalize, fade the whole track in and out.
    track = np.tanh(track * 1.5)
    track *= 0.9 / (np.max(np.abs(track)) + 1e-9)
    fade = int(1.5 * SR)
    track[:, :fade] *= np.linspace(0, 1, fade)
    track[:, -fade:] *= np.linspace(1, 0, fade)

    pcm = (track.T * 32767).astype(np.int16)
    with wave.open(args.output, "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(pcm.tobytes())
    print(f"saved {args.output} ({args.duration:.0f}s, seed={args.seed})")


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--duration", type=float, default=60.0, help="track length in seconds")
    p.add_argument("--output", default="space_track.wav")
    p.add_argument("--seed", type=int, default=None, help="random seed (default: random)")
    p.add_argument("--base-freq", type=float, default=55.0,
                   help="drone root frequency in Hz (55 = deep A)")
    p.add_argument("--drone", type=float, default=0.22,
                   help="drone volume 0-1 (0 = no drone)")
    p.add_argument("--pings", type=int, default=18, help="number of sonar blips")
    p.add_argument("--sweeps", type=int, default=5, help="number of gliding signals")
    p.add_argument("--whooshes", type=int, default=6, help="number of noise swells")
    p.add_argument("--brightness", type=float, default=900.0,
                   help="noise lowpass cutoff in Hz (higher = airier whooshes)")
    p.add_argument("--echo", type=float, default=0.45,
                   help="echo feedback 0-0.9 (0 = dry)")
    args = p.parse_args()
    render(args)


if __name__ == "__main__":
    main()
