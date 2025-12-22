#!/usr/bin/env bash
set -euo pipefail

# Linux packaging script for H266VideoConverter using flet pack
# Embeds PNG icon into the package (AppImage by default)
# Requirements:
#   - Linux
#   - Python with flet installed
#   - attachments/vidoedit.png present
# Usage:
#   chmod +x scripts/build_linux.sh
#   scripts/build_linux.sh

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ATTACH_DIR="$ROOT_DIR/attachments"
ICON_PNG="$ATTACH_DIR/vidoedit.png"

if [[ ! -f "$ICON_PNG" ]]; then
  echo "Error: $ICON_PNG not found." >&2
  exit 1
fi

echo "Installing flet CLI if missing..."
python3 -m pip show flet >/dev/null 2>&1 || python3 -m pip install flet
python3 -m pip show flet >/dev/null 2>&1 || {
  echo "Error: flet installation failed." >&2
  exit 1
}

echo "Packing Linux AppImage..."
cd "$ROOT_DIR"
flet pack main.py \
  --name "VidoEdit" \
  --icon "$ICON_PNG"

echo "\n✓ Build complete. Check the dist/ folder for the AppImage." 
