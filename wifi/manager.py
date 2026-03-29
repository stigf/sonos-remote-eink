# wifi/manager.py — NetworkManager (nmcli) wrappers for WiFi management
#
# Requires Raspberry Pi OS Bookworm which uses NetworkManager by default.
# All operations shell out to nmcli for reliability and simplicity.

import logging
import re
import subprocess
from typing import Optional

import config
from state import WifiNetwork

logger = logging.getLogger(__name__)


def _run(cmd: list, timeout: float = 15.0) -> tuple:
    """Run a command, return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        logger.warning('Command timed out: %s', ' '.join(cmd))
        return -1, '', 'timeout'
    except FileNotFoundError:
        logger.warning('Command not found: %s', cmd[0])
        return -1, '', 'not found'


# ------------------------------------------------------------------
# Current connection
# ------------------------------------------------------------------

def get_current_connection() -> dict:
    """
    Returns {'ssid': str, 'ip': str, 'signal': int} or empty values.
    """
    result = {'ssid': '', 'ip': '', 'signal': 0}

    # Active SSID + signal
    rc, out, _ = _run(['nmcli', '-t', '-f', 'ACTIVE,SSID,SIGNAL', 'dev', 'wifi'])
    if rc == 0:
        for line in out.splitlines():
            # nmcli -t uses ':' as delimiter; SSIDs can contain ':'
            # Format: ACTIVE:SSID:SIGNAL — split from right to handle colons in SSID
            parts = line.split(':')
            if len(parts) >= 3 and parts[0] == 'yes':
                # Signal is always last, SSID is everything in between
                result['ssid'] = ':'.join(parts[1:-1])
                try:
                    result['signal'] = int(parts[-1])
                except ValueError:
                    pass
                break

    # IP address
    rc, out, _ = _run([
        'nmcli', '-t', '-f', 'IP4.ADDRESS', 'dev', 'show', 'wlan0'
    ])
    if rc == 0:
        for line in out.splitlines():
            if line.startswith('IP4.ADDRESS'):
                # Format: IP4.ADDRESS[1]:192.168.1.42/24
                match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                if match:
                    result['ip'] = match.group(1)
                break

    return result


# ------------------------------------------------------------------
# Scan
# ------------------------------------------------------------------

def scan_networks() -> list:
    """
    Scan for WiFi networks. Returns list[WifiNetwork], sorted by signal
    strength (strongest first). Duplicate SSIDs are de-duplicated.
    """
    rc, out, _ = _run([
        'nmcli', '-t', '-f', 'ACTIVE,SSID,SIGNAL,SECURITY',
        'dev', 'wifi', 'list', '--rescan', 'yes'
    ])
    if rc != 0:
        logger.warning('WiFi scan failed (rc=%d)', rc)
        return []

    seen = set()
    networks = []
    for line in out.splitlines():
        # Format: ACTIVE:SSID:SIGNAL:SECURITY — SSIDs can contain ':'
        # Split with limit: active is first, security is last, signal is
        # second-to-last, SSID is everything in between
        parts = line.split(':')
        if len(parts) < 4:
            continue
        active = parts[0] == 'yes'
        security = parts[-1] if parts[-1] else 'open'
        try:
            signal = int(parts[-2])
        except ValueError:
            signal = 0
        ssid = ':'.join(parts[1:-2])
        if not ssid or ssid in seen:
            continue
        seen.add(ssid)

        networks.append(WifiNetwork(
            ssid=ssid,
            signal=signal,
            security=security,
            active=active,
        ))

    networks.sort(key=lambda n: n.signal, reverse=True)
    return networks


# ------------------------------------------------------------------
# Connect
# ------------------------------------------------------------------

def connect(ssid: str, password: Optional[str] = None) -> tuple:
    """
    Connect to a WiFi network.
    Returns (success: bool, message: str).
    """
    cmd = ['nmcli', 'dev', 'wifi', 'connect', ssid]
    if password:
        cmd += ['password', password]

    rc, out, err = _run(cmd, timeout=30.0)
    if rc == 0:
        logger.info('Connected to %s', ssid)
        return True, f'Connected to {ssid}'
    else:
        msg = err or out or 'Connection failed'
        logger.warning('Failed to connect to %s: %s', ssid, msg)
        return False, msg


# ------------------------------------------------------------------
# Hotspot (AP mode)
# ------------------------------------------------------------------

def start_hotspot() -> tuple:
    """
    Start a WiFi hotspot for captive portal setup.
    Returns (success: bool, ip: str).
    """
    # Stop any existing hotspot first
    stop_hotspot()

    rc, out, err = _run([
        'nmcli', 'dev', 'wifi', 'hotspot',
        'ifname', 'wlan0',
        'ssid', config.WIFI_HOTSPOT_SSID,
        'password', config.WIFI_HOTSPOT_PASSWORD,
    ])
    if rc != 0:
        logger.error('Failed to start hotspot: %s', err or out)
        return False, ''

    logger.info('Hotspot started: %s', config.WIFI_HOTSPOT_SSID)
    return True, config.WIFI_PORTAL_IP


def stop_hotspot() -> bool:
    """Stop the hotspot and restore normal WiFi client mode."""
    rc, _, _ = _run(['nmcli', 'con', 'down', 'Hotspot'])
    if rc == 0:
        logger.info('Hotspot stopped')
    # Also try to reconnect to the last known network
    _run(['nmcli', 'dev', 'wifi', 'rescan'])
    return rc == 0


def is_hotspot_active() -> bool:
    """Check if the hotspot connection is currently active."""
    rc, out, _ = _run(['nmcli', '-t', '-f', 'NAME,TYPE,STATE', 'con', 'show', '--active'])
    if rc != 0:
        return False
    for line in out.splitlines():
        if 'Hotspot' in line and 'activated' in line:
            return True
    return False
