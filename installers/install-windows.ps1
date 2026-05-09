#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Installs dependencies and builds media-converter as a Windows executable.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

Write-Host "=== Media Converter Windows Build ===" -ForegroundColor Cyan

# Chocolatey
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Chocolatey..." -ForegroundColor Yellow
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString("https://community.chocolatey.org/install.ps1"))

    $ChocolateyBin = Join-Path $env:ProgramData "chocolatey\bin"
    $env:Path = "$env:Path;$ChocolateyBin"
}

# Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Python..." -ForegroundColor Yellow
    choco install python --yes

    $PythonPath = "C:\Python312"
    $PythonScripts = "C:\Python312\Scripts"

    if (Test-Path $PythonPath) {
        $env:Path = "$env:Path;$PythonPath;$PythonScripts"
    }
}

# ffmpeg
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "Installing ffmpeg..." -ForegroundColor Yellow
    choco install ffmpeg --yes

    $FfmpegPath = Join-Path $env:ProgramData "chocolatey\bin"
    $env:Path = "$env:Path;$FfmpegPath"
}

# Virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
python -m venv .venv
& ".\.venv\Scripts\Activate.ps1"

# Dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip
python -m pip install PyQt6 pyinstaller

# Build
Write-Host "Building executable..." -ForegroundColor Yellow
pyinstaller --onefile --windowed --name "media-converter" `
    --add-data "media_converter.py;." `
    --add-data "media_extractor.py;." `
    media-converter-gui.py

Write-Host ""
Write-Host "Done. Executable: dist\media-converter.exe" -ForegroundColor Green
