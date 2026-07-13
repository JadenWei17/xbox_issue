"""Hardware-independent component tests."""

import json
import unittest

from drive_mixer import mix_drive, scale_wheel_speeds
from input_filter import InputFilter
from udp_receiver import DistanceMove, UDPReceiver


class DriveMixerTests(unittest.TestCase):
    def test_forward_and_reverse(self) -> None:
        self.assertEqual(mix_drive(1.0, 0.0), (1.0, 1.0))
        self.assertEqual(mix_drive(-1.0, 0.0), (-1.0, -1.0))

    def test_turn_and_saturation(self) -> None:
        self.assertEqual(mix_drive(0.0, 1.0), (1.0, -1.0))
        self.assertEqual(mix_drive(1.0, 1.0), (1.0, 0.0))
        self.assertEqual(mix_drive(1.0, 1.0, 0.5), (1.0, 1.0 / 3.0))
        self.assertEqual(scale_wheel_speeds(1.0, -1.0, 255), (255, -255))


class InputFilterTests(unittest.TestCase):
    def test_deadzone_and_smoothing(self) -> None:
        input_filter = InputFilter(alpha=0.5, deadzone=0.1)
        self.assertEqual(input_filter.update(0.05, 0.0), (0.0, 0.0))
        x, y = input_filter.update(1.0, -1.0)
        self.assertEqual((x, y), (0.5, -0.5))
        input_filter.reset()
        self.assertEqual(input_filter.update(0.0, 0.0), (0.0, 0.0))


class UDPValidationTests(unittest.TestCase):
    def test_valid_packet(self) -> None:
        packet = json.dumps({"x": 0.2, "y": -1.0}).encode()
        command = UDPReceiver._parse_packet(packet)
        self.assertIsNotNone(command)
        assert command is not None
        self.assertEqual((command.x, command.y), (0.2, -1.0))

    def test_safety_commands(self) -> None:
        self.assertEqual(
            UDPReceiver._parse_packet(b'{"command":"ESTOP"}'), "ESTOP"
        )
        self.assertEqual(
            UDPReceiver._parse_packet(b'{"command":"RESET"}'), "RESET"
        )
        self.assertIsNone(
            UDPReceiver._parse_packet(b'{"command":"ESTOP","x":0}')
        )

    def test_distance_move(self) -> None:
        packet = json.dumps(
            {
                "command": "MOVE",
                "direction": "FWD",
                "speed_level": 2,
                "distance_cm": 10,
            }
        ).encode()
        command = UDPReceiver._parse_packet(packet)
        self.assertIsInstance(command, DistanceMove)
        assert isinstance(command, DistanceMove)
        self.assertEqual(
            (command.direction, command.speed_level, command.distance_cm),
            ("FWD", 2, 10),
        )

    def test_invalid_packets(self) -> None:
        packets = [
            b"{}",
            b"not-json",
            json.dumps({"x": 2, "y": 0}).encode(),
            json.dumps({"x": True, "y": 0}).encode(),
            json.dumps({"x": 0, "y": 0, "left_stick_pressed": False}).encode(),
            json.dumps({"x": 0, "y": 0, "extra": 0}).encode(),
            json.dumps(
                {
                    "command": "MOVE",
                    "direction": "LEFT",
                    "speed_level": 2,
                    "distance_cm": 10,
                }
            ).encode(),
            json.dumps(
                {
                    "command": "MOVE",
                    "direction": "FWD",
                    "speed_level": 4,
                    "distance_cm": 10,
                }
            ).encode(),
            json.dumps(
                {
                    "command": "MOVE",
                    "direction": "FWD",
                    "speed_level": 2.0,
                    "distance_cm": 10,
                }
            ).encode(),
            json.dumps(
                {
                    "command": "MOVE",
                    "direction": "FWD",
                    "speed_level": 2,
                    "distance_cm": 0,
                }
            ).encode(),
        ]
        for packet in packets:
            with self.subTest(packet=packet):
                self.assertIsNone(UDPReceiver._parse_packet(packet))


if __name__ == "__main__":
    unittest.main()
