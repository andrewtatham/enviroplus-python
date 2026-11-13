#!/bin/bash
# One-shot setup for a fresh Raspberry Pi OS Lite (Trixie/Bookworm) on a Pi Zero W.
# Run as the normal user (needs sudo). Safe to re-run.
set -euo pipefail

REPO_URL="https://github.com/andrewtatham/enviroplus-python.git"
APP_DIR="$HOME/enviroplus-python"
BOOT_CFG=/boot/firmware/config.txt
[ -f "$BOOT_CFG" ] || BOOT_CFG=/boot/config.txt

echo "== apt packages"
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    git python3-venv python3-dev build-essential i2c-tools \
    python3-rpi-lgpio python3-spidev python3-smbus2 python3-numpy python3-pil \
    libportaudio2 avahi-daemon libnss-mdns

echo "== enable I2C + SPI"
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_spi 0
# The Enviro+ LCD uses GPIO9 (SPI0 MISO) as its data/command pin and never reads
# from the display, so release MISO. Without this the gpiod-based st7735 library
# can't claim GPIO9. Replaces the plain dtparam=spi=on.
sudo sed -i 's/^dtparam=spi=on/dtoverlay=spi0-2cs,no_miso/' "$BOOT_CFG"
# Enviro+ microphone
grep -q '^dtoverlay=adau7002-simple' "$BOOT_CFG" || \
    echo 'dtoverlay=adau7002-simple' | sudo tee -a "$BOOT_CFG" >/dev/null

echo "== clone / update repo"
if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" pull --ff-only
else
    git clone "$REPO_URL" "$APP_DIR"
fi

echo "== python venv"
python3 -m venv --system-site-packages "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt" -r "$APP_DIR/requirements-pi.txt"

echo "== systemd unit (installed, NOT enabled until the HAT is fitted)"
sed -e "s|@USER@|$USER|g" -e "s|@APP_DIR@|$APP_DIR|g" \
    "$APP_DIR/deploy/enviro.service" | sudo tee /etc/systemd/system/enviro.service >/dev/null
sudo systemctl daemon-reload
echo "Enable with: sudo systemctl enable --now enviro"
