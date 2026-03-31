# ui/tab_now_playing.py — Now Playing tab renderer
#
# The Now Playing tab does NOT show the tab bar by default.  Instead a
# small menu icon (⋮) sits in the top-right corner.  Tapping it sets
# show_tab_bar=True, which overlays the tab bar at the bottom.
# Content always renders at the full 122px; the tab bar draws on top.
#
# Two visual modes:
#
#   IDLE  — title, artist, total duration centred (full height)
#   ACTIVE — title, artist, progress bar, controls, volume
#
# The menu icon is drawn in active mode when the tab bar is hidden.
# It is NOT drawn in idle mode — idle has no interactive elements.
#
# Album art (optional, user setting) is drawn on the left side of the
# screen in both idle and active modes, with text offset right.

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

import config
from ui import fonts, widgets
from state import AppState


# Exported for hit-testing
REGIONS = {}


def render(snap: AppState) -> Image.Image:
    img  = Image.new('1', (config.DISPLAY_W, config.DISPLAY_H), config.WHITE)
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"

    has_tabs = snap.show_tab_bar

    if snap.idle_mode:
        _draw_idle(img, draw, snap)
    else:
        _draw_active(img, draw, snap)

    if has_tabs:
        widgets.draw_tab_bar(draw, snap.active_tab)
    elif not snap.idle_mode:
        _draw_menu_icon(draw)

    nothing = (not snap.idle_mode and not snap.track_title
               and snap.playback_state in ('STOPPED', ''))
    _build_regions(has_tabs, snap.idle_mode, nothing)
    return img


# ------------------------------------------------------------------
# Menu icon (vertical dots ⋮)
# ------------------------------------------------------------------

def _draw_menu_icon(draw: ImageDraw) -> None:
    # Vertical dots (⋮) — 2×2px each for better visibility
    cx = config.MENU_ICON_X + config.MENU_ICON_W // 2
    for dy in [2, 7, 12]:
        draw.rectangle([cx - 1, dy, cx + 1, dy + 1], fill=config.BLACK)


# ------------------------------------------------------------------
# Idle layout — title, artist, total duration (clean, minimal)
# ------------------------------------------------------------------

def _draw_idle(img: Image.Image, draw: ImageDraw, snap: AppState) -> None:
    art_img = _get_art(snap)

    if art_img is not None:
        _draw_idle_with_art(img, draw, snap, art_img)
    else:
        _draw_idle_no_art(draw, snap)


