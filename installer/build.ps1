#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent

Write-Host "============================================================"
Write-Host " tdibam_t2s -- Release Build"
Write-Host "============================================================"

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Error "pyinstaller not found. Run: pip install pyinstaller"
    exit 1
}
$makensis = Get-Command makensis -ErrorAction SilentlyContinue
if (-not $makensis) {
    $candidates = @(
        "$env:ProgramFiles\NSIS\makensis.exe",
        "${env:ProgramFiles(x86)}\NSIS\makensis.exe",
        "$env:ProgramFiles\NSIS\Bin\makensis.exe",
        "${env:ProgramFiles(x86)}\NSIS\Bin\makensis.exe"
    )
    $found = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $found) {
        Write-Error "makensis not found in PATH or Program Files. Install NSIS from https://nsis.sourceforge.io"
        exit 1
    }
    $makensis = $found
    Write-Host "Found NSIS at: $makensis"
} else {
    $makensis = $makensis.Source
}

Write-Host ""
Write-Host "[1/3] Cleaning previous build..."
Remove-Item "$root\build", "$root\dist" -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "[2/3] Building executables with PyInstaller..."
Push-Location $root
pyinstaller installer\tt2s.spec --noconfirm
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    Write-Error "PyInstaller failed."
    exit 1
}
Pop-Location

Write-Host ""
Write-Host "[3/3] Building installer with NSIS..."
& $makensis "$PSScriptRoot\tt2s.nsis"
if ($LASTEXITCODE -ne 0) {
    Write-Error "makensis failed."
    exit 1
}

Write-Host ""
Write-Host "============================================================"
Write-Host " Done.  Installer: $root\dist\tdibam_t2s-1.0.0-setup.exe"
Write-Host "============================================================"
