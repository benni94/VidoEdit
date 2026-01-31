"""Utility functions for subprocess operations"""
import platform


def get_creation_flags():
    """
    Get the appropriate creation flags for subprocess calls on Windows.
    
    Returns:
        int: Creation flags value (0x08000000 for Windows to hide console, 0 for other platforms)
    """
    if platform.system() == "Windows":
        return 0x08000000  # CREATE_NO_WINDOW
    return 0
