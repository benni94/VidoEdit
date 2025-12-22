"""Translation module for H266VideoConverter"""

TRANSLATIONS = {
    "en": {
        # Main window
        "app_title": "VidoEdit",
        
        # Tabs
        "tab_convert": "Convert",
        "tab_compress": "Compress",
        "merge_videos": "Merge Videos",
        "renamer": "Renamer",
        # Common / generic
        "directory": "Directory",
        "choose_folder": "Choose folder",
        "identifier_regex": "Identifier regex",
        "pattern": "Pattern",
        "pattern_sxe": "SxxEyy (e.g., S01E02A)",
        "pattern_sxe_sep": "SxxEyy with separator (e.g., S01-E02)",
        "pattern_numxnum": "1x02 (e.g., 1x02A)",
        "output_id_sample": "Output ID sample",
        "mode": "Mode",
        "batch_all_episodes": "Batch (all episodes)",
        "single_identifier": "Single identifier",
        "identifier_placeholder": "Identifier (e.g., S01E01A)",
        "overwrite_all_outputs": "Overwrite all existing outputs",
        "preview": "Preview",
        "merge": "Merge",
        "rename": "Rename",
        "new_name_template": "New name template",
        "numbering_mode": "Numbering mode",
        "use_parsed_numbers": "Use parsed numbers from filenames",
        "manual_start_numbers": "Start from season/episode below",
        "start_season": "Start season",
        "start_episode": "Start episode",
        # Status / messages
        "idle_status": "Idle",
        "starting_status": "Starting...",
        "dir_not_exist": "Directory does not exist",
        "invalid_regex": "Invalid regex",
        "identifier_missing_groups_default_used": "Identifier missing groups; using default pattern.",
        "invalid_identifier": "Could not parse identifier",
        "no_parts_found": "No matching part files found",
        "no_episode_parts": "No episode parts found.",
        "total_episodes": "Total episodes: {episodes}, total parts: {parts}",
        "merging_file": "Merging {name}...",
        "ffmpeg_failed": "ffmpeg failed",
        "done_status": "Done",
        "conflicts_detected": "Conflicts detected:",
        "nothing_to_rename": "Nothing to rename",
        
        # Common buttons
        "add_files": "Add Files",
        "add_folder": "Add Folder",
        "clear_queue": "Clear Queue",
        "start": "START",
        "cancel": "CANCEL",
        
        # Convert Tab
        "target_codec": "Target Codec:",
        "replace_original": "Replace original files",
        "start_conversion": "Start Conversion",
        "ready": "Ready",
        "log": "Log:",
        "conversion_started": "=== Conversion started ===",
        "starting": "Starting...",
        "queue_empty": "✗ Queue is empty. Add files first.",
        "no_video_files": "No video files found.",
        "no_files_found": "No files found",
        "conversion_cancelled": "Conversion cancelled.",
        "done": "✓ Done! {count} files converted",
        "conversion_complete": "\n=== Conversion complete! ({count} files) ===",
        
        # Compress Tab
        "encoder": "Encoder:",
        "mode": "Mode",
        "target_size": "Target Size (GB)",
        "presets": "Presets:",
        "idle": "Idle",
        "compressing": "Compressing... ({percent}%)",
        
        # Presets
        "preset_film": "Film - Balances encoding quality with file size, suited for most films.",
        "preset_anime": "Anime - Optimized for animation, preserving fine lines and details at a higher quality.",
        "preset_4k": "4K - Tailored for 4K videos, allows for a slight reduction in quality to reduce file size.",
        "preset_plex": "Plex - Designed for streaming platforms like Plex, balancing quality with a faster encoding speed.",
        
        # Settings
        "settings": "Settings",
        "language": "Language",
        "select_language": "Select Language:",
        "close": "Close",
        "theme_light": "Light Mode",
        "theme_dark": "Dark Mode",
    },
    "de": {
        # Main window
        "app_title": "VidoEdit",
        
        # Tabs
        "tab_convert": "Konvertieren",
        "tab_compress": "Komprimieren",
        "merge_videos": "Videos zusammenführen",
        "renamer": "Umbenennen",
        # Common / generic
        "directory": "Ordner",
        "choose_folder": "Ordner auswählen",
        "identifier_regex": "Bezeichner-RegEx",
        "pattern": "Muster",
        "pattern_sxe": "SxxEyy (z. B. S01E02A)",
        "pattern_sxe_sep": "SxxEyy mit Trennzeichen (z. B. S01-E02)",
        "pattern_numxnum": "1x02 (z. B. 1x02A)",
        "output_id_sample": "Ausgabe-ID-Beispiel",
        "mode": "Modus",
        "batch_all_episodes": "Stapel (alle Episoden)",
        "single_identifier": "Einzelner Bezeichner",
        "identifier_placeholder": "Bezeichner (z. B. S01E01A)",
        "overwrite_all_outputs": "Alle vorhandenen Ausgaben überschreiben",
        "preview": "Vorschau",
        "merge": "Zusammenführen",
        "rename": "Umbenennen",
        "new_name_template": "Neuer Namens-Template",
        "numbering_mode": "Nummerierungsmodus",
        "use_parsed_numbers": "Aus Dateinamen ausgelesene Nummern verwenden",
        "manual_start_numbers": "Ab Staffel/Episode unten starten",
        "start_season": "Start-Staffel",
        "start_episode": "Start-Episode",
        # Status / messages
        "idle_status": "Bereit",
        "starting_status": "Starte...",
        "dir_not_exist": "Ordner existiert nicht",
        "invalid_regex": "Ungültige RegEx",
        "identifier_missing_groups_default_used": "Bezeichner ohne erforderliche Gruppen; Standardmuster wird verwendet.",
        "invalid_identifier": "Bezeichner konnte nicht erkannt werden",
        "no_parts_found": "Keine passenden Teil-Dateien gefunden",
        "no_episode_parts": "Keine Episoden-Teile gefunden.",
        "total_episodes": "Gesamte Episoden: {episodes}, Teile insgesamt: {parts}",
        "merging_file": "Führe {name} zusammen...",
        "ffmpeg_failed": "ffmpeg fehlgeschlagen",
        "done_status": "Fertig",
        "conflicts_detected": "Konflikte erkannt:",
        "nothing_to_rename": "Nichts zum Umbenennen",
        
        # Common buttons
        "add_files": "Dateien hinzufügen",
        "add_folder": "Ordner hinzufügen",
        "clear_queue": "Warteschlange leeren",
        "start": "START",
        "cancel": "ABBRECHEN",
        
        # Convert Tab
        "target_codec": "Zielcodec:",
        "replace_original": "Originaldateien ersetzen",
        "start_conversion": "Konvertierung starten",
        "ready": "Bereit",
        "log": "Protokoll:",
        "conversion_started": "=== Konvertierung gestartet ===",
        "starting": "Starte...",
        "queue_empty": "✗ Warteschlange ist leer. Fügen Sie zuerst Dateien hinzu.",
        "no_video_files": "Keine Video-Dateien gefunden.",
        "no_files_found": "Keine Dateien gefunden",
        "conversion_cancelled": "Konvertierung abgebrochen.",
        "done": "✓ Fertig! {count} Dateien konvertiert",
        "conversion_complete": "\n=== Konvertierung abgeschlossen! ({count} Dateien) ===",
        
        # Compress Tab
        "encoder": "Encoder:",
        "mode": "Modus",
        "target_size": "Zielgröße (GB)",
        "presets": "Voreinstellungen:",
        "idle": "Bereit",
        "compressing": "Komprimiere... ({percent}%)",
        
        # Presets
        "preset_film": "Film - Ausgewogene Kodierungsqualität mit Dateigröße, geeignet für die meisten Filme.",
        "preset_anime": "Anime - Optimiert für Animationen, bewahrt feine Linien und Details in höherer Qualität.",
        "preset_4k": "4K - Zugeschnitten auf 4K-Videos, ermöglicht eine leichte Qualitätsreduzierung zur Verkleinerung der Dateigröße.",
        "preset_plex": "Plex - Entwickelt für Streaming-Plattformen wie Plex, ausgewogene Qualität mit schnellerer Kodierungsgeschwindigkeit.",
        
        # Settings
        "settings": "Einstellungen",
        "language": "Sprache",
        "select_language": "Sprache auswählen:",
        "close": "Schließen",
        "theme_light": "Heller Modus",
        "theme_dark": "Dunkler Modus",
    }
}
