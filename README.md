# Layout Switcher Daemon (Manjaro / Hyprland)

Python daemon that fixes text typed in the wrong keyboard layout on Wayland, similar to Punto Switcher.

## Features
- Last-word mode: selects the previous word in the active app, converts it, and replaces it
- Selection mode: converts selected text via clipboard
- English (US) <-> Ukrainian mapping with hardcoded conversion
- Works on Wayland with `ydotool` and `wl-clipboard`
- Hyprland OSD feedback via `hyprctl notify`
- Browser/editor-first behavior: terminal apps are intentionally ignored

## Platform Notes
- Best-supported environment: Manjaro/Arch + Hyprland + Wayland
- Ubuntu is also possible if you use Wayland and have `ydotool`, `wl-clipboard`, and `keyd`
- The current app-ignore detection uses `hyprctl`, so that part is Hyprland-specific
- On Ubuntu without Hyprland, the browser/editor conversion flow can still work, but terminal ignoring may need a different backend later

## Dependencies
System packages (Manjaro/Arch):
- `python`
- `python-evdev`
- `ydotool`
- `wl-clipboard`
- `keyd`
- `hyprland` (for `hyprctl`)

Python packages:
- `evdev`

Install Python deps:
```bash
pip install -r requirements.txt
```

Or install the app into its own user venv:
```bash
python3 -m venv ~/.local/share/layout-switcher/venv
~/.local/share/layout-switcher/venv/bin/python -m pip install .
```

Run a local readiness check:
```bash
layout-switcher doctor
```

Remove the user installation:
```bash
./scripts/uninstall_user.sh
```

Quick bootstrap:
```bash
./scripts/bootstrap.sh
```

Or explicitly:
```bash
./scripts/bootstrap_arch.sh
```

or on Ubuntu:
```bash
./scripts/bootstrap_ubuntu.sh
```

## System Setup
This project expects three system-side pieces to be in place:
- access to `/dev/input` for reading keyboard events
- a running `ydotoold` daemon with a stable user socket
- a `keyd` remap that turns the physical `Menu`/`Compose` key into `F24`

For a short step-by-step setup, see [SETUP.md](/home/tuipik/PROJECTS/layout_switcher/SETUP.md).

Install system packages:
```bash
sudo pacman -S python python-evdev ydotool wl-clipboard keyd
```

Ubuntu note:
- package names and availability differ
- `wl-clipboard` and `python3-evdev` are straightforward
- `ydotool` and `keyd` may require distro-specific packages or manual install depending on Ubuntu release
- this repo includes `bootstrap_ubuntu.sh`, which falls back to `F8` / `Shift+F8` if `keyd` is unavailable

Allow your user to read keyboard events:
```bash
sudo usermod -aG input $USER
```

Load the `uinput` kernel module:
```bash
sudo modprobe uinput
```

Log out and back in after the group change.

If you want `uinput` loaded automatically on boot:
```bash
echo uinput | sudo tee /etc/modules-load.d/uinput.conf
```

## Configuration
Edit `config.json`:
- `hotkeys.buffer_mode` and `hotkeys.selection_mode`
- `language.primary` / `language.secondary`
- `capture_layout`: fallback source layout when auto-detect cannot resolve direction
- `buffer_auto_detect`: auto-detect direction using the current Hyprland keymap
- `ignored_apps`: applications to ignore (Hyprland class)
- `executor.clipboard_copy_combo` / `executor.clipboard_paste_combo`: override copy/paste shortcuts (useful for terminals)
- `terminal_apps`: terminal classes to ignore entirely in browser-first mode; entries are matched by substring
- `executor.buffer_select_combo`: key combo used to select the previous word before replacement
- `executor.clipboard_capture_timeout_ms` / `executor.clipboard_capture_poll_ms`: how long to wait for `copy` to update the clipboard
- `executor.restore_clipboard_after_paste`: restore previous clipboard after paste; disabled by default because Wayland paste is often asynchronous
- `executor.clipboard_restore_delay_ms`: restore delay when clipboard restoration is enabled

Browsers and editors use one selection-first path: select text, copy it, translate it, then replace it via clipboard paste. Terminal apps are intentionally ignored because terminal copy/paste semantics were causing repeated regressions.

## keyd F24 hotkeys
The default config now expects `F24` and `Shift+F24` as internal hotkeys. A sample `keyd` remap is included at `keyd/layout-switcher.conf`:

