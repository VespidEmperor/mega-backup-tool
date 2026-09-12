#!/usr/bin/env bash
set -euo pipefail

echo "=== mega-backup-tool setup ==="

if ! command -v python >/dev/null 2>&1; then
  echo "[ERROR] python not found on PATH." >&2
  exit 1
fi

# python -m pip, not bare pip, so deps land in the same interpreter as `python`.
python -m pip install -r requirements.txt

# mega.py (server_copy.py dep) installed --no-deps: 1.0.8 pins tenacity<6 which
# is broken on Python 3.11+; modern tenacity is installed via requirements.txt.
python -m pip install --no-deps "mega.py==1.0.8"

if ! command -v megatools >/dev/null 2>&1; then
  echo
  echo "[WARNING] megatools not found on PATH."
  echo "  Debian/Ubuntu: sudo apt install megatools"
  echo "  Or download a build: https://xff.cz/megatools/builds/builds/"
  echo
fi

echo
echo "Setup complete. Run: python generate_accounts.py"
