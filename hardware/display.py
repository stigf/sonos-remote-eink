# hardware/display.py — Waveshare Touch e-Paper HAT display driver wrapper
#
# The display is physically 122×250 (portrait). We always work in landscape
# (250×122). The Waveshare getbuffer() handles the coordinate rotation when
# you pass an image whose dimensions are (epd.height, epd.width) = (250, 122).

import sys
import logging

import config

logger = logging.getLogger(__name__)


def _load_waveshare_module():
    sys.path.insert(0, config.WAVESHARE_LIB_PATH)
    try:
        import epd2in13_V2
        return epd2in13_V2
    except ImportError:
        logger.warning('Waveshare library not found at %s', config.WAVESHARE_LIB_PATH)
        return None


class DisplayDriver:
    """
    Wraps the Waveshare EPD driver.

    Refresh modes
    -------------
    push_full  — full waveform, clears all ghosting, ~2 s, flashes white
    push_fast  — fast waveform, slight ghosting risk, ~0.3 s, minor flash
    push_partial — partial update (changed pixels only), ~0.3 s, no flash
                   requires a prior push_full or push_fast as the base image

    After FULL_REFRESH_EVERY fast/partial cycles a full refresh is forced
    automatically to prevent ghosting accumulation.
    """

    def __init__(self):
        self._mod = _load_waveshare_module()
        self._simulation = self._mod is None
        self._epd = None
        self._cycle_count = 0
        self._base_image = None   # last image sent to display (for partial)
        self._in_fast_mode = False

        if self._simulation:
            self.width  = config.DISPLAY_W
            self.height = config.DISPLAY_H
        else:
            self._epd = self._mod.EPD()
            # Landscape: PIL image is (epd.height × epd.width) = (250 × 122)
            self.width  = self._epd.height   # 250
            self.height = self._epd.width    # 122

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def init(self):
        """Full initialisation. Call once at startup and after sleep."""
        if self._simulation:
            return
        self._epd.init()
        self._epd.Clear()
        self._cycle_count = 0
        self._in_fast_mode = False
        logger.debug('EPD init complete')

    def sleep(self):
        if not self._simulation:
            self._epd.sleep()
        logger.debug('EPD sleeping')

    def wake(self):
        """Re-initialise after sleep. Returns display to known state."""
        self._cycle_count = 0
        self._in_fast_mode = False
        if not self._simulation:
            self._epd.init()

    # ------------------------------------------------------------------
    # Refresh methods
    # ------------------------------------------------------------------

    def push_full(self, image):
        """Full waveform refresh. Use on tab switches and after sleep."""
        if self._simulation:
            self._save_preview(image)
            return
        if self._in_fast_mode:
            self._epd.init()
            self._in_fast_mode = False
        self._epd.display(self._epd.getbuffer(image))
        self._base_image = image.copy()
        self._cycle_count = 0
        logger.debug('Full refresh')

    def push_fast(self, image):
        """
        Fast refresh. ~0.3 s, minimal flash. Use for in-tab content updates.
        Automatically falls back to push_full after FULL_REFRESH_EVERY cycles.
        """
        if self._cycle_count >= config.FULL_REFRESH_EVERY:
            self.push_full(image)
            return

        if self._simulation:
            self._save_preview(image)
            self._cycle_count += 1
            return

        if not self._in_fast_mode:
            try:
                self._epd.init_Fast()
                self._in_fast_mode = True
            except AttributeError:
                # Fallback: driver doesn't have init_Fast
                self._epd.init()
                self._in_fast_mode = False

        self._epd.display(self._epd.getbuffer(image))
        self._base_image = image.copy()
        self._cycle_count += 1
        logger.debug('Fast refresh (cycle %d)', self._cycle_count)

    def push_partial(self, image):
        """
        Partial refresh — only changed pixels are updated.
        Requires a previous full/fast push to have established the base image.
        Falls back to push_fast if no base is available.
        """
        if self._base_image is None:
            self.push_fast(image)
            return

        if self._cycle_count >= config.FULL_REFRESH_EVERY:
            self.push_full(image)
            return

        if self._simulation:
            self._save_preview(image)
            self._cycle_count += 1
            return

        try:
            if self._in_fast_mode:
                # Must re-init for partial mode
                self._epd.init()
                self._in_fast_mode = False
            self._epd.displayPartBaseImage(self._epd.getbuffer(self._base_image))
            self._epd.displayPartial(self._epd.getbuffer(image))
            self._base_image = image.copy()
            self._cycle_count += 1
            logger.debug('Partial refresh (cycle %d)', self._cycle_count)
        except AttributeError:
            self.push_fast(image)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _save_preview(self, image):
        try:
            image.save('/tmp/epd_preview.png')
        except Exception:
            pass
