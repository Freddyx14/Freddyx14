"""Build the animated GitHub cover.

Two constraints shape every decision here, and both were found by testing rather
than assumed:

1. GitHub shows the cover through an <img>, and a browser renders SVG-as-image in
   a restricted mode. CSS @keyframes DO NOT RUN there, and an element carrying a
   frozen animation renders at its 0% keyframe, so a CSS-animated banner shows up
   blank. SMIL (<animate>) does run. That is why there is no <style> block below.
   SVG <mask> does not work in that mode either, so the cutout ships as a plain
   alpha PNG and its glow is a native gradient.

2. External fonts cannot load in that mode, so Montserrat is unavailable from
   inside the SVG. The type is therefore rendered in Chrome, where the real font
   is present, and shipped as image layers.

Safe by construction: NOTHING here is hidden at time zero. Entrance animations
were tried and rejected, because any environment that freezes animation at frame
zero renders their hidden state, and a blank cover is a far worse outcome than a
still one. Every animation is additive: it departs from the finished state and
returns to it, so the banner is complete whether or not it ever animates. The
only element that starts invisible is the light sweep, whose resting state is
invisible anyway.

Layers, back to front:
  bg      JPEG    glow, grain, spine, baseline, plus the cutout's soft glow and
                  ground shadow, which cost nothing on an opaque layer
  topo    vector  highland contours, drawn in with stroke-dashoffset
  vignette vector sits above topo so the contours fade at the corners
  photo   PNG8    the cutout alone
  text    PNG8    eyebrow, name, rule, lead
  creds   PNG8    the credential row
  sweep   vector  a slow band of light crossing the banner
"""
import base64, math, pathlib, subprocess

HERE = pathlib.Path(__file__).parent
OUT = HERE.parent / "assets"
BUILD = HERE / ".layers"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
W, H = 1600, 500
DUR = "4s"

CENTRES = [(430, 470, 1.0), (1180, 120, 0.72)]
HARMONICS = [(3, 0.085, 0.7), (5, 0.05, 2.1), (7, 0.028, 4.4), (11, 0.016, 1.2)]
EASE = ".22 .61 .36 1"
HOLD = "0 0 1 1"


def ring(cx, cy, r, squash, seed, steps=121):
    """Return (path data, path length). The length is measured here rather than
    left to pathLength, which is not worth trusting in SVG-as-image mode."""
    pts = []
    for i in range(steps + 1):
        t = i / steps * 2 * math.pi
        k = 1.0
        for freq, amp, phase in HARMONICS:
            k += amp * math.sin(freq * t + phase + seed)
        pts.append((cx + math.cos(t) * r * k, cy + math.sin(t) * r * k * squash))
    length = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
    return "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z", length


def contours():
    for cx, cy, scale in CENTRES:
        for n in range(26):
            op = 0.30 - n * 0.009
            if op <= 0.02:
                continue
            d, length = ring(cx, cy, (34 + n * 27) * scale, 0.78, n * 0.19)
            yield d, op, length, n


def shot(layer, path):
    subprocess.run([
        CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--allow-file-access-from-files", "--default-background-color=00000000",
        "--force-device-scale-factor=2", f"--window-size={W},{H}",
        "--virtual-time-budget=9000", f"--screenshot={path}",
        f"file://{HERE / 'banner.html'}#{layer}",
    ], capture_output=True)
    if not pathlib.Path(path).exists():
        raise SystemExit(f"chrome produced no screenshot for layer {layer}")


def uri(path, mime):
    return f"data:{mime};base64," + base64.b64encode(pathlib.Path(path).read_bytes()).decode()


def fade_in(hold, done):
    """Opacity 0 until `hold` of the timeline, faded in by `done`, then held."""
    return (f'<animate attributeName="opacity" values="0;0;1;1" '
            f'keyTimes="0;{hold};{done};1" dur="{DUR}" fill="freeze" '
            f'calcMode="spline" keySplines="{HOLD};{EASE};{HOLD}"/>')


def rise(hold, done, dy):
    return (f'<animateTransform attributeName="transform" type="translate" '
            f'values="0 {dy};0 {dy};0 0;0 0" keyTimes="0;{hold};{done};1" '
            f'dur="{DUR}" fill="freeze" calcMode="spline" '
            f'keySplines="{HOLD};{EASE};{HOLD}"/>')


