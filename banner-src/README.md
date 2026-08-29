# Banner source

`cover.svg` is drawn entirely in code. No screenshot, no embedded photograph:
every mark in it is geometry.

```sh
uv run --with uharfbuzz --with fonttools python codegen.py
```

That writes `../assets/cover.svg`. Fonts are fetched and instanced on first run.

## Why it is built this way

GitHub shows a profile cover through an `<img>`, and a browser renders
SVG-as-image in a restricted mode. Two consequences drove every decision here,
both found by testing rather than assumed:

- **No webfonts.** A font cannot load in that mode, so Montserrat, Inter and
  JetBrains Mono are converted from outlines into SVG paths. HarfBuzz shapes the
  text first, so kerning and the tilde on the N are correct.
- **No CSS animation.** `@keyframes` do not run there, and an element carrying a
  frozen animation renders at its 0% keyframe, which turns an animated cover
  blank. SMIL does run. GitHub serves the file byte for byte unmodified, so what
  ships is what renders.

## What moves

| Element | Motion | Safe when frozen |
|---|---|---|
| Contours | draw themselves once, then ripple | texture only, nothing lost |
| Name | gold outline traced by a moving clip | fill is always present |
| Rule | highlight slides along it | bar is fully drawn at rest |
| Ticker | types and retypes the marquee words | decorative, never content |
| Flag | wave runs through the cloth, folds slide with it | rests mid-wave |
| Glint | band of light crosses the banner | invisible at rest |

Nothing carrying meaning is hidden at time zero. Verified by rendering the SVG
with animation frozen: the name, the line, the credentials and the flag are all
still there.

Colours and type follow the portfolio brand tokens: `#0A0A0A` ink, `#8B1A1A`
scarlet, `#C9A84C` gold, `#F5F0EB` ivory.
