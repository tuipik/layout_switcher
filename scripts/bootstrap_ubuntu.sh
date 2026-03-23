#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="${HOME}/.config/layout-switcher"
SYSTEMD_DIR="${HOME}/.config/systemd/user"
CONFIG_PATH="${CONFIG_DIR}/config.json"
APP_DIR="${HOME}/.local/share/layout-switcher"
VENV_DIR="${APP_DIR}/venv"
BIN_DIR="${HOME}/.local/bin"
SHELL_NAME="$(basename "${SHELL:-}")"
PATH_SNIPPET='export PATH="$HOME/.local/bin:$PATH"'

echo "[1/8] Installing Ubuntu packages"
sudo apt update
sudo apt install -y python3 python3-pip python3-venv python3-evdev wl-clipboard ydotool ydotoold

echo "[2/8] Ensuring input access"
sudo usermod -aG input "${USER}"
sudo modprobe uinput
echo uinput | sudo tee /etc/modules-load.d/uinput.conf >/dev/null

echo "[3/8] Installing Python package"
mkdir -p "${APP_DIR}"
python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/python" -m pip install "${PROJECT_ROOT}"

echo "[4/8] Installing user config"
mkdir -p "${CONFIG_DIR}"
mkdir -p "${BIN_DIR}"
if [[ ! -f "${CONFIG_PATH}" ]]; then
  cp "${PROJECT_ROOT}/layout_switcher/default_config.json" "${CONFIG_PATH}"
fi
cat > "${BIN_DIR}/layout-switcher" <<EOF
#!/usr/bin/env bash
exec "${VENV_DIR}/bin/layout-switcher" "\$@"
EOF
chmod +x "${BIN_DIR}/layout-switcher"
if [[ "${SHELL_NAME}" == "zsh" ]]; then
  SHELL_RC="${HOME}/.zshrc"
elif [[ "${SHELL_NAME}" == "bash" ]]; then
  SHELL_RC="${HOME}/.bashrc"
else
  SHELL_RC="${HOME}/.profile"
fi
touch "${SHELL_RC}"
if ! grep -Fqs "${PATH_SNIPPET}" "${SHELL_RC}"; then
  printf '\n%s\n' "${PATH_SNIPPET}" >> "${SHELL_RC}"
fi

echo "[5/8] Configuring hotkeys"
if apt-cache show keyd >/dev/null 2>&1; then
  echo "keyd package is available; using Compose -> F24 setup"
  sudo apt install -y keyd
  sudo cp "${PROJECT_ROOT}/keyd/layout-switcher.conf" /etc/keyd/default.conf
  sudo systemctl enable --now keyd
  sudo keyd reload
else
  echo "keyd package not found in apt; switching config to F8 / Shift+F8 fallback"
  python3 - "$CONFIG_PATH" <<'PY'
import json, sys
path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    data = json.load(f)
data.setdefault("hotkeys", {})
data["hotkeys"]["buffer_mode"] = "F8"
data["hotkeys"]["selection_mode"] = "SHIFT+F8"
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY
fi

echo "[6/8] Installing user services"
mkdir -p "${SYSTEMD_DIR}"
cp "${PROJECT_ROOT}/systemd/ydotoold.service" "${SYSTEMD_DIR}/ydotoold.service"
cp "${PROJECT_ROOT}/systemd/layout-switcher.service" "${SYSTEMD_DIR}/layout-switcher.service"

echo "[7/8] Enabling user services"
systemctl --user daemon-reload
systemctl --user enable --now ydotoold.service
systemctl --user enable --now layout-switcher.service

echo "[8/8] Running diagnostics"
export YDTOOL_SOCKET="/run/user/$(id -u)/.ydotool_socket"
if command -v timeout >/dev/null 2>&1; then
  timeout 10s "${VENV_DIR}/bin/layout-switcher" doctor || true
else
  "${VENV_DIR}/bin/layout-switcher" doctor || true
fi

cat <<'EOF'

Bootstrap finished.

Important:
1. Log out and back in so the new input group membership takes effect.
2. After re-login, run:
   layout-switcher doctor
3. On Ubuntu without keyd, the fallback hotkeys are:
   F8 / Shift+F8
4. If the shell still does not see the command, run:
   source ~/.zshrc
EOF
