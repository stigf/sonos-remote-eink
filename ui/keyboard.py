# ui/keyboard.py — Full-screen on-screen keyboard for password entry
#
# Takes over the entire 250×122 display as a modal overlay.
# No tab bar is drawn while the keyboard is active.
#
# Layout (250×122):
#   y= 0-11  Label: "WiFi: SSID"
#   y=12-23  Input field (inverted, showing entered text + cursor)
#   y=24-45  Keyboard row 1 (10 keys, 22px tall)
#   y=46-67  Keyboard row 2 (9 keys, offset, 22px tall)
#   y=68-89  Keyboard row 3 (shift + 7 keys + del, 22px tall)
#   y=90-121 Keyboard row 4 (mode + space + cancel + ok, 32px tall)

from PIL import Image, ImageDraw

import config
from ui import fonts, widgets

# Hit regions: key_id → (x0, y0, x1, y1)
# Rebuilt on each render() call.
REGIONS = {}

# --- Layout constants ---
_W = config.DISPLAY_W       # 250
_H = config.DISPLAY_H       # 122

_LABEL_Y  = 0
_LABEL_H  = 12
_INPUT_Y  = 12
_INPUT_H  = 12

_ROW_Y = [24, 46, 68, 90]
_ROW_H = [22, 22, 22, 32]   # bottom row taller for bigger touch targets

_KEY_W = 25                  # standard key width

# --- Key layouts ---
_ALPHA_LOWER = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm']
_ALPHA_UPPER = ['QWERTYUIOP', 'ASDFGHJKL', 'ZXCVBNM']
_SYMBOLS     = ['1234567890', '-/:;()&@.', '!?#%^*_']

# Row 3 special key widths
_SHIFT_W = 35
_DEL_W   = 40

# Row 4 widths
_MODE_W   = 50    # "?123" / "abc"
_SPACE_W  = 70
_CANCEL_W = 65
_OK_W     = 65


