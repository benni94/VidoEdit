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

# Windows icon sizes - including larger sizes for high DPI displays
# ICO format supports up to 256x256
sizes = [(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (96, 96), (128, 128), (256, 256)]

# Create resized versions for each size
resized_images = []
for size in sizes:
    resized = img.resize(size, Image.Resampling.LANCZOS)
    resized_images.append(resized)

# Save ICO with all sizes - PIL handles the multi-resolution ICO format
img.save(out_ico, format="ICO", sizes=sizes)
print(f"✓ Wrote {out_ico} with {len(sizes)} sizes: {sizes}")