def _draw_idle_no_art(draw: ImageDraw, snap: AppState) -> None:
    """Idle without art: everything centred on screen."""
    content_h = config.DISPLAY_H
    W = config.DISPLAY_W

    # Compute total text block height to centre vertically
    title_raw = snap.track_title or 'Nothing playing'

    # Auto-downsize: use large font if title fits, otherwise fall back
    idle_font = fonts.IDLE_TITLE
    if widgets._text_w(title_raw, idle_font) > W - 8:
        idle_font = fonts.TITLE

    title_h = widgets._text_h(idle_font)
    artist_h = widgets._text_h(fonts.REGULAR)
    album_h = widgets._text_h(fonts.SMALL)

    has_artist = bool(snap.track_artist)
    has_album = bool(snap.track_album)
    has_time = snap.duration_sec > 0 or snap.playback_state == 'PLAYING'

    # Block: title + artist + album + time
    block_h = title_h
    if has_artist:
        block_h += 4 + artist_h
    if has_album:
        block_h += 2 + album_h
    if has_time:
        block_h += 12 + widgets._text_h(fonts.TITLE)

    top_y = max(4, (content_h - block_h) // 2)
    y = top_y

    # Title (centred, truncated to fit)
    title = widgets.truncate(title_raw, idle_font, W - 8)
    tw = widgets._text_w(title, idle_font)
    draw.text(((W - tw) // 2, y), title, font=idle_font, fill=config.BLACK)
    y += title_h + 4

    # Artist (centred)
    if has_artist:
        artist = widgets.truncate(snap.track_artist, fonts.REGULAR, W - 8)
        aw = widgets._text_w(artist, fonts.REGULAR)
        draw.text(((W - aw) // 2, y), artist,
                  font=fonts.REGULAR, fill=config.BLACK)
        y += artist_h + 2

    # Album (centred, smaller font)
    if has_album:
        album = widgets.truncate(snap.track_album, fonts.SMALL, W - 8)
        alw = widgets._text_w(album, fonts.SMALL)
        draw.text(((W - alw) // 2, y), album,
                  font=fonts.SMALL, fill=config.BLACK)
        y += album_h

    # Total duration (centred, with gap)
    if has_time:
        if snap.duration_sec > 0:
            dur_str = _fmt_time(snap.duration_sec)
        else:
            dur_str = '...'
        dw = widgets._text_w(dur_str, fonts.TITLE)
        dy = y + 12
        draw.text(((W - dw) // 2, dy), dur_str, font=fonts.TITLE, fill=config.BLACK)


def _draw_idle_with_art(img: Image.Image, draw: ImageDraw, snap: AppState,
                        art_img) -> None:
    """Idle with art: art on left, text vertically centred beside it."""
    content_h = config.DISPLAY_H
    W = config.DISPLAY_W
    art_sz = config.ART_IDLE_SIZE
    art = _prepare_art(art_img, art_sz)

    # Centre art vertically
    art_y = max(2, (content_h - art_sz) // 2)
    img.paste(art, (config.ART_X, art_y))
    draw.rectangle([config.ART_X - 1, art_y - 1,
                     config.ART_X + art_sz, art_y + art_sz],
                    outline=config.BLACK)

    # Text area to the right of art
    text_x = config.ART_X + art_sz + config.ART_GAP + 2
    text_w = W - text_x - 2

    # Build text block — auto-downsize title if it would truncate at TITLE
    title_raw = snap.track_title or 'Nothing playing'
    title_font = fonts.TITLE
    if widgets._text_w(title_raw, title_font) > text_w:
        title_font = fonts.BOLD
    title_h = widgets._text_h(title_font)
    artist_h = widgets._text_h(fonts.REGULAR)
    album_h = widgets._text_h(fonts.SMALL)

    has_artist = bool(snap.track_artist)
    has_album = bool(snap.track_album)
    has_time = snap.duration_sec > 0 or snap.playback_state == 'PLAYING'

    block_h = title_h
    if has_artist:
        block_h += 4 + artist_h
    if has_album:
        block_h += 2 + album_h
    if has_time:
        block_h += 10 + title_h

    top_y = max(4, (content_h - block_h) // 2)
    y = top_y

    # Title
    draw.text((text_x, y),
              widgets.truncate(title_raw, title_font, text_w),
              font=title_font, fill=config.BLACK)
    y += title_h + 4

    # Artist
    if has_artist:
        draw.text((text_x, y),
                  widgets.truncate(snap.track_artist, fonts.REGULAR, text_w),
                  font=fonts.REGULAR, fill=config.BLACK)
        y += artist_h + 2

    # Album (smaller font)
    if has_album:
        draw.text((text_x, y),
                  widgets.truncate(snap.track_album, fonts.SMALL, text_w),
                  font=fonts.SMALL, fill=config.BLACK)
        y += album_h

    # Total duration
    if has_time:
        y += 10
        if snap.duration_sec > 0:
            dur_str = _fmt_time(snap.duration_sec)
        else:
            dur_str = '...'
        draw.text((text_x, y), dur_str, font=fonts.TITLE, fill=config.BLACK)


# ------------------------------------------------------------------
# Active layout — full controls
# ------------------------------------------------------------------

def _draw_active(img: Image.Image, draw: ImageDraw, snap: AppState) -> None:
    content_h = config.DISPLAY_H
    W = config.DISPLAY_W

    # Nothing playing — minimal centered state
    if not snap.track_title and snap.playback_state in ('STOPPED', ''):
        msg = 'Nothing playing'
        mw = widgets._text_w(msg, fonts.TITLE)
        mh = widgets._text_h(fonts.TITLE)
        cy = content_h // 2 - 6
        draw.text(((W - mw) // 2, cy - mh // 2), msg,
                  font=fonts.TITLE, fill=config.BLACK)
        # Play icon below text
        widgets.draw_icon_play(draw, W // 2, cy + mh + 8, 14)
        return

    art_img = _get_art(snap)

    # Text offset depends on art
    text_x = config.MARGIN
    if art_img is not None:
        art_sz = config.ART_SIZE
        art = _prepare_art(art_img, art_sz)
        img.paste(art, (config.ART_X, config.ART_Y))
        draw.rectangle([config.ART_X - 1, config.ART_Y - 1,
                         config.ART_X + art_sz, config.ART_Y + art_sz],
                        outline=config.BLACK)
        text_x = config.ART_X + art_sz + config.ART_GAP

    # Right edge for title (leave room for menu icon when no tab bar)
    title_r = W - config.MARGIN
    if not snap.show_tab_bar:
        title_r = W - config.MENU_ICON_W - 4
    title_max = title_r - text_x

    # ---- Title ----
    title = snap.track_title or 'Nothing playing'
    draw.text((text_x, config.NP_TITLE_Y),
              widgets.truncate(title, fonts.TITLE, title_max),
              font=fonts.TITLE, fill=config.BLACK)

    # ---- Artist ----
    if snap.track_artist:
        draw.text((text_x, config.NP_ARTIST_Y),
                  widgets.truncate(snap.track_artist, fonts.REGULAR, W - text_x - 2),
                  font=fonts.REGULAR, fill=config.BLACK)

    # ---- Progress bar (always full width) ----
    # Push below art if present so the bar doesn't overlap
    prog_y = config.NP_PROGRESS_Y
    if art_img is not None:
        art_bottom = config.ART_Y + config.ART_SIZE + 2
        prog_y = max(prog_y, art_bottom)

    frac = (snap.position_sec / snap.duration_sec
            if snap.duration_sec > 0 else 0.0)
    widgets.draw_bar(draw, 0, prog_y, W,
                     config.NP_PROGRESS_H, frac, border=True)

    # Timestamp (elapsed / total)
    time_y = prog_y + config.NP_PROGRESS_H + 2

    pos_str = _fmt_time(snap.position_sec) + ' / ' + _fmt_time(snap.duration_sec)
    draw.text((2, time_y), pos_str, font=fonts.TINY, fill=config.BLACK)

    # ---- Control icons (no outlines — hit regions built separately in _build_regions) ----
    cy   = config.NP_CTRL_Y + config.NP_CTRL_H // 2
    icon_sz = 14

    playing = (snap.playback_state == 'PLAYING')

    for (cx, _hw, action) in [
        (config.NP_BTN_PREV[0],  config.NP_BTN_PREV[1],  'prev'),
        (config.NP_BTN_PLAY[0],  config.NP_BTN_PLAY[1],  'play_pause'),
        (config.NP_BTN_NEXT[0],  config.NP_BTN_NEXT[1],  'next'),
        (config.NP_BTN_VOLD[0],  config.NP_BTN_VOLD[1],  'vol_down'),
        (config.NP_BTN_VOLU[0],  config.NP_BTN_VOLU[1],  'vol_up'),
    ]:
        _draw_ctrl_icon(draw, action, cx, cy, icon_sz, playing)

    # ---- Volume row (occupies same slot as tab bar) ----
    if not snap.show_tab_bar:
        vol_y  = config.NP_VOL_Y
        vol_h  = config.NP_VOL_H
        vol_frac = snap.volume / 100.0
        text_y = vol_y + (vol_h - widgets._text_h(fonts.SMALL)) // 2

        vol_str = str(snap.volume)
        vw = widgets._text_w(vol_str, fonts.SMALL)
        num_x = W - vw - config.MARGIN

        bar_x = config.MARGIN
        bar_w = num_x - bar_x - 3
        widgets.draw_bar(draw, bar_x, vol_y + 3, bar_w, vol_h - 6, vol_frac,
                         border=True)

        draw.text((num_x, text_y), vol_str, font=fonts.SMALL, fill=config.BLACK)


# ------------------------------------------------------------------
# Shared helpers
# ------------------------------------------------------------------

def _get_art(snap: AppState):
    """Return the album art PIL Image if enabled and available, else None."""
    if snap.show_album_art and snap.album_art_img is not None:
        return snap.album_art_img
    return None


def _prepare_art(art_img, size: int) -> Image.Image:
    """Resize greyscale art to target size and convert to 1-bit.

    The conversion pipeline (autocontrast → sharpen → Floyd-Steinberg dither)
    runs AFTER resizing so the dithering pattern matches the final pixel grid.
    """
    grey = art_img.resize((size, size), Image.LANCZOS)
    if grey.mode != 'L':
        grey = grey.convert('L')
    grey = ImageOps.autocontrast(grey, cutoff=2)
    grey = ImageEnhance.Sharpness(grey).enhance(1.5)
    return grey.convert('1')


def _draw_ctrl_icon(draw, action, cx, cy, sz, playing):
    icon_fn = {
        'prev':       widgets.draw_icon_prev,
        'next':       widgets.draw_icon_next,
        'vol_down':   widgets.draw_icon_vol_down,
        'vol_up':     widgets.draw_icon_vol_up,
    }.get(action)

    if icon_fn:
        icon_fn(draw, cx, cy, sz)
    elif action == 'play_pause':
        if playing:
            widgets.draw_icon_pause(draw, cx, cy, sz)
        else:
            widgets.draw_icon_play(draw, cx, cy, sz)


def _build_regions(has_tabs: bool, idle: bool = False,
                   nothing_playing: bool = False) -> None:
    """Populate the exported REGIONS dict for hit-testing."""
    REGIONS.clear()

    if idle:
        # Idle mode has no interactive elements — any touch just wakes up
        return

    if nothing_playing:
        # Only play button and menu icon — centred play icon acts as play_pause
        content_h = config.DISPLAY_H
        icon_cy = content_h // 2 - 6 + widgets._text_h(fonts.TITLE) + 8
        icon_cx = config.DISPLAY_W // 2
        REGIONS['play_pause'] = (icon_cx - 20, icon_cy - 14,
                                 icon_cx + 20, icon_cy + 14)
        if not has_tabs:
            REGIONS['menu'] = (config.MENU_ICON_X, config.MENU_ICON_Y,
                               config.MENU_ICON_X + config.MENU_ICON_W - 1,
                               config.MENU_ICON_Y + config.MENU_ICON_H - 1)
        return

    # Control buttons (active mode only)
    cy = config.NP_CTRL_Y + config.NP_CTRL_H // 2
    hh = config.NP_BTN_HALF_H

    for cx, hw, action in [
        (config.NP_BTN_PREV[0],  config.NP_BTN_PREV[1],  'prev'),
        (config.NP_BTN_PLAY[0],  config.NP_BTN_PLAY[1],  'play_pause'),
        (config.NP_BTN_NEXT[0],  config.NP_BTN_NEXT[1],  'next'),
        (config.NP_BTN_VOLD[0],  config.NP_BTN_VOLD[1],  'vol_down'),
        (config.NP_BTN_VOLU[0],  config.NP_BTN_VOLU[1],  'vol_up'),
    ]:
        REGIONS[action] = (cx - hw, cy - hh, cx + hw, cy + hh)

    # Menu icon (only when tab bar is hidden)
    if not has_tabs:
        REGIONS['menu'] = (config.MENU_ICON_X, config.MENU_ICON_Y,
                           config.MENU_ICON_X + config.MENU_ICON_W - 1,
                           config.MENU_ICON_Y + config.MENU_ICON_H - 1)


def _fmt_time(seconds: int) -> str:
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f'{h}:{m:02d}:{s:02d}'
    return f'{m}:{s:02d}'
