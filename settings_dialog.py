"""Settings Dialog for H266VideoConverter"""
import flet as ft
from language_manager import LanguageManager

try:
    from flet import icons
except (ImportError, AttributeError):
    icons = None


class SettingsDialog:
    """Settings dialog with language selection"""
    
    def __init__(self, page: ft.Page, language_manager: LanguageManager):
        self.page = page
        self.lang_manager = language_manager
        self.bottom_sheet = None
        self.language_dropdown_ref = ft.Ref[ft.Dropdown]()
    
    def _get_text(self, key: str) -> str:
        """Get translated text"""
        return self.lang_manager.get_text(key)
    
    def _on_language_change(self, e):
        """Handle language change"""
        new_language = self.language_dropdown_ref.current.value
        self.lang_manager.set_language(new_language)
    
    def _close_dialog(self, e):
        """Close the settings dialog"""
        if self.bottom_sheet:
            self.bottom_sheet.open = False
            self.page.update()
    
    def show(self):
        """Show the settings dialog"""
        try:
            available_languages = self.lang_manager.get_available_languages()
            current_language = self.lang_manager.get_current_language()
            
            language_dropdown = ft.Dropdown(
                ref=self.language_dropdown_ref,
                width=300,
                value=current_language,
                options=[
                    ft.dropdown.Option(key, value) 
                    for key, value in available_languages.items()
                ],
                border_color="#6366f1",
                focused_border_color="#818cf8",
                color="#cdd6f4",
                bgcolor="#1e1e2e",
                on_change=self._on_language_change,
            )
            
            content = ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(
                                    self._get_text("settings"),
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                    color="#cdd6f4",
                                ),
                                ft.Container(expand=True),
                                ft.IconButton(
                                    icon=icons.CLOSE if icons else "close",
                                    icon_color="#cdd6f4",
                                    on_click=self._close_dialog,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Divider(color="#313244", height=20),
                        ft.Text(
                            self._get_text("select_language"),
                            color="#cdd6f4",
                            weight=ft.FontWeight.BOLD,
                            size=16,
                        ),
                        ft.Container(height=10),
                        language_dropdown,
                        ft.Container(height=20),
                    ],
                    spacing=10,
                    tight=True,
                ),
                padding=30,
                bgcolor="#1e1e2e",
                border_radius=ft.border_radius.only(top_left=20, top_right=20),
            )
            
            self.bottom_sheet = ft.BottomSheet(
                content=content,
                open=True,
                bgcolor="#1e1e2e",
            )
            
            self.page.overlay.append(self.bottom_sheet)
            self.page.update()
        except Exception as e:
            print(f"Error showing settings: {e}")
