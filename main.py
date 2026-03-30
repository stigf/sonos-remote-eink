#!/usr/bin/env python3
# main.py — Entry point for the Sonos e-ink remote
#
# Wires hardware, state, events and Sonos together, then runs the render loop.

import logging
import sys
import threading
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

import config
import events as evt
import settings
from state import StateStore
from hardware.display import DisplayDriver
from hardware.touch import TouchDriver
from sonos import client as sonos_client
from sonos.poller import SonosPoller
from ui.renderer import Renderer
from ui import tab_now_playing, tab_queue, tab_speakers, tab_wifi, keyboard
from wifi import manager as wifi_mgr
from wifi import portal as wifi_portal


def main():
    logger.info('Starting Sonos e-ink remote')

    # ---- Hardware ----
    display = DisplayDriver()
    display.init()

    touch = TouchDriver()
    touch.init()

    # ---- State & events ----
    store = StateStore()
    bus   = evt.EventBus()

    # Load persistent settings into state
    store.update(lambda s: setattr(s, 'show_album_art',
                                   settings.get('show_album_art')))

    # ---- Sonos ----
    poller = SonosPoller(store, bus)

    # ---- UI ----
    renderer = Renderer(store, display)

    # ---- Wire events ----
    # Track changes always trigger a render (even in idle mode)
    bus.subscribe(evt.EVT_TRACK_CHANGED, renderer.mark_dirty)
    bus.subscribe(evt.EVT_TAB_CHANGED,   renderer.mark_dirty)

    # Position ticks only trigger a render when NOT idle
    def _on_state_changed(_payload):
        snap = store.get_snapshot()
        if not snap.idle_mode:
            renderer.mark_dirty()

    bus.subscribe(evt.EVT_STATE_CHANGED, _on_state_changed)

    # All Sonos actions route through the poller
    _action_events = [
        evt.EVT_PLAY_PAUSE, evt.EVT_NEXT, evt.EVT_PREV,
        evt.EVT_VOL_UP, evt.EVT_VOL_DOWN,
        evt.EVT_FAVOURITE, evt.EVT_QUEUE_ITEM, evt.EVT_SPEAKER,
        evt.EVT_GROUP_TOGGLE,
    ]
    for event_type in _action_events:
        _action = event_type   # capture in closure
        bus.subscribe(_action,
                      lambda payload, a=_action: poller.handle_action(a, payload))

    # ---- WiFi events ----
    bus.subscribe(evt.EVT_WIFI_SCAN,
                  lambda _: _wifi_scan(store, bus))
    bus.subscribe(evt.EVT_WIFI_AP_START,
                  lambda _: _wifi_start_ap(store, bus))
    bus.subscribe(evt.EVT_WIFI_AP_STOP,
                  lambda _: _wifi_stop_ap(store, bus))

    # ---- Album art toggle ----
    def _on_toggle_art(_payload):
        snap = store.get_snapshot()
        new_val = not snap.show_album_art
        settings.set('show_album_art', new_val)
        def _update(s):
            s.show_album_art = new_val
            # Clear cached art so toggling ON triggers a fresh fetch
            if not new_val:
                s.album_art_img = None
            s.needs_full_refresh = True
        store.update(_update)
        bus.publish(evt.EVT_STATE_CHANGED)

    bus.subscribe(evt.EVT_TOGGLE_ART, _on_toggle_art)

    # ---- Shuffle toggle ----
    def _on_toggle_shuffle(_payload):
        snap = store.get_snapshot()
        new_shuffle = not snap.shuffle
        device = sonos_client.get_device_by_ip(snap.active_speaker_ip)
        if device:
            sonos_client.set_play_mode(device, new_shuffle, snap.repeat)
        store.update(lambda s: setattr(s, 'shuffle', new_shuffle))
        bus.publish(evt.EVT_STATE_CHANGED)

    bus.subscribe(evt.EVT_TOGGLE_SHUFFLE, _on_toggle_shuffle)

    # ---- Repeat toggle ----
    def _on_toggle_repeat(_payload):
        snap = store.get_snapshot()
        new_repeat = not snap.repeat
        device = sonos_client.get_device_by_ip(snap.active_speaker_ip)
        if device:
            sonos_client.set_play_mode(device, snap.shuffle, new_repeat)
        store.update(lambda s: setattr(s, 'repeat', new_repeat))
        bus.publish(evt.EVT_STATE_CHANGED)

    bus.subscribe(evt.EVT_TOGGLE_REPEAT, _on_toggle_repeat)

    # ---- Touch handler ----
    _last_activity = [time.monotonic()]

    def on_touch(x: int, y: int):
        now = time.monotonic()
        _last_activity[0] = now

        snap = store.get_snapshot()

        # Exit idle mode on any touch — no swallowed tap, instant response
        if snap.idle_mode:
            store.update(lambda s: setattr(s, 'idle_mode', False))
            renderer.mark_dirty()   # redraw with live position info

        # Keyboard intercepts all touches when active
        if snap.keyboard_active:
            _hit_keyboard(x, y, snap, bus, store)
            return

        _dispatch_touch(x, y, snap, bus, store)

    touch.set_handler(on_touch)
    touch.start()

    # ---- Initial WiFi state ----
    _wifi_scan(store, bus)

    # ---- Start polling ----
    poller.start()

    # ---- WiFi background scan thread ----
    _wifi_scan_running = [True]

    def _wifi_scan_loop():
        import time as _t
        while _wifi_scan_running[0]:
            _t.sleep(config.WIFI_SCAN_INTERVAL)
            snap = store.get_snapshot()
            # Only auto-scan when WiFi tab is active and not in AP mode
            if snap.active_tab == 3 and not snap.wifi_ap_mode:
                _wifi_scan(store, bus)

    wifi_scan_thread = threading.Thread(
        target=_wifi_scan_loop, name='wifi-scan', daemon=True)
    wifi_scan_thread.start()

    # ---- Render loop ----
    logger.info('Entering render loop')
    try:
        while True:
            renderer.render_if_dirty()

            # Idle mode management — no hardware sleep, just stop
            # refreshing on position ticks.  Track changes still render.
            idle_secs = time.monotonic() - _last_activity[0]
            snap = store.get_snapshot()
            if idle_secs >= config.IDLE_TIMEOUT_SEC and not snap.idle_mode:
                logger.info('Entering idle mode (track-change updates only)')
                def _enter_idle(s):
                    s.idle_mode = True
                    s.active_tab = 0          # return to Now Playing
                    s.show_tab_bar = False
                    s.needs_full_refresh = True
                store.update(_enter_idle)
                renderer.mark_dirty()

            time.sleep(0.05)

    except KeyboardInterrupt:
        logger.info('Shutting down')
    finally:
        _wifi_scan_running[0] = False
        wifi_portal.stop()
        wifi_mgr.stop_hotspot()
        poller.stop()
        touch.stop()
        display.sleep()


