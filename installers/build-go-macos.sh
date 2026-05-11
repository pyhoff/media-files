#!/bin/bash
# Installs Go + dependencies, then compiles media-converter (Go version) for macOS.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Media Converter (Go) — macOS Build ==="

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

# --- Xcode Command Line Tools (required for CGo) ---
if ! xcode-select -p &>/dev/null; then
    echo "Installing Xcode Command Line Tools..."
    xcode-select --install
    echo "Re-run this script after the Xcode CLT installation finishes."
    exit 0
fi

# --- Homebrew ---
if ! command -v brew &>/dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv)"
fi

# --- Go + ffmpeg ---
echo "Installing Go and ffmpeg..."
brew install go ffmpeg

# --- Check Go version (need 1.21+) ---
GO_VERSION="$(go version | grep -oE 'go[0-9]+\.[0-9]+' | head -1 | sed 's/go//')"
GO_MAJOR="$(echo "$GO_VERSION" | cut -d. -f1)"
GO_MINOR="$(echo "$GO_VERSION" | cut -d. -f2)"
if [ "$GO_MAJOR" -lt 1 ] || { [ "$GO_MAJOR" -eq 1 ] && [ "$GO_MINOR" -lt 21 ]; }; then
    echo "Error: Go $GO_VERSION found but 1.21+ is required. Run: brew upgrade go" >&2
    exit 1
fi
echo "Go $GO_VERSION — OK"

# --- Build ---
echo "Fetching dependencies..."
cd go
go mod tidy

echo "Building executable..."
mkdir -p ../dist
go build -ldflags="-s -w" -o "../dist/media-converter" .


_LANG="$(_detect_lang)"
if [ "$_LANG" = "es" ]; then
    [ -f README.es.md ]            && cp README.es.md README.md
    [ -f installers/README.es.md ] && cp installers/README.es.md installers/README.md
    echo ""
    echo "¡Listo! Ejecutable: dist/media-converter"
    echo "Uso:  ./dist/media-converter                                     (GUI)"
    echo "      ./dist/media-converter --cli <entrada> <fmt> <salida> [-r] (CLI)"
    echo "Documentación actualizada al español (README.md)."
else
    echo ""
    echo "Done. Executable: dist/media-converter"
    echo "Usage:  ./dist/media-converter                        (GUI)"
    echo "        ./dist/media-converter --cli <in> <fmt> <out> [-r]  (CLI)"
fi
