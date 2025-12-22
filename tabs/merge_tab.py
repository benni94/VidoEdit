import os
import threading
import subprocess
import platform
import flet as ft
import re
import shlex
import shutil

try:
    from flet import icons
except (ImportError, AttributeError):
    icons = None


class MergeTab:
    def __init__(self, page: ft.Page, language_manager):
        self.page = page
        self.lang_manager = language_manager
        
        # Refs
        self.dir_field = ft.Ref[ft.TextField]()
        self.regex_field = ft.Ref[ft.TextField]()
        self.sample_field = ft.Ref[ft.TextField]()
        self.mode_radio = ft.Ref[ft.RadioGroup]()
        self.identifier_field = ft.Ref[ft.TextField]()
        self.overwrite_all_cb = ft.Ref[ft.Checkbox]()
        self.preview_list = ft.Ref[ft.ListView]()
        self.progress = ft.Ref[ft.ProgressBar]()
        self.status_text = ft.Ref[ft.Text]()
        
        # Pickers
        self.folder_picker = ft.FilePicker(on_result=self._on_folder_picked)
        page.overlay.append(self.folder_picker)

    def _c(self, light, dark):
        return dark if self.page.theme_mode == ft.ThemeMode.DARK else light

    def build(self) -> ft.Control:
        header = ft.Text(self.lang_manager.get_text("merge_videos") if hasattr(self.lang_manager, 'get_text') else "Merge Videos",
                         weight=ft.FontWeight.BOLD,
                         color=self._c("#111827", "#cdd6f4"))
        
        dir_row = ft.Row([
            ft.TextField(ref=self.dir_field, width=500, label=self.lang_manager.get_text("directory"),
                         bgcolor=self._c("#ffffff", "#1e1e2e"),
                         color=self._c("#1e1e2e", "#cdd6f4"),
                         border_color="#6366f1", focused_border_color="#818cf8"),
            ft.IconButton(icon=icons.FOLDER_OPEN if icons else "folder_open",
                          icon_color="#6366f1",
                          tooltip=self.lang_manager.get_text("choose_folder"),
                          on_click=self._open_dir_dialog)
        ], wrap=True, spacing=10)

        regex_row = ft.Row([
            ft.TextField(ref=self.regex_field, width=450, label=self.lang_manager.get_text("identifier_regex"),
                         value=DEFAULT_ID_REGEX_TEXT,
                         bgcolor=self._c("#ffffff", "#1e1e2e"),
                         color=self._c("#1e1e2e", "#cdd6f4"),
                         border_color="#6366f1", focused_border_color="#818cf8"),
            ft.TextField(ref=self.sample_field, width=230, label=self.lang_manager.get_text("output_id_sample"),
                         value="S01E10",
                         bgcolor=self._c("#ffffff", "#1e1e2e"),
                         color=self._c("#1e1e2e", "#cdd6f4"),
                         border_color="#6366f1", focused_border_color="#818cf8"),
        ], wrap=True, spacing=10)

        mode_col = ft.Column([
            ft.Text(self.lang_manager.get_text("mode"), weight=ft.FontWeight.BOLD, color=self._c("#111827", "#cdd6f4")),
            ft.RadioGroup(ref=self.mode_radio, value="BATCH",
                          content=ft.Column([
                              ft.Radio(value="BATCH", label=self.lang_manager.get_text("batch_all_episodes")),
                              ft.Radio(value="SINGLE", label=self.lang_manager.get_text("single_identifier"))
                          ]))
        ], spacing=6)

        single_row = ft.Row([
            ft.TextField(ref=self.identifier_field, width=300, label=self.lang_manager.get_text("identifier_placeholder"),
                         bgcolor=self._c("#ffffff", "#1e1e2e"),
                         color=self._c("#1e1e2e", "#cdd6f4"),
                         border_color="#6366f1", focused_border_color="#818cf8")
        ])

        opts_row = ft.Row([
            ft.Checkbox(ref=self.overwrite_all_cb, label=self.lang_manager.get_text("overwrite_all_outputs"), value=False)
        ])

        buttons = ft.Row([
            ft.ElevatedButton(text=self.lang_manager.get_text("preview"), icon="visibility",
                               on_click=self._preview, style=ft.ButtonStyle(bgcolor="#6366f1", color="#ffffff")),
            ft.ElevatedButton(text=self.lang_manager.get_text("merge"), icon="merge",
                               on_click=self._merge, style=ft.ButtonStyle(bgcolor="#22c55e", color="#ffffff")),
        ], spacing=10)

        preview = ft.Container(
            content=ft.ListView(ref=self.preview_list, spacing=4, padding=10),
            border=ft.border.all(1, self._c("#e5e7eb", "#313244")),
            border_radius=8,
            bgcolor=self._c("#f9fafb", "#181825"),
            height=200,
        )

        progress = ft.Column([
            ft.Text(ref=self.status_text, value=self.lang_manager.get_text("idle_status"), color=self._c("#374151", "#a6adc8")),
            ft.ProgressBar(ref=self.progress, value=0, width=700, visible=True, color="#6366f1",
                           bgcolor=self._c("#e5e7eb", "#313244")),
        ], spacing=6)

        return ft.Column([
            ft.Container(height=10),
            header,
            ft.Container(height=10),
            dir_row,
            ft.Container(height=10),
            regex_row,
            ft.Container(height=10),
            mode_col,
            ft.Container(height=10),
            single_row,
            ft.Container(height=10),
            opts_row,
            ft.Container(height=10),
            buttons,
            ft.Container(height=10),
            preview,
            ft.Container(height=10),
            progress,
        ], expand=True, scroll=ft.ScrollMode.AUTO)

    def _on_folder_picked(self, e: ft.FilePickerResultEvent):
        if e.path:
            self.dir_field.current.value = e.path
            self.page.update()

    def _open_dir_dialog(self, e):
        # Try macOS AppleScript first for reliability, then fall back to Flet picker
        if platform.system() == "Darwin":
            try:
                result = subprocess.run([
                    "osascript", "-e",
                    'POSIX path of (choose folder with prompt "Select folder")'
                ], capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    self.dir_field.current.value = result.stdout.strip().rstrip('/')
                    self.page.update()
                    return
            except Exception:
                pass
        # Fallback to Flet's directory picker
        try:
            self.folder_picker.get_directory_path(dialog_title="Select folder")
        except Exception:
            pass

    def _append_preview(self, text: str, color: str | None = None):
        self.preview_list.current.controls.append(ft.Text(text, size=12, color=color or self._c("#374151", "#a6adc8")))

    def _preview(self, e):
        self.preview_list.current.controls.clear()
        directory = (self.dir_field.current.value or os.getcwd()).strip()
        regex_text = self.regex_field.current.value.strip() or DEFAULT_ID_REGEX_TEXT
        patt = compile_id_regex(regex_text)
        out_sep, out_sw, out_ew = parse_output_id_sample(self.sample_field.current.value.strip() or "S01E10")
        mode = self.mode_radio.current.value

        if not os.path.isdir(directory):
            self._append_preview(self.lang_manager.get_text("dir_not_exist"), "#ef4444")
            self.page.update()
            return

        if mode == "BATCH":
            groups = scan_all_groups(directory, patt)
            if not groups:
                self._append_preview(self.lang_manager.get_text("no_episode_parts"))
            else:
                total_parts = 0
                for s, e2, lst in groups:
                    total_parts += len(lst)
                    self._append_preview(f"{format_output_id(s, e2, out_sep, out_sw, out_ew)}: {len(lst)}")
                self._append_preview(self.lang_manager.get_text("total_episodes", episodes=len(groups), parts=total_parts))
        else:
            ident = (self.identifier_field.current.value or "").strip()
            parsed = parse_identifier(ident, patt)
            if not parsed:
                self._append_preview(self.lang_manager.get_text("invalid_identifier"), "#ef4444")
            else:
                season, episode, _ = parsed
                matches = scan_matching_files(directory, patt, season, episode)
                if not matches:
                    self._append_preview(self.lang_manager.get_text("no_parts_found"))
                else:
                    for i, (p, part) in enumerate(matches, start=1):
                        self._append_preview(f"{i:2d}. {os.path.basename(p)} (part {part})")
        self.page.update()

    def _merge(self, e):
        directory = (self.dir_field.current.value or os.getcwd()).strip()
        regex_text = self.regex_field.current.value.strip() or DEFAULT_ID_REGEX_TEXT
        patt = compile_id_regex(regex_text)
        out_sep, out_sw, out_ew = parse_output_id_sample(self.sample_field.current.value.strip() or "S01E10")
        mode = self.mode_radio.current.value
        overwrite_all = self.overwrite_all_cb.current.value

        if not ensure_ffmpeg():
            self.status_text.current.value = "ffmpeg not found"
            self.page.update()
            return
        if not os.path.isdir(directory):
            self.status_text.current.value = self.lang_manager.get_text("dir_not_exist")
            self.page.update()
            return

        def worker():
            self.progress.current.value = 0
            self.status_text.current.value = self.lang_manager.get_text("starting_status")
            self.preview_list.current.controls.clear()
            self.page.update()

            try:
                if mode == "BATCH":
                    groups = scan_all_groups(directory, patt)
                    total = len(groups)
                    for idx, (s, e2, lst) in enumerate(groups, start=1):
                        inputs = [p for p, _ in lst]
                        if not inputs:
                            continue
                        out_basename = f"{format_output_id(s, e2, out_sep, out_sw, out_ew)}.mp4"
                        output_path = os.path.join(directory, out_basename)
                        if os.path.exists(output_path) and not overwrite_all:
                            output_path = next_available_name(output_path)
                        self._append_preview(self.lang_manager.get_text("merging_file", name=out_basename))
                        cmd = build_ffmpeg_concat_command(inputs, output_path, reencode=True)
                        proc = subprocess.run(cmd)
                        if proc.returncode != 0:
                            self._append_preview(self.lang_manager.get_text("ffmpeg_failed"), "#ef4444")
                        self.progress.current.value = idx / max(total, 1)
                        self.status_text.current.value = f"{idx}/{total}"
                        self.page.update()
                else:
                    ident = (self.identifier_field.current.value or "").strip()
                    parsed = parse_identifier(ident, patt)
                    if not parsed:
                        self._append_preview(self.lang_manager.get_text("invalid_identifier"), "#ef4444")
                    else:
                        s, e2, _ = parsed
                        matches = scan_matching_files(directory, patt, s, e2)
                        inputs = [p for p, _ in matches]
                        if not inputs:
                            self._append_preview(self.lang_manager.get_text("no_parts_found"), "#f97316")
                        else:
                            out_default = os.path.join(directory, f"{format_output_id(s, e2, out_sep, out_sw, out_ew)}.mp4")
                            output_path = out_default
                            if os.path.exists(output_path) and not overwrite_all:
                                output_path = next_available_name(output_path)
                            self._append_preview(self.lang_manager.get_text("merging_file", name=os.path.basename(output_path)))
                            cmd = build_ffmpeg_concat_command(inputs, output_path, reencode=True)
                            proc = subprocess.run(cmd)
                            if proc.returncode != 0:
                                self._append_preview(self.lang_manager.get_text("ffmpeg_failed"), "#ef4444")
                            self.progress.current.value = 1
                            self.status_text.current.value = self.lang_manager.get_text("done_status")
                            self.page.update()
            finally:
                self.status_text.current.value = self.lang_manager.get_text("done_status")
                self.page.update()

        threading.Thread(target=worker, daemon=True).start()

ALLOWED_EXTS = {'.mp4', '.mkv', '.mov', '.m4v', '.avi', '.webm'}
DEFAULT_ID_REGEX_TEXT = r"S(?P<season>\d{1,2})E(?P<episode>\d{2})(?P<part>[A-Z])?"
FALLBACK_SIMPLE_EP_REGEX = re.compile(r"(?i)(?P<episode>\d{2})(?P<part>[a-z])?")

def parse_output_id_sample(sample: str):
    if not sample:
        return ('E', 2, 2)
    text = sample.strip()
    m = re.match(r"(?i)^s(?P<body>.+)$", text)
    if not m:
        return ('E', 2, 2)
    body = m.group('body')
    m2 = re.match(r"^(?P<s>\d+)(?P<sep>\D+)(?P<e>\d+)$", body)
    if m2:
        s_digits = m2.group('s')
        e_digits = m2.group('e')
        sep = m2.group('sep')
        return (sep, len(s_digits), len(e_digits))
    if re.fullmatch(r"\d+", body):
        n = len(body)
        if n >= 4:
            if n % 2 == 0:
                half = n // 2
                s_digits = body[:half]
                e_digits = body[half:]
            else:
                s_digits = body[:-2]
                e_digits = body[-2:]
            return ('', len(s_digits), len(e_digits))
        elif n == 3:
            return ('', 1, 2)
        elif n == 2:
            return ('', 1, 1)
    return ('E', 2, 2)

def format_output_id(season: int, episode: int, sep: str, sw: int, ew: int) -> str:
    return f"S{season:0{sw}d}{sep}{episode:0{ew}d}"

def compile_id_regex(text: str) -> re.Pattern:
    try:
        patt = re.compile(text, re.IGNORECASE)
    except re.error:
        patt = re.compile(DEFAULT_ID_REGEX_TEXT, re.IGNORECASE)
    if not {"season", "episode"}.issubset(set(patt.groupindex.keys())):
        sample_se = re.search(r"(?i)s(?P<season>\d{1,2})e(?P<episode>\d{2})(?P<part>[a-z])?", text)
        sample_bare = re.search(r"(?i)(?P<episode>\d{1,2})(?P<part>[a-z])?", text)
        if sample_se or sample_bare:
            patt = re.compile(DEFAULT_ID_REGEX_TEXT, re.IGNORECASE)
        else:
            patt = re.compile(DEFAULT_ID_REGEX_TEXT, re.IGNORECASE)
    return patt

def parse_identifier(text: str, patt: re.Pattern):
    m = patt.search(text)
    if not m:
        return None
    season = int(m.group('season'))
    episode = int(m.group('episode'))
    part = m.groupdict().get('part')
    return season, episode, (part.upper() if part else None)

def scan_matching_files(directory: str, patt: re.Pattern, season: int, episode: int):
    matches = []
    for name in os.listdir(directory):
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            continue
        root, ext = os.path.splitext(name)
        if ext.lower() not in ALLOWED_EXTS:
            continue
        m = patt.search(name)
        if m:
            s = int(m.group('season'))
            e = int(m.group('episode'))
            if s == season and e == episode:
                part = (m.groupdict().get('part') or '').upper()
                if part:
                    matches.append((path, part))
            continue
        fm = FALLBACK_SIMPLE_EP_REGEX.search(name)
        if fm:
            s = 1
            e = int(fm.group('episode'))
            if s == season and e == episode:
                part = (fm.groupdict().get('part') or '').upper()
                if part:
                    matches.append((path, part))
    matches.sort(key=lambda t: (t[1], t[0].lower()))
    return matches

def scan_all_groups(directory: str, patt: re.Pattern):
    groups = {}
    for name in os.listdir(directory):
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            continue
        _, ext = os.path.splitext(name)
        if ext.lower() not in ALLOWED_EXTS:
            continue
        m = patt.search(name)
        if m:
            s = int(m.group('season'))
            e = int(m.group('episode'))
            part = (m.groupdict().get('part') or '').upper()
            if part:
                groups.setdefault((s, e), []).append((path, part))
            continue
        fm = FALLBACK_SIMPLE_EP_REGEX.search(name)
        if fm:
            s = 1
            e = int(fm.group('episode'))
            part = (fm.groupdict().get('part') or '').upper()
            if part:
                groups.setdefault((s, e), []).append((path, part))
    result = []
    for (s, e), lst in groups.items():
        lst.sort(key=lambda t: (t[1], t[0].lower()))
        seen = set()
        unique = []
        for p, part in lst:
            if part in seen:
                continue
            seen.add(part)
            unique.append((p, part))
        result.append((s, e, unique))
    result.sort(key=lambda x: (x[0], x[1]))
    return result

def ensure_ffmpeg() -> bool:
    return shutil.which('ffmpeg') is not None

def build_ffmpeg_concat_command(inputs, output, reencode=True, target_w=512, target_h=384, target_fps='24000/1001', target_sr=48000, target_layout='stereo'):
    args = ['ffmpeg', '-hide_banner', '-y']
    for inp in inputs:
        args += ['-i', inp]
    n = len(inputs)
    per_input_filters_v = []
    per_input_filters_a = []
    for i in range(n):
        per_input_filters_v.append(
            f"[{i}:v]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
            f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"fps={target_fps},format=yuv420p,setsar=1[v{i}]"
        )
        per_input_filters_a.append(
            f"[{i}:a]aresample={target_sr},aformat=sample_fmts=fltp:channel_layouts={target_layout}[a{i}]"
        )
    stream_pairs = ''.join(f"[v{i}][a{i}]" for i in range(n))
    filter_expr = ';'.join(per_input_filters_v + per_input_filters_a) + f";{stream_pairs}concat=n={n}:v=1:a=1[v][a]"
    args += ['-filter_complex', filter_expr, '-map', '[v]', '-map', '[a]']
    if reencode:
        args += ['-c:v', 'libx264', '-crf', '20', '-preset', 'veryfast', '-c:a', 'aac', '-b:a', '192k']
    args += [output]
    return args

def next_available_name(path: str) -> str:
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 2
    while True:
        cand = f"{base} ({i}){ext}"
        if not os.path.exists(cand):
            return cand
        i += 1