# ------------------------------------------------------------------
# Touch dispatcher — maps (x, y) to EventBus events
# ------------------------------------------------------------------

def _dispatch_touch(x: int, y: int, snap, bus, store) -> None:
    # Tab bar is visible on non-NowPlaying tabs, or NowPlaying with show_tab_bar
    has_tab_bar = (snap.active_tab != 0) or snap.show_tab_bar

    # ---- Tab bar ----
    if has_tab_bar and y >= config.CONTENT_H:
        tab = x // config.TAB_W
        tab = min(tab, config.TAB_COUNT - 1)
        if tab != snap.active_tab:
            def _switch(s):
                s.active_tab = tab
                s.needs_full_refresh = True
                # Arriving at Now Playing hides the tab bar
                if tab == 0:
                    s.show_tab_bar = False
            store.update(_switch)
            bus.publish(evt.EVT_TAB_CHANGED, tab)
        else:
            # Tapped the already-active tab on Now Playing — hide tab bar
            if tab == 0 and snap.show_tab_bar:
                def _hide_tabs(s):
                    s.show_tab_bar = False
                    s.needs_full_refresh = True
                store.update(_hide_tabs)
                bus.publish(evt.EVT_STATE_CHANGED)
        return

    # ---- Content area — delegate to active tab's regions ----
    if snap.active_tab == 0:
        _hit_now_playing(x, y, snap, bus, store)
    elif snap.active_tab == 1:
        _hit_queue(x, y, snap, bus, store)
    elif snap.active_tab == 2:
        _hit_speakers(x, y, snap, bus)
    elif snap.active_tab == 3:
        _hit_wifi(x, y, snap, bus, store)


