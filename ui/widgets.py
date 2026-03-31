# ui/widgets.py — Reusable drawing primitives

import config
from ui import fonts
from PIL import ImageDraw


# ------------------------------------------------------------------
# Text utilities
# ------------------------------------------------------------------

def truncate(text: str, font, max_px: int) -> str:
    """Truncate text with ellipsis to fit within max_px width."""
    if not text:
        return ''
    if _text_w(text, font) <= max_px:
        return text
    ellipsis = '...'
    ew = _text_w(ellipsis, font)
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _text_w(text[:mid], font) + ew <= max_px:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo] + ellipsis


def _text_w(text: str, font) -> int:
    """Return pixel width of text string."""
    try:
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0]
    except AttributeError:
        # Older Pillow
        w, _ = font.getsize(text)
        return w


def _text_h(font) -> int:
    try:
        bbox = font.getbbox('Ay')
        return bbox[3] - bbox[1]
    except AttributeError:
        _, h = font.getsize('Ay')
        return h


# ------------------------------------------------------------------
# Tab bar
# ------------------------------------------------------------------

def draw_tab_bar(draw: ImageDraw, active_tab: int) -> None:
    """Draw the 16px tab bar at the bottom of the display."""
    y0 = config.CONTENT_H
    y1 = config.DISPLAY_H

    # Background
    draw.rectangle([0, y0, config.DISPLAY_W - 1, y1 - 1], fill=config.WHITE)
    # Top border line
    draw.line([0, y0, config.DISPLAY_W - 1, y0], fill=config.BLACK)

    for i, name in enumerate(config.TAB_NAMES):
        x0 = i * config.TAB_W
        # Last tab gets the remainder to fill full width
        if i == config.TAB_COUNT - 1:
            x1 = config.DISPLAY_W - 1
        else:
            x1 = x0 + config.TAB_W - 1
        tab_w = x1 - x0 + 1
        if i == active_tab:
            draw.rectangle([x0, y0 + 1, x1, y1 - 1], fill=config.BLACK)
            fill = config.WHITE
        else:
            fill = config.BLACK
        # Vertical divider between tabs
        if i > 0:
            draw.line([x0, y0 + 1, x0, y1 - 1], fill=config.BLACK)
        # Tab label centred
        tw = _text_w(name, fonts.TAB)
        th = _text_h(fonts.TAB)
        tx = x0 + (tab_w - tw) // 2
        ty = y0 + (config.TAB_BAR_H - th) // 2
        draw.text((tx, ty), name, font=fonts.TAB, fill=fill)


# ------------------------------------------------------------------
# Progress / volume bar
# ------------------------------------------------------------------

def draw_bar(draw: ImageDraw, x: int, y: int, w: int, h: int,
             fraction: float, border: bool = True) -> None:
    """Horizontal filled bar. fraction in [0, 1]."""
    fraction = max(0.0, min(1.0, fraction))
    if border:
        draw.rectangle([x, y, x + w - 1, y + h - 1],
                       outline=config.BLACK, fill=config.WHITE)
        filled_w = int((w - 2) * fraction)
        if filled_w > 0:
            draw.rectangle([x + 1, y + 1, x + filled_w, y + h - 2],
                           fill=config.BLACK)
    else:
        draw.rectangle([x, y, x + w - 1, y + h - 1], fill=config.WHITE)
        filled_w = int(w * fraction)
        if filled_w > 0:
            draw.rectangle([x, y, x + filled_w - 1, y + h - 1], fill=config.BLACK)


# ------------------------------------------------------------------
# Button
# ------------------------------------------------------------------

def draw_button(draw: ImageDraw, x: int, y: int, w: int, h: int,
                label: str, font=None, inverted: bool = False) -> None:
    """Rectangle button with centred text label."""
    if font is None:
        font = fonts.BOLD
    bg   = config.BLACK if inverted else config.WHITE
    fg   = config.WHITE if inverted else config.BLACK
    draw.rectangle([x, y, x + w - 1, y + h - 1], fill=bg, outline=config.BLACK)
    tw = _text_w(label, font)
    th = _text_h(font)
    tx = x + (w - tw) // 2
    ty = y + (h - th) // 2
    draw.text((tx, ty), label, font=font, fill=fg)


# ------------------------------------------------------------------
# List row
# ------------------------------------------------------------------

