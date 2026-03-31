# ui/tab_wifi.py — More tab (playback toggles, WiFi management)
#
# Two modes:
#   Normal  — toggle buttons at top, network list below, action buttons
#   AP mode — hotspot instructions (connect phone, open portal URL)
#
# Layout (content area 250×106):
#
#   NORMAL MODE:
#     y=0   [Art]  [Shuffle]  [Repeat]   ← toggle buttons (inverted = on)
#     y=18  ──── separator ────
#     y=20  Network list rows (4 visible, 15px each)
#             Connected network shown inverted; "Not connected" if empty
#     y=82  [Scan]            [Hotspot]  ← WiFi action buttons
#
#   AP MODE:
#     y=0   "Connect phone to WiFi:"
#     y=13  SSID (title)
#     y=30  "Password:"
#     y=42  password (bold)
#     y=58  "Then open in browser:"
#     y=70  URL (bold)
#     y=86  [Stop Hotspot]

from PIL import Image, ImageDraw

import config
from ui import fonts, widgets
from state import AppState

# Exported for hit-testing
REGIONS = {}

_ROW_H = config.WIFI_ROW_H
_BTN_H = 16
_BTN_GAP = 3

# Normal mode layout (toggles on top, WiFi below)
_TOGGLE_Y  = 0
_SEP_Y     = _TOGGLE_Y + _BTN_H + 2          # 18
_LIST_TOP  = _SEP_Y + 2                       # 20
NET_VISIBLE = 4                                # network rows visible
_ACTION_Y  = _LIST_TOP + NET_VISIBLE * _ROW_H + 2  # 82


