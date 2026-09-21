from __future__ import annotations

import argparse

from .config import HOST, PORT, DB_PATH
from .server import serve
from .service import IntelligenceService
from .store import Store


def main() -> None:
    parser = argparse.ArgumentParser(description="JA Assure competitor intelligence")
    parser.add_argument("command", nargs="?", default="serve", choices=("serve", "scan-all", "poll-feeds"))
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", default=PORT, type=int)
    args = parser.parse_args()

    if args.command == "serve":
        serve(args.host, args.port)
        return

    service = IntelligenceService(Store(DB_PATH))
    if args.command == "scan-all":
        for result in service.scan_all():
            print(result.to_dict())
    else:
        for result in service.poll_feeds():
            print(result)


if __name__ == "__main__":
    main()
