"""FFmpeg utilities for finding bundled executables"""
import os
import sys
import platform
from pathlib import Path


def get_ffmpeg_path():
    """Get the path to ffmpeg executable, checking bundled location first"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        bundle_dir = Path(sys._MEIPASS)
        
        # Determine executable name based on platform
        exe_name = "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg"
        ffmpeg_path = bundle_dir / "ffmpeg_bundle" / "bin" / exe_name
        
        if ffmpeg_path.exists():
            return str(ffmpeg_path)
    
    # Check if ffmpeg is in PATH
    return "ffmpeg"


def get_ffprobe_path():
    """Get the path to ffprobe executable, checking bundled location first"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        bundle_dir = Path(sys._MEIPASS)
        
        # Determine executable name based on platform
        exe_name = "ffprobe.exe" if platform.system() == "Windows" else "ffprobe"
        ffprobe_path = bundle_dir / "ffmpeg_bundle" / "bin" / exe_name
        
        if ffprobe_path.exists():
            return str(ffprobe_path)
    
    # Check if ffprobe is in PATH
    return "ffprobe"
