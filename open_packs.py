#!/usr/bin/env python3
"""Open Wiki Masters packs until none are left (or a 401 is received).

See README.md for usage and configuration.
"""
import argparse
import sys
import time

import requests

from auth import build_cookie, get_session
from display import print_pack

URL = "https://www.wiki-masters.com/api/packs/open"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:156.0) Gecko/20100101 Firefox/156.0",
    "Accept": "*/*",
    "Accept-Language": "fr,fr-FR;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.wiki-masters.com/pulls",
    "Origin": "https://www.wiki-masters.com",
}


def open_all(delay: float, max_packs: int) -> int:
    """Open packs until none are left, a 401 or an error. Returns the number opened."""
    http = requests.Session()
    http.headers.update(HEADERS)

    count = 0
    while not max_packs or count < max_packs:
        # Check/renew the session before each pack (no network call if it is still valid).
        http.headers["Cookie"] = build_cookie(get_session())
        resp = http.post(URL, timeout=30)

        if resp.status_code == 401:
            print(f"Got a 401 after {count} pack(s) opened: stopping.")
            break
        if not resp.ok:
            print(f"Unexpected error {resp.status_code}: {resp.text[:300]}")
            break

        count += 1
        try:
            data = resp.json()
        except ValueError:
            print(f"[{count}] {resp.text[:300]}")
            data = {}
        else:
            print_pack(count, data)

        if data.get("packs_remaining") == 0:
            print("No packs remaining: stopping.")
            break

        time.sleep(delay)

    print(f"Total: {count} pack(s).")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Open the available Wiki Masters packs.")
    parser.add_argument("--delay", type=float, default=10.0, help="pause between two packs in seconds (default 10)")
    parser.add_argument("--max", type=int, default=0, help="max packs per pass (0 = unlimited)")
    parser.add_argument("--interval", type=float, default=0,
                        help="run again every N seconds (e.g. 3600); 0 = a single pass")
    args = parser.parse_args()

    while True:
        try:
            open_all(args.delay, args.max)
        except (requests.RequestException, RuntimeError) as exc:
            print(f"Error: {exc}")
            if not args.interval:
                sys.exit(1)
        if not args.interval:
            break
        print(f"Next pass in {args.interval:.0f} s.", flush=True)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
