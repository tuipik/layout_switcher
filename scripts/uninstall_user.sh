#!/usr/bin/env bash
set -euo pipefail

SYSTEMD_DIR="${HOME}/.config/systemd/user"
CONFIG_DIR="${HOME}/.config/layout-switcher"
APP_DIR="${HOME}/.local/share/layout-switcher"
BIN_DIR="${HOME}/.local/bin"

echo "[1/4] Stopping and disabling user services"
systemctl --user disable --now layout-switcher.service 2>/dev/null || true
systemctl --user disable --now ydotoold.service 2>/dev/null || true

echo "[2/4] Removing user service files"
rm -f "${SYSTEMD_DIR}/layout-switcher.service"
rm -f "${SYSTEMD_DIR}/ydotoold.service"
systemctl --user daemon-reload

echo "[3/4] Uninstalling Python package"
rm -rf "${APP_DIR}"
rm -f "${BIN_DIR}/layout-switcher"

echo "[4/4] Remaining user data"
cat <<EOF
The app config was left in place:
  ${CONFIG_DIR}/config.json

If you want to remove it too:
  rm -rf "${CONFIG_DIR}"
EOF
