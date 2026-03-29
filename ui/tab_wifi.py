# ui/tab_wifi.py — WiFi settings tab
#
# Two modes:
#   Normal  — shows current connection, scanned networks, [Scan] and [Setup] buttons
#   AP mode — shows hotspot instructions (connect phone, open portal URL)
#
# Layout (content area 250×106):
#
#   NORMAL MODE:
#     y=0   Status line: "Connected: MyNetwork  (IP)"  or  "Not connected"
#     y=14  Signal bar
#     y=22  ──── separator ────
#     y=24  Network list rows (4 visible, 15px each)
#     y=84  ──── separator ────
#     y=86  [Scan]   [Setup AP]
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
_BTN_Y = 88
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
    visible  = config.WIFI_VISIBLE_ROWS
    scroll   = max(0, min(snap.wifi_scroll, max(0, len(networks) - visible)))

    for i in range(visible):
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
    if scroll + visible < len(networks):
        bottom = _LIST_TOP + visible * _ROW_H - 1
        draw.polygon([(W - 8, bottom), (W - 4, bottom),
                       (W - 6, bottom + 3)], fill=config.BLACK)

    # ---- Separator ----
    draw.line([0, 85, W - 1, 85], fill=config.BLACK)

    # ---- Buttons (evenly spaced across width) ----
    btn_gap = 3
    btn_w = (W - 4 - btn_gap * 2) // 3   # ~81px each
    btn_x0 = 2
    btn_x1 = btn_x0 + btn_w + btn_gap
    btn_x2 = btn_x1 + btn_w + btn_gap

    widgets.draw_button(draw, btn_x0, _BTN_Y, btn_w, _BTN_H,
                        'Scan', font=fonts.SMALL)

    art_label = 'Art:ON' if snap.show_album_art else 'Art:OFF'
    widgets.draw_button(draw, btn_x1, _BTN_Y, btn_w, _BTN_H,
                        art_label, font=fonts.SMALL,
                        inverted=snap.show_album_art)

    widgets.draw_button(draw, btn_x2, _BTN_Y, W - btn_x2 - 2, _BTN_H,
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
    widgets.draw_button(draw, W - 72, _BTN_Y, 70, _BTN_H, 'Stop AP',
                        font=fonts.SMALL, inverted=True)


# ------------------------------------------------------------------
# Hit regions
# ------------------------------------------------------------------

def _build_regions(snap: AppState) -> None:
    REGIONS.clear()
    W = config.DISPLAY_W

    if snap.wifi_ap_mode:
        REGIONS['wifi_ap_stop'] = (W - 72, _BTN_Y, W - 2, _BTN_Y + _BTN_H)
    else:
        btn_gap = 3
        btn_w = (W - 4 - btn_gap * 2) // 3
        btn_x0 = 2
        btn_x1 = btn_x0 + btn_w + btn_gap
        btn_x2 = btn_x1 + btn_w + btn_gap
        REGIONS['wifi_scan'] = (btn_x0, _BTN_Y, btn_x0 + btn_w - 1, _BTN_Y + _BTN_H)
        REGIONS['toggle_art'] = (btn_x1, _BTN_Y, btn_x1 + btn_w - 1, _BTN_Y + _BTN_H)
        REGIONS['wifi_ap_start'] = (btn_x2, _BTN_Y, W - 2, _BTN_Y + _BTN_H)

        # Network rows (tap to see info — actual connection is via portal)
        visible = config.WIFI_VISIBLE_ROWS
        scroll  = max(0, min(snap.wifi_scroll,
                             max(0, len(snap.wifi_networks) - visible)))
        for i in range(min(visible, len(snap.wifi_networks) - scroll)):
            idx = i + scroll
            y = _LIST_TOP + i * _ROW_H
            REGIONS[f'wifi_net_{idx}'] = (0, y, W - 1, y + _ROW_H - 1)

        # Scroll zones
        if len(snap.wifi_networks) > visible:
            REGIONS['wifi_scroll_up'] = (0, _LIST_TOP, W - 1,
                                          _LIST_TOP + _ROW_H - 1)
            bottom = _LIST_TOP + visible * _ROW_H
            REGIONS['wifi_scroll_down'] = (0, bottom - _ROW_H, W - 1, bottom - 1)
