#!/usr/bin/env bash
# install.sh — Set up the Sonos e-ink remote on Raspberry Pi OS
#
# Run as: sudo bash install.sh

set -euo pipefail

APP_DIR="/opt/sonos-remote"
WAVESHARE_DIR="/home/pi/Touch_e-Paper_HAT"
SERVICE_NAME="sonos-remote"

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
chown -R pi:pi "$APP_DIR"
chmod +x "$APP_DIR/main.py"

echo "==> Creating assets/fonts directory"
mkdir -p "$APP_DIR/assets/fonts"

echo "==> Installing systemd service"
cp "$APP_DIR/sonos-remote.service" "/etc/systemd/system/${SERVICE_NAME}.service"
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"

echo ""
echo "Done. Reboot to start the remote, or run:"
echo "  sudo systemctl start ${SERVICE_NAME}"
echo ""
echo "View logs with:"
echo "  journalctl -u ${SERVICE_NAME} -f"