```ini
[ids]
*

[main]
compose = f24
shift+compose = S-f24
```

This keeps the physical trigger on the physical `Menu`/`Compose` key, but applications only see `F24`, which avoids many browser and terminal conflicts and sidesteps Plasma bindings that can react to `F13`.

Suggested setup on Manjaro:
```bash
sudo cp keyd/layout-switcher.conf /etc/keyd/default.conf
sudo systemctl enable --now keyd
sudo keyd reload
```

Verify the remap:
```bash
sudo keyd monitor
```

Press the physical `Menu`/`Compose` key. You should see `f24 down` / `f24 up`.

Then restart the app:
```bash
python main.py --config config.json
```

## ydotoold user service
To keep the `ydotool` socket stable across sessions, a user service is included at `systemd/ydotoold.service`.

Install and start it:
```bash
mkdir -p ~/.config/systemd/user
cp systemd/ydotoold.service ~/.config/systemd/user/ydotoold.service
systemctl --user daemon-reload
systemctl --user enable --now ydotoold.service
```

Check that the daemon is up:
```bash
systemctl --user status ydotoold.service
ls -l /run/user/$(id -u)/.ydotool_socket
```

Run the app in the same user session with:
```bash
export YDTOOL_SOCKET=/run/user/$(id -u)/.ydotool_socket
python main.py --config config.json
```

## App user service
A user service for the app itself is included at `systemd/layout-switcher.service`.

Install it:
```bash
mkdir -p ~/.config/systemd/user
cp systemd/layout-switcher.service ~/.config/systemd/user/layout-switcher.service
systemctl --user daemon-reload
systemctl --user enable --now layout-switcher.service
```

It expects the installed CLI entry point at:
```text
~/.local/bin/layout-switcher
```

and the user config at:
```text
~/.config/layout-switcher/config.json
```

## Run
Recommended launch sequence:
```bash
export YDTOOL_SOCKET=/run/user/$(id -u)/.ydotool_socket
python main.py --config config.json
```

Or, after installing into the app venv:
```bash
export YDTOOL_SOCKET=/run/user/$(id -u)/.ydotool_socket
layout-switcher
```

Diagnostic mode:
```bash
layout-switcher doctor
```

Expected startup log:
```text
Listening on input device: ... (keyd virtual keyboard)
Listening on input device: ... (your physical keyboard)
```

## Quick Check
After setup:
1. Put focus in a browser or editor text field.
2. Type a word in the wrong layout.
3. Press `Menu`/`Compose` for last-word conversion.
4. Select text and press `Shift+Menu`/`Shift+Compose` for selection conversion.

## Notes
- The daemon uses raw evdev events and does not depend on the current system keyboard layout.
- If `ydotool` or `wl-clipboard` is missing, conversion actions will log errors and skip.
- If terminal apps are not being ignored, set `executor.hyprctl` to the full path of `hyprctl` in `config.json` so active-window detection works reliably in your session.

## Troubleshooting
- `ydotool failed to connect socket`: make sure `YDTOOL_SOCKET` points to `/run/user/$(id -u)/.ydotool_socket` and `ydotoold.service` is running.
- `Listening on input device` shows only the physical keyboard: make sure `keyd` is running; the app should also see `keyd virtual keyboard`.
- `Menu`/`Compose` still opens a menu instead of converting text: run `sudo keyd monitor` and confirm the key is emitted as `f24`.
- Browser/editor hotkeys do nothing: verify `wl-copy`, `wl-paste`, and `ydotool` are installed and available in `PATH`.
- App detection does not ignore terminals: set the full path to `hyprctl` in `config.json`, for example `"/usr/bin/hyprctl"` if that is where it is installed on your system.
- For a one-command bootstrap of the user-side pieces, run `./scripts/install_user.sh`.
- For automatic distro detection, run `./scripts/bootstrap.sh`.
- For distro-specific bootstrap, run `./scripts/bootstrap_arch.sh` or `./scripts/bootstrap_ubuntu.sh`.
- To remove the user installation, run `./scripts/uninstall_user.sh`.
- The install scripts also create `~/.local/bin/layout-switcher` as a convenience wrapper.
- If `layout-switcher` is not found in `zsh`, run `source ~/.zprofile` or log in again so `~/.local/bin` is picked up.
- To check the current machine state, run `layout-switcher doctor`.
