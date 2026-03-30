#!/usr/bin/env python3
"""Render preview images of all tabs and Now Playing states."""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from PIL import Image
from state import AppState, QueueItem, Favourite, SpeakerInfo, WifiNetwork
import config
from ui import tab_now_playing, tab_queue, tab_speakers, tab_wifi, keyboard


def _art_to_greyscale(img):
    """Convert a PIL Image to greyscale, matching the poller's storage format.

    The 1-bit conversion (autocontrast → sharpen → dither) happens at render
    time in tab_now_playing._prepare_art(), after resizing to the display size.
    """
    return img.convert('L')


def _download_art(url, path):
    """Download an image if not already cached."""
    import urllib.request
    if os.path.isfile(path):
        return True
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        req = urllib.request.Request(url, headers={'User-Agent': 'SonosRemote/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        with open(path, 'wb') as f:
            f.write(data)
        print(f'  Downloaded → {os.path.basename(path)}')
        return True
    except Exception as exc:
        print(f'  Could not download {os.path.basename(path)}: {exc}')
        return False


def _load_album_arts():
    """Load both album covers. Returns (madvillainy_1bit, zombie_1bit)."""
    assets = os.path.join(os.path.dirname(__file__), 'assets')

    madvillainy_path = os.path.join(assets, 'album_art.png')
    zombie_path = os.path.join(assets, 'album_art_zombie.jpg')

    _download_art(
        'https://upload.wikimedia.org/wikipedia/en/5/5e/Madvillainy_cover.png',
        madvillainy_path)
    _download_art(
        'https://upload.wikimedia.org/wikipedia/en/f/f5/FelaZombie.jpg',
        zombie_path)

    def _load(path):
        if os.path.isfile(path):
            return _art_to_greyscale(Image.open(path))
        return Image.new('L', (200, 200), 128)

    return _load(madvillainy_path), _load(zombie_path)


def _base_snap():
    """Create a base AppState with realistic data."""
    snap = AppState()
    snap.track_title = 'All Caps'
    snap.track_artist = 'Madvillain'
    snap.track_album = 'Madvillainy'
    snap.position_sec = 78
    snap.duration_sec = 130
    snap.playback_state = 'PLAYING'
    snap.volume = 42
    snap.queue_position = 2
    snap.show_tab_bar = False
    snap.idle_mode = False
    snap.show_album_art = False
    snap.album_art_img = None
    snap.active_speaker_ip = '192.168.1.10'

    snap.queue = [
        QueueItem(index=0, title='The Illest Villains', artist='Madvillain'),
        QueueItem(index=1, title='Accordion', artist='Madvillain'),
        QueueItem(index=2, title='All Caps', artist='Madvillain'),
        QueueItem(index=3, title='Meat Grinder', artist='Madvillain'),
        QueueItem(index=4, title='Bistro', artist='Madvillain'),
        QueueItem(index=5, title='Raid', artist='Madvillain'),
        QueueItem(index=6, title="America's Most Blunted", artist='Madvillain'),
        QueueItem(index=7, title='Sickfit', artist='Madvillain'),
        QueueItem(index=8, title='Rhinestone Cowboy', artist='Madvillain'),
        QueueItem(index=9, title='Fancy Clown', artist='Madvillain'),
    ]

    snap.favourites = [
        Favourite(title='Madvillainy', uri='x-rincon:mv'),
        Favourite(title='Mm..Food', uri='x-rincon:mmf'),
        Favourite(title='Operation: Doomsday', uri='x-rincon:od'),
        Favourite(title='Piñata', uri='x-rincon:pin'),
        Favourite(title='Bandana', uri='x-rincon:ban'),
        Favourite(title='Discover Weekly', uri='x-rincon:dw'),
        Favourite(title='Lo-Fi Beats', uri='x-rincon:lfb'),
        Favourite(title='Jazz Vibes', uri='x-rincon:jv'),
    ]

    snap.speakers = [
        SpeakerInfo(uid='a1', name='Living Room', ip='192.168.1.10', volume=42, is_coordinator=True, is_grouped=True),
        SpeakerInfo(uid='a2', name='Kitchen', ip='192.168.1.11', volume=35, is_coordinator=False, is_grouped=True),
        SpeakerInfo(uid='a3', name='Bedroom', ip='192.168.1.12', volume=20, is_coordinator=False, is_grouped=False),
        SpeakerInfo(uid='a4', name='Office Speaker Pro Max', ip='192.168.1.13', volume=55, is_coordinator=False, is_grouped=False),
    ]

    snap.wifi_ssid = 'HomeNetwork'
    snap.wifi_ip = '192.168.1.100'
    snap.wifi_signal = 78
    snap.wifi_networks = [
        WifiNetwork(ssid='HomeNetwork', signal=78, security='WPA2', active=True),
        WifiNetwork(ssid='Neighbor5G', signal=45, security='WPA2', active=False),
        WifiNetwork(ssid='CoffeeShop', signal=30, security='open', active=False),
        WifiNetwork(ssid='IoT-Network', signal=62, security='WPA', active=False),
        WifiNetwork(ssid='GuestWiFi', signal=55, security='WPA2', active=False),
    ]

    return snap


def _save(img, name, out_dir):
    scaled = img.resize((img.width * 4, img.height * 4), Image.NEAREST)
    path = os.path.join(out_dir, f'{name}.png')
    scaled.save(path)
    print(f'  {name}.png')


def _fela_snap(zombie_art):
    """Create an AppState for Fela Kuti — Zombie with long title."""
    snap = _base_snap()
    snap.track_title = 'Mistake (Live at the Berlin Jazz Festival, 1978)'
    snap.track_artist = 'Fela Kuti'
    snap.track_album = 'Zombie'
    snap.position_sec = 312
    snap.duration_sec = 780
    snap.show_album_art = True
    snap.album_art_img = zombie_art
    return snap


def main():
    madvillainy_art, zombie_art = _load_album_arts()
    out_dir = os.path.join(os.path.dirname(__file__), 'previews')
    os.makedirs(out_dir, exist_ok=True)

    # Clean old previews
    for f in os.listdir(out_dir):
        if f.endswith('.png'):
            os.remove(os.path.join(out_dir, f))

    print('Now Playing — Active:')

    # 1. Active, no art
    snap = _base_snap()
    _save(tab_now_playing.render(snap), '01_active_no_art', out_dir)

    # 2. Active, with art (Madvillainy)
    snap = _base_snap()
    snap.show_album_art = True
    snap.album_art_img = madvillainy_art
    _save(tab_now_playing.render(snap), '02_active_with_art', out_dir)

    # 3. Active, with tab bar (Fela Kuti — long title, busy art)
    snap = _fela_snap(zombie_art)
    snap.show_tab_bar = True
    _save(tab_now_playing.render(snap), '03_active_art_tab_bar', out_dir)

    # 4. Active, no art, with tab bar
    snap = _base_snap()
    snap.show_tab_bar = True
    _save(tab_now_playing.render(snap), '04_active_tab_bar', out_dir)

    print('\nNow Playing — Idle:')

    # 5. Idle, no art (Fela Kuti — long title, no art shown)
    snap = _fela_snap(zombie_art)
    snap.idle_mode = True
    snap.show_album_art = False
    snap.album_art_img = None
    _save(tab_now_playing.render(snap), '05_idle_no_art', out_dir)

    # 6. Idle, with art (Madvillainy — simple cover)
    snap = _base_snap()
    snap.idle_mode = True
    snap.show_album_art = True
    snap.album_art_img = madvillainy_art
    _save(tab_now_playing.render(snap), '06_idle_with_art', out_dir)

    # 7. Idle, with art (Fela Kuti — busy cover, long title)
    snap = _fela_snap(zombie_art)
    snap.idle_mode = True
    _save(tab_now_playing.render(snap), '07_idle_busy_art', out_dir)

    print('\nNow Playing — Other states:')

    # 8. Active, paused
    snap = _base_snap()
    snap.playback_state = 'PAUSED_PLAYBACK'
    _save(tab_now_playing.render(snap), '08_active_paused', out_dir)

    # 9. Nothing playing
    snap = _base_snap()
    snap.track_title = ''
    snap.track_artist = ''
    snap.track_album = ''
    snap.position_sec = 0
    snap.duration_sec = 0
    snap.playback_state = 'STOPPED'
    snap.volume = 0
    _save(tab_now_playing.render(snap), '09_nothing_playing', out_dir)

    print('\nOther tabs:')

    # 10. Queue
    snap = _base_snap()
    snap.active_tab = 1
    _save(tab_queue.render(snap), '10_queue', out_dir)

    # 11a. Speakers (4 — no scroll)
    snap = _base_snap()
    snap.active_tab = 2
    _save(tab_speakers.render(snap), '11a_speakers', out_dir)

    # 11b. Speakers (6 — with scroll arrows)
    snap = _base_snap()
    snap.active_tab = 2
    snap.speakers = [
        SpeakerInfo(uid='a1', name='Living Room', ip='192.168.1.10', volume=42, is_coordinator=True, is_grouped=True),
        SpeakerInfo(uid='a2', name='Kitchen', ip='192.168.1.11', volume=35, is_coordinator=False, is_grouped=True),
        SpeakerInfo(uid='a3', name='Bedroom', ip='192.168.1.12', volume=20, is_coordinator=False, is_grouped=False),
        SpeakerInfo(uid='a4', name='Office Speaker Pro Max', ip='192.168.1.13', volume=55, is_coordinator=False, is_grouped=False),
        SpeakerInfo(uid='a5', name='Bathroom', ip='192.168.1.14', volume=30, is_coordinator=False, is_grouped=True),
        SpeakerInfo(uid='a6', name='Garage', ip='192.168.1.15', volume=10, is_coordinator=False, is_grouped=False),
    ]
    _save(tab_speakers.render(snap), '11b_speakers_scroll', out_dir)

    # 12. Settings (all toggles off)
    snap = _base_snap()
    snap.active_tab = 3
    _save(tab_wifi.render(snap), '12_settings_normal', out_dir)

    # 13. Settings (art on, shuffle on)
    snap = _base_snap()
    snap.active_tab = 3
    snap.show_album_art = True
    snap.shuffle = True
    _save(tab_wifi.render(snap), '13_settings_toggles', out_dir)

    # 14. Settings (AP mode)
    snap = _base_snap()
    snap.active_tab = 3
    snap.wifi_ap_mode = True
    snap.wifi_status = 'Hotspot active'
    _save(tab_wifi.render(snap), '14_settings_ap_mode', out_dir)

    print('\nKeyboard:')

    # 15. Keyboard (empty)
    snap = _base_snap()
    snap.keyboard_active = True
    snap.keyboard_target_ssid = 'HomeNetwork'
    snap.keyboard_text = ''
    snap.keyboard_shift = False
    snap.keyboard_symbols = False
    _save(keyboard.render(snap), '15_keyboard_empty', out_dir)

    # 16. Keyboard (typing)
    snap = _base_snap()
    snap.keyboard_active = True
    snap.keyboard_target_ssid = 'HomeNetwork'
    snap.keyboard_text = 'myP@ss'
    snap.keyboard_shift = False
    snap.keyboard_symbols = False
    _save(keyboard.render(snap), '16_keyboard_typing', out_dir)

    # 17. Keyboard (shift)
    snap = _base_snap()
    snap.keyboard_active = True
    snap.keyboard_target_ssid = 'HomeNetwork'
    snap.keyboard_text = 'myP@ss'
    snap.keyboard_shift = True
    snap.keyboard_symbols = False
    _save(keyboard.render(snap), '17_keyboard_shift', out_dir)

    # 18. Keyboard (symbols)
    snap = _base_snap()
    snap.keyboard_active = True
    snap.keyboard_target_ssid = 'HomeNetwork'
    snap.keyboard_text = 'myP@ss'
    snap.keyboard_shift = False
    snap.keyboard_symbols = True
    _save(keyboard.render(snap), '18_keyboard_symbols', out_dir)

    total = len([f for f in os.listdir(out_dir) if f.endswith('.png')])
    print(f'\nDone! {total} images in {out_dir}/')


if __name__ == '__main__':
    main()
