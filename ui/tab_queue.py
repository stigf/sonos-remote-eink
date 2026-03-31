# ui/tab_queue.py — Queue tab: Favourites (left) | Queue (right)
#
# Layout (250×122 canvas, tab bar overlaid at bottom):
#
#   |← 115 px →|1px|← 134 px →|
#   | fav item 1   | queue item 1 |  ← each row 15px tall, 7 rows visible
#   | fav item 2   | ▌item 2      |  ← current track inverted
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
    draw.fontmode = "1"

    _draw_content(draw, snap)
    widgets.draw_tab_bar(draw, snap.active_tab)
    _build_regions(snap)

    return img


def _draw_content(draw: ImageDraw, snap: AppState) -> None:
    # Vertical divider
    divx = config.FAV_PANE_W
    draw.line([divx, 0, divx, config.CONTENT_H - 1], fill=config.BLACK)

    visible = config.VISIBLE_ROWS

    # ---- Favourites ----
    favs = snap.favourites
    scroll_f = max(0, min(snap.fav_scroll, max(0, len(favs) - visible)))
    fav_scrollable = len(favs) > visible
    # Reserve width for scroll arrows when list is scrollable
    fav_text_w = config.FAV_PANE_W - widgets.SCROLL_W if fav_scrollable else config.FAV_PANE_W

    for i in range(visible):
        idx = i + scroll_f
        y = i * _ROW_H
        if idx < len(favs):
            widgets.draw_list_row(
                draw, _FAV_X, y, fav_text_w, _ROW_H,
                favs[idx].title, font=fonts.SMALL
            )

    # ---- Queue ----
    queue = snap.queue
    scroll_q = max(0, min(snap.queue_scroll, max(0, len(queue) - visible)))
    cur_pos  = snap.queue_position
    queue_scrollable = len(queue) > visible
    queue_text_w = config.QUEUE_PANE_W - widgets.SCROLL_W if queue_scrollable else config.QUEUE_PANE_W

    for i in range(visible):
        idx = i + scroll_q
        y = i * _ROW_H
        if idx < len(queue):
            item = queue[idx]
            is_current = (item.index == cur_pos)
            font = fonts.BOLD if is_current else fonts.SMALL
            widgets.draw_list_row(
                draw, _QUEUE_X, y, queue_text_w, _ROW_H,
                item.title, font=font,
                inverted=is_current
            )

    # Scroll arrows
    list_top = 0
    list_bottom = visible * _ROW_H

    if fav_scrollable:
        widgets.draw_scroll_arrows(
            draw, _FAV_X, list_top, list_bottom, config.FAV_PANE_W,
            can_up=(scroll_f > 0),
            can_down=(scroll_f + visible < len(favs)))

    if queue_scrollable:
        widgets.draw_scroll_arrows(
            draw, _QUEUE_X, list_top, list_bottom, config.QUEUE_PANE_W,
            can_up=(scroll_q > 0),
            can_down=(scroll_q + visible < len(queue)))



def _build_regions(snap: AppState) -> None:
    """Update REGIONS dict with hit rects for all visible rows."""
    REGIONS.clear()
    visible = config.VISIBLE_ROWS
    scroll_f = max(0, min(snap.fav_scroll, max(0, len(snap.favourites) - visible)))
    scroll_q = max(0, min(snap.queue_scroll, max(0, len(snap.queue) - visible)))

    fav_scrollable = len(snap.favourites) > visible
    queue_scrollable = len(snap.queue) > visible

    # Row width for hit regions (narrower when scrollable, so arrows get their own zone)
    fav_hit_w = config.FAV_PANE_W - widgets.SCROLL_W if fav_scrollable else config.FAV_PANE_W
    queue_hit_r = config.DISPLAY_W - widgets.SCROLL_W if queue_scrollable else config.DISPLAY_W

    for i in range(visible):
        y0 = i * _ROW_H
        y1 = y0 + _ROW_H - 1
        fav_idx = i + scroll_f
        if fav_idx < len(snap.favourites):
            REGIONS[f'fav_{fav_idx}'] = (_FAV_X, y0, fav_hit_w - 1, y1)
        q_idx = i + scroll_q
        if q_idx < len(snap.queue):
            REGIONS[f'queue_{q_idx}'] = (_QUEUE_X, y0, queue_hit_r - 1, y1)

    # Scroll arrow hit regions (non-overlapping with rows)
    list_top = 0
    list_bottom = visible * _ROW_H

    if fav_scrollable:
        up, down = widgets.scroll_hit_regions(
            _FAV_X, list_top, list_bottom, config.FAV_PANE_W)
        if scroll_f > 0:
            REGIONS['scroll_fav_up'] = up
        if scroll_f + visible < len(snap.favourites):
            REGIONS['scroll_fav_down'] = down

    if queue_scrollable:
        up, down = widgets.scroll_hit_regions(
            _QUEUE_X, list_top, list_bottom, config.QUEUE_PANE_W)
        if scroll_q > 0:
            REGIONS['scroll_queue_up'] = up
        if scroll_q + visible < len(snap.queue):
            REGIONS['scroll_queue_down'] = down
