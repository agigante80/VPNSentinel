"""Alert delivery: Telegram plus optional Apprise targets (issue #142).

``notify(title, body_html)`` is the single exit for the server's five alerts. It sends to Telegram
when Telegram is enabled, and, when ``VPN_SENTINEL_APPRISE_URLS`` (or ``..._FILE``) lists targets,
hands the message to ONE daemon worker thread through a bounded queue. Apprise never runs on the
caller's thread: the keepalive handler calls ``notify`` synchronously, and a blackholed target would
otherwise stall it for the Apprise connect and read timeouts.

Invariants worth knowing before changing this file:

* ``apprise`` is imported lazily, on the worker, only after an item is queued. With the variable
  unset nothing is imported and nothing is queued (the base install has no apprise at all).
* Apprise URLs embed tokens. They are never logged: only ``scheme://***`` is. The ``apprise`` logger
  itself prints full URLs (``Unparseable URL <url>`` at ERROR), so the worker raises its level to
  CRITICAL.
* The queue is handed to the worker as an argument, so ``_reset_for_tests`` can abandon a worker
  stuck in a slow sender without it ever touching the next test's queue.
* State is lost on restart (queued, unsent alerts are dropped). Accepted: the thread is a daemon and
  the server has no shutdown hook.
* Never call ``notify`` while holding ``api_routes.client_status_lock``.
"""

from __future__ import annotations

import logging
import queue
import re
import threading
from typing import List, Optional

from .config import read_secret
from .log_utils import log_warn

APPRISE_URLS_VAR = "VPN_SENTINEL_APPRISE_URLS"
APPRISE_QUEUE_MAX = 50
# Per-target socket timeouts handed to Apprise (its defaults are 4 s connect plus 4 s read).
_TARGET_TIMEOUT_SECONDS = 3
_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*$")

_state_lock = threading.Lock()
_queue: Optional["queue.Queue"] = None
_worker: Optional[threading.Thread] = None


def _apprise_targets() -> List[str]:
    """Return the configured Apprise URLs: comma or whitespace separated, blanks dropped.

    Read through ``read_secret`` because the URLs embed tokens, so ``VPN_SENTINEL_APPRISE_URLS_FILE``
    works too. Reads the environment at call time.

    Raises:
        ValueError: from ``read_secret`` for a bad ``_FILE`` setup (names the variable and path only).
    """
    raw = read_secret(APPRISE_URLS_VAR)
    return [part for part in re.split(r"[\s,]+", raw) if part]


def _redact(url: str) -> str:
    """Return ``scheme://***`` for a URL, or ``invalid://***`` when no clean scheme can be told."""
    scheme, sep, _rest = url.partition("://")
    if not sep or not _SCHEME_RE.match(scheme):
        return "invalid://***"
    return f"{scheme}://***"


def _prepare_url(url: str) -> str:
    """Add ``format=text`` and per-target timeouts to a URL that does not set them itself.

    ``format=text`` makes targets such as ``json://`` forward plain text instead of raw ``<b>``
    markup; a target that sets ``format`` keeps its own. ``cto`` and ``rto`` bound a dead target.
    """
    base, _q, query = url.partition("?")
    present = {pair.split("=", 1)[0].lower() for pair in query.split("&") if pair}
    extra = [
        f"{key}={value}"
        for key, value in (
            ("format", "text"),
            ("cto", _TARGET_TIMEOUT_SECONDS),
            ("rto", _TARGET_TIMEOUT_SECONDS),
        )
        if key not in present
    ]
    if not extra:
        return url
    return f"{base}?{query + '&' if query else ''}{'&'.join(extra)}"


def _apprise_send(targets: List[str], title: str, body_html: str):
    """Send one message to every target. Runs on the worker thread only.

    Returns the ``AppriseResult`` (2.x API: ``.status`` is SUCCESS, FAILURE, TIMEOUT, PARTIAL or
    NOMATCH), or None when no target could even be parsed (each is warned about, redacted).
    """
    import apprise

    sender = apprise.Apprise()
    for url in targets:
        if not sender.add(_prepare_url(url)):
            log_warn("notify", f"apprise target rejected: {_redact(url)}")
    if len(sender) == 0:
        return None
    return sender.notify(title=title, body=body_html, body_format=apprise.NotifyFormat.HTML)


