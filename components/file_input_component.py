"""Reusable File Input Component for video file selection"""
import os
import subprocess
import platform
import queue
from pathlib import Path

import flet as ft

try:
    from flet import icons
except (ImportError, AttributeError):
    icons = None


class FileInputComponent:
    """Reusable component for file and folder selection with queue management"""
    
    def __init__(self, page: ft.Page, language_manager, video_extensions, 
                 on_files_added=None, queue_height=150):
        """
        Initialize the file input component
        
        Args:
            page: Flet page instance
            language_manager: Language manager for translations
            video_extensions: Tuple of allowed video file extensions (e.g., (".mkv", ".mp4"))
            on_files_added: Optional callback function called when files are added
            queue_height: Height of the queue container in pixels
        """
        self.page = page
        self.lang_manager = language_manager
        self.video_extensions = video_extensions
        self.on_files_added = on_files_added
        self.queue_height = queue_height
        
        self.queue_list = ft.Ref[ft.ListView]()
        self._task_queue: "queue.Queue" = queue.Queue()
        
        self.files_picker = ft.FilePicker(on_result=self._on_files_picked)
        self.folder_picker = ft.FilePicker(on_result=self._on_folder_picked)
        page.overlay.append(self.files_picker)
        page.overlay.append(self.folder_picker)
    
    def _c(self, light, dark):
        """Helper to get color based on theme"""
        return dark if self.page.theme_mode == ft.ThemeMode.DARK else light
    
    def build(self) -> tuple[ft.Row, ft.Container]:
        """
        Build and return the file input UI components
        
        Returns:
            Tuple of (buttons_row, queue_container)
        """
        add_buttons = ft.Row(
            [
                ft.ElevatedButton(
                    self.lang_manager.get_text("add_files"),
                    icon=icons.ADD if icons else "add",
                    on_click=self._browse_files,
                    style=ft.ButtonStyle(bgcolor="#6366f1", color="#ffffff"),
                ),
                ft.ElevatedButton(
                    self.lang_manager.get_text("add_folder"),
                    icon=icons.FOLDER_OPEN if icons else "folder_open",
                    on_click=self._browse_folder,
                    style=ft.ButtonStyle(bgcolor="#6366f1", color="#ffffff"),
                ),
                ft.ElevatedButton(
                    self.lang_manager.get_text("clear_queue"),
                    icon=icons.DELETE if icons else "delete",
                    on_click=self.clear_queue,
                    style=ft.ButtonStyle(bgcolor="#ef4444", color="#ffffff"),
                ),
            ],
            spacing=10,
            wrap=True,
        )
        
        queue_container = ft.Container(
            content=ft.ListView(
                ref=self.queue_list,
                spacing=4,
                padding=10,
                auto_scroll=False,
            ),
            border=ft.border.all(1, self._c("#e5e7eb", "#313244")),
            border_radius=8,
            bgcolor=self._c("#f9fafb", "#181825"),
            height=self.queue_height,
        )
        
        return add_buttons, queue_container
    
    def _browse_files(self, e):
        """Open file picker for selecting multiple video files"""
        if platform.system() == "Darwin":
            try:
                ext_list = ', '.join([f'"{ext[1:]}"' for ext in self.video_extensions])
                result = subprocess.run(
                    ["osascript", "-e", f'set theFiles to choose file with prompt "Select video files" of type {{{ext_list}}} with multiple selections allowed', "-e", 'set output to ""', "-e", 'repeat with f in theFiles', "-e", 'set output to output & POSIX path of f & "\n"', "-e", 'end repeat', "-e", 'return output'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0 and result.stdout.strip():
                    added = 0
                    for line in result.stdout.strip().split("\n"):
                        file_path = line.strip()
                        if file_path and file_path.lower().endswith(self.video_extensions):
                            self._add_file_to_queue(file_path)
                            added += 1
                    if added > 0 and self.on_files_added:
                        self.on_files_added(added)
                    self.page.update()
            except Exception as ex:
                print(f"Error browsing files: {ex}")
        else:
            self.files_picker.pick_files(
                allow_multiple=True,
                dialog_title="Add video files",
            )
    
    def _browse_folder(self, e):
        """Open folder picker for selecting a folder containing video files"""
        if platform.system() == "Darwin":
            try:
                result = subprocess.run(
                    ["osascript", "-e", 'POSIX path of (choose folder with prompt "Select folder with videos")'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0 and result.stdout.strip():
                    folder_path = result.stdout.strip().rstrip('/')
                    folder = Path(folder_path)
                    added = 0
                    for p in folder.iterdir():
                        if p.is_file() and p.suffix.lower() in self.video_extensions:
                            self._add_file_to_queue(str(p))
                            added += 1
                    if added > 0 and self.on_files_added:
                        self.on_files_added(added)
                    self.page.update()
            except Exception as ex:
                print(f"Error browsing folder: {ex}")
        else:
            self.folder_picker.get_directory_path(
                dialog_title="Add folder with videos",
            )
    
    def _on_files_picked(self, e: ft.FilePickerResultEvent):
        """Handle files selected from file picker"""
        if not e.files:
            return
        added = 0
        for f in e.files:
            if f.path and f.path.lower().endswith(self.video_extensions):
                self._add_file_to_queue(f.path)
                added += 1
        if added > 0 and self.on_files_added:
            self.on_files_added(added)
        self.page.update()
    
    def _on_folder_picked(self, e: ft.FilePickerResultEvent):
        """Handle folder selected from folder picker"""
        if not e.path:
            return
        folder = Path(e.path)
        added = 0
        try:
            for p in folder.iterdir():
                if p.is_file() and p.suffix.lower() in self.video_extensions:
                    self._add_file_to_queue(str(p))
                    added += 1
        except Exception:
            pass
        if added > 0 and self.on_files_added:
            self.on_files_added(added)
        self.page.update()
    
    def _add_file_to_queue(self, file_path):
        """Add a file to the queue and display it in the list"""
        self._task_queue.put(file_path)
        self.queue_list.current.controls.append(
            ft.Text(Path(file_path).name, size=12, color=self._c("#374151", "#a6adc8"))
        )
    
    def clear_queue(self, e=None):
        """Clear all files from the queue"""
        self._task_queue = queue.Queue()
        self.queue_list.current.controls.clear()
        self.page.update()
    
    def get_queue(self):
        """Get the task queue"""
        return self._task_queue
    
    def queue_size(self):
        """Get the current size of the queue"""
        return self._task_queue.qsize()
    
    def is_empty(self):
        """Check if the queue is empty"""
        return self._task_queue.empty()