def _hit_now_playing(x: int, y: int, snap, bus, store) -> None:
    for action, (x0, y0, x1, y1) in tab_now_playing.REGIONS.items():
        if x0 <= x <= x1 and y0 <= y <= y1:
            if action == 'menu':
                # Toggle tab bar visibility
                def _show_tabs(s):
                    s.show_tab_bar = True
                    s.needs_full_refresh = True
                store.update(_show_tabs)
                bus.publish(evt.EVT_STATE_CHANGED)
            else:
                bus.publish(action)
            return


def _hit_queue(x: int, y: int, snap, bus, store) -> None:
    for key, (x0, y0, x1, y1) in tab_queue.REGIONS.items():
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            continue
        if key.startswith('fav_'):
            idx = int(key[4:])
            bus.publish(evt.EVT_FAVOURITE, idx)
        elif key.startswith('queue_'):
            idx = int(key[6:])
            bus.publish(evt.EVT_QUEUE_ITEM, idx)
        elif key == 'scroll_fav_down':
            store.update(lambda s: setattr(s, 'fav_scroll',
                         min(s.fav_scroll + 1,
                             max(0, len(s.favourites) - config.VISIBLE_ROWS))))
            bus.publish(evt.EVT_STATE_CHANGED)
        elif key == 'scroll_fav_up':
            store.update(lambda s: setattr(s, 'fav_scroll', max(0, s.fav_scroll - 1)))
            bus.publish(evt.EVT_STATE_CHANGED)
        elif key == 'scroll_queue_down':
            store.update(lambda s: setattr(s, 'queue_scroll',
                         min(s.queue_scroll + 1,
                             max(0, len(s.queue) - config.VISIBLE_ROWS))))
            bus.publish(evt.EVT_STATE_CHANGED)
        elif key == 'scroll_queue_up':
            store.update(lambda s: setattr(s, 'queue_scroll',
                         max(0, s.queue_scroll - 1)))
            bus.publish(evt.EVT_STATE_CHANGED)
        return


def _hit_speakers(x: int, y: int, snap, bus) -> None:
    for key, (x0, y0, x1, y1) in tab_speakers.REGIONS.items():
        if x0 <= x <= x1 and y0 <= y <= y1 and key.startswith('speaker_'):
            uid = key[len('speaker_'):]
            # Find speaker for this uid
            for sp in snap.speakers:
                if sp.uid == uid:
                    if sp.is_coordinator:
                        # Tapping coordinator switches active speaker
                        bus.publish(evt.EVT_SPEAKER, sp.ip)
                    else:
                        # Tapping non-coordinator toggles group membership
                        bus.publish(evt.EVT_GROUP_TOGGLE, sp.ip)
                    return


def _hit_wifi(x: int, y: int, snap, bus, store) -> None:
    for key, (x0, y0, x1, y1) in tab_wifi.REGIONS.items():
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            continue
        if key == 'wifi_scan':
            bus.publish(evt.EVT_WIFI_SCAN)
        elif key == 'toggle_art':
            bus.publish(evt.EVT_TOGGLE_ART)
        elif key == 'toggle_shuffle':
            bus.publish(evt.EVT_TOGGLE_SHUFFLE)
        elif key == 'toggle_repeat':
            bus.publish(evt.EVT_TOGGLE_REPEAT)
        elif key == 'wifi_ap_start':
            bus.publish(evt.EVT_WIFI_AP_START)
        elif key == 'wifi_ap_stop':
            bus.publish(evt.EVT_WIFI_AP_STOP)
        elif key.startswith('wifi_net_'):
            idx = int(key[len('wifi_net_'):])
            if idx < len(snap.wifi_networks):
                net = snap.wifi_networks[idx]
                if net.security == 'open':
                    # Open network: connect directly
                    threading.Thread(
                        target=lambda: _wifi_connect_direct(net.ssid, store, bus),
                        daemon=True,
                    ).start()
                else:
                    # Secured network: open keyboard for password
                    def _open_kb(s):
                        s.keyboard_active = True
                        s.keyboard_text = ''
                        s.keyboard_target_ssid = net.ssid
                        s.keyboard_shift = False
                        s.keyboard_symbols = False
                        s.needs_full_refresh = True
                    store.update(_open_kb)
                    bus.publish(evt.EVT_STATE_CHANGED)
        elif key == 'wifi_scroll_up':
            store.update(lambda s: setattr(s, 'wifi_scroll',
                         max(0, s.wifi_scroll - 1)))
            bus.publish(evt.EVT_STATE_CHANGED)
        elif key == 'wifi_scroll_down':
            store.update(lambda s: setattr(s, 'wifi_scroll',
                         min(s.wifi_scroll + 1,
                             max(0, len(s.wifi_networks) - tab_wifi._VISIBLE_ROWS))))
            bus.publish(evt.EVT_STATE_CHANGED)
        return


