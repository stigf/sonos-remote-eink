# ui/tab_queue.py — Queue tab: Favourites (left) | Queue (right)
#
# Layout (content area 250×106):
#
#   |← 95 px →|1px|← 154 px →|
#   | Favourites   | Queue        |
#   | ─────────────|──────────────|
#   | fav item 1   | queue item 1 |  ← each row 15px tall → ~7 rows visible
#   | fav item 2   | > item 2 ←current
#   | ...          | ...          |

from PIL import Image, ImageDraw

import config
from ui import fonts, widgets
from state import AppState

# Exported for hit-testing (populated in _build_regions)
REGIONS = {}   # 'fav_N' and 'queue_N' → (x0, y0, x1, y1) for visible rows

_FAV_X   = 0
_QUEUE_X = config.FAV_PANE_W + 1   # +1 for divider
_ROW_H   = config.LIST_ROW_H


def render(snap: AppState) -> Image.Image:
    img  = Image.new('1', (config.DISPLAY_W, config.DISPLAY_H), config.WHITE)
    draw = ImageDraw.Draw(img)

    _draw_content(draw, snap)
    widgets.draw_tab_bar(draw, snap.active_tab)
    _build_regions(snap)

    return img


def _draw_content(draw: ImageDraw, snap: AppState) -> None:
    # Vertical divider
    divx = config.FAV_PANE_W
    draw.line([divx, 0, divx, config.CONTENT_H - 1], fill=config.BLACK)

    _draw_header(draw, 'Favs', _FAV_X, config.FAV_PANE_W)
    _draw_header(draw, 'Queue', _QUEUE_X, config.QUEUE_PANE_W)

    header_h = _ROW_H
    visible  = (config.CONTENT_H - header_h) // _ROW_H

    # ---- Favourites ----
    favs = snap.favourites
    scroll_f = max(0, min(snap.fav_scroll, max(0, len(favs) - visible)))
    for i in range(visible):
        idx = i + scroll_f
        y = header_h + i * _ROW_H
        if idx < len(favs):
            widgets.draw_list_row(
                draw, _FAV_X, y, config.FAV_PANE_W, _ROW_H,
                favs[idx].title, font=fonts.SMALL
            )

    # ---- Queue ----
    queue = snap.queue
    scroll_q = max(0, min(snap.queue_scroll, max(0, len(queue) - visible)))
    cur_pos  = snap.queue_position
    for i in range(visible):
        idx = i + scroll_q
        y = header_h + i * _ROW_H
        if idx < len(queue):
            item = queue[idx]
            is_current = (item.index == cur_pos)
            prefix = '>' if is_current else ' '
            font   = fonts.BOLD if is_current else fonts.SMALL
            widgets.draw_list_row(
                draw, _QUEUE_X, y, config.QUEUE_PANE_W, _ROW_H,
                item.title, font=font, prefix=prefix,
                inverted=is_current
            )

    # Scroll indicators
    _draw_scroll_hints(draw, scroll_f, len(favs), visible,
                       _FAV_X, config.FAV_PANE_W, header_h)
    _draw_scroll_hints(draw, scroll_q, len(queue), visible,
                       _QUEUE_X, config.QUEUE_PANE_W, header_h)


def _draw_header(draw, label, x, w):
    draw.rectangle([x, 0, x + w - 1, _ROW_H - 1], fill=config.BLACK)
    tw = widgets._text_w(label, fonts.BOLD)
    th = widgets._text_h(fonts.BOLD)
    tx = x + (w - tw) // 2
    ty = (_ROW_H - th) // 2
    draw.text((tx, ty), label, font=fonts.BOLD, fill=config.WHITE)


def _draw_scroll_hints(draw, scroll, total, visible, x, w, header_h):
    """Draw tiny up/down arrows if the list can scroll."""
    if total <= visible:
        return
    if scroll > 0:
        # Up arrow at top-right of pane
        ax = x + w - 8
        ay = header_h + 1
        draw.polygon([(ax, ay + 4), (ax + 4, ay + 4), (ax + 2, ay)], fill=config.BLACK)
    if scroll + visible < total:
        # Down arrow at bottom-right
        bottom_y = config.CONTENT_H - 5
        ax = x + w - 8
        draw.polygon([(ax, bottom_y), (ax + 4, bottom_y), (ax + 2, bottom_y + 4)],
                     fill=config.BLACK)


def _build_regions(snap: AppState) -> None:
    """Update REGIONS dict with hit rects for all visible rows."""
    REGIONS.clear()
    header_h = _ROW_H
    visible  = (config.CONTENT_H - header_h) // _ROW_H
    scroll_f = max(0, min(snap.fav_scroll, max(0, len(snap.favourites) - visible)))
    scroll_q = max(0, min(snap.queue_scroll, max(0, len(snap.queue) - visible)))

    for i in range(visible):
        y0 = header_h + i * _ROW_H
        y1 = y0 + _ROW_H - 1
        fav_idx = i + scroll_f
        if fav_idx < len(snap.favourites):
            REGIONS[f'fav_{fav_idx}'] = (_FAV_X, y0, config.FAV_PANE_W - 1, y1)
        q_idx = i + scroll_q
        if q_idx < len(snap.queue):
            REGIONS[f'queue_{q_idx}'] = (_QUEUE_X, y0,
                                          config.DISPLAY_W - 1, y1)

    # Scroll zones (bottom strip of each pane)
    bottom = config.CONTENT_H
    REGIONS['scroll_fav_down']   = (_FAV_X,   bottom - 14, config.FAV_PANE_W - 1, bottom - 1)
    REGIONS['scroll_fav_up']     = (_FAV_X,   header_h,    config.FAV_PANE_W - 1, header_h + 13)
    REGIONS['scroll_queue_down'] = (_QUEUE_X, bottom - 14, config.DISPLAY_W - 1,  bottom - 1)
    REGIONS['scroll_queue_up']   = (_QUEUE_X, header_h,    config.DISPLAY_W - 1,  header_h + 13)
