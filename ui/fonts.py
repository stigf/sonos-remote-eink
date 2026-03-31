# ui/fonts.py — Font loading (loaded once at import time)

import logging
import os
from PIL import ImageFont

logger = logging.getLogger(__name__)

_ASSETS_FONTS = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'assets', 'fonts'))

_FALLBACK_PATHS = [
    # Raspberry Pi OS / Debian system fonts
    '/usr/share/fonts/truetype/dejavu',
    '/usr/share/fonts/truetype/freefont',
    '/usr/share/fonts/truetype/liberation',
    # macOS user fonts
    os.path.expanduser('~/Library/Fonts'),
]

_FALLBACK_FILES = {
    'regular': ['DejaVuSans.ttf', 'FreeSans.ttf', 'LiberationSans-Regular.ttf'],
    'bold':    ['DejaVuSans-Bold.ttf', 'FreeSansBold.ttf', 'LiberationSans-Bold.ttf'],
}


def _find_fallback(style: str) -> str | None:
    """Search system paths for a fallback font."""
    for directory in _FALLBACK_PATHS:
        for filename in _FALLBACK_FILES[style]:
            path = os.path.join(directory, filename)
            if os.path.isfile(path):
                return path
    return None


def _load(galmuri_file: str, galmuri_size: int,
          fallback_style: str, fallback_size: int) -> ImageFont.FreeTypeFont:
    """Load a Galmuri font, falling back to a system font if unavailable."""
    # Try Galmuri first (pixel-perfect at its native size on 1-bit displays)
    galmuri_path = os.path.join(_ASSETS_FONTS, galmuri_file)
    if os.path.isfile(galmuri_path):
        try:
            font = ImageFont.truetype(galmuri_path, galmuri_size)
            logger.debug('Loaded %s at %dpx', galmuri_file, galmuri_size)
            return font
        except Exception as exc:
            logger.warning('Could not load %s at %dpx: %s',
                           galmuri_file, galmuri_size, exc)

    # Fall back to system font (DejaVuSans / FreeSans / Liberation)
    fallback_path = _find_fallback(fallback_style)
    if fallback_path:
        try:
            font = ImageFont.truetype(fallback_path, fallback_size)
            logger.info('Galmuri not found, using fallback %s at %dpx',
                        os.path.basename(fallback_path), fallback_size)
            return font
        except Exception as exc:
            logger.warning('Could not load fallback %s: %s', fallback_path, exc)

    logger.warning('No fonts found — using PIL default bitmap font')
    return ImageFont.load_default()


# ── Pre-loaded font instances ────────────────────────────────────────────
#
# Galmuri is a proportional pixel font that renders pixel-perfectly at its
# native sizes on 1-bit displays (no antialiasing artifacts).  Each variant
# is designed for a specific pixel height:
#
#   Galmuri7  →  8px    Galmuri9  → 10px    Galmuri11 → 12px
#   Galmuri14 → 15px    Galmuri11-Bold → 12px
#
# The fallback sizes match the original DejaVuSans sizes used before the
# Galmuri migration, so the layout stays roughly the same either way.
#
#                       Galmuri file        px   Fallback style  px
TINY       = _load('Galmuri7.ttf',        8,  'regular',       8)
SMALL      = _load('Galmuri9.ttf',       10,  'regular',       9)
REGULAR    = SMALL   # same font; separate name for semantic clarity
BOLD       = _load('Galmuri11-Bold.ttf', 12,  'bold',         11)
TITLE      = _load('Galmuri11-Bold.ttf', 12,  'bold',         13)
IDLE_TITLE = _load('Galmuri14.ttf',      15,  'bold',         15)
TAB        = _load('Galmuri7.ttf',        8,  'regular',       9)
