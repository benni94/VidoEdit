param(
  [string]$Python="python"
)

# Windows app packaging with custom icon using flet pack
# Requirements:
#  - Windows
#  - Python with flet and pillow installed
#  - attachments/vidoedit.png present (will be converted to .ico)
# Usage:
#  PowerShell:
#    ./scripts/build_windows.ps1

$ROOT = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ATTACH = Join-Path $ROOT "attachments"
$PNG = Join-Path $ATTACH "vidoedit.png"
$ICO = Join-Path $ATTACH "vidoedit.ico"

if (!(Test-Path $PNG)) {
  Write-Error "Source icon not found: $PNG"
  exit 1
}

Write-Output "Installing dependencies if missing..."
& $Python -m pip show flet | Out-Null; if ($LASTEXITCODE -ne 0) { & $Python -m pip install flet }
& $Python -m pip show pyinstaller | Out-Null; if ($LASTEXITCODE -ne 0) { & $Python -m pip install pyinstaller }

Write-Output "Generating .ico from PNG..."
& $Python (Join-Path $ROOT "scripts/make_ico.py")
if (!(Test-Path $ICO)) {
  Write-Error "Failed to create ICO: $ICO"
  exit 1
}

Write-Output "Packing Windows app..."
Push-Location $ROOT
& $Python -m flet.cli pack main.py `
  --name "VidoEdit" `
  --icon $ICO
Pop-Location

Write-Output "`nBuild complete. Check the dist/ folder for the installer/exe."
