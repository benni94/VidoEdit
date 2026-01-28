# VidoEdit

VidoEdit is a modern, cross-platform desktop application for video editing tasks including converting H.266/VVC video files to H.265 (HEVC) or H.264 (AVC), compressing videos with GPU acceleration, managing audio tracks, merging episode parts, and batch-renaming files.

![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-blue)
![Python](https://img.shields.io/badge/python-3.13+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## Download current Releas

https://github.com/benni94/VidoEdit/releases/tag/v1.1.0

## Features

✨ **Modern GUI** - Clean, intuitive interface built with Flet  
🎯 **Batch Processing** - Process entire folders of videos at once  
📊 **Real-time Progress** - Visual progress bar and detailed logging  
🔄 **Multiple Codecs** - Support for H.265 (HEVC) and H.264 (AVC)  
🎵 **Audio Track Management** - Detect, select, and remove audio tracks from videos  
🗜️ **GPU-Accelerated Compression** - Fast video compression with NVIDIA/AMD/Intel hardware encoding  
💾 **Flexible Output** - All processed files saved to 'edited' subfolder  
🌍 **Cross-platform** - Works on macOS, Windows, and Linux  
🎨 **Native Dialogs** - Platform-native file picker dialogs  
🔀 **Video Merging** - Combine multiple video parts into one file  
📝 **Batch Renaming** - Rename multiple files with pattern matching

## Screenshots

![VidoEdit Interface](screenshot.png)

## Requirements

- Python 3.13 or higher (important for Flet)
- FFmpeg

Note: The provided build scripts for Windows, macOS, and Linux will attempt to auto-install FFmpeg (and Python where applicable) using the system package manager if they are not already present. You can still install FFmpeg manually if you prefer.

## Installation

### 1. Install FFmpeg (optional if using build scripts)

The build scripts attempt to auto-install FFmpeg. If you want to install it manually:

- macOS (Homebrew): `brew install ffmpeg`
- Windows (winget): `winget install -e --id FFmpeg.FFmpeg --accept-package-agreements --accept-source-agreements`
- Windows (Chocolatey): `choco install ffmpeg -y`
- Linux (Debian/Ubuntu): `sudo apt update && sudo apt install -y ffmpeg`

### 2. Clone the Repository

```bash
git clone https://github.com/benni94/VidoEdit.git
cd VidoEdit
```

### 3. Create Virtual Environment (Recommended)

```bash
python3.13 -m venv venv
source venv/bin/activate  # macOS/Linux
# or on Windows: venv\Scripts\activate
pip install flet
```

### 4. Run the Application

```bash
python main.py
```

On first run, the application will automatically prompt you to install Flet if it's not already installed.

## Usage

### Compress Tab

Compress videos with GPU-accelerated encoding (HEVC/H.265):

1. Add files or folders to the queue
2. Select compression mode (CRF or Target Size)
3. Choose quality preset
4. Click START to begin processing

### Convert Tab

Convert H.266/VVC videos to H.265 or H.264:

1. Select folder containing videos
2. Choose output codec (H.265 or H.264)
3. Optionally replace original files
4. Click START to begin conversion

### Audio Tracks Tab

Manage audio tracks in your videos:

1. **Add Files** - Click "Add Files" or "Add Folder" to queue videos
2. **Detect Tracks** - Click "Detect Audio Tracks" to analyze the first file
3. **Select Tracks** - Use checkboxes to select which audio tracks to keep
   - Use "Select/Deselect All" to quickly toggle all tracks
   - All tracks are selected by default
4. **Process Queue** - Click "Process All Files in Queue" to apply your selection to all files
5. **Output** - Processed files are saved to an `edited` subfolder with original filenames

### Merge Videos Tab

Combine multiple video parts into one file:

1. Add video files to merge
2. Arrange them in the desired order
3. Click START to merge

### Renamer Tab

Batch rename files with pattern matching:

1. Select folder with files to rename
2. Configure identifier regex and naming pattern
3. Preview changes
4. Apply renaming

## Supported Formats

**Input:** `.mkv`, `.mp4` (H.266/VVC encoded)  
**Output:** `.mkv` (H.265 or H.264 encoded)

## Configuration

The converter uses the following FFmpeg settings:

- **Preset:** medium (balance between speed and quality)
- **CRF:** 23 (constant rate factor for quality)
- **Audio:** copy (no re-encoding)

## Technical Details

### Architecture

- **GUI Framework:** Flet (Flutter-based Python framework)
- **Video Processing:** FFmpeg via subprocess
- **Platform Detection:** Automatic OS detection for native dialogs

### File Structure

```
VidoEdit/
├── main.py                 # Main entry point
├── tabs/
│   ├── __init__.py         # Package exports
│   ├── compress_tab.py     # GPU-accelerated compression
│   ├── convert_tab.py      # H.266 to H.265/H.264 conversion
│   ├── audio_tab.py        # Audio track management
│   ├── merge_tab.py        # Merge episode parts (UI + logic)
│   └── renamer_tab.py      # Multi-file renamer (UI + logic)
├── attachments/
│   └── vidoedit.png        # App icon (source image)
├── scripts/
│   ├── build_macos.sh      # Build macOS .app with custom icon (.icns)
│   ├── build_linux.sh      # Build Linux AppImage with icon (PNG)
│   ├── build_windows.ps1   # Build Windows app with icon (.ico)
│   └── make_ico.py         # Helper: PNG → ICO (Windows)
├── language_manager.py     # Multi-language support (EN/DE)
├── translations.py         # Translation strings
├── ffmpeg_utils.py         # FFmpeg/FFprobe path utilities
├── README.md               # This file
└── requirements.txt        # Python dependencies
```

## Troubleshooting

### "FFmpeg nicht gefunden"

- Ensure FFmpeg is installed and available in your system PATH
- Test by running `ffmpeg -version` in terminal

### Folder picker doesn't open

- On macOS: AppleScript is used (built-in)
- On Windows: PowerShell is used (built-in)
- On Linux: Manually paste folder path

### Conversion fails

- Check that input files are valid video files
- Ensure you have write permissions in the target folder
- Check FFmpeg logs in the application log area

## Development

### Dependencies

```bash
pip install flet
```

### Running from Source

```bash
source venv/bin/activate
python main.py
```

### Building Standalone Executable (with custom icon)

#### Getting started: build matrix

| OS      | Prereqs                                                                         | Command                       | Icon file used                          | Output              |
| ------- | ------------------------------------------------------------------------------- | ----------------------------- | --------------------------------------- | ------------------- |
| macOS   | Xcode CLT (iconutil, sips). Script ensures Python/FFmpeg via Homebrew if needed | `scripts/build_macos.sh`      | `attachments/vidoedit.icns` (generated) | `dist/VidoEdit.app` |
| Windows | Script ensures Python via winget and FFmpeg via winget/Chocolatey if needed     | `./scripts/build_windows.ps1` | `attachments/vidoedit.ico` (generated)  | `dist/` executable  |
| Linux   | Script attempts FFmpeg install via common package managers                      | `scripts/build_linux.sh`      | `attachments/vidoedit.png`              | `dist/` AppImage    |

#### macOS (Flet pack)

The Dock icon on macOS is taken from the app bundle and won’t change at runtime. Use the provided script to embed the icon and create a .app:

```bash
chmod +x scripts/build_macos.sh
scripts/build_macos.sh
```

Output: `dist/VidoEdit.app` with your custom icon.

#### Windows (Flet pack)

Use the PowerShell script to convert the PNG to ICO and pack the app:

```powershell
./scripts/build_windows.ps1
```

Output: look in `dist/` for the executable with your icon.

#### Linux (Flet pack)

```bash
chmod +x scripts/build_linux.sh
scripts/build_linux.sh
```

Output: `dist/` folder with an AppImage using your PNG icon.

### Development icon during `python main.py`

- The app serves `attachments/` as `assets_dir` and sets `page.window.icon = "vidoedit.png"`.
- On Windows/Linux this affects the window/title icon.
- On macOS the Dock icon comes from the bundled .icns; use the macOS build script to see it in the Dock.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Roadmap

- [x] Multi-language support (English/German)
- [x] Dark/Light theme toggle
- [x] Audio track management
- [x] GPU-accelerated compression
- [x] Batch processing with queue system
- [ ] Add drag-and-drop support
- [ ] Support for more input/output formats
- [ ] Custom FFmpeg parameter configuration
- [ ] Conversion presets (quality/speed profiles)
- [ ] Video preview before conversion

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Flet](https://flet.dev/) - Flutter for Python
- Video processing powered by [FFmpeg](https://ffmpeg.org/)
- Icons from [Material Design Icons](https://fonts.google.com/icons)

## Author

**Benjamin Fink**

- GitHub: [@benni94](https://github.com/benni94)

## Support

If you encounter any issues or have questions, please [open an issue](https://github.com/benni94/VidoEdit/issues) on GitHub.

---

⭐ If you find this project useful, please consider giving it a star!
