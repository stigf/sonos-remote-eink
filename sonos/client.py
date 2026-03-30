# sonos/client.py — Stateless SoCo wrappers
#
# All functions accept a soco.SoCo device (coordinator).
# Network/SoCo errors are caught and logged; functions return None on failure.

import logging
from typing import Optional

import soco
import soco.exceptions

from state import QueueItem, Favourite, SpeakerInfo

logger = logging.getLogger(__name__)


def _safe(fn, *args, default=None, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        logger.warning('Sonos call failed: %s', exc)
        return default


# ------------------------------------------------------------------
# Discovery
# ------------------------------------------------------------------

def discover_speakers(timeout: float = 5.0,
                      coordinator_ip: str = None) -> list:
    """Return list[SpeakerInfo] for all discovered Sonos devices.

    If coordinator_ip is given, is_grouped is set for speakers that are
    members of that coordinator's zone group.
    """
    try:
        zones = soco.discover(timeout=timeout) or set()
    except Exception as exc:
        logger.error('Discovery failed: %s', exc)
        return []

    # Build set of UIDs in the coordinator's group
    grouped_uids = set()
    if coordinator_ip:
        for zone in zones:
            if zone.ip_address == coordinator_ip:
                try:
                    for member in zone.group.members:
                        grouped_uids.add(member.uid)
                except Exception:
                    grouped_uids.add(zone.uid)
                break

    result = []
    for zone in sorted(zones, key=lambda z: z.player_name):
        try:
            vol = zone.volume
        except Exception:
            vol = 0
        result.append(SpeakerInfo(
            uid=zone.uid,
            name=zone.player_name,
            ip=zone.ip_address,
            volume=vol,
            is_coordinator=(zone.ip_address == coordinator_ip),
            is_grouped=(zone.uid in grouped_uids),
        ))
    return result


def get_device_by_ip(ip: str) -> Optional[soco.SoCo]:
    try:
        return soco.SoCo(ip)
    except Exception:
        return None


# ------------------------------------------------------------------
# Now Playing
# ------------------------------------------------------------------

def get_track_info(device) -> Optional[dict]:
    """
    Returns dict with keys:
        title, artist, album, position_sec, duration_sec, playback_state, volume
    """
    try:
        info      = device.get_current_track_info()
        transport = device.get_current_transport_info()
        vol       = device.volume

        def _parse_time(t: str) -> int:
            """'H:MM:SS' or '' → seconds."""
            if not t:
                return 0
            parts = t.split(':')
            try:
                if len(parts) == 3:
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                if len(parts) == 2:
                    return int(parts[0]) * 60 + int(parts[1])
            except (ValueError, IndexError):
                pass
            return 0

        return {
            'title':          info.get('title', ''),
            'artist':         info.get('artist', ''),
            'album':          info.get('album', ''),
            'album_art_uri':  info.get('album_art_uri', ''),
            'position_sec':   _parse_time(info.get('position', '')),
            'duration_sec':   _parse_time(info.get('duration', '')),
            'playback_state': transport.get('current_transport_state', 'STOPPED'),
            'volume':         vol,
            'queue_position': max(0, int(info.get('playlist_position', 1)) - 1),
        }
    except Exception as exc:
        logger.warning('get_track_info failed: %s', exc)
        return None


# ------------------------------------------------------------------
# Play mode (shuffle / repeat)
# ------------------------------------------------------------------

def get_play_mode(device) -> Optional[dict]:
    """Return {'shuffle': bool, 'repeat': bool} from device play mode.

    SoCo play_mode values: NORMAL, SHUFFLE, REPEAT_ALL, SHUFFLE_REPEAT_ALL,
    SHUFFLE_NOREPEAT, REPEAT_ONE (ignored — we only support repeat-all).
    """
    try:
        mode = device.play_mode
        return {
            'shuffle': 'SHUFFLE' in mode,
            'repeat': 'REPEAT' in mode,
        }
    except Exception as exc:
        logger.warning('get_play_mode failed: %s', exc)
        return None


def set_play_mode(device, shuffle: bool, repeat: bool) -> None:
    """Set play mode from separate shuffle/repeat booleans."""
    if shuffle and repeat:
        mode = 'SHUFFLE_REPEAT_ALL'
    elif shuffle:
        mode = 'SHUFFLE_NOREPEAT'
    elif repeat:
        mode = 'REPEAT_ALL'
    else:
        mode = 'NORMAL'
    try:
        device.play_mode = mode
    except Exception as exc:
        logger.warning('set_play_mode failed: %s', exc)


# ------------------------------------------------------------------
# Queue & Favourites
# ------------------------------------------------------------------

def get_queue(device, max_items: int = 100) -> list:
    """Return list[QueueItem]."""
    try:
        raw = device.get_queue(max_items=max_items)
        result = []
        for i, item in enumerate(raw):
            result.append(QueueItem(
                index=i,
                title=getattr(item, 'title', '') or '',
                artist=getattr(item, 'creator', '') or '',
            ))
        return result
    except Exception as exc:
        logger.warning('get_queue failed: %s', exc)
        return []


def get_favourites(device) -> list:
    """Return list[Favourite] from Sonos Favourites."""
    try:
        raw = device.music_library.get_sonos_favorites(max_items=50)
        result = []
        for item in raw:
            result.append(Favourite(
                title=item.title or '',
                uri=item.get_uri() or '',
                meta=getattr(item, 'resource_meta_data', '') or '',
            ))
        return result
    except Exception as exc:
        logger.warning('get_favourites failed: %s', exc)
        return []


# ------------------------------------------------------------------
# Playback controls
# ------------------------------------------------------------------

def play(device):
    _safe(device.play)

def pause(device):
    _safe(device.pause)

def play_pause(device):
    try:
        state = device.get_current_transport_info()['current_transport_state']
        if state == 'PLAYING':
            device.pause()
        else:
            device.play()
    except Exception as exc:
        logger.warning('play_pause failed: %s', exc)

def next_track(device):
    _safe(device.next)

def prev_track(device):
    _safe(device.previous)

def set_volume(device, volume: int):
    vol = max(0, min(100, volume))
    _safe(setattr, device, 'volume', vol)

def volume_up(device, step: int = 5):
    try:
        device.volume = min(100, device.volume + step)
    except Exception as exc:
        logger.warning('volume_up failed: %s', exc)

def volume_down(device, step: int = 5):
    try:
        device.volume = max(0, device.volume - step)
    except Exception as exc:
        logger.warning('volume_down failed: %s', exc)


# ------------------------------------------------------------------
# Favourites & queue operations
# ------------------------------------------------------------------

def play_favourite(device, fav: Favourite):
    """Clear queue, add favourite, play."""
    try:
        device.clear_queue()
        device.add_uri_to_queue(fav.uri)
        device.play_from_queue(0)
    except Exception as exc:
        logger.warning('play_favourite failed: %s', exc)

def seek_to_queue_position(device, position: int):
    """Jump to 0-indexed queue position."""
    try:
        device.play_from_queue(position)
    except Exception as exc:
        logger.warning('seek_to_queue_position failed: %s', exc)


# ------------------------------------------------------------------
# Speaker grouping
# ------------------------------------------------------------------

def join_group(speaker_ip: str, coordinator_ip: str) -> bool:
    """Add a speaker to the coordinator's group. Returns True on success."""
    try:
        speaker = soco.SoCo(speaker_ip)
        coordinator = soco.SoCo(coordinator_ip)
        speaker.join(coordinator)
        logger.info('Joined %s to group of %s', speaker_ip, coordinator_ip)
        return True
    except Exception as exc:
        logger.warning('join_group failed: %s', exc)
        return False


def unjoin_speaker(speaker_ip: str) -> bool:
    """Remove a speaker from its current group. Returns True on success."""
    try:
        speaker = soco.SoCo(speaker_ip)
        speaker.unjoin()
        logger.info('Unjoined %s from group', speaker_ip)
        return True
    except Exception as exc:
        logger.warning('unjoin_speaker failed: %s', exc)
        return False


# ------------------------------------------------------------------
# Speaker volume (individual, not group-wide)
# ------------------------------------------------------------------

def get_speaker_volumes(ips: list) -> dict:
    """Return {ip: volume} for a list of speaker IPs."""
    result = {}
    for ip in ips:
        try:
            result[ip] = soco.SoCo(ip).volume
        except Exception:
            result[ip] = 0
    return result