def render(snap: AppState) -> Image.Image:
    img  = Image.new('1', (config.DISPLAY_W, config.DISPLAY_H), config.WHITE)
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"

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

    # ---- Toggle buttons row (Art, Shuffle, Repeat) ----
    toggle_w = (W - 4 - _BTN_GAP * 2) // 3
    tx0 = 2
    tx1 = tx0 + toggle_w + _BTN_GAP
    tx2 = tx1 + toggle_w + _BTN_GAP

    widgets.draw_button(draw, tx0, _TOGGLE_Y, toggle_w, _BTN_H,
                        'Art', font=fonts.SMALL,
                        inverted=snap.show_album_art)

    widgets.draw_button(draw, tx1, _TOGGLE_Y, toggle_w, _BTN_H,
                        'Shuffle', font=fonts.SMALL,
                        inverted=snap.shuffle)

    widgets.draw_button(draw, tx2, _TOGGLE_Y, W - tx2 - 2, _BTN_H,
                        'Repeat', font=fonts.SMALL,
                        inverted=snap.repeat)

    # ---- Separator ----
    draw.line([0, _SEP_Y, W - 1, _SEP_Y], fill=config.BLACK)

    # ---- Network list (connected network shown inverted) ----
    networks = snap.wifi_networks
    scroll   = max(0, min(snap.wifi_scroll, max(0, len(networks) - NET_VISIBLE)))
    scrollable = len(networks) > NET_VISIBLE

    if not networks:
        msg = 'No networks'
        draw.text((config.MARGIN, _LIST_TOP + 2), msg,
                  font=fonts.SMALL, fill=config.BLACK)
    else:
        row_w = W - widgets.SCROLL_W if scrollable else W

        for i in range(NET_VISIBLE):
            idx = i + scroll
            y = _LIST_TOP + i * _ROW_H
            if idx >= len(networks):
                break
            net = networks[idx]
            is_active = net.active

            font = fonts.BOLD if is_active else fonts.SMALL
            prefix = '* ' if is_active else '  '
            lock = '' if net.security == 'open' else ' [+]'

            sig_str = f'{net.signal}%{lock}'
            sig_w = widgets._text_w(sig_str, fonts.TINY)

            name_max = row_w - sig_w - 8
            label = prefix + widgets.truncate(
                net.ssid, font,
                name_max - widgets._text_w(prefix, font))

            widgets.draw_list_row(draw, 0, y, row_w, _ROW_H, '',
                                  inverted=is_active)
            fg = config.WHITE if is_active else config.BLACK
            draw.text((2, y + (_ROW_H - widgets._text_h(font)) // 2),
                      label, font=font, fill=fg)
            draw.text((row_w - sig_w - 2,
                       y + (_ROW_H - widgets._text_h(fonts.TINY)) // 2),
                      sig_str, font=fonts.TINY, fill=fg)

        # Scroll arrows
        if scrollable:
            list_bottom = _LIST_TOP + NET_VISIBLE * _ROW_H
            widgets.draw_scroll_arrows(
                draw, 0, _LIST_TOP, list_bottom, W,
                can_up=(scroll > 0),
                can_down=(scroll + NET_VISIBLE < len(networks)))

    # Status message below network list
    if snap.wifi_status:
        status_text = widgets.truncate(snap.wifi_status, fonts.TINY, W - 4)
        list_end_y = _LIST_TOP + min(len(networks), NET_VISIBLE) * _ROW_H
        draw.text((2, list_end_y + 1), status_text,
                  font=fonts.TINY, fill=config.BLACK)

    # ---- WiFi action buttons row (Scan, Hotspot) ----
    action_w = (W - 4 - _BTN_GAP) // 2
    ax0 = 2
    ax1 = ax0 + action_w + _BTN_GAP

    widgets.draw_button(draw, ax0, _ACTION_Y, action_w, _BTN_H,
                        'Scan', font=fonts.SMALL)
    widgets.draw_button(draw, ax1, _ACTION_Y, W - ax1 - 2, _BTN_H,
                        'Hotspot', font=fonts.SMALL)


# ------------------------------------------------------------------
# AP mode
# ------------------------------------------------------------------

def _draw_ap_mode(draw: ImageDraw, snap: AppState) -> None:
    W = config.DISPLAY_W

    M = config.MARGIN
    draw.text((M, 0), 'Connect phone to WiFi:', font=fonts.SMALL, fill=config.BLACK)

    ssid = config.WIFI_HOTSPOT_SSID
    draw.text((M, 13), ssid, font=fonts.TITLE, fill=config.BLACK)

    draw.text((M, 30), 'Password:', font=fonts.SMALL, fill=config.BLACK)
    draw.text((M, 42), config.WIFI_HOTSPOT_PASSWORD,
              font=fonts.BOLD, fill=config.BLACK)

    draw.text((M, 58), 'Then open in browser:', font=fonts.SMALL, fill=config.BLACK)
    url = f'http://{config.WIFI_PORTAL_IP}'
    draw.text((M, 70), url, font=fonts.BOLD, fill=config.BLACK)

    # Status
    if snap.wifi_status:
        draw.text((M, 86),
                  widgets.truncate(snap.wifi_status, fonts.TINY, W - M * 2),
                  font=fonts.TINY, fill=config.BLACK)

    # Stop button
    widgets.draw_button(draw, W - 82, _ACTION_Y, 80, _BTN_H,
                        'Stop Hotspot', font=fonts.SMALL, inverted=True)


# ------------------------------------------------------------------
# Hit regions
# ------------------------------------------------------------------

def _build_regions(snap: AppState) -> None:
    REGIONS.clear()
    W = config.DISPLAY_W

    if snap.wifi_ap_mode:
        REGIONS['wifi_ap_stop'] = (W - 82, _ACTION_Y, W - 2, _ACTION_Y + _BTN_H)
    else:
        # Toggle row
        toggle_w = (W - 4 - _BTN_GAP * 2) // 3
        tx0 = 2
        tx1 = tx0 + toggle_w + _BTN_GAP
        tx2 = tx1 + toggle_w + _BTN_GAP
        REGIONS['toggle_art']     = (tx0, _TOGGLE_Y,
                                     tx0 + toggle_w - 1, _TOGGLE_Y + _BTN_H)
        REGIONS['toggle_shuffle'] = (tx1, _TOGGLE_Y,
                                     tx1 + toggle_w - 1, _TOGGLE_Y + _BTN_H)
        REGIONS['toggle_repeat']  = (tx2, _TOGGLE_Y,
                                     W - 2, _TOGGLE_Y + _BTN_H)

        # Action row
        action_w = (W - 4 - _BTN_GAP) // 2
        ax0 = 2
        ax1 = ax0 + action_w + _BTN_GAP
        REGIONS['wifi_scan']     = (ax0, _ACTION_Y,
                                    ax0 + action_w - 1, _ACTION_Y + _BTN_H)
        REGIONS['wifi_ap_start'] = (ax1, _ACTION_Y,
                                    W - 2, _ACTION_Y + _BTN_H)

        # Network rows
        scroll = max(0, min(snap.wifi_scroll,
                            max(0, len(snap.wifi_networks) - NET_VISIBLE)))
        scrollable = len(snap.wifi_networks) > NET_VISIBLE
        row_hit_w = W - widgets.SCROLL_W if scrollable else W

        for i in range(min(NET_VISIBLE, len(snap.wifi_networks) - scroll)):
            idx = i + scroll
            y = _LIST_TOP + i * _ROW_H
            REGIONS[f'wifi_net_{idx}'] = (0, y, row_hit_w - 1, y + _ROW_H - 1)

        # Scroll arrow hit regions
        if scrollable:
            list_bottom = _LIST_TOP + NET_VISIBLE * _ROW_H
            up, down = widgets.scroll_hit_regions(
                0, _LIST_TOP, list_bottom, W)
            if scroll > 0:
                REGIONS['wifi_scroll_up'] = up
            if scroll + NET_VISIBLE < len(snap.wifi_networks):
                REGIONS['wifi_scroll_down'] = down
