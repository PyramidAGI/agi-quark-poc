"""Generate a "pixel radiation" space pattern: a starfield of bright pixel dots
radiating from a center point, with a glowing column of light in the middle.

Reproduces the look of `pixel radiation space pattern.png` by default, and the
parameters let you produce other patterns (spiral, rings, burst, uniform).

Examples:
    python radiation_pattern.py
    python radiation_pattern.py --mode spiral --swirl 6 --glow-color 80,0,120
    python radiation_pattern.py --mode rings --rings 14 --dots 6000
    python radiation_pattern.py --mode burst --rays 48 --streak 30
    python radiation_pattern.py --mode uniform --glow-strength 0 --dots 2500
"""

import argparse

import numpy as np
from PIL import Image


def parse_color(text):
    """Parse 'R,G,B' (0-255) into a float array scaled to 0-1."""
    parts = [int(p) for p in text.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("color must be 'R,G,B' with values 0-255")
    return np.array(parts, dtype=np.float64) / 255.0


def make_background(width, height, cx, cy, bg_color, glow_color,
                    glow_strength, glow_width, glow_softness):
    """Dark background plus a vertical glowing column through the center."""
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float64)
    img = np.zeros((height, width, 3))
    img += bg_color

    # Vertical glow band: falls off horizontally from the center column,
    # widening slightly and dimming toward top/bottom (like the photo).
    dx = np.abs(xx - cx)
    dy = np.abs(yy - cy) / (0.6 * height)
    band = glow_width * (1.0 + glow_softness * dy)
    glow = np.exp(-((dx / band) ** 2)) * np.exp(-(dy ** 2))
    # Hot core right at the axis
    core = np.exp(-((dx / (band * 0.25)) ** 2)) * np.exp(-(dy ** 2)) * 0.6

    img += glow_strength * (glow[..., None] * glow_color
                            + core[..., None] * (glow_color * 0.5 + 0.3))
    return img


def gaussian_blob(size):
    """Small round intensity kernel used to stamp one dot."""
    r = np.arange(size) - (size - 1) / 2.0
    d2 = r[:, None] ** 2 + r[None, :] ** 2
    sigma = max(size / 3.5, 0.6)
    return np.exp(-d2 / (2 * sigma ** 2))


def stamp(img, x, y, kernel, color):
    """Additively blend a colored kernel onto the image at (x, y)."""
    h, w = img.shape[:2]
    k = kernel.shape[0]
    x0, y0 = int(round(x)) - k // 2, int(round(y)) - k // 2
    ix0, iy0 = max(x0, 0), max(y0, 0)
    ix1, iy1 = min(x0 + k, w), min(y0 + k, h)
    if ix0 >= ix1 or iy0 >= iy1:
        return
    sub = kernel[iy0 - y0:iy1 - y0, ix0 - x0:ix1 - x0]
    img[iy0:iy1, ix0:ix1] += sub[..., None] * color


def sample_particles(rng, args, max_r):
    """Return per-particle radius and angle according to the chosen mode."""
    n = args.dots
    # Radius: density falls off with distance so the field thins out at the
    # edges. falloff=1 is uniform area coverage; higher concentrates inward.
    u = rng.random(n)
    r = max_r * u ** (args.falloff / 2.0)

    if args.rays > 0:
        # Snap angles onto discrete rays with jitter -> visible spokes.
        ray = rng.integers(0, args.rays, n)
        theta = ray * (2 * np.pi / args.rays) + rng.normal(0, args.ray_jitter, n)
    else:
        theta = rng.uniform(0, 2 * np.pi, n)

    if args.mode == "spiral":
        theta += args.swirl * (r / max_r)
    elif args.mode == "rings":
        ring = np.round(r / max_r * args.rings)
        r = (ring / args.rings) * max_r + rng.normal(0, max_r * 0.008, n)
    elif args.mode == "uniform":
        r = max_r * np.sqrt(rng.random(n))

    return r, theta


