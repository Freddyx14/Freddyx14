"""Draw the GitHub cover entirely in code, as one animated SVG.

No screenshots and no embedded photograph: every mark is geometry. The type is
real Montserrat, Inter and JetBrains Mono, converted from font outlines into SVG
paths, because a browser rendering SVG-as-image cannot load a webfont. HarfBuzz
does the shaping, so kerning and the accented N are correct rather than guessed.

Motion is SMIL, not CSS. CSS @keyframes do not run in the context GitHub renders
the cover in; SMIL does, and GitHub serves the file byte for byte unmodified.

What moves, and why it is safe:
  contours   draw themselves once, then hold. Pure texture, so nothing is lost
             if an environment freezes animation.
  name       always filled. A gold outline traces across it behind a moving clip
             that starts off-canvas, so at rest the shimmer is simply absent.
  rule       a highlight slides along a bar that is fully drawn at rest.
  ticker     types and retypes the marquee words. Decorative, never content.
  flag       waves continuously from a mid-wave resting position.
  glint      a band of light crosses the banner, invisible at rest.
Nothing that carries meaning is ever hidden at time zero.

Run: uv run --with uharfbuzz --with fonttools python codegen.py
"""
import math, pathlib, urllib.request
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform

HERE = pathlib.Path(__file__).parent
OUT = HERE.parent / "assets" / "banner.svg"
W, H = 1600, 500

INK_DEEP = "#060606"
SCARLET = "#8B1A1A"
SCARLET_BRIGHT = "#A82323"
IVORY = "#F5F0EB"
IVORY_DIM = "#CFC8BF"
MUTED = "#A39D94"
GOLD = "#C9A84C"
GOLD_SOFT = "#D9BE6E"
FLAG_RED = "#A81E28"
FLAG_RED_DARK = "#6E1119"
FLAG_WHITE = "#F2EDE7"
FLAG_WHITE_DARK = "#9E9890"


class Face:
    """A font, able to shape a string and hand back its glyph outlines."""

    def __init__(self, path):
        self.hb = hb.Font(hb.Face(hb.Blob.from_file_path(str(path))))
        self.tt = TTFont(path)
        self.upem = self.tt["head"].unitsPerEm
        self.glyphs = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()

    def shape(self, text, size, tracking=0.0):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb, buf)
        s = size / self.upem
        out, x = [], 0.0
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            out.append((self.order[info.codepoint], x + pos.x_offset * s, pos.y_offset * s))
            x += pos.x_advance * s + tracking
        return out, x

    def outline(self, gname, x, baseline, size):
        pen = SVGPathPen(self.glyphs)
        s = size / self.upem
        self.glyphs[gname].draw(TransformPen(pen, Transform(s, 0, 0, -s, x, baseline)))
        return pen.getCommands()

    def letters(self, text, x, baseline, size, tracking=0.0):
        """One path per glyph, so letters can be animated independently."""
        placed, width = self.shape(text, size, tracking)
        out = [(self.outline(g, x + gx, baseline - gy, size)) for g, gx, gy in placed]
        return [d for d in out if d], width

    def run(self, text, x, baseline, size, tracking=0.0):
        """All glyphs merged into a single path."""
        ds, width = self.letters(text, x, baseline, size, tracking)
        return " ".join(ds), width


# Google ships these as variable fonts only, so each weight is instanced at
# build time. They are fetched rather than committed: the repo stays light and
# the build stays reproducible from a clean checkout.
GF = "https://raw.githubusercontent.com/google/fonts/main/ofl"
SOURCES = {"Montserrat": f"{GF}/montserrat/Montserrat%5Bwght%5D.ttf",
           "Inter": f"{GF}/inter/Inter%5Bopsz,wght%5D.ttf",
           "JetBrainsMono": f"{GF}/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf"}
WEIGHTS = [("Montserrat", 900), ("Inter", 500), ("Inter", 600),
           ("JetBrainsMono", 400), ("JetBrainsMono", 600)]


def fonts():
    d = HERE / "fonts"
    d.mkdir(exist_ok=True)
    for family, url in SOURCES.items():
        var = d / f"{family}-var.ttf"
        if not var.exists():
            print(f"fetching {family}")
            urllib.request.urlretrieve(url, var)
    out = {}
    for family, weight in WEIGHTS:
        cut = d / f"{family}-{weight}.ttf"
        if not cut.exists():
            f = TTFont(d / f"{family}-var.ttf")
            instancer.instantiateVariableFont(f, {"wght": weight}, inplace=True)
            f.save(cut)
        out[f"{family}-{weight}"] = Face(cut)
    return out


F = fonts()

