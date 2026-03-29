# hardware/touch.py — GT1151 capacitive touch controller driver
#
# The GT1151 sits on I2C bus 1 at address 0x14. It uses 16-bit register
# addressing (big-endian). Coordinates are in the panel's native portrait
# orientation and are remapped here to landscape (250×122).
#
# Touch coordinate remap (portrait → landscape):
#   landscape_x = touch_y          (0..250 → 0..250)
#   landscape_y = NATIVE_SHORT - touch_x   (0..122 → 122..0)
#
# Adjust TOUCH_SWAP_XY / TOUCH_FLIP_X / TOUCH_FLIP_Y in config if your
# physical mounting differs.

import logging
import threading
import time

import config

logger = logging.getLogger(__name__)

# ---- try to import hardware libraries ----
try:
    import RPi.GPIO as GPIO
    _HAS_GPIO = True
except ImportError:
    _HAS_GPIO = False
    logger.warning('RPi.GPIO not available — touch in simulation mode')

try:
    from smbus2 import SMBus, i2c_msg
    _HAS_I2C = True
except ImportError:
    _HAS_I2C = False
    logger.warning('smbus2 not available — touch in simulation mode')

_SIMULATION = not (_HAS_GPIO and _HAS_I2C)

# GT1151 register map
_REG_STATUS = 0x814E   # bit7=buffer ready, bits[3:0]=touch count
_REG_TOUCH1 = 0x8150   # first touch point (8 bytes)
# Touch point layout: [track_id, x_lo, x_hi, y_lo, y_hi, sz_lo, sz_hi, pad]


class TouchDriver:
    """
    Polls the GT1151 every TOUCH_POLL_INTERVAL seconds.

    set_handler(fn) registers a callable that receives (x, y) in landscape
    pixel coordinates on each new touch-down event (rising edge only,
    debounced).
    """

    def __init__(self):
        self._bus = None
        self._handler = None
        self._running = False
        self._thread = None
        self._was_touching = False
        self._last_event_time = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def init(self):
        if _SIMULATION:
            logger.info('Touch driver: simulation mode')
            return
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(config.TOUCH_RST_PIN, GPIO.OUT)
        GPIO.setup(config.TOUCH_INT_PIN, GPIO.IN)
        self._reset()
        self._bus = SMBus(config.TOUCH_I2C_BUS)
        logger.info('Touch driver initialised')

    def set_handler(self, fn):
        """Register callback fn(x, y) for touch-down events."""
        self._handler = fn

    def start(self):
        self._running = True
        self._thread = threading.Thread(
            target=self._poll_loop, name='touch-poll', daemon=True
        )
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._bus and not _SIMULATION:
            self._bus.close()

    # ------------------------------------------------------------------
    # GT1151 I2C helpers
    # ------------------------------------------------------------------

    def _reset(self):
        GPIO.output(config.TOUCH_RST_PIN, GPIO.LOW)
        time.sleep(0.010)
        GPIO.output(config.TOUCH_RST_PIN, GPIO.HIGH)
        time.sleep(0.050)

    def _read_reg(self, reg: int, length: int) -> list:
        """Read `length` bytes from a 16-bit register address."""
        write = i2c_msg.write(config.TOUCH_I2C_ADDR, [(reg >> 8) & 0xFF, reg & 0xFF])
        read  = i2c_msg.read(config.TOUCH_I2C_ADDR, length)
        self._bus.i2c_rdwr(write, read)
        return list(read)

    def _write_reg(self, reg: int, data: bytes) -> None:
        """Write bytes to a 16-bit register address."""
        payload = [(reg >> 8) & 0xFF, reg & 0xFF] + list(data)
        write = i2c_msg.write(config.TOUCH_I2C_ADDR, payload)
        self._bus.i2c_rdwr(write)

    def _clear_buffer(self):
        self._write_reg(_REG_STATUS, b'\x00')

    # ------------------------------------------------------------------
    # Scan & remap
    # ------------------------------------------------------------------

    def _scan(self):
        """
        Read current touch state.
        Returns (x, y) in landscape coordinates, or None if no touch.
        """
        try:
            status_bytes = self._read_reg(_REG_STATUS, 1)
        except Exception as exc:
            logger.debug('Touch I2C error: %s', exc)
            return None

        status = status_bytes[0]

        if not (status & 0x80):
            return None   # buffer not ready

        count = status & 0x0F
        if count == 0:
            self._clear_buffer()
            return None

        try:
            data = self._read_reg(_REG_TOUCH1, 8)
        except Exception as exc:
            logger.debug('Touch point read error: %s', exc)
            self._clear_buffer()
            return None

        self._clear_buffer()

        x_raw = data[1] | (data[2] << 8)
        y_raw = data[3] | (data[4] << 8)

        # Remap portrait → landscape
        lx = y_raw
        ly = config.DISPLAY_NATIVE_SHORT - x_raw

        # Clamp to display bounds
        lx = max(0, min(config.DISPLAY_W - 1, lx))
        ly = max(0, min(config.DISPLAY_H - 1, ly))

        return (lx, ly)

    # ------------------------------------------------------------------
    # Poll loop
    # ------------------------------------------------------------------

    def _poll_loop(self):
        while self._running:
            if _SIMULATION:
                time.sleep(config.TOUCH_POLL_INTERVAL)
                continue

            point = self._scan()

            if point is not None:
                if not self._was_touching:
                    now = time.monotonic()
                    if now - self._last_event_time >= config.TOUCH_DEBOUNCE_SEC:
                        self._last_event_time = now
                        if self._handler:
                            try:
                                self._handler(*point)
                            except Exception as exc:
                                logger.error('Touch handler error: %s', exc)
                self._was_touching = True
            else:
                self._was_touching = False

            time.sleep(config.TOUCH_POLL_INTERVAL)
