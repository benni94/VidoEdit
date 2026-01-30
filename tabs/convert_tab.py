"""Convert Tab - H.266/VVC to H.265/H.264 conversion"""
import os
import subprocess
import platform
import threading
import re
import queue
from pathlib import Path

import flet as ft
from ffmpeg_utils import get_ffmpeg_path, get_ffprobe_path
from components.file_input_component import FileInputComponent

try:
    from flet import icons
except (ImportError, AttributeError):
    icons = None


class ConvertTab:
    """Tab for converting H.266/VVC videos to H.265 or H.264"""
    
    VIDEO_EXTENSIONS = (".mkv", ".mp4", ".avi", ".mov", ".wmv", ".vvc")
    
    def __init__(self, page: ft.Page, language_manager):
        self.page = page
        self.lang_manager = language_manager
        
        # UI Refs
        self.codec_dropdown = ft.Ref[ft.Dropdown]()
        self.replace_checkbox = ft.Ref[ft.Checkbox]()
        self.log_column = ft.Ref[ft.Column]()
        self.progress_bar = ft.Ref[ft.ProgressBar]()
        self.progress_text = ft.Ref[ft.Text]()
        self.start_button_ref = ft.Ref[ft.ElevatedButton]()
        self.cancel_button_ref = ft.Ref[ft.ElevatedButton]()
        self.open_folder_button_ref = ft.Ref[ft.ElevatedButton]()
        
        # Track output directory
        self._output_dir = None
        
        # State
        self._ui_queue: "queue.Queue[tuple]" = queue.Queue()
        self._cancel_requested = False
        self._current_process = None
        self._ui_poller_started = False
        
        # File input component
        self.file_input = FileInputComponent(
            page=page,
            language_manager=language_manager,
            video_extensions=self.VIDEO_EXTENSIONS,
            on_files_added=self._on_files_added,
            queue_height=150
        )
    
    def _c(self, light, dark):
        return dark if self.page.theme_mode == ft.ThemeMode.DARK else light

    def build(self) -> ft.Control:
        """Build and return the tab content"""
        self._start_ui_poller()
        
        add_buttons, queue_container = self.file_input.build()

        codec_row = ft.Row([
            ft.Text(self.lang_manager.get_text("target_codec"), width=120, color=self._c("#1e1e2e", "#cdd6f4")),
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
                color=self._c("#1e1e2e", "#cdd6f4"),
                bgcolor=self._c("#ffffff", "#1e1e2e")
            )
        ])

        replace_row = ft.Row([
            ft.Checkbox(
                ref=self.replace_checkbox,
                label=self.lang_manager.get_text("replace_original"),
                value=False,
                check_color="#ffffff",
                active_color="#6366f1",
                label_style=ft.TextStyle(color=self._c("#1f2937", "#cdd6f4"))
            )
        ])

        start_cancel_row = ft.Row(
            [
                ft.ElevatedButton(
                    ref=self.start_button_ref,
                    text=self.lang_manager.get_text("start_conversion"),
                    icon=icons.PLAY_ARROW if icons else "play_arrow",
                    on_click=self._start_conversion,
                    style=ft.ButtonStyle(color="#ffffff", bgcolor="#22c55e"),
                    visible=True,
                ),
                ft.ElevatedButton(
                    ref=self.cancel_button_ref,
                    text=self.lang_manager.get_text("cancel"),
                    icon=icons.CLOSE if icons else "close",
                    on_click=self._cancel_conversion,
                    style=ft.ButtonStyle(color="#ffffff", bgcolor="#f97316"),
                    visible=False,
                ),
                ft.ElevatedButton(
                    ref=self.open_folder_button_ref,
                    text=self.lang_manager.get_text("open_output_folder") if hasattr(self.lang_manager, 'get_text') else "Open Output Folder",
                    icon=icons.FOLDER_OPEN if icons else "folder_open",
                    on_click=self._open_output_folder,
                    style=ft.ButtonStyle(color="#ffffff", bgcolor="#6366f1"),
                    visible=False,
                ),
            ],
            spacing=10,
        )

        progress_section = ft.Column([
            ft.Text(
                ref=self.progress_text,
                value=self.lang_manager.get_text("ready"),
                size=14,
                weight=ft.FontWeight.BOLD,
                color="#6366f1"
            ),
            ft.ProgressBar(
                ref=self.progress_bar,
                value=0,
                width=700,
                visible=True,
                color="#6366f1",
                bgcolor=self._c("#e5e7eb", "#313244")
            )
        ], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        log_container = ft.Container(
            content=ft.Column(
                ref=self.log_column,
                scroll=ft.ScrollMode.AUTO,
                spacing=5
            ),
            border=ft.border.all(1, self._c("#e5e7eb", "#313244")),
            border_radius=8,
            padding=15,
            height=150,
            bgcolor=self._c("#f9fafb", "#181825"),
            expand=True
        )

        return ft.Column(
            [
                ft.Container(height=10),
                add_buttons,
                ft.Container(height=10),
                queue_container,
                ft.Container(height=10),
                codec_row,
                ft.Container(height=10),
                replace_row,
                ft.Container(height=10),
                start_cancel_row,
                ft.Container(height=10),
                progress_section,
                ft.Container(height=10),
                ft.Text(self.lang_manager.get_text("log"), weight=ft.FontWeight.BOLD, color=self._c("#111827", "#cdd6f4")),
                log_container
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
    
    def _on_files_added(self, count):
        """Callback when files are added to the queue"""
        self.progress_text.current.value = f"Queued: {self.file_input.queue_size()} files"
        self.page.update()

    def _cancel_conversion(self, e):
        self._cancel_requested = True
        if self._current_process:
            self._current_process.terminate()
        self._output_dir = None
        try:
            if self._current_process is not None:
                self._current_process.kill()
        except Exception:
            pass
        self.progress_text.current.value = "Cancelling..."
        self.page.update()
    
    def _log(self, message, color=None):
        if threading.current_thread() is not threading.main_thread():
            self._ui_queue.put(("log", message, color))
            return
        log_entry = ft.Text(message, size=12, color=color if color else self._c("#374151", "#a6adc8"))
        self.log_column.current.controls.append(log_entry)
        self.page.update()

    def _start_ui_poller(self):
        if self._ui_poller_started:
            return
        self._ui_poller_started = True

        def poll_loop():
            import time
            while True:
                updated = False
                try:
                    while True:
                        msg = self._ui_queue.get_nowait()
                        if msg[0] == "log":
                            _, message, color = msg
                            log_entry = ft.Text(message, size=12, color=color if color else self._c("#374151", "#a6adc8"))
                            self.log_column.current.controls.append(log_entry)
                            updated = True
                        elif msg[0] == "progress":
                            _, value, text = msg
                            self.progress_bar.current.value = value
                            self.progress_text.current.value = text
                            updated = True
                        elif msg[0] == "done":
                            _, value, text, color = msg
                            self.progress_bar.current.value = value
                            self.progress_text.current.value = text
                            self.progress_text.current.color = color
                            updated = True
                        elif msg[0] == "idle":
                            self.start_button_ref.current.visible = True
                            self.cancel_button_ref.current.visible = False
                            # Show open folder button if output directory exists
                            if self._output_dir and os.path.exists(self._output_dir):
                                self.open_folder_button_ref.current.visible = True
                            else:
                                self.open_folder_button_ref.current.visible = False
                            self.file_input.queue_list.current.controls.clear()
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

    def _get_video_duration(self, input_file):
        try:
            cmd = [
                get_ffprobe_path(), "-v", "error",
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

    def _parse_ffmpeg_time(self, time_str):
        try:
            parts = time_str.split(":")
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        except Exception:
            return 0

    def _convert_file(self, input_file, file_index, total_files):
        replace = self.replace_checkbox.current.value
        codec = self.codec_dropdown.current.value

        # Create 'edited' subfolder in the same directory as input file
        input_dir = os.path.dirname(input_file)
        output_dir = os.path.join(input_dir, "edited")
        os.makedirs(output_dir, exist_ok=True)
        
        # Store output directory for opening later
        if self._output_dir is None:
            self._output_dir = output_dir
        
        # Get filename without path and create output path without prefix
        filename = os.path.basename(input_file)
        name, ext = os.path.splitext(filename)
        output_file = os.path.join(output_dir, f"{name}.mkv")
        
        tmp_file = input_file + ".tmp" if replace else output_file
        vcodec = "libx265" if codec == "h265" else "libx264"

        duration = self._get_video_duration(input_file)

        cmd = [
            get_ffmpeg_path(), "-i", input_file,
            "-c:v", vcodec,
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "copy",
            "-y", tmp_file,
        ]

        self._log(f"Konvertiere: {os.path.basename(input_file)}", "#6366f1")
        try:
            self._current_process = subprocess.Popen(
                cmd,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                universal_newlines=True,
            )

            time_pattern = re.compile(r"time=(\d+:\d+:\d+\.\d+)")

            while True:
                if self._current_process.stderr is None:
                    break

                line = self._current_process.stderr.readline()
                if not line and self._current_process.poll() is not None:
                    break

                match = time_pattern.search(line)
                if match and duration:
                    current_time = self._parse_ffmpeg_time(match.group(1))
                    file_progress = min(current_time / duration, 1.0)
                    overall_progress = ((file_index - 1) + file_progress) / total_files

                    percent = int(file_progress * 100)
                    self._ui_queue.put((
                        "progress",
                        overall_progress,
                        f"Datei {file_index}/{total_files}: {os.path.basename(input_file)} ({percent}%)",
                    ))

            if self._current_process.returncode == 0:
                if replace:
                    os.replace(tmp_file, input_file)
                    self._log(f"✓ Original ersetzt: {os.path.basename(input_file)}", "#22c55e")
                else:
                    self._log(f"✓ Gespeichert: {os.path.basename(output_file)}", "#22c55e")
            else:
                self._log(f"✗ Fehler bei: {os.path.basename(input_file)}", "#ef4444")
                if replace and os.path.exists(tmp_file):
                    os.remove(tmp_file)

        except FileNotFoundError:
            self._log("✗ FFmpeg nicht gefunden! Bitte installiere FFmpeg.", "#ef4444")

    def _open_output_folder(self, e):
        """Open the output directory in file explorer"""
        if self._output_dir and os.path.exists(self._output_dir):
            if platform.system() == "Windows":
                os.startfile(self._output_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", self._output_dir])
            else:  # Linux
                subprocess.Popen(["xdg-open", self._output_dir])
    
    def _start_conversion(self, e):
        if self.file_input.is_empty():
            self._log(self.lang_manager.get_text("queue_empty"), "#ef4444")
            return
        
        # Reset output directory
        self._output_dir = None
        self._cancel_requested = False
        self.start_button_ref.current.visible = False
        self.cancel_button_ref.current.visible = True
        self.open_folder_button_ref.current.visible = False
        self._ui_queue.put(("clear_log",))
        self._ui_queue.put(("log", self.lang_manager.get_text("conversion_started"), "#6366f1"))
        self._ui_queue.put(("progress", 0, self.lang_manager.get_text("starting")))
        self.page.update()

        threading.Thread(target=self._run_conversion, daemon=True).start()

    def _run_conversion(self):
        video_files = []
        task_queue = self.file_input.get_queue()
        while not task_queue.empty():
            video_files.append(task_queue.get())

        total_files = len(video_files)

        if total_files == 0:
            self._ui_queue.put(("log", self.lang_manager.get_text("no_video_files"), "#f97316"))
            self._ui_queue.put(("done", 0, self.lang_manager.get_text("no_files_found"), "#f97316"))
            self._ui_queue.put(("idle",))
            return

        converted = 0
        for index, file_path in enumerate(video_files, 1):
            if self._cancel_requested:
                self._ui_queue.put(("log", self.lang_manager.get_text("conversion_cancelled"), "#f97316"))
                break
            self._convert_file(file_path, index, total_files)
            converted += 1

        if not self._cancel_requested:
            self._ui_queue.put((
                "done",
                1.0,
                self.lang_manager.get_text("done", count=converted),
                "#22c55e",
            ))
            self._ui_queue.put(("log", self.lang_manager.get_text("conversion_complete", count=converted), "#22c55e"))
        
        self._ui_queue.put(("idle",))
        self._cancel_requested = False