def main():
    BUILD.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    for layer in ("bg", "photo", "text", "creds", "full"):
        shot(layer, BUILD / f"{layer}.png")

    subprocess.run(["magick", BUILD / "bg.png", "-quality", "88", "-strip",
                    BUILD / "bg.jpg"], check=True)

    # Each remaining layer is mostly empty. Crop to its real box, place it back
    # at that offset, and quantise: a 255-colour palette is visually identical
    # here and roughly a quarter of the truecolour weight.
    boxes = {}
    for layer in ("photo", "text", "creds"):
        geom = subprocess.run(["magick", BUILD / f"{layer}.png", "-format", "%@",
                               "info:"], capture_output=True, text=True,
                              check=True).stdout.strip()
        wh, x, y = geom.replace("+", " +").split()
        bw, bh = (int(v) for v in wh.split("x"))
        boxes[layer] = (int(x) / 2, int(y) / 2, bw / 2, bh / 2)  # renders are 2x
        subprocess.run(["magick", BUILD / f"{layer}.png", "-trim", "+repage",
                        "-strip", "-colors", "255",
                        f"PNG8:{BUILD / (layer + '.opt.png')}"], check=True)

    # The contours are drawn at rest and stay drawn. A brightness ripple travels
    # outward through them, so the terrain reads as alive without any ring ever
    # being invisible.
    # 0.66 mirrors the opacity the HTML original applied over the whole contour
    # group, so the SVG matches the approved render instead of shouting louder.
    rings = "".join(
        f'<path d="{d}" stroke-opacity="{op * .66:.3f}">'
        f'<animate attributeName="stroke-opacity" '
        f'values="{op * .66:.3f};{min(op * 1.9, 0.42):.3f};{op * .66:.3f}" '
        f'dur="7s" begin="{n * 0.14:.2f}s" repeatCount="indefinite"/></path>'
        for d, op, length, n in contours())

    def place(layer):
        x, y, w, h = boxes[layer]
        return f'x="{x}" y="{y}" width="{w}" height="{h}"'

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img">
<title>Freddy Nanez. Builder. From Pilpichaca, Peru, to the world.</title>
<defs>
  <radialGradient id="vig" cx="42%" cy="46%" r="72%">
    <stop offset="40%" stop-color="#000" stop-opacity="0"/>
    <stop offset="100%" stop-color="#000" stop-opacity=".55"/>
  </radialGradient>
  <linearGradient id="sw" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="#F5F0EB" stop-opacity="0"/>
    <stop offset="45%" stop-color="#F5F0EB" stop-opacity=".16"/>
    <stop offset="55%" stop-color="#C9A84C" stop-opacity=".18"/>
    <stop offset="100%" stop-color="#C9A84C" stop-opacity="0"/>
  </linearGradient>
</defs>

<image href="{uri(BUILD / 'bg.jpg', 'image/jpeg')}" x="0" y="0" width="{W}" height="{H}" opacity="1">
  <animate attributeName="opacity" values="1;.92;1" dur="11s" repeatCount="indefinite"/>
</image>

<g fill="none" stroke="#F5F0EB" stroke-width="1">{rings}</g>

<rect x="0" y="0" width="{W}" height="{H}" fill="url(#vig)"/>

<image href="{uri(BUILD / 'photo.opt.png', 'image/png')}" {place('photo')}/>
<image href="{uri(BUILD / 'text.opt.png', 'image/png')}" {place('text')}/>
<image href="{uri(BUILD / 'creds.opt.png', 'image/png')}" {place('creds')}/>

<g opacity="0">
  <rect x="-260" y="-140" width="230" height="800" fill="url(#sw)" transform="skewX(-14)"/>
  <animateTransform attributeName="transform" type="translate" values="-760 0;2320 0" dur="9s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="0;.5;0;0" keyTimes="0;.07;.24;1" dur="9s" repeatCount="indefinite"/>
</g>
</svg>'''

    (OUT / "banner.svg").write_text(svg)
    subprocess.run(["magick", BUILD / "full.png", "-resize", "2000x625", "-strip",
                    "-define", "png:compression-level=9", OUT / "banner.png"], check=True)
    print(f"banner.svg  {len(svg)/1024:.0f} KB")


if __name__ == "__main__":
    main()
