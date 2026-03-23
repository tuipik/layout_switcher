#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -r /etc/os-release ]]; then
  . /etc/os-release
else
  echo "Cannot detect Linux distribution: /etc/os-release is missing" >&2
  exit 1
fi

case "${ID:-}" in
  ubuntu)
    exec "${PROJECT_ROOT}/scripts/bootstrap_ubuntu.sh"
    ;;
  manjaro|arch)
    exec "${PROJECT_ROOT}/scripts/bootstrap_arch.sh"
    ;;
  *)
    if [[ "${ID_LIKE:-}" == *debian* ]]; then
      exec "${PROJECT_ROOT}/scripts/bootstrap_ubuntu.sh"
    fi
    if [[ "${ID_LIKE:-}" == *arch* ]]; then
      exec "${PROJECT_ROOT}/scripts/bootstrap_arch.sh"
    fi
    echo "Unsupported distribution: ID='${ID:-unknown}', ID_LIKE='${ID_LIKE:-unknown}'" >&2
    echo "Use one of the distro-specific scripts manually:" >&2
    echo "  ./scripts/bootstrap_ubuntu.sh" >&2
    echo "  ./scripts/bootstrap_arch.sh" >&2
    exit 1
    ;;
esac
