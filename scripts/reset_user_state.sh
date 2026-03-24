#!/usr/bin/env bash
set -euo pipefail

SYSTEMD_DIR="${HOME}/.config/systemd/user"
CONFIG_DIR="${HOME}/.config/layout-switcher"
APP_DIR="${HOME}/.local/share/layout-switcher"
BIN_DIR="${HOME}/.local/bin"

echo "[1/5] Stopping and disabling user services"
systemctl --user disable --now layout-switcher.service 2>/dev/null || true
systemctl --user disable --now ydotoold.service 2>/dev/null || true

echo "[2/5] Removing user service files"
rm -f "${SYSTEMD_DIR}/layout-switcher.service"
rm -f "${SYSTEMD_DIR}/ydotoold.service"
systemctl --user daemon-reload

echo "[3/5] Removing app files"
rm -rf "${APP_DIR}"
rm -f "${BIN_DIR}/layout-switcher"

echo "[4/5] Removing user config"
rm -rf "${CONFIG_DIR}"

echo "[5/5] Done"
cat <<'EOF'
User-side layout-switcher state has been removed.

You can now run a clean install again, for example:
  ./scripts/bootstrap.sh
EOF
