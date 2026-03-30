# ui/tab_wifi.py — Settings tab (WiFi, art, shuffle, repeat)
#
# Two modes:
#   Normal  — shows current connection, scanned networks, toggle buttons,
#             and WiFi action buttons
#   AP mode — shows hotspot instructions (connect phone, open portal URL)
#
# Layout (content area 250×106):
#
#   NORMAL MODE:
#     y=0   Status line: "Connected: MyNetwork  (IP)"  or  "Not connected"
#     y=14  Signal bar
#     y=22  ──── separator ────
#     y=24  Network list rows (3 visible, 15px each)
#     y=69  ──── separator ────
#     y=71  [Art:ON]  [Shfl:ON]  [Rpt:ON]   ← toggle buttons
#     y=88  [Scan]    [Setup AP]             ← WiFi action buttons
#
#   AP MODE:
#     y=0   "Connect phone to WiFi:"
#     y=14  SSID (bold)
#     y=30  "Password:"
#     y=44  password (bold)
#     y=62  "Then open in browser:"
#     y=76  URL (bold)
#     y=92  [Stop AP]

from PIL import Image, ImageDraw

import config
from ui import fonts, widgets
from state import AppState

# Exported for hit-testing
REGIONS = {}

_ROW_H = config.WIFI_ROW_H
_LIST_TOP = 24
_VISIBLE_ROWS = 3        # reduced from 4 to fit toggle row
_TOGGLE_Y = 71            # toggle buttons row (Art, Shuffle, Repeat)
_ACTION_Y = 88            # WiFi action buttons row (Scan, Setup AP)
_BTN_H = 16


def render(snap: AppState) -> Image.Image:
    img  = Image.new('1', (config.DISPLAY_W, config.DISPLAY_H), config.WHITE)
    draw = ImageDraw.Draw(img)

    if snap.wifi_ap_mode:
        _draw_ap_mode(draw, snap)
    else:
        _draw_normal(draw, snap)

    widgets.draw_tab_bar(draw, snap.active_tab)
    _build_regions(snap)

    return img


# ------------------------------------------------------------------
# Normal mode
# ------------------------------------------------------------------

