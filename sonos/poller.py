# sonos/poller.py — Background thread that keeps AppState in sync with Sonos

import io
import logging
import threading
import time
import urllib.request
from typing import Optional

from PIL import Image

import config
import soco
from events import EVT_STATE_CHANGED, EVT_TRACK_CHANGED
from sonos import client

logger = logging.getLogger(__name__)


class SonosPoller:
    """
    Polls the active Sonos coordinator on a background daemon thread.

    - Track info / transport state: every SONOS_POLL_INTERVAL seconds
    - Queue: every SONOS_POLL_INTERVAL seconds (only when tab 1 is active)
    - Favourites & speaker list: every SONOS_FAV_POLL_INTERVAL seconds
    """

    def __init__(self, store, bus):
        self._store = store
        self._bus   = bus
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._device: Optional[soco.SoCo] = None
        self._fav_timer = 0.0
        self._art_cache_uri: str = ''       # last fetched album_art_uri

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        self._running = True
        self._thread = threading.Thread(
            target=self._run, name='sonos-poll', daemon=True
        )
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)

    # ------------------------------------------------------------------
    # Device access
    # ------------------------------------------------------------------

    def _get_device(self) -> Optional[soco.SoCo]:
        """Return the active coordinator device, re-discovering if needed."""
        snap = self._store.get_snapshot()
        if snap.active_speaker_ip:
            if self._device and self._device.ip_address == snap.active_speaker_ip:
                return self._device
            self._device = client.get_device_by_ip(snap.active_speaker_ip)
            return self._device
        # No speaker selected yet — use first discovered coordinator
        if self._device:
            return self._device
        return None

    def _discover_and_set(self):
        """Discover speakers and pick the first coordinator if none selected."""
        speakers = client.discover_speakers()
        if not speakers:
            self._store.update(lambda s: setattr(s, 'sonos_error', 'No Sonos found'))
            return

        def _update(s):
            s.speakers = speakers
            s.sonos_error = None
            if s.active_speaker_ip is None:
                coordinators = [sp for sp in speakers if sp.is_coordinator]
                target = coordinators[0] if coordinators else speakers[0]
                s.active_speaker_ip = target.ip

        self._store.update(_update)
        snap = self._store.get_snapshot()
        if snap.active_speaker_ip:
            self._device = client.get_device_by_ip(snap.active_speaker_ip)
        self._notify_changed()

    # ------------------------------------------------------------------
    # Poll loop
    # ------------------------------------------------------------------

    def _run(self):
        # Initial discovery
        self._discover_and_set()

        while self._running:
            self._poll_track_info()

            now = time.monotonic()
            if now - self._fav_timer >= config.SONOS_FAV_POLL_INTERVAL:
                self._poll_favourites_and_speakers()
                self._fav_timer = now

            # Poll queue only when that tab is visible
            snap = self._store.get_snapshot()
            if snap.active_tab == 1:
                self._poll_queue()

            time.sleep(config.SONOS_POLL_INTERVAL)

    # Fields that constitute a meaningful track change (not just a position tick)
    _IMPORTANT_KEYS = frozenset({
        'title', 'artist', 'album', 'playback_state', 'volume',
        'duration_sec', 'queue_position',
    })

    def _poll_track_info(self):
        device = self._get_device()
        if device is None:
            return

        info = client.get_track_info(device)
        if info is None:
            return

        changed = False
        track_changed = False

        def _update(s):
            nonlocal changed, track_changed
            for key in ('title', 'artist', 'album',
                        'position_sec', 'duration_sec', 'playback_state',
                        'volume', 'queue_position'):
                state_key = 'track_' + key if key in ('title', 'artist', 'album') else key
                old = getattr(s, state_key, None)
                new = info.get(key)
                if old != new:
                    setattr(s, state_key, new)
                    changed = True
                    if key in self._IMPORTANT_KEYS:
                        track_changed = True

        self._store.update(_update)

        # Poll play mode (shuffle / repeat)
        play_mode = client.get_play_mode(device)
        if play_mode is not None:
            def _update_play_mode(s):
                nonlocal changed, track_changed
                if s.shuffle != play_mode['shuffle']:
                    s.shuffle = play_mode['shuffle']
                    changed = True
                    track_changed = True
                if s.repeat != play_mode['repeat']:
                    s.repeat = play_mode['repeat']
                    changed = True
                    track_changed = True
            self._store.update(_update_play_mode)

        # Fetch album art if URI changed and setting is enabled
        snap = self._store.get_snapshot()
        art_uri = info.get('album_art_uri', '')
        if snap.show_album_art and art_uri:
            # Fetch if URI changed, or if art is enabled but image is missing
            # (e.g. art was just toggled on, or speaker was switched)
            if art_uri != self._art_cache_uri or snap.album_art_img is None:
                self._fetch_album_art(device, art_uri)
                track_changed = True  # art change is visually important
        elif not art_uri and self._art_cache_uri:
            # Track has no art — clear cache
            self._art_cache_uri = ''
            self._store.update(lambda s: setattr(s, 'album_art_img', None))
            track_changed = True

        if changed:
            self._notify_changed()
        if track_changed:
            self._notify_track_changed()

    def _fetch_album_art(self, device, art_uri: str) -> None:
        """Download album art from the Sonos speaker, store as greyscale."""
        try:
            # Build full URL — art_uri is typically like /getaa?s=1&u=...
            if art_uri.startswith('http'):
                url = art_uri
            else:
                url = f'http://{device.ip_address}:1400{art_uri}'

            req = urllib.request.Request(url, headers={'User-Agent': 'EinkRemote/1.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = resp.read()

            img = Image.open(io.BytesIO(data))
            # Store as greyscale — 1-bit dithering is done at render time
            # after resizing to the display size, so the dithering pattern
            # matches the final pixel grid.
            img = img.convert('L')

            self._art_cache_uri = art_uri
            self._store.update(lambda s: setattr(s, 'album_art_img', img))
            logger.debug('Fetched album art: %s', art_uri)

        except Exception as exc:
            logger.warning('Failed to fetch album art: %s', exc)
            self._art_cache_uri = art_uri  # don't retry same broken URI
            self._store.update(lambda s: setattr(s, 'album_art_img', None))

    def _poll_queue(self):
        device = self._get_device()
        if device is None:
            return
        queue = client.get_queue(device)
        changed = False

        def _update(s):
            nonlocal changed
            if s.queue != queue:
                s.queue = queue
                changed = True

        self._store.update(_update)
        if changed:
            self._notify_changed()

    def _poll_favourites_and_speakers(self):
        device = self._get_device()
        favs = client.get_favourites(device) if device else []
        snap = self._store.get_snapshot()
        speakers = client.discover_speakers(
            coordinator_ip=snap.active_speaker_ip)
        changed = False

        def _update(s):
            nonlocal changed
            if s.favourites != favs:
                s.favourites = favs
                changed = True
            if s.speakers != speakers:
                s.speakers = speakers
                changed = True

        self._store.update(_update)
        if changed:
            self._notify_changed()

    def _notify_changed(self):
        self._bus.publish(EVT_STATE_CHANGED)

    def _notify_track_changed(self):
        self._bus.publish(EVT_TRACK_CHANGED)

    # ------------------------------------------------------------------
    # Public action dispatcher (called from main thread via event handler)
    # ------------------------------------------------------------------

    def handle_action(self, action: str, payload=None):
        """Execute a Sonos action. Called by the main thread event handler."""
        device = self._get_device()
        if device is None:
            logger.warning('No active device for action: %s', action)
            return

        action_map = {
            'play_pause':    lambda: client.play_pause(device),
            'next':          lambda: client.next_track(device),
            'prev':          lambda: client.prev_track(device),
            'vol_up':        lambda: client.volume_up(device),
            'vol_down':      lambda: client.volume_down(device),
        }

        if action == 'favourite':
            snap = self._store.get_snapshot()
            if payload is not None and payload < len(snap.favourites):
                client.play_favourite(device, snap.favourites[payload])

        elif action == 'queue_item':
            if payload is not None:
                client.seek_to_queue_position(device, payload)

        elif action == 'speaker':
            # Switch active speaker — validate device before updating state
            if payload:
                new_device = client.get_device_by_ip(payload)
                if new_device is not None:
                    def _switch(s):
                        s.active_speaker_ip = payload
                        # Clear art so new speaker's art is fetched fresh
                        s.album_art_img = None
                    self._store.update(_switch)
                    self._device = new_device
                    self._art_cache_uri = ''
                else:
                    logger.warning('Invalid speaker IP: %s', payload)

        elif action == 'group_toggle':
            # Toggle speaker in/out of coordinator's group
            if payload:
                snap = self._store.get_snapshot()
                coord_ip = snap.active_speaker_ip
                # Find if this speaker is currently grouped
                is_grouped = False
                for sp in snap.speakers:
                    if sp.ip == payload:
                        is_grouped = sp.is_grouped
                        break
                if is_grouped:
                    client.unjoin_speaker(payload)
                else:
                    if coord_ip:
                        client.join_group(payload, coord_ip)
                # Re-poll speakers to update group state
                self._poll_favourites_and_speakers()

        elif action in action_map:
            action_map[action]()

        # Force immediate poll after action
        self._poll_track_info()
