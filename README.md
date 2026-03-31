# sonos-remote-eink

A touch e-ink remote for Sonos, built with a Raspberry Pi and a 2.13" e-paper display. Control playback, browse the queue, group speakers, toggle shuffle and repeat, and configure WiFi — all from a low-power, always-on 250×122 px touchscreen.

Runs on any Raspberry Pi with WiFi and a 40-pin GPIO header (Zero 2W, Zero W, 3B/3B+, 4B, 5).

---

## Hardware

| Component | Details |
|-----------|---------|
| SBC | Any Raspberry Pi with WiFi and a 40-pin GPIO header |
| Display | Waveshare 2.13" Touch e-Paper HAT (or compatible, e.g. ABKN) — 250×122 px, B/W, SPI + I2C, HAT form factor |

### Pin assignments (BCM)

| Signal | GPIO |
|--------|------|
| EPD RST | 17 |
| EPD DC | 25 |
| EPD CS | 8 (CE0) |
| EPD BUSY | 24 |
| Touch INT | 27 |
| Touch RST | 16 |
| SPI MOSI | 10 |
| SPI CLK | 11 |
| I2C SDA | 2 |
| I2C SCL | 3 |

## Recommended OS

**Raspberry Pi OS Lite (64-bit), Bookworm** — the headless variant (no desktop).

