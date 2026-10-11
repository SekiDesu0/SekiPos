import threading
import time

VALID_PAGES = {'inventory', 'checkout', 'sales', 'gastos', 'dicom'}

STALE_SECONDS = 600

_pages = {}
_lock = threading.Lock()


def announce(sid, page, now=None):
    if not sid or page not in VALID_PAGES:
        return False
    with _lock:
        _pages[sid] = {"page": page, "seen": time.time()}
    return True


def _purge_locked():
    cutoff = time.time() - STALE_SECONDS
    for k in [k for k, v in _pages.items() if v["seen"] < cutoff]:
        del _pages[k]


def current_page(sid=None):
    with _lock:
        _purge_locked()
        if sid and sid in _pages:
            return _pages[sid]["page"]
        if _pages:
            return max(_pages.values(), key=lambda v: v["seen"])["page"]
        return None
