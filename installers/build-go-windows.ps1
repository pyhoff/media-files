#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Installs Go, MinGW (CGo), and ffmpeg, then compiles media-converter (Go version) for Windows.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location $ProjectRoot

Write-Host "=== Media Converter (Go) — Windows Build ===" -ForegroundColor Cyan

# --- Chocolatey ---
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Chocolatey..." -ForegroundColor Yellow
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    $env:PATH += ";$env:ALLUSERSPROFILE\chocolatey\bin"
}

# --- Go ---
if (-not (Get-Command go -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Go..." -ForegroundColor Yellow
    choco install golang --yes
    refreshenv
    $env:PATH += ";$env:ProgramFiles\Go\bin"
}

# --- MinGW (provides gcc, required by CGo for Fyne) ---
if (-not (Get-Command gcc -ErrorAction SilentlyContinue)) {
    Write-Host "Installing MinGW (GCC — required for CGo/Fyne)..." -ForegroundColor Yellow
    choco install mingw --yes
    refreshenv
    $env:PATH += ";$env:ProgramFiles\mingw64\bin"
}

# --- ffmpeg ---
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "Installing ffmpeg..." -ForegroundColor Yellow
    choco install ffmpeg --yes
    refreshenv
}

# --- Check Go version (need 1.21+) ---
$goVerStr = (go version) -replace ".*go([0-9]+\.[0-9]+).*", '$1'
$goMajor, $goMinor = $goVerStr.Split(".") | ForEach-Object { [int]$_ }
if ($goMajor -lt 1 -or ($goMajor -eq 1 -and $goMinor -lt 21)) {
    Write-Host "Error: Go $goVerStr found but 1.21+ is required. Run: choco upgrade golang" -ForegroundColor Red
    exit 1
}
Write-Host "Go $goVerStr — OK" -ForegroundColor Green

# --- Build ---
Write-Host "Fetching dependencies..." -ForegroundColor Yellow
Set-Location go
go mod tidy

Write-Host "Building executable..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "..\dist" | Out-Null
go build -ldflags="-s -w" -o "..\dist\media-converter.exe" .

Write-Host ""
Write-Host "Done. Executable: dist\media-converter.exe" -ForegroundColor Green
Write-Host "Usage:  .\dist\media-converter.exe                       (GUI)"
Write-Host "        .\dist\media-converter.exe <in> <fmt> <out> [-r]  (CLI)"
