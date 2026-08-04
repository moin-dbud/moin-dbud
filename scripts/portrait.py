#!/usr/bin/env python3
"""
Turn a headshot into an animated, typing ASCII-portrait SVG.

Usage:
    python3 scripts/portrait.py photo.jpg portrait.svg

Photo requirements (the pipeline can't fix a bad input):
  - 45-degree side light, one side of the face in shadow
  - tight crop: chin to just above the hair
  - 1200px+ on the short side
  - plain background, subject not wearing black against a dark wall
  - slight angle, not dead-on
"""
import sys
import numpy as np
import cv2
from PIL import Image
from rembg import remove

RAMP = " .`:-=+*cs#%@"        # 13 levels
COLS = 90
CHAR_W = 7.74                  # em advance baked into the grid — see README Part 1 "trap"
FONT_SIZE = 12.9
STAGGER = 0.09                 # seconds between each row starting to type


def load_and_cutout(path):
    img = Image.open(path).convert("RGB")
    cut = remove(img)                       # forces background to transparent/white
    bg = Image.new("RGB", cut.size, (255, 255, 255))
    bg.paste(cut, mask=cut.split()[3] if cut.mode == "RGBA" else None)
    return np.array(bg)


def enhance(arr):
    # bilateral filter: smooths skin, keeps edges
    arr = cv2.bilateralFilter(arr, d=9, sigmaColor=75, sigmaSpace=75)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    # CLAHE: local contrast, so a flatly-lit face doesn't collapse to one tone
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    # darkening curve — the fix that keeps glasses/brows/lips from washing out
    normalized = gray.astype(np.float64) / 255.0
    darkened = np.power(normalized, 1.7) * 255.0
    return darkened.astype(np.uint8)


def to_ascii_rows(gray):
    h, w = gray.shape
    rows = max(1, round(COLS * (h / w) * 0.48))
    resized = cv2.resize(gray, (COLS, rows), interpolation=cv2.INTER_AREA)
    lines = []
    n = len(RAMP)
    for r in range(rows):
        line = []
        for c in range(COLS):
            v = resized[r, c]
            idx = min(n - 1, int((255 - v) / 256 * n))  # bright -> low index (space)
            line.append(RAMP[idx])
        lines.append("".join(line))
    return lines


def build_svg(lines):
    row_h = FONT_SIZE * 1.05
    width = COLS * CHAR_W + 10
    height = len(lines) * row_h + 10

    defs = []
    body = []
    for i, line in enumerate(lines):
        y = (i + 1) * row_h
        clip_id = f"clip{i}"
        row_w = len(line) * CHAR_W
        begin = round(i * STAGGER, 2)
        # width animates 0 -> row_w, freezes at the end so it types once and stops
        defs.append(
            f'<clipPath id="{clip_id}">'
            f'<rect x="0" y="{y - FONT_SIZE}" width="0" height="{row_h}">'
            f'<animate attributeName="width" from="0" to="{row_w}" '
            f'dur="0.5s" begin="{begin}s" fill="freeze"/>'
            f'</rect></clipPath>'
        )
        escaped = (
            line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        body.append(
            f'<text x="0" y="{y}" font-family="\'ramp\', monospace" '
            f'font-size="{FONT_SIZE}" fill="currentColor" xml:space="preserve" '
            f'clip-path="url(#{clip_id})">{escaped}</text>'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.1f} {height:.1f}">'
        f'<defs>{"".join(defs)}</defs>'
        f'{"".join(body)}'
        f'</svg>'
    )


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    src, out = sys.argv[1], sys.argv[2]
    arr = load_and_cutout(src)
    gray = enhance(arr)
    lines = to_ascii_rows(gray)
    svg = build_svg(lines)
    with open(out, "w") as f:
        f.write(svg)
    print(f"wrote {out}: {len(lines)} rows x {COLS} cols, "
          f"typing time ~{len(lines) * STAGGER + 0.5:.1f}s")


if __name__ == "__main__":
    main()