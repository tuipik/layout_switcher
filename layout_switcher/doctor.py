from __future__ import annotations

import grp
import os
import pwd
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
from pathlib import Path

from evdev import InputDevice
from evdev.util import list_devices

from .config import DEFAULT_CONFIG_PATH, resolve_default_config_path


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str
    required: bool = True


def run_doctor() -> int:
    print("layout-switcher doctor")
    print()
    checks = [
        ("config", _check_config),
        ("ydotool", lambda: _check_binary("ydotool", required=True)),
        ("wl-copy", lambda: _check_binary("wl-copy", required=True)),
        ("wl-paste", lambda: _check_binary("wl-paste", required=True)),
        ("keyd", lambda: _check_binary("keyd", required=False)),
        ("hyprctl", lambda: _check_binary("hyprctl", required=False)),
        ("input group", _check_input_group),
        ("uinput", _check_uinput),
        ("ydotool socket", _check_ydotool_socket),
        ("keyd virtual keyboard", _check_keyd_virtual_keyboard),
        ("ydotoold.service", lambda: _check_user_service("ydotoold.service", required=False)),
        ("layout-switcher.service", lambda: _check_user_service("layout-switcher.service", required=False)),
    ]

    results: list[CheckResult] = []
    for name, check in checks:
        print(f"Checking {name}...", flush=True)
        result = check()
        results.append(result)
        status = "OK" if result.ok else ("WARN" if not result.required else "FAIL")
        print(f"[{status}] {result.name}: {result.detail}", flush=True)

    failures = [item for item in results if item.required and not item.ok]
    return 1 if failures else 0


def _check_config() -> CheckResult:
    path = resolve_default_config_path()
    source = "user config" if path == DEFAULT_CONFIG_PATH else "project/default config"
    return CheckResult("config", path.exists(), f"{path} ({source})")


def _check_binary(name: str, required: bool) -> CheckResult:
    path = shutil.which(name)
    return CheckResult(name, path is not None, path or "not found in PATH", required=required)


def _check_input_group() -> CheckResult:
    try:
        input_group = grp.getgrnam("input")
    except KeyError:
        return CheckResult("input group", False, "group 'input' does not exist")

    username = _current_username()
    in_primary = os.getgid() == input_group.gr_gid
    in_supplementary = input_group.gr_gid in os.getgroups()
    listed = username in input_group.gr_mem if username else False
    ok = in_primary or in_supplementary or listed
    detail = "current user is in 'input'" if ok else "current user is not in 'input'"
    return CheckResult("input group", ok, detail)


def _check_uinput() -> CheckResult:
    device = Path("/dev/uinput")
    if device.exists():
        return CheckResult("uinput", True, "/dev/uinput is present")
    return CheckResult("uinput", False, "/dev/uinput is missing; run 'sudo modprobe uinput'")


def _check_ydotool_socket() -> CheckResult:
    configured = Path(os.environ.get("YDTOOL_SOCKET", f"/run/user/{os.getuid()}/.ydotool_socket"))
    candidates = [configured]
    tmp_socket = Path("/tmp/.ydotool_socket")
    if tmp_socket not in candidates:
        candidates.append(tmp_socket)

    for socket_path in candidates:
        if socket_path.exists():
            detail = str(socket_path)
            if socket_path != configured:
                detail += f" (fallback; YDTOOL_SOCKET is {configured})"
            return CheckResult("ydotool socket", True, detail)
    return CheckResult("ydotool socket", False, f"{configured} missing")


def _check_keyd_virtual_keyboard() -> CheckResult:
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_list_input_device_names)
            names = future.result(timeout=3)
    except FutureTimeout:
        return CheckResult("keyd virtual keyboard", False, "timed out while enumerating input devices", required=False)
    except OSError as exc:
        return CheckResult("keyd virtual keyboard", False, f"failed to enumerate input devices: {exc}", required=False)
    ok = any("keyd virtual keyboard" in name.lower() for name in names)
    detail = "device found" if ok else "device not found"
    return CheckResult("keyd virtual keyboard", ok, detail, required=False)


def _check_user_service(name: str, required: bool) -> CheckResult:
    systemctl = shutil.which("systemctl")
    if systemctl is None:
        return CheckResult(name, False, "systemctl not found", required=required)
    try:
        result = subprocess.run(
            [systemctl, "--user", "is-active", name],
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
    except OSError as exc:
        return CheckResult(name, False, f"failed to query service: {exc}", required=required)
    except subprocess.TimeoutExpired:
        return CheckResult(name, False, "timed out while querying service", required=required)
    state = (result.stdout or result.stderr).strip() or "unknown"
    return CheckResult(name, result.returncode == 0 and state == "active", state, required=required)


def _current_username() -> str | None:
    try:
        return pwd.getpwuid(os.getuid()).pw_name
    except KeyError:
        return None


def _list_input_device_names() -> list[str]:
    return [(InputDevice(path).name or "") for path in list_devices()]