# --------------------------------------------------------------- topography
# Placed in the negative space: one under the type at bottom left, one in
# the gap between the type and the flag. Behind either of them the texture
# would simply be invisible.
CENTRES = [(250, 512, 1.0), (905, 108, 0.80)]
HARMONICS = [(3, 0.085, 0.7), (5, 0.05, 2.1), (7, 0.028, 4.4), (11, 0.016, 1.2)]


def contours():
    for cx, cy, scale in CENTRES:
        for n in range(26):
            op = (0.30 - n * 0.009) * 0.82
            if op <= 0.013:
                continue
            pts = []
            r, seed = (34 + n * 27) * scale, n * 0.19
            for i in range(122):
                t = i / 121 * 2 * math.pi
                k = 1.0 + sum(a * math.sin(f * t + p + seed) for f, a, p in HARMONICS)
                pts.append((cx + math.cos(t) * r * k, cy + math.sin(t) * r * k * 0.78))
            length = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
            d = "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z"
            yield d, op, length, n


def topo():
    parts = []
    for d, op, length, n in contours():
        begin = min(n * 0.07, 1.7)
        parts.append(
            f'<path d="{d}" stroke-opacity="{op:.3f}" stroke-dasharray="{length:.0f}" '
            f'stroke-dashoffset="{length:.0f}">'
            f'<animate attributeName="stroke-dashoffset" values="{length:.0f};0" '
            f'dur="2.4s" begin="{begin:.2f}s" fill="freeze"/>'
            f'<animate attributeName="stroke-opacity" values="{op:.3f};{min(op*3,.5):.3f};{op:.3f}" '
            f'dur="6s" begin="{4 + n*0.1:.2f}s" repeatCount="indefinite"/></path>')
    return ('<g fill="none" stroke="#F5F0EB" stroke-width="1">' + "".join(parts) +
            '<animateTransform attributeName="transform" type="translate" '
            'values="0 0;14 -8;0 0;-12 7;0 0" dur="26s" repeatCount="indefinite"/></g>')


# --------------------------------------------------------------------- flag
X0, FW, Y0, FH = 1118, 392, 148, 244
WAVE_A, LAMBDA, PHASES = 15.0, FW / 1.25, 5


def _edge(xa, xb, phase, amp_scale, samples=34):
    """Points along one horizontal edge of the cloth at a given wave phase."""
    pts = []
    for i in range(samples + 1):
        x = xa + (xb - xa) * i / samples
        y = WAVE_A * amp_scale * math.sin(2 * math.pi * (x - X0) / LAMBDA + phase)
        pts.append((x, y))
    return pts


def _band(xa, xb, phase):
    """A closed path for one colour band: wavy top, wavy bottom, straight sides.
    The bottom edge runs a slightly smaller amplitude, which is what makes cloth
    read as cloth instead of as a ribbon."""
    top = _edge(xa, xb, phase, 1.0)
    bot = _edge(xa, xb, phase, 0.82)
    d = "M" + f"{top[0][0]:.1f},{Y0 + top[0][1]:.1f}"
    d += "".join(f"L{x:.1f},{Y0 + y:.1f}" for x, y in top[1:])
    d += "".join(f"L{x:.1f},{Y0 + FH + y:.1f}" for x, y in reversed(bot))
    return d + "Z"


def flag():
    thirds = [(X0, X0 + FW / 3, FLAG_RED),
              (X0 + FW / 3, X0 + 2 * FW / 3, FLAG_WHITE),
              (X0 + 2 * FW / 3, X0 + FW, FLAG_RED)]
    phases = [2 * math.pi * i / (PHASES - 1) for i in range(PHASES)]
    parts = []
    for xa, xb, colour in thirds:
        vals = ";".join(_band(xa, xb, ph) for ph in phases)
        parts.append(f'<path d="{_band(xa, xb, 0)}" fill="{colour}">'
                     f'<animate attributeName="d" values="{vals}" dur="4.6s" '
                     f'repeatCount="indefinite"/></path>')
    # One overlay across the whole cloth carries the folds: a repeating gradient
    # that slides along, so the shading travels with the wave instead of being
    # baked into each band.
    vals = ";".join(_band(X0, X0 + FW, ph) for ph in phases)
    parts.append(f'<path d="{_band(X0, X0 + FW, 0)}" fill="url(#fold)">'
                 f'<animate attributeName="d" values="{vals}" dur="4.6s" '
                 f'repeatCount="indefinite"/></path>')
    return (f'<ellipse cx="{X0 + FW/2}" cy="{Y0 + FH/2}" rx="{FW*0.78:.0f}" '
            f'ry="{FH*0.92:.0f}" fill="url(#flagGlow)"/>{"".join(parts)}')


