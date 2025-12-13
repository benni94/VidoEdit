#!/usr/bin/env python3
import os
import subprocess
import sys
import platform
import time
import threading
import re

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

# Import icons and colors - handle different flet versions
try:
    from flet import icons, colors
except (ImportError, AttributeError):
    # Fallback for older versions
    icons = None
    colors = None


class ConverterApp:
    def __init__(self, page: ft.Page):
        self.page = page
        page.title = "H266VideoConverter"
        page.padding = 20
        page.window.width = 800
        page.window.height = 600
        page.theme_mode = ft.ThemeMode.DARK
        page.theme = ft.Theme(
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
        page.bgcolor = "#11111b"
        
        # Variables
        self.folder_path = ft.Ref[ft.TextField]()
        self.codec_dropdown = ft.Ref[ft.Dropdown]()
        self.replace_checkbox = ft.Ref[ft.Checkbox]()
        self.log_column = ft.Ref[ft.Column]()
        self.progress_bar = ft.Ref[ft.ProgressBar]()
        self.progress_text = ft.Ref[ft.Text]()
        self.start_button_ref = ft.Ref[ft.ElevatedButton]()
        self.browse_button_ref = ft.Ref[ft.ElevatedButton]()
        
        # File picker for folder selection
        self.folder_picker = ft.FilePicker(on_result=self.on_folder_picked)
        page.overlay.append(self.folder_picker)
        page.update()
        
        # Build UI
        self.build_ui()
    
    def build_ui(self):
        # Folder input area
        folder_input_area = ft.Container(
            content=ft.Column([
                ft.Icon(icons.FOLDER_OPEN if icons else "folder_open", size=48, color="#6366f1"),
                ft.Text("Ordner auswählen", size=18, weight=ft.FontWeight.BOLD, color="#cdd6f4"),
                ft.Row([
                    ft.TextField(
                        ref=self.folder_path,
                        hint_text="Ordner-Pfad eingeben...",
                        expand=True,
                        text_size=14,
                        border_color="#6366f1",
                        focused_border_color="#818cf8",
                        cursor_color="#6366f1",
                        color="#cdd6f4",
                        hint_style=ft.TextStyle(color="#6c7086")
                    ),
                    ft.ElevatedButton(
                        "Durchsuchen",
                        ref=self.browse_button_ref,
                        icon=icons.FOLDER_OPEN if icons else "folder_open",
                        on_click=self.browse_folder,
                        height=50,
                        style=ft.ButtonStyle(
                            bgcolor="#6366f1",
                            color="#ffffff"
                        )
                    )
                ], width=650, spacing=10),
                ft.Text("Oder Pfad aus Finder kopieren (Rechtsklick → 'Als Pfadname kopieren') und hier einfügen", 
                       size=10, 
                       italic=True,
                       color="#6c7086")
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            bgcolor="#1e1e2e",
            border=ft.border.all(2, "#6366f1"),
            border_radius=10,
            padding=30,
            alignment=ft.alignment.center
        )
        
        # Codec selection
        codec_row = ft.Row([
            ft.Text("Zielcodec:", width=120, color="#cdd6f4"),
            ft.Dropdown(
                ref=self.codec_dropdown,
                width=200,
                value="h265",
                options=[
                    ft.dropdown.Option("h265", "H.265 (HEVC)"),
                    ft.dropdown.Option("h264", "H.264 (AVC)")
                ],
                border_color="#6366f1",
                focused_border_color="#818cf8",
                color="#cdd6f4",
                bgcolor="#1e1e2e"
            )
        ])
        
        # Replace checkbox
        replace_row = ft.Row([
            ft.Checkbox(
                ref=self.replace_checkbox,
                label="Originaldateien ersetzen",
                value=False,
                check_color="#ffffff",
                active_color="#6366f1",
                label_style=ft.TextStyle(color="#cdd6f4")
            )
        ])
        
        # Start button
        start_button = ft.ElevatedButton(
            ref=self.start_button_ref,
            text="Start Konvertierung",
            icon=icons.PLAY_ARROW if icons else "play_arrow",
            on_click=self.start_conversion,
            style=ft.ButtonStyle(
                color="#ffffff",
                bgcolor="#22c55e"
            )
        )
        
        # Progress section
        progress_section = ft.Column([
            ft.Text(
                ref=self.progress_text,
                value="Bereit",
                size=14,
                weight=ft.FontWeight.BOLD,
                color="#6366f1"
            ),
            ft.ProgressBar(
                ref=self.progress_bar,
                value=0,
                width=700,
                visible=False,
                color="#6366f1",
                bgcolor="#313244"
            )
        ], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        # Log area
        log_container = ft.Container(
            content=ft.Column(
                ref=self.log_column,
                scroll=ft.ScrollMode.AUTO,
                spacing=5
            ),
            border=ft.border.all(1, "#313244"),
            border_radius=8,
            padding=15,
            height=200,
            bgcolor="#181825",
            expand=True
        )
        
        # Add all to page with scrollable container
        self.page.add(
            ft.Column(
                [
                    ft.Container(height=10),
                    folder_input_area,
                    ft.Container(height=10),
                    codec_row,
                    ft.Container(height=10),
                    replace_row,
                    ft.Container(height=20),
                    start_button,
                    ft.Container(height=15),
                    progress_section,
                    ft.Container(height=15),
                    ft.Text("Log:", weight=ft.FontWeight.BOLD, color="#cdd6f4"),
                    log_container
                ],
                scroll=ft.ScrollMode.AUTO,
                expand=True
            )
        )
    
    def browse_folder(self, e):
        # Platform-specific folder selection
        if platform.system() == "Darwin":
            # macOS: Use native AppleScript dialog
            try:
                result = subprocess.run(
                    ["osascript", "-e", 'POSIX path of (choose folder with prompt "Video-Ordner auswählen")'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0 and result.stdout.strip():
                    folder_path = result.stdout.strip().rstrip('/')
                    self.folder_path.current.value = folder_path
                    self.page.update()
                    self.log(f"Ordner ausgewählt: {folder_path}", "#22c55e")
                else:
                    self.log("Auswahl abgebrochen", "#f97316")
            except Exception as ex:
                self.log(f"Fehler beim Öffnen des Dialogs: {ex}", "#ef4444")
        else:
            # Windows/Linux: Use Flet FilePicker
            self.folder_picker.get_directory_path(
                dialog_title="Video-Ordner auswählen"
            )
    
    def on_folder_picked(self, e: ft.FilePickerResultEvent):
        # This is only used on Windows/Linux
        if e.path:
            self.folder_path.current.value = e.path
            self.page.update()
            self.log(f"Ordner ausgewählt: {e.path}", "#22c55e")
        else:
            self.log("Auswahl abgebrochen", "#f97316")
    
    def log(self, message, color=None):
        log_entry = ft.Text(
            message,
            size=12,
            color=color if color else "#a6adc8"
        )
        self.log_column.current.controls.append(log_entry)
        self.page.update()
    
    def get_video_duration(self, input_file):
        """Get video duration in seconds using ffprobe"""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                input_file
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except:
            pass
        return None
    
    def parse_ffmpeg_time(self, time_str):
        """Parse FFmpeg time string (HH:MM:SS.ms) to seconds"""
        try:
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        except:
            return 0
    
    def convert_file(self, input_file, file_index, total_files):
        replace = self.replace_checkbox.current.value
        codec = self.codec_dropdown.current.value
        
        tmp_file = input_file + ".tmp" if replace else os.path.splitext(input_file)[0] + f"_{codec}.mkv"
        vcodec = "libx265" if codec == "h265" else "libx264"
        
        # Get video duration for progress calculation
        duration = self.get_video_duration(input_file)
        
        cmd = [
            "ffmpeg", "-i", input_file,
            "-c:v", vcodec,
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "copy",
            "-y", tmp_file
        ]
        
        self.log(f"Konvertiere: {os.path.basename(input_file)}", "#6366f1")
        try:
            # Run FFmpeg with real-time progress parsing
            process = subprocess.Popen(
                cmd,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Parse FFmpeg output for progress
            time_pattern = re.compile(r'time=(\d+:\d+:\d+\.\d+)')
            
            while True:
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break
                
                # Look for time= in FFmpeg output
                match = time_pattern.search(line)
                if match and duration:
                    current_time = self.parse_ffmpeg_time(match.group(1))
                    file_progress = min(current_time / duration, 1.0)
                    
                    # Calculate overall progress: completed files + current file progress
                    overall_progress = ((file_index - 1) + file_progress) / total_files
                    self.progress_bar.current.value = overall_progress
                    
                    # Show percentage for current file
                    percent = int(file_progress * 100)
                    self.progress_text.current.value = f"Datei {file_index}/{total_files}: {os.path.basename(input_file)} ({percent}%)"
                    self.page.update()
            
            # Check if FFmpeg succeeded
            if process.returncode == 0:
                if replace:
                    os.replace(tmp_file, input_file)
                    self.log(f"✓ Original ersetzt: {os.path.basename(input_file)}", "#22c55e")
                else:
                    self.log(f"✓ Gespeichert als: {os.path.basename(tmp_file)}", "#22c55e")
            else:
                self.log(f"✗ Fehler bei: {os.path.basename(input_file)}", "#ef4444")
                if replace and os.path.exists(tmp_file):
                    os.remove(tmp_file)
                    
        except FileNotFoundError:
            self.log("✗ FFmpeg nicht gefunden! Bitte installiere FFmpeg.", "#ef4444")
    
    def start_conversion(self, e):
        folder = self.folder_path.current.value
        
        if not folder or not os.path.isdir(folder):
            self.log("✗ Bitte wähle einen gültigen Ordner aus.", "#ef4444")
            return
        
        # Disable UI elements during conversion
        self.start_button_ref.current.disabled = True
        self.browse_button_ref.current.disabled = True
        self.folder_path.current.disabled = True
        self.codec_dropdown.current.disabled = True
        self.replace_checkbox.current.disabled = True
        self.page.update()
        
        # Clear log
        self.log_column.current.controls.clear()
        self.log("=== Konvertierung gestartet ===", "#6366f1")
        
        # Show progress bar
        self.progress_bar.current.visible = True
        self.progress_bar.current.value = 0
        self.progress_text.current.color = "#6366f1"
        self.page.update()
        
        # Run conversion in a separate thread to keep UI responsive
        threading.Thread(target=self._run_conversion, args=(folder,), daemon=True).start()
    
    def _run_conversion(self, folder):
        # Collect all video files first
        video_files = []
        for root_dir, dirs, files in os.walk(folder):
            for f in files:
                if f.lower().endswith((".mkv", ".mp4")):
                    video_files.append(os.path.join(root_dir, f))
        
        total_files = len(video_files)
        
        if total_files == 0:
            self.log("Keine Video-Dateien (.mkv, .mp4) gefunden.", "#f97316")
            self.progress_text.current.value = "Keine Dateien gefunden"
            self.progress_bar.current.visible = False
            self.start_button_ref.current.disabled = False
            self.browse_button_ref.current.disabled = False
            self.folder_path.current.disabled = False
            self.codec_dropdown.current.disabled = False
            self.replace_checkbox.current.disabled = False
            self.page.update()
            return
        
        # Convert each file with progress updates
        for index, file_path in enumerate(video_files, 1):
            self.convert_file(file_path, index, total_files)
        
        # Completion
        self.progress_bar.current.value = 1.0
        self.progress_text.current.value = f"✓ Fertig! {total_files} Dateien konvertiert"
        self.progress_text.current.color = "#22c55e"
        self.log(f"\n=== Konvertierung abgeschlossen! ({total_files} Dateien) ===", "#22c55e")
        
        # Re-enable UI
        self.start_button_ref.current.disabled = False
        self.browse_button_ref.current.disabled = False
        self.folder_path.current.disabled = False
        self.codec_dropdown.current.disabled = False
        self.replace_checkbox.current.disabled = False
        self.page.update()


def main(page: ft.Page):
    app = ConverterApp(page)


if __name__ == "__main__":
    ft.app(target=main)