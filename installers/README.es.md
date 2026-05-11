# Instaladores

Scripts de compilación que instalan todas las dependencias y compilan media-converter en un ejecutable independiente.

Hay dos implementaciones disponibles: Python (PyInstaller) y Go. Ambas producen un único binario en `dist/`.

> **Nota:** Cada script resuelve las rutas automáticamente sin importar desde dónde se ejecute. ffmpeg se instala como paquete del sistema por cada script.

---

## Scripts de compilación Go

Las versiones Go producen un **verdadero binario único** sin dependencias en tiempo de ejecución (solo ffmpeg debe estar en el PATH). Fyne usa CGo, por lo que debes compilar en el sistema operativo destino — la compilación cruzada no está soportada.

### Linux — `build-go-linux.sh`

**Requiere:** acceso sudo. Soporta Debian/Ubuntu, Fedora/RHEL y distros basadas en Arch.

```bash
chmod +x installers/build-go-linux.sh
./installers/build-go-linux.sh
```

Qué hace:
1. Detecta la distro e instala Go, ffmpeg y las bibliotecas C de Fyne mediante el gestor de paquetes nativo
2. Verifica Go 1.21+
3. Ejecuta `go mod tidy && go build`
4. Genera `dist/media-converter`

### macOS — `build-go-macos.sh`

**Requiere:** macOS 12+, acceso a internet

```bash
chmod +x installers/build-go-macos.sh
./installers/build-go-macos.sh
```

Qué hace:
1. Verifica que las Herramientas de Línea de Comandos de Xcode estén instaladas (necesarias para CGo)
2. Instala Go y ffmpeg mediante Homebrew
3. Verifica Go 1.21+
4. Ejecuta `go mod tidy && go build`
5. Genera `dist/media-converter`

### Windows — `build-go-windows.ps1`

**Requiere:** PowerShell 5+, ejecutar como Administrador

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\installers\build-go-windows.ps1
```

Qué hace:
1. Instala [Chocolatey](https://chocolatey.org) si falta
2. Instala Go y ffmpeg mediante Chocolatey
3. Instala MinGW (GCC) — necesario por CGo para Fyne
4. Verifica Go 1.21+
5. Ejecuta `go mod tidy && go build`
6. Genera `dist\media-converter.exe`

---

## Scripts de compilación Python (PyInstaller)

## Windows — `install-windows.ps1`

**Requiere:** PowerShell 5+, ejecutar como Administrador

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\installers\install-windows.ps1
```

Qué hace:
1. Instala [Chocolatey](https://chocolatey.org) si falta
2. Instala Python y ffmpeg mediante Chocolatey
3. Crea un entorno virtual `.venv`
4. Instala `PyQt6` y `pyinstaller`
5. Genera `dist\media-converter.exe`

---

## macOS — `install-macos.sh`

**Requiere:** macOS 12+, acceso a internet

```bash
chmod +x installers/install-macos.sh
./installers/install-macos.sh
```

Qué hace:
1. Instala [Homebrew](https://brew.sh) si falta
2. Instala Python y ffmpeg mediante Homebrew
3. Crea un entorno virtual `.venv`
4. Instala `PyQt6` y `pyinstaller`
5. Genera `dist/Media Converter.app`

---

## Linux — `install-linux.sh`

**Requiere:** acceso sudo. Soporta Debian/Ubuntu, Fedora/RHEL y distros basadas en Arch.

```bash
chmod +x installers/install-linux.sh
./installers/install-linux.sh
```

Qué hace:
1. Detecta la distro e instala Python, pip y ffmpeg mediante el gestor de paquetes nativo (`apt`, `dnf` o `pacman`)
2. Crea un entorno virtual `.venv`
3. Instala `PyQt6` y `pyinstaller`
4. Genera `dist/media-converter`

---

## Resultados

| Script | Plataforma | Resultado |
|--------|------------|-----------|
| Python | Windows    | `dist\media-converter.exe` |
| Python | macOS      | `dist/Media Converter.app` |
| Python | Linux      | `dist/media-converter` |
| Go     | Windows    | `dist\media-converter.exe` |
| Go     | macOS      | `dist/media-converter` |
| Go     | Linux      | `dist/media-converter` |

El entorno virtual de Python se crea en `.venv/` en la raíz del proyecto y puede eliminarse de forma segura tras la compilación. La caché de módulos de Go es gestionada por Go mismo.
