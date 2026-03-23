#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="${HOME}/.config/layout-switcher"
SYSTEMD_DIR="${HOME}/.config/systemd/user"

echo "[1/5] Installing Python package"
python -m pip install --user "${PROJECT_ROOT}"

echo "[2/5] Creating user config directory"
mkdir -p "${CONFIG_DIR}"
if [[ ! -f "${CONFIG_DIR}/config.json" ]]; then
  cp "${PROJECT_ROOT}/layout_switcher/default_config.json" "${CONFIG_DIR}/config.json"
  echo "Created ${CONFIG_DIR}/config.json"
else
  echo "Keeping existing ${CONFIG_DIR}/config.json"
fi

echo "[3/5] Installing systemd user services"
mkdir -p "${SYSTEMD_DIR}"
cp "${PROJECT_ROOT}/systemd/ydotoold.service" "${SYSTEMD_DIR}/ydotoold.service"
cp "${PROJECT_ROOT}/systemd/layout-switcher.service" "${SYSTEMD_DIR}/layout-switcher.service"

echo "[4/5] Reloading and enabling services"
systemctl --user daemon-reload
systemctl --user enable --now ydotoold.service
systemctl --user enable --now layout-switcher.service

echo "[5/5] Next manual steps"
cat <<'EOF'
1. Ensure your user is in the input group:
   sudo usermod -aG input $USER

2. Ensure uinput is loaded:
   sudo modprobe uinput

3. Install the keyd remap:
   sudo cp keyd/layout-switcher.conf /etc/keyd/default.conf
   sudo systemctl enable --now keyd
   sudo keyd reload

4. Log out and back in after any group change.

5. Check the service:
   systemctl --user status layout-switcher.service

6. Run a quick diagnostic:
   layout-switcher doctor
EOF
