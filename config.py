# config.py — Hardware constants and layout dimensions

# --- Display ---
DISPLAY_W = 250         # landscape width (pixels)
DISPLAY_H = 122         # landscape height (pixels)
TAB_BAR_H = 16          # tab bar at bottom
CONTENT_H = DISPLAY_H - TAB_BAR_H  # 106px usable content height

# Physical panel native dimension (used for touch coordinate remapping)
DISPLAY_NATIVE_SHORT = 122   # portrait x-axis

# PIL color values for mode '1'
WHITE = 255
BLACK = 0

# --- GPIO pins (BCM numbering, per Waveshare Touch e-Paper HAT) ---
EPD_RST_PIN  = 17
EPD_DC_PIN   = 25
EPD_CS_PIN   = 8
EPD_BUSY_PIN = 24
TOUCH_INT_PIN = 27
TOUCH_RST_PIN = 16

# --- I2C (GT1151 touch controller) ---
TOUCH_I2C_BUS  = 1
TOUCH_I2C_ADDR = 0x14

# --- Waveshare library ---
# Clone https://github.com/waveshareteam/Touch_e-Paper_HAT to this path
WAVESHARE_LIB_PATH = '/home/pi/Touch_e-Paper_HAT/python/TP_lib'

# --- Polling intervals (seconds) ---
SONOS_POLL_INTERVAL     = 2.0
SONOS_FAV_POLL_INTERVAL = 30.0
TOUCH_POLL_INTERVAL     = 0.05   # 50 ms

# --- Touch ---
TOUCH_DEBOUNCE_SEC = 0.25
IDLE_TIMEOUT_SEC   = 60         # switch to idle mode (track-change-only updates)

# --- Refresh ---
# After this many fast refreshes, do a full refresh to clear ghosting
FULL_REFRESH_EVERY = 10

# --- Tabs ---
TAB_NAMES  = ['Play', 'Queue', 'Spkrs', 'Setup']
TAB_COUNT  = len(TAB_NAMES)
TAB_W      = DISPLAY_W // TAB_COUNT   # 62 px each (last tab gets remainder)

# --- WiFi ---
WIFI_SCAN_INTERVAL     = 15.0     # seconds between background scans
WIFI_ROW_H             = 15       # height of each network row
WIFI_HOTSPOT_SSID      = 'SonosRemote-Setup'
WIFI_HOTSPOT_PASSWORD   = 'sonossetup'
WIFI_PORTAL_PORT       = 80       # captive portal HTTP port
WIFI_PORTAL_IP         = '10.42.0.1'  # NM hotspot default IP

# --- Queue tab layout ---
FAV_PANE_W   = 95    # left pane: favourites
QUEUE_PANE_W = DISPLAY_W - FAV_PANE_W - 1   # right pane: queue (154 px)
LIST_ROW_H   = 15    # height of each list row
VISIBLE_ROWS = CONTENT_H // LIST_ROW_H       # ~7 rows

# --- Album art ---
ART_SIZE         = 48      # square album art in active mode
ART_IDLE_SIZE    = 96      # larger art in idle mode (more vertical space)
ART_X            = 2       # left edge
ART_Y            = 2       # top edge
ART_GAP          = 4       # gap between art and text

# --- Now Playing layout (within content area 250×106) ---
NP_TITLE_Y    = 2
NP_ARTIST_Y   = 18
NP_ALBUM_Y    = 30
NP_PROGRESS_Y = 42
NP_PROGRESS_H = 4
NP_CTRL_Y     = 68   # controls row top — pushed down for breathing room
NP_CTRL_H     = 28   # controls row height
NP_VOL_Y      = CONTENT_H   # volume sits at bottom — tab bar replaces it
NP_VOL_H      = TAB_BAR_H   # same height as tab bar (16px)

# Control button centres (x) and half-widths — evenly spaced across 250px
NP_BTN_PREV   = (25,  21)   # (x_center, half_w)
NP_BTN_PLAY   = (75,  21)
NP_BTN_NEXT   = (125, 21)
NP_BTN_VOLD   = (175, 21)
NP_BTN_VOLU   = (225, 21)
NP_BTN_HALF_H = 12   # all control buttons share this half-height

# Menu icon (top-right of Now Playing, opens tab bar)
MENU_ICON_X = 232
MENU_ICON_Y = 0
MENU_ICON_W = 18
MENU_ICON_H = 16