def _deliver(targets: List[str], title: str, body_html: str) -> None:
    result = _apprise_send(targets, title, body_html)
    if result is None:
        return
    status = getattr(result.status, "name", str(result.status))
    if status != "SUCCESS":
        schemes = ", ".join(_redact(url) for url in targets)
        log_warn("notify", f"apprise delivery {status} for {schemes}")


def _worker_loop(work: "queue.Queue") -> None:
    missing_warned = False
    while True:
        item = work.get()
        try:
            if item is None:
                return
            if missing_warned:
                continue
            targets, title, body = item
            try:
                import apprise  # noqa: F401  # lazy: only the worker ever imports it
            except ImportError:
                missing_warned = True
                log_warn("notify", "apprise not installed (pip install '.[notify]'); Apprise targets are ignored")
                continue
            # The apprise logger prints full URLs, tokens included, even at ERROR.
            logging.getLogger("apprise").setLevel(logging.CRITICAL)
            _deliver(targets, title, body)
        except Exception as e:  # noqa: BLE001  # one bad item must never kill the worker
            log_warn("notify", f"apprise delivery failed: {type(e).__name__}")
        finally:
            work.task_done()


def _enqueue(targets: List[str], title: str, body_html: str) -> None:
    global _queue, _worker
    with _state_lock:
        if _queue is None:
            _queue = queue.Queue(maxsize=APPRISE_QUEUE_MAX)
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_worker_loop, args=(_queue,), name="notifications-worker", daemon=True)
            _worker.start()
        work = _queue
    try:
        work.put_nowait((targets, title, body_html))
    except queue.Full:
        log_warn("notify", "apprise queue full, alert not sent to Apprise targets")


def notify(title: str, body_html: str) -> bool:
    """Deliver one alert to Telegram (when enabled) and to the Apprise targets (when configured).

    Never raises. Returns the Telegram send result: False when Telegram is disabled or failed.
    """
    from . import telegram  # lazy: telegram imports this module's callers, avoid a cycle

    try:
        targets = _apprise_targets()
    except ValueError as e:
        log_warn("notify", f"Apprise targets ignored: {e}")
        targets = []
    if targets:
        try:
            _enqueue(targets, title, body_html)
        except Exception as e:  # noqa: BLE001  # Apprise trouble must not stop Telegram
            log_warn("notify", f"apprise enqueue failed: {type(e).__name__}")
    if telegram.TELEGRAM_ENABLED:
        return telegram.send_telegram_message(body_html)
    return False


def flush(timeout: float = 5.0) -> bool:
    """Wait until every queued Apprise item has been processed. True when drained, False on timeout.

    Test seam: waits on ``queue.join()`` in a daemon helper thread so a stuck sender cannot hang
    the caller (or the interpreter at exit) past ``timeout``.
    """
    with _state_lock:
        work = _queue
    if work is None:
        return True
    done = threading.Event()

    def _wait() -> None:
        work.join()
        done.set()

    threading.Thread(target=_wait, name="notifications-flush", daemon=True).start()
    return done.wait(timeout)


def _reset_for_tests() -> None:
    """Stop the worker and forget the queue. Never blocks on a full queue or a stuck sender.

    The queue is drained (not put to), a stop sentinel is added with ``put_nowait``, and the join is
    bounded. A worker stuck inside a sender is abandoned: it is a daemon holding only its own old
    queue, so it cannot affect the next test.
    """
    global _queue, _worker
    with _state_lock:
        work, thread = _queue, _worker
        _queue = None
        _worker = None
    if work is None:
        return
    while True:
        try:
            work.get_nowait()
        except queue.Empty:
            break
        work.task_done()
    try:
        work.put_nowait(None)
    except queue.Full:
        pass
    if thread is not None:
        thread.join(timeout=2.0)
