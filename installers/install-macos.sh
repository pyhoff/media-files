#!/bin/bash
# Installs dependencies and builds media-converter as a macOS .app bundle.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Media Converter — macOS Build ==="

# --- Homebrew ---
if ! command -v brew &>/dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv)"
fi

# --- Python & ffmpeg ---
echo "Installing Python and ffmpeg..."
brew install python ffmpeg

# --- Virtual environment ---
echo "Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# --- Dependencies ---
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install PyQt6 pyinstaller

# --- Build ---
echo "Building .app bundle..."
pyinstaller --windowed --name "Media Converter" \
    --add-data "media_converter.py:." \
    --add-data "media_extractor.py:." \
    media-converter-gui.py

echo ""
echo "Done. App bundle: dist/Media Converter.app"
