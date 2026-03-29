# sonos-remote-eink

A physical Sonos controller built around a Raspberry Pi Zero 2W and a Waveshare 2.13" Touch e-Paper HAT (or compatible, e.g. ABKN) — 250×122 px, black & white. Browse now-playing info, manage the queue, group speakers, and configure WiFi — all from a low-power, always-on e-ink touchscreen.

---

## Hardware

| Component | Details |
|-----------|---------|
| SBC | Raspberry Pi Zero 2W, Zero W, 3B/3B+, 4B, or 5 — any model with a 40-pin GPIO header |
| Display | Waveshare 2.13" Touch e-Paper HAT (or compatible) — 250×122 px, B/W, SPI (EPD) + I2C (GT1151 touch) |
| Connection | 40-pin header (HAT form factor) |

### Pin assignments (BCM, per Waveshare schematic)

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

---

## Recommended OS

**Raspberry Pi OS Lite (64-bit), Bookworm** — the headless variant (no desktop).

- Smaller footprint; more RAM and CPU available for the application.
- Includes Python 3.11, pip, and GPIO libraries out of the box.
- Use the [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to flash the SD card. Under *Advanced Options*:
  - Set hostname, enable SSH, and pre-configure WiFi credentials.
- A desktop environment is not required and should not be installed.

---

## Quick start

```bash
# On the Pi (as the default 'pi' user):
git clone https://github.com/stigf/sonos-remote-eink.git
cd sonos-remote-eink
sudo bash install.sh
sudo reboot
```

The service starts on boot and automatically discovers Sonos speakers on the local network.

---

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

### 3. Clone the Waveshare Touch e-Paper HAT library

```bash
git clone --depth=1 \
  https://github.com/waveshareteam/Touch_e-Paper_HAT.git \
  /home/pi/Touch_e-Paper_HAT
```

The application expects the library at `/home/pi/Touch_e-Paper_HAT/python/TP_lib/`. If you place it elsewhere, update `WAVESHARE_LIB_PATH` in `config.py`. Make sure you clone the **Touch_e-Paper_HAT** repo — not the general e-Paper repo.

### 4. Install Python dependencies

```bash
sudo pip3 install --break-system-packages soco Pillow smbus2
```

### 5. Deploy the application

```bash
sudo cp -r . /opt/sonos-remote/
sudo chown -R pi:pi /opt/sonos-remote/
```

### 6. Install the systemd service

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
| `WIFI_HOTSPOT_SSID` | `SonosRemote-Setup` | Hotspot SSID for WiFi setup |
| `WIFI_HOTSPOT_PASSWORD` | `sonossetup` | Hotspot password |
| `WIFI_PORTAL_PORT` | `80` | Captive portal HTTP port |
| `WIFI_SCAN_INTERVAL` | `15.0` s | Background scan interval on the WiFi tab |

### Persistent settings

User preferences are stored in `/opt/sonos-remote/settings.json` and persist across reboots.

| Setting | Default | Description |
|---------|---------|-------------|
| `show_album_art` | `false` | Display dithered album art on the Now Playing screen |

Album art can be toggled from the WiFi tab via the **Art:ON / Art:OFF** button. The setting is saved immediately to disk.

### Touch coordinate calibration

The GT1151 reports coordinates in the display panel's native **portrait** orientation. The driver remaps them to landscape with:

```
landscape_x = touch_y
landscape_y = 122 - touch_x
```

If taps register in the wrong location (e.g. axes are swapped or inverted), adjust the remap in `hardware/touch.py` → `_scan()`.

---

## UI layout

The display is 250×122 px in landscape mode.

```
┌──────────────────────────────────────┐  y=0
│                                      │
│        Content area (250×106)        │
│                                      │
│                                      │  y=106
├─────────┬────────┬────────┬─────────┤
│  Play   │ Queue  │ Spkrs  │  WiFi   │  y=106–122 (tab bar)
└─────────┴────────┴────────┴─────────┘  y=122
```

### Tab 0 — Now Playing

Active mode (no album art):

```
Song Title (bold, truncated)
Artist Name
Album Name (smaller)
████████░░░░░░  0:42 / 3:15        ← progress bar
   [⏮]   [⏪]   [▶/⏸]   [⏩]   [⏭]   ← transport controls
VOL [████████░░░░░░░░░░] 72        ← shares slot with tab bar
```

Active mode (with album art):

```
┌──────┐ Song Title (bold, truncated)
│ ART  │ Artist Name
│48×48 │ Album Name (smaller)
└──────┘ ████████░░░  0:42 / 3:15
   [⏮]   [⏪]   [▶/⏸]   [⏩]   [⏭]
VOL [████████░░░░░░░░░░] 72
```

Idle mode shows a simplified display — no controls, no menu icon. With album art enabled, a larger 96×96 art image is shown on the left with track info beside it. Without art, track info is centred on screen.

A subtle menu icon (⋮) in the top-right corner opens the tab bar. The tab bar and volume bar share the same 16px slot at the bottom — only one is shown at a time.

### Tab 1 — Queue

```
| Favs (95px)   | Queue (154px)         |
|───────────────|───────────────────────|
| Radio 1       | > 3. Current Song     |  ← each row 15px
| My Playlist   |   4. Next Song        |
| Jazz FM       |   5. Another One      |
| ...           |   ...                 |
```

Tap a favourite to replace the queue and start playing it. Tap a queue item to jump to that position. Scroll by tapping near the top or bottom of each pane.

### Tab 2 — Speakers

```
■ Living Room   ████████░  42   ← coordinator (inverted row)
● Kitchen       ██████░░░  35   ← grouped member
○ Bedroom       ████░░░░░  20   ← ungrouped
○ Office        ████████░  55   ← ungrouped
```

**Indicators:**
- **■** Coordinator — the active/master speaker controlling playback
- **●** Grouped — member of the coordinator's zone group
- **○** Ungrouped — standalone speaker

**Touch actions:**
- Tap the **coordinator** row to switch the active speaker target
- Tap a **non-coordinator** speaker to toggle its group membership (join/unjoin the coordinator's zone group)

### Tab 3 — WiFi

Normal mode:

```
MyNetwork  192.168.1.42
████░  72%
────────────────────────────────────
* MyNetwork          92% [+]
  Neighbor-5G        78% [+]
  CoffeeShop         45% [+]
  OpenNetwork         20%
────────────────────────────────────
[Scan]                  [Setup AP]
```

AP mode (captive portal active):

```
Connect phone to WiFi:
SonosRemote-Setup
Password:
sonossetup
Then open in browser:
http://10.42.0.1
                          [Stop AP]
```

**How WiFi setup works:**

**Primary: on-screen keyboard.** Tap a secured network in the list and a full-screen QWERTY keyboard appears. Type the password and tap OK. The keyboard has shift, symbols (numbers + punctuation), delete, and cancel. Each key is ~25×22 px — small but usable for a one-time password entry.

```
WiFi: MyNetwork
[secretpass__|                    ]
[q][w][e][r][t][y][u][i][o][p]
  [a][s][d][f][g][h][j][k][l]
[ABC][z][x][c][v][b][n][m][DEL]
[?123][  SPACE  ][ CNCL ][  OK  ]
```

Open networks connect immediately on tap (no keyboard).

**Fallback: captive portal.** Tap **Setup AP** and the device starts a WiFi hotspot (`SonosRemote-Setup`). Connect your phone to it, open `http://10.42.0.1`, and enter the password in a web form. The device then connects to the chosen network. If it fails, the hotspot restarts for retry.

The hotspot SSID and password are configurable in `config.py`.

---

## Idle mode and refresh strategy

After 60 seconds of inactivity the device enters **idle mode**. There is no hardware sleep — e-ink is bi-stable, so the last-rendered image stays on screen drawing zero power.

| Mode | Triggers a display refresh |
|------|----------------------------|
| **Active** (user interacting) | Every Sonos poll (~2 s) — position, progress bar, volume |
| **Idle** (no touch for 60 s) | Only on **track change**, playback state change, or volume change — position ticks are ignored |

The display always reflects the currently playing track. When a song ends and the next begins, the screen refreshes with the new title, artist, and remaining time. Between refreshes the image is static.

Any touch instantly exits idle mode — there is no wake delay and no swallowed tap. The display resumes live updates immediately.

| Situation | Refresh type | Duration |
|-----------|-------------|----------|
| Tab switch | Full waveform | ~2 s (white flash) |
| Now-playing update (active) | Fast waveform | ~0.3 s |
| Track change (idle) | Fast waveform | ~0.3 s |
| After 10 fast refreshes | Automatic full clear | ~2 s |

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
├── config.py               # All hardware constants and layout dimensions
├── state.py                # AppState dataclass + thread-safe StateStore
├── events.py               # Simple publish/subscribe EventBus
├── settings.py             # Persistent JSON settings (album art toggle, etc.)
├── hardware/
│   ├── display.py          # Waveshare EPD wrapper (full/fast/partial refresh)
│   └── touch.py            # GT1151 I2C touch driver
├── sonos/
│   ├── client.py           # Stateless SoCo wrappers (incl. grouping)
│   └── poller.py           # Background Sonos polling thread (incl. album art)
├── wifi/
│   ├── manager.py          # nmcli wrappers (scan, connect, hotspot)
│   └── portal.py           # Captive portal HTTP server for password entry
├── ui/
│   ├── fonts.py            # Font loading (loaded once at startup)
│   ├── widgets.py          # Shared drawing primitives (truncation, etc.)
│   ├── renderer.py         # Render orchestrator (dirty-flag, hash dedup)
│   ├── keyboard.py         # Full-screen on-screen QWERTY keyboard
│   ├── tab_now_playing.py  # Now Playing tab (active + idle modes, album art)
│   ├── tab_queue.py        # Queue / Favourites tab
│   ├── tab_speakers.py     # Speaker selection & grouping tab
│   └── tab_wifi.py         # WiFi settings / captive portal setup tab
├── render_previews.py      # Generate preview PNGs of all UI states
├── run_portal.py           # Standalone captive portal runner (dev)
├── requirements.txt
├── install.sh
├── sonos-remote.service    # systemd unit file
└── LICENSE
```

---

## License

This project is licensed under the [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/).

- **Non-commercial use** is freely permitted — personal projects, hobby builds, education, research.
- **Commercial use** requires a separate license from the author.

See [LICENSE](LICENSE) for the full terms.
