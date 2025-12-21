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
from language_manager import LanguageManager
from settings_dialog import SettingsDialog

try:
    from flet import icons
except (ImportError, AttributeError):
    icons = None


class H266VideoConverterApp:
    """Main application class that manages all tabs"""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.lang_manager = LanguageManager()
        self.settings_dialog = SettingsDialog(page, self.lang_manager)
        self.tabs_ref = ft.Ref[ft.Tabs]()
        self._setup_page()
        self._init_tabs()
        self._build_ui()
        self.lang_manager.register_callback(self._on_language_change)
    
    def _setup_page(self):
        """Configure page settings and theme"""
        self.page.title = self.lang_manager.get_text("app_title")
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
        self.convert_tab = ConvertTab(self.page, self.lang_manager)
        self.compress_tab = CompressTab(self.page, self.lang_manager)
        # Add more tabs here in the future:
        # self.another_tab = AnotherTab(self.page)
    
    def _build_ui(self):
        """Build the main UI with tabs"""
        settings_button = ft.IconButton(
            icon=icons.SETTINGS if icons else "settings",
            icon_color="#6366f1",
            tooltip=self.lang_manager.get_text("settings"),
            on_click=self._show_settings,
        )
        
        header = ft.Row(
            [
                ft.Text(
                    self.lang_manager.get_text("app_title"),
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color="#cdd6f4",
                ),
                ft.Container(expand=True),
                settings_button,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        
        tabs = ft.Tabs(
            ref=self.tabs_ref,
            selected_index=0,
            animation_duration=250,
            tabs=[
                ft.Tab(text=self.lang_manager.get_text("tab_convert"), content=self.convert_tab.build()),
                ft.Tab(text=self.lang_manager.get_text("tab_compress"), content=self.compress_tab.build()),
            ],
            expand=1,
        )
        
        self.page.add(header)
        self.page.add(tabs)
        self.page.update()
    
    def _show_settings(self, e):
        """Show settings dialog"""
        try:
            self.settings_dialog.show()
        except Exception as ex:
            print(f"Error showing settings: {ex}")
    
    def _on_language_change(self):
        """Handle language change - rebuild UI"""
        if hasattr(self.page, 'dialog') and self.page.dialog:
            self.page.dialog.open = False
        
        self.page.controls.clear()
        self.page.title = self.lang_manager.get_text("app_title")
        
        self.settings_dialog = SettingsDialog(self.page, self.lang_manager)
        
        self._build_ui()


def main(page: ft.Page):
    """Entry point for the Flet application"""
    app = H266VideoConverterApp(page)


if __name__ == "__main__":
    ft.app(target=main)
