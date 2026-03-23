import json
from importlib import resources
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Hotkeys:
    buffer_mode: str
    selection_mode: str


@dataclass(frozen=True)
class LanguageConfig:
    primary: str
    secondary: str


@dataclass(frozen=True)
class InputConfig:
    device_path: Optional[str]
    device_name: Optional[str]
    grab_device: bool


@dataclass(frozen=True)
class NotificationsConfig:
    enable: bool
    use_hyprctl: bool
    fallback_notify_send: bool


@dataclass(frozen=True)
class ExecutorConfig:
    ydotool: str
    wl_copy: str
    wl_paste: str
    hyprctl: str
    notify_send: str
    type_delay_ms: int
    combo_delay_ms: int
    clipboard_capture_timeout_ms: int
    clipboard_capture_poll_ms: int
    restore_clipboard_after_paste: bool
    clipboard_restore_delay_ms: int
    buffer_select_combo: str
    clipboard_copy_combo: str
    clipboard_paste_combo: str


@dataclass(frozen=True)
class LoggingConfig:
    level: str


@dataclass(frozen=True)
class AppConfig:
    hotkeys: Hotkeys
    language: LanguageConfig
    capture_layout: str
    selection_auto_detect: bool
    buffer_auto_detect: bool
    input: InputConfig
    ignored_apps: List[str]
    terminal_apps: List[str]
    notifications: NotificationsConfig
    executor: ExecutorConfig
    logging: LoggingConfig


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "layout-switcher" / "config.json"
LEGACY_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.json"


def _get(obj: Dict[str, Any], key: str, default: Any) -> Any:
    value = obj.get(key, default)
    return default if value is None else value


def load_config(path: Optional[str]) -> AppConfig:
    cfg_path = Path(path) if path else resolve_default_config_path()
    data = json.loads(cfg_path.read_text(encoding="utf-8"))

    hotkeys = Hotkeys(
        buffer_mode=_get(data.get("hotkeys", {}), "buffer_mode", "F10"),
        selection_mode=_get(data.get("hotkeys", {}), "selection_mode", "SHIFT+F10"),
    )
    language = LanguageConfig(
        primary=_get(data.get("language", {}), "primary", "en"),
        secondary=_get(data.get("language", {}), "secondary", "uk"),
    )
    input_cfg = InputConfig(
        device_path=_get(data.get("input", {}), "device_path", None),
        device_name=_get(data.get("input", {}), "device_name", None),
        grab_device=bool(_get(data.get("input", {}), "grab_device", False)),
    )
    notifications = NotificationsConfig(
        enable=bool(_get(data.get("notifications", {}), "enable", True)),
        use_hyprctl=bool(_get(data.get("notifications", {}), "use_hyprctl", True)),
        fallback_notify_send=bool(_get(data.get("notifications", {}), "fallback_notify_send", True)),
    )
    executor = ExecutorConfig(
        ydotool=_get(data.get("executor", {}), "ydotool", "ydotool"),
        wl_copy=_get(data.get("executor", {}), "wl_copy", "wl-copy"),
        wl_paste=_get(data.get("executor", {}), "wl_paste", "wl-paste"),
        hyprctl=_get(data.get("executor", {}), "hyprctl", "hyprctl"),
        notify_send=_get(data.get("executor", {}), "notify_send", "notify-send"),
        type_delay_ms=int(_get(data.get("executor", {}), "type_delay_ms", 2)),
        combo_delay_ms=int(_get(data.get("executor", {}), "combo_delay_ms", 2)),
        clipboard_capture_timeout_ms=int(
            _get(data.get("executor", {}), "clipboard_capture_timeout_ms", 350)
        ),
        clipboard_capture_poll_ms=int(
            _get(data.get("executor", {}), "clipboard_capture_poll_ms", 25)
        ),
        restore_clipboard_after_paste=bool(
            _get(data.get("executor", {}), "restore_clipboard_after_paste", False)
        ),
        clipboard_restore_delay_ms=int(_get(data.get("executor", {}), "clipboard_restore_delay_ms", 250)),
        buffer_select_combo=_get(data.get("executor", {}), "buffer_select_combo", "CTRL+SHIFT+LEFT"),
        clipboard_copy_combo=_get(data.get("executor", {}), "clipboard_copy_combo", "CTRL+C"),
        clipboard_paste_combo=_get(data.get("executor", {}), "clipboard_paste_combo", "CTRL+V"),
    )
    logging_cfg = LoggingConfig(
        level=_get(data.get("logging", {}), "level", "INFO"),
    )

    return AppConfig(
        hotkeys=hotkeys,
        language=language,
        capture_layout=_get(data, "capture_layout", "uk"),
        selection_auto_detect=bool(_get(data, "selection_auto_detect", True)),
        buffer_auto_detect=bool(_get(data, "buffer_auto_detect", True)),
        input=input_cfg,
        ignored_apps=list(_get(data, "ignored_apps", [])),
        terminal_apps=list(_get(data, "terminal_apps", [])),
        notifications=notifications,
        executor=executor,
        logging=logging_cfg,
    )


def resolve_default_config_path() -> Path:
    if DEFAULT_CONFIG_PATH.exists():
        return DEFAULT_CONFIG_PATH
    if LEGACY_CONFIG_PATH.exists():
        return LEGACY_CONFIG_PATH
    with resources.as_file(resources.files("layout_switcher").joinpath("default_config.json")) as path:
        return path
