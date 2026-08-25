"""Generate the highland topographic contour texture for the banner.

Nested closed loops perturbed by a few fixed sine harmonics, so every ring
reads as the next altitude line of the same terrain. Two centres, offset,
so the field feels like a ridge rather than a bullseye.
"""
import math

W, H = 1600, 500
CENTRES = [(430, 470, 1.0), (1180, 120, 0.72)]
HARMONICS = [(3, 0.085, 0.7), (5, 0.05, 2.1), (7, 0.028, 4.4), (11, 0.016, 1.2)]


def ring(cx, cy, r, squash, seed):
    pts = []
    for i in range(241):
        t = i / 240 * 2 * math.pi
        k = 1.0
        for freq, amp, phase in HARMONICS:
            k += amp * math.sin(freq * t + phase + seed)
        x = cx + math.cos(t) * r * k
        y = cy + math.sin(t) * r * k * squash
        pts.append(f"{x:.1f},{y:.1f}")
    return "M" + "L".join(pts) + "Z"


paths = []
for cx, cy, scale in CENTRES:
    for n in range(26):
        r = (34 + n * 27) * scale
        # outer rings fade out; inner rings sit brightest at the summit
        op = 0.30 - n * 0.009
        if op <= 0.02:
            continue
        paths.append(
            f'<path d="{ring(cx, cy, r, 0.78, n * 0.19)}" fill="none" '
            f'stroke="#F5F0EB" stroke-opacity="{op:.3f}" stroke-width="1"/>'
        )

svg = (
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}">' + "".join(paths) + "</svg>"
)
open("/Users/freddy/projects/2-projects-stand-by/github-profile/.build/topo.svg", "w").write(svg)
print("topo.svg", len(svg), "bytes")
