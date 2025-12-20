"""Convert Tab - H.266/VVC to H.265/H.264 conversion"""
import os
import subprocess
import platform
import threading
import re
import queue
from pathlib import Path

import flet as ft

try:
    from flet import icons
except (ImportError, AttributeError):
    icons = None


class ConvertTab:
    """Tab for converting H.266/VVC videos to H.265 or H.264"""
    
    VIDEO_EXTENSIONS = (".mkv", ".mp4", ".avi", ".mov", ".wmv", ".vvc")
    
    def __init__(self, page: ft.Page):
        self.page = page
        
        # UI Refs
        self.queue_list = ft.Ref[ft.ListView]()
        self.codec_dropdown = ft.Ref[ft.Dropdown]()
        self.replace_checkbox = ft.Ref[ft.Checkbox]()
        self.log_column = ft.Ref[ft.Column]()
        self.progress_bar = ft.Ref[ft.ProgressBar]()
        self.progress_text = ft.Ref[ft.Text]()
        self.start_button_ref = ft.Ref[ft.ElevatedButton]()
        self.cancel_button_ref = ft.Ref[ft.ElevatedButton]()
        
        # State
        self._task_queue: "queue.Queue[str]" = queue.Queue()
        self._ui_queue: "queue.Queue[tuple]" = queue.Queue()
        self._cancel_requested = False
        self._current_process = None
        self._ui_poller_started = False
        
        # File pickers (Windows/Linux)
        self.files_picker = ft.FilePicker(on_result=self._on_files_picked)
        self.folder_picker = ft.FilePicker(on_result=self._on_folder_picked)
        page.overlay.append(self.files_picker)
        page.overlay.append(self.folder_picker)
    
    def build(self) -> ft.Control:
        """Build and return the tab content"""
        self._start_ui_poller()
        
        add_buttons = ft.Row(
            [
                ft.ElevatedButton(
                    "Add Files",
                    icon=icons.ADD if icons else "add",
                    on_click=self._browse_files,
                    style=ft.ButtonStyle(bgcolor="#6366f1", color="#ffffff"),
                ),
                ft.ElevatedButton(
                    "Add Folder",
                    icon=icons.FOLDER_OPEN if icons else "folder_open",
                    on_click=self._browse_folder,
                    style=ft.ButtonStyle(bgcolor="#6366f1", color="#ffffff"),
                ),
                ft.ElevatedButton(
                    "Clear Queue",
                    icon=icons.DELETE if icons else "delete",
                    on_click=self._clear_queue,
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
            border=ft.border.all(1, "#313244"),
            border_radius=8,
            bgcolor="#181825",
            height=150,
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

        start_cancel_row = ft.Row(
            [
                ft.ElevatedButton(
                    ref=self.start_button_ref,
                    text="Start Konvertierung",
                    icon=icons.PLAY_ARROW if icons else "play_arrow",
                    on_click=self._start_conversion,
                    style=ft.ButtonStyle(color="#ffffff", bgcolor="#22c55e"),
                    visible=True,
                ),
                ft.ElevatedButton(
                    ref=self.cancel_button_ref,
                    text="CANCEL",
                    icon=icons.CLOSE if icons else "close",
                    on_click=self._cancel_conversion,
                    style=ft.ButtonStyle(color="#ffffff", bgcolor="#f97316"),
                    visible=False,
                ),
            ],
            spacing=10,
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
                visible=True,
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
            height=150,
            bgcolor="#181825",
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
                ft.Text("Log:", weight=ft.FontWeight.BOLD, color="#cdd6f4"),
                log_container
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
    
    def _browse_files(self, e):
        if platform.system() == "Darwin":
            try:
                result = subprocess.run(
                    ["osascript", "-e", 'set theFiles to choose file with prompt "Select video files" of type {"mkv", "mp4", "avi", "mov", "wmv", "vvc"} with multiple selections allowed', "-e", 'set output to ""', "-e", 'repeat with f in theFiles', "-e", 'set output to output & POSIX path of f & "\n"', "-e", 'end repeat', "-e", 'return output'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0 and result.stdout.strip():
                    added = 0
                    for line in result.stdout.strip().split("\n"):
                        file_path = line.strip()
                        if file_path and file_path.lower().endswith(self.VIDEO_EXTENSIONS):
                            self._task_queue.put(file_path)
                            self.queue_list.current.controls.append(
                                ft.Text(Path(file_path).name, size=12, color="#a6adc8")
                            )
                            added += 1
                    if added:
                        self.progress_text.current.value = f"Queued: {self._task_queue.qsize()} files"
                        self.page.update()
            except Exception as ex:
                self._log(f"Error: {ex}", "#ef4444")
        else:
            self.files_picker.pick_files(
                allow_multiple=True,
                dialog_title="Add video files",
            )

    def _browse_folder(self, e):
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
                        if p.is_file() and p.suffix.lower() in self.VIDEO_EXTENSIONS:
                            self._task_queue.put(str(p))
                            self.queue_list.current.controls.append(
                                ft.Text(p.name, size=12, color="#a6adc8")
                            )
                            added += 1
                    if added:
                        self.progress_text.current.value = f"Queued: {self._task_queue.qsize()} files"
                        self.page.update()
            except Exception as ex:
                self._log(f"Error: {ex}", "#ef4444")
        else:
            self.folder_picker.get_directory_path(
                dialog_title="Select folder with videos",
            )

    def _on_files_picked(self, e: ft.FilePickerResultEvent):
        if not e.files:
            return
        added = 0
        for f in e.files:
            if f.path and f.path.lower().endswith(self.VIDEO_EXTENSIONS):
                self._task_queue.put(f.path)
                self.queue_list.current.controls.append(
                    ft.Text(Path(f.path).name, size=12, color="#a6adc8")
                )
                added += 1
        if added:
            self.progress_text.current.value = f"Queued: {self._task_queue.qsize()} files"
            self.page.update()

    def _on_folder_picked(self, e: ft.FilePickerResultEvent):
        if not e.path:
            return
        folder = Path(e.path)
        added = 0
        try:
            for p in folder.iterdir():
                if p.is_file() and p.suffix.lower() in self.VIDEO_EXTENSIONS:
                    self._task_queue.put(str(p))
                    self.queue_list.current.controls.append(
                        ft.Text(p.name, size=12, color="#a6adc8")
                    )
                    added += 1
        except Exception:
            pass
        if added:
            self.progress_text.current.value = f"Queued: {self._task_queue.qsize()} files"
            self.page.update()

    def _clear_queue(self, e):
        self._task_queue = queue.Queue()
        self.queue_list.current.controls.clear()
        self.progress_bar.current.value = 0
        self.progress_text.current.value = "Bereit"
        self.page.update()

    def _cancel_conversion(self, e):
        self._cancel_requested = True
        self.progress_text.current.value = "Cancelling..."
        try:
            if self._current_process is not None:
                self._current_process.kill()
        except Exception:
            pass
        self.page.update()
    
    def _log(self, message, color=None):
        if threading.current_thread() is not threading.main_thread():
            self._ui_queue.put(("log", message, color))
            return
        log_entry = ft.Text(message, size=12, color=color if color else "#a6adc8")
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
                            log_entry = ft.Text(message, size=12, color=color if color else "#a6adc8")
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
                            self.queue_list.current.controls.clear()
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

        tmp_file = input_file + ".tmp" if replace else os.path.splitext(input_file)[0] + f"_{codec}.mkv"
        vcodec = "libx265" if codec == "h265" else "libx264"

        duration = self._get_video_duration(input_file)

        cmd = [
            "ffmpeg", "-i", input_file,
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
                    self._log(f"✓ Gespeichert als: {os.path.basename(tmp_file)}", "#22c55e")
            else:
                self._log(f"✗ Fehler bei: {os.path.basename(input_file)}", "#ef4444")
                if replace and os.path.exists(tmp_file):
                    os.remove(tmp_file)

        except FileNotFoundError:
            self._log("✗ FFmpeg nicht gefunden! Bitte installiere FFmpeg.", "#ef4444")

    def _start_conversion(self, e):
        if self._task_queue.empty():
            self._log("✗ Queue is empty. Add files first.", "#ef4444")
            return

        self._cancel_requested = False
        self.start_button_ref.current.visible = False
        self.cancel_button_ref.current.visible = True
        self._ui_queue.put(("clear_log",))
        self._ui_queue.put(("log", "=== Konvertierung gestartet ===", "#6366f1"))
        self._ui_queue.put(("progress", 0, "Starting..."))
        self.page.update()

        threading.Thread(target=self._run_conversion, daemon=True).start()

    def _run_conversion(self):
        video_files = []
        while not self._task_queue.empty():
            video_files.append(self._task_queue.get())

        total_files = len(video_files)

        if total_files == 0:
            self._ui_queue.put(("log", "Keine Video-Dateien gefunden.", "#f97316"))
            self._ui_queue.put(("done", 0, "Keine Dateien gefunden", "#f97316"))
            self._ui_queue.put(("idle",))
            return

        converted = 0
        for index, file_path in enumerate(video_files, 1):
            if self._cancel_requested:
                self._ui_queue.put(("log", "Konvertierung abgebrochen.", "#f97316"))
                break
            self._convert_file(file_path, index, total_files)
            converted += 1

        if not self._cancel_requested:
            self._ui_queue.put((
                "done",
                1.0,
                f"✓ Fertig! {converted} Dateien konvertiert",
                "#22c55e",
            ))
            self._ui_queue.put(("log", f"\n=== Konvertierung abgeschlossen! ({converted} Dateien) ===", "#22c55e"))
        
        self._ui_queue.put(("idle",))
        self._cancel_requested = False
