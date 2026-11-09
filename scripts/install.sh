#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Install on your Mac. Preview and tests can run on other systems."
  exit 1
fi
python3 -c 'import sys; assert sys.version_info >= (3,11), "Install Python 3.11 or newer from python.org first"'
python3 -m venv .venv
.venv/bin/python -m src.cli configure
echo
echo 'Installed. Next:'
echo '  .venv/bin/python -m src.cli doctor'
echo '  .venv/bin/python -m src.cli'
echo 'No texts sent; scheduling is off.'
