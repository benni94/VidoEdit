"""Compress Tab - GPU-accelerated video compression"""
import os
import subprocess
import platform
import threading
import time
import queue
from pathlib import Path

import flet as ft
from ffmpeg_utils import get_ffmpeg_path, get_ffprobe_path
from components.file_input_component import FileInputComponent
from subprocess_utils import get_creation_flags

try:
    from flet import icons
except (ImportError, AttributeError):
    icons = None


class CompressTab:
    """Tab for GPU-accelerated video compression"""
    
    VIDEO_EXTENSIONS = (".mkv", ".mp4", ".avi", ".mov", ".wmv")
    
    def __init__(self, page: ft.Page, language_manager):
        self.page = page
        self.lang_manager = language_manager
        
        # UI Refs
        self.mode_radio = ft.Ref[ft.RadioGroup]()
        self.preset_dropdown = ft.Ref[ft.Dropdown]()
        self.target_size = ft.Ref[ft.TextField]()
        self.progress_bar = ft.Ref[ft.ProgressBar]()
        self.progress_text = ft.Ref[ft.Text]()
        self.status_text = ft.Ref[ft.Text]()
        self.start_button_ref = ft.Ref[ft.ElevatedButton]()
        self.cancel_button_ref = ft.Ref[ft.ElevatedButton]()
        self.open_folder_button_ref = ft.Ref[ft.ElevatedButton]()
        
        # Track output directory
        self._output_dir = None
        
        # State
        self._ui_queue: "queue.Queue[tuple]" = queue.Queue()
        self._cancel_requested = False
        self._current_process = None
        self._encoder = self._detect_gpu_encoder()
        
        # File input component
        self.file_input = FileInputComponent(
            page=page,
            language_manager=language_manager,
            video_extensions=self.VIDEO_EXTENSIONS,
            on_files_added=self._on_files_added,
            queue_height=200
        )
    
    def _c(self, light, dark):
        return dark if self.page.theme_mode == ft.ThemeMode.DARK else light

    def build(self) -> ft.Control:
        """Build and return the tab content"""
        self._start_ui_poller()
        
        preset_options = [
            self.lang_manager.get_text("preset_plex"),
            self.lang_manager.get_text("preset_fast"),
            self.lang_manager.get_text("preset_film"),
            self.lang_manager.get_text("preset_anime"),
            self.lang_manager.get_text("preset_4k"),
        ]
        preset_mapping = {
            self.lang_manager.get_text("preset_fast"): {"crf": 26, "preset": "fast"},
            self.lang_manager.get_text("preset_plex"): {"crf": 24, "preset": "medium"},
            self.lang_manager.get_text("preset_film"): {"crf": 23, "preset": "slow"},
            self.lang_manager.get_text("preset_anime"): {"crf": 20, "preset": "veryslow"},
            self.lang_manager.get_text("preset_4k"): {"crf": 22, "preset": "slow"},
        }
        self._preset_mapping = preset_mapping
        
        encoder_row = ft.Row([
            ft.Text(self.lang_manager.get_text("encoder"), width=120, color=self._c("#1e1e2e", "#cdd6f4")),
            ft.Text(self._encoder, color=self._c("#374151", "#a6adc8")),
        ])

        add_buttons, queue_container = self.file_input.build()

        mode_section = ft.Column(
            [
                ft.Text(self.lang_manager.get_text("mode"), weight=ft.FontWeight.BOLD, color=self._c("#111827", "#cdd6f4")),
                ft.RadioGroup(
                    ref=self.mode_radio,
                    value="CRF",
                    content=ft.Column(
                        [
                            ft.Radio(value="CRF", label="CRF"),
                            ft.Radio(value="SIZE", label=self.lang_manager.get_text("target_size")),
                        ]
                    ),
                ),
                ft.TextField(
                    ref=self.target_size,
                    value="5",
                    label=self.lang_manager.get_text("target_size"),
                    width=200,
                    border_color="#6366f1",
                    focused_border_color="#818cf8",
                    color=self._c("#1e1e2e", "#cdd6f4"),
                    bgcolor=self._c("#ffffff", "#1e1e2e"),
                ),
            ],
            spacing=6,
        )

        preset_row = ft.Row([
            ft.Text(self.lang_manager.get_text("presets"), width=120, color=self._c("#1e1e2e", "#cdd6f4")),
            ft.Dropdown(
                ref=self.preset_dropdown,
                width=600,
                value=preset_options[0],
                options=[ft.dropdown.Option(k, k) for k in preset_options],
                border_color="#6366f1",
                focused_border_color="#818cf8",
                color=self._c("#1e1e2e", "#cdd6f4"),
                bgcolor=self._c("#ffffff", "#1e1e2e"),
            )
        ], wrap=True)

        progress_section = ft.Column(
            [
                ft.Text(
                    ref=self.progress_text,
                    value=self.lang_manager.get_text("idle"),
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color="#6366f1",
                ),
                ft.ProgressBar(
                    ref=self.progress_bar,
                    value=0,
                    width=700,
                    visible=True,
                    color="#6366f1",
                    bgcolor=self._c("#e5e7eb", "#313244"),
                ),
                ft.Text(ref=self.status_text, value=self.lang_manager.get_text("idle"), color=self._c("#374151", "#a6adc8")),
            ],
            spacing=6,
        )

        start_cancel_row = ft.Row(
            [
                ft.ElevatedButton(
                    ref=self.start_button_ref,
                    text=self.lang_manager.get_text("start"),
                    icon=icons.PLAY_ARROW if icons else "play_arrow",
                    on_click=self._start_compress,
                    style=ft.ButtonStyle(color="#ffffff", bgcolor="#22c55e"),
                    visible=True,
                ),
                ft.ElevatedButton(
                    ref=self.cancel_button_ref,
                    text=self.lang_manager.get_text("cancel"),
                    icon=icons.CLOSE if icons else "close",
                    on_click=self._cancel_compress,
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
                [get_ffmpeg_path(), "-encoders"],
                stderr=subprocess.DEVNULL,
                text=True,
                creationflags=get_creation_flags(),
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
    
    def _on_files_added(self, count):
        """Callback when files are added to the queue"""
        self.status_text.current.value = f"Queued: {self.file_input.queue_size()}"
        self.page.update()
    
    def _get_duration_seconds(self, path):
        out = subprocess.check_output(
            [
                get_ffprobe_path(), "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            text=True,
            creationflags=get_creation_flags(),
        )
        return float(out.strip())

    def _calculate_bitrate_kbps(self, duration, target_gb):
        target_bits = target_gb * 1024**3 * 8
        total_kbps = target_bits / duration / 1000
        return max(int(total_kbps), 500)

    def _open_output_folder(self, e):
        """Open the output directory in file explorer"""
        if self._output_dir and os.path.exists(self._output_dir):
            if platform.system() == "Windows":
                os.startfile(self._output_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", self._output_dir])
            else:  # Linux
                subprocess.Popen(["xdg-open", self._output_dir])
    
    def _start_compress(self, e):
        if self.file_input.is_empty():
            self.status_text.current.value = "Queue is empty"
            self.page.update()
            return

        # Reset output directory
        self._output_dir = None
        self._cancel_requested = False
        self.start_button_ref.current.visible = False
        self.cancel_button_ref.current.visible = True
        self.open_folder_button_ref.current.visible = False
        self.progress_text.current.value = "Starting..."
        self.status_text.current.value = "Starting..."
        self.page.update()

        threading.Thread(target=self._compress_worker, daemon=True).start()
    
    def _cancel_compress(self, e):
        self._cancel_requested = True
        self._output_dir = None
        if self._current_process:
            try:
                self._current_process.kill()
            except Exception:
                pass

    def _compress_worker(self):
        task_queue = self.file_input.get_queue()
        while not task_queue.empty():
            if self._cancel_requested:
                break
            file_path = task_queue.get()
            self._ui_queue.put(("status", f"Encoding: {Path(file_path).name}"))
            try:
                self._encode_file(file_path)
            finally:
                task_queue.task_done()

        self._ui_queue.put(("idle",))
        self._cancel_requested = False

    def _encode_file(self, input_file):
        duration = self._get_duration_seconds(input_file)
        
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

        mode = self.mode_radio.current.value
        preset_key = self.preset_dropdown.current.value
        preset = self._preset_mapping.get(preset_key, {"crf": 23, "preset": "slow"})

        cmd = [
            get_ffmpeg_path(), "-y",
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
            creationflags=get_creation_flags(),
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
                self._ui_queue.put(("progress", progress))

        self._ui_queue.put(("done",))

    def _start_ui_poller(self):
        def poll_loop():
            while True:
                updated = False
                try:
                    while True:
                        msg = self._ui_queue.get_nowait()
                        if msg[0] == "progress":
                            _, prog = msg
                            self.progress_bar.current.value = prog / 100.0
                            self.progress_text.current.value = self.lang_manager.get_text("compressing", percent=int(prog))
                            updated = True
                        elif msg[0] == "status":
                            self.status_text.current.value = msg[1]
                            updated = True
                        elif msg[0] == "done":
                            self.progress_bar.current.value = 0
                            self.progress_text.current.value = self.lang_manager.get_text("idle")
                            updated = True
                        elif msg[0] == "idle":
                            self.status_text.current.value = self.lang_manager.get_text("idle")
                            self.progress_text.current.value = self.lang_manager.get_text("idle")
                            self.start_button_ref.current.visible = True
                            self.cancel_button_ref.current.visible = False
                            # Show open folder button if output directory exists
                            if self._output_dir and os.path.exists(self._output_dir):
                                self.open_folder_button_ref.current.visible = True
                            else:
                                self.open_folder_button_ref.current.visible = False
                            self.file_input.queue_list.current.controls.clear()
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
