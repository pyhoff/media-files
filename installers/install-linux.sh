#!/bin/bash
# Installs dependencies and builds media-converter as a Linux executable.
# Supports Debian/Ubuntu, Fedora, and Arch-based distros.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Media Converter — Linux Build ==="

# --- Detect distro ---
if [ ! -f /etc/os-release ]; then
    echo "Error: cannot detect distro — /etc/os-release not found." >&2
    exit 1
fi

. /etc/os-release
DISTRO_ID="${ID:-unknown}"
DISTRO_LIKE="${ID_LIKE:-}"

install_system_deps() {
    case "$DISTRO_ID" in
        ubuntu|debian|linuxmint|pop|kali)
            echo "Detected Debian-based distro ($DISTRO_ID)"
            sudo apt-get update -q
            sudo apt-get install -y python3 python3-pip python3-venv ffmpeg
            ;;
        fedora)
            echo "Detected Fedora"
            sudo dnf install -y python3 python3-pip ffmpeg
            ;;
        rhel|centos|rocky|almalinux)
            echo "Detected RHEL-based distro ($DISTRO_ID)"
            sudo dnf install -y python3 python3-pip ffmpeg || \
            sudo yum install -y python3 python3-pip ffmpeg
            ;;
        arch|manjaro|endeavouros|garuda)
            echo "Detected Arch-based distro ($DISTRO_ID)"
            sudo pacman -Sy --noconfirm python python-pip ffmpeg
            ;;
        *)
            # Fallback: check ID_LIKE
            if echo "$DISTRO_LIKE" | grep -q "debian\|ubuntu"; then
                echo "Detected Debian-like distro via ID_LIKE"
                sudo apt-get update -q
                sudo apt-get install -y python3 python3-pip python3-venv ffmpeg
            elif echo "$DISTRO_LIKE" | grep -q "fedora\|rhel"; then
                echo "Detected Fedora/RHEL-like distro via ID_LIKE"
                sudo dnf install -y python3 python3-pip ffmpeg
            elif echo "$DISTRO_LIKE" | grep -q "arch"; then
                echo "Detected Arch-like distro via ID_LIKE"
                sudo pacman -Sy --noconfirm python python-pip ffmpeg
            else
                echo "Error: unsupported distro '$DISTRO_ID'. Install Python 3, pip, and ffmpeg manually then re-run." >&2
                exit 1
            fi
            ;;
    esac
}

install_system_deps

# --- Virtual environment ---
echo "Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# --- Dependencies ---
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install PyQt6 pyinstaller

# --- Build ---
echo "Building executable..."
pyinstaller --onefile --windowed --name "media-converter" media-converter-gui.py

echo ""
echo "Done. Executable: dist/media-converter"
