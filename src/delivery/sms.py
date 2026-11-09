"""Local Messages delivery. Values are argv, never AppleScript source."""
import platform
import re
import subprocess

SCRIPT = '''on run argv
    set recipientNumber to item 1 of argv
    set messageBody to item 2 of argv
    set transportName to item 3 of argv
    tell application "Messages"
        if transportName is "sms" then
            set targetService to first service whose service type is SMS
        else
            set targetService to first service whose service type is iMessage
        end if
        set targetBuddy to buddy recipientNumber of targetService
        send messageBody to targetBuddy
    end tell
end run'''

def normalize_number(value):
    if not isinstance(value, str):
        raise ValueError("Recipients must be phone numbers as strings")
    number = re.sub(r"[\s().-]", "", value)
    if not re.fullmatch(r"\+[1-9]\d{7,14}", number):
        raise ValueError("Use international phone format, for example +15555550123")
    return number

def send_sms(to_number, message, transport="imessage"):
    number = normalize_number(to_number)
    if transport not in ("imessage", "sms"):
        raise ValueError("transport must be imessage or sms")
    if platform.system() != "Darwin":
        raise RuntimeError("Messages delivery requires macOS")
    try:
        subprocess.run(
            ["/usr/bin/osascript", "-e", SCRIPT, number, message, transport],
            check=True, capture_output=True, text=True, timeout=45,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(
            "Messages did not confirm submission. Check Automation permission and Messages setup. "
            "Delivery may be uncertain; inspect Messages before retrying."
        ) from exc
    return True  # Submission to Messages, not a carrier/read receipt.
