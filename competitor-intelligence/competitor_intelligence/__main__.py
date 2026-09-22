from __future__ import annotations

import argparse
import time

from .config import DB_PATH, HOST, PORT, SCAN_INTERVAL
from .provision import provision_changedetection
from .server import serve
from .service import IntelligenceService
from .store import Store


def main() -> None:
    parser = argparse.ArgumentParser(description="JA Assure competitor intelligence")
    parser.add_argument(
        "command",
        nargs="?",
        default="serve",
        choices=("serve", "scan-all", "poll-feeds", "worker", "provision-changedetection"),
    )
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", default=PORT, type=int)
    args = parser.parse_args()

    if args.command == "serve":
        serve(args.host, args.port)
        return

    if args.command == "provision-changedetection":
        for result in provision_changedetection():
            print(result)
        return

    service = IntelligenceService(Store(DB_PATH))
    if args.command == "scan-all":
        for result in service.scan_all():
            print(result.to_dict())
    elif args.command == "poll-feeds":
        for result in service.poll_feeds():
            print(result)
    else:
        print(f"Competitor intelligence worker polling every {SCAN_INTERVAL}s")
        try:
            while True:
                try:
                    print(service.sync_changedetection(), flush=True)
                except Exception as exc:
                    print(f"Changedetection sync unavailable: {exc}", flush=True)
                for watch in service.due_watches():
                    result = service.scan_watch(watch)
                    print(result.to_dict(), flush=True)
                for result in service.poll_feeds():
                    print(result, flush=True)
                time.sleep(SCAN_INTERVAL)
        except KeyboardInterrupt:
            print("\nStopping competitor intelligence worker")


if __name__ == "__main__":
    main()
