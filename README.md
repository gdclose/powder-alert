# Powder Alert — personal Mac edition

A free, local Mt. Bachelor and Bend (97703) forecast for you and a few friends.
Runs on your Mac and submits messages through Apple's Messages app. No Twilio,
cloud hosting, API keys, subscriptions or pip packages required. Your mobile
carrier's normal messaging terms still apply to SMS.

The daily text is a compact briefing: Bachelor snow windows, weather, resort summary,\n10-day snow signals and a one-line Bend forecast. Full daily tables and lift timestamps\nstay in the local dashboard. Use `python3 -m src.cli --detailed` for a full terminal preview.\n\n## Included

- Equal-weight GFS / ECMWF / ICON blend from Open-Meteo.
- New snow through 24 / 48 / 72 hours, starting at the current hour, for
  Bachelor base elevation and a representative NW Bend point in 97703.
- Ten consecutive Pacific calendar days of weather, temperatures and snowfall.
- Snow ranges showing **min/max of available models**, not probability bounds.
  This is a multi-model blend, not a perturbed-member probabilistic ensemble.
  Missing model hours are excluded; shorter model horizons are never padded
  with zero snow. Single-model results are marked.
- Bachelor's latest primary/alpine snow report and winter lift feed.
  Updates older than 36 hours are flagged, not presented as current operations.
- Local HTML dashboard, full text, JSON snapshot and 30 days of forecast history.
- Preview by default, per-recipient duplicate protection, private local settings.
- A per-user LaunchAgent for daily runs and morning catch-up.

Mountain forecasts use the base point at 1,920 m (~6,300 ft). They are not summit
forecasts and do not predict lift closures. Bend's representative point is
44.079, -121.343 at 1,090 m; a ZIP code spans varying elevations. Adjust points
in src/config.py if needed. Model ranges are not calibrated uncertainty, and
snowfall is the API's model snow-depth estimate, not a verified resort total.

## 1. Install on this Mac

Install **Python 3.11 or newer** from https://www.python.org/downloads/macos/
if needed. Check with `python3 --version`. Git may prompt you to install Apple's
Command Line Tools on a new Mac.

In Terminal:

```bash
mkdir -p ~/Projects
cd ~/Projects
git clone --branch modernize-mac-personal https://github.com/gdclose/powder-alert.git
cd powder-alert
bash scripts/install.sh
```

Keep the folder here (not Desktop/Documents/iCloud). Moving it later requires
reinstalling the LaunchAgent. The installer creates a virtual environment and
asks for phone numbers. **Start with only your own number.** Use international
format, e.g. +15555550123. It does not send anything or enable scheduling.

The private settings file is `~/.config/powder-alert/config.json`, outside this
public repository, created with owner-only permissions. Add friends there after
your self-only test. Each recipient can use a different transport:

```json
{
  "recipients": [
    {"number": "+15555550123", "transport": "imessage"},
    {"number": "+15555550124", "transport": "sms"}
  ],
  "hour": 7,
  "minute": 0,
  "catch_up_until_hour": 12
}
```

Do not commit real phone numbers or your private config to GitHub.

## 2. Set up Messages and preview

1. Open Messages and sign in. Confirm you can manually send a message.
2. For blue-bubble recipients use `imessage`. For actual SMS use `sms` and
   enable **Text Message Forwarding** for this Mac on your iPhone, signed into
   the same Apple Account. The iPhone must remain available for SMS relay.
3. Run:

```bash
.venv/bin/python -m src.cli doctor
.venv/bin/python -m src.cli
open "$HOME/Library/Application Support/PowderAlert/dashboard.html"
```

Allow Terminal/Python to control Messages when macOS prompts. If blocked, check
System Settings → Privacy & Security → Automation. The doctor checks service
access without sending. Scheduled runs can require separate permission on some
macOS versions; verify the first scheduled run and its log.

Preview fetches live forecasts and reports but **never sends messages**.
Outputs live under `~/Library/Application Support/PowderAlert/`.

## 3. Send one self-only test

With only your number in the private config:

```bash
.venv/bin/python -m src.cli --send
```

Check Messages and your phone. Submission is not a delivery/read receipt.
AppleScript service support varies with macOS and carrier setup; actual
iMessage/SMS delivery needs this Mac test. If SMS service is unavailable, fix
iPhone forwarding or switch Apple recipients to iMessage.

The compact briefing may still span multiple SMS segments.
It is one text submission per recipient, not a group text.

## 4. Enable daily sending

After the self-only test works, add friends to the private settings. Keep this
Mac's system time zone set to Pacific, then run:

```bash
.venv/bin/python scripts/schedule.py --enable
```

Default: **7:00 a.m. Pacific**. Enabling also runs the morning check immediately;
new recipients may receive today's briefing if enabled before noon. Recipients
already attempted today are skipped.

A 15-minute check retries forecast/network failures and catches up after login
or waking, until noon. No late-evening backlog is sent. It does not wake a shut
down Mac or bypass the login screen. The Mac needs to be logged into your user
account, online, and awake at delivery time (or wake before the cutoff).
launchd calendar triggers catch up after sleep; if it stays asleep, delivery waits.
A new network attempt generates a fresh briefing, not a cached prior-day text.

Change `hour`, `minute`, or cutoff in the private config and rerun
`--enable`. To stop:

```bash
.venv/bin/python scripts/schedule.py --disable
```

## Troubleshooting and delivery protection

- Log: `~/Library/Application Support/PowderAlert/launchd.log`.
- Check the agent: `launchctl print gui/$(id -u)/com.powderalert.daily`.
- No complete next-24-hour forecast for either location: no texts sent; next
  morning check can retry.
- A resort feed failure does not stop weather delivery; report availability is
  stated. A lift entity's last change is only a conservative freshness signal,
  not proof the resort has or has not reviewed it.
- Each recipient is marked *uncertain* on disk before invoking Messages, then
  *submitted* when AppleScript succeeds. Neither automatically retries that day.
  This prefers a potentially missed briefing to duplicates after a timeout/crash.
- If a send fails: first inspect Messages. Disable the scheduler before editing
  `delivery-state.json`. Only if you confirm nothing was submitted, remove that
  recipient's entry and rerun `--send`. Deleting the entire ledger allows all
  recipients to receive another briefing that day.
- Preview does not consume the daily send allowance.
- Settings changes do not read your Contacts or Messages history.
- Forecast history is retained for later evaluation; automatic accuracy-based
  model weighting is **not implemented**. Equal weights are explicit.
- Snapshot HTML is local and does not auto-refresh. Run preview again to update.
- Logs can be removed while scheduling is disabled if they become large.

## Validation

```bash
python3 -m unittest discover -s tests -v
python3 -m src.cli --output-dir /tmp/powder-alert-preview
```

Tests use fixtures/mocks and send no texts. Live preview needs network access.
Actual Messages and launchd operation must be verified on macOS.

## Sources

- Weather: [Open-Meteo](https://open-meteo.com/) (CC BY 4.0 attribution).
  Free API is for qualifying noncommercial use within published limits.
- Reports: [Mt. Bachelor](https://www.mtbachelor.com/the-mountain/lift-trail-report/).
  CMS schema/availability can change; timestamps and unavailable states matter.
- [Apple Messages setup](https://support.apple.com/guide/messages/set-up-messages-ichte16154fb/mac)
- [Apple text forwarding](https://support.apple.com/102545)
- [Apple timed jobs](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html)

Personal project; check resort operations before heading up the mountain.
