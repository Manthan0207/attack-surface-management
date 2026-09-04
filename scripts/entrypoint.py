"""Container entrypoint: migrate DB, then start the API."""

from __future__ import annotations

import subprocess
import sys


def main() -> None:
    print("Running database migrations...", flush=True)
    subprocess.check_call([sys.executable, "-m", "alembic", "upgrade", "head"])

    print("Starting API...", flush=True)
    raise SystemExit(
        subprocess.call(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
            ]
        )
    )


if __name__ == "__main__":
    main()
