# events.py — Simple synchronous publish/subscribe event bus

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# Event type constants
EVT_STATE_CHANGED  = 'state_changed'
EVT_TAB_CHANGED    = 'tab_changed'    # payload: int (tab index)
EVT_PLAY_PAUSE     = 'play_pause'
EVT_NEXT           = 'next'
EVT_PREV           = 'prev'
EVT_VOL_UP         = 'vol_up'
EVT_VOL_DOWN       = 'vol_down'
EVT_FAVOURITE      = 'favourite'      # payload: int (list index)
EVT_QUEUE_ITEM     = 'queue_item'     # payload: int (queue index)
EVT_SPEAKER        = 'speaker'        # payload: str (speaker uid)
EVT_SCROLL_UP      = 'scroll_up'      # payload: str ('fav' | 'queue')
EVT_SCROLL_DOWN    = 'scroll_down'    # payload: str ('fav' | 'queue')
EVT_TRACK_CHANGED  = 'track_changed'   # track title/state/volume changed (not just position)
EVT_WIFI_SCAN      = 'wifi_scan'
EVT_WIFI_AP_START  = 'wifi_ap_start'
EVT_WIFI_AP_STOP   = 'wifi_ap_stop'
EVT_WIFI_CONNECT   = 'wifi_connect'   # payload: (ssid, password)
EVT_TOGGLE_ART     = 'toggle_art'    # toggle album art display on/off
EVT_GROUP_TOGGLE   = 'group_toggle'  # payload: str (speaker IP) — join/unjoin


class EventBus:
    def __init__(self):
        self._listeners = defaultdict(list)

    def subscribe(self, event_type: str, callback) -> None:
        self._listeners[event_type].append(callback)

    def publish(self, event_type: str, payload=None) -> None:
        for cb in self._listeners[event_type]:
            try:
                cb(payload)
            except Exception as exc:
                logger.error('Event handler error for %s: %s',
                             event_type, exc)