# --------------------------------------------------------------------- type
def build():
    defs, body = [], []

    # ---- eyebrow
    eb, _ = F["JetBrainsMono-600"].run("BUILDER · PILPICHACA, PERU → THE WORLD", 84, 58, 14, 3.4)
    body.append(f'<path d="{eb}" fill="{GOLD}"/>')

    # ---- name: filled always, gold outline traced by a moving clip
    fills, strokes = [], []
    for text, baseline in (("FREDDY", 158), ("ÑAÑEZ", 246)):
        ds, _ = F["Montserrat-900"].letters(text, 84, baseline, 92, -2.8)
        for d in ds:
            fills.append(f'<path d="{d}" fill="{IVORY}"/>')
            strokes.append(f'<path d="{d}" fill="none" stroke="{GOLD_SOFT}" stroke-width="1.2"/>')
    defs.append(
        '<clipPath id="shine"><rect x="-340" y="0" width="190" height="500">'
        '<animate attributeName="x" values="-340;-340;1700;1700" keyTimes="0;.16;.62;1" '
        'dur="7.5s" repeatCount="indefinite"/></rect></clipPath>')
    body.append("".join(fills))
    body.append(f'<g clip-path="url(#shine)">{"".join(strokes)}</g>')

    # ---- rule with a highlight sliding along it
    body.append(f'<rect x="84" y="282" width="78" height="4" rx="2" fill="{SCARLET_BRIGHT}"/>')
    body.append(
        f'<rect x="84" y="282" width="20" height="4" rx="2" fill="{GOLD_SOFT}" opacity="0">'
        f'<animate attributeName="x" values="84;84;142;142" keyTimes="0;.18;.5;1" dur="7.5s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="0;0;.95;.95;0;0" keyTimes="0;.18;.24;.46;.5;1" dur="7.5s" repeatCount="indefinite"/></rect>')

    # ---- lead, two weights on one line
    x = 84.0
    for text, font, fill in (("I build startups and ", "Inter-500", IVORY_DIM),
                             ("the software behind them.", "Inter-600", IVORY)):
        d, w = F[font].run(text, x, 330, 25)
        body.append(f'<path d="{d}" fill="{fill}"/>')
        x += w
    d, _ = F["Inter-500"].run("The strategy, the product, and the code.", 84, 362, 25)
    body.append(f'<path d="{d}" fill="{IVORY_DIM}"/>')

    # ---- ticker: types the marquee words, then retypes them
    prompt, pw = F["JetBrainsMono-600"].run("> ", 84, 410, 15, 1.2)
    body.append(f'<path d="{prompt}" fill="{SCARLET_BRIGHT}"/>')
    words = ["Tech", "Entrepreneurship", "Startups"]
    cycle, n = 13.5, len(words)
    for i, word in enumerate(words):
        d, ww = F["JetBrainsMono-400"].run(word, 84 + pw, 410, 15, 1.2)
        a = i / n                       # slot start, as a fraction of the cycle
        reveal, hold = a + 0.075, a + 0.28
        kt = f"0;{a:.3f};{reveal:.3f};{hold:.3f};{hold + 0.012:.3f};1"
        x0, x1 = 84 + pw, 84 + pw + ww + 2
        defs.append(
            f'<clipPath id="tw{i}"><rect x="{x0:.1f}" y="392" width="0" height="26">'
            f'<animate attributeName="width" values="0;0;{ww + 2:.1f};{ww + 2:.1f};0;0" '
            f'keyTimes="{kt}" dur="{cycle}s" repeatCount="indefinite"/></rect></clipPath>')
        body.append(
            f'<g opacity="0"><animate attributeName="opacity" values="0;1;1;1;0;0" '
            f'keyTimes="{kt}" dur="{cycle}s" repeatCount="indefinite"/>'
            f'<g clip-path="url(#tw{i})"><path d="{d}" fill="{IVORY_DIM}"/></g>'
            f'<rect x="{x0:.1f}" y="396" width="8" height="17" fill="{GOLD}">'
            f'<animate attributeName="x" values="{x0:.1f};{x0:.1f};{x1:.1f};{x1:.1f};{x0:.1f};{x0:.1f}" '
            f'keyTimes="{kt}" dur="{cycle}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;.45;.5;.95;1" '
            f'dur="1.1s" repeatCount="indefinite"/></rect></g>')

    # ---- credentials, gold dots between the segments
    x = 84.0
    segs = ["Stanford d.school Fellow", "U.S. State Department Scholar",
            "START Hack, St. Gallen", "Founder of Loopmind"]
    for i, seg in enumerate(segs):
        d, w = F["JetBrainsMono-400"].run(seg, x, 462, 13.5, 0.9)
        body.append(f'<path d="{d}" fill="{MUTED}"/>')
        x += w
        if i < len(segs) - 1:
            body.append(
                f'<circle cx="{x + 9:.1f}" cy="458" r="2.1" fill="{GOLD}" opacity=".85">'
                f'<animate attributeName="opacity" values=".85;.3;.85" dur="3.2s" '
                f'begin="{i * 0.5:.1f}s" repeatCount="indefinite"/></circle>')
            x += 20

    return defs, body


