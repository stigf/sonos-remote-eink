# ui/renderer.py — Orchestrates rendering and decides refresh mode
#
# The renderer keeps a hash of the last pushed image.  If the new image
# is identical, the push is skipped entirely to avoid unnecessary flicker.

import logging
import threading
import zlib

import config
from ui import tab_now_playing, tab_queue, tab_speakers, tab_wifi, keyboard
from state import AppState

logger = logging.getLogger(__name__)

_TAB_RENDERERS = [
    tab_now_playing.render,
    tab_queue.render,
    tab_speakers.render,
    tab_wifi.render,
]


class Renderer:
    def __init__(self, store, display_driver):
        self._store   = store
        self._display = display_driver
        self._dirty   = threading.Event()
        self._dirty.set()   # draw immediately on first call
        self._last_hash  = None
        self._last_tab   = -1

    # ------------------------------------------------------------------
    # Called from EventBus callbacks (may run in any thread)
    # ------------------------------------------------------------------

    def mark_dirty(self, _payload=None):
        self._dirty.set()

    # ------------------------------------------------------------------
    # Called from the main loop
    # ------------------------------------------------------------------

    def render_if_dirty(self) -> bool:
        """
        If dirty, render and push to display.
        Returns True if a push happened.
        """
        if not self._dirty.is_set():
            return False

        snap = self._store.get_snapshot()
        self._dirty.clear()

        if snap.keyboard_active:
            img = keyboard.render(snap)
        else:
            img = _TAB_RENDERERS[snap.active_tab](snap)

        # Skip if image unchanged
        img_hash = _image_hash(img)
        if img_hash == self._last_hash:
            return False

        tab_changed = (snap.active_tab != self._last_tab)
        needs_full  = snap.needs_full_refresh or tab_changed

        if needs_full:
            self._display.push_full(img)
            if snap.needs_full_refresh:
                self._store.update(lambda s: setattr(s, 'needs_full_refresh', False))
        else:
            self._display.push_fast(img)

        self._last_hash = img_hash
        self._last_tab  = snap.active_tab

        logger.debug('Rendered tab %d (%s refresh)',
                     snap.active_tab, 'full' if needs_full else 'fast')
        return True


def _image_hash(img) -> int:
    """Fast CRC32 of image bytes — sufficient for change detection."""
    return zlib.crc32(img.tobytes())
