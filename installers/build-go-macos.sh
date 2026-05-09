#!/bin/bash
# Installs Go + dependencies, then compiles media-converter (Go version) for macOS.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Media Converter (Go) — macOS Build ==="

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

echo ""
echo "Done. Executable: dist/media-converter"
echo "Usage:  ./dist/media-converter                        (GUI)"
echo "        ./dist/media-converter <in> <fmt> <out> [-r]  (CLI)"
