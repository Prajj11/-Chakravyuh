"""Wait for both local services, then open the investigation workbench."""

import argparse
import socket
import sys
import time
import urllib.error
import urllib.request
import webbrowser

WORKBENCH = "http://127.0.0.1:3000"
HEALTH = "http://127.0.0.1:8001/api/v1/health"


def wait_for_services(timeout: float) -> None:
    deadline = time.monotonic() + timeout
    for url in (HEALTH, WORKBENCH):
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"Service did not become ready: {url}")
            try:
                with urllib.request.urlopen(url, timeout=min(2, remaining)) as response:
                    if response.status == 200:
                        break
            except (urllib.error.URLError, OSError, TimeoutError):
                pass
            time.sleep(min(0.5, max(0, deadline - time.monotonic())))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--no-browser", action="store_true", help="Check readiness only")
    mode.add_argument(
        "--ports-free",
        nargs="*",
        type=int,
        choices=(8001, 3000),
        help="Check ports before starting services (default: both)",
    )
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args()
    if not 0 < args.timeout <= 120:
        parser.error("Timeout must be greater than zero and at most 120 seconds")
    if args.ports_free is not None:
        for port in args.ports_free or (8001, 3000):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                    probe.bind(("127.0.0.1", port))
            except OSError as exc:
                print(
                    f"Port {port} is unavailable. If Chakravyuh is already running, "
                    f"open {WORKBENCH}. To restart, close its existing service windows first.",
                    file=sys.stderr,
                )
                raise SystemExit(1) from exc
        return
    try:
        wait_for_services(args.timeout)
    except TimeoutError as exc:
        print(
            f"{exc}. Check the backend and frontend terminal windows.", file=sys.stderr
        )
        raise SystemExit(1) from exc
    print(f"Chakravyuh is ready: {WORKBENCH}")
    if not args.no_browser:
        try:
            opened = webbrowser.open(WORKBENCH, new=2)
        except (webbrowser.Error, OSError):
            opened = False
        if not opened:
            print("Open the workbench address above in your browser.")


if __name__ == "__main__":
    main()
