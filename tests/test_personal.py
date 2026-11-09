import importlib.util
import json
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from src.config import PACIFIC
from src.forecast.engine import rolling_windows, blend_forecasts, format_message
from src.delivery.sms import normalize_number, send_sms, SCRIPT
from src.scrapers.bachelor import parse_snow, parse_lifts
from src.cli import deliver, due, load_config, main
from src.dashboard import render_dashboard

NOW = datetime(2026, 1, 1, 7, tzinfo=PACIFIC)

def hourly(hours=72, snow=1):
    start = int(NOW.timestamp())
    return {"hourly": {"time": list(range(start, start + (hours + 1) * 3600, 3600)),
                       "snowfall": [snow] * (hours + 1),
                       "wind_gusts_10m": [30] * (hours + 1),
                       "temperature_2m": [20] * (hours + 1),
                       "weather_code": [73] * (hours + 1)}}

def daily(days, snow):
    start = int(NOW.replace(hour=0).timestamp())
    return {"daily": {"time": [start + i*86400 for i in range(days)], "snowfall_sum": snow,
                      "temperature_2m_max": [30]*days, "temperature_2m_min": [20]*days,
                      "weather_code": [73]*days, "wind_gusts_10m_max": [40]*days}}

class ForecastTests(unittest.TestCase):
    def test_cumulative_windows_exclude_current_and_include_end(self):
        data = hourly()
        data["hourly"]["snowfall"][0] = 999
        windows = rolling_windows({"GFS": data}, NOW)
        self.assertEqual([w["snow"]["mean"] for w in windows], [24,48,72])

    def test_partial_horizon_never_becomes_zero(self):
        windows = rolling_windows({"GFS": hourly(), "ICON": hourly(48, 2)}, NOW)
        self.assertEqual(windows[1]["snow"]["models"], 2)
        self.assertEqual(windows[2]["by_model"], {"GFS": 72})

    def test_null_hour_excludes_whole_model_for_that_window(self):
        data = hourly()
        data["hourly"]["snowfall"][12] = None
        self.assertIsNone(rolling_windows({"GFS": data}, NOW)[0]["snow"])

    def test_hourly_rounding_and_dst_use_elapsed_time(self):
        now = datetime(2026, 3, 8, 0, 15, tzinfo=PACIFIC)
        data = hourly()
        start = int(now.timestamp()) // 3600 * 3600
        data["hourly"]["time"] = [start + i*3600 for i in range(73)]
        window = rolling_windows({"GFS": data}, now)[0]
        self.assertEqual(window["snow"]["mean"],24)
        self.assertEqual(datetime.fromisoformat(window["end"]).hour,1)

    def test_daily_unequal_horizons_and_nulls(self):
        days = blend_forecasts({"GFS": daily(3,[1,2,3]), "ICON": daily(1,[4]), "ECMWF": None})
        self.assertEqual(len(days), 3)
        self.assertEqual(days[0]["snowfall"]["models"],2)
        self.assertEqual(days[2]["snowfall"]["mean"],3)

    def test_all_missing_is_unavailable(self):
        days = blend_forecasts({"GFS": daily(1,[None])})
        self.assertIsNone(days[0]["snowfall"])

class ResortTests(unittest.TestCase):
    def report(self, location, timestamp, amount=0):
        return {"attributes":{"date":timestamp,"amount":amount,"base_depth":3},
                "relationships":{"location":{"data":{"id":location}}}}

    def test_latest_primary_report_not_first_or_nordic(self):
        old = self.report("alpine",(NOW-timedelta(days=7)).isoformat(),9)
        current = self.report("alpine",NOW.isoformat(),0)
        nordic = self.report("nordic",NOW.isoformat(),25)
        result = parse_snow({"data":[old,nordic,current]}, {"alpine"}, NOW)
        self.assertEqual(result["new_snow_24h"],0)
        self.assertFalse(result["stale"])

    def test_future_or_undated_report_not_current(self):
        data={"data":[self.report("a",(NOW+timedelta(days=2)).isoformat())]}
        self.assertIsNone(parse_snow(data,{"a"},NOW))

    def test_old_lifts_and_summer_filter(self):
        lifts = parse_lifts({"data":[
            {"attributes":{"name":"Summit","season":"winter","status":"open","changed":(NOW-timedelta(days=3)).isoformat()}},
            {"attributes":{"name":"Summer","season":"summer","status":"open","changed":NOW.isoformat()}}]},NOW)
        self.assertEqual(len(lifts),1)
        self.assertTrue(lifts[0]["stale"])

