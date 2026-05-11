#!/bin/bash
# Installs dependencies and builds media-converter as a macOS .app bundle.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Media Converter — macOS Build ==="

# --- Detect OS UI language (2-letter code) ---
_detect_lang() {
    local lang="" val=""
    # macOS: query System Preferences language list
    if command -v defaults &>/dev/null; then
        lang="$(defaults read -g AppleLanguages 2>/dev/null \
            | grep -o '"[A-Za-z][A-Za-z]' | head -1 \
            | tr -d '"' | tr '[:upper:]' '[:lower:]')" || true
    fi
    # POSIX / GNU env var fallback
    if [ -z "$lang" ]; then
        for _lv in LC_ALL LC_MESSAGES LANG LANGUAGE; do
            val="${!_lv:-}"
            [ -z "$val" ] && continue
            val="${val%%:*}"
            val="$(printf '%s' "$val" | sed 's/[_.@-].*//' | tr '[:upper:]' '[:lower:]')"
            if [ "$val" = "c" ] || [ "$val" = "posix" ]; then lang="en"; break; fi
            if [ -n "$val" ]; then lang="$val"; break; fi
        done
    fi
    printf '%s' "${lang:-en}"
}

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


_LANG="$(_detect_lang)"
if [ "$_LANG" = "es" ]; then
    [ -f README.es.md ]            && cp README.es.md README.md
    [ -f installers/README.es.md ] && cp installers/README.es.md installers/README.md
    echo ""
    echo "¡Listo! Paquete de aplicación: dist/Media Converter.app"
    echo "Documentación actualizada al español (README.md)."
else
    echo ""
    echo "Done. App bundle: dist/Media Converter.app"
fi
