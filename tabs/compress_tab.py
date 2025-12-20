"""Compress Tab - GPU-accelerated video compression"""
import subprocess
import platform
import threading
import time
import queue
from pathlib import Path

import flet as ft

try:
    from flet import icons
except (ImportError, AttributeError):
    icons = None


class CompressTab:
    """Tab for GPU-accelerated video compression"""
    
    VIDEO_EXTENSIONS = (".mkv", ".mp4", ".avi", ".mov", ".wmv")
    
    PRESETS = {
        "Film - Balances encoding quality with file size, suited for most films.": {"crf": 23, "preset": "slow"},
        "Anime - Optimized for animation, preserving fine lines and details at a higher quality.": {"crf": 20, "preset": "veryslow"},
        "4K - Tailored for 4K videos, allows for a slight reduction in quality to reduce file size.": {"crf": 22, "preset": "slow"},
        "Plex - Designed for streaming platforms like Plex, balancing quality with a faster encoding speed.": {"crf": 24, "preset": "medium"},
    }
    
    def __init__(self, page: ft.Page):
        self.page = page
        
        # UI Refs
        self.queue_list = ft.Ref[ft.ListView]()
        self.mode_radio = ft.Ref[ft.RadioGroup]()
        self.preset_dropdown = ft.Ref[ft.Dropdown]()
        self.target_size = ft.Ref[ft.TextField]()
        self.progress_bar = ft.Ref[ft.ProgressBar]()
        self.eta_text = ft.Ref[ft.Text]()
        self.status_text = ft.Ref[ft.Text]()
        self.start_button_ref = ft.Ref[ft.ElevatedButton]()
        self.cancel_button_ref = ft.Ref[ft.ElevatedButton]()
        
        # State
        self._task_queue: "queue.Queue[str]" = queue.Queue()
        self._ui_queue: "queue.Queue[tuple]" = queue.Queue()
        self._cancel_requested = False
        self._current_process = None
        self._encoder = self._detect_gpu_encoder()
        
        # File pickers (Windows/Linux)
        self.files_picker = ft.FilePicker(on_result=self._on_files_picked)
        self.folder_picker = ft.FilePicker(on_result=self._on_folder_picked)
        page.overlay.append(self.files_picker)
        page.overlay.append(self.folder_picker)
    
    def build(self) -> ft.Control:
        """Build and return the tab content"""
        self._start_ui_poller()
        
        preset_options = list(self.PRESETS.keys())
        
        encoder_row = ft.Row([
            ft.Text("Encoder:", width=120, color="#cdd6f4"),
            ft.Text(self._encoder, color="#a6adc8"),
        ])

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
            height=200,
        )

        mode_section = ft.Column(
            [
                ft.Text("Mode", weight=ft.FontWeight.BOLD, color="#cdd6f4"),
                ft.RadioGroup(
                    ref=self.mode_radio,
                    value="CRF",
                    content=ft.Column(
                        [
                            ft.Radio(value="CRF", label="CRF"),
                            ft.Radio(value="SIZE", label="Target Size (GB)"),
                        ]
                    ),
                ),
                ft.TextField(
                    ref=self.target_size,
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
                ref=self.preset_dropdown,
                width=600,
                value=preset_options[0],
                options=[ft.dropdown.Option(k, k) for k in preset_options],
                border_color="#6366f1",
                focused_border_color="#818cf8",
                color="#cdd6f4",
                bgcolor="#1e1e2e",
            )
        ], wrap=True)

        progress_section = ft.Column(
            [
                ft.ProgressBar(
                    ref=self.progress_bar,
                    value=0,
                    width=700,
                    visible=True,
                    color="#6366f1",
                    bgcolor="#313244",
                ),
                ft.Row(
                    [
                        ft.Text(ref=self.eta_text, value="ETA: --", color="#a6adc8"),
                        ft.Text(ref=self.status_text, value="Idle", color="#a6adc8"),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            ],
            spacing=6,
        )

        start_cancel_row = ft.Row(
            [
                ft.ElevatedButton(
                    ref=self.start_button_ref,
                    text="START",
                    icon=icons.PLAY_ARROW if icons else "play_arrow",
                    on_click=self._start_compress,
                    style=ft.ButtonStyle(color="#ffffff", bgcolor="#22c55e"),
                    visible=True,
                ),
                ft.ElevatedButton(
                    ref=self.cancel_button_ref,
                    text="CANCEL",
                    icon=icons.CLOSE if icons else "close",
                    on_click=self._cancel_compress,
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
    
    def _detect_gpu_encoder(self):
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
    
    def _browse_files(self, e):
        if platform.system() == "Darwin":
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
                        if file_path and file_path.lower().endswith(self.VIDEO_EXTENSIONS):
                            self._task_queue.put(file_path)
                            self.queue_list.current.controls.append(
                                ft.Text(Path(file_path).name, size=12, color="#a6adc8")
                            )
                            added += 1
                    if added:
                        self.status_text.current.value = f"Queued: {self._task_queue.qsize()}"
                        self.page.update()
            except Exception as ex:
                self.status_text.current.value = f"Error: {ex}"
                self.page.update()
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
                        self.status_text.current.value = f"Queued: {self._task_queue.qsize()}"
                        self.page.update()
            except Exception as ex:
                self.status_text.current.value = f"Error: {ex}"
                self.page.update()
        else:
            self.folder_picker.get_directory_path(
                dialog_title="Add folder with videos",
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
            self.status_text.current.value = f"Queued: {self._task_queue.qsize()}"
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
            self.status_text.current.value = f"Queued: {self._task_queue.qsize()}"
            self.page.update()

    def _clear_queue(self, e):
        self._task_queue = queue.Queue()
        self.queue_list.current.controls.clear()
        self.progress_bar.current.value = 0
        self.eta_text.current.value = "ETA: --"
        self.status_text.current.value = "Idle"
        self.page.update()

    def _cancel_compress(self, e):
        self._cancel_requested = True
        self.status_text.current.value = "Cancelling..."
        try:
            if self._current_process is not None:
                self._current_process.kill()
        except Exception:
            pass
        self.page.update()

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

    def _start_compress(self, e):
        if self._task_queue.empty():
            self.status_text.current.value = "Queue is empty"
            self.page.update()
            return

        self._cancel_requested = False
        self.start_button_ref.current.visible = False
        self.cancel_button_ref.current.visible = True
        self.status_text.current.value = "Starting..."
        self.page.update()

        threading.Thread(target=self._compress_worker, daemon=True).start()

    def _compress_worker(self):
        while not self._task_queue.empty():
            if self._cancel_requested:
                break
            file_path = self._task_queue.get()
            self._ui_queue.put(("status", f"Encoding: {Path(file_path).name}"))
            try:
                self._encode_file(file_path)
            finally:
                self._task_queue.task_done()

        self._ui_queue.put(("idle",))
        self._cancel_requested = False

    def _encode_file(self, input_file):
        duration = self._get_duration_seconds(input_file)
        output_file = str(Path(input_file).with_name(Path(input_file).stem + "_compressed.mkv"))

        mode = self.mode_radio.current.value
        preset_key = self.preset_dropdown.current.value
        preset = self.PRESETS.get(preset_key, {"crf": 23, "preset": "slow"})

        cmd = [
            "ffmpeg", "-y",
            "-i", input_file,
            "-map", "0",
            "-c:v", self._encoder,
            "-profile:v", "main10",
            "-pix_fmt", "p010le",
            "-preset", preset["preset"],
        ]

        if mode == "CRF":
            cmd += ["-crf", str(preset["crf"])]
        else:
            try:
                target_gb = float(self.target_size.current.value)
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

        self._current_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )

        start = time.time()
        if self._current_process.stdout is None:
            return

        for line in self._current_process.stdout:
            if self._cancel_requested:
                try:
                    self._current_process.kill()
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
                self._ui_queue.put(("progress", progress, eta))

        self._ui_queue.put(("done",))

    def _start_ui_poller(self):
        def poll_loop():
            while True:
                updated = False
                try:
                    while True:
                        msg = self._ui_queue.get_nowait()
                        if msg[0] == "progress":
                            _, prog, eta = msg
                            self.progress_bar.current.value = prog / 100.0
                            self.eta_text.current.value = f"ETA: {eta}s"
                            updated = True
                        elif msg[0] == "status":
                            self.status_text.current.value = msg[1]
                            updated = True
                        elif msg[0] == "done":
                            self.progress_bar.current.value = 0
                            self.eta_text.current.value = "ETA: --"
                            updated = True
                        elif msg[0] == "idle":
                            self.status_text.current.value = "Idle"
                            self.start_button_ref.current.visible = True
                            self.cancel_button_ref.current.visible = False
                            self.queue_list.current.controls.clear()
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
