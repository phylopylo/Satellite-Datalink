#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests"]
# ///
"""

NOTE: This file was generated and executed by Claude Code. This is the only such file in this repository. All other code was written by hand, by Philip Roberts.

Fetch the last N days of TLE history for SpaceX (Starlink) satellites from Space-Track.org.

Usage:
    export SPACETRACK_USER=...
    export SPACETRACK_PASS=...
    uv run fetch_spacex_tle.py [--days 7] [--out spacex_tle_week.json] [--no-thin]

Credentials are read from SPACETRACK_USER / SPACETRACK_PASS env vars, or from
a ".env" file next to this script (see .env.example). Never hardcode
credentials in this file.

Scope: matches OBJECT_NAME LIKE '%STARLINK%', which is the SpaceX Starlink
constellation -- the overwhelming majority of SpaceX-operated satellites
currently on orbit. Rocket bodies and debris are excluded.

Fidelity: Space-Track's gp_history class returns every element set published,
which for thousands of actively-maneuvering Starlink satellites can mean
several TLEs per satellite per day. For a ground-tracking simulation, one TLE
per satellite per day is already past SGP4's practical accuracy horizon, so
by default this script keeps only the latest element set per satellite per
UTC day (pass --no-thin to keep everything).

Rate limits: this makes exactly two HTTP requests total (one login, one data
query), far under Space-Track's published limits of 30 requests/minute and
300 requests/hour.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BASE_URL = "https://www.space-track.org"
LOGIN_URL = f"{BASE_URL}/ajaxauth/login"
QUERY_TEMPLATE = (
    f"{BASE_URL}/basicspacedata/query/class/gp_history/"
    "OBJECT_NAME/~~STARLINK/"
    "EPOCH/{start}--{end}/"
    "orderby/NORAD_CAT_ID,EPOCH/"
    "format/json/"
    "emptyresult/show"
)


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_credentials() -> tuple[str, str]:
    load_dotenv(Path(__file__).with_name(".env"))
    user = os.environ.get("SPACETRACK_USER")
    password = os.environ.get("SPACETRACK_PASS")
    if not user or not password:
        sys.exit(
            "Set SPACETRACK_USER and SPACETRACK_PASS (env vars, or a .env "
            "file next to this script) before running."
        )
    return user, password


def fetch_tle_history(session: requests.Session, days: int) -> list[dict]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    url = QUERY_TEMPLATE.format(
        start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d")
    )
    resp = session.get(url, timeout=120)
    resp.raise_for_status()
    return resp.json()


def thin_to_daily(records: list[dict]) -> list[dict]:
    """Keep only the latest element set per satellite per UTC day."""
    best: dict[tuple[str, str], dict] = {}
    for rec in records:
        key = (rec["NORAD_CAT_ID"], rec["EPOCH"][:10])
        if key not in best or rec["EPOCH"] > best[key]["EPOCH"]:
            best[key] = rec
    return sorted(best.values(), key=lambda r: (int(r["NORAD_CAT_ID"]), r["EPOCH"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--out", type=Path, default=Path("spacex_tle_week.json"))
    parser.add_argument(
        "--no-thin",
        action="store_true",
        help="Keep every published element set instead of one-per-satellite-per-day.",
    )
    args = parser.parse_args()

    user, password = get_credentials()

    with requests.Session() as session:
        login_resp = session.post(
            LOGIN_URL, data={"identity": user, "password": password}, timeout=30
        )
        login_resp.raise_for_status()
        if "Failed" in login_resp.text:
            sys.exit("Space-Track login failed -- check SPACETRACK_USER/SPACETRACK_PASS.")

        time.sleep(1)  # stay well clear of the 30 requests/minute limit
        records = fetch_tle_history(session, args.days)

    print(f"Fetched {len(records)} raw element sets.")
    if not args.no_thin:
        records = thin_to_daily(records)
        print(f"Thinned to {len(records)} records (<=1 per satellite per UTC day).")

    satellites = {r["NORAD_CAT_ID"] for r in records}
    print(f"Covers {len(satellites)} satellites.")

    args.out.write_text(json.dumps(records, indent=2))
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
