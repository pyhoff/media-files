#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Installs Go, MinGW (CGo), and ffmpeg, then compiles media-converter (Go version) for Windows.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

Write-Host "=== Media Converter (Go) Windows Build ===" -ForegroundColor Cyan

# Chocolatey
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Chocolatey..." -ForegroundColor Yellow
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString("https://community.chocolatey.org/install.ps1"))

    $ChocolateyBin = Join-Path $env:ProgramData "chocolatey\bin"
    $env:Path = "$env:Path;$ChocolateyBin"
}

# Go
if (-not (Get-Command go -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Go..." -ForegroundColor Yellow
    choco install golang --yes

    $GoBin = Join-Path $env:ProgramFiles "Go\bin"
    if (Test-Path $GoBin) {
        $env:Path = "$env:Path;$GoBin"
    }
}

# MinGW - gcc is required by CGo (Fyne)
if (-not (Get-Command gcc -ErrorAction SilentlyContinue)) {
    Write-Host "Installing MinGW (required for CGo/Fyne)..." -ForegroundColor Yellow
    choco install mingw --yes

    $MingwBin = Join-Path $env:ProgramFiles "mingw64\bin"
    if (Test-Path $MingwBin) {
        $env:Path = "$env:Path;$MingwBin"
    }
}

# ffmpeg
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "Installing ffmpeg..." -ForegroundColor Yellow
    choco install ffmpeg --yes

    $FfmpegBin = Join-Path $env:ProgramData "chocolatey\bin"
    $env:Path = "$env:Path;$FfmpegBin"
}

# Check Go version (need 1.21+)
$goVerStr = (go version) -replace ".*go([0-9]+\.[0-9]+).*", '$1'
$goParts  = $goVerStr.Split(".")
$goMajor  = [int]$goParts[0]
$goMinor  = [int]$goParts[1]
if ($goMajor -lt 1 -or ($goMajor -eq 1 -and $goMinor -lt 21)) {
    Write-Host "Error: Go $goVerStr found but 1.21+ is required. Run: choco upgrade golang" -ForegroundColor Red
    exit 1
}
Write-Host "Go $goVerStr - OK" -ForegroundColor Green

# Build
Write-Host "Fetching dependencies..." -ForegroundColor Yellow
Set-Location go
go mod tidy

Write-Host "Building executable..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "..\dist" | Out-Null
go build -ldflags="-s -w -H windowsgui" -o "..\dist\media-converter.exe" .


# --- Language detection and README localization ---
$LangCode = [System.Globalization.CultureInfo]::CurrentUICulture.TwoLetterISOLanguageName.ToLower()
if ($LangCode -eq "es") {
    if (Test-Path "README.es.md")            { Copy-Item "README.es.md"            "README.md"            -Force }
    if (Test-Path "installers\README.es.md") { Copy-Item "installers\README.es.md" "installers\README.md" -Force }
    Write-Host ""
    Write-Host "¡Listo! Ejecutable: dist\media-converter.exe" -ForegroundColor Green
    Write-Host "Uso:  .\dist\media-converter.exe                         (GUI)"
    Write-Host "      .\dist\media-converter.exe --cli <entrada> <fmt> <salida>  (CLI)"
    Write-Host "Documentación actualizada al español (README.md)."
} else {
    Write-Host ""
    Write-Host "Done. Executable: dist\media-converter.exe" -ForegroundColor Green
    Write-Host "Usage:  .\dist\media-converter.exe                        (GUI)"
    Write-Host "        .\dist\media-converter.exe --cli <in> <fmt> <out>  (CLI)"
}
