from __future__ import annotations

import logging
import shutil
import subprocess
import time
from typing import Iterable, Optional

from evdev import ecodes

from .config import ExecutorConfig, NotificationsConfig

logger = logging.getLogger(__name__)


_COMBO_MODIFIERS = {
    "SHIFT": (ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT),
    "CTRL": (ecodes.KEY_LEFTCTRL, ecodes.KEY_RIGHTCTRL),
    "ALT": (ecodes.KEY_LEFTALT, ecodes.KEY_RIGHTALT),
    "META": (ecodes.KEY_LEFTMETA, ecodes.KEY_RIGHTMETA),
    "SUPER": (ecodes.KEY_LEFTMETA, ecodes.KEY_RIGHTMETA),
}


class Executor:
    def __init__(self, executor_cfg: ExecutorConfig, notifications_cfg: NotificationsConfig) -> None:
        self._cfg = executor_cfg
        self._notifications = notifications_cfg

    def send_combo(self, modifiers: Iterable[int], key: int) -> None:
        sequence = []
        for mod in modifiers:
            sequence.append(f"{mod}:1")
        sequence.append(f"{key}:1")
        sequence.append(f"{key}:0")
        for mod in reversed(list(modifiers)):
            sequence.append(f"{mod}:0")
        self._ydotool_key(sequence)
        time.sleep(self._cfg.combo_delay_ms / 1000)

    def send_combo_from_string(self, combo: str) -> None:
        parts = self._split_combos(combo)
        for idx, part in enumerate(parts):
            try:
                modifiers, main_key = self._parse_combo(part)
            except ValueError as exc:
                logger.error("Invalid combo definition '%s': %s", part, exc)
                continue
            self.send_combo(modifiers, main_key)
            if idx < len(parts) - 1:
                time.sleep(self._cfg.combo_delay_ms / 1000)

    def get_clipboard(self) -> Optional[str]:
        if not self._check_binary(self._cfg.wl_paste):
            logger.error("wl-paste not found in PATH")
            return None
        cmd = [self._cfg.wl_paste, "--no-newline"]
        result = self._run(cmd, "wl-paste", capture_output=True)
        if result is None:
            return None
        return result.stdout

    def set_clipboard(self, text: str) -> bool:
        if not self._check_binary(self._cfg.wl_copy):
            logger.error("wl-copy not found in PATH")
            return False
        cmd = [self._cfg.wl_copy]
        result = self._run(cmd, "wl-copy", input_text=text)
        return result is not None

    def notify(self, message: str) -> None:
        if not self._notifications.enable:
            return
        if self._notifications.use_hyprctl and self._check_binary(self._cfg.hyprctl):
            cmd = [self._cfg.hyprctl, "notify", "1", "2000", "0", message]
            if self._run(cmd, "hyprctl notify") is not None:
                return
        if self._notifications.fallback_notify_send and self._check_binary(self._cfg.notify_send):
            cmd = [self._cfg.notify_send, message]
            self._run(cmd, "notify-send")

    def binary_available(self, name: str) -> bool:
        return self._check_binary(name)

    def _ydotool_key(self, sequence: Iterable[str]) -> None:
        if not self._check_binary(self._cfg.ydotool):
            logger.error("ydotool not found in PATH")
            return
        cmd = [self._cfg.ydotool, "key", *sequence]
        self._run(cmd, "ydotool key")

    def _parse_combo(self, raw: str) -> tuple[list[int], int]:
        parts = [part.strip().upper() for part in raw.split("+") if part.strip()]
        modifiers: list[int] = []
        main = None
        for part in parts:
            if part in _COMBO_MODIFIERS:
                modifiers.append(_COMBO_MODIFIERS[part][0])
            else:
                key_name = part if part.startswith("KEY_") else f"KEY_{part}"
                if key_name not in ecodes.ecodes:
                    raise ValueError(f"Unknown combo key: {part}")
                main = ecodes.ecodes[key_name]
        if main is None:
            raise ValueError(f"Invalid combo definition: {raw}")
        return modifiers, main

    @staticmethod
    def _split_combos(raw: str) -> list[str]:
        if "|" not in raw:
            return [raw]
        return [part.strip() for part in raw.split("|") if part.strip()]

    def _check_binary(self, name: str) -> bool:
        return shutil.which(name) is not None

    def _run(
        self,
        cmd: list[str],
        label: str,
        capture_output: bool = False,
        input_text: Optional[str] = None,
    ) -> Optional[subprocess.CompletedProcess[str]]:
        try:
            return subprocess.run(
                cmd,
                input=input_text,
                capture_output=capture_output,
                check=True,
                text=True,
            )
        except FileNotFoundError:
            logger.error("Command not found: %s", cmd[0])
            return None
        except subprocess.CalledProcessError as exc:
            logger.error("%s failed: %s", label, exc)
            return None
