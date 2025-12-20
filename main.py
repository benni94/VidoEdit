#!/usr/bin/env python3
"""
H266VideoConverter - Main Application
A modern, cross-platform desktop application for video conversion and compression.
"""
import subprocess
import sys

# Check if flet is installed, if not ask user to install
try:
    import flet as ft
except ImportError:
    print("=" * 60)
    print("Flet is not installed!")
    print("Flet is required to run this application.")
    print("=" * 60)
    response = input("\nWould you like to install it now? (y/n): ").strip().lower()
    
    if response == 'y':
        print("\nInstalling flet...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "flet"])
            print("\n✓ Flet installed successfully!")
            print("Please run the script again.\n")
        except subprocess.CalledProcessError:
            print("\n✗ Installation failed. Please install manually with:")
            print(f"  {sys.executable} -m pip install flet\n")
        sys.exit(0)
    else:
        print("\nCannot run without flet. Install it with:")
        print(f"  {sys.executable} -m pip install flet\n")
        sys.exit(1)

from tabs import ConvertTab, CompressTab


class H266VideoConverterApp:
    """Main application class that manages all tabs"""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self._setup_page()
        self._init_tabs()
        self._build_ui()
    
    def _setup_page(self):
        """Configure page settings and theme"""
        self.page.title = "H266VideoConverter"
        self.page.padding = 20
        self.page.window.width = 800
        self.page.window.height = 600
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.theme = ft.Theme(
            color_scheme=ft.ColorScheme(
                primary="#6366f1",
                on_primary="#ffffff",
                secondary="#818cf8",
                surface="#1e1e2e",
                on_surface="#cdd6f4",
                background="#11111b",
                on_background="#cdd6f4",
            )
        )
        self.page.bgcolor = "#11111b"
    
    def _init_tabs(self):
        """Initialize all tab instances"""
        self.convert_tab = ConvertTab(self.page)
        self.compress_tab = CompressTab(self.page)
        # Add more tabs here in the future:
        # self.another_tab = AnotherTab(self.page)
    
    def _build_ui(self):
        """Build the main UI with tabs"""
        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=250,
            tabs=[
                ft.Tab(text="Convert", content=self.convert_tab.build()),
                ft.Tab(text="Compress", content=self.compress_tab.build()),
                # Add more tabs here:
                # ft.Tab(text="Another", content=self.another_tab.build()),
            ],
            expand=1,
        )
        
        self.page.add(tabs)
        self.page.update()


def main(page: ft.Page):
    """Entry point for the Flet application"""
    app = H266VideoConverterApp(page)


if __name__ == "__main__":
    ft.app(target=main)
