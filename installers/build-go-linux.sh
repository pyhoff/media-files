#!/bin/bash
# Installs Go + system dependencies, then compiles media-converter (Go version) for Linux.
# Supports Debian/Ubuntu, Fedora/RHEL, and Arch-based distros.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Media Converter (Go) — Linux Build ==="

# --- Detect distro ---
if [ ! -f /etc/os-release ]; then
    echo "Error: cannot detect distro — /etc/os-release not found." >&2
    exit 1
fi
. /etc/os-release
DISTRO_ID="${ID:-unknown}"
DISTRO_LIKE="${ID_LIKE:-}"

# --- Install system deps (Go + Fyne C libs + ffmpeg) ---
install_system_deps() {
    case "$DISTRO_ID" in
        ubuntu|debian|linuxmint|pop|kali)
            echo "Detected Debian-based distro ($DISTRO_ID)"
            sudo apt-get update -q
            sudo apt-get install -y golang-go ffmpeg \
                libgl1-mesa-dev xorg-dev libxcursor-dev libxrandr-dev \
                libxinerama-dev libxi-dev
            ;;
        fedora)
            echo "Detected Fedora"
            sudo dnf install -y golang ffmpeg \
                mesa-libGL-devel libXcursor-devel libXrandr-devel \
                libXinerama-devel libXi-devel
            ;;
        rhel|centos|rocky|almalinux)
            echo "Detected RHEL-based distro ($DISTRO_ID)"
            sudo dnf install -y golang ffmpeg \
                mesa-libGL-devel libXcursor-devel libXrandr-devel \
                libXinerama-devel libXi-devel || \
            sudo yum install -y golang ffmpeg \
                mesa-libGL-devel libXcursor-devel libXrandr-devel \
                libXinerama-devel libXi-devel
            ;;
        arch|manjaro|endeavouros|garuda)
            echo "Detected Arch-based distro ($DISTRO_ID)"
            sudo pacman -Sy --noconfirm go ffmpeg \
                mesa libxcursor libxrandr libxinerama libxi
            ;;
        *)
            if echo "$DISTRO_LIKE" | grep -q "debian\|ubuntu"; then
                echo "Detected Debian-like distro via ID_LIKE"
                sudo apt-get update -q
                sudo apt-get install -y golang-go ffmpeg \
                    libgl1-mesa-dev xorg-dev libxcursor-dev libxrandr-dev \
                    libxinerama-dev libxi-dev
            elif echo "$DISTRO_LIKE" | grep -q "fedora\|rhel"; then
                echo "Detected Fedora/RHEL-like distro via ID_LIKE"
                sudo dnf install -y golang ffmpeg \
                    mesa-libGL-devel libXcursor-devel libXrandr-devel \
                    libXinerama-devel libXi-devel
            elif echo "$DISTRO_LIKE" | grep -q "arch"; then
                echo "Detected Arch-like distro via ID_LIKE"
                sudo pacman -Sy --noconfirm go ffmpeg \
                    mesa libxcursor libxrandr libxinerama libxi
            else
                echo "Error: unsupported distro '$DISTRO_ID'. Install Go 1.21+, ffmpeg, and Fyne system libs manually." >&2
                exit 1
            fi
            ;;
    esac
}

# --- Detect OS UI language (2-letter code) ---
_detect_lang() {
    local lang="" val=""
    for _lv in LC_ALL LC_MESSAGES LANG LANGUAGE; do
        val="${!_lv:-}"
        [ -z "$val" ] && continue
        val="${val%%:*}"
        val="$(printf '%s' "$val" | sed 's/[_.@-].*//' | tr '[:upper:]' '[:lower:]')"
        if [ "$val" = "c" ] || [ "$val" = "posix" ]; then lang="en"; break; fi
        if [ -n "$val" ]; then lang="$val"; break; fi
    done
    printf '%s' "${lang:-en}"
}

install_system_deps

# --- Check Go version (need 1.21+) ---
GO_VERSION="$(go version | grep -oP 'go\K[0-9]+\.[0-9]+')"
GO_MAJOR="$(echo "$GO_VERSION" | cut -d. -f1)"
GO_MINOR="$(echo "$GO_VERSION" | cut -d. -f2)"
if [ "$GO_MAJOR" -lt 1 ] || { [ "$GO_MAJOR" -eq 1 ] && [ "$GO_MINOR" -lt 21 ]; }; then
    echo ""
    echo "Warning: Go $GO_VERSION is installed but this project requires Go 1.21+."
    echo "Install a newer version from https://go.dev/dl/ and re-run this script."
    exit 1
fi
echo "Go $GO_VERSION — OK"

# --- Build ---
echo "Fetching dependencies..."
cd go
go mod tidy

echo "Building executable..."
mkdir -p ../dist
go build -ldflags="-s -w" -o ../dist/media-converter .


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
