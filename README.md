# H266VideoConverter

A modern, cross-platform desktop application for converting H.266/VVC video files to H.265 (HEVC) or H.264 (AVC) formats.

![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-blue)
![Python](https://img.shields.io/badge/python-3.13+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## Features

✨ **Modern GUI** - Clean, intuitive interface built with Flet  
🎯 **Batch Processing** - Convert entire folders of videos at once  
📊 **Real-time Progress** - Visual progress bar and detailed logging  
🔄 **Multiple Codecs** - Support for H.265 (HEVC) and H.264 (AVC)  
💾 **Flexible Output** - Replace originals or create new files  
🌍 **Cross-platform** - Works on macOS, Windows, and Linux  
🎨 **Native Dialogs** - Platform-native folder picker dialogs

## Screenshots

![H266VideoConverter Interface](screenshot.png)

## Requirements

- Python 3.13 or higher (important for Flet)
- FFmpeg (must be installed and available in PATH)

## Installation

### 1. Install FFmpeg

**macOS (using Homebrew):**

```bash
brew install ffmpeg
```

**Windows (using Chocolatey):**

```bash
choco install ffmpeg
```

**Windows (manual):**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH

**Linux (Ubuntu/Debian):**

```bash
sudo apt update
sudo apt install ffmpeg
```

### 2. Clone the Repository

```bash
git clone https://github.com/yourusername/H266VideoConverter.git
cd H266VideoConverter
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

1. **Select Folder**

   - Click "Durchsuchen" to open a folder picker
   - Or manually paste the folder path into the text field
   - On macOS: Right-click folder → Hold Option → "Copy as Pathname"

2. **Choose Codec**

   - Select H.265 (HEVC) for better compression
   - Select H.264 (AVC) for wider compatibility

3. **Optional Settings**

   - Check "Originaldateien ersetzen" to replace original files
   - Leave unchecked to create new files with codec suffix

4. **Start Conversion**
   - Click "Start Konvertierung"
   - Monitor progress in real-time
   - View detailed logs for each file

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
H266VideoConverter/
├── main.py              # Main entry point
├── tabs/
│   ├── __init__.py      # Package exports
│   ├── convert_tab.py   # H.266 to H.265/H.264 conversion
│   └── compress_tab.py  # GPU-accelerated compression
├── README.md            # This file
└── requirements.txt     # Python dependencies
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

### Building Standalone Executable

#### macOS

1. **Install PyInstaller:**
   ```bash
   pip install pyinstaller
   ```

2. **Build the app:**
   ```bash
   pyinstaller --onefile --windowed --name H266VideoConverter main.py
   ```

3. **Or use Flet's built-in packaging:**
   ```bash
   flet pack main.py --name H266VideoConverter --icon icon.icns
   ```

4. **Find your executable:**
   - PyInstaller: `dist/H266VideoConverter.app`
   - Flet pack: `dist/H266VideoConverter.app`

#### Windows

1. **Install PyInstaller:**
   ```bash
   pip install pyinstaller
   ```

2. **Build the exe:**
   ```bash
   pyinstaller --onefile --windowed --name H266VideoConverter main.py
   ```

3. **Find your executable:** `dist\H266VideoConverter.exe`

#### Linux

```bash
pip install pyinstaller
pyinstaller --onefile --name H266VideoConverter main.py
```

The executable will be in `dist/H266VideoConverter`.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Roadmap

- [ ] Add drag-and-drop support
- [ ] Support for more input/output formats
- [ ] Custom FFmpeg parameter configuration
- [ ] Multi-language support
- [ ] Dark/Light theme toggle
- [ ] Conversion presets (quality/speed profiles)
- [ ] Video preview before conversion

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Flet](https://flet.dev/) - Flutter for Python
- Video processing powered by [FFmpeg](https://ffmpeg.org/)
- Icons from [Material Design Icons](https://fonts.google.com/icons)

## Author

**Your Name**

- GitHub: [@benni94](https://github.com/benni94)

## Support

If you encounter any issues or have questions, please [open an issue](https://github.com/benni94/H266VideoConverter/issues) on GitHub.

---

⭐ If you find this project useful, please consider giving it a star!
