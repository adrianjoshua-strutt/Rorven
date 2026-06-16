"""Worker entrypoint for local deterministic agent work."""

from __future__ import annotations

import argparse
from time import sleep

from rorven.composition import create_local_services


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one Rorven worker leasing pass.")
    parser.add_argument("--worker-id", default="local-worker")
    parser.add_argument("--limit", type=int, default=2)
    parser.add_argument("--loop", action="store_true", help="Keep polling for ready work.")
    parser.add_argument("--poll-interval", type=float, default=2.0)
    args = parser.parse_args()

    services = create_local_services()
    while True:
        completed = services.worker.work_once(worker_id=args.worker_id, limit=args.limit)
        print(f"completed_tasks={len(completed)}")
        if not args.loop:
            break
        sleep(args.poll_interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
