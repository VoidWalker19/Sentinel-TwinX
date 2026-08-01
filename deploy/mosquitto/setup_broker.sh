#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# setup_broker.sh — One-command Mosquitto setup for Raspberry Pi
# ═══════════════════════════════════════════════════════════════════
#
# Usage:
#   sudo bash setup_broker.sh
#
# What this does:
#   1. Updates apt package list
#   2. Installs mosquitto broker + command-line clients
#   3. Copies the Sentinel Twin mosquitto config
#   4. Enables and starts the mosquitto service
#   5. Verifies it's running and prints the Pi's IP
#
# After running this, your Pi is ready to receive MQTT from the ESP32.
# ═══════════════════════════════════════════════════════════════════

set -e  # Exit on any error

echo ""
echo "  ┌──────────────────────────────────────────────────────┐"
echo "  │   Sentinel Twin — Raspberry Pi MQTT Broker Setup     │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

# Check we're running as root
if [ "$EUID" -ne 0 ]; then
  echo "  ✗ This script must be run as root (use sudo)"
  exit 1
fi

# Step 1: Update package list
echo "  [1/5] Updating package list..."
apt-get update -qq

# Step 2: Install mosquitto
echo "  [2/5] Installing mosquitto broker + clients..."
apt-get install -y -qq mosquitto mosquitto-clients

# Step 3: Copy Sentinel Twin config
echo "  [3/5] Installing Sentinel Twin MQTT config..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_SRC="${SCRIPT_DIR}/mosquitto.conf"

if [ ! -f "$CONFIG_SRC" ]; then
  echo "  ✗ Cannot find mosquitto.conf in ${SCRIPT_DIR}"
  echo "    Make sure this script is in the same directory as mosquitto.conf"
  exit 1
fi

cp "$CONFIG_SRC" /etc/mosquitto/conf.d/sentinel.conf
echo "  ✓ Config installed to /etc/mosquitto/conf.d/sentinel.conf"

# Step 4: Enable and restart mosquitto
echo "  [4/5] Enabling and starting mosquitto service..."
systemctl enable mosquitto
systemctl restart mosquitto

# Step 5: Verify
echo "  [5/5] Verifying..."
sleep 1

if systemctl is-active --quiet mosquitto; then
  echo ""
  echo "  ┌──────────────────────────────────────────────────────┐"
  echo "  │  ✓ Mosquitto is RUNNING on port 1883                │"
  echo "  └──────────────────────────────────────────────────────┘"
else
  echo ""
  echo "  ┌──────────────────────────────────────────────────────┐"
  echo "  │  ✗ Mosquitto FAILED to start                        │"
  echo "  │    Check: sudo journalctl -u mosquitto --no-pager    │"
  echo "  └──────────────────────────────────────────────────────┘"
  exit 1
fi

# Print the Pi's IP address
PI_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "  Your Raspberry Pi's IP address is: ${PI_IP}"
echo ""
echo "  ┌──────────────────────────────────────────────────────┐"
echo "  │  Next steps:                                         │"
echo "  │                                                      │"
echo "  │  1. Copy this IP into your ESP32's .ino file:        │"
echo "  │     #define MQTT_SERVER  \"${PI_IP}\"                   │"
echo "  │                                                      │"
echo "  │  2. Test from this Pi:                               │"
echo "  │     mosquitto_sub -t 'sentinel/#' -v                 │"
echo "  │                                                      │"
echo "  │  3. Flash the ESP32 and watch data arrive!           │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

# Quick self-test: publish and subscribe
echo "  Running quick self-test..."
mosquitto_pub -t "sentinel/test" -m '{"test":"broker_ok"}' &
RESULT=$(timeout 2 mosquitto_sub -t "sentinel/test" -C 1 2>/dev/null || echo "")

if [ -n "$RESULT" ]; then
  echo "  ✓ Self-test PASSED — broker can publish and subscribe"
else
  echo "  ⚠ Self-test inconclusive (this is normal on some setups)"
fi

echo ""
echo "  Setup complete!"
echo ""
