# ui/tab_speakers.py — Speaker selection & grouping tab
#
# Layout (content area 250×106):
#   Each speaker row: 26px tall
#   Row: [indicator] Name (truncated)   VOL: ████░  NN
#
#   4 rows visible (4×26 = 104px, leaving 2px at bottom)
#   Active coordinator shown with inverted row.
#
#   Indicators:
#     ■  coordinator (this is the active/master speaker)
#     ●  grouped (member of coordinator's group)
#     ○  ungrouped (standalone, tap to add to group)
#
#   Tap a non-coordinator speaker to toggle its group membership.

from PIL import Image, ImageDraw

import config
from ui import fonts, widgets
from state import AppState

# Exported hit regions: 'speaker_<uid>' → (x0, y0, x1, y1)
REGIONS = {}

_ROW_H    = 26
_VISIBLE  = config.CONTENT_H // _ROW_H   # 4
_VOL_W    = 50   # width of volume bar
_VOL_X    = config.DISPLAY_W - _VOL_W - 22  # leave room for vol number
_NUM_X    = config.DISPLAY_W - 20


def render(snap: AppState) -> Image.Image:
    img  = Image.new('1', (config.DISPLAY_W, config.DISPLAY_H), config.WHITE)
    draw = ImageDraw.Draw(img)

    _draw_content(draw, snap)
    widgets.draw_tab_bar(draw, snap.active_tab)
    _build_regions(snap)

    return img


def _draw_content(draw: ImageDraw, snap: AppState) -> None:
    speakers = snap.speakers

    if not speakers:
        msg = 'Searching for speakers...'
        mw = widgets._text_w(msg, fonts.REGULAR)
        mh = widgets._text_h(fonts.REGULAR)
        draw.text(
            ((config.DISPLAY_W - mw) // 2, (config.CONTENT_H - mh) // 2),
            msg, font=fonts.REGULAR, fill=config.BLACK
        )
        return

    for i in range(min(_VISIBLE, len(speakers))):
        sp  = speakers[i]
        y0  = i * _ROW_H
        y1  = y0 + _ROW_H - 1
        is_coord = sp.is_coordinator

        # Row background
        if is_coord:
            draw.rectangle([0, y0, config.DISPLAY_W - 1, y1], fill=config.BLACK)
        else:
            draw.rectangle([0, y0, config.DISPLAY_W - 1, y1], fill=config.WHITE)
            draw.line([0, y1, config.DISPLAY_W - 1, y1], fill=config.BLACK)

        fg = config.WHITE if is_coord else config.BLACK

        # Group indicator
        if is_coord:
            bullet = '\u25a0'   # ■ filled square — coordinator
        elif sp.is_grouped:
            bullet = '\u25cf'   # ● filled circle — grouped
        else:
            bullet = '\u25cb'   # ○ empty circle — ungrouped

        draw.text((3, y0 + (_ROW_H - widgets._text_h(fonts.BOLD)) // 2),
                  bullet, font=fonts.BOLD, fill=fg)

        # Speaker name
        name_w = _VOL_X - 16
        name   = widgets.truncate(sp.name, fonts.REGULAR, name_w)
        draw.text((16, y0 + (_ROW_H - widgets._text_h(fonts.REGULAR)) // 2),
                  name, font=fonts.REGULAR, fill=fg)

        # Volume bar
        bar_fill  = config.WHITE if is_coord else config.BLACK
        bar_bg    = config.BLACK if is_coord else config.WHITE
        bar_out   = config.WHITE if is_coord else config.BLACK
        bar_y     = y0 + (_ROW_H - 6) // 2
        draw.rectangle([_VOL_X, bar_y, _VOL_X + _VOL_W - 1, bar_y + 5],
                       outline=bar_out, fill=bar_bg)
        filled = int(_VOL_W * sp.volume / 100)
        if filled > 0:
            draw.rectangle([_VOL_X + 1, bar_y + 1,
                            _VOL_X + filled - 1, bar_y + 4], fill=bar_fill)

        # Volume number
        vol_str = str(sp.volume)
        vw = widgets._text_w(vol_str, fonts.TINY)
        draw.text((_NUM_X + (20 - vw) // 2,
                   y0 + (_ROW_H - widgets._text_h(fonts.TINY)) // 2),
                  vol_str, font=fonts.TINY, fill=fg)


def _build_regions(snap: AppState) -> None:
    REGIONS.clear()
    for i in range(min(_VISIBLE, len(snap.speakers))):
        sp  = snap.speakers[i]
        y0  = i * _ROW_H
        y1  = y0 + _ROW_H - 1
        REGIONS[f'speaker_{sp.uid}'] = (0, y0, config.DISPLAY_W - 1, y1)