def render(args):
    rng = np.random.default_rng(args.seed)
    w, h = args.width, args.height
    cx, cy = args.center_x * w, args.center_y * h

    img = make_background(w, h, cx, cy, args.bg_color, args.glow_color,
                          args.glow_strength, args.glow_width * w,
                          args.glow_softness)

    max_r = np.hypot(max(cx, w - cx), max(cy, h - cy))
    r, theta = sample_particles(rng, args, max_r)
    xs = cx + r * np.cos(theta)
    ys = cy + r * np.sin(theta)

    # Per-dot appearance: size, brightness, and a white..tint color mix.
    sizes = rng.integers(args.dot_min, args.dot_max + 1, args.dots)
    bright = rng.uniform(0.35, 1.0, args.dots) ** 2
    mix = rng.uniform(0, 1, args.dots)[:, None]
    colors = (1 - mix) * np.ones(3) + mix * args.dot_color

    kernels = {s: gaussian_blob(s) for s in range(args.dot_min, args.dot_max + 1)}

    streak_px = args.streak * (r / max_r)  # outer dots streak more
    ux, uy = np.cos(theta), np.sin(theta)  # outward direction

    for i in range(args.dots):
        c = colors[i] * bright[i]
        kern = kernels[sizes[i]]
        steps = max(1, int(streak_px[i] / 2))
        for s in range(steps):
            t = s / max(steps - 1, 1)
            fade = (1 - 0.8 * t)
            stamp(img, xs[i] + ux[i] * streak_px[i] * t,
                  ys[i] + uy[i] * streak_px[i] * t, kern, c * fade)

    # A dusting of faint single-pixel stars everywhere.
    n_faint = args.dots * 2
    fx = rng.integers(0, w, n_faint)
    fy = rng.integers(0, h, n_faint)
    fb = rng.uniform(0.05, 0.35, n_faint)
    img[fy, fx] += fb[:, None] * (0.7 + 0.3 * args.dot_color)

    out = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(out).save(args.output)
    print(f"saved {args.output} ({w}x{h}, mode={args.mode}, dots={args.dots})")


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--width", type=int, default=1600)
    p.add_argument("--height", type=int, default=1000)
    p.add_argument("--output", default="radiation_pattern_out.png")
    p.add_argument("--seed", type=int, default=None, help="random seed (default: random)")

    p.add_argument("--mode", choices=["radial", "spiral", "rings", "burst", "uniform"],
                   default="radial", help="overall pattern layout")
    p.add_argument("--dots", type=int, default=4000, help="number of bright dots")
    p.add_argument("--falloff", type=float, default=0.9,
                   help="radial density falloff; 1=even coverage, >1 denser at center")
    p.add_argument("--streak", type=float, default=14.0,
                   help="max outward streak length in px (0 = plain dots)")
    p.add_argument("--rays", type=int, default=0,
                   help="snap dots onto this many spokes (0 = continuous)")
    p.add_argument("--ray-jitter", type=float, default=0.02,
                   help="angular jitter (radians) when using --rays")
    p.add_argument("--swirl", type=float, default=4.0,
                   help="spiral twist amount (spiral mode)")
    p.add_argument("--rings", type=int, default=10, help="ring count (rings mode)")

    p.add_argument("--center-x", type=float, default=0.5, help="center x as 0-1 fraction")
    p.add_argument("--center-y", type=float, default=0.45, help="center y as 0-1 fraction")
    p.add_argument("--dot-min", type=int, default=2, help="smallest dot size (px)")
    p.add_argument("--dot-max", type=int, default=5, help="largest dot size (px)")

    p.add_argument("--bg-color", type=parse_color, default="5,6,14",
                   help="background R,G,B")
    p.add_argument("--dot-color", type=parse_color, default="170,220,255",
                   help="dot tint R,G,B (dots blend between white and this)")
    p.add_argument("--glow-color", type=parse_color, default="30,70,220",
                   help="central glow R,G,B")
    p.add_argument("--glow-strength", type=float, default=1.0,
                   help="glow brightness, 0 disables the glow column")
    p.add_argument("--glow-width", type=float, default=0.10,
                   help="glow column half-width as fraction of image width")
    p.add_argument("--glow-softness", type=float, default=2.5,
                   help="how much the glow widens toward top/bottom")

    args = p.parse_args()

    if args.mode == "burst" and args.rays == 0:
        args.rays = 36
    if args.mode == "burst":
        args.streak = max(args.streak, 24.0)
    if args.mode == "uniform":
        args.streak = 0.0

    render(args)


if __name__ == "__main__":
    main()
