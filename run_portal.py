#!/usr/bin/env python3
"""Run the captive portal standalone on port 8080 for local dev/preview."""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))

# Override portal port before importing
import config
config.WIFI_PORTAL_PORT = 8080

from wifi import portal

print(f'Starting captive portal on http://localhost:{config.WIFI_PORTAL_PORT}')
portal.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    portal.stop()
