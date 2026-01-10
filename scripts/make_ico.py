#!/usr/bin/env python3
from pathlib import Path
import sys

try:
    from PIL import Image
except ImportError:
    print("Pillow is required. Install with: python -m pip install pillow", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
src_png = ROOT / "attachments" / "vidoedit.png"
out_ico = ROOT / "attachments" / "vidoedit.ico"

if not src_png.exists():
    print(f"Error: source image not found: {src_png}", file=sys.stderr)
    sys.exit(1)

img = Image.open(src_png).convert("RGBA")
# Common Windows icon sizes
sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

# Resize for all sizes
icons = [img.resize(s, Image.LANCZOS) for s in sizes]

icons[0].save(out_ico, format="ICO", sizes=sizes)
print(f"✓ Wrote {out_ico}")
