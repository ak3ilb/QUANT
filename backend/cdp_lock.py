"""Global CDP request lock to prevent concurrent TradingView chart mutations."""
import os
import time
import random

LOCK_PATH = "/tmp/cdp_request.lock"
LOCK_STALE_SECONDS = 120


def _is_stale():
    if not os.path.exists(LOCK_PATH):
        return True
    try:
        return (time.time() - os.path.getmtime(LOCK_PATH)) > LOCK_STALE_SECONDS
    except OSError:
        return True


def acquire(timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _is_stale():
            try:
                with open(LOCK_PATH, "x") as f:
                    f.write(str(os.getpid()))
                return True
            except FileExistsError:
                pass
        time.sleep(0.25 + random.uniform(0, 0.25))
    return False


def release():
    try:
        if os.path.exists(LOCK_PATH):
            os.remove(LOCK_PATH)
    except OSError:
        pass


def jittered_settle_ms(low=2000, high=4000):
    return random.randint(low, high)


class cdp_lock:
    def __enter__(self):
        if not acquire():
            raise TimeoutError("Could not acquire CDP request lock")
        return self

    def __exit__(self, exc_type, exc, tb):
        release()
