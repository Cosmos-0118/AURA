from __future__ import annotations

import argparse

from .config import DB_PATH
from .provision import provision_changedetection
from .service import IntelligenceService
from .store import Store


def main() -> None:
    parser = argparse.ArgumentParser(description="AURA competitor intelligence maintenance commands")
    parser.add_argument(
        "command",
        nargs="?",
        default="scan-all",
        choices=("scan-all", "poll-feeds", "provision-changedetection"),
    )
    args = parser.parse_args()

    if args.command == "provision-changedetection":
        for result in provision_changedetection():
            print(result)
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
