#!/usr/bin/env python3
import os
import subprocess
import sys
import platform
import time

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
        page.window_width = 800
        page.window_height = 600
        
        # Variables
        self.folder_path = ft.Ref[ft.TextField]()
        self.codec_dropdown = ft.Ref[ft.Dropdown]()
        self.replace_checkbox = ft.Ref[ft.Checkbox]()
        self.log_column = ft.Ref[ft.Column]()
        self.progress_bar = ft.Ref[ft.ProgressBar]()
        self.progress_text = ft.Ref[ft.Text]()
        self.start_button_ref = ft.Ref[ft.ElevatedButton]()
        
        # Build UI
        self.build_ui()
    
    def build_ui(self):
        # Folder input area
        folder_input_area = ft.Container(
            content=ft.Column([
                ft.Icon(icons.FOLDER_OPEN if icons else "folder_open", size=48, color=colors.BLUE if colors else "blue"),
                ft.Text("Ordner auswählen", size=18, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.TextField(
                        ref=self.folder_path,
                        hint_text="Ordner-Pfad eingeben...",
                        expand=True,
                        text_size=14,
                        border_color=colors.BLUE if colors else "blue"
                    ),
                    ft.ElevatedButton(
                        "Durchsuchen",
                        icon=icons.FOLDER_OPEN if icons else "folder_open",
                        on_click=self.browse_folder,
                        height=50
                    )
                ], width=650, spacing=10),
                ft.Text("Oder Pfad aus Finder kopieren (Rechtsklick → 'Als Pfadname kopieren') und hier einfügen", 
                       size=10, 
                       italic=True,
                       color=colors.ON_SURFACE_VARIANT if colors else "gray")
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            bgcolor=colors.SURFACE_VARIANT if colors else "#f5f5f5",
            border=ft.border.all(2, colors.BLUE if colors else "blue"),
            border_radius=10,
            padding=30,
            alignment=ft.alignment.center
        )
        
        # Codec selection
        codec_row = ft.Row([
            ft.Text("Zielcodec:", width=120),
            ft.Dropdown(
                ref=self.codec_dropdown,
                width=200,
                value="h265",
                options=[
                    ft.dropdown.Option("h265", "H.265 (HEVC)"),
                    ft.dropdown.Option("h264", "H.264 (AVC)")
                ]
            )
        ])
        
        # Replace checkbox
        replace_row = ft.Row([
            ft.Checkbox(
                ref=self.replace_checkbox,
                label="Originaldateien ersetzen",
                value=False
            )
        ])
        
        # Start button
        start_button = ft.ElevatedButton(
            ref=self.start_button_ref,
            text="Start Konvertierung",
            icon=icons.PLAY_ARROW if icons else "play_arrow",
            on_click=self.start_conversion,
            style=ft.ButtonStyle(
                color=colors.WHITE if colors else "white",
                bgcolor=colors.BLUE if colors else "blue"
            )
        )
        
        # Progress section
        progress_section = ft.Column([
            ft.Text(
                ref=self.progress_text,
                value="Bereit",
                size=14,
                weight=ft.FontWeight.BOLD,
                color=colors.BLUE if colors else "blue"
            ),
            ft.ProgressBar(
                ref=self.progress_bar,
                value=0,
                width=700,
                visible=False
            )
        ], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        # Log area
        log_container = ft.Container(
            content=ft.Column(
                ref=self.log_column,
                scroll=ft.ScrollMode.AUTO,
                spacing=5
            ),
            border=ft.border.all(1, colors.OUTLINE if colors else "outline"),
            border_radius=5,
            padding=10,
            height=300,
            bgcolor=colors.SURFACE_VARIANT if colors else "#e0e0e0"
        )
        
        # Add all to page
        self.page.add(
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
            ft.Text("Log:", weight=ft.FontWeight.BOLD),
            log_container
        )
    
    def browse_folder(self, e):
        self.log("Öffne Ordner-Auswahl...", colors.BLUE if colors else "blue")
        try:
            folder_path = None
            
            if platform.system() == "Darwin":  # macOS
                # Use AppleScript for macOS native folder picker
                applescript = '''
                tell application "System Events"
                    activate
                    set folderPath to choose folder with prompt "Ordner auswählen:"
                    return POSIX path of folderPath
                end tell
                '''
                result = subprocess.run(
                    ['osascript', '-e', applescript],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    folder_path = result.stdout.strip()
                    
            elif platform.system() == "Windows":  # Windows
                # Use PowerShell for Windows native folder picker
                powershell_script = '''
                Add-Type -AssemblyName System.Windows.Forms
                $folderBrowser = New-Object System.Windows.Forms.FolderBrowserDialog
                $folderBrowser.Description = "Ordner auswählen"
                $folderBrowser.RootFolder = [System.Environment+SpecialFolder]::MyComputer
                $result = $folderBrowser.ShowDialog()
                if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
                    Write-Output $folderBrowser.SelectedPath
                }
                '''
                result = subprocess.run(
                    ['powershell', '-Command', powershell_script],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    folder_path = result.stdout.strip()
                    
            else:  # Linux or other
                self.log("Bitte Pfad manuell eingeben (Ordner-Dialog nicht verfügbar auf diesem System)", 
                        colors.ORANGE if colors else "orange")
                return
            
            if folder_path:
                self.folder_path.current.value = folder_path
                self.page.update()
                self.log(f"Ordner ausgewählt: {folder_path}", colors.GREEN if colors else "green")
            else:
                self.log("Ordner-Auswahl abgebrochen", colors.ORANGE if colors else "orange")
                
        except subprocess.TimeoutExpired:
            self.log("Ordner-Auswahl Timeout", colors.RED if colors else "red")
        except Exception as ex:
            self.log(f"Fehler: {ex}", colors.RED if colors else "red")
    
    def log(self, message, color=None):
        log_entry = ft.Text(
            message,
            size=12,
            color=color if color else (colors.ON_SURFACE if colors else None)
        )
        self.log_column.current.controls.append(log_entry)
        self.page.update()
    
    def convert_file(self, input_file):
        replace = self.replace_checkbox.current.value
        codec = self.codec_dropdown.current.value
        
        tmp_file = input_file + ".tmp" if replace else os.path.splitext(input_file)[0] + f"_{codec}.mkv"
        vcodec = "libx265" if codec == "h265" else "libx264"
        
        cmd = [
            "ffmpeg", "-i", input_file,
            "-c:v", vcodec,
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "copy",
            "-y", tmp_file
        ]
        
        self.log(f"Konvertiere: {os.path.basename(input_file)}", colors.BLUE if colors else "blue")
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            if replace:
                os.replace(tmp_file, input_file)
                self.log(f"✓ Original ersetzt: {os.path.basename(input_file)}", colors.GREEN if colors else "green")
            else:
                self.log(f"✓ Gespeichert als: {os.path.basename(tmp_file)}", colors.GREEN if colors else "green")
        except subprocess.CalledProcessError as ex:
            self.log(f"✗ Fehler bei: {os.path.basename(input_file)}", colors.RED if colors else "red")
            if replace and os.path.exists(tmp_file):
                os.remove(tmp_file)
        except FileNotFoundError:
            self.log("✗ FFmpeg nicht gefunden! Bitte installiere FFmpeg.", colors.RED if colors else "red")
    
    def start_conversion(self, e):
        folder = self.folder_path.current.value
        
        if not folder or not os.path.isdir(folder):
            self.log("✗ Bitte wähle einen gültigen Ordner aus.", colors.RED if colors else "red")
            return
        
        # Disable UI elements during conversion
        self.start_button_ref.current.disabled = True
        self.folder_path.current.disabled = True
        self.codec_dropdown.current.disabled = True
        self.replace_checkbox.current.disabled = True
        self.page.update()
        
        # Clear log
        self.log_column.current.controls.clear()
        self.log("=== Konvertierung gestartet ===", colors.BLUE if colors else "blue")
        
        # Show progress bar
        self.progress_bar.current.visible = True
        self.progress_bar.current.value = 0
        self.progress_text.current.color = colors.BLUE if colors else "blue"
        self.page.update()
        
        # Collect all video files first
        video_files = []
        for root_dir, dirs, files in os.walk(folder):
            for f in files:
                if f.lower().endswith((".mkv", ".mp4")):
                    video_files.append(os.path.join(root_dir, f))
        
        total_files = len(video_files)
        
        if total_files == 0:
            self.log("Keine Video-Dateien (.mkv, .mp4) gefunden.", colors.ORANGE if colors else "orange")
            self.progress_text.current.value = "Keine Dateien gefunden"
            self.progress_bar.current.visible = False
            self.start_button_ref.current.disabled = False
            self.folder_path.current.disabled = False
            self.codec_dropdown.current.disabled = False
            self.replace_checkbox.current.disabled = False
            self.page.update()
            return
        
        # Convert each file with progress updates
        for index, file_path in enumerate(video_files, 1):
            progress = index / total_files
            self.progress_bar.current.value = progress
            self.progress_text.current.value = f"Konvertiere {index} von {total_files} Dateien..."
            self.page.update()
            
            self.convert_file(file_path)
        
        # Completion
        self.progress_bar.current.value = 1.0
        self.progress_text.current.value = f"✓ Fertig! {total_files} Dateien konvertiert"
        self.progress_text.current.color = colors.GREEN if colors else "green"
        self.log(f"\n=== Konvertierung abgeschlossen! ({total_files} Dateien) ===", colors.GREEN if colors else "green")
        
        # Re-enable UI
        self.start_button_ref.current.disabled = False
        self.folder_path.current.disabled = False
        self.codec_dropdown.current.disabled = False
        self.replace_checkbox.current.disabled = False
        self.page.update()


def main(page: ft.Page):
    app = ConverterApp(page)


if __name__ == "__main__":
    ft.app(target=main)