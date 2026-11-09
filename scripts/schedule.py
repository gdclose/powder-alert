#!/usr/bin/env python3
"""Install/uninstall the user's LaunchAgent. Enabling may send during the morning window."""
import argparse
import os
from pathlib import Path
import platform
import plistlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.cli import load_config
from src.config import DATA_DIR

LABEL = "com.powderalert.daily"

def make_plist(root, data_dir, hour, minute):
    return {
        "Label": LABEL,
        "ProgramArguments": [str(root / ".venv" / "bin" / "python"), "-m", "src.cli", "--send", "--scheduled"],
        "WorkingDirectory": str(root),
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "StartInterval": 900,
        "RunAtLoad": True,
        "ProcessType": "Background",
        "StandardOutPath": str(data_dir / "launchd.log"),
        "StandardErrorPath": str(data_dir / "launchd.log"),
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--enable", action="store_true")
    group.add_argument("--disable", action="store_true")
    args = parser.parse_args()
    if platform.system() != "Darwin":
        parser.error("Run this on your Mac")
    domain = f"gui/{os.getuid()}"
    path = Path.home() / "Library" / "LaunchAgents" / (LABEL + ".plist")
    target = domain + "/" + LABEL
    # Only ignore the expected 'not loaded' case; installation errors remain visible.
    loaded = subprocess.run(["launchctl", "print", target], capture_output=True).returncode == 0
    if loaded:
        subprocess.run(["launchctl", "bootout", target], check=True)
    if args.disable:
        path.unlink(missing_ok=True)
        print("Daily sending disabled.")
        return
    config = load_config()
    if not config["recipients"]:
        parser.error("Configure recipients first")
    if not (ROOT / ".venv" / "bin" / "python").exists():
        parser.error("Run bash scripts/install.sh first")
    local = subprocess.check_output(["date", "+%Z"], text=True).strip()
    if local not in ("PST", "PDT"):
        parser.error("Set this Mac's time zone to Pacific before enabling. The runner uses Pacific time.")
    DATA_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        plistlib.dump(make_plist(ROOT, DATA_DIR, config["hour"], config["minute"]), stream)
    subprocess.run(["launchctl", "bootstrap", domain, str(path)], check=True)
    print(f'Daily sending enabled at {config["hour"]:02}:{config["minute"]:02} Pacific, with morning catch-up.')
    print("May run now if inside the morning window. Logs: " + str(DATA_DIR / "launchd.log"))

if __name__ == "__main__":
    main()
