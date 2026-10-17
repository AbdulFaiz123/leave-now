#!/usr/bin/env python3
"""Leave Now: when do I need to walk out the door to catch my next train?

Usage:
  leave.py setup            Pick your home stop and walking time (saved to config)
  leave.py                  Show when to leave for the next catchable departures
  leave.py --walk 7         Override walking time for this run
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

APIS = {
    "db": "https://v6.db.transport.rest",
    "vbb": "https://v6.vbb.transport.rest",
}
CONFIG_PATH = os.path.expanduser(
    os.environ.get("LEAVE_NOW_CONFIG", "~/.config/leave-now/config.json")
)
TIMEOUT_S = 8
OPTIONS_SHOWN = 3


# ---------- config (feature 1) ----------

def load_config():
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


# ---------- API (feature 2) ----------

def api_get(base, path, params):
    url = f"{base}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "leave-now-cli"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return json.load(resp)


def search_stops(base, query):
    results = api_get(base, "/locations", {
        "query": query, "results": 6, "addresses": "false", "poi": "false",
    })
    return [r for r in results if r.get("type") in ("stop", "station")]


def fetch_departures(base, stop_id, window_min):
    data = api_get(base, f"/stops/{stop_id}/departures", {
        "duration": window_min, "results": 40, "remarks": "false",
    })
    # v6 wraps the list in {"departures": [...]}; older versions return a bare list
    return data["departures"] if isinstance(data, dict) else data


# ---------- leave-time logic (features 3 & 4) ----------

def parse_time(s):
    return datetime.fromisoformat(s) if s else None


def catchable_options(departures, walk_min, now):
    """Return departures you can still make, with the time you must leave."""
    options = []
    seen = set()
    for d in departures:
        if d.get("cancelled"):
            continue
        # "when" is the real-time departure (planned + delay) when live data exists
        real = parse_time(d.get("when")) or parse_time(d.get("plannedWhen"))
        if real is None:
            continue
        leave_at = real - timedelta(minutes=walk_min)
        if leave_at < now:
            continue
        line = (d.get("line") or {}).get("name", "?")
        key = (line, real, d.get("direction"))
        if key in seen:
            continue
        seen.add(key)
        delay_s = d.get("delay")
        options.append({
            "line": line,
            "direction": d.get("direction") or "",
            "platform": d.get("platform"),
            "departs": real,
            "delay_min": None if delay_s is None else round(delay_s / 60),
            "leave_at": leave_at,
            "leave_in": int((leave_at - now).total_seconds() // 60),
        })
    options.sort(key=lambda o: o["departs"])
    return options


# ---------- output (feature 5) ----------

def bold(s):
    return f"\033[1m{s}\033[0m" if sys.stdout.isatty() else s


def delay_text(o):
    if o["delay_min"] is None:
        return "no live data"
    if o["delay_min"] == 0:
        return "on time"
    return f"{o['delay_min']:+d} delay"


def leave_phrase(o):
    return "LEAVE NOW" if o["leave_in"] == 0 else f"Leave in {o['leave_in']} min"


def print_answer(options, stop_name, walk_min):
    if not options:
        print(f"No catchable departures from {stop_name} in the next hour.")
        return
    top = options[0]
    local = lambda t: t.astimezone().strftime("%H:%M")
    print()
    print(bold(f"  {leave_phrase(top)} → {top['line']} at {local(top['departs'])}, {delay_text(top)}"))
    print(f"  towards {top['direction']}" + (f" · platform {top['platform']}" if top["platform"] else ""))
    print()
    rest = options[1:1 + OPTIONS_SHOWN]
    if rest:
        print("  Next options:")
        for o in rest:
            print(f"    leave {local(o['leave_at'])} (in {o['leave_in']:>2} min)  "
                  f"{o['line']:<6} {local(o['departs'])}  {delay_text(o):<12} → {o['direction']}")
        print()
    print(f"  {stop_name} · {walk_min} min walk")


# ---------- commands ----------

def cmd_setup(api_name):
    base = APIS[api_name]
    query = input("Your home stop (e.g. 'Berlin Ostkreuz'): ").strip()
    stops = search_stops(base, query)
    if not stops:
        sys.exit("No stops found. Try a different name.")
    for i, s in enumerate(stops, 1):
        print(f"  {i}. {s['name']}")
    choice = input(f"Pick 1-{len(stops)} [1]: ").strip() or "1"
    stop = stops[int(choice) - 1]
    walk = int(input("Minutes to walk there, door to platform: ").strip())
    save_config({"api": api_name, "stop_id": stop["id"], "stop_name": stop["name"], "walk_min": walk})
    print(f"Saved: {stop['name']}, {walk} min walk → {CONFIG_PATH}")


def cmd_leave(cfg, walk_override):
    walk = walk_override if walk_override is not None else cfg["walk_min"]
    base = APIS[cfg.get("api", "db")]
    departures = fetch_departures(base, cfg["stop_id"], walk + 60)
    now = datetime.now(timezone.utc)
    print_answer(catchable_options(departures, walk, now), cfg["stop_name"], walk)


def main():
    p = argparse.ArgumentParser(description="When do I need to leave to catch my train?")
    p.add_argument("command", nargs="?", choices=["setup"], help="run interactive setup")
    p.add_argument("--walk", type=int, help="walking minutes for this run only")
    p.add_argument("--api", choices=APIS, default="db",
                   help="API used by setup: db (all Germany) or vbb (Berlin/Brandenburg)")
    args = p.parse_args()

    if args.command == "setup":
        cmd_setup(args.api)
        return
    cfg = load_config()
    if cfg is None:
        sys.exit("No config yet. Run:  leave.py setup")
    cmd_leave(cfg, args.walk)


if __name__ == "__main__":
    main()
