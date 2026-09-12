#!/usr/bin/env bash
set -euo pipefail

echo "=== mega-backup-tool setup ==="

if ! command -v python >/dev/null 2>&1; then
  echo "[ERROR] python not found on PATH." >&2
  exit 1
fi

# python -m pip, not bare pip, so deps land in the same interpreter as `python`.
python -m pip install -r requirements.txt

if ! command -v megatools >/dev/null 2>&1; then
  echo
  echo "[WARNING] megatools not found on PATH."
  echo "  Debian/Ubuntu: sudo apt install megatools"
  echo "  Or download a build: https://xff.cz/megatools/builds/builds/"
  echo
fi

echo
echo "Setup complete. Run: python generate_accounts.py"
