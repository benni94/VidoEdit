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

# -----------------------------
# Ensure Python is installed
# -----------------------------
if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  echo "Python not found. Attempting installation via Homebrew..."

  if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew not found. Install it first: https://brew.sh" >&2
    exit 1
  fi

  brew update
  brew install python

  PYTHON=python3
fi

echo "Python OK: $($PYTHON --version)"

# -----------------------------
# Download and bundle FFmpeg
# -----------------------------
echo "Preparing FFmpeg for bundling..."

FFMPEG_BUNDLE="$ROOT_DIR/ffmpeg_bundle"
FFMPEG_BIN="$FFMPEG_BUNDLE/bin"
FFMPEG_EXE="$FFMPEG_BIN/ffmpeg"
FFPROBE_EXE="$FFMPEG_BIN/ffprobe"

if [[ ! -f "$FFMPEG_EXE" ]] || [[ ! -f "$FFPROBE_EXE" ]]; then
  echo "Downloading FFmpeg for bundling..."
  
  TEMP_DIR=$(mktemp -d)
  
  # Detect architecture
  ARCH=$(uname -m)
  if [[ "$ARCH" == "arm64" ]]; then
    FFMPEG_URL="https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip"
    FFPROBE_URL="https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip"
  else
    FFMPEG_URL="https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip"
    FFPROBE_URL="https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip"
  fi
  
  echo "Downloading FFmpeg for macOS ($ARCH)..."
  curl -L -o "$TEMP_DIR/ffmpeg.zip" "$FFMPEG_URL" || {
    echo "Error: Failed to download FFmpeg" >&2
    echo "Please download FFmpeg manually from https://evermeet.cx/ffmpeg/" >&2
    echo "Extract and place ffmpeg and ffprobe in: $FFMPEG_BIN" >&2
    exit 1
  }
  
  echo "Downloading FFprobe..."
  curl -L -o "$TEMP_DIR/ffprobe.zip" "$FFPROBE_URL" || {
    echo "Error: Failed to download FFprobe" >&2
    exit 1
  }
  
  echo "Extracting FFmpeg..."
  mkdir -p "$FFMPEG_BIN"
  unzip -q "$TEMP_DIR/ffmpeg.zip" -d "$TEMP_DIR"
  unzip -q "$TEMP_DIR/ffprobe.zip" -d "$TEMP_DIR"
  
  mv "$TEMP_DIR/ffmpeg" "$FFMPEG_EXE"
  mv "$TEMP_DIR/ffprobe" "$FFPROBE_EXE"
  chmod +x "$FFMPEG_EXE" "$FFPROBE_EXE"
  
  rm -rf "$TEMP_DIR"
  echo "✓ FFmpeg extracted to: $FFMPEG_BIN"
fi

echo "FFmpeg ready for bundling: $FFMPEG_EXE"

echo "Installing flet CLI if missing..."
python3 -m pip show flet >/dev/null 2>&1 || python3 -m pip install flet
python3 -m pip show flet >/dev/null 2>&1 || {
  echo "Error: flet installation failed." >&2
  exit 1
}

echo "Packing macOS app bundle with bundled FFmpeg..."
cd "$ROOT_DIR"
# --name controls app bundle name; adjust if desired
flet pack main.py \
  --name "VidoEdit" \
  --icon "$ICNS_OUT" \
  --add-binary "$FFMPEG_EXE:ffmpeg_bundle/bin" \
  --add-binary "$FFPROBE_EXE:ffmpeg_bundle/bin"

echo ""
echo "========================================="
echo "✓ Build complete!"
echo "========================================="
echo "Executable location: $ROOT_DIR/dist/VidoEdit.app"
echo ""
echo "The app bundle is fully standalone and includes:"
echo "  ✓ FFmpeg and FFprobe"
echo "  ✓ All Python dependencies"
echo "  ✓ Application assets and translations"
echo ""
echo "You can distribute this .app bundle to users without any additional dependencies."
