#!/usr/bin/env bash
# install.sh — Set up the Sonos e-ink remote on Raspberry Pi OS
#
# Run as: sudo bash install.sh
#
# Detects the invoking (non-root) user automatically. Override by running:
#   sudo TARGET_USER=myuser bash install.sh

set -euo pipefail

# --- Resolve the target user ---
# Prefer explicit TARGET_USER, then SUDO_USER (set by sudo), else fall back
# to the first real user in /home.
if [ -n "${TARGET_USER:-}" ]; then
    RUN_USER="$TARGET_USER"
elif [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
    RUN_USER="$SUDO_USER"
else
    RUN_USER="$(getent passwd | awk -F: '$3 >= 1000 && $3 < 65534 {print $1; exit}')"
fi

if [ -z "$RUN_USER" ] || ! id -u "$RUN_USER" >/dev/null 2>&1; then
    echo "ERROR: could not determine target user. Run with sudo TARGET_USER=<name> bash install.sh" >&2
    exit 1
fi

RUN_GROUP="$(id -gn "$RUN_USER")"
RUN_HOME="$(getent passwd "$RUN_USER" | cut -d: -f6)"

APP_DIR="/opt/sonos-remote"
WAVESHARE_DIR="$RUN_HOME/Touch_e-Paper_HAT"
SERVICE_NAME="sonos-remote"

echo "==> Installing for user: $RUN_USER ($RUN_GROUP), home: $RUN_HOME"

echo "==> Updating package lists"
apt-get update -qq

echo "==> Installing system dependencies"
apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    python3-pil \
    python3-rpi.gpio \
    python3-smbus \
    fonts-dejavu-core \
    git \
    avahi-daemon

echo "==> Enabling SPI and I2C interfaces"
raspi-config nonint do_spi 0
raspi-config nonint do_i2c 0

echo "==> Cloning Waveshare Touch e-Paper HAT library"
if [ -d "$WAVESHARE_DIR" ]; then
    echo "    Already exists — pulling latest"
    git -C "$WAVESHARE_DIR" pull --ff-only
else
    git clone --depth=1 \
        https://github.com/waveshareteam/Touch_e-Paper_HAT.git \
        "$WAVESHARE_DIR"
fi

echo "==> Installing Python dependencies"
pip3 install --break-system-packages --quiet \
    "soco>=0.30.0" \
    "Pillow>=10.0.0" \
    "smbus2>=0.4.3"

echo "==> Deploying application to $APP_DIR"
mkdir -p "$APP_DIR"
cp -r . "$APP_DIR/"
chown -R "$RUN_USER:$RUN_GROUP" "$APP_DIR"
chown -R "$RUN_USER:$RUN_GROUP" "$WAVESHARE_DIR"
chmod +x "$APP_DIR/main.py"

echo "==> Creating assets/fonts directory"
mkdir -p "$APP_DIR/assets/fonts"

echo "==> Installing systemd service (User=$RUN_USER, Group=$RUN_GROUP)"
SERVICE_DST="/etc/systemd/system/${SERVICE_NAME}.service"
sed -e "s/^User=.*/User=$RUN_USER/" \
    -e "s/^Group=.*/Group=$RUN_GROUP/" \
    "$APP_DIR/sonos-remote.service" > "$SERVICE_DST"
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"

echo ""
echo "Done. Reboot to start the remote, or run:"
echo "  sudo systemctl start ${SERVICE_NAME}"
echo ""
echo "View logs with:"
echo "  journalctl -u ${SERVICE_NAME} -f"
