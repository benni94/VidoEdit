import os
import threading
import platform
import subprocess
import flet as ft
import re
from typing import List, Tuple, Dict, Optional

try:
    from flet import icons
except (ImportError, AttributeError):
    icons = None


class RenamerTab:
    def __init__(self, page: ft.Page, language_manager):
        self.page = page
        self.lang_manager = language_manager

        # Refs
        self.dir_field = ft.Ref[ft.TextField]()
        self.regex_field = ft.Ref[ft.TextField]()
        self.template_field = ft.Ref[ft.TextField]()
        self.use_parsed_radio = ft.Ref[ft.RadioGroup]()
        self.start_season = ft.Ref[ft.TextField]()
        self.start_episode = ft.Ref[ft.TextField]()
        self.preview_list = ft.Ref[ft.ListView]()
        self.progress = ft.Ref[ft.ProgressBar]()
        self.status_text = ft.Ref[ft.Text]()

        # Picker
        self.folder_picker = ft.FilePicker(on_result=self._on_folder_picked)
        page.overlay.append(self.folder_picker)

    def _c(self, light, dark):
        return dark if self.page.theme_mode == ft.ThemeMode.DARK else light

    def build(self) -> ft.Control:
        header = ft.Text(self.lang_manager.get_text("renamer") if hasattr(self.lang_manager, 'get_text') else "Renamer",
                         weight=ft.FontWeight.BOLD,
                         color=self._c("#111827", "#cdd6f4"))

        dir_row = ft.Row([
            ft.TextField(ref=self.dir_field, width=500, label=self.lang_manager.get_text("directory"),
                         bgcolor=self._c("#ffffff", "#1e1e2e"), color=self._c("#1e1e2e", "#cdd6f4"),
                         border_color="#6366f1", focused_border_color="#818cf8"),
            ft.IconButton(icon=icons.FOLDER_OPEN if icons else "folder_open", icon_color="#6366f1",
                          tooltip=self.lang_manager.get_text("choose_folder"),
                          on_click=self._open_dir_dialog)
        ], wrap=True, spacing=10)

        regex_row = ft.Row([
            ft.TextField(ref=self.regex_field, width=500, label=self.lang_manager.get_text("identifier_regex"),
                         value=DEFAULT_REGEX,
                         bgcolor=self._c("#ffffff", "#1e1e2e"), color=self._c("#1e1e2e", "#cdd6f4"),
                         border_color="#6366f1", focused_border_color="#818cf8"),
        ])

        template_row = ft.Row([
            ft.TextField(ref=self.template_field, width=600, label=self.lang_manager.get_text("new_name_template"),
                         value="Episode {episode} Staffel {season}",
                         bgcolor=self._c("#ffffff", "#1e1e2e"), color=self._c("#1e1e2e", "#cdd6f4"),
                         border_color="#6366f1", focused_border_color="#818cf8"),
        ])

        mode_col = ft.Column([
            ft.Text(self.lang_manager.get_text("numbering_mode"), weight=ft.FontWeight.BOLD, color=self._c("#111827", "#cdd6f4")),
            ft.RadioGroup(ref=self.use_parsed_radio, value="PARSED",
                          content=ft.Column([
                              ft.Radio(value="PARSED", label=self.lang_manager.get_text("use_parsed_numbers")),
                              ft.Radio(value="MANUAL", label=self.lang_manager.get_text("manual_start_numbers")),
                          ]))
        ], spacing=6)

        manual_row = ft.Row([
            ft.TextField(ref=self.start_season, width=140, label=self.lang_manager.get_text("start_season"), value="1",
                         bgcolor=self._c("#ffffff", "#1e1e2e"), color=self._c("#1e1e2e", "#cdd6f4"),
                         border_color="#6366f1", focused_border_color="#818cf8"),
            ft.TextField(ref=self.start_episode, width=160, label=self.lang_manager.get_text("start_episode"), value="1",
                         bgcolor=self._c("#ffffff", "#1e1e2e"), color=self._c("#1e1e2e", "#cdd6f4"),
                         border_color="#6366f1", focused_border_color="#818cf8"),
        ], spacing=10)

        buttons = ft.Row([
            ft.ElevatedButton(text=self.lang_manager.get_text("preview"), icon=icons.PREVIEW if icons else "visibility",
                               on_click=self._preview, style=ft.ButtonStyle(bgcolor="#6366f1", color="#ffffff")),
            ft.ElevatedButton(text=self.lang_manager.get_text("rename"), icon=icons.DRIVE_FILE_RENAME_OUTLINE if icons else "drive_file_rename_outline",
                               on_click=self._rename, style=ft.ButtonStyle(bgcolor="#22c55e", color="#ffffff")),
        ], spacing=10)

        preview = ft.Container(
            content=ft.ListView(ref=self.preview_list, spacing=4, padding=10),
            border=ft.border.all(1, self._c("#e5e7eb", "#313244")),
            border_radius=8,
            bgcolor=self._c("#f9fafb", "#181825"),
            height=220,
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
            template_row,
            ft.Container(height=10),
            mode_col,
            ft.Container(height=10),
            manual_row,
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
        try:
            self.folder_picker.get_directory_path(dialog_title="Select folder")
        except Exception:
            pass

    def _append_preview(self, text: str, color: str | None = None):
        self.preview_list.current.controls.append(ft.Text(text, size=12, color=color or self._c("#374151", "#a6adc8")))

    def _preview(self, e):
        self.preview_list.current.controls.clear()
        directory = (self.dir_field.current.value or os.getcwd()).strip()
        regex_text = (self.regex_field.current.value or DEFAULT_REGEX).strip()
        try:
            pattern = re.compile(regex_text)
        except re.error as ex:
            self._append_preview(f"{self.lang_manager.get_text('invalid_regex')}: {ex}", "#ef4444")
            self.page.update()
            return
        # Ensure required groups exist
        required_groups = {"season", "episode"}
        if not required_groups.issubset(set(pattern.groupindex.keys())):
            try:
                pattern = re.compile(DEFAULT_REGEX)
                self._append_preview(self.lang_manager.get_text("identifier_missing_groups_default_used"), "#f97316")
            except Exception:
                self._append_preview("Internal error compiling default pattern.", "#ef4444")
                self.page.update()
                return

        if not os.path.isdir(directory):
            self._append_preview(self.lang_manager.get_text("dir_not_exist"), "#ef4444")
            self.page.update()
            return

        files = scan_files(directory)
        plan = compute_plan(directory, files, pattern, self.template_field.current.value or "Episode {episode} Staffel {season}",
                               use_parsed=(self.use_parsed_radio.current.value == "PARSED"),
                               start_season=int(self.start_season.current.value or 1),
                               start_episode=int(self.start_episode.current.value or 1))
        if not plan:
            self._append_preview(self.lang_manager.get_text("nothing_to_rename"))
        else:
            width = max(len(src) for src, _ in plan)
            for src, tgt in plan:
                self._append_preview(f"{src.ljust(width)}  ->  {tgt}")
        self.page.update()

    def _rename(self, e):
        directory = (self.dir_field.current.value or os.getcwd()).strip()
        regex_text = (self.regex_field.current.value or DEFAULT_REGEX).strip()
        try:
            pattern = re.compile(regex_text)
        except re.error as ex:
            self.status_text.current.value = f"{self.lang_manager.get_text('invalid_regex')}: {ex}"
            self.page.update()
            return
        # Ensure required groups exist
        required_groups = {"season", "episode"}
        if not required_groups.issubset(set(pattern.groupindex.keys())):
            pattern = re.compile(DEFAULT_REGEX)

        if not os.path.isdir(directory):
            self.status_text.current.value = self.lang_manager.get_text("dir_not_exist")
            self.page.update()
            return

        def worker():
            self.status_text.current.value = self.lang_manager.get_text("starting_status")
            self.progress.current.value = 0
            self.preview_list.current.controls.clear()
            self.page.update()
            try:
                files = scan_files(directory)
                plan = compute_plan(directory, files, pattern, self.template_field.current.value or "Episode {episode} Staffel {season}",
                                       use_parsed=(self.use_parsed_radio.current.value == "PARSED"),
                                       start_season=int(self.start_season.current.value or 1),
                                       start_episode=int(self.start_episode.current.value or 1))
                if not plan:
                    self._append_preview(self.lang_manager.get_text("nothing_to_rename"))
                    return
                ok, errors = check_conflicts(directory, plan)
                if not ok:
                    self._append_preview(self.lang_manager.get_text("conflicts_detected"), "#ef4444")
                    for err in errors:
                        self._append_preview(f"- {err}", "#ef4444")
                    return
                apply_plan(directory, plan)
                for src, tgt in plan:
                    self._append_preview(f"{src} -> {tgt}")
                self.progress.current.value = 1
                self.status_text.current.value = self.lang_manager.get_text("done_status")
                self.page.update()
            finally:
                self.page.update()

        threading.Thread(target=worker, daemon=True).start()

DEFAULT_REGEX = r"S(?P<season>\d{2})E(?P<episode>\d{2})(?P<part>[A-Za-z])?"
FALLBACK_SIMPLE_EP_REGEX = re.compile(r"(?P<episode>\d{2})(?P<part>[A-Za-z])?")

PartOrder = {chr(c): i for i, c in enumerate(range(ord('A'), ord('Z')+1), start=1)}

def scan_files(directory: str) -> List[str]:
    files = []
    for name in os.listdir(directory):
        path = os.path.join(directory, name)
        if os.path.isfile(path):
            files.append(name)
    return files

def parse_identifier(name: str, pattern: re.Pattern) -> Optional[Tuple[int, int, Optional[str]]]:
    m = pattern.search(name)
    if m:
        season = int(m.group('season'))
        episode = int(m.group('episode'))
        part = m.groupdict().get('part')
        if part:
            part = part.upper()
        return season, episode, part
    fm = FALLBACK_SIMPLE_EP_REGEX.search(name)
    if fm:
        season = 1
        episode = int(fm.group('episode'))
        part = fm.groupdict().get('part')
        if part:
            part = part.upper()
        return season, episode, part
    return None

def sort_key(item: Tuple[str, Tuple[int, int, Optional[str]]]):
    name, (season, episode, part) = item
    part_rank = PartOrder.get(part, 0) if part else 0
    return (season, episode, part_rank, name.lower())

def build_numbering(parsed: List[Tuple[str, int, int, Optional[str]]], use_parsed: bool,
                    start_season: int, start_episode: int) -> Dict[str, Tuple[int, int, Optional[str]]]:
    mapping: Dict[str, Tuple[int, int, Optional[str]]] = {}
    cur_season = start_season
    cur_episode = start_episode
    for idx, (fname, p_season, p_episode, p_part) in enumerate(parsed, start=1):
        if use_parsed:
            mapping[fname] = (p_season, p_episode, p_part)
        else:
            mapping[fname] = (cur_season, cur_episode, p_part)
            cur_episode += 1
    return mapping

def render_new_name(template: str, season: int, episode: int, part: Optional[str], index: int, ext: str) -> str:
    return template.format(season=season, episode=episode, part=(part or ''), index=index, ext=ext)

def compute_plan(directory: str, files: List[str], pattern: re.Pattern, template: str,
                 use_parsed: bool, start_season: int, start_episode: int) -> List[Tuple[str, str]]:
    parsed: List[Tuple[str, int, int, Optional[str]]] = []
    skipped: List[str] = []
    for f in files:
        res = parse_identifier(f, pattern)
        if res:
            parsed.append((f, res[0], res[1], res[2]))
        else:
            skipped.append(f)
    if not parsed:
        return []
    parsed_sorted = sorted(parsed, key=lambda x: sort_key((x[0], (x[1], x[2], x[3]))))
    numbering = build_numbering(parsed_sorted, use_parsed, start_season, start_episode)
    plan: List[Tuple[str, str]] = []
    for idx, (fname, _, _, _) in enumerate(parsed_sorted, start=1):
        season, episode, part = numbering[fname]
        root, ext = os.path.splitext(fname)
        new_base = render_new_name(template, season, episode, part, idx, ext.lstrip('.'))
        target = f"{new_base}.{ext.lstrip('.')}" if '{ext' not in template and not new_base.endswith(f".{ext.lstrip('.')}") and ext else new_base
        plan.append((fname, target))
    return plan

def check_conflicts(directory: str, plan: List[Tuple[str, str]]) -> Tuple[bool, List[str]]:
    targets = {}
    dupes = []
    for _, tgt in plan:
        if tgt in targets:
            dupes.append(tgt)
        targets[tgt] = True
    errors = []
    if dupes:
        errors.append(f"Duplicate targets in plan: {sorted(set(dupes))}")
    existing = set(os.listdir(directory))
    for src, tgt in plan:
        if tgt != src and tgt in existing:
            errors.append(f"Target exists already: {tgt}")
    return (len(errors) == 0), errors

def apply_plan(directory: str, plan: List[Tuple[str, str]]) -> None:
    temp_suffix = ".__renametemp__"
    temps: Dict[str, str] = {}
    plan_map = {src: tgt for src, tgt in plan}
    targets = {tgt for _, tgt in plan}
    for src, tgt in plan:
        if tgt in plan_map and tgt != src:
            src_path = os.path.join(directory, tgt)
            tmp = tgt + temp_suffix
            while os.path.exists(os.path.join(directory, tmp)):
                tmp = tmp + "_x"
            os.replace(src_path, os.path.join(directory, tmp))
            temps[tmp] = tgt
    for src, tgt in plan:
        if src == tgt:
            continue
        src_path = os.path.join(directory, src)
        tgt_path = os.path.join(directory, tgt)
        os.replace(src_path, tgt_path)
    for tmp, final in temps.items():
        tmp_path = os.path.join(directory, tmp)
        final_path = os.path.join(directory, final)
        if os.path.exists(tmp_path):
            os.replace(tmp_path, final_path)
