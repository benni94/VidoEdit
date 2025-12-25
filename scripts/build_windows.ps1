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
# Download and bundle FFmpeg
# -----------------------------
Write-Host "Preparing FFmpeg for bundling..."

$FFMPEG_BUNDLE = Join-Path $ROOT "ffmpeg_bundle"
$FFMPEG_BIN = Join-Path $FFMPEG_BUNDLE "bin"
$FFMPEG_EXE = Join-Path $FFMPEG_BIN "ffmpeg.exe"
$FFPROBE_EXE = Join-Path $FFMPEG_BIN "ffprobe.exe"

if (-not (Test-Path $FFMPEG_EXE) -or -not (Test-Path $FFPROBE_EXE)) {
  Write-Host "Downloading FFmpeg for bundling..."
  
  $tempDir = Join-Path $env:TEMP "ffmpeg_download_$(Get-Random)"
  New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
  
  $ffmpegUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
  $zipPath = Join-Path $tempDir "ffmpeg.zip"
  
  try {
    Write-Host "Downloading from: $ffmpegUrl"
    Invoke-WebRequest -Uri $ffmpegUrl -OutFile $zipPath -UseBasicParsing
    
    Write-Host "Extracting FFmpeg..."
    Expand-Archive -Path $zipPath -DestinationPath $tempDir -Force
    
    $extractedFolder = Get-ChildItem -Path $tempDir -Directory | Where-Object { $_.Name -like "ffmpeg-*" } | Select-Object -First 1
    
    if ($extractedFolder) {
      New-Item -ItemType Directory -Force -Path $FFMPEG_BUNDLE | Out-Null
      Copy-Item -Path (Join-Path $extractedFolder.FullName "bin") -Destination $FFMPEG_BUNDLE -Recurse -Force
      Write-Host "FFmpeg extracted to: $FFMPEG_BIN"
    } else {
      throw "Could not find extracted FFmpeg folder"
    }
    
    Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
  } catch {
    Write-Error "Failed to download FFmpeg: $_"
    Write-Host "Please download FFmpeg manually from https://ffmpeg.org/download.html"
    Write-Host "Extract and place ffmpeg.exe and ffprobe.exe in: $FFMPEG_BIN"
    exit 1
  }
}

Write-Host "FFmpeg ready for bundling: $FFMPEG_EXE"

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
# Build application with bundled FFmpeg
# -----------------------------
Write-Host "Packaging Windows app with icon and FFmpeg..."

Push-Location $ROOT
& $Python -m flet.cli pack main.py `
  --name "VidoEdit" `
  --icon $ICO `
  --add-binary "$FFMPEG_EXE;ffmpeg_bundle/bin" `
  --add-binary "$FFPROBE_EXE;ffmpeg_bundle/bin"
Pop-Location

Write-Host "`n========================================="
Write-Host "Build complete!" -ForegroundColor Green
Write-Host "========================================="
Write-Host "Executable location: $ROOT\dist\VidoEdit.exe"
Write-Host "`nThe executable is fully standalone and includes:"
Write-Host "  ✓ FFmpeg and FFprobe" -ForegroundColor Green
Write-Host "  ✓ All Python dependencies" -ForegroundColor Green
Write-Host "  ✓ Application assets and translations" -ForegroundColor Green
Write-Host "`nYou can distribute this .exe file to users without any additional dependencies."
