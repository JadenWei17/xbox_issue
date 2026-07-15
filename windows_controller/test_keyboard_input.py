"""Tests for distance-mode terminal parsing."""

import unittest

from .keyboard_input import TurnCommand, parse_distance_command, parse_motion_command


class KeyboardInputTests(unittest.TestCase):
    def test_forward_and_backward(self) -> None:
        forward = parse_distance_command("w 2 10")
        backward = parse_distance_command("s 1 7")
        self.assertEqual((forward.direction, forward.speed_level, forward.distance_cm),
                         ("FWD", 2, 10))
        self.assertEqual((backward.direction, backward.speed_level, backward.distance_cm),
                         ("BWD", 1, 7))

    def test_invalid_commands(self) -> None:
        for text in ("w 0 10", "w 3 10", "w 4 10", "w 2 0", "x 2 10", "w fast 10"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse_distance_command(text)

    def test_turn_commands_and_limits(self) -> None:
        left = parse_motion_command("a 2 90")
        right = parse_motion_command("d 1 720")
        self.assertIsInstance(left, TurnCommand)
        self.assertEqual((left.direction, left.speed_level, left.angle_deg), ("LEFT", 2, 90))
        self.assertEqual((right.direction, right.angle_deg), ("RIGHT", 720))
        for text in ("a 0 90", "a 3 90", "a 1 0", "d 2 721", "d fast 45"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_motion_command(text)


if __name__ == "__main__":
    unittest.main()
