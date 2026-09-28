"""Handle the MX Keys Mini for Mac special key over a Bolt receiver.

HID++ 0x1B04 temporary diversion exposes the otherwise invisible DND/lock
button as control 0x011D. Only this control is changed; restore its original
diversion bit when pausing or quitting. No persistent device settings change.
"""

import ctypes
import logging
import threading
import time

LOG = logging.getLogger(__name__)
CONTROL = 0x011D
FEATURE = 0x1B04
SOFTWARE_ID = 0x0B


def lock_windows():
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.LockWorkStation.argtypes = []
    user32.LockWorkStation.restype = ctypes.c_int
    if not user32.LockWorkStation():
        raise ctypes.WinError(ctypes.get_last_error())


class BoltConnection:
    """Read both receiver collections: short requests can have long replies."""

    def __init__(self, paths, hid_module):
        self.handles = {}
        self.on_event = lambda packet: None
        try:
            for usage, path in paths.items():
                handle = hid_module.device()
                handle.open_path(path)
                self.handles[usage] = handle
                handle.set_nonblocking(True)
        except Exception:
            self.close()
            raise

    def read(self):
        for handle in self.handles.values():
            packet = bytes(handle.read(64))
            if packet:
                return packet
        return b""

    def request(self, slot, feature, function, params=b"", timeout=2.0):
        address = (function << 4) | SOFTWARE_ID
        long_report = len(params) > 3
        report_id, size, usage = (0x11, 20, 2) if long_report else (0x10, 7, 1)
        packet = bytes([report_id, slot, feature, address]) + params
        if self.handles[usage].write(packet.ljust(size, b"\0")) <= 0:
            raise OSError("HID++ request was not sent")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            reply = self.read()
            if len(reply) >= 7 and reply[1] == slot:
                if reply[2:4] == bytes([feature, address]):
                    return reply[4:]
                if reply[2] in (0x8F, 0xFF) and reply[3:5] == bytes([feature, address]):
                    raise OSError(f"HID++ error {reply[5]:02X}")
            if reply:
                self.on_event(reply)
            else:
                time.sleep(0.01)
        raise TimeoutError("No HID++ reply")

    def close(self):
        for handle in self.handles.values():
            handle.close()
        self.handles.clear()


def receiver_paths(hid_module):
    receivers = {}
    for device in hid_module.enumerate(0x046D, 0xC548):
        if device["usage_page"] == 0xFF00 and device["usage"] in (1, 2):
            # Windows paths distinguish short/long reports by collection number.
            path = device["path"]
            parts = path.lower().split(b"#")
            identity = (parts[1].split(b"&col")[0], parts[2].rsplit(b"&", 1)[0])
            receivers.setdefault(identity, {})[device["usage"]] = path
    return [paths for paths in receivers.values() if 1 in paths and 2 in paths]


def find_keyboard(connection, stopped):
    for slot in range(1, 7):
        if stopped.is_set():
            return None
        try:
            name_feature = connection.request(slot, 0, 0, b"\x00\x05")[0]
            if not name_feature:
                continue
            length = connection.request(slot, name_feature, 0)[0]
            name = b"".join(connection.request(slot, name_feature, 1, bytes([offset]))[:16]
                            for offset in range(0, length, 16))[:length].decode("utf-8")
            if name != "MX Keys Mini for Mac":
                continue
            feature = connection.request(slot, 0, 0, FEATURE.to_bytes(2, "big"))[0]
            if not feature:
                continue
            count = connection.request(slot, feature, 0)[0]
            for index in range(count):
                info = connection.request(slot, feature, 1, bytes([index]))
                if int.from_bytes(info[:2], "big") == CONTROL and info[4] & 0x20:
                    return slot, feature
        except (OSError, TimeoutError, UnicodeError):
            continue
    return None


def get_diverted(connection, slot, feature):
    result = connection.request(slot, feature, 2, CONTROL.to_bytes(2, "big"))
    if result[:2] != CONTROL.to_bytes(2, "big"):
        raise OSError("Unexpected control in HID++ reply")
    return bool(result[2] & 1)


def set_diverted(connection, slot, feature, enabled):
    # Bit 1 validates bit 0. Zero remap leaves the native mapping intact.
    params = CONTROL.to_bytes(2, "big") + bytes([0x02 | int(enabled), 0, 0])
    result = connection.request(slot, feature, 3, params)
    if result[:5] != params:
        raise OSError("Keyboard did not acknowledge the lock-key setting")


class LockKeyListener:
    def __init__(self, enabled, action=lock_windows):
        self.enabled = enabled
        self.action = action
        self.stopped = threading.Event()
        self.thread = None
        self.pressed = False

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stopped.set()
        if self.thread:
            self.thread.join(timeout=5)

    def handle_event(self, packet, slot, feature):
        if len(packet) < 12 or packet[0] != 0x11 or packet[1:4] != bytes([slot, feature, 0]):
            return
        controls = [int.from_bytes(packet[i:i + 2], "big") for i in range(4, 12, 2)]
        pressed = CONTROL in controls
        if pressed and not self.pressed and self.enabled() and not self.stopped.is_set():
            self.action()
        self.pressed = pressed

    def _listen(self, connection, slot, feature):
        original = get_diverted(connection, slot, feature)
        self.pressed = False
        try:
            set_diverted(connection, slot, feature, True)
            connection.on_event = lambda packet: self.handle_event(packet, slot, feature)
            next_check = time.monotonic() + 30
            while not self.stopped.is_set() and self.enabled():
                packet = connection.read()
                if packet:
                    connection.on_event(packet)
                elif self.stopped.wait(0.02):
                    break
                if time.monotonic() >= next_check:
                    # Sleep/reconnect can reset temporary settings.
                    if not get_diverted(connection, slot, feature):
                        self.pressed = False
                        set_diverted(connection, slot, feature, True)
                    next_check = time.monotonic() + 30
        finally:
            connection.on_event = lambda packet: None
            try:
                set_diverted(connection, slot, feature, original)
            except OSError:
                LOG.warning("Could not restore lock-key setting; keyboard may be disconnected")

    def _run(self):
        try:
            import hid
        except ImportError:
            LOG.warning("Install requirements.txt to enable the Logitech lock key")
            return
        while not self.stopped.is_set():
            if self.enabled():
                try:
                    for paths in receiver_paths(hid):
                        connection = BoltConnection(paths, hid)
                        try:
                            target = find_keyboard(connection, self.stopped)
                            if target and self.enabled() and not self.stopped.is_set():
                                self._listen(connection, *target)
                        finally:
                            connection.close()
                except OSError:
                    LOG.warning("Logitech lock-key connection unavailable", exc_info=True)
            self.stopped.wait(2)