def main():
    defs, body = build()
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img">
<title>Freddy Nanez. Builder. From Pilpichaca, Peru, to the world.</title>
<defs>
  <radialGradient id="gRed" cx="76%" cy="108%" r="66%">
    <stop offset="0%" stop-color="{SCARLET}" stop-opacity=".62"/>
    <stop offset="100%" stop-color="{SCARLET}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="gGold" cx="10%" cy="-14%" r="58%">
    <stop offset="0%" stop-color="{GOLD}" stop-opacity=".14"/>
    <stop offset="100%" stop-color="{GOLD}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="flagGlow" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="{SCARLET_BRIGHT}" stop-opacity=".34"/>
    <stop offset="100%" stop-color="{SCARLET_BRIGHT}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="vig" cx="40%" cy="46%" r="74%">
    <stop offset="42%" stop-color="#000" stop-opacity="0"/>
    <stop offset="100%" stop-color="#000" stop-opacity=".58"/>
  </radialGradient>
  <linearGradient id="spine" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#5E1212"/><stop offset="45%" stop-color="{SCARLET_BRIGHT}"/>
    <stop offset="100%" stop-color="#5E1212"/>
  </linearGradient>
  <linearGradient id="baseline" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="{SCARLET}"/>
    <stop offset="42%" stop-color="{GOLD}" stop-opacity=".55"/>
    <stop offset="78%" stop-color="{GOLD}" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="fold" gradientUnits="userSpaceOnUse" x1="{X0}" y1="0" x2="{X0 + LAMBDA/2:.0f}" y2="0" spreadMethod="repeat">
    <stop offset="0%" stop-color="#000" stop-opacity=".30"/>
    <stop offset="34%" stop-color="#000" stop-opacity="0"/>
    <stop offset="62%" stop-color="#fff" stop-opacity=".10"/>
    <stop offset="100%" stop-color="#000" stop-opacity=".30"/>
    <animateTransform attributeName="gradientTransform" type="translate" values="0 0;{LAMBDA/2:.0f} 0" dur="4.6s" repeatCount="indefinite"/>
  </linearGradient>
  <linearGradient id="sw" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="{IVORY}" stop-opacity="0"/>
    <stop offset="44%" stop-color="{IVORY}" stop-opacity=".30"/>
    <stop offset="58%" stop-color="{GOLD}" stop-opacity=".26"/>
    <stop offset="100%" stop-color="{GOLD}" stop-opacity="0"/>
  </linearGradient>
  <filter id="grain" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="3" stitchTiles="stitch"/>
    <feColorMatrix type="saturate" values="0"/>
  </filter>
  {''.join(defs)}
</defs>

<rect width="{W}" height="{H}" fill="{INK_DEEP}"/>
<rect width="{W}" height="{H}" fill="url(#gRed)">
  <animate attributeName="opacity" values="1;.82;1" dur="11s" repeatCount="indefinite"/>
</rect>
<rect width="{W}" height="{H}" fill="url(#gGold)"/>
{topo()}
<rect width="{W}" height="{H}" fill="url(#vig)"/>
<rect width="{W}" height="{H}" filter="url(#grain)" opacity=".05"/>
{flag()}
{''.join(body)}
<rect x="0" y="0" width="6" height="{H}" fill="url(#spine)"/>
<rect x="0" y="{H-2}" width="{W}" height="2" fill="url(#baseline)"/>
<g opacity="0">
  <rect x="-300" y="-150" width="300" height="820" fill="url(#sw)" transform="skewX(-14)"/>
  <animateTransform attributeName="transform" type="translate" values="-100 0;-100 0;2100 0;2100 0" keyTimes="0;.14;.44;1" dur="7.5s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;.14;.2;.38;.44;1" dur="7.5s" repeatCount="indefinite"/>
</g>
</svg>'''
    OUT.write_text(svg)
    print(f"banner.svg  {len(svg)/1024:.0f} KB   animaciones: {svg.count('<animate')}")


if __name__ == "__main__":
    main()
