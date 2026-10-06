"""MX Keys Mini BACKLIGHT2 controls; preserve unrelated device settings."""

import struct
import threading
from dataclasses import dataclass, replace

from logitech_lock import BoltConnection, find_keyboard, receiver_paths


@dataclass(frozen=True)
class BacklightState:
    enabled: int
    options: int
    supported: int
    effects: int
    level: int
    hands_away: int
    hands_near: int
    powered: int

    @property
    def mode(self):
        return (self.options >> 3) & 3 if self.enabled else -1

    @classmethod
    def read(cls, connection, slot, feature):
        return cls(*struct.unpack('<BBBHBHHH', connection.request(slot, feature, 0)[:12]))

    def changed(self, field, value, levels):
        if field == 'mode':
            if value not in (-1, 1, 3):
                raise ValueError('Unknown illumination mode')
            if value == 1 and not self.supported & 8:
                raise ValueError('Automatic mode is unavailable')
            if value == 3 and not self.supported & 32:
                raise ValueError('Manual mode is unavailable')
            return replace(self, enabled=int(value != -1), options=(self.options & 7) | ((value if value != -1 else (self.options >> 3) & 3) << 3))
        if field == 'level':
            if not 0 <= value < levels:
                raise ValueError('Brightness outside device range')
            return replace(self.changed('mode', 3, levels), level=value)
        if field in ('hands_away', 'hands_near', 'powered'):
            if not 5 <= value <= 600:
                raise ValueError('Timeout must be between 5 and 600 seconds')
            return replace(self, **{field: (value + 4) // 5})
        raise ValueError('Unknown backlight setting')

    def packet(self):
        return struct.pack('<BBBBHHH', self.enabled, self.options, 255,
                           self.level if self.mode == 3 else 0,
                           self.hands_away, self.hands_near, self.powered)


class BacklightController:
    def __init__(self, updated=lambda: None):
        self.updated = updated
        self.state = None
        self.levels = 0
        self.status = 'Reading keyboard…'
        self.busy = False
        self._lock = threading.Lock()

    def request(self, field=None, value=None):
        if not self._lock.acquire(blocking=False):
            return
        self.busy = True
        threading.Thread(target=self._work, args=(field, value), daemon=True).start()

    def _work(self, field, value):
        try:
            import hid
            for paths in receiver_paths(hid):
                connection = BoltConnection(paths, hid, software_id=0x0C)
                try:
                    target = find_keyboard(connection, threading.Event())
                    if not target:
                        continue
                    slot, _ = target
                    info = connection.request(slot, 0, 0, b'\x19\x82')
                    feature = info[0]
                    if not feature or info[2] < 3:
                        raise OSError('Backlight controls require BACKLIGHT2 v3')
                    state = BacklightState.read(connection, slot, feature)
                    levels = connection.request(slot, feature, 2)[0]
                    if field is not None:
                        desired = state.changed(field, value, levels)
                        connection.request(slot, feature, 1, desired.packet())
                        state = BacklightState.read(connection, slot, feature)
                        if field == 'mode':
                            verified = state.mode == value
                        elif field == 'level':
                            verified = state.mode == 3 and state.level == value
                        else:
                            verified = getattr(state, field) == getattr(desired, field)
                        if not verified:
                            raise OSError('Keyboard did not retain the requested setting')
                    self.state, self.levels = state, levels
                    self.status = 'Backlight'
                    return
                finally:
                    connection.close()
            raise OSError('Keyboard unavailable — wake it and refresh')
        except (OSError, ValueError, ImportError, IndexError, struct.error) as exc:
            self.state = None
            self.status = str(exc)
        finally:
            self.busy = False
            self._lock.release()
            self.updated()
