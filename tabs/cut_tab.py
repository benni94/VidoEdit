"""Cut/Trim Tab for VidoEdit - Extract specific time ranges from videos"""
import os
import subprocess
import platform
import threading
import queue
from pathlib import Path

import flet as ft
from ffmpeg_utils import get_ffmpeg_path, get_ffprobe_path
from components.file_input_component import FileInputComponent
from subprocess_utils import get_creation_flags
from power_management import execute_power_action

try:
    from flet import icons
except (ImportError, AttributeError):
    icons = None


VIDEO_EXTENSIONS = (".mkv", ".mp4", ".avi", ".mov", ".wmv")


class CutTab:
    """Tab for cutting/trimming videos to specific time ranges"""
    
    def __init__(self, page: ft.Page, language_manager):
        self.page = page
        self.lang_manager = language_manager
        
        self.file_input = FileInputComponent(
            page=page,
            language_manager=language_manager,
            video_extensions=VIDEO_EXTENSIONS,
            on_files_added=self._on_files_added,
            queue_height=150
        )
        
        self.time_ranges = []
        self.time_ranges_column = ft.Ref[ft.Column]()
        self.remove_ranges_checkbox = ft.Ref[ft.Checkbox]()
        self.trim_start_checkbox = ft.Ref[ft.Checkbox]()
        self.trim_end_checkbox = ft.Ref[ft.Checkbox]()
        self.trim_start_field = ft.Ref[ft.TextField]()
        self.trim_end_field = ft.Ref[ft.TextField]()
        self.trim_start_container = ft.Ref[ft.Container]()
        self.trim_end_container = ft.Ref[ft.Container]()
        self.remove_ranges_container = ft.Ref[ft.Container]()
        self.status_text = ft.Ref[ft.Text]()
        self.progress_bar = ft.Ref[ft.ProgressBar]()
        self.start_button_ref = ft.Ref[ft.ElevatedButton]()
        self.cancel_button_ref = ft.Ref[ft.ElevatedButton]()
        self.open_folder_button_ref = ft.Ref[ft.ElevatedButton]()
        
        self._current_process = None
        self._cancel_requested = False
        self._output_dir = None
        
        self._add_initial_time_range()
    
    def _c(self, light, dark):
        """Helper to get color based on theme"""
        return dark if self.page.theme_mode == ft.ThemeMode.DARK else light
    
    def _add_initial_time_range(self):
        """Add the first time range"""
        self.time_ranges.append({
            'start': ft.Ref[ft.TextField](),
            'end': ft.Ref[ft.TextField](),
            'container': ft.Ref[ft.Container]()
        })
    
    def build(self) -> ft.Control:
        """Build the Cut tab UI"""
        header = ft.Text(
            self.lang_manager.get_text("cut_trim_videos"),
            size=24,
            weight=ft.FontWeight.BOLD,
            color=self._c("#1f2937", "#e5e7eb")
        )
        
        description = ft.Text(
            self.lang_manager.get_text("cut_description"),
            size=12,
            color=self._c("#6b7280", "#9ca3af")
        )
        
        add_buttons, queue_container, power_options_row = self.file_input.build(show_multi_folder=True, show_power_options=True)
        
        # Mode selection with checkboxes
        mode_selection = ft.Column(
            [
                ft.Text(
                    self.lang_manager.get_text("cut_options"),
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=self._c("#374151", "#cdd6f4")
                ),
                ft.Checkbox(
                    ref=self.remove_ranges_checkbox,
                    label=self.lang_manager.get_text("cut_remove_ranges"),
                    value=False,
                    on_change=self._on_mode_change
                ),
                ft.Checkbox(
                    ref=self.trim_start_checkbox,
                    label=self.lang_manager.get_text("cut_trim_start"),
                    value=False,
                    on_change=self._on_mode_change
                ),
                ft.Checkbox(
                    ref=self.trim_end_checkbox,
                    label=self.lang_manager.get_text("cut_trim_end"),
                    value=False,
                    on_change=self._on_mode_change
                ),
            ],
            spacing=8
        )
        
        # Remove ranges section
        time_ranges_header = ft.Row(
            [
                ft.Text(
                    self.lang_manager.get_text("cut_time_ranges_header"),
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=self._c("#374151", "#cdd6f4")
                ),
                ft.IconButton(
                    icon=icons.ADD_CIRCLE if icons else "add_circle",
                    icon_color="#22c55e",
                    tooltip=self.lang_manager.get_text("cut_add_range_tooltip"),
                    on_click=self._add_time_range
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )
        
        time_ranges_column = ft.Column(
            ref=self.time_ranges_column,
            controls=[self._build_time_range_row(0)],
            spacing=10
        )
        
        remove_ranges_container = ft.Container(
            ref=self.remove_ranges_container,
            content=ft.Column([time_ranges_header, time_ranges_column], spacing=8),
            border=ft.border.all(1, self._c("#e5e7eb", "#313244")),
            border_radius=8,
            bgcolor=self._c("#f9fafb", "#181825"),
            padding=15,
            visible=False
        )
        
        # Trim from start section
        trim_start_field = ft.TextField(
            ref=self.trim_start_field,
            label=self.lang_manager.get_text("cut_trim_start_field"),
            hint_text="00:00:30",
            width=300,
            bgcolor=self._c("#ffffff", "#1e1e2e"),
            color=self._c("#1e1e2e", "#cdd6f4"),
            border_color="#6366f1",
            focused_border_color="#818cf8",
        )
        
        trim_start_container = ft.Container(
            ref=self.trim_start_container,
            content=ft.Column([
                ft.Text(self.lang_manager.get_text("cut_trim_start_label"), size=14, weight=ft.FontWeight.BOLD, color=self._c("#374151", "#cdd6f4")),
                trim_start_field,
                ft.Text(self.lang_manager.get_text("cut_trim_start_hint"), size=11, color=self._c("#6b7280", "#9ca3af"))
            ], spacing=8),
            border=ft.border.all(1, self._c("#e5e7eb", "#313244")),
            border_radius=8,
            bgcolor=self._c("#f9fafb", "#181825"),
            padding=15,
            visible=False
        )
        
        # Trim from end section
        trim_end_field = ft.TextField(
            ref=self.trim_end_field,
            label=self.lang_manager.get_text("cut_trim_end_field"),
            hint_text="00:00:40",
            width=300,
            bgcolor=self._c("#ffffff", "#1e1e2e"),
            color=self._c("#1e1e2e", "#cdd6f4"),
            border_color="#6366f1",
            focused_border_color="#818cf8",
        )
        
        trim_end_container = ft.Container(
            ref=self.trim_end_container,
            content=ft.Column([
                ft.Text(self.lang_manager.get_text("cut_trim_end_label"), size=14, weight=ft.FontWeight.BOLD, color=self._c("#374151", "#cdd6f4")),
                trim_end_field,
                ft.Text(self.lang_manager.get_text("cut_trim_end_hint"), size=11, color=self._c("#6b7280", "#9ca3af"))
            ], spacing=8),
            border=ft.border.all(1, self._c("#e5e7eb", "#313244")),
            border_radius=8,
            bgcolor=self._c("#f9fafb", "#181825"),
            padding=15,
            visible=False
        )
        
        start_button = ft.ElevatedButton(
            ref=self.start_button_ref,
            text=self.lang_manager.get_text("cut_start_button"),
            icon=icons.CONTENT_CUT if icons else "content_cut",
            on_click=self._start_cutting,
            style=ft.ButtonStyle(bgcolor="#22c55e", color="#ffffff"),
        )
        
        cancel_button = ft.ElevatedButton(
            ref=self.cancel_button_ref,
            text=self.lang_manager.get_text("cancel"),
            icon=icons.CANCEL if icons else "cancel",
            on_click=self._cancel_process,
            style=ft.ButtonStyle(bgcolor="#ef4444", color="#ffffff"),
            visible=False,
        )
        
        open_folder_button = ft.ElevatedButton(
            ref=self.open_folder_button_ref,
            text=self.lang_manager.get_text("open_output_folder"),
            icon=icons.FOLDER_OPEN if icons else "folder_open",
            on_click=self._open_output_folder,
            style=ft.ButtonStyle(bgcolor="#3b82f6", color="#ffffff"),
            visible=False,
        )
        
        buttons_row = ft.Row(
            [start_button, cancel_button, open_folder_button],
            spacing=10
        )
        
        status_text = ft.Text(
            ref=self.status_text,
            value="Ready",
            size=14,
            color=self._c("#374151", "#a6adc8")
        )
        
        progress_bar = ft.ProgressBar(
            ref=self.progress_bar,
            value=0,
            width=700,
            visible=False,
            color="#6366f1",
            bgcolor=self._c("#e5e7eb", "#313244")
        )
        
        progress_section = ft.Column([status_text, progress_bar], spacing=6)
        
        return ft.Column(
            [
                ft.Container(height=10),
                header,
                description,
                ft.Container(height=10),
                add_buttons,
                ft.Container(height=10),
                queue_container,
                ft.Container(height=10),
                power_options_row,
                ft.Container(height=15),
                mode_selection,
                ft.Container(height=10),
                remove_ranges_container,
                trim_start_container,
                trim_end_container,
                ft.Container(height=15),
                buttons_row,
                ft.Container(height=10),
                progress_section,
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
    
    def _build_time_range_row(self, index):
        """Build a single time range row"""
        time_range = self.time_ranges[index]
        
        start_field = ft.TextField(
            ref=time_range['start'],
            label=self.lang_manager.get_text("cut_start_time"),
            hint_text="00:00:00",
            width=150,
            bgcolor=self._c("#ffffff", "#1e1e2e"),
            color=self._c("#1e1e2e", "#cdd6f4"),
            border_color="#6366f1",
            focused_border_color="#818cf8",
        )
        
        end_field = ft.TextField(
            ref=time_range['end'],
            label=self.lang_manager.get_text("cut_end_time"),
            hint_text="00:01:00",
            width=150,
            bgcolor=self._c("#ffffff", "#1e1e2e"),
            color=self._c("#1e1e2e", "#cdd6f4"),
            border_color="#6366f1",
            focused_border_color="#818cf8",
        )
        
        remove_button = ft.IconButton(
            icon=icons.REMOVE_CIRCLE if icons else "remove_circle",
            icon_color="#ef4444",
            tooltip=self.lang_manager.get_text("cut_remove_range_tooltip"),
            on_click=lambda e, idx=index: self._remove_time_range(idx),
            visible=index > 0
        )
        
        row = ft.Row(
            [
                ft.Text(self.lang_manager.get_text("cut_range_label").format(num=index + 1), weight=ft.FontWeight.BOLD, color=self._c("#374151", "#a6adc8")),
                start_field,
                ft.Text("→", color=self._c("#6b7280", "#9ca3af")),
                end_field,
                remove_button
            ],
            spacing=10,
            alignment=ft.MainAxisAlignment.START
        )
        
        container = ft.Container(
            ref=time_range['container'],
            content=row
        )
        
        return container
    
    def _add_time_range(self, e):
        """Add a new time range"""
        index = len(self.time_ranges)
        self.time_ranges.append({
            'start': ft.Ref[ft.TextField](),
            'end': ft.Ref[ft.TextField](),
            'container': ft.Ref[ft.Container]()
        })
        
        self.time_ranges_column.current.controls.append(
            self._build_time_range_row(index)
        )
        self.page.update()
    
    def _remove_time_range(self, index):
        """Remove a time range"""
        if index > 0 and index < len(self.time_ranges):
            self.time_ranges.pop(index)
            self.time_ranges_column.current.controls.pop(index)
            
            # Rebuild all rows to update numbering
            self.time_ranges_column.current.controls.clear()
            for i in range(len(self.time_ranges)):
                self.time_ranges_column.current.controls.append(
                    self._build_time_range_row(i)
                )
            
            self.page.update()
    
    def _on_mode_change(self, e):
        """Handle mode change - show/hide sections based on checkboxes"""
        self.remove_ranges_container.current.visible = self.remove_ranges_checkbox.current.value
        self.trim_start_container.current.visible = self.trim_start_checkbox.current.value
        self.trim_end_container.current.visible = self.trim_end_checkbox.current.value
        
        self.page.update()
    
    def _on_files_added(self, count):
        """Callback when files are added"""
        self.status_text.current.value = self.lang_manager.get_text("cut_queued").format(count=self.file_input.queue_size())
        self.page.update()
    
    def _validate_time_format(self, time_str):
        """Validate time format HH:MM:SS"""
        if not time_str:
            return False
        
        parts = time_str.split(':')
        if len(parts) != 3:
            return False
        
        try:
            hours, minutes, seconds = map(int, parts)
            return 0 <= hours <= 23 and 0 <= minutes <= 59 and 0 <= seconds <= 59
        except ValueError:
            return False
    
    def _start_cutting(self, e):
        """Start cutting videos"""
        if self.file_input.is_empty():
            self.status_text.current.value = self.lang_manager.get_text("cut_error_no_files")
            self.page.update()
            return
        
        # Collect all selected modes and validate
        operations = []
        
        # Check remove ranges
        if self.remove_ranges_checkbox.current.value:
            valid_ranges = []
            for i, time_range in enumerate(self.time_ranges):
                start = time_range['start'].current.value or ""
                end = time_range['end'].current.value or ""
                
                if not start and not end:
                    continue
                
                if not self._validate_time_format(start):
                    self.status_text.current.value = self.lang_manager.get_text("cut_error_invalid_start").format(num=i + 1)
                    self.page.update()
                    return
                
                if not self._validate_time_format(end):
                    self.status_text.current.value = self.lang_manager.get_text("cut_error_invalid_end").format(num=i + 1)
                    self.page.update()
                    return
                
                valid_ranges.append((start, end))
            
            if not valid_ranges:
                self.status_text.current.value = self.lang_manager.get_text("cut_error_no_range")
                self.page.update()
                return
            
            operations.append(('remove_ranges', valid_ranges))
        
        # Check trim start
        if self.trim_start_checkbox.current.value:
            trim_time = self.trim_start_field.current.value or ""
            if not self._validate_time_format(trim_time):
                self.status_text.current.value = self.lang_manager.get_text("cut_error_invalid_trim_start")
                self.page.update()
                return
            operations.append(('trim_start', trim_time))
        
        # Check trim end
        if self.trim_end_checkbox.current.value:
            trim_time = self.trim_end_field.current.value or ""
            if not self._validate_time_format(trim_time):
                self.status_text.current.value = self.lang_manager.get_text("cut_error_invalid_trim_end")
                self.page.update()
                return
            operations.append(('trim_end', trim_time))
        
        # Check if at least one operation is selected
        if not operations:
            self.status_text.current.value = self.lang_manager.get_text("cut_error_no_option")
            self.page.update()
            return
        
        self._cancel_requested = False
        self.start_button_ref.current.visible = False
        self.cancel_button_ref.current.visible = True
        self.progress_bar.current.visible = True
        self.open_folder_button_ref.current.visible = False
        self.status_text.current.value = "Starting..."
        self.page.update()
        
        threading.Thread(
            target=self._process_queue,
            args=(operations,),
            daemon=True
        ).start()
    
    def _process_queue(self, operations):
        """Process all files in queue with parallel processing"""
        import concurrent.futures
        import time

        task_queue = self.file_input.get_queue()
        files_to_process = []

        # Collect all files to process
        while not task_queue.empty():
            files_to_process.append(task_queue.get())

        if not files_to_process:
            return

        total_files = len(files_to_process)
        processed_count = 0

        # Use ThreadPoolExecutor for parallel processing (limit to 3 concurrent threads for cut operations)
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(3, total_files)) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self._cut_video, file_path, operations): file_path
                for file_path in files_to_process
            }

            # Process completed tasks
            for future in concurrent.futures.as_completed(future_to_file):
                if self._cancel_requested:
                    # Cancel remaining tasks
                    for f in future_to_file:
                        f.cancel()
                    break

                file_path = future_to_file[future]
                processed_count += 1

                try:
                    future.result()  # This will raise an exception if the task failed
                    self.status_text.current.value = f"Completed {processed_count}/{total_files}: {Path(file_path).name}"
                    self.progress_bar.current.value = processed_count / total_files
                    # Update UI less frequently to improve performance
                    if processed_count % 3 == 0 or processed_count == total_files:
                        self.page.update()
                except Exception as ex:
                    self.status_text.current.value = f"Error processing {Path(file_path).name}: {ex}"
                    self.progress_bar.current.visible = False
                    self.start_button_ref.current.visible = True
                    self.cancel_button_ref.current.visible = False
                    self.page.update()
                    return

        if not self._cancel_requested:
            self.status_text.current.value = f"All {processed_count} files processed successfully!"
            self.open_folder_button_ref.current.visible = True
        else:
            self.status_text.current.value = "Cancelled"

        # Clear the queue after processing
        self.file_input.queue_list.current.controls.clear()

        self.progress_bar.current.visible = False
        self.start_button_ref.current.visible = True
        self.cancel_button_ref.current.visible = False
        self.page.update()
        
        # Execute power action if selected and processing completed successfully
        if not self._cancel_requested:
            power_action = self.file_input.get_power_action()
            if power_action != "none":
                action_text = self.lang_manager.get_text(f"power_{power_action}")
                self.status_text.current.value = self.lang_manager.get_text("power_executing").format(action=action_text)
                self.page.update()
                threading.Thread(target=execute_power_action, args=(power_action,), daemon=True).start()
    
    def _cut_video(self, input_file, operations):
        """Cut video by applying all selected operations in sequence"""
        input_dir = os.path.dirname(input_file)
        output_dir = os.path.join(input_dir, "edited")
        os.makedirs(output_dir, exist_ok=True)
        
        if self._output_dir is None:
            self._output_dir = output_dir
        
        filename = Path(input_file).stem
        extension = Path(input_file).suffix
        
        # Apply operations in sequence
        # Start with the original file
        current_file = input_file
        temp_files = []
        
        try:
            for i, (mode, data) in enumerate(operations):
                if self._cancel_requested:
                    break
                
                # Determine output filename for this step
                if i < len(operations) - 1:
                    # Not the last operation, use temp file
                    temp_output = os.path.join(output_dir, f"{filename}_temp_step_{i}{extension}")
                    temp_files.append(temp_output)
                else:
                    # Last operation, use final output name
                    temp_output = os.path.join(output_dir, f"{filename}_cut{extension}")
                
                if mode == "remove_ranges":
                    self._remove_ranges(current_file, temp_output, data)
                elif mode == "trim_start":
                    self._trim_from_start(current_file, temp_output, data)
                elif mode == "trim_end":
                    self._trim_from_end(current_file, temp_output, data)
                
                # Update current file for next operation
                if i < len(operations) - 1:
                    current_file = temp_output
        
        finally:
            # Clean up intermediate temp files (not the final output)
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception:
                    pass
    
    def _remove_ranges(self, input_file, output_file, time_ranges):
        """Remove specified time ranges and keep the rest using FFmpeg complex filter with progress tracking"""

        # Get video duration first
        duration = self._get_video_duration(input_file)
        if duration is None:
            raise Exception("Could not determine video duration")

        # Build segments to keep (inverse of ranges to remove)
        keep_segments = []
        current_time = 0.0

        for start_str, end_str in sorted(time_ranges, key=lambda x: self._time_to_seconds(x[0])):
            start_sec = self._time_to_seconds(start_str)
            end_sec = self._time_to_seconds(end_str)

            # Add segment before this range
            if current_time < start_sec:
                keep_segments.append((current_time, start_sec))

            current_time = max(current_time, end_sec)

        # Add final segment if there's time left
        if current_time < duration:
            keep_segments.append((current_time, duration))

        if not keep_segments:
            raise Exception("All video would be removed")

        # Use FFmpeg concat demuxer for multiple segments with progress tracking
        if len(keep_segments) == 1:
            # Simple case: single segment - most efficient
            start, end = keep_segments[0]
            cmd = [
                get_ffmpeg_path(),
                "-y",
                "-i", input_file,
                "-ss", str(start),
                "-t", str(end - start),
                "-c", "copy",
                "-progress", "pipe:1",
                "-nostats",
                output_file
            ]
        else:
            # Multiple segments: use segment extraction + concat (more reliable than complex filter)
            segment_files = []
            for i, (start, end) in enumerate(keep_segments):
                segment_file = f"{output_file}.segment{i}.ts"
                segment_files.append(segment_file)

                # Extract each segment efficiently
                segment_cmd = [
                    get_ffmpeg_path(),
                    "-y", "-hide_banner", "-loglevel", "error",  # Reduce output
                    "-i", input_file,
                    "-ss", str(start),
                    "-t", str(end - start),
                    "-c", "copy",
                    "-f", "mpegts",
                    "-avoid_negative_ts", "make_zero",
                    segment_file
                ]

                self._current_process = subprocess.Popen(
                    segment_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=get_creation_flags()
                )
                stdout, stderr = self._current_process.communicate()

                if self._cancel_requested:
                    # Clean up partial segments
                    for sf in segment_files:
                        try:
                            if os.path.exists(sf):
                                os.remove(sf)
                        except:
                            pass
                    return

                if self._current_process.returncode != 0:
                    raise Exception(f"FFmpeg segment extraction failed: {stderr[:200]}")

            # Create concat file
            concat_file = f"{output_file}.concat.txt"
            with open(concat_file, 'w', encoding='utf-8') as f:
                for segment_file in segment_files:
                    f.write(f"file '{segment_file}'\n")

            # Concatenate segments efficiently
            cmd = [
                get_ffmpeg_path(),
                "-y", "-hide_banner", "-loglevel", "error",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                "-progress", "pipe:1",
                "-nostats",
                "-avoid_negative_ts", "make_zero",
                output_file
            ]

        self._current_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=get_creation_flags()
        )

        # Monitor progress
        for line in self._current_process.stdout:
            if self._cancel_requested:
                self._current_process.kill()
                return

        stdout, stderr = self._current_process.communicate()

        if self._cancel_requested:
            return

        if self._current_process.returncode != 0:
            raise Exception(f"FFmpeg failed: {stderr[:200]}")

        # Clean up segment files and concat file
        try:
            if len(keep_segments) > 1:
                for i in range(len(keep_segments)):
                    segment_file = f"{output_file}.segment{i}.ts"
                    if os.path.exists(segment_file):
                        os.remove(segment_file)
                if os.path.exists(concat_file):
                    os.remove(concat_file)
        except Exception:
            pass
    
    def _trim_from_start(self, input_file, output_file, trim_time):
        """Remove from start until specified time with progress tracking"""

        cmd = [
            get_ffmpeg_path(),
            "-y",
            "-i", input_file,
            "-ss", trim_time,
            "-c", "copy",
            "-progress", "pipe:1",
            "-nostats",
            output_file
        ]

        self._current_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=get_creation_flags()
        )

        # Monitor progress
        for line in self._current_process.stdout:
            if self._cancel_requested:
                self._current_process.kill()
                return

        stdout, stderr = self._current_process.communicate()

        if self._cancel_requested:
            return

        if self._current_process.returncode != 0:
            raise Exception(f"FFmpeg failed: {stderr[:200]}")
    
    def _trim_from_end(self, input_file, output_file, trim_time):
        """Remove from end until specified time with progress tracking"""

        # Get duration efficiently
        duration = self._get_video_duration(input_file)

        if duration is not None:
            # Calculate end time (duration - trim_time)
            trim_seconds = self._time_to_seconds(trim_time)
            end_time = max(0, duration - trim_seconds)

            cmd = [
                get_ffmpeg_path(),
                "-y",
                "-i", input_file,
                "-t", str(end_time),
                "-c", "copy",
                "-progress", "pipe:1",
                "-nostats",
                output_file
            ]
        else:
            raise Exception("Could not determine video duration")

        self._current_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=get_creation_flags()
        )

        # Monitor progress
        for line in self._current_process.stdout:
            if self._cancel_requested:
                self._current_process.kill()
                return

        stdout, stderr = self._current_process.communicate()

        if self._cancel_requested:
            return

        if self._current_process.returncode != 0:
            raise Exception(f"FFmpeg failed: {stderr[:200]}")
    
    def _get_video_duration(self, input_file):
        """Get video duration in seconds using ffprobe efficiently"""
        try:
            cmd = [
                get_ffprobe_path(),
                "-v", "quiet",  # Less verbose output
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                input_file,
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=get_creation_flags(),
                timeout=10  # Add timeout to prevent hanging
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except subprocess.TimeoutExpired:
            print(f"ffprobe timeout for {input_file}")
        except Exception as e:
            print(f"Exception in _get_video_duration: {e}")
        return None
    
    def _time_to_seconds(self, time_str):
        """Convert HH:MM:SS to seconds"""
        parts = time_str.split(':')
        hours, minutes, seconds = map(int, parts)
        return hours * 3600 + minutes * 60 + seconds
    
    def _parse_duration_from_ffmpeg(self, stderr):
        """Parse duration from FFmpeg stderr output"""
        try:
            # Look for Duration: HH:MM:SS.ms in ffmpeg output
            # Pattern allows for more flexible matching including N/A and variable decimal places
            import re
            match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2}\.?\d*)', stderr)
            if match:
                hours = int(match.group(1))
                minutes = int(match.group(2))
                seconds = float(match.group(3))
                duration = hours * 3600 + minutes * 60 + seconds
                print(f"Parsed duration: {duration} seconds from FFmpeg output")
                return duration
            else:
                # Try to find it in a longer excerpt
                print(f"Could not parse duration. Searching in full stderr...")
                print(f"Full stderr length: {len(stderr)} chars")
                # Look for Duration anywhere in the full output
                for line in stderr.split('\n'):
                    if 'Duration:' in line:
                        print(f"Found Duration line: {line}")
                        match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2}\.?\d*)', line)
                        if match:
                            hours = int(match.group(1))
                            minutes = int(match.group(2))
                            seconds = float(match.group(3))
                            duration = hours * 3600 + minutes * 60 + seconds
                            print(f"Parsed duration: {duration} seconds")
                            return duration
        except Exception as e:
            print(f"Exception parsing FFmpeg duration: {e}")
        return None
    
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
        """Open the output directory"""
        if self._output_dir and os.path.exists(self._output_dir):
            if platform.system() == "Windows":
                os.startfile(self._output_dir)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", self._output_dir])
            else:
                subprocess.Popen(["xdg-open", self._output_dir], creationflags=get_creation_flags())
