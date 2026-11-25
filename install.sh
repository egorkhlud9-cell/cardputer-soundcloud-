#!/bin/sh
set -eu

PACKAGE_URL="https://github.com/egorkhlud9-cell/cardputer-soundcloud-/releases/download/v2.0.0/soundcloud-cardputer_2.0.0_all.deb"
PACKAGE_FILE="/tmp/soundcloud-cardputer_2.0.0_all.deb"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this installer as root: curl ... | sudo bash" >&2
  exit 1
fi

ARCH="$(dpkg --print-architecture)"
if [ "$ARCH" != "arm64" ]; then
  echo "Unsupported architecture: $ARCH (this package is for ARM64/aarch64)." >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required to download the package. Install it with: sudo apt-get install curl" >&2
  exit 1
fi

echo "[1/3] Updating package index..."
apt-get update

echo "[2/3] Downloading prebuilt SoundCloud Cardputer 2.0.0..."
curl -fL --retry 3 --connect-timeout 20 "$PACKAGE_URL" -o "$PACKAGE_FILE"

echo "[3/3] Installing package and dependencies..."
apt-get install -y "$PACKAGE_FILE"
rm -f "$PACKAGE_FILE"

echo
echo "SoundCloud Cardputer AURORA 2.0 is installed."
echo "Open APPLaunch and select SoundCloud, or run: soundcloud-cardputer"
echo "No compilation or package building was performed on this device."
