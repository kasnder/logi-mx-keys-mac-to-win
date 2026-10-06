import struct
import unittest

from logitech_backlight import BacklightState


class BacklightTests(unittest.TestCase):
    def setUp(self):
        self.state = BacklightState(1, 13, 61, 1, 4, 6, 6, 60)

    def test_brightness_preserves_timeouts_and_option_bits(self):
        updated = self.state.changed('level', 7, 8)
        self.assertEqual(struct.unpack('<BBBBHHH', updated.packet()),
                         (1, 29, 255, 7, 6, 6, 60))

    def test_timeout_rounds_up_and_preserves_others(self):
        updated = self.state.changed('hands_away', 31, 8)
        self.assertEqual(updated.hands_away, 7)
        self.assertEqual((updated.options, updated.hands_near, updated.powered), (13, 6, 60))

    def test_off_preserves_mode_and_timeouts(self):
        updated = self.state.changed('mode', -1, 8)
        self.assertEqual(updated.mode, -1)
        self.assertEqual((updated.options, updated.powered), (13, 60))

    def test_rejects_invalid_values(self):
        for field, value in [('level', 8), ('level', -1), ('powered', 0), ('mode', 2)]:
            with self.assertRaises(ValueError):
                self.state.changed(field, value, 8)


if __name__ == '__main__':
    unittest.main()