def _hit_keyboard(x: int, y: int, snap, bus, store) -> None:
    """Handle touch events on the on-screen keyboard."""
    for key, (x0, y0, x1, y1) in keyboard.REGIONS.items():
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            continue

        if key.startswith('char_'):
            ch = key[5:]   # the typed character
            store.update(lambda s: setattr(s, 'keyboard_text', s.keyboard_text + ch))
            # Auto-disable shift after one character (like a phone keyboard)
            store.update(lambda s: setattr(s, 'keyboard_shift', False))

        elif key == 'space':
            store.update(lambda s: setattr(s, 'keyboard_text', s.keyboard_text + ' '))

        elif key == 'del':
            store.update(lambda s: setattr(s, 'keyboard_text', s.keyboard_text[:-1]))

        elif key == 'shift':
            store.update(lambda s: setattr(s, 'keyboard_shift', not s.keyboard_shift))

        elif key == 'mode':
            store.update(lambda s: setattr(s, 'keyboard_symbols', not s.keyboard_symbols))

        elif key == 'cancel':
            def _close(s):
                s.keyboard_active = False
                s.keyboard_text = ''
                s.needs_full_refresh = True
            store.update(_close)

        elif key == 'ok':
            ssid = snap.keyboard_target_ssid
            password = snap.keyboard_text
            # Close keyboard
            def _close(s):
                s.keyboard_active = False
                s.keyboard_text = ''
                s.wifi_status = f'Connecting to {ssid}...'
                s.needs_full_refresh = True
            store.update(_close)
            # Connect in background
            threading.Thread(
                target=lambda: _wifi_connect_direct(ssid, store, bus, password),
                daemon=True,
            ).start()

        bus.publish(evt.EVT_STATE_CHANGED)
        return


# ------------------------------------------------------------------
# WiFi helpers
# ------------------------------------------------------------------

def _wifi_scan(store, bus):
    """Scan networks and update state."""
    networks = wifi_mgr.scan_networks()
    conn = wifi_mgr.get_current_connection()

    def _update(s):
        s.wifi_networks = networks
        s.wifi_ssid     = conn.get('ssid', '')
        s.wifi_ip       = conn.get('ip', '')
        s.wifi_signal   = conn.get('signal', 0)

    store.update(_update)
    bus.publish(evt.EVT_STATE_CHANGED)


def _wifi_connect_direct(ssid, store, bus, password=None):
    """Connect to a network directly (called from a background thread)."""
    store.update(lambda s: setattr(s, 'wifi_status', f'Connecting to {ssid}...'))
    bus.publish(evt.EVT_STATE_CHANGED)

    ok, msg = wifi_mgr.connect(ssid, password)
    store.update(lambda s: setattr(s, 'wifi_status', msg))
    bus.publish(evt.EVT_STATE_CHANGED)

    # Refresh connection info
    _wifi_scan(store, bus)


def _wifi_start_ap(store, bus):
    """Start hotspot + captive portal."""
    store.update(lambda s: setattr(s, 'wifi_status', 'Starting hotspot...'))
    bus.publish(evt.EVT_STATE_CHANGED)

    ok, ip = wifi_mgr.start_hotspot()
    if ok:
        wifi_portal.start(store=store, bus=bus)
        def _update(s):
            s.wifi_ap_mode = True
            s.wifi_status = 'Hotspot active'
            s.needs_full_refresh = True
        store.update(_update)
    else:
        store.update(lambda s: setattr(s, 'wifi_status', 'Failed to start hotspot'))

    bus.publish(evt.EVT_STATE_CHANGED)


def _wifi_stop_ap(store, bus):
    """Stop hotspot + captive portal."""
    wifi_portal.stop()
    wifi_mgr.stop_hotspot()

    def _update(s):
        s.wifi_ap_mode = False
        s.wifi_status = 'Hotspot stopped'
        s.needs_full_refresh = True

    store.update(_update)
    bus.publish(evt.EVT_STATE_CHANGED)

    # Re-scan to pick up current connection
    _wifi_scan(store, bus)


if __name__ == '__main__':
    main()
