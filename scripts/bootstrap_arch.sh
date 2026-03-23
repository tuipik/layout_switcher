#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="${HOME}/.config/layout-switcher"
SYSTEMD_DIR="${HOME}/.config/systemd/user"
CONFIG_PATH="${CONFIG_DIR}/config.json"
APP_DIR="${HOME}/.local/share/layout-switcher"
VENV_DIR="${APP_DIR}/venv"
BIN_DIR="${HOME}/.local/bin"

echo "[1/7] Installing Arch/Manjaro packages"
sudo pacman -S --needed python python-pip python-evdev ydotool wl-clipboard keyd

echo "[2/7] Ensuring input access"
sudo usermod -aG input "${USER}"
sudo modprobe uinput
echo uinput | sudo tee /etc/modules-load.d/uinput.conf >/dev/null

echo "[3/7] Installing Python package"
mkdir -p "${APP_DIR}"
python -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/python" -m pip install "${PROJECT_ROOT}"

echo "[4/7] Installing user config"
mkdir -p "${CONFIG_DIR}"
mkdir -p "${BIN_DIR}"
if [[ ! -f "${CONFIG_PATH}" ]]; then
  cp "${PROJECT_ROOT}/layout_switcher/default_config.json" "${CONFIG_PATH}"
fi
ln -sf "${VENV_DIR}/bin/layout-switcher" "${BIN_DIR}/layout-switcher"

echo "[5/7] Installing keyd remap"
sudo cp "${PROJECT_ROOT}/keyd/layout-switcher.conf" /etc/keyd/default.conf
sudo systemctl enable --now keyd
sudo keyd reload

echo "[6/7] Installing and enabling user services"
mkdir -p "${SYSTEMD_DIR}"
cp "${PROJECT_ROOT}/systemd/ydotoold.service" "${SYSTEMD_DIR}/ydotoold.service"
cp "${PROJECT_ROOT}/systemd/layout-switcher.service" "${SYSTEMD_DIR}/layout-switcher.service"
systemctl --user daemon-reload
systemctl --user enable --now ydotoold.service
systemctl --user enable --now layout-switcher.service

echo "[7/7] Running diagnostics"
export YDTOOL_SOCKET="/run/user/$(id -u)/.ydotool_socket"
"${VENV_DIR}/bin/layout-switcher" doctor || true

cat <<'EOF'

Bootstrap finished.

Important:
1. Log out and back in so the new input group membership takes effect.
2. After re-login, run:
   layout-switcher doctor
3. Default hotkeys stay on:
   Compose / Shift+Compose
EOF
