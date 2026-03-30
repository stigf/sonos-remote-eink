# state.py — Shared application state with thread-safe access

import copy
import threading
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class QueueItem:
    index: int      # 0-indexed position in Sonos queue
    title: str
    artist: str


@dataclass
class Favourite:
    title: str
    uri: str
    meta: str = ''


@dataclass
class SpeakerInfo:
    uid: str
    name: str
    ip: str
    volume: int = 0
    is_coordinator: bool = False
    is_grouped: bool = False      # in the active coordinator's group


@dataclass
class WifiNetwork:
    ssid: str
    signal: int           # 0-100
    security: str         # 'open', 'WPA', 'WPA2', etc.
    active: bool = False  # currently connected


@dataclass
class AppState:
    # UI
    active_tab: int = 0
    needs_full_refresh: bool = True
    idle_mode: bool = False
    show_tab_bar: bool = False        # Now Playing hides tab bar by default

    # Now Playing
    track_title: str = 'Loading...'
    track_artist: str = ''
    track_album: str = ''
    position_sec: int = 0
    duration_sec: int = 0
    playback_state: str = 'STOPPED'   # PLAYING | PAUSED_PLAYBACK | STOPPED
    volume: int = 0
    queue_position: int = 0           # 0-indexed
    album_art_img: Any = None         # PIL Image (mode 'L' greyscale) or None
    show_album_art: bool = False      # user setting: display album art
    shuffle: bool = False             # Sonos shuffle state
    repeat: bool = False              # Sonos repeat-all state

    # Lists
    queue: list = field(default_factory=list)        # list[QueueItem]
    favourites: list = field(default_factory=list)   # list[Favourite]
    speakers: list = field(default_factory=list)     # list[SpeakerInfo]
    active_speaker_ip: Optional[str] = None

    # Scroll offsets (list row index of topmost visible item)
    fav_scroll: int = 0
    queue_scroll: int = 0
    speaker_scroll: int = 0

    # Error display (None = no error)
    sonos_error: Optional[str] = None

    # WiFi
    wifi_ssid: str = ''               # current connected SSID
    wifi_ip: str = ''                 # current IP address
    wifi_signal: int = 0              # 0-100
    wifi_networks: list = field(default_factory=list)  # list[WifiNetwork]
    wifi_ap_mode: bool = False        # True while hotspot is active
    wifi_status: str = ''             # status message shown on WiFi tab
    wifi_scroll: int = 0              # scroll offset for network list

    # On-screen keyboard
    keyboard_active: bool = False
    keyboard_text: str = ''
    keyboard_target_ssid: str = ''    # SSID we're entering a password for
    keyboard_shift: bool = False
    keyboard_symbols: bool = False


class StateStore:
    """Thread-safe wrapper around AppState."""

    def __init__(self):
        self._state = AppState()
        self._lock = threading.Lock()

    def get_snapshot(self) -> AppState:
        """Return a shallow copy of the current state."""
        with self._lock:
            return copy.copy(self._state)

    def update(self, fn) -> None:
        """Call fn(state) while holding the lock to mutate state."""
        with self._lock:
            fn(self._state)
