from __future__ import annotations

import logging
import select
import threading
from typing import Callable, List, Optional

from evdev import InputDevice, categorize, ecodes
from evdev.util import list_devices

from .config import InputConfig

logger = logging.getLogger(__name__)


class InputListener(threading.Thread):
    def __init__(self, input_cfg: InputConfig, callback: Callable[[object], None]) -> None:
        super().__init__(daemon=True)
        self._input_cfg = input_cfg
        self._callback = callback
        self._stop_event = threading.Event()
        self._devices: List[InputDevice] = []

    def stop(self) -> None:
        self._stop_event.set()
        for device in self._devices:
            try:
                device.ungrab()
            except OSError:
                pass
            try:
                device.close()
            except OSError:
                pass

    def run(self) -> None:
        try:
            self._devices = self._open_devices()
        except Exception as exc:
            logger.error("Input listener failed to start: %s", exc)
            return

        if self._input_cfg.grab_device:
            for device in self._devices:
                try:
                    device.grab()
                    logger.info("Input device grabbed for exclusive access: %s (%s)", device.path, device.name)
                except OSError as exc:
                    logger.warning("Failed to grab device %s: %s", device.path, exc)

        for device in self._devices:
            logger.info("Listening on input device: %s (%s)", device.path, device.name)

        while not self._stop_event.is_set():
            try:
                ready, _, _ = select.select([device.fd for device in self._devices], [], [], 0.5)
                if not ready:
                    continue
                ready_fds = set(ready)
                for device in self._devices:
                    if device.fd not in ready_fds:
                        continue
                    for event in device.read():
                        if event.type != ecodes.EV_KEY:
                            continue
                        key_event = categorize(event)
                        self._callback(key_event)
            except OSError as exc:
                logger.error("Input device read error: %s", exc)
                break

    def _open_devices(self) -> List[InputDevice]:
        if self._input_cfg.device_path:
            return [InputDevice(self._input_cfg.device_path)]

        devices = [InputDevice(path) for path in list_devices()]
        if not devices:
            raise RuntimeError("No input devices found")

        keyboards = [dev for dev in devices if self._is_keyboard_device(dev)]
        if not keyboards:
            keyboards = devices

        filtered = [dev for dev in keyboards if not self._is_ignored_device(dev)]
        if not filtered:
            filtered = keyboards

        preferred = self._input_cfg.device_name
        if preferred:
            preferred_devices = [
                dev for dev in filtered if preferred.lower() in (dev.name or "").lower()
            ]
            if preferred_devices:
                return preferred_devices

        return filtered

    @staticmethod
    def _is_ignored_device(device: InputDevice) -> bool:
        name = (device.name or "").lower()
        if "ydotoold" in name:
            return True
        return False

    @staticmethod
    def _is_keyboard_device(device: InputDevice) -> bool:
        caps = device.capabilities().get(ecodes.EV_KEY, [])
        return ecodes.KEY_A in caps and ecodes.KEY_Z in caps
