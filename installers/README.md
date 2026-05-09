# Installers

Build scripts that install all dependencies and compile media-converter into a standalone executable.

Two implementations are available — Python (PyInstaller) and Go. Both produce a single binary in `dist/`.

> **Note:** Each script resolves paths automatically regardless of where it is called from. ffmpeg is installed by each script as a system package.

---

## Go build scripts

The Go versions produce a **true single binary** with no runtime dependencies (only ffmpeg must be on PATH at runtime). Fyne uses CGo, so you must build on the target OS — cross-compilation is not supported.

### Linux — `build-go-linux.sh`

**Requires:** sudo access. Supports Debian/Ubuntu, Fedora/RHEL, and Arch-based distros.

```bash
chmod +x installers/build-go-linux.sh
./installers/build-go-linux.sh
```

What it does:
1. Detects distro and installs Go, ffmpeg, and Fyne's required C libraries via the native package manager
2. Verifies Go 1.21+
3. Runs `go mod tidy && go build`
4. Outputs `dist/media-converter`

### macOS — `build-go-macos.sh`

**Requires:** macOS 12+, internet access

```bash
chmod +x installers/build-go-macos.sh
./installers/build-go-macos.sh
```

What it does:
1. Ensures Xcode Command Line Tools are installed (required for CGo)
2. Installs Go and ffmpeg via Homebrew
3. Verifies Go 1.21+
4. Runs `go mod tidy && go build`
5. Outputs `dist/media-converter`

### Windows — `build-go-windows.ps1`

**Requires:** PowerShell 5+, run as Administrator

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\installers\build-go-windows.ps1
```

What it does:
1. Installs [Chocolatey](https://chocolatey.org) if missing
2. Installs Go and ffmpeg via Chocolatey
3. Installs MinGW (GCC) — required by CGo for Fyne
4. Verifies Go 1.21+
5. Runs `go mod tidy && go build`
6. Outputs `dist\media-converter.exe`

---

## Python build scripts (PyInstaller)

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

| Script | Platform | Output |
|--------|----------|--------|
| Python | Windows  | `dist\media-converter.exe` |
| Python | macOS    | `dist/Media Converter.app` |
| Python | Linux    | `dist/media-converter` |
| Go     | Windows  | `dist\media-converter.exe` |
| Go     | macOS    | `dist/media-converter` |
| Go     | Linux    | `dist/media-converter` |

The Python virtual environment is created at `.venv/` in the project root and can be safely deleted after building. The Go module cache is managed by Go itself.
