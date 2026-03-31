# wifi/portal.py — Minimal captive portal HTTP server
#
# Serves a single-page WiFi setup form. When the device enters AP mode,
# the user connects their phone to the hotspot and opens the portal URL
# in a browser to enter WiFi credentials.
#
# Runs in a daemon thread. Start/stop from main.py via the WiFi manager.

import html
import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

import config
from wifi import manager as wifi_mgr

logger = logging.getLogger(__name__)

_server_instance = None
_server_thread = None


# ------------------------------------------------------------------
# HTML template
# ------------------------------------------------------------------

_PAGE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>WiFi Setup</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,sans-serif;max-width:420px;margin:0 auto;padding:16px;background:#fff;color:#000}}
h2{{margin-bottom:16px}}
label{{display:block;margin:12px 0 4px;font-weight:bold}}
select,input[type=password],button{{width:100%;padding:14px;font-size:16px;border:2px solid #000;border-radius:0;background:#fff}}
button{{background:#000;color:#fff;cursor:pointer;margin-top:16px;font-weight:bold}}
button:active{{background:#333}}
.msg{{padding:12px;margin:12px 0;border:2px solid #000}}
.msg.ok{{background:#e8f5e9}}
.msg.err{{background:#ffebee}}
.net{{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #ccc}}
.net .signal{{color:#666;font-size:14px}}
</style>
</head>
<body>
<h2>WiFi Setup</h2>
{status}
<form method="POST" action="/connect">
<label for="ssid">Network</label>
<select name="ssid" id="ssid">
{options}
</select>
<label for="password">Password</label>
<input type="password" name="password" id="password" placeholder="Leave blank for open networks">
<button type="submit">Connect</button>
</form>
<p style="margin-top:24px;font-size:13px;color:#666">
After connecting, this setup page will become unreachable.
The device display will update automatically.
</p>
</body>
</html>
"""


def _build_page(networks=None, status_html=''):
    if networks is None:
        networks = wifi_mgr.scan_networks()

    options = []
    for net in networks:
        esc_ssid = html.escape(net.ssid, quote=True)
        lock = '' if net.security == 'open' else ' [secured]'
        options.append(
            f'<option value="{esc_ssid}">'
            f'{esc_ssid}  ({net.signal}%{lock})</option>'
        )

    if not options:
        options.append('<option value="">No networks found</option>')

    return _PAGE_TEMPLATE.format(
        status=status_html,
        options='\n'.join(options),
    )


# ------------------------------------------------------------------
# HTTP handler
# ------------------------------------------------------------------

class _PortalHandler(BaseHTTPRequestHandler):
    # Shared state set by start()
    _store = None
    _bus = None

    def log_message(self, fmt, *args):
        logger.debug('Portal: ' + fmt, *args)

    def do_GET(self):
        body = _build_page()
        self._send_html(200, body)

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(length).decode('utf-8')
        params = parse_qs(raw)

        ssid = params.get('ssid', [''])[0]
        password = params.get('password', [''])[0]

        if not ssid:
            body = _build_page(status_html='<div class="msg err">No network selected.</div>')
            self._send_html(400, body)
            return

        # Attempt connection in a background thread so the HTTP response
        # can be sent before the hotspot drops.
        def _do_connect():
            # Stop hotspot first so wlan0 is free for station mode
            wifi_mgr.stop_hotspot()

            ok, msg = wifi_mgr.connect(ssid, password if password else None)

            if self._store:
                from events import EVT_STATE_CHANGED
                def _update(s):
                    s.wifi_ap_mode = False
                    s.wifi_status = msg
                self._store.update(_update)
                if self._bus:
                    self._bus.publish(EVT_STATE_CHANGED)

            if not ok:
                # Connection failed — restart hotspot so user can retry
                logger.warning('WiFi connection failed, restarting hotspot')
                wifi_mgr.start_hotspot()
                if self._store:
                    self._store.update(lambda s: setattr(s, 'wifi_ap_mode', True))

        # Send response first
        status_msg = (
            f'<div class="msg ok">Connecting to <b>{html.escape(ssid)}</b>... '
            f'This page will stop working. Check the device display.</div>'
        )
        body = _build_page(status_html=status_msg)
        self._send_html(200, body)

        t = threading.Thread(target=_do_connect, daemon=True)
        t.start()

    def _send_html(self, code, body):
        encoded = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


# ------------------------------------------------------------------
# Start / stop
# ------------------------------------------------------------------

def start(store=None, bus=None):
    """Start the captive portal HTTP server in a daemon thread."""
    global _server_instance, _server_thread

    if _server_instance is not None:
        return  # already running

    _PortalHandler._store = store
    _PortalHandler._bus = bus

    try:
        _server_instance = HTTPServer(('0.0.0.0', config.WIFI_PORTAL_PORT), _PortalHandler)
    except OSError as exc:
        logger.error('Cannot start portal on port %d: %s', config.WIFI_PORTAL_PORT, exc)
        return

    _server_thread = threading.Thread(
        target=_server_instance.serve_forever,
        name='wifi-portal',
        daemon=True,
    )
    _server_thread.start()
    logger.info('Captive portal started on port %d', config.WIFI_PORTAL_PORT)


def stop():
    """Stop the captive portal HTTP server."""
    global _server_instance, _server_thread

    if _server_instance is not None:
        _server_instance.shutdown()
        _server_instance = None
        _server_thread = None
        logger.info('Captive portal stopped')
