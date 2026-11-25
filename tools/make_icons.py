"""Draw the app icons (a bowl with a leaf on green) with Pillow.

    python tools/make_icons.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "icons"
GREEN, DARK, CREAM, LEAF = (43, 138, 62), (31, 102, 46), (250, 246, 236), (140, 214, 120)


def draw(size, padding=0.0, rounded=True):
    s = size * 4  # draw large, then shrink for smooth edges
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if rounded:
        d.rounded_rectangle([0, 0, s, s], radius=int(s * 0.22), fill=GREEN)
    else:
        d.rectangle([0, 0, s, s], fill=GREEN)
    k = 1 - 2 * padding  # shrink artwork into the maskable safe zone
    def p(x, y):
        return (s * (padding + x * k), s * (padding + y * k))
    # steam / leaf
    d.ellipse([*p(0.44, 0.16), *p(0.66, 0.46)], fill=LEAF)
    d.ellipse([*p(0.34, 0.24), *p(0.52, 0.48)], fill=(110, 190, 95))
    # bowl
    d.chord([*p(0.17, 0.20), *p(0.83, 0.80)], start=0, end=180, fill=CREAM)
    d.rectangle([*p(0.17, 0.49), *p(0.83, 0.52)], fill=CREAM)
    d.rounded_rectangle([*p(0.38, 0.79), *p(0.62, 0.84)], radius=int(s * 0.02), fill=CREAM)
    d.chord([*p(0.23, 0.26), *p(0.77, 0.74)], start=0, end=180, fill=DARK)
    d.chord([*p(0.23, 0.30), *p(0.77, 0.74)], start=0, end=180, fill=CREAM)
    return img.resize((size, size), Image.LANCZOS)


OUT.mkdir(exist_ok=True)
draw(192).save(OUT / "icon-192.png")
draw(512).save(OUT / "icon-512.png")
draw(512, padding=0.12, rounded=False).save(OUT / "icon-maskable-512.png")
draw(180, rounded=False).convert("RGB").save(OUT / "apple-touch-icon.png")  # iOS rounds it itself
(OUT / "icon.svg").write_text(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
    '<rect width="100" height="100" rx="22" fill="#2b8a3e"/>'
    '<ellipse cx="55" cy="31" rx="11" ry="15" fill="#8cd678"/>'
    '<ellipse cx="43" cy="36" rx="9" ry="12" fill="#6ebe5f"/>'
    '<path d="M17 50h66a33 30 0 0 1-66 0z" fill="#faf6ec"/>'
    '<rect x="38" y="79" width="24" height="5" rx="2" fill="#faf6ec"/>'
    '</svg>\n', encoding="utf-8")
print("Icons written to", OUT)
