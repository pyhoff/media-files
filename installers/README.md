# Installers

Build scripts that install all dependencies and compile media-converter into a standalone executable.

> **Note:** Each script must be run from the `installers/` directory or will resolve paths automatically. ffmpeg is installed by each script as a system package.

---

## Windows — `install-windows.ps1`

**Requires:** PowerShell 5+, run as Administrator

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\installers\install-windows.ps1
```

What it does:
1. Installs [Chocolatey](https://chocolatey.org) if missing
2. Installs Python and ffmpeg via Chocolatey
3. Creates a `.venv` virtual environment
4. Installs `PyQt6` and `pyinstaller`
5. Builds `dist\media-converter.exe`

---

## macOS — `install-macos.sh`

**Requires:** macOS 12+, internet access

```bash
chmod +x installers/install-macos.sh
./installers/install-macos.sh
```

What it does:
1. Installs [Homebrew](https://brew.sh) if missing
2. Installs Python and ffmpeg via Homebrew
3. Creates a `.venv` virtual environment
4. Installs `PyQt6` and `pyinstaller`
5. Builds `dist/Media Converter.app`

---

## Linux — `install-linux.sh`

**Requires:** sudo access. Supports Debian/Ubuntu, Fedora/RHEL, and Arch-based distros.

```bash
chmod +x installers/install-linux.sh
./installers/install-linux.sh
```

What it does:
1. Detects distro and installs Python, pip, and ffmpeg via the native package manager (`apt`, `dnf`, or `pacman`)
2. Creates a `.venv` virtual environment
3. Installs `PyQt6` and `pyinstaller`
4. Builds `dist/media-converter`

---

## Output

| Platform | Output |
|----------|--------|
| Windows  | `dist\media-converter.exe` |
| macOS    | `dist/Media Converter.app` |
| Linux    | `dist/media-converter` |

The virtual environment is created at `.venv/` in the project root and can be safely deleted after building.
