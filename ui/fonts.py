# ui/fonts.py — Font loading (loaded once at import time)

import logging
import os
from PIL import ImageFont

logger = logging.getLogger(__name__)

_SEARCH_PATHS = [
    # Bundled fonts (place TTFs in assets/fonts/ alongside this project)
    os.path.join(os.path.dirname(__file__), '..', 'assets', 'fonts'),
    # Raspberry Pi OS / Debian system fonts
    '/usr/share/fonts/truetype/dejavu',
    '/usr/share/fonts/truetype/freefont',
    '/usr/share/fonts/truetype/liberation',
    # macOS user fonts
    os.path.expanduser('~/Library/Fonts'),
]

_FONT_FILES = {
    'regular': ['DejaVuSans.ttf', 'FreeSans.ttf', 'LiberationSans-Regular.ttf'],
    'bold':    ['DejaVuSans-Bold.ttf', 'FreeSansBold.ttf', 'LiberationSans-Bold.ttf'],
}


def _find_font(style: str) -> str:
    for directory in _SEARCH_PATHS:
        directory = os.path.abspath(directory)
        for filename in _FONT_FILES[style]:
            path = os.path.join(directory, filename)
            if os.path.isfile(path):
                return path
    return None


def _load(style: str, size: int) -> ImageFont.FreeTypeFont:
    path = _find_font(style)
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception as exc:
            logger.warning('Could not load font %s at size %d: %s', path, size, exc)
    # Fallback to PIL default bitmap font
    logger.warning('Using default PIL bitmap font (quality will be poor)')
    return ImageFont.load_default()


# Pre-loaded font instances
TINY    = _load('regular', 8)
SMALL   = _load('regular', 9)
REGULAR = _load('regular', 10)
BOLD    = _load('bold',    11)
TITLE   = _load('bold',    13)
TAB     = _load('regular',  9)