- Smaller footprint; more RAM and CPU available for the application.
- Includes Python 3.11, pip, and GPIO libraries out of the box.
- Use the [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to flash the SD card. Under *Advanced Options*:
  - Set hostname, enable SSH, and pre-configure WiFi credentials.
- A desktop environment is not required and should not be installed.

## Quick start

```bash
# On the Pi (as the default 'pi' user):
git clone https://github.com/stigf/sonos-remote-eink.git
cd sonos-remote-eink
sudo bash install.sh
sudo reboot
```

The service starts on boot and automatically discovers Sonos speakers on the local network.

## Manual installation (step by step)

### 1. Enable SPI and I2C

```bash
sudo raspi-config
# → Interface Options → SPI → Enable
# → Interface Options → I2C → Enable
```

Or non-interactively:

```bash
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2c 0
```

### 2. Install system packages

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip fonts-dejavu-core git avahi-daemon
```

### 3. Clone the application

```bash
git clone https://github.com/stigf/sonos-remote-eink.git
cd sonos-remote-eink
```

### 4. Clone the Waveshare Touch e-Paper HAT library

```bash
git clone --depth=1 \
  https://github.com/waveshareteam/Touch_e-Paper_HAT.git \
  /home/pi/Touch_e-Paper_HAT
```

The application expects the library at `/home/pi/Touch_e-Paper_HAT/python/TP_lib/`. If you place it elsewhere, update `WAVESHARE_LIB_PATH` in `config.py`. Make sure you clone the **Touch_e-Paper_HAT** repo — not the general e-Paper repo.

### 5. Install Python dependencies

```bash
sudo pip3 install --break-system-packages soco Pillow smbus2
```

### 6. Deploy the application

```bash
sudo cp -r . /opt/sonos-remote/
sudo chown -R pi:pi /opt/sonos-remote/
```

### 7. Install the systemd service

```bash
sudo cp /opt/sonos-remote/sonos-remote.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sonos-remote
sudo systemctl start sonos-remote
```

---

## Configuration

All tunable constants live in **`config.py`**.

| Constant | Default | Description |
|----------|---------|-------------|
| `WAVESHARE_LIB_PATH` | `/home/pi/Touch_e-Paper_HAT/python/TP_lib` | Path to Waveshare EPD + GT1151 drivers |
| `SONOS_POLL_INTERVAL` | `2.0` s | Track info polling interval |
| `SONOS_FAV_POLL_INTERVAL` | `30.0` s | Favourites and speaker list polling interval |
| `IDLE_TIMEOUT_SEC` | `60` s | Inactivity timeout before entering idle mode |
| `FULL_REFRESH_EVERY` | `10` | Fast refreshes between full e-ink clears |
| `TOUCH_DEBOUNCE_SEC` | `0.25` s | Minimum interval between touch events |
| `WIFI_HOTSPOT_SSID` | `EinkRemote-Setup` | Hotspot SSID for WiFi setup |
| `WIFI_HOTSPOT_PASSWORD` | `einksetup` | Hotspot password |
| `WIFI_PORTAL_PORT` | `80` | Captive portal HTTP port |
| `WIFI_SCAN_INTERVAL` | `15.0` s | Background scan interval on the More tab |

### Persistent settings

User preferences are stored in `/opt/sonos-remote/settings.json` and persist across reboots.

| Setting | Default | Description |
|---------|---------|-------------|
| `show_album_art` | `false` | Display dithered album art on the Now Playing screen |

Album art can be toggled from the More tab via the **Art** button. The setting is saved immediately to disk.

Shuffle and repeat are also toggled from the More tab (**Shuffle**, **Repeat**). These control the Sonos play mode directly and are not persisted locally — they are read from the speaker on each poll.

### Touch coordinate calibration

The GT1151 reports coordinates in the display panel's native **portrait** orientation. The driver remaps them to landscape with:

```
landscape_x = touch_y
landscape_y = 122 - touch_x
```

If taps register in the wrong location (e.g. axes are swapped or inverted), adjust the remap in `hardware/touch.py` → `_scan()`.

---

## UI layout

The display is 250 x 122 px in landscape mode.

```
┌──────────────────────────────────────┐
│                                      │
│          Full canvas (250×122)       │
│                                      │
├──────────────────────────────────────┤
│   Play     Queue     Spkrs     More   │  ← tab bar overlaid on bottom 16 px
└──────────────────────────────────────┘
```

Content always renders at the full 250×122. The tab bar draws on top of the bottom 16 px. On the Now Playing tab the tab bar is hidden by default — a menu icon (⋮) in the top-right opens it; the volume bar occupies that space instead. Tap the Play tab to hide the tab bar and show volume again.

### Tab 0 — Now Playing

```
Title (bold, truncated)          ⋮
Artist
████████████░░░░░░░░░░░░░░░░░░░░░
1:18 / 2:10
  |◄    ||    ►|     −     +
████████████████░░░░░░░░░░░░░░ 42
```

Title, artist, full-width progress bar, timestamp, transport icons, and a volume bar at the bottom. When album art is enabled, a 48×48 dithered thumbnail appears top-left with text beside it; the progress bar is pushed below the art but still spans the full width. Long titles that would truncate at the large idle font automatically downsize to a smaller bold font to show more text.

**Idle mode** shows a simplified layout — no controls, no menu icon. With art enabled, a larger 96×96 image is shown with track info beside it. Without art, track info is centred using a large font.

### Tab 1 — Queue

```
Favs (115px)  │ Queue (134px)
──────────────┼───────────────
Madvillainy   │ The Illest Vi…
Mm..Food      │ Accordion
Operation: D… │ ▌All Caps
Piñata        │ Meat Grinder
Bandana       │ Bistro
Discover Wee… │ Raid
Lo-Fi Beats   │ America's Mo…
```

Favourites and queue side by side, 7 rows visible. The current track is shown inverted (white on black). Tap a favourite to start playing it. Tap a queue item to jump to that track. When either list overflows, ▲/▼ scroll arrows appear at the right edge.

### Tab 2 — Speakers

```
■ Living Room    ████████░░  42
● Kitchen        ██████░░░░  35
○ Bedroom        ████░░░░░░  20
○ Office         ████████░░  55
```

- **■** Coordinator — the active/master speaker
- **●** Grouped — member of the coordinator's group
- **○** Ungrouped — standalone speaker

Tap the coordinator to switch active speaker. Tap a non-coordinator to toggle group membership. When there are more than 4 speakers, ▲/▼ scroll arrows appear at the right edge.

### Tab 3 — More

```
[  Art  ] [Shuffle] [Repeat]
────────────────────────────────
* HomeNetwork          78% [+]
  Neighbor5G           45% [+]
  CoffeeShop              30%
  IoT-Network          62% [+]
[  Scan  ]         [Hotspot]
```

Toggle buttons for album art, shuffle, and repeat at the top — inverted (white on black) when active. Network list below (4 rows visible, connected network inverted). Tap a secured network to open the on-screen keyboard and enter a password. Open networks connect immediately.

**Fallback: captive portal.** Tap **Hotspot** to start a WiFi access point (`EinkRemote-Setup`). Connect a phone to it, open `http://10.42.0.1`, and enter credentials in a web form. The hotspot SSID and password are configurable in `config.py`.

---

## Idle mode and refresh strategy

After 60 seconds of inactivity the device enters **idle mode**. There is no hardware sleep — e-ink is bi-stable, so the last-rendered image stays on screen drawing zero power.

| Mode | Triggers a display refresh |
|------|----------------------------|
| **Active** (user interacting) | Every Sonos poll (~2 s) — position, progress bar, volume |
| **Idle** (no touch for 60 s) | Only on **track change**, playback state change, or volume change — position ticks are ignored |

The display always reflects the currently playing track. When a song ends and the next begins, the screen refreshes with the new info. Any touch instantly exits idle mode with no wake delay and no swallowed tap.

| Refresh type | When | Duration |
|-------------|------|----------|
| Full waveform | Tab switch, every 10th refresh | ~2 s (white flash) |
| Fast waveform | Now-playing updates, track changes | ~0.3 s |

---

## Troubleshooting

**Display shows nothing / stays white**
- Verify SPI is enabled: `ls /dev/spidev*` should list `/dev/spidev0.0`.
- Check that the HAT is seated firmly on the 40-pin header.
- Inspect logs: `journalctl -u sonos-remote -n 50`.

**Touch does not respond**
- Verify I2C is enabled: `i2cdetect -y 1` should show address `14`.
- Confirm `TOUCH_RST_PIN` and `TOUCH_INT_PIN` in `config.py` match your HAT revision.

**No Sonos devices found**
- The Pi must be on the same network and VLAN as the Sonos speakers.
- Sonos relies on multicast. Some routers block it between WiFi bands — try 2.4 GHz.
- Test discovery manually: `python3 -c "import soco; print(soco.discover())"`.

**Waveshare library import error**
- Make sure you cloned the **Touch_e-Paper_HAT** repo, not the general e-Paper repo.
- Verify the path in `config.py` → `WAVESHARE_LIB_PATH`.

---

## Project structure

```
sonos-remote-eink/
├── main.py                 # Entry point, event wiring, render loop
├── config.py               # Hardware constants and layout dimensions
├── state.py                # AppState dataclass + thread-safe StateStore
├── events.py               # Publish/subscribe EventBus
├── settings.py             # Persistent JSON settings
├── hardware/
│   ├── display.py          # Waveshare EPD wrapper (full/fast refresh)
│   └── touch.py            # GT1151 I2C touch driver
├── sonos/
│   ├── client.py           # Stateless SoCo wrappers (incl. grouping)
│   └── poller.py           # Background polling thread (incl. album art)
├── wifi/
│   ├── manager.py          # nmcli wrappers (scan, connect, hotspot)
│   └── portal.py           # Captive portal HTTP server
├── ui/
│   ├── fonts.py            # Font loading
│   ├── widgets.py          # Shared drawing primitives
│   ├── renderer.py         # Render orchestrator (dirty-flag, hash dedup)
│   ├── keyboard.py         # Full-screen on-screen QWERTY keyboard
│   ├── tab_now_playing.py  # Now Playing tab (active + idle, album art)
│   ├── tab_queue.py        # Queue / Favourites tab
│   ├── tab_speakers.py     # Speaker selection and grouping tab
│   └── tab_wifi.py         # More tab (WiFi, art, shuffle, repeat)
├── docs/                   # GitHub Pages website
├── render_previews.py      # Generate preview PNGs of all UI states
├── install.sh              # One-step installer
├── sonos-remote.service    # systemd unit file
├── requirements.txt
└── LICENSE
```

## License

This project is licensed under the [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/).

- **Non-commercial use** is freely permitted — personal projects, hobby builds, education, research.
- **Commercial use** requires a separate license from the author.

See [LICENSE](LICENSE) for the full terms.

---

This project is not affiliated with or endorsed by Sonos, Inc. Sonos is a trademark of Sonos, Inc.
