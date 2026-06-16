"""Worker entrypoint for local deterministic agent work."""

from __future__ import annotations

import argparse

from rorven.composition import create_local_services


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one Rorven worker leasing pass.")
    parser.add_argument("--worker-id", default="local-worker")
    parser.add_argument("--limit", type=int, default=2)
    args = parser.parse_args()

    services = create_local_services()
    completed = services.worker.work_once(worker_id=args.worker_id, limit=args.limit)
    print(f"completed_tasks={len(completed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

