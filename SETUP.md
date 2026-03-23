# Setup Guide

This is the shortest path from a clean Manjaro/Hyprland system to a working `layout_switcher`.

Ubuntu note:
- the same overall flow applies on Ubuntu Wayland
- package names differ
- the current terminal-ignore detection is Hyprland-specific because it uses `hyprctl`
- browser/editor conversion can still work on Ubuntu, but Hyprland-specific behavior will not
- if `keyd` is unavailable, use `./scripts/bootstrap_ubuntu.sh`, which switches to `F8` / `Shift+F8`

## 1. Install packages
```bash
sudo pacman -S python python-evdev ydotool wl-clipboard keyd
```

## 2. Allow keyboard access
Add your user to the `input` group:
```bash
sudo usermod -aG input $USER
```

Load `uinput` now:
```bash
sudo modprobe uinput
```

Optional: load `uinput` automatically on boot:
```bash
echo uinput | sudo tee /etc/modules-load.d/uinput.conf
```

Log out and back in after the group change.

## 3. Install Python dependencies
From the project directory:
```bash
pip install -r requirements.txt
```

Optional: install the app into its own user venv:
```bash
python3 -m venv ~/.local/share/layout-switcher/venv
~/.local/share/layout-switcher/venv/bin/python -m pip install .
```

## 4. Install the keyd remap
This project uses the physical `Menu`/`Compose` key as the trigger.
`keyd` remaps it to internal hotkeys:
- `Compose` -> `F24`
- `Shift+Compose` -> `Shift+F24`

Install the remap:
```bash
sudo cp keyd/layout-switcher.conf /etc/keyd/default.conf
sudo systemctl enable --now keyd
sudo keyd reload
```

Verify it:
```bash
sudo keyd monitor
```

Press the physical `Menu`/`Compose` key. You should see:
```text
f24 down
f24 up
```

## 5. Install the ydotoold user service
Copy the included service:
```bash
mkdir -p ~/.config/systemd/user
cp systemd/ydotoold.service ~/.config/systemd/user/ydotoold.service
systemctl --user daemon-reload
systemctl --user enable --now ydotoold.service
```

Check that it started:
```bash
systemctl --user status ydotoold.service
ls -l /run/user/$(id -u)/.ydotool_socket
```

The socket should exist at:
```text
/run/user/<your-uid>/.ydotool_socket
```

## 6. Check config
Default hotkeys in `config.json`:
```json
"hotkeys": {
  "buffer_mode": "F24",
  "selection_mode": "SHIFT+F24"
}
```

This means:
- `Menu`/`Compose` triggers last-word conversion
- `Shift+Menu`/`Shift+Compose` triggers selection conversion

Terminal apps are intentionally ignored in the current browser-first version.

## 7. Run the app
Export the ydotool socket in the same session:
```bash
export YDTOOL_SOCKET=/run/user/$(id -u)/.ydotool_socket
python main.py --config config.json
```

If you installed the app into its user venv, you can also run:
```bash
layout-switcher doctor
layout-switcher
```

If `zsh` does not see the command yet:
```bash
source ~/.zprofile
```

Expected startup log:
```text
Listening on input device: ... (keyd virtual keyboard)
Listening on input device: ... (your physical keyboard)
```

## 8. Quick test
1. Focus a browser or text editor input field.
2. Type a word in the wrong layout.
3. Press `Menu`/`Compose`.
4. Select text and press `Shift+Menu`/`Shift+Compose`.

Before testing, you can run:
```bash
layout-switcher doctor
```

## Optional bootstrap
There is also a helper script that installs the Python package, copies the default user config, and installs the user services:
```bash
./scripts/install_user.sh
```

For a distro-specific automated setup:
```bash
./scripts/bootstrap.sh
./scripts/bootstrap_arch.sh
./scripts/bootstrap_ubuntu.sh
```

To remove the user-side installation later:
```bash
./scripts/uninstall_user.sh
```

## Troubleshooting
### `ydotool` socket errors
If you see socket connection errors:
```bash
export YDTOOL_SOCKET=/run/user/$(id -u)/.ydotool_socket
systemctl --user restart ydotoold.service
```

### `Menu` still opens a menu
Check `keyd`:
```bash
sudo keyd monitor
```

If you do not see `f24`, the remap is not active.

### The app does not see the key
Startup logs should show both:
- `keyd virtual keyboard`
- your physical keyboard

If `keyd virtual keyboard` is missing, make sure `keyd` is running:
```bash
sudo systemctl status keyd
```

### Terminals are still affected
The current project version is browser-first. If terminals are not ignored, set the full path to `hyprctl` in `config.json`, for example:
```json
"hyprctl": "/usr/bin/hyprctl"
```

### Browser/editor conversion does nothing
Check that these binaries exist:
```bash
which wl-copy
which wl-paste
which ydotool
```
