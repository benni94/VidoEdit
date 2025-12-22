#!/usr/bin/env bash
set -euo pipefail

# macOS app bundling with custom icon for H266VideoConverter
# Requirements:
#   - macOS with Xcode Command Line Tools (for iconutil)
#   - Python venv with flet installed (or global flet)
#   - attachments/vidoedit.png present
# Usage:
#   chmod +x scripts/build_macos.sh
#   scripts/build_macos.sh

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ATTACH_DIR="$ROOT_DIR/attachments"
ICON_PNG="$ATTACH_DIR/vidoedit.png"
ICNS_OUT="$ATTACH_DIR/vidoedit.icns"
ICONSET_DIR="$ATTACH_DIR/Icon.iconset"

if [[ ! -f "$ICON_PNG" ]]; then
  echo "Error: $ICON_PNG not found." >&2
  exit 1
fi

rm -rf "$ICONSET_DIR"
mkdir -p "$ICONSET_DIR"

# Generate required iconset sizes from base PNG
# If your source PNG is small, consider starting from a larger source image.
SIZES=(16 32 64 128 256 512)
for size in "${SIZES[@]}"; do
  sips -z "$size" "$size" "$ICON_PNG" --out "$ICONSET_DIR/icon_${size}x${size}.png" >/dev/null
  double=$((size*2))
  sips -z "$double" "$double" "$ICON_PNG" --out "$ICONSET_DIR/icon_${size}x${size}@2x.png" >/dev/null
done

# Build .icns from iconset
iconutil -c icns "$ICONSET_DIR" -o "$ICNS_OUT"

if [[ ! -f "$ICNS_OUT" ]]; then
  echo "Error: failed to generate $ICNS_OUT" >&2
  exit 1
fi

echo "✓ Generated icon: $ICNS_OUT"

echo "Installing flet CLI if missing..."
python3 -m pip show flet >/dev/null 2>&1 || python3 -m pip install flet
python3 -m pip show flet >/dev/null 2>&1 || {
  echo "Error: flet installation failed." >&2
  exit 1
}

echo "Packing macOS app bundle..."
cd "$ROOT_DIR"
# --name controls app bundle name; adjust if desired
flet pack main.py \
  --name "VidoEdit" \
  --icon "$ICNS_OUT"

echo "\n✓ Build complete. Check the dist/ folder for the VidoEdit.app bundle."