class DeliveryTests(unittest.TestCase):
    def test_number_validation(self):
        self.assertEqual(normalize_number("+1 (555) 555-0123"),"+15555550123")
        with self.assertRaises(ValueError): normalize_number('"; do shell script "oops"')

    @patch("src.delivery.sms.platform.system", return_value="Darwin")
    @patch("src.delivery.sms.subprocess.run")
    def test_applescript_message_is_an_argument(self, run, system):
        body = 'snow "quotes"\n$(touch /tmp/never) \\ backslash'
        send_sms("+15555550123",body,"sms")
        args = run.call_args.args[0]
        self.assertEqual(args[2],SCRIPT)
        self.assertEqual(args[4],body)
        self.assertEqual(args[5],"sms")
        self.assertNotIn(body, SCRIPT)

    def test_success_and_uncertain_attempts_not_automatically_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)/"state.json"
            recipients=[{"number":"+15555550123","transport":"imessage"},
                        {"number":"+15555550124","transport":"sms"}]
            calls=[]
            def sender(number,*args):
                calls.append(number)
                if number.endswith("124"): raise RuntimeError("uncertain")
                return True
            self.assertEqual(deliver("forecast",recipients,state,NOW,sender),1)
            self.assertEqual(deliver("forecast",recipients,state,NOW,sender),0)
            self.assertEqual(len(calls),2)
            statuses={r["status"] for r in json.loads(state.read_text()).values()}
            self.assertEqual(statuses,{"submitted","uncertain"})
            self.assertNotIn("+15555550123",state.read_text())
            self.assertEqual(state.stat().st_mode & 0o777,0o600)

    def test_corrupt_ledger_stops_before_sending(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)/"state.json";state.write_text("{bad")
            with self.assertRaises(ValueError):
                deliver("forecast",[],state,NOW,lambda *a:self.fail("must not send"))

    def test_morning_gate(self):
        config={"hour":7,"minute":0,"catch_up_until_hour":12}
        self.assertFalse(due(NOW.replace(hour=6),config))
        self.assertTrue(due(NOW.replace(hour=11),config))
        self.assertFalse(due(NOW.replace(hour=12),config))

    def test_duplicate_numbers_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"settings.json"
            path.write_text(json.dumps({"recipients":[{"number":"+15555550123"},{"number":"+1 555 555 0123"}]}))
            with self.assertRaises(ValueError):load_config(path)

    @patch("src.cli.build_briefing")
    @patch("src.cli.send_sms")
    def test_preview_never_sends(self,sender,build):
        build.side_effect=RuntimeError("offline")
        with patch("sys.argv",["powder-alert"]):
            self.assertEqual(main(),1)
        sender.assert_not_called()

    def test_plist_uses_separate_args_for_paths_with_spaces(self):
        spec=importlib.util.spec_from_file_location("schedule",Path(__file__).parents[1]/"scripts/schedule.py")
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        data=module.make_plist(Path("/Users/Test User/powder-alert"),Path("/tmp/Test Data"),7,15)
        self.assertEqual(data["ProgramArguments"][0],"/Users/Test User/powder-alert/.venv/bin/python")
        self.assertEqual(data["StartCalendarInterval"],{"Hour":7,"Minute":15})
        self.assertTrue(data["RunAtLoad"])

if __name__ == "__main__":
    unittest.main()
