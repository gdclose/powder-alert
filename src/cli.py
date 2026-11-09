"""Preview by default; explicit local sending and launchd catch-up mode."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta
import fcntl
import hashlib
import json
import logging
import os
from pathlib import Path
import platform
import subprocess
import sys

from .config import CONFIG_FILE, DATA_DIR, PACIFIC
from .delivery.sms import normalize_number, send_sms
from .forecast.engine import build_briefing, format_message
from .dashboard import render_dashboard

def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        os.chmod(temporary, 0o600)
        json.dump(data, stream, indent=2, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)

def load_config(path=CONFIG_FILE):
    with Path(path).open(encoding="utf-8") as stream:
        config = json.load(stream)
    if not isinstance(config, dict):
        raise ValueError("Config must be a JSON object")
    recipients = config.get("recipients", [])
    if not isinstance(recipients, list):
        raise ValueError("recipients must be a list")
    normalized = []
    for recipient in recipients:
        if not isinstance(recipient, dict):
            raise ValueError("Each recipient needs number and transport")
        number = normalize_number(recipient.get("number"))
        transport = recipient.get("transport", "imessage")
        if transport not in ("sms", "imessage"):
            raise ValueError("Recipient transport must be sms or imessage")
        if number in {r["number"] for r in normalized}:
            raise ValueError("Duplicate recipient number")
        normalized.append({"number": number, "transport": transport})
    config["recipients"] = normalized
    hour = config.get("hour", 7)
    minute = config.get("minute", 0)
    cutoff = config.get("catch_up_until_hour", 12)
    if not all(type(v) is int for v in (hour, minute, cutoff)):
        raise ValueError("Schedule times must be integers")
    if not (0 <= hour < cutoff <= 24 and 0 <= minute <= 59):
        raise ValueError("Invalid schedule or catch-up cutoff")
    return {**config, "hour": hour, "minute": minute, "catch_up_until_hour": cutoff}

def configure(path):
    if Path(path).exists():
        print(f"Settings already exist: {path}\nEdit that file to change recipients or schedule.")
        return
    print("Private settings stay on this Mac. Add only yourself for the first test.")
    raw = input("Phone numbers, international format, separated by commas: ").strip()
    numbers = [normalize_number(n.strip()) for n in raw.split(",") if n.strip()]
    if not numbers:
        raise ValueError("Enter at least one recipient")
    transport = input("Delivery [imessage/sms] (default imessage): ").strip().lower() or "imessage"
    if transport not in ("sms", "imessage"):
        raise ValueError("Choose imessage or sms")
    config = {"recipients": [{"number": n, "transport": transport} for n in numbers],
              "hour": 7, "minute": 0, "catch_up_until_hour": 12}
    write_json(path, config)
    load_config(path)
    print(f"Saved private settings to {path}. No texts sent; schedule not enabled.")

def due(now, config):
    return (now.hour, now.minute) >= (config["hour"], config["minute"]) and now.hour < config["catch_up_until_hour"]

@contextmanager
def delivery_lock(directory):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (directory / "delivery.lock").open("a") as lock:
        os.chmod(directory / "delivery.lock", 0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another delivery is running")
        yield

def deliver(message, recipients, state_path, now, sender=send_sms):
    # Mark before invoking Messages: after a crash, do not automatically duplicate
    # a submission whose actual outcome is unknown.
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    if not isinstance(state, dict):
        raise ValueError("Invalid delivery state; inspect it before sending")
    today = now.date().isoformat()
    state = {key: value for key, value in state.items() if key.startswith(today + ":")}
    failures = 0
    for recipient in recipients:
        identifier = hashlib.sha256(recipient["number"].encode()).hexdigest()
        key = today + ":" + identifier
        if key in state:
            logging.info("Skipping recipient already submitted or uncertain today")
            continue
        state[key] = {"status": "uncertain", "attempted": now.isoformat()}
        write_json(state_path, state)
        try:
            if not sender(recipient["number"], message, recipient["transport"]):
                raise RuntimeError("Messages rejected submission")
        except (RuntimeError, OSError):
            failures += 1
            logging.error("Messages submission uncertain. Inspect Messages and delivery-state.json before any manual retry.")
            continue
        state[key]["status"] = "submitted"
        write_json(state_path, state)
        logging.info("Submitted briefing to Messages (delivery receipt not available)")
    return failures

def save_outputs(briefing, directory, now):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    write_json(directory / "latest.json", briefing)
    (directory / "latest.txt").write_text(format_message(briefing), encoding="utf-8")
    (directory / "dashboard.html").write_text(render_dashboard(briefing), encoding="utf-8")
    history = directory / "history"
    write_json(history / (now.strftime("%Y-%m-%d_%H%M%S") + ".json"), briefing)
    cutoff = now - timedelta(days=30)
    for path in history.glob("*.json"):
        if datetime.fromtimestamp(path.stat().st_mtime, PACIFIC) < cutoff:
            path.unlink()

def doctor(config):
    if platform.system() != "Darwin":
        raise RuntimeError("Messages and launchd require macOS; preview works on other systems")
    if not config["recipients"]:
        raise ValueError("No recipients configured")
    script = 'tell application "Messages" to get service type of every service'
    result = subprocess.run(["/usr/bin/osascript", "-e", script],
                            capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise RuntimeError("Messages access failed. Allow your terminal/Python to control Messages in System Settings > Privacy & Security > Automation.")
    services = result.stdout.lower()
    for transport in {r["transport"] for r in config["recipients"]}:
        if transport not in services:
            raise RuntimeError(f"No {transport} service available in Messages")
    print("Messages services accessible. No texts sent. Run a self-only send test before enabling scheduling.")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=["preview", "configure", "doctor"], default="preview")
    parser.add_argument("--config", type=Path, default=CONFIG_FILE)
    parser.add_argument("--output-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--send", action="store_true", help="Actually submit texts to configured recipients")
    parser.add_argument("--scheduled", action="store_true", help="Only send during configured morning window")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        if args.command == "configure":
            configure(args.config)
            return 0
        config = load_config(args.config) if args.send or args.command == "doctor" else None
        if args.command == "doctor":
            doctor(config)
            return 0
        now = datetime.now(PACIFIC)
        if args.scheduled and not args.send:
            raise ValueError("--scheduled requires --send")
        if args.scheduled and not due(now, config):
            logging.info("Outside morning delivery window; skipping")
            return 0
        if args.send:
            if platform.system() != "Darwin":
                raise RuntimeError("Sending requires macOS; omit --send for a preview")
            if not config["recipients"]:
                raise ValueError("No recipients configured")
            with delivery_lock(args.output_dir):
                state_path = args.output_dir / "delivery-state.json"
                # Fast no-op for the 15-minute scheduler after all recipients have
                # been submitted (or marked uncertain), before requesting APIs.
                if state_path.exists():
                    state = json.loads(state_path.read_text())
                    keys = [now.date().isoformat() + ":" + hashlib.sha256(r["number"].encode()).hexdigest()
                            for r in config["recipients"]]
                    if all(key in state for key in keys):
                        logging.info("All recipients already attempted today; skipping")
                        return 0
                briefing = build_briefing(now)
                save_outputs(briefing, args.output_dir, now)
                return 1 if deliver(format_message(briefing), config["recipients"], state_path, now) else 0
        briefing = build_briefing(now)
        save_outputs(briefing, args.output_dir, now)
        print(format_message(briefing))
        print("\nPreview only. Dashboard: " + str(args.output_dir / "dashboard.html"))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        # Config parsing errors can contain recipient details: do not dump traces.
        if isinstance(exc, json.JSONDecodeError):
            logging.error("Invalid JSON in settings/state; fix the file before retrying")
        else:
            logging.error("%s", exc)
        return 1

if __name__ == "__main__":
    sys.exit(main())
