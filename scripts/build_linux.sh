#!/usr/bin/env bash
set -euo pipefail

# Linux packaging script for VidoEdit using flet pack
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

# -----------------------------
# Ensure Python is installed
# -----------------------------
if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  echo "Python3 not found. Attempting installation..."

  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip

  elif command -v apt >/dev/null 2>&1; then
    sudo apt update
    sudo apt install -y python3 python3-pip

  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y python3 python3-pip

  elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y python3 python3-pip

  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -Sy --noconfirm python python-pip

  elif command -v zypper >/dev/null 2>&1; then
    sudo zypper --non-interactive install python3 python3-pip

  else
    echo "No supported package manager found. Install Python manually." >&2
    exit 1
  fi

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
  FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
  FFMPEG_ARCHIVE="$TEMP_DIR/ffmpeg.tar.xz"
  
  echo "Downloading from: $FFMPEG_URL"
  curl -L -o "$FFMPEG_ARCHIVE" "$FFMPEG_URL" || {
    echo "Error: Failed to download FFmpeg" >&2
    echo "Please download FFmpeg manually from https://johnvansickle.com/ffmpeg/" >&2
    echo "Extract and place ffmpeg and ffprobe in: $FFMPEG_BIN" >&2
    exit 1
  }
  
  echo "Extracting FFmpeg..."
  tar -xf "$FFMPEG_ARCHIVE" -C "$TEMP_DIR"
  
  EXTRACTED_DIR=$(find "$TEMP_DIR" -maxdepth 1 -type d -name "ffmpeg-*" | head -n 1)
  
  if [[ -z "$EXTRACTED_DIR" ]]; then
    echo "Error: Could not find extracted FFmpeg folder" >&2
    exit 1
  fi
  
  mkdir -p "$FFMPEG_BIN"
  cp "$EXTRACTED_DIR/ffmpeg" "$FFMPEG_EXE"
  cp "$EXTRACTED_DIR/ffprobe" "$FFPROBE_EXE"
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

echo "Packing Linux AppImage with bundled FFmpeg..."
cd "$ROOT_DIR"
flet pack main.py \
  --name "VidoEdit" \
  --icon "$ICON_PNG" \
  --add-binary "$FFMPEG_EXE:ffmpeg_bundle/bin" \
  --add-binary "$FFPROBE_EXE:ffmpeg_bundle/bin"

echo ""
echo "========================================="
echo "✓ Build complete!"
echo "========================================="
echo "Executable location: $ROOT_DIR/dist/"
echo ""
echo "The AppImage is fully standalone and includes:"
echo "  ✓ FFmpeg and FFprobe"
echo "  ✓ All Python dependencies"
echo "  ✓ Application assets and translations"
echo ""
echo "You can distribute this AppImage to users without any additional dependencies." 
