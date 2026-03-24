from __future__ import annotations

import json
import logging
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Set

from evdev import ecodes

from .config import AppConfig
from .executor import Executor
from .translator import Translator

logger = logging.getLogger(__name__)


_MODIFIERS: Dict[str, Iterable[int]] = {
    "SHIFT": (ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT),
    "CTRL": (ecodes.KEY_LEFTCTRL, ecodes.KEY_RIGHTCTRL),
    "ALT": (ecodes.KEY_LEFTALT, ecodes.KEY_RIGHTALT),
    "META": (ecodes.KEY_LEFTMETA, ecodes.KEY_RIGHTMETA),
    "SUPER": (ecodes.KEY_LEFTMETA, ecodes.KEY_RIGHTMETA),
}


@dataclass(frozen=True)
class Hotkey:
    main_key: int
    modifiers: Set[str]

    @classmethod
    def parse(cls, raw: str) -> "Hotkey":
        parts = [part.strip().upper() for part in raw.split("+") if part.strip()]
        modifiers = {part for part in parts if part in _MODIFIERS}
        main = next((part for part in parts if part not in _MODIFIERS), "")
        if not main:
            raise ValueError(f"Invalid hotkey definition: {raw}")
        if not main.startswith("KEY_"):
            main = f"KEY_{main}"
        if main not in ecodes.ecodes:
            raise ValueError(f"Unknown hotkey key: {main}")
        return cls(main_key=ecodes.ecodes[main], modifiers=modifiers)

    def match(self, keycode: int, pressed_keys: Set[int]) -> bool:
        if keycode != self.main_key:
            return False
        for mod in self.modifiers:
            if not any(code in pressed_keys for code in _MODIFIERS[mod]):
                return False
        return True


