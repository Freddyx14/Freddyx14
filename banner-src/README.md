# Banner source

The cover image is not a template. It is rendered from `banner.html` at 1600x500
logical pixels with a 2x device scale factor, then downscaled to 2000x625.

- `topo.py` generates `topo.svg`, the highland contour texture. Nested closed
  loops perturbed by fixed sine harmonics, two offset centres so the field reads
  as a ridge instead of a bullseye.
- `freddy-cut.png` is the alpha-trimmed cutout. Original lives in the portfolio
  repo at `public/photos/hero/freddy-front-master.png`.
- Colors and type follow the portfolio brand tokens: `#0A0A0A` ink,
  `#8B1A1A` scarlet, `#C9A84C` gold, `#F5F0EB` ivory, Montserrat + Inter +
  JetBrains Mono.

To rebuild:

```sh
# banner.html already carries topo.svg inlined. Regenerate it only if you want
# a different terrain: python3 topo.py, then paste topo.svg into the .topo div.
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --hide-scrollbars --allow-file-access-from-files \
  --force-device-scale-factor=2 --window-size=1600,500 --virtual-time-budget=8000 \
  --screenshot=banner-2x.png "file://$PWD/banner.html"
magick banner-2x.png -resize 2000x625 -strip ../assets/banner.png
```
