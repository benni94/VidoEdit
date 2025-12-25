param(
  [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$ROOT = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ATTACH = Join-Path $ROOT "attachments"
$PNG = Join-Path $ATTACH "vidoedit.png"
$ICO = Join-Path $ATTACH "vidoedit.ico"

Write-Host "Building VidoEdit for Windows"
Write-Host "Project root: $ROOT"

# -----------------------------
# Ensure Python is installed
# -----------------------------
if (-not (Get-Command $Python -ErrorAction SilentlyContinue)) {
  Write-Host "Python not found. Attempting installation via winget..."

  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Error "winget not available. Install Python manually from https://python.org"
    exit 1
  }

  winget install `
    --id Python.Python.3 `
    --exact `
    --silent `
    --accept-package-agreements `
    --accept-source-agreements

  # Refresh PATH for current session
  $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
              [System.Environment]::GetEnvironmentVariable("Path", "User")

  if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python installation failed."
    exit 1
  }
}

$Python = "python"
Write-Host "Python OK"

# -----------------------------
# Ensure FFmpeg is installed
# -----------------------------
Write-Host "Ensuring FFmpeg is installed..."

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {

  Write-Host "FFmpeg not found. Attempting installation..."
  $installed = $false

  if (Get-Command winget -ErrorAction SilentlyContinue) {
    foreach ($id in @("Gyan.FFmpeg", "BtbN.FFmpeg")) {
      try {
        Write-Host "Trying winget package: $id"
        winget install `
          --id $id `
          --exact `
          --silent `
          --accept-package-agreements `
          --accept-source-agreements

        if ($LASTEXITCODE -eq 0) {
          $installed = $true
          break
        }
      } catch {}
    }
  }

  if (-not $installed -and (Get-Command choco -ErrorAction SilentlyContinue)) {
    choco install ffmpeg -y --no-progress
    if ($LASTEXITCODE -eq 0) { $installed = $true }
  }

  if (-not $installed -or -not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Error "FFmpeg installation failed. Install it manually and re-run."
    exit 1
  }
}

Write-Host "FFmpeg OK"

# -----------------------------
# Install Python dependencies
# -----------------------------
Write-Host "Installing Python dependencies..."

& $Python -m pip show flet *> $null
if ($LASTEXITCODE -ne 0) { & $Python -m pip install flet }

& $Python -m pip show pyinstaller *> $null
if ($LASTEXITCODE -ne 0) { & $Python -m pip install pyinstaller }

& $Python -m pip show pillow *> $null
if ($LASTEXITCODE -ne 0) { & $Python -m pip install pillow }

# -----------------------------
# Generate ICO from PNG
# -----------------------------
if (-not (Test-Path $PNG)) {
  Write-Error "Icon PNG not found: $PNG"
  exit 1
}

Write-Host "Generating ICO from PNG..."
& $Python (Join-Path $ROOT "scripts\make_ico.py")

if (-not (Test-Path $ICO)) {
  Write-Error "ICO generation failed."
  exit 1
}

# -----------------------------
# Build application
# -----------------------------
Write-Host "Packaging Windows app with icon..."

Push-Location $ROOT
& $Python -m flet.cli pack main.py `
  --name "VidoEdit" `
  --icon $ICO
Pop-Location

Write-Host "`nBuild complete."
Write-Host "Check the dist\ folder for the executable."
