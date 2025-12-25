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

# Ensure FFmpeg is installed
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "FFmpeg not found. Attempting installation..."
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update && sudo apt-get install -y ffmpeg
  elif command -v apt >/dev/null 2>&1; then
    sudo apt update && sudo apt install -y ffmpeg
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y ffmpeg
  elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y epel-release || true
    sudo yum install -y ffmpeg
  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -Sy --noconfirm ffmpeg
  elif command -v zypper >/dev/null 2>&1; then
    sudo zypper --non-interactive install ffmpeg
  else
    echo "Could not detect a supported package manager to install FFmpeg. Please install FFmpeg manually." >&2
    exit 1
  fi
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
