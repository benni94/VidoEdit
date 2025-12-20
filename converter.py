#!/usr/bin/env python3
import os
import subprocess
import sys
import platform
import time
import threading
import re
import queue
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

        self.compress_queue_list = ft.Ref[ft.ListView]()
        self.compress_mode_radio = ft.Ref[ft.RadioGroup]()
        self.compress_preset_dropdown = ft.Ref[ft.Dropdown]()
        self.compress_target_size = ft.Ref[ft.TextField]()
        self.compress_progress_bar = ft.Ref[ft.ProgressBar]()
        self.compress_eta_text = ft.Ref[ft.Text]()
        self.compress_status_text = ft.Ref[ft.Text]()
        self.compress_start_button_ref = ft.Ref[ft.ElevatedButton]()
        self.compress_cancel_button_ref = ft.Ref[ft.ElevatedButton]()

        self._compress_task_queue: "queue.Queue[str]" = queue.Queue()
        self._compress_ui_queue: "queue.Queue[tuple]" = queue.Queue()
        self._compress_cancel_requested = False
        self._compress_current_process = None
        self._compress_encoder = self.detect_gpu_encoder()

        self._ui_queue: "queue.Queue[tuple]" = queue.Queue()
        self._ui_poller_started = False
        
        # File picker for folder selection
        self.folder_picker = ft.FilePicker(on_result=self.on_folder_picked)
        self.compress_files_picker = ft.FilePicker(on_result=self.on_compress_files_picked)
        self.compress_folder_picker = ft.FilePicker(on_result=self.on_compress_folder_picked)
        page.overlay.append(self.folder_picker)
        page.overlay.append(self.compress_files_picker)
        page.overlay.append(self.compress_folder_picker)
        page.update()
        
        # Build UI
        self.build_ui()
    
    def build_ui(self):
        convert_tab = self._build_convert_tab()
        compress_tab = self._build_compress_tab()

        self.page.add(
            ft.Tabs(
                selected_index=0,
                animation_duration=250,
                tabs=[
                    ft.Tab(text="Convert", content=convert_tab),
                    ft.Tab(text="Compress", content=compress_tab),
                ],
                expand=1,
            )
        )

        self._start_compress_ui_poller()
        self._start_ui_poller()

    def _build_convert_tab(self):
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

        return ft.Column(
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

    def _build_compress_tab(self):
        preset_options = [
            ("Film - Balances encoding quality with file size, suited for most films.", {"crf": 23, "preset": "slow"}),
            ("Anime - Optimized for animation, preserving fine lines and details at a higher quality.", {"crf": 20, "preset": "veryslow"}),
            ("4K - Tailored for 4K videos, allows for a slight reduction in quality to reduce file size.", {"crf": 22, "preset": "slow"}),
            ("Plex - Designed for streaming platforms like Plex, balancing quality with a faster encoding speed.", {"crf": 24, "preset": "medium"}),
        ]
        self._compress_presets = {k: v for k, v in preset_options}

        encoder_row = ft.Row([
            ft.Text("Encoder:", width=120, color="#cdd6f4"),
            ft.Text(self._compress_encoder, color="#a6adc8"),
        ])

        add_buttons = ft.Row(
            [
                ft.ElevatedButton(
                    "Add Files",
                    icon=icons.ADD if icons else "add",
                    on_click=self.browse_compress_files,
                    style=ft.ButtonStyle(bgcolor="#6366f1", color="#ffffff"),
                ),
                ft.ElevatedButton(
                    "Add Folder",
                    icon=icons.FOLDER_OPEN if icons else "folder_open",
                    on_click=self.browse_compress_folder,
                    style=ft.ButtonStyle(bgcolor="#6366f1", color="#ffffff"),
                ),
                ft.ElevatedButton(
                    "Clear Queue",
                    icon=icons.DELETE if icons else "delete",
                    on_click=self.clear_compress_queue,
                    style=ft.ButtonStyle(bgcolor="#ef4444", color="#ffffff"),
                ),
            ],
            spacing=10,
            wrap=True,
        )

        queue_container = ft.Container(
            content=ft.ListView(
                ref=self.compress_queue_list,
                spacing=4,
                padding=10,
                auto_scroll=False,
            ),
            border=ft.border.all(1, "#313244"),
            border_radius=8,
            bgcolor="#181825",
            height=200,
        )

        mode_section = ft.Column(
            [
                ft.Text("Mode", weight=ft.FontWeight.BOLD, color="#cdd6f4"),
                ft.RadioGroup(
                    ref=self.compress_mode_radio,
                    value="CRF",
                    content=ft.Column(
                        [
                            ft.Radio(value="CRF", label="CRF"),
                            ft.Radio(value="SIZE", label="Target Size (GB)"),
                        ]
                    ),
                ),
                ft.TextField(
                    ref=self.compress_target_size,
                    value="5",
                    label="Target Size (GB)",
                    width=200,
                    border_color="#6366f1",
                    focused_border_color="#818cf8",
                    color="#cdd6f4",
                    bgcolor="#1e1e2e",
                ),
            ],
            spacing=6,
        )

        preset_row = ft.Row([
            ft.Text("Presets:", width=120, color="#cdd6f4"),
            ft.Dropdown(
                ref=self.compress_preset_dropdown,
                width=600,
                value=preset_options[0][0],
                options=[ft.dropdown.Option(k, k) for k, _ in preset_options],
                border_color="#6366f1",
                focused_border_color="#818cf8",
                color="#cdd6f4",
                bgcolor="#1e1e2e",
            )
        ], wrap=True)

        progress_section = ft.Column(
            [
                ft.ProgressBar(
                    ref=self.compress_progress_bar,
                    value=0,
                    width=700,
                    visible=True,
                    color="#6366f1",
                    bgcolor="#313244",
                ),
                ft.Row(
                    [
                        ft.Text(ref=self.compress_eta_text, value="ETA: --", color="#a6adc8"),
                        ft.Text(ref=self.compress_status_text, value="Idle", color="#a6adc8"),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            ],
            spacing=6,
        )

        start_cancel_row = ft.Row(
            [
                ft.ElevatedButton(
                    ref=self.compress_start_button_ref,
                    text="START",
                    icon=icons.PLAY_ARROW if icons else "play_arrow",
                    on_click=self.start_compress,
                    style=ft.ButtonStyle(color="#ffffff", bgcolor="#22c55e"),
                    visible=True,
                ),
                ft.ElevatedButton(
                    ref=self.compress_cancel_button_ref,
                    text="CANCEL",
                    icon=icons.CLOSE if icons else "close",
                    on_click=self.cancel_compress,
                    style=ft.ButtonStyle(color="#ffffff", bgcolor="#f97316"),
                    visible=False,
                ),
            ],
            spacing=10,
        )

        return ft.Column(
            [
                ft.Container(height=10),
                encoder_row,
                ft.Container(height=10),
                add_buttons,
                ft.Container(height=10),
                queue_container,
                ft.Container(height=10),
                mode_section,
                ft.Container(height=10),
                preset_row,
                ft.Container(height=10),
                progress_section,
                ft.Container(height=10),
                start_cancel_row,
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
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

    def browse_compress_files(self, e):
        if platform.system() == "Darwin":
            # macOS: Use native AppleScript dialog
            try:
                result = subprocess.run(
                    ["osascript", "-e", 'set theFiles to choose file with prompt "Select video files" of type {"mkv", "mp4", "avi", "mov", "wmv"} with multiple selections allowed', "-e", 'set output to ""', "-e", 'repeat with f in theFiles', "-e", 'set output to output & POSIX path of f & "\n"', "-e", 'end repeat', "-e", 'return output'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0 and result.stdout.strip():
                    added = 0
                    for line in result.stdout.strip().split("\n"):
                        file_path = line.strip()
                        if file_path and file_path.lower().endswith((".mkv", ".mp4", ".avi", ".mov", ".wmv")):
                            self._compress_task_queue.put(file_path)
                            self.compress_queue_list.current.controls.append(
                                ft.Text(Path(file_path).name, size=12, color="#a6adc8")
                            )
                            added += 1
                    if added:
                        self.compress_status_text.current.value = f"Queued: {self._compress_task_queue.qsize()}"
                        self.page.update()
            except Exception as ex:
                self.compress_status_text.current.value = f"Error: {ex}"
                self.page.update()
        else:
            # Windows/Linux: Use Flet FilePicker
            self.compress_files_picker.pick_files(
                allow_multiple=True,
                dialog_title="Add video files",
            )

    def browse_compress_folder(self, e):
        if platform.system() == "Darwin":
            # macOS: Use native AppleScript dialog
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
                        if p.is_file() and p.suffix.lower() in (".mkv", ".mp4", ".avi", ".mov", ".wmv"):
                            self._compress_task_queue.put(str(p))
                            self.compress_queue_list.current.controls.append(
                                ft.Text(p.name, size=12, color="#a6adc8")
                            )
                            added += 1
                    if added:
                        self.compress_status_text.current.value = f"Queued: {self._compress_task_queue.qsize()}"
                        self.page.update()
            except Exception as ex:
                self.compress_status_text.current.value = f"Error: {ex}"
                self.page.update()
        else:
            # Windows/Linux: Use Flet FilePicker
            self.compress_folder_picker.get_directory_path(
                dialog_title="Add folder with videos",
            )
    
    def on_folder_picked(self, e: ft.FilePickerResultEvent):
        # This is only used on Windows/Linux
        if e.path:
            self.folder_path.current.value = e.path
            self.page.update()
            self.log(f"Ordner ausgewählt: {e.path}", "#22c55e")
        else:
            self.log("Auswahl abgebrochen", "#f97316")

    def on_compress_files_picked(self, e: ft.FilePickerResultEvent):
        if not e.files:
            return
        added = 0
        for f in e.files:
            if f.path and f.path.lower().endswith((".mkv", ".mp4", ".avi", ".mov", ".wmv")):
                self._compress_task_queue.put(f.path)
                self.compress_queue_list.current.controls.append(
                    ft.Text(Path(f.path).name, size=12, color="#a6adc8")
                )
                added += 1
        if added:
            self.compress_status_text.current.value = f"Queued: {self._compress_task_queue.qsize()}"
            self.page.update()

    def on_compress_folder_picked(self, e: ft.FilePickerResultEvent):
        if not e.path:
            return
        folder = Path(e.path)
        added = 0
        try:
            for p in folder.iterdir():
                if p.is_file() and p.suffix.lower() in (".mkv", ".mp4", ".avi", ".mov", ".wmv"):
                    self._compress_task_queue.put(str(p))
                    self.compress_queue_list.current.controls.append(
                        ft.Text(p.name, size=12, color="#a6adc8")
                    )
                    added += 1
        except Exception:
            pass
        if added:
            self.compress_status_text.current.value = f"Queued: {self._compress_task_queue.qsize()}"
            self.page.update()
    
    def log(self, message, color=None):
        if threading.current_thread() is not threading.main_thread():
            self._ui_queue.put(("log", message, color))
            return

        log_entry = ft.Text(
            message,
            size=12,
            color=color if color else "#a6adc8"
        )
        self.log_column.current.controls.append(log_entry)
        self.page.update()

    def clear_compress_queue(self, e):
        self._compress_task_queue = queue.Queue()
        self.compress_queue_list.current.controls.clear()
        self.compress_progress_bar.current.value = 0
        self.compress_eta_text.current.value = "ETA: --"
        self.compress_status_text.current.value = "Idle"
        self.page.update()

    def detect_gpu_encoder(self):
        try:
            encoders = subprocess.check_output(
                ["ffmpeg", "-encoders"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            if "hevc_nvenc" in encoders:
                return "hevc_nvenc"
            if "hevc_amf" in encoders:
                return "hevc_amf"
            if "hevc_qsv" in encoders:
                return "hevc_qsv"
        except Exception:
            pass
        return "libx265"

    def _get_duration_seconds(self, path):
        out = subprocess.check_output(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            text=True,
        )
        return float(out.strip())

    def _calculate_bitrate_kbps(self, duration, target_gb):
        target_bits = target_gb * 1024**3 * 8
        total_kbps = target_bits / duration / 1000
        return max(int(total_kbps), 500)

    def start_compress(self, e):
        if self._compress_task_queue.empty():
            self.compress_status_text.current.value = "Queue is empty"
            self.page.update()
            return

        self._compress_cancel_requested = False
        self.compress_start_button_ref.current.visible = False
        self.compress_cancel_button_ref.current.visible = True
        self.compress_status_text.current.value = "Starting..."
        self.page.update()

        threading.Thread(target=self._compress_worker, daemon=True).start()

    def cancel_compress(self, e):
        self._compress_cancel_requested = True
        self.compress_status_text.current.value = "Cancelling..."
        try:
            if self._compress_current_process is not None:
                self._compress_current_process.kill()
        except Exception:
            pass
        self.page.update()

    def _compress_worker(self):
        while not self._compress_task_queue.empty():
            if self._compress_cancel_requested:
                break
            file_path = self._compress_task_queue.get()
            self._compress_ui_queue.put(("status", f"Encoding: {Path(file_path).name}"))
            try:
                self._compress_encode_file(file_path)
            finally:
                self._compress_task_queue.task_done()

        self._compress_ui_queue.put(("idle",))
        self._compress_cancel_requested = False

    def _compress_encode_file(self, input_file):
        duration = self._get_duration_seconds(input_file)
        output_file = str(Path(input_file).with_name(Path(input_file).stem + "_compressed.mkv"))

        mode = self.compress_mode_radio.current.value
        preset_key = self.compress_preset_dropdown.current.value
        preset = self._compress_presets.get(preset_key, {"crf": 23, "preset": "slow"})

        cmd = [
            "ffmpeg", "-y",
            "-i", input_file,
            "-map", "0",
            "-c:v", self._compress_encoder,
            "-profile:v", "main10",
            "-pix_fmt", "p010le",
            "-preset", preset["preset"],
        ]

        if mode == "CRF":
            cmd += ["-crf", str(preset["crf"])]
        else:
            try:
                target_gb = float(self.compress_target_size.current.value)
            except Exception:
                target_gb = 5.0
            bitrate = self._calculate_bitrate_kbps(duration, target_gb)
            cmd += [
                "-b:v", f"{bitrate}k",
                "-maxrate", f"{bitrate}k",
                "-bufsize", f"{bitrate * 2}k",
            ]

        cmd += [
            "-c:a", "copy",
            "-c:s", "copy",
            "-color_primaries", "bt2020",
            "-color_trc", "smpte2084",
            "-colorspace", "bt2020nc",
            "-progress", "pipe:1",
            "-nostats",
            output_file,
        ]

        self._compress_current_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )

        start = time.time()
        current_sec = 0.0
        if self._compress_current_process.stdout is None:
            return

        for line in self._compress_current_process.stdout:
            if self._compress_cancel_requested:
                try:
                    self._compress_current_process.kill()
                except Exception:
                    pass
                return

            if line.startswith("out_time_ms="):
                value = line.split("=", 1)[1].strip()
                if not value.isdigit():
                    continue
                current_sec = int(value) / 1_000_000
                progress = min((current_sec / duration) * 100.0, 100.0) if duration > 0 else 0

                elapsed = time.time() - start
                eta = int((elapsed / current_sec) * (duration - current_sec)) if current_sec > 0 else 0
                self._compress_ui_queue.put(("progress", progress, eta))

        self._compress_ui_queue.put(("done",))

    def _start_compress_ui_poller(self):
        def poll_loop():
            while True:
                updated = False
                try:
                    while True:
                        msg = self._compress_ui_queue.get_nowait()
                        if msg[0] == "progress":
                            _, prog, eta = msg
                            self.compress_progress_bar.current.value = prog / 100.0
                            self.compress_eta_text.current.value = f"ETA: {eta}s"
                            updated = True

                        elif msg[0] == "status":
                            self.compress_status_text.current.value = msg[1]
                            updated = True

                        elif msg[0] == "done":
                            self.compress_progress_bar.current.value = 0
                            self.compress_eta_text.current.value = "ETA: --"
                            updated = True

                        elif msg[0] == "idle":
                            self.compress_status_text.current.value = "Idle"
                            self.compress_start_button_ref.current.visible = True
                            self.compress_cancel_button_ref.current.visible = False
                            updated = True

                except queue.Empty:
                    pass

                if updated:
                    try:
                        self.page.update()
                    except Exception:
                        pass

                time.sleep(0.1)

        threading.Thread(target=poll_loop, daemon=True).start()

    def _start_ui_poller(self):
        if self._ui_poller_started:
            return
        self._ui_poller_started = True

        def poll_loop():
            while True:
                updated = False
                try:
                    while True:
                        msg = self._ui_queue.get_nowait()
                        if msg[0] == "log":
                            _, message, color = msg
                            log_entry = ft.Text(
                                message,
                                size=12,
                                color=color if color else "#a6adc8",
                            )
                            self.log_column.current.controls.append(log_entry)
                            updated = True

                        elif msg[0] == "convert_progress":
                            _, value, text = msg
                            self.progress_bar.current.value = value
                            self.progress_text.current.value = text
                            updated = True

                        elif msg[0] == "convert_visibility":
                            _, visible = msg
                            self.progress_bar.current.visible = visible
                            updated = True

                        elif msg[0] == "convert_text_color":
                            _, color = msg
                            self.progress_text.current.color = color
                            updated = True

                        elif msg[0] == "convert_done":
                            _, value, text, color = msg
                            self.progress_bar.current.value = value
                            self.progress_text.current.value = text
                            self.progress_text.current.color = color
                            updated = True

                        elif msg[0] == "convert_enable_ui":
                            self.start_button_ref.current.disabled = False
                            self.browse_button_ref.current.disabled = False
                            self.folder_path.current.disabled = False
                            self.codec_dropdown.current.disabled = False
                            self.replace_checkbox.current.disabled = False
                            updated = True

                        elif msg[0] == "convert_disable_ui":
                            self.start_button_ref.current.disabled = True
                            self.browse_button_ref.current.disabled = True
                            self.folder_path.current.disabled = True
                            self.codec_dropdown.current.disabled = True
                            self.replace_checkbox.current.disabled = True
                            updated = True

                        elif msg[0] == "clear_log":
                            self.log_column.current.controls.clear()
                            updated = True

                except queue.Empty:
                    pass

                if updated:
                    try:
                        self.page.update()
                    except Exception:
                        pass

                time.sleep(0.05)

        threading.Thread(target=poll_loop, daemon=True).start()

    def get_video_duration(self, input_file):
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                input_file,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except Exception:
            pass
        return None

    def parse_ffmpeg_time(self, time_str):
        try:
            parts = time_str.split(":")
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        except Exception:
            return 0

    def convert_file(self, input_file, file_index, total_files):
        replace = self.replace_checkbox.current.value
        codec = self.codec_dropdown.current.value

        tmp_file = input_file + ".tmp" if replace else os.path.splitext(input_file)[0] + f"_{codec}.mkv"
        vcodec = "libx265" if codec == "h265" else "libx264"

        duration = self.get_video_duration(input_file)

        cmd = [
            "ffmpeg", "-i", input_file,
            "-c:v", vcodec,
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "copy",
            "-y", tmp_file,
        ]

        self.log(f"Konvertiere: {os.path.basename(input_file)}", "#6366f1")
        try:
            process = subprocess.Popen(
                cmd,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                universal_newlines=True,
            )

            time_pattern = re.compile(r"time=(\d+:\d+:\d+\.\d+)")

            while True:
                if process.stderr is None:
                    break

                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break

                match = time_pattern.search(line)
                if match and duration:
                    current_time = self.parse_ffmpeg_time(match.group(1))
                    file_progress = min(current_time / duration, 1.0)
                    overall_progress = ((file_index - 1) + file_progress) / total_files

                    percent = int(file_progress * 100)
                    self._ui_queue.put((
                        "convert_progress",
                        overall_progress,
                        f"Datei {file_index}/{total_files}: {os.path.basename(input_file)} ({percent}%)",
                    ))

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

        self._ui_queue.put(("convert_disable_ui",))
        self._ui_queue.put(("clear_log",))
        self._ui_queue.put(("log", "=== Konvertierung gestartet ===", "#6366f1"))
        self._ui_queue.put(("convert_visibility", True))
        self._ui_queue.put(("convert_progress", 0, "Bereit"))
        self._ui_queue.put(("convert_text_color", "#6366f1"))

        threading.Thread(target=self._run_conversion, args=(folder,), daemon=True).start()

    def _run_conversion(self, folder):
        video_files = []
        for root_dir, dirs, files in os.walk(folder):
            for f in files:
                if f.lower().endswith((".mkv", ".mp4")):
                    video_files.append(os.path.join(root_dir, f))

        total_files = len(video_files)

        if total_files == 0:
            self._ui_queue.put(("log", "Keine Video-Dateien (.mkv, .mp4) gefunden.", "#f97316"))
            self._ui_queue.put(("convert_done", 0, "Keine Dateien gefunden", "#f97316"))
            self._ui_queue.put(("convert_visibility", False))
            self._ui_queue.put(("convert_enable_ui",))
            return

        for index, file_path in enumerate(video_files, 1):
            self.convert_file(file_path, index, total_files)

        self._ui_queue.put((
            "convert_done",
            1.0,
            f"✓ Fertig! {total_files} Dateien konvertiert",
            "#22c55e",
        ))
        self._ui_queue.put(("log", f"\n=== Konvertierung abgeschlossen! ({total_files} Dateien) ===", "#22c55e"))
        self._ui_queue.put(("convert_enable_ui",))


def main(page: ft.Page):
    app = ConverterApp(page)


if __name__ == "__main__":
    ft.app(target=main)