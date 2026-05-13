"""nyxus_toast — shared toast helper for every NYXUS GTK4 app.

Every app currently rolls its own Adw.ToastOverlay + Adw.Toast wiring.
This module provides one consistent helper so timings, accent colour
glow, action-button styling and log-on-fallback behaviour are
identical app-to-app. Drop-in:

    from nyxus_toast import attach_toaster, toast

    overlay = attach_toaster(window)        # wraps existing content
    toast(window, "Saved",   tone="ok")
    toast(window, "Failed",  tone="danger", action=("Retry", on_retry))

Tones map to subtle CSS classes: "ok" / "warn" / "danger" / "info"
(default). Falls back to plain `print()` and the python `logging`
module when GTK is unavailable (CLI / headless contexts).
"""
from __future__ import annotations

import logging
from typing import Callable, Optional, Tuple

log = logging.getLogger("nyxus_toast")

try:
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw, Gtk  # type: ignore
    HAS_GTK = True
except Exception:
    HAS_GTK = False


# Default toast lifetime in seconds. Mirrors macOS notification timing.
_DEFAULT_TIMEOUT = {
    "ok":     3,
    "warn":   5,
    "danger": 6,
    "info":   3,
}

# CSS the consuming app should install once. Provided as a string so
# apps can fold it into their existing CssProvider pipeline.
TOAST_CSS = """
.nyx-toast-ok     toastbox { box-shadow: inset 3px 0 0 0 #5ff3b8; }
.nyx-toast-warn   toastbox { box-shadow: inset 3px 0 0 0 #f5b342; }
.nyx-toast-danger toastbox { box-shadow: inset 3px 0 0 0 #ff6464; }
.nyx-toast-info   toastbox { box-shadow: inset 3px 0 0 0 #d4b87a; }
"""


def attach_toaster(window) -> Optional[object]:
    """Wrap `window`'s current content in an Adw.ToastOverlay and store
    the overlay on `window._nyx_toast_overlay`. Idempotent — safe to
    call more than once. Returns the overlay (or None if GTK absent).
    """
    if not HAS_GTK or window is None:
        return None
    existing = getattr(window, "_nyx_toast_overlay", None)
    if existing is not None:
        return existing
    try:
        content = window.get_content() if hasattr(window, "get_content") \
            else window.get_child()
        overlay = Adw.ToastOverlay()
        if content is not None:
            # Detach without unparenting twice
            try:
                if hasattr(window, "set_content"):
                    window.set_content(None)
                else:
                    window.set_child(None)
            except Exception:
                pass
            overlay.set_child(content)
        if hasattr(window, "set_content"):
            window.set_content(overlay)
        else:
            window.set_child(overlay)
        window._nyx_toast_overlay = overlay  # type: ignore[attr-defined]
        return overlay
    except Exception as e:
        log.warning("attach_toaster: %s", e)
        return None


def toast(
    window,
    msg: str,
    *,
    tone: str = "info",
    timeout: Optional[int] = None,
    action: Optional[Tuple[str, Callable[[], None]]] = None,
) -> None:
    """Post a toast on `window`. Falls back to logging if GTK
    unavailable. `action` is an optional (label, callback) pair."""
    if not HAS_GTK or window is None:
        log.info("[%s] %s", tone, msg)
        return
    overlay = getattr(window, "_nyx_toast_overlay", None) \
        or attach_toaster(window)
    if overlay is None:
        log.info("[%s] %s", tone, msg)
        return
    try:
        t = Adw.Toast.new(msg)
        t.set_timeout(timeout if timeout is not None
                      else _DEFAULT_TIMEOUT.get(tone, 3))
        cls = f"nyx-toast-{tone if tone in _DEFAULT_TIMEOUT else 'info'}"
        # Adw.Toast supports add_css_class on libadwaita >= 1.4
        try:
            t.add_css_class(cls)
        except Exception:
            pass
        if action is not None:
            label, cb = action
            t.set_button_label(label)
            t.connect("button-clicked", lambda *_: _safe(cb))
        overlay.add_toast(t)
    except Exception as e:
        log.warning("toast: %s | %s", e, msg)


def _safe(fn: Callable[[], None]) -> None:
    try:
        fn()
    except Exception as e:
        log.warning("toast action: %s", e)
