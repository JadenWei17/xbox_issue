"""Tests for distance-mode terminal parsing."""

import unittest

from keyboard_input import parse_distance_command


class KeyboardInputTests(unittest.TestCase):
    def test_forward_and_backward(self) -> None:
        forward = parse_distance_command("w 2 10")
        backward = parse_distance_command("s 3 7")
        self.assertEqual((forward.direction, forward.speed_level, forward.distance_cm),
                         ("FWD", 2, 10))
        self.assertEqual((backward.direction, backward.speed_level, backward.distance_cm),
                         ("BWD", 3, 7))

    def test_invalid_commands(self) -> None:
        for text in ("w 0 10", "w 4 10", "w 2 0", "x 2 10", "w fast 10"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse_distance_command(text)


if __name__ == "__main__":
    unittest.main()
