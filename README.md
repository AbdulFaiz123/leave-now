# Leave Now

A tiny command-line tool that answers one question:

> **When do I need to walk out the door to catch my next train, and can I still make it?**

Transit apps tell you when the train departs. Leave Now tells you when to **leave home**, using live departure data (including delays) and your own walking time to the station.

```
  Leave in 4 min → S5 at 20:20, +2 delay
  towards Westkreuz · platform 2

  Next options:
    leave 20:26 (in 10 min)  S5     20:32  on time      → Westkreuz
    leave 20:36 (in 20 min)  S5     20:42  +1 delay     → Westkreuz

  S Ostkreuz Bhf (Berlin) · 6 min walk
```

## Requirements

- Python 3.8+ (standard library only, nothing to install)
- Internet connection

## Setup

```bash
python3 leave.py setup
```

Type your home station, pick it from the list, and enter how many minutes it takes to walk there (door to platform). This is saved to `~/.config/leave-now/config.json`.

If you're in Berlin/Brandenburg, you can use the VBB data source instead of Deutsche Bahn:

```bash
python3 leave.py setup --api vbb
```

## Usage

```bash
python3 leave.py              # when should I leave?
python3 leave.py --walk 10    # slower today? override the walk time once
```

## How it works

1. Fetches upcoming departures from your stop via the free [transport.rest](https://transport.rest) API (`v6.db.transport.rest` or `v6.vbb.transport.rest`).
2. Uses the **real** departure time (scheduled + delay), not the timetable.
3. Leave time = real departure − walking time.
4. Hides trains you can no longer catch, and cancelled trains.
5. Prints the best option first, then the next 3.

## Roadmap

- [x] Config with stop and walk time
- [x] Live departures
- [x] Delay-aware leave time
- [x] Catchable trains only
- [x] One clear answer first
- [ ] Urgency colors (green / yellow / red)
- [ ] Line and direction filter (e.g. only S5 towards the city)
- [ ] Buffer setting (extra minutes for tickets, stairs, slow mornings)
- [ ] Friendly errors when the API is down or you're offline
- [ ] Multiple saved routes, watch mode, desktop notifications, cancellation alerts

Out of scope: journey planning, transfers, ticket buying.
