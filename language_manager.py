"""Language Manager for H266VideoConverter"""
import locale
import json
from pathlib import Path
from typing import Callable, Optional
from translations import TRANSLATIONS


class LanguageManager:
    """Manages application language and translations"""
    
    CONFIG_FILE = Path.home() / ".h266videoconverter" / "config.json"
    
    def __init__(self):
        self._current_language = self._load_language()
        self._callbacks = []
    
    def _detect_system_language(self) -> str:
        """Detect system language, fallback to English"""
        try:
            system_lang = locale.getdefaultlocale()[0]
            if system_lang:
                lang_code = system_lang.split('_')[0].lower()
                if lang_code in TRANSLATIONS:
                    return lang_code
        except Exception:
            pass
        return "en"
    
    def _load_language(self) -> str:
        """Load language from config file or detect system language"""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    lang = config.get('language')
                    if lang in TRANSLATIONS:
                        return lang
            except Exception:
                pass
        return self._detect_system_language()
    
    def _save_language(self, language: str):
        """Save language to config file"""
        try:
            self.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            config = {'language': language}
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except Exception:
            pass
    
    def get_current_language(self) -> str:
        """Get current language code"""
        return self._current_language
    
    def set_language(self, language: str):
        """Set current language and notify callbacks"""
        if language in TRANSLATIONS:
            self._current_language = language
            self._save_language(language)
            self._notify_callbacks()
    
    def get_text(self, key: str, **kwargs) -> str:
        """Get translated text for key"""
        text = TRANSLATIONS.get(self._current_language, {}).get(key, key)
        if kwargs:
            text = text.format(**kwargs)
        return text
    
    def register_callback(self, callback: Callable):
        """Register callback to be called when language changes"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable):
        """Unregister callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self):
        """Notify all registered callbacks of language change"""
        for callback in self._callbacks:
            try:
                callback()
            except Exception:
                pass
    
    def get_available_languages(self) -> dict:
        """Get available languages"""
        return {
            "en": "English",
            "de": "Deutsch"
        }
