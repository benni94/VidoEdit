#!/usr/bin/env python3
"""
VidoEdit - Main Application
A modern, cross-platform desktop application for video conversion and compression.
"""
import subprocess
import sys
from pathlib import Path

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

from tabs import ConvertTab, CompressTab, MergeTab, RenamerTab, AudioTab
from language_manager import LanguageManager
from settings_dialog import SettingsDialog

try:
    from flet import icons
except (ImportError, AttributeError):
    icons = None


class VidoEditApp:
    """Main application class that manages all tabs"""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.lang_manager = LanguageManager()
        self.settings_dialog = SettingsDialog(page, self.lang_manager)
        self.tabs_ref = ft.Ref[ft.Tabs]()
        self.show_tab_labels = True
        self._setup_page()
        self._init_tabs()
        self._build_ui()
        self.lang_manager.register_callback(self._on_language_change)
        self.page.on_resized = self._on_window_resize
    
    def _setup_page(self):
        """Configure page settings and theme"""
        self.page.title = self.lang_manager.get_text("app_title")
        self.page.padding = 20
        self.page.window.width = 800
        self.page.window.height = 600
        try:
            # Use app assets for cross-platform icon resolution
            icon_asset = "vidoedit.png"
            assets_dir = Path(__file__).parent / "attachments"
            if (assets_dir / icon_asset).exists():
                # When assets_dir is provided to ft.app, set window icon by asset name
                self.page.window.icon = icon_asset
        except Exception:
            pass
        
        # Load saved theme mode
        saved_theme = self.lang_manager.get_theme_mode()
        self.page.theme_mode = ft.ThemeMode.DARK if saved_theme == "dark" else ft.ThemeMode.LIGHT
        
        # Use different color schemes for dark vs light so text contrast is appropriate
        if self.page.theme_mode == ft.ThemeMode.DARK:
            color_scheme = ft.ColorScheme(
                primary="#6366f1",
                on_primary="#ffffff",
                secondary="#8da2fb",
                surface="#16161c",
                on_surface="#eeeeee",
                on_surface_variant="#ffffff",
                background="#11111b",
                on_background="#e5e5e5",
            )
            self.page.bgcolor = "#11111b"
        else:
            color_scheme = ft.ColorScheme(
                primary="#6366f1",
                on_primary="#ffffff",
                secondary="#818cf8",
                surface="#ffffff",
                on_surface="#1e1e2e",
                on_surface_variant="#1e1e2e",
                background="#ffffff",
                on_background="#1e1e2e",
            )
            self.page.bgcolor = "#ffffff"
        
        self.page.theme = ft.Theme(color_scheme=color_scheme)
    
    def _init_tabs(self):
        """Initialize all tab instances"""
        self.convert_tab = ConvertTab(self.page, self.lang_manager)
        self.compress_tab = CompressTab(self.page, self.lang_manager)
        # Add more tabs here in the future:
        self.audio_tab = AudioTab(self.page, self.lang_manager)
        self.merge_tab = MergeTab(self.page, self.lang_manager)
        self.renamer_tab = RenamerTab(self.page, self.lang_manager)
    
    def _build_ui(self, selected_index: int = 0):
        """Build the main UI with tabs
        selected_index: which tab should be active after rebuild
        """
        is_dark = self.page.theme_mode == ft.ThemeMode.DARK
        
        theme_button = ft.IconButton(
            icon=icons.DARK_MODE if icons and is_dark else icons.LIGHT_MODE if icons else "light_mode",
            icon_color="#6366f1",
            tooltip=self.lang_manager.get_text("theme_light" if is_dark else "theme_dark"),
            on_click=self._toggle_theme,
        )
        
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
                    color="#cdd6f4" if is_dark else "#1e1e2e",
                ),
                ft.Container(expand=True),
                theme_button,
                settings_button,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        
        # Create tabs with icons
        tab_list = [
            ft.Tab(
                icon=icons.COMPRESS if icons else "compress",
                text=self.lang_manager.get_text("tab_compress") if self.show_tab_labels else None,
                content=self.compress_tab.build()
            ),
            ft.Tab(
                icon=icons.TRANSFORM if icons else "transform",
                text=self.lang_manager.get_text("tab_convert") if self.show_tab_labels else None,
                content=self.convert_tab.build()
            ),
            ft.Tab(
                icon=icons.AUDIOTRACK if icons else "audiotrack",
                text=self.lang_manager.get_text("tab_audio") if self.show_tab_labels else None,
                content=self.audio_tab.build()
            ),
            ft.Tab(
                icon=icons.MERGE if icons else "merge",
                text=self.lang_manager.get_text("merge_videos") if self.show_tab_labels and hasattr(self.lang_manager, 'get_text') else ("Merge Videos" if self.show_tab_labels else None),
                content=self.merge_tab.build()
            ),
            ft.Tab(
                icon=icons.DRIVE_FILE_RENAME_OUTLINE if icons else "drive_file_rename_outline",
                text=self.lang_manager.get_text("renamer") if self.show_tab_labels and hasattr(self.lang_manager, 'get_text') else ("Renamer" if self.show_tab_labels else None),
                content=self.renamer_tab.build()
            ),
        ]
        
        tabs = ft.Tabs(
            ref=self.tabs_ref,
            selected_index=selected_index,
            animation_duration=250,
            label_color="#ffffff" if is_dark else "#1e1e2e",
            unselected_label_color="#ffffff" if is_dark else "#1e1e2e",
            tabs=tab_list,
            scrollable=True,
            expand=1,
        )
        
        self.page.add(header)
        self.page.add(tabs)
        self.page.update()
    
    def _toggle_theme(self, e):
        """Toggle between dark and light theme"""
        current_index = 0
        try:
            if self.tabs_ref.current is not None:
                current_index = int(self.tabs_ref.current.selected_index or 0)
        except Exception:
            current_index = 0
        
        if self.page.theme_mode == ft.ThemeMode.DARK:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.page.bgcolor = "#ffffff"
            self.lang_manager.set_theme_mode("light")
            # Update color scheme for light mode
            self.page.theme = ft.Theme(
                color_scheme=ft.ColorScheme(
                    primary="#6366f1",
                    on_primary="#ffffff",
                    secondary="#818cf8",
                    surface="#ffffff",
                    on_surface="#1e1e2e",
                    on_surface_variant="#1e1e2e",
                    background="#ffffff",
                    on_background="#1e1e2e",
                )
            )
        else:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.page.bgcolor = "#11111b"
            self.lang_manager.set_theme_mode("dark")
            # Update color scheme for dark mode
            self.page.theme = ft.Theme(
                color_scheme=ft.ColorScheme(
                    primary="#6366f1",
                    on_primary="#ffffff",
                    secondary="#8da2fb",
                    surface="#16161c",
                    on_surface="#eeeeee",
                    on_surface_variant="#ffffff",
                    background="#11111b",
                    on_background="#e5e5e5",
                )
            )
        
        # Rebuild UI to update colors and icons
        self.page.controls.clear()
        self._build_ui(selected_index=current_index)
    
    def _show_settings(self, e):
        """Show settings dialog"""
        try:
            self.settings_dialog.show()
        except Exception as ex:
            print(f"Error showing settings: {ex}")
    
    def _on_language_change(self):
        """Handle language change - rebuild UI"""
        current_index = 0
        try:
            if self.tabs_ref.current is not None:
                current_index = int(self.tabs_ref.current.selected_index or 0)
        except Exception:
            current_index = 0
        
        if hasattr(self.page, 'dialog') and self.page.dialog:
            self.page.dialog.open = False
        
        self.page.controls.clear()
        self.page.title = self.lang_manager.get_text("app_title")
        
        self.settings_dialog = SettingsDialog(self.page, self.lang_manager)
        
        self._build_ui(selected_index=current_index)
    
    def _on_window_resize(self, e):
        """Handle window resize to show/hide tab labels"""
        try:
            # Get current window width
            window_width = self.page.window.width or 800
            
            # Threshold for showing labels (adjust as needed)
            # Below 600px width, show only icons
            should_show_labels = window_width >= 600
            
            # Only rebuild if the state changed
            if should_show_labels != self.show_tab_labels:
                self.show_tab_labels = should_show_labels
                current_index = 0
                try:
                    if self.tabs_ref.current is not None:
                        current_index = int(self.tabs_ref.current.selected_index or 0)
                except Exception:
                    current_index = 0
                
                self.page.controls.clear()
                self._build_ui(selected_index=current_index)
        except Exception:
            pass


def main(page: ft.Page):
    """Entry point for the Flet application"""
    app = VidoEditApp(page)


if __name__ == "__main__":
    # Serve attachments folder as app assets so window icon can be referenced by name
    assets = str((Path(__file__).parent / "attachments").resolve())
    ft.app(target=main, assets_dir=assets)
