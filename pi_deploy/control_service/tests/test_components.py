"""Hardware-independent component tests."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from drive_mixer import (
    apply_minimum_wheel_speed,
    mix_drive,
    scale_wheel_speeds,
)
from input_filter import InputFilter
from udp_receiver import DistanceMove, TurnMove, UDPReceiver


class DriveMixerTests(unittest.TestCase):
    def test_forward_and_reverse(self) -> None:
        self.assertEqual(mix_drive(1.0, 0.0), (1.0, 1.0))
        self.assertEqual(mix_drive(-1.0, 0.0), (-1.0, -1.0))

    def test_turn_and_saturation(self) -> None:
        self.assertEqual(mix_drive(0.0, 1.0), (1.0, -1.0))
        self.assertEqual(mix_drive(1.0, 1.0), (1.0, 0.0))
        self.assertEqual(mix_drive(1.0, 1.0, 0.5), (1.0, 1.0 / 3.0))
        self.assertEqual(scale_wheel_speeds(1.0, -1.0, 255), (255, -255))

    def test_manual_minimum_pwm_preserves_stop_and_direction(self) -> None:
        self.assertEqual(apply_minimum_wheel_speed(0, 0, 155, 255), (0, 0))
        self.assertEqual(apply_minimum_wheel_speed(1, -1, 155, 255), (155, -155))
        self.assertEqual(apply_minimum_wheel_speed(200, -255, 155, 255), (200, -255))


class InputFilterTests(unittest.TestCase):
    def test_deadzone_and_smoothing(self) -> None:
        input_filter = InputFilter(alpha=0.5, deadzone=0.1)
        self.assertEqual(input_filter.update(0.05, 0.0), (0.0, 0.0))
        x, y = input_filter.update(1.0, -1.0)
        self.assertEqual((x, y), (0.5, -0.5))
        input_filter.reset()
        self.assertEqual(input_filter.update(0.0, 0.0), (0.0, 0.0))

    def test_centered_axis_stops_without_ema_tail(self) -> None:
        input_filter = InputFilter(alpha=0.35, deadzone=0.03)
        reverse_x, _ = input_filter.update(-1.0, 0.0)
        self.assertLess(reverse_x, 0.0)
        self.assertEqual(input_filter.update(0.0, 0.0), (0.0, 0.0))

    def test_axes_stop_independently(self) -> None:
        input_filter = InputFilter(alpha=0.35, deadzone=0.03)
        input_filter.update(-1.0, 1.0)
        x, y = input_filter.update(0.0, 1.0)
        self.assertEqual(x, 0.0)
        self.assertGreater(y, 0.0)


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
        self.assertEqual(
            UDPReceiver._parse_packet(b'{"command":"IDLE"}'), "IDLE"
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
                    "speed_level": 3,
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

    def test_turn_move(self) -> None:
        packet = json.dumps({"command": "TURN", "direction": "LEFT", "speed_level": 2, "angle_deg": 90}).encode()
        command = UDPReceiver._parse_packet(packet)
        self.assertIsInstance(command, TurnMove)
        self.assertEqual((command.direction, command.speed_level, command.angle_deg), ("LEFT", 2, 90))


if __name__ == "__main__":
    unittest.main()