def _draw_normal(draw: ImageDraw, snap: AppState) -> None:
    W = config.DISPLAY_W

    # ---- Status line ----
    if snap.wifi_ssid:
        status = f'{snap.wifi_ssid}  {snap.wifi_ip}'
        draw.text((2, 0), widgets.truncate(status, fonts.BOLD, W - 4),
                  font=fonts.BOLD, fill=config.BLACK)
        # Signal bar
        widgets.draw_bar(draw, 2, 14, 60, 5,
                         snap.wifi_signal / 100.0, border=True)
        sig_str = f'{snap.wifi_signal}%'
        draw.text((65, 12), sig_str, font=fonts.TINY, fill=config.BLACK)
    else:
        draw.text((2, 0), 'Not connected', font=fonts.BOLD, fill=config.BLACK)

    # Status message (e.g. "Connected to X" or error)
    if snap.wifi_status:
        sw = widgets._text_w(snap.wifi_status, fonts.TINY)
        draw.text((W - sw - 2, 12),
                  widgets.truncate(snap.wifi_status, fonts.TINY, W // 2),
                  font=fonts.TINY, fill=config.BLACK)

    # ---- Separator ----
    draw.line([0, 22, W - 1, 22], fill=config.BLACK)

    # ---- Network list ----
    networks = snap.wifi_networks
    scroll   = max(0, min(snap.wifi_scroll, max(0, len(networks) - _VISIBLE_ROWS)))

    for i in range(_VISIBLE_ROWS):
        idx = i + scroll
        y = _LIST_TOP + i * _ROW_H
        if idx >= len(networks):
            break
        net = networks[idx]
        is_active = net.active

        # Row
        font = fonts.BOLD if is_active else fonts.SMALL
        prefix = '* ' if is_active else '  '
        lock = '' if net.security == 'open' else ' [+]'

        # Signal indicator (text)
        sig_str = f'{net.signal}%{lock}'
        sig_w = widgets._text_w(sig_str, fonts.TINY)

        name_max = W - sig_w - 8
        label = prefix + widgets.truncate(net.ssid, font, name_max - widgets._text_w(prefix, font))

        widgets.draw_list_row(draw, 0, y, W, _ROW_H, '',
                              inverted=is_active)
        fg = config.WHITE if is_active else config.BLACK
        draw.text((2, y + (_ROW_H - widgets._text_h(font)) // 2),
                  label, font=font, fill=fg)
        draw.text((W - sig_w - 2, y + (_ROW_H - widgets._text_h(fonts.TINY)) // 2),
                  sig_str, font=fonts.TINY, fill=fg)

    # Scroll hints
    if scroll > 0:
        draw.polygon([(W - 8, _LIST_TOP + 1), (W - 4, _LIST_TOP + 1),
                       (W - 6, _LIST_TOP - 2)], fill=config.BLACK)
    if scroll + _VISIBLE_ROWS < len(networks):
        bottom = _LIST_TOP + _VISIBLE_ROWS * _ROW_H - 1
        draw.polygon([(W - 8, bottom), (W - 4, bottom),
                       (W - 6, bottom + 3)], fill=config.BLACK)

    # ---- Separator ----
    draw.line([0, 69, W - 1, 69], fill=config.BLACK)

    # ---- Toggle buttons row (Art, Shuffle, Repeat) ----
    btn_gap = 3
    toggle_w = (W - 4 - btn_gap * 2) // 3
    tx0 = 2
    tx1 = tx0 + toggle_w + btn_gap
    tx2 = tx1 + toggle_w + btn_gap

    art_label = 'Art:ON' if snap.show_album_art else 'Art:OFF'
    widgets.draw_button(draw, tx0, _TOGGLE_Y, toggle_w, _BTN_H,
                        art_label, font=fonts.SMALL,
                        inverted=snap.show_album_art)

    shfl_label = 'Shfl:ON' if snap.shuffle else 'Shfl:OFF'
    widgets.draw_button(draw, tx1, _TOGGLE_Y, toggle_w, _BTN_H,
                        shfl_label, font=fonts.SMALL,
                        inverted=snap.shuffle)

    rpt_label = 'Rpt:ON' if snap.repeat else 'Rpt:OFF'
    widgets.draw_button(draw, tx2, _TOGGLE_Y, W - tx2 - 2, _BTN_H,
                        rpt_label, font=fonts.SMALL,
                        inverted=snap.repeat)

    # ---- WiFi action buttons row (Scan, Setup AP) ----
    action_w = (W - 4 - btn_gap) // 2
    ax0 = 2
    ax1 = ax0 + action_w + btn_gap

    widgets.draw_button(draw, ax0, _ACTION_Y, action_w, _BTN_H,
                        'Scan', font=fonts.SMALL)
    widgets.draw_button(draw, ax1, _ACTION_Y, W - ax1 - 2, _BTN_H,
                        'Setup AP', font=fonts.SMALL)


# ------------------------------------------------------------------
# AP mode
# ------------------------------------------------------------------

def _draw_ap_mode(draw: ImageDraw, snap: AppState) -> None:
    W = config.DISPLAY_W

    draw.text((2, 0), 'Connect phone to WiFi:', font=fonts.SMALL, fill=config.BLACK)

    ssid = config.WIFI_HOTSPOT_SSID
    draw.text((2, 13), ssid, font=fonts.TITLE, fill=config.BLACK)

    draw.text((2, 30), 'Password:', font=fonts.SMALL, fill=config.BLACK)
    draw.text((2, 42), config.WIFI_HOTSPOT_PASSWORD, font=fonts.BOLD, fill=config.BLACK)

    draw.text((2, 58), 'Then open in browser:', font=fonts.SMALL, fill=config.BLACK)
    url = f'http://{config.WIFI_PORTAL_IP}'
    draw.text((2, 70), url, font=fonts.BOLD, fill=config.BLACK)

    # Status
    if snap.wifi_status:
        draw.text((2, 86), widgets.truncate(snap.wifi_status, fonts.TINY, W - 4),
                  font=fonts.TINY, fill=config.BLACK)

    # Stop button
    widgets.draw_button(draw, W - 72, _ACTION_Y, 70, _BTN_H, 'Stop AP',
                        font=fonts.SMALL, inverted=True)


# ------------------------------------------------------------------
# Hit regions
# ------------------------------------------------------------------

def _build_regions(snap: AppState) -> None:
    REGIONS.clear()
    W = config.DISPLAY_W

    if snap.wifi_ap_mode:
        REGIONS['wifi_ap_stop'] = (W - 72, _ACTION_Y, W - 2, _ACTION_Y + _BTN_H)
    else:
        btn_gap = 3

        # Toggle row
        toggle_w = (W - 4 - btn_gap * 2) // 3
        tx0 = 2
        tx1 = tx0 + toggle_w + btn_gap
        tx2 = tx1 + toggle_w + btn_gap
        REGIONS['toggle_art']     = (tx0, _TOGGLE_Y, tx0 + toggle_w - 1, _TOGGLE_Y + _BTN_H)
        REGIONS['toggle_shuffle'] = (tx1, _TOGGLE_Y, tx1 + toggle_w - 1, _TOGGLE_Y + _BTN_H)
        REGIONS['toggle_repeat']  = (tx2, _TOGGLE_Y, W - 2, _TOGGLE_Y + _BTN_H)

        # Action row
        action_w = (W - 4 - btn_gap) // 2
        ax0 = 2
        ax1 = ax0 + action_w + btn_gap
        REGIONS['wifi_scan']     = (ax0, _ACTION_Y, ax0 + action_w - 1, _ACTION_Y + _BTN_H)
        REGIONS['wifi_ap_start'] = (ax1, _ACTION_Y, W - 2, _ACTION_Y + _BTN_H)

        # Network rows
        scroll = max(0, min(snap.wifi_scroll,
                            max(0, len(snap.wifi_networks) - _VISIBLE_ROWS)))
        for i in range(min(_VISIBLE_ROWS, len(snap.wifi_networks) - scroll)):
            idx = i + scroll
            y = _LIST_TOP + i * _ROW_H
            REGIONS[f'wifi_net_{idx}'] = (0, y, W - 1, y + _ROW_H - 1)

        # Scroll zones
        if len(snap.wifi_networks) > _VISIBLE_ROWS:
            REGIONS['wifi_scroll_up'] = (0, _LIST_TOP, W - 1,
                                          _LIST_TOP + _ROW_H - 1)
            bottom = _LIST_TOP + _VISIBLE_ROWS * _ROW_H
            REGIONS['wifi_scroll_down'] = (0, bottom - _ROW_H, W - 1, bottom - 1)
