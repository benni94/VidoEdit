# VidoEdit Build Instructions

All build scripts automatically bundle FFmpeg and all required dependencies into standalone executables.

## Prerequisites

### Python Environment Setup

Before building, ensure you have the correct Python environment set up:

1. **Python Version**: Python 3.13 or compatible version
2. **Install Dependencies**: Use the provided `requirements.txt` to install exact package versions

   ```bash
   # Create a virtual environment (recommended)
   python -m venv venv

   # Activate the virtual environment
   # Windows:
   .\venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate

   # Install all dependencies with pinned versions
   pip install -r requirements.txt
   ```

3. **Key Dependencies**:
   - `flet==0.28.3` - UI framework
   - `pyinstaller==6.17.0` - Executable builder
   - `pillow==12.0.0` - Image processing
   - All other dependencies are listed in `requirements.txt`

### Running from Source (Development)

To run the application without building:

```bash
# With terminal (for debugging)
python main.py

# Without terminal window (Windows only)
pythonw VidoEdit.pyw
```

---

## What's Included in All Builds

- ✅ **FFmpeg and FFprobe** - Automatically downloaded and bundled
- ✅ **All Python dependencies** (Flet, etc.)
- ✅ **Application assets and translations**
- ✅ **All application code and tabs**

---

## Windows Build

### How to Build

1. **Run the build script:**

   ```powershell
   .\scripts\build_windows.ps1
   ```

2. **What the script does:**

   - Checks for Python installation (installs via winget if needed)
   - Downloads FFmpeg essentials build (~100MB) if not already present
   - Extracts FFmpeg and FFprobe to `ffmpeg_bundle/bin/`
   - Installs Python dependencies (flet, pyinstaller, pillow)
   - Generates application icon from PNG
   - Packages everything into a single `.exe` file

3. **Output:**
   - Standalone executable: `dist\VidoEdit.exe`

### FFmpeg Source

- https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip

---

## Linux Build

### How to Build

1. **Make the script executable:**

   ```bash
   chmod +x scripts/build_linux.sh
   ```

2. **Run the build script:**

   ```bash
   ./scripts/build_linux.sh
   ```

3. **What the script does:**

   - Checks for Python installation (installs via package manager if needed)
   - Downloads FFmpeg static build (~100MB) if not already present
   - Extracts FFmpeg and FFprobe to `ffmpeg_bundle/bin/`
   - Installs Python dependencies (flet)
   - Packages everything into an AppImage

4. **Output:**
   - Standalone AppImage: `dist/VidoEdit.AppImage`
   - Users may need to make it executable: `chmod +x VidoEdit.AppImage`

### FFmpeg Source

- https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz

---

## macOS Build

### How to Build

1. **Make the script executable:**

   ```bash
   chmod +x scripts/build_macos.sh
   ```

2. **Run the build script:**

   ```bash
   ./scripts/build_macos.sh
   ```

3. **What the script does:**

   - Checks for Python installation (installs via Homebrew if needed)
   - Downloads FFmpeg for macOS (supports Intel and Apple Silicon)
   - Extracts FFmpeg and FFprobe to `ffmpeg_bundle/bin/`
   - Generates .icns icon from PNG
   - Installs Python dependencies (flet)
   - Packages everything into a .app bundle

4. **Output:**
   - Standalone app bundle: `dist/VidoEdit.app`

### FFmpeg Source

- https://evermeet.cx/ffmpeg/
- Automatically detects architecture (x86_64 or arm64)

---

### Technical Details

### FFmpeg Bundling

- FFmpeg is downloaded automatically during the first build
- Stored locally in: `ffmpeg_bundle/bin/`
- Bundled into the executable at build time
- The application automatically detects if it's running as a standalone executable and uses the bundled FFmpeg
- Platform-specific executables are used (`.exe` on Windows, no extension on Linux/macOS)

### Code Changes

The following files were modified to support bundled FFmpeg:

1. **`ffmpeg_utils.py`** (new file)

   - Provides `get_ffmpeg_path()` and `get_ffprobe_path()` functions
   - Automatically detects if running as standalone executable
   - Handles platform-specific executable names (Windows vs Linux/macOS)
   - Returns bundled paths when frozen, system paths otherwise

2. **`tabs/convert_tab.py`**

   - Updated to use `get_ffmpeg_path()` and `get_ffprobe_path()`

3. **`tabs/compress_tab.py`**

   - Updated to use `get_ffmpeg_path()` and `get_ffprobe_path()`

4. **`tabs/merge_tab.py`**

   - Updated to use `get_ffmpeg_path()`

5. **Build Scripts**
   - `scripts/build_windows.ps1` - Downloads and bundles FFmpeg for Windows
   - `scripts/build_linux.sh` - Downloads and bundles FFmpeg for Linux
   - `scripts/build_macos.sh` - Downloads and bundles FFmpeg for macOS
   - All use `flet pack` with `--add-binary` flags

## Distribution

The generated executables are fully standalone:

- **Windows**: `VidoEdit.exe` - Single executable file
- **Linux**: `VidoEdit.AppImage` - Single AppImage file
- **macOS**: `VidoEdit.app` - App bundle

All builds include:

- No Python installation required
- No FFmpeg installation required
- No additional dependencies needed
- Users can simply download and run

## Notes

- The `ffmpeg_bundle/` directory is automatically created during build and is excluded from git
- FFmpeg is only downloaded once - subsequent builds reuse the cached version
- The build process requires an internet connection for the first build (to download FFmpeg)
- All platforms use the same `ffmpeg_utils.py` module for cross-platform compatibility
