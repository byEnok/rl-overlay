import sys
import threading
import time
import urllib.request

import uvicorn

from frontend.main import run


BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}/docs"


def wait_for_backend(timeout: float = 10.0) -> bool:
    """Wait until the FastAPI backend is responding."""
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(BACKEND_URL, timeout=0.5)
            return True
        except Exception:
            time.sleep(0.1)

    return False


def start_backend() -> tuple[uvicorn.Server, threading.Thread]:
    """Run the FastAPI backend in-process on a background thread."""
    config = uvicorn.Config(
        "backend.main:app",
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        log_level="warning",
    )
    server = uvicorn.Server(config)

    thread = threading.Thread(
        target=server.run,
        daemon=True,
    )
    thread.start()

    return server, thread


def stop_backend(server: uvicorn.Server, thread: threading.Thread) -> None:
    """Stop the backend and wait for its thread to finish."""
    server.should_exit = True
    thread.join(timeout=5)


def main():
    server, thread = start_backend()

    try:
        if not wait_for_backend():
            print("Backend failed to start.")
            return 1


        run()
        return 0

    finally:
        stop_backend(server, thread)


if __name__ == "__main__":
    sys.exit(main())