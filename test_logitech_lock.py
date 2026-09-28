import threading
import unittest
from unittest.mock import Mock

from logitech_lock import (
    BoltConnection, CONTROL, LockKeyListener, get_diverted, receiver_paths, set_diverted,
)


def notification(slot=6, feature=8, control=CONTROL):
    return bytes([0x11, slot, feature, 0]) + control.to_bytes(2, "big") + bytes(14)


class LockKeyTests(unittest.TestCase):
    def test_press_once_until_released(self):
        action = Mock()
        listener = LockKeyListener(lambda: True, action)
        listener.handle_event(notification(slot=1), 6, 8)
        listener.handle_event(notification(feature=9), 6, 8)
        listener.handle_event(notification(control=0xE9), 6, 8)
        listener.handle_event(b"\x11\x06\x08", 6, 8)
        action.assert_not_called()
        for _ in range(3):
            listener.handle_event(notification(), 6, 8)
        action.assert_called_once()
        listener.handle_event(notification(control=0), 6, 8)
        listener.handle_event(notification(), 6, 8)
        self.assertEqual(action.call_count, 2)

    def test_no_lock_when_disabled_or_stopped(self):
        action = Mock()
        listener = LockKeyListener(lambda: False, action)
        listener.handle_event(notification(), 6, 8)
        listener.handle_event(notification(control=0), 6, 8)
        listener.enabled = lambda: True
        listener.stopped.set()
        listener.handle_event(notification(), 6, 8)
        action.assert_not_called()

    def test_diversion_only_changes_temporary_bit(self):
        connection = Mock()
        for enabled, flags in ((True, 3), (False, 2)):
            expected = b"\x01\x1d" + bytes([flags, 0, 0])
            connection.request.return_value = expected + bytes(11)
            set_diverted(connection, 6, 8, enabled)
            connection.request.assert_called_with(6, 8, 3, expected)
        connection.request.return_value = b"\x00\xe9\x01\0\0"
        with self.assertRaises(OSError):
            get_diverted(connection, 6, 8)

    def test_restore_original_setting_on_read_failure(self):
        for original in (False, True):
            listener = LockKeyListener(lambda: True, Mock())
            connection = Mock()
            connection.request.side_effect = [
                b"\x01\x1d" + bytes([original, 0, 0]),
                b"\x01\x1d\x03\0\0",
                b"\x01\x1d" + bytes([2 | original, 0, 0]),
            ]
            connection.read.side_effect = OSError("receiver unplugged")
            with self.assertRaises(OSError):
                listener._listen(connection, 6, 8)
            connection.request.assert_called_with(
                6, 8, 3, b"\x01\x1d" + bytes([2 | original, 0, 0]))

    def test_short_request_accepts_long_reply_on_other_collection(self):
        connection = BoltConnection.__new__(BoltConnection)
        short, long = Mock(), Mock()
        short.write.return_value = 7
        short.read.return_value = []
        long.read.side_effect = [list(notification()), list(bytes([0x11, 6, 8, 0x2B]) + b"\x01\x1d\x01" + bytes(13))]
        connection.handles = {1: short, 2: long}
        connection.on_event = Mock()
        result = connection.request(6, 8, 2, b"\x01\x1d")
        self.assertEqual(result[:3], b"\x01\x1d\x01")
        connection.on_event.assert_called_once_with(notification())
        short.write.assert_called_once_with(b"\x10\x06\x08\x2b\x01\x1d\0")

    def test_receiver_collections_stay_paired(self):
        devices = []
        for receiver in (b"abc", b"def"):
            for usage in (1, 2):
                path = (b"\\\\?\\HID#VID_046D&PID_C548&MI_02&Col0" + str(usage).encode()
                        + b"#8&" + receiver + b"&0&000" + str(usage - 1).encode() + b"#{guid}")
                devices.append(dict(usage_page=0xFF00, usage=usage, path=path))
        hid = Mock()
        hid.enumerate.return_value = devices
        groups = receiver_paths(hid)
        self.assertEqual(len(groups), 2)
        for group in groups:
            self.assertEqual(group[1].split(b"#")[2][:-1], group[2].split(b"#")[2][:-1])


if __name__ == "__main__":
    unittest.main()