def draw_list_row(draw: ImageDraw, x: int, y: int, w: int, h: int,
                  text: str, font=None, prefix: str = '',
                  inverted: bool = False) -> None:
    """Single list item row, optionally inverted (current item)."""
    if font is None:
        font = fonts.REGULAR
    bg = config.BLACK if inverted else config.WHITE
    fg = config.WHITE if inverted else config.BLACK
    draw.rectangle([x, y, x + w - 1, y + h - 1], fill=bg)
    label = truncate(prefix + text, font, w - 4)
    draw.text((x + 2, y + (h - _text_h(font)) // 2), label, font=font, fill=fg)


# ------------------------------------------------------------------
# Scroll indicators
# ------------------------------------------------------------------

# Width reserved at the right edge of scrollable lists for scroll arrows.
# Text truncation should subtract this when the list is scrollable.
SCROLL_W = 13

_ARROW_W = 11   # odd width → triangle centres exactly
_ARROW_H = 11   # odd height → triangle centres exactly

def draw_scroll_arrows(draw: ImageDraw, x: int, y_top: int,
                       y_bottom: int, w: int,
                       can_up: bool, can_down: bool) -> None:
    """Draw up/down scroll arrows at the right edge of a list area.

    x, w:       the full pane position and width
    y_top:      y of the first row
    y_bottom:   y of the bottom of the last row
    """
    if not can_up and not can_down:
        return

    bx = x + w - SCROLL_W + 1  # 1px left margin in column

    if can_up:
        by = y_top
        draw.rectangle([bx, by, bx + _ARROW_W - 1, by + _ARROW_H - 1],
                       fill=config.WHITE, outline=config.BLACK)
        # Triangle pointing up — centred in odd×odd box
        cx = bx + _ARROW_W // 2
        cy = by + _ARROW_H // 2
        draw.polygon([(cx - 2, cy + 1), (cx + 2, cy + 1), (cx, cy - 2)],
                     fill=config.BLACK)

    if can_down:
        by = y_bottom - _ARROW_H
        draw.rectangle([bx, by, bx + _ARROW_W - 1, by + _ARROW_H - 1],
                       fill=config.WHITE, outline=config.BLACK)
        # Triangle pointing down — centred in odd×odd box
        cx = bx + _ARROW_W // 2
        cy = by + _ARROW_H // 2
        draw.polygon([(cx - 2, cy - 1), (cx + 2, cy - 1), (cx, cy + 2)],
                     fill=config.BLACK)


def scroll_hit_regions(x: int, y_top: int, y_bottom: int,
                       w: int) -> tuple:
    """Return (up_rect, down_rect) hit regions matching draw_scroll_arrows."""
    bx = x + w - SCROLL_W + 1
    up_rect   = (bx, y_top, bx + _ARROW_W - 1, y_top + _ARROW_H - 1)
    down_rect = (bx, y_bottom - _ARROW_H, bx + _ARROW_W - 1, y_bottom - 1)
    return up_rect, down_rect


# ------------------------------------------------------------------
# Icons (drawn with PIL primitives — no image files needed)
# ------------------------------------------------------------------

def _draw_triangle_right(draw, cx, cy, size, fill):
    """Right-pointing triangle centred at (cx, cy)."""
    pts = [
        (cx - size // 2, cy - size // 2),
        (cx + size // 2, cy),
        (cx - size // 2, cy + size // 2),
    ]
    draw.polygon(pts, fill=fill)


def _draw_triangle_left(draw, cx, cy, size, fill):
    """Left-pointing triangle centred at (cx, cy)."""
    pts = [
        (cx + size // 2, cy - size // 2),
        (cx - size // 2, cy),
        (cx + size // 2, cy + size // 2),
    ]
    draw.polygon(pts, fill=fill)


def draw_icon_play(draw, cx, cy, size=10, fill=config.BLACK):
    _draw_triangle_right(draw, cx, cy, size, fill)


def draw_icon_pause(draw, cx, cy, size=10, fill=config.BLACK):
    bar_w = max(2, size // 4)
    bar_h = size
    gap   = max(2, size // 4)
    lx = cx - gap // 2 - bar_w
    rx = cx + gap // 2
    draw.rectangle([lx, cy - bar_h // 2, lx + bar_w - 1, cy + bar_h // 2], fill=fill)
    draw.rectangle([rx, cy - bar_h // 2, rx + bar_w - 1, cy + bar_h // 2], fill=fill)


def draw_icon_prev(draw, cx, cy, size=10, fill=config.BLACK):
    bar_w = max(2, size // 5)
    draw.rectangle([cx - size // 2, cy - size // 2,
                    cx - size // 2 + bar_w - 1, cy + size // 2], fill=fill)
    _draw_triangle_left(draw, cx + bar_w // 2, cy, size - bar_w - 1, fill)


def draw_icon_next(draw, cx, cy, size=10, fill=config.BLACK):
    bar_w = max(2, size // 5)
    draw.rectangle([cx + size // 2 - bar_w + 1, cy - size // 2,
                    cx + size // 2, cy + size // 2], fill=fill)
    _draw_triangle_right(draw, cx - bar_w // 2, cy, size - bar_w - 1, fill)


def draw_icon_vol_down(draw, cx, cy, size=10, fill=config.BLACK):
    hw = max(3, size // 3)
    hh = max(2, size // 5)
    draw.rectangle([cx - hw, cy - hh, cx + hw, cy + hh], fill=fill)


def draw_icon_vol_up(draw, cx, cy, size=10, fill=config.BLACK):
    hw = max(3, size // 3)
    hh = max(1, size // 8)
    draw.rectangle([cx - hw, cy - hh, cx + hw, cy + hh], fill=fill)
    draw.rectangle([cx - hh, cy - hw, cx + hh, cy + hw], fill=fill)
