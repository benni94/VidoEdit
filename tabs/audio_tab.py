"""Audio Tab - Select and remove audio tracks from video files"""
import os
import subprocess
import platform
import threading
import json
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


class AudioTab:
    """Tab for selecting and removing audio tracks from video files"""
    
    VIDEO_EXTENSIONS = (".mkv", ".mp4", ".avi", ".mov", ".wmv")
    
    def __init__(self, page: ft.Page, language_manager):
        self.page = page
        self.lang_manager = language_manager
        
        # UI Refs
        self.audio_tracks_column = ft.Ref[ft.Column]()
        self.audio_tracks_row = ft.Ref[ft.Row]()
        self.audio_tracks_container = ft.Ref[ft.Container]()
        self.progress_bar = ft.Ref[ft.ProgressBar]()
        self.status_text = ft.Ref[ft.Text]()
        self.start_button_ref = ft.Ref[ft.ElevatedButton]()
        self.process_button_ref = ft.Ref[ft.ElevatedButton]()
        self.cancel_button_ref = ft.Ref[ft.ElevatedButton]()
        self.open_folder_button_ref = ft.Ref[ft.ElevatedButton]()
        self.select_all_checkbox = ft.Ref[ft.Checkbox]()
        
        # Track output directory
        self._output_dir = None
        
        # State
        self._current_file = None
        self._audio_tracks = []
        self._track_checkboxes = {}
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
        
        audio_tracks_container = ft.Container(
            ref=self.audio_tracks_container,
            content=ft.Column(
                ref=self.audio_tracks_column,
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
            ),
            border=ft.border.all(1, self._c("#e5e7eb", "#313244")),
            border_radius=8,
            bgcolor=self._c("#f9fafb", "#181825"),
            padding=15,
            height=300,
            expand=False,
            visible=False,
        )
        
        progress_section = ft.Column(
            [
                ft.ProgressBar(
                    ref=self.progress_bar,
                    value=0,
                    width=700,
                    visible=False,
                    color="#6366f1",
                    bgcolor=self._c("#e5e7eb", "#313244"),
                ),
                ft.Text(
                    ref=self.status_text,
                    value=self.lang_manager.get_text("idle") if hasattr(self.lang_manager, 'get_text') else "Idle",
                    color=self._c("#374151", "#a6adc8")
                ),
            ],
            spacing=6,
        )
        
        action_buttons = ft.Row(
            [
                ft.ElevatedButton(
                    ref=self.process_button_ref,
                    text="Process All Files in Queue",
                    icon=icons.PLAY_ARROW if icons else "play_arrow",
                    on_click=self._start_processing_queue,
                    style=ft.ButtonStyle(color="#ffffff", bgcolor="#22c55e"),
                    visible=False,
                ),
                ft.ElevatedButton(
                    ref=self.cancel_button_ref,
                    text=self.lang_manager.get_text("cancel"),
                    icon=icons.CLOSE if icons else "close",
                    on_click=self._cancel_process,
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
            wrap=True,
        )
        
        return ft.Column(
            [
                ft.Container(height=10),
                add_buttons,
                ft.Container(height=10),
                queue_container,
                ft.Container(height=10),
                ft.ElevatedButton(
                    ref=self.start_button_ref,
                    text=self.lang_manager.get_text("detect_audio_tracks"),
                    icon=icons.SEARCH if icons else "search",
                    on_click=self._detect_tracks_from_first_file,
                    style=ft.ButtonStyle(color="#ffffff", bgcolor="#6366f1"),
                    visible=True,
                ),
                ft.Container(height=10),
                ft.Row(
                    ref=self.audio_tracks_row,
                    controls=[
                        ft.Text(
                            self.lang_manager.get_text("audio_tracks_label"),
                            weight=ft.FontWeight.BOLD,
                            color=self._c("#111827", "#cdd6f4")
                        ),
                        ft.Checkbox(
                            ref=self.select_all_checkbox,
                            label="Select/Deselect All",
                            value=True,
                            on_change=self._toggle_all_tracks,
                            visible=False,
                            label_style=ft.TextStyle(color=self._c("#1f2937", "#e5e7eb")),
                        ),
                    ],
                    spacing=20,
                    visible=False,
                ),
                audio_tracks_container,
                ft.Container(height=10),
                progress_section,
                ft.Container(height=10),
                action_buttons,
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
    
    def _on_files_added(self, count):
        """Callback when files are added to the queue"""
        self.status_text.current.value = f"Queued: {self.file_input.queue_size()}"
        self.page.update()
    
    def _toggle_all_tracks(self, e):
        """Toggle all audio track checkboxes"""
        select_all = self.select_all_checkbox.current.value
        for checkbox in self._track_checkboxes.values():
            checkbox.value = select_all
        self.page.update()

    def _detect_tracks_from_first_file(self, e):
        """Detect audio tracks from the first file in queue"""
        if self.file_input.is_empty():
            self.status_text.current.value = "Queue is empty - add files first"
            self.page.update()
            return
        
        # Get first file from queue to detect audio tracks
        task_queue = self.file_input.get_queue()
        file_path = task_queue.queue[0]  # Peek at first item
        
        self._current_file = file_path
        self.status_text.current.value = f"Detecting audio tracks from: {Path(file_path).name}"
        self.page.update()
        
        # Run detection in background thread
        threading.Thread(target=self._detect_audio_tracks, args=(file_path,), daemon=True).start()

    def _detect_audio_tracks(self, file_path):
        """Detect audio tracks using ffprobe"""
        try:
            result = subprocess.run(
                [
                    get_ffprobe_path(),
                    "-v", "error",
                    "-print_format", "json",
                    "-show_streams",
                    "-select_streams", "a",
                    file_path
                ],
                capture_output=True,
                text=True,
                creationflags=get_creation_flags(),
            )
            
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else "Unknown error"
                self._ui_queue.put(("error", f"FFprobe failed: {error_msg[:100]}"))
                return
            
            if not result.stdout.strip():
                self._ui_queue.put(("error", "FFprobe returned no data"))
                return
            
            data = json.loads(result.stdout)
            streams = data.get("streams", [])
            
            if not streams:
                self._ui_queue.put(("error", "No audio tracks found in file"))
                return
            
            self._audio_tracks = []
            for stream in streams:
                track_info = {
                    "index": stream.get("index"),
                    "codec": stream.get("codec_name", "unknown"),
                    "channels": stream.get("channels", "unknown"),
                    "language": stream.get("tags", {}).get("language", "und"),
                    "title": stream.get("tags", {}).get("title", ""),
                }
                self._audio_tracks.append(track_info)
            
            self._ui_queue.put(("tracks_loaded", self._audio_tracks))
            
        except Exception as ex:
            self._ui_queue.put(("error", f"Error detecting tracks: {ex}"))

    def _display_audio_tracks(self, tracks):
        """Display audio tracks with checkboxes"""
        self.audio_tracks_column.current.controls.clear()
        self._track_checkboxes.clear()
        
        if not tracks:
            self.audio_tracks_column.current.controls.append(
                ft.Text("No audio tracks found", color=self._c("#374151", "#a6adc8"))
            )
            self.status_text.current.value = "No audio tracks found in this file"
        else:
            self.status_text.current.value = f"Found {len(tracks)} audio track(s) - Select tracks to keep"
            for i, track in enumerate(tracks):
                # Build detailed track label
                track_label = f"Track {i+1} (Stream #{track['index']}): {track['codec'].upper()}"
                
                # Always show channels
                if track['channels'] != "unknown":
                    track_label += f" | {track['channels']} ch"
                
                # Always show language (even if undefined)
                lang = track['language'] if track['language'] != "und" else "Unknown"
                track_label += f" | Lang: {lang}"
                
                # Show title if available
                if track['title']:
                    track_label += f" | {track['title']}"
                
                checkbox = ft.Checkbox(
                    label=track_label,
                    value=True,
                    label_style=ft.TextStyle(
                        color=self._c("#1f2937", "#e5e7eb"),
                        size=13,
                    ),
                )
                self._track_checkboxes[track['index']] = checkbox
                self.audio_tracks_column.current.controls.append(checkbox)
            
            # Show process button, select all checkbox, and audio tracks section
            self.process_button_ref.current.text = f"Process All Files in Queue ({self.file_input.queue_size()})"
            self.process_button_ref.current.visible = True
            self.select_all_checkbox.current.visible = True
            self.select_all_checkbox.current.value = True
            self.audio_tracks_row.current.visible = True
            self.audio_tracks_container.current.visible = True
        
        self.page.update()

    def _start_processing_queue(self, e):
        """Start processing all files in queue with selected audio tracks"""
        if not self._audio_tracks or not self._track_checkboxes:
            self.status_text.current.value = "No audio tracks detected"
            self.page.update()
            return
        
        # Get selected track indices
        selected_indices = [
            index for index, checkbox in self._track_checkboxes.items()
            if checkbox.value
        ]
        
        if not selected_indices:
            self.status_text.current.value = "Error: At least one audio track must be selected"
            self.page.update()
            return
        
        # Check if all tracks are selected (no processing needed)
        if len(selected_indices) == len(self._audio_tracks):
            self.status_text.current.value = "All tracks selected - no processing needed"
            self.page.update()
            return
        
        # Store selected indices for batch processing
        self._selected_track_indices = selected_indices
        
        self._cancel_requested = False
        self.start_button_ref.current.visible = False
        self.cancel_button_ref.current.visible = True
        self.progress_bar.current.visible = True
        self.audio_tracks_column.current.controls.clear()
        self.status_text.current.value = "Processing queue..."
        self.page.update()
        
        # Start processing worker
        threading.Thread(target=self._process_queue_worker, daemon=True).start()
    
    def _process_queue_worker(self):
        """Process all files in queue"""
        task_queue = self.file_input.get_queue()
        while not task_queue.empty():
            if self._cancel_requested:
                break
            
            file_path = task_queue.get()
            
            self._ui_queue.put(("processing", Path(file_path).name))
            
            try:
                self._process_single_file(file_path, self._selected_track_indices)
            except Exception as ex:
                self._ui_queue.put(("error", f"Error processing {Path(file_path).name}: {ex}"))
                break
        
        if not self._cancel_requested:
            self._ui_queue.put(("all_done",))
        else:
            self._ui_queue.put(("cancelled",))
    

    def _process_single_file(self, input_file, selected_indices):
        """Worker thread to process the file"""
        try:
            # Create 'edited' subfolder in the same directory as input file
            input_dir = os.path.dirname(input_file)
            output_dir = os.path.join(input_dir, "edited")
            os.makedirs(output_dir, exist_ok=True)
            
            # Store output directory for opening later
            if self._output_dir is None:
                self._output_dir = output_dir
            
            # Get filename and create output path
            filename = os.path.basename(input_file)
            output_file = os.path.join(output_dir, filename)
            
            # Build FFmpeg command
            cmd = [get_ffmpeg_path(), "-y", "-i", input_file]
            
            # Map video stream
            cmd.extend(["-map", "0:v"])
            
            # Map selected audio streams
            for index in selected_indices:
                cmd.extend(["-map", f"0:{index}"])
            
            # Map subtitle streams
            cmd.extend(["-map", "0:s?"])
            
            # Copy all streams without re-encoding
            cmd.extend(["-c", "copy"])
            
            cmd.append(output_file)
            
            self._current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=get_creation_flags(),
            )
            
            # Wait for process to complete
            stdout, stderr = self._current_process.communicate()
            
            if self._cancel_requested:
                self._ui_queue.put(("cancelled",))
                return
            
            if self._current_process.returncode == 0:
                # Success - file already removed from queue by worker loop
                pass
            else:
                raise Exception(f"FFmpeg failed: {stderr[:200]}")
                
        except Exception as ex:
            self._ui_queue.put(("error", f"Error: {ex}"))

    def _cancel_process(self, e):
        """Cancel the current process"""
        self._cancel_requested = True
        self._output_dir = None
        if self._current_process:
            try:
                self._current_process.kill()
            except Exception:
                pass

    def _open_output_folder(self, e):
        """Open the output directory in file explorer"""
        if self._output_dir and os.path.exists(self._output_dir):
            if platform.system() == "Windows":
                os.startfile(self._output_dir)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", self._output_dir])
            else:
                creationflags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
                subprocess.Popen(["xdg-open", self._output_dir], creationflags=creationflags)

    def _start_ui_poller(self):
        """Start the UI update poller"""
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
                        if msg[0] == "tracks_loaded":
                            self._display_audio_tracks(msg[1])
                            updated = True
                        elif msg[0] == "processing":
                            self.status_text.current.value = f"Processing: {msg[1]}"
                            # Update queue list - remove first item
                            if self.file_input.queue_list.current.controls:
                                self.file_input.queue_list.current.controls.pop(0)
                            updated = True
                        elif msg[0] == "all_done":
                            self.status_text.current.value = "All files processed!"
                            self.progress_bar.current.visible = False
                            self.start_button_ref.current.visible = True
                            self.cancel_button_ref.current.visible = False
                            self.open_folder_button_ref.current.visible = True
                            self.file_input.queue_list.current.controls.clear()
                            updated = True
                        elif msg[0] == "error":
                            self.status_text.current.value = msg[1]
                            self.progress_bar.current.visible = False
                            self.start_button_ref.current.visible = True
                            self.cancel_button_ref.current.visible = False
                            updated = True
                        elif msg[0] == "cancelled":
                            self.status_text.current.value = "Cancelled"
                            self.progress_bar.current.visible = False
                            self.start_button_ref.current.visible = True
                            self.cancel_button_ref.current.visible = False
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