def render(snap) -> Image.Image:
    """Render the full-screen keyboard overlay. Returns 250×122 image."""
    img  = Image.new('1', (_W, _H), config.WHITE)
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"

    ssid = snap.keyboard_target_ssid
    text = snap.keyboard_text
    shift = snap.keyboard_shift
    symbols = snap.keyboard_symbols

    # Pick the active character layout
    if symbols:
        rows = _SYMBOLS
    elif shift:
        rows = _ALPHA_UPPER
    else:
        rows = _ALPHA_LOWER

    # --- Label (smaller font — secondary context) ---
    label = widgets.truncate(f'WiFi: {ssid}', fonts.TINY, _W - 4)
    draw.text((2, _LABEL_Y + (_LABEL_H - widgets._text_h(fonts.TINY)) // 2),
              label, font=fonts.TINY, fill=config.BLACK)

    # --- Input field (inverted for visual separation from keys) ---
    _draw_input(draw, text)

    # --- Keyboard rows 1-3 ---
    _draw_char_rows(draw, rows, shift, symbols)

    # --- Row 4: mode, space, cancel, ok ---
    _draw_bottom_row(draw, symbols)

    # --- Build hit regions ---
    _build_regions(rows, symbols)

    return img


# ------------------------------------------------------------------
# Input field
# ------------------------------------------------------------------

def _draw_input(draw: ImageDraw, text: str) -> None:
    x, y, w, h = 0, _INPUT_Y, _W, _INPUT_H

    # Inverted input field — visually distinct from the keyboard keys
    draw.rectangle([x, y, x + w - 1, y + h - 1], fill=config.BLACK)

    # Show text with cursor
    display_text = text + '|'
    max_chars_w = w - 8

    # If text overflows, show the rightmost portion
    font = fonts.BOLD
    while widgets._text_w(display_text, font) > max_chars_w and len(display_text) > 1:
        display_text = display_text[1:]

    th = widgets._text_h(font)
    draw.text((x + 4, y + (h - th) // 2), display_text,
              font=font, fill=config.WHITE)


# ------------------------------------------------------------------
# Character rows (rows 1-3)
# ------------------------------------------------------------------

def _draw_char_rows(draw: ImageDraw, rows: list, shift: bool, symbols: bool) -> None:
    # Row 1: 10 keys, full width
    _draw_key_row(draw, rows[0], 0, _ROW_Y[0], _ROW_H[0], _KEY_W)

    # Row 2: 9 keys, offset by half a key width
    offset = (_W - len(rows[1]) * _KEY_W) // 2
    _draw_key_row(draw, rows[1], offset, _ROW_Y[1], _ROW_H[1], _KEY_W)

    # Row 3: shift/abc + 7 chars + del
    y3 = _ROW_Y[2]
    h3 = _ROW_H[2]
    x = 0

    # Shift or ABC button
    if not symbols:
        mode_label = 'ABC' if not shift else 'abc'
    else:
        mode_label = 'abc'
    _draw_key(draw, x, y3, _SHIFT_W, h3, mode_label, inverted=shift)
    x += _SHIFT_W

    # Character keys
    char_w = (_W - _SHIFT_W - _DEL_W) // len(rows[2])
    for ch in rows[2]:
        _draw_key(draw, x, y3, char_w, h3, ch)
        x += char_w

    # Delete button (fills remaining width)
    _draw_key(draw, x, y3, _W - x, h3, 'DEL')


def _draw_key_row(draw: ImageDraw, chars: str, x_offset: int,
                  y: int, h: int, key_w: int) -> None:
    x = x_offset
    for ch in chars:
        _draw_key(draw, x, y, key_w, h, ch)
        x += key_w


# ------------------------------------------------------------------
# Bottom row (row 4)
# ------------------------------------------------------------------

def _draw_bottom_row(draw: ImageDraw, symbols: bool) -> None:
    y = _ROW_Y[3]
    h = _ROW_H[3]
    x = 0

    mode_label = 'abc' if symbols else '?123'
    _draw_key(draw, x, y, _MODE_W, h, mode_label)
    x += _MODE_W

    _draw_key(draw, x, y, _SPACE_W, h, 'SPACE')
    x += _SPACE_W

    _draw_key(draw, x, y, _CANCEL_W, h, 'CNCL')
    x += _CANCEL_W

    _draw_key(draw, x, y, _OK_W, h, 'OK', inverted=True)


# ------------------------------------------------------------------
# Single key drawing
# ------------------------------------------------------------------

def _draw_key(draw: ImageDraw, x: int, y: int, w: int, h: int,
              label: str, inverted: bool = False) -> None:
    bg = config.BLACK if inverted else config.WHITE
    fg = config.WHITE if inverted else config.BLACK

    draw.rectangle([x, y, x + w - 1, y + h - 1], fill=bg, outline=config.BLACK)

    font = fonts.SMALL if len(label) > 2 else fonts.BOLD
    tw = widgets._text_w(label, font)
    th = widgets._text_h(font)
    tx = x + (w - tw) // 2
    ty = y + (h - th) // 2
    draw.text((tx, ty), label, font=font, fill=fg)


# ------------------------------------------------------------------
# Hit regions
# ------------------------------------------------------------------

def _build_regions(rows: list, symbols: bool) -> None:
    REGIONS.clear()

    # Row 1: 10 character keys
    for i, ch in enumerate(rows[0]):
        x = i * _KEY_W
        REGIONS[f'char_{ch}'] = (x, _ROW_Y[0], x + _KEY_W - 1, _ROW_Y[0] + _ROW_H[0] - 1)

    # Row 2: 9 character keys (offset)
    offset = (_W - len(rows[1]) * _KEY_W) // 2
    for i, ch in enumerate(rows[1]):
        x = offset + i * _KEY_W
        REGIONS[f'char_{ch}'] = (x, _ROW_Y[1], x + _KEY_W - 1, _ROW_Y[1] + _ROW_H[1] - 1)

    # Row 3: shift/abc + characters + del
    y3 = _ROW_Y[2]
    h3 = _ROW_H[2]
    x = 0

    REGIONS['shift'] = (x, y3, x + _SHIFT_W - 1, y3 + h3 - 1)
    x += _SHIFT_W

    char_w = (_W - _SHIFT_W - _DEL_W) // len(rows[2])
    for ch in rows[2]:
        REGIONS[f'char_{ch}'] = (x, y3, x + char_w - 1, y3 + h3 - 1)
        x += char_w

    REGIONS['del'] = (x, y3, _W - 1, y3 + h3 - 1)

    # Row 4: mode, space, cancel, ok
    y4 = _ROW_Y[3]
    h4 = _ROW_H[3]
    x = 0

    REGIONS['mode'] = (x, y4, x + _MODE_W - 1, y4 + h4 - 1)
    x += _MODE_W

    REGIONS['space'] = (x, y4, x + _SPACE_W - 1, y4 + h4 - 1)
    x += _SPACE_W

    REGIONS['cancel'] = (x, y4, x + _CANCEL_W - 1, y4 + h4 - 1)
    x += _CANCEL_W

    REGIONS['ok'] = (x, y4, _W - 1, y4 + h4 - 1)