class Processor:
    def __init__(self, config: AppConfig, translator: Translator, executor: Executor) -> None:
        self._config = config
        self._translator = translator
        self._executor = executor
        self._lock = threading.Lock()
        self._clipboard_restore_lock = threading.Lock()
        self._clipboard_restore_generation = 0
        self._pressed_keys: Set[int] = set()
        self._suppress_until = 0.0
        self._last_app_check = 0.0
        self._cached_app: Optional[str] = None
        self._ignored_apps = {
            app.lower() for app in [*config.ignored_apps, *config.terminal_apps]
        }

        self._buffer_hotkey = Hotkey.parse(config.hotkeys.buffer_mode)
        self._selection_hotkey = Hotkey.parse(config.hotkeys.selection_mode)

    def handle_key_event(self, key_event: object) -> None:
        now = time.monotonic()
        if now < self._suppress_until:
            return

        keycode = getattr(key_event, "scancode", None)
        keystate = getattr(key_event, "keystate", None)
        if keycode is None or keystate is None:
            return

        with self._lock:
            if keystate == key_event.key_down:
                self._pressed_keys.add(keycode)
                return

            if keystate != key_event.key_up:
                return

            if self._selection_hotkey.match(keycode, self._pressed_keys):
                self._pressed_keys.discard(keycode)
                self._handle_selection_mode()
                return

            if self._buffer_hotkey.match(keycode, self._pressed_keys):
                self._pressed_keys.discard(keycode)
                self._handle_last_word_mode()
                return

            self._pressed_keys.discard(keycode)

    def _handle_last_word_mode(self) -> None:
        if self._is_ignored_app():
            logger.debug("Ignoring last-word hotkey in ignored app")
            return
        logger.debug("Selecting previous word via %s", self._config.executor.buffer_select_combo)
        self._executor.send_combo_from_string(self._config.executor.buffer_select_combo)
        time.sleep(0.05)
        self._translate_selected_text("last word")

    def _handle_selection_mode(self) -> None:
        if self._is_ignored_app():
            logger.debug("Ignoring selection hotkey in ignored app")
            return
        self._translate_selected_text("selection")

    def _translate_selected_text(self, label: str) -> bool:
        original_clipboard = self._executor.get_clipboard()
        capture = self._capture_selected_text(label)
        selected_text = capture[0] if capture else None
        if not selected_text:
            if original_clipboard is not None and self._config.executor.restore_clipboard_after_paste:
                self._executor.set_clipboard(original_clipboard)
            return False
        paste_combo = capture[1]

        fallback_source = self._resolve_source_layout()
        if self._config.selection_auto_detect:
            direction = self._translator.detect_direction(selected_text, fallback_source=fallback_source)
            source = direction.source
            target = direction.target
        else:
            source = fallback_source
            target = (
                self._config.language.secondary
                if source == self._config.language.primary
                else self._config.language.primary
            )

        try:
            converted = self._translator.translate(selected_text, source=source, target=target)
        except ValueError as exc:
            logger.error("Translation error: %s", exc)
            return False

        if converted == selected_text:
            logger.debug("Selected %s remains unchanged after translation", label)
            if original_clipboard is not None and self._config.executor.restore_clipboard_after_paste:
                self._executor.set_clipboard(original_clipboard)
            return False

        logger.debug("%s convert: '%s' -> '%s' (%s -> %s)", label.title(), selected_text, converted, source, target)
        if not self._executor.set_clipboard(converted):
            logger.error("Clipboard write failed; cannot paste translated %s", label)
            if original_clipboard is not None and self._config.executor.restore_clipboard_after_paste:
                self._executor.set_clipboard(original_clipboard)
            return False

        self._suppress_until = time.monotonic() + 0.3
        self._executor.send_combo_from_string(paste_combo)
        if original_clipboard is not None and self._config.executor.restore_clipboard_after_paste:
            self._schedule_clipboard_restore(original_clipboard)
        self._executor.notify(f"Converted {label} ({source} -> {target})")
        return True

    def _capture_selected_text(self, label: str) -> Optional[tuple[str, str]]:
        copy_combo = self._config.executor.clipboard_copy_combo
        paste_combo = self._config.executor.clipboard_paste_combo
        previous_primary = self._executor.get_primary_selection()
        sentinel = f"__layout_switcher_copy_probe__:{uuid.uuid4()}__"
        if not self._executor.set_clipboard(sentinel):
            logger.error("Clipboard write failed; cannot prepare %s capture", label)
            return None
        logger.debug("%s copy via %s", label.title(), copy_combo)
        self._executor.send_combo_from_string(copy_combo)
        timeout_ms = max(self._config.executor.clipboard_capture_timeout_ms, 0)
        poll_ms = max(self._config.executor.clipboard_capture_poll_ms, 1)
        deadline = time.monotonic() + (timeout_ms / 1000)
        while time.monotonic() <= deadline:
            selected_text = self._executor.get_clipboard()
            if selected_text and selected_text != sentinel:
                return selected_text, paste_combo
            primary_selection = self._executor.get_primary_selection()
            if (
                primary_selection
                and primary_selection != previous_primary
                and primary_selection != sentinel
            ):
                logger.debug("Using primary selection update for %s", label)
                return primary_selection, paste_combo
            time.sleep(poll_ms / 1000)
        primary_selection = self._executor.get_primary_selection()
        if primary_selection:
            logger.debug("Using primary selection fallback for %s", label)
            return primary_selection, paste_combo
        logger.debug("No %s text captured from clipboard via %s", label, copy_combo)
        return None

    def _is_ignored_app(self) -> bool:
        if not self._ignored_apps:
            return False
        active = self._get_active_app_class()
        return self._matches_app((active or "").lower(), self._ignored_apps)

    def _get_active_app_class(self) -> Optional[str]:
        now = time.monotonic()
        if self._cached_app is not None and now - self._last_app_check < 0.5:
            return self._cached_app
        if not self._executor.binary_available(self._config.executor.hyprctl):
            return self._cached_app
        try:
            result = subprocess.run(
                [self._config.executor.hyprctl, "activewindow", "-j"],
                capture_output=True,
                check=True,
                text=True,
            )
            payload = json.loads(result.stdout)
            if isinstance(payload, dict):
                active = payload.get("class") or payload.get("initialClass")
                if active:
                    self._cached_app = active
                    self._last_app_check = now
                return active or self._cached_app
        except (subprocess.SubprocessError, json.JSONDecodeError) as exc:
            logger.debug("Failed to read active window: %s", exc)
        return self._cached_app

    def _resolve_source_layout(self) -> str:
        if self._config.buffer_auto_detect:
            detected = self._get_active_layout()
            if detected:
                return detected
        return self._config.capture_layout

    def _get_active_layout(self) -> Optional[str]:
        if not self._executor.binary_available(self._config.executor.hyprctl):
            return None
        try:
            result = subprocess.run(
                [self._config.executor.hyprctl, "devices", "-j"],
                capture_output=True,
                check=True,
                text=True,
            )
            payload = json.loads(result.stdout)
            keyboards = payload.get("keyboards", []) if isinstance(payload, dict) else []
            for keyboard in keyboards:
                keymap = (keyboard.get("active_keymap") or keyboard.get("activeKeymap") or "").lower()
                if "ukrain" in keymap or "ua" in keymap:
                    return "uk"
                if "english" in keymap or "us" in keymap or "en" in keymap:
                    return "en"
        except (subprocess.SubprocessError, json.JSONDecodeError) as exc:
            logger.debug("Failed to read active layout: %s", exc)
        return None

    def _schedule_clipboard_restore(self, text: str) -> None:
        delay_ms = max(self._config.executor.clipboard_restore_delay_ms, 0)
        with self._clipboard_restore_lock:
            self._clipboard_restore_generation += 1
            generation = self._clipboard_restore_generation

        def restore() -> None:
            if delay_ms > 0:
                time.sleep(delay_ms / 1000)
            with self._clipboard_restore_lock:
                if generation != self._clipboard_restore_generation:
                    logger.debug("Skipping stale clipboard restore")
                    return
            if not self._executor.set_clipboard(text):
                logger.debug("Clipboard restore failed")

        threading.Thread(target=restore, daemon=True).start()

    @staticmethod
    def _matches_app(active: str, patterns: Set[str]) -> bool:
        if not active:
            return False
        for pattern in patterns:
            if pattern and pattern in active:
                return True
        return False
