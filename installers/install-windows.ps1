#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Installs dependencies and builds media-converter as a Windows executable.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location $ProjectRoot

Write-Host "=== Media Converter — Windows Build ===" -ForegroundColor Cyan

# --- Chocolatey ---
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Chocolatey..." -ForegroundColor Yellow
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    $env:PATH += ";$env:ALLUSERSPROFILE\chocolatey\bin"
}

# --- Python ---
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Python..." -ForegroundColor Yellow
    choco install python --yes
    refreshenv
}

# --- ffmpeg ---
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "Installing ffmpeg..." -ForegroundColor Yellow
    choco install ffmpeg --yes
    refreshenv
}

# --- Virtual environment ---
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
python -m venv .venv
& ".venv\Scripts\Activate.ps1"

# --- Dependencies ---
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip
pip install PyQt6 pyinstaller

# --- Build ---
Write-Host "Building executable..." -ForegroundColor Yellow
pyinstaller --onefile --windowed --name "media-converter" media-converter-gui.py

Write-Host ""
Write-Host "Done. Executable: dist\media-converter.exe" -ForegroundColor Green
