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
from obstacle_avoidance import ObstacleAvoidance, parse_ultrasonic_distance
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


class ObstacleAvoidanceTests(unittest.TestCase):
    def make_planner(self) -> ObstacleAvoidance:
        return ObstacleAvoidance(
            slow_distance_cm=80, stop_distance_cm=45,
            fast_chunk_cm=20, slow_chunk_cm=5,
            bypass_distance_cm=50, turn_speed_level=1,
            bypass_speed_level=1, sensor_settle_seconds=0.4,
        )

    def test_clear_path_uses_chunks_until_goal(self) -> None:
        planner = self.make_planner()
        planner.start(25, 2, 0)
        planner.observe_distance(150, 0.1)
        first = planner.next_action(0.1)
        self.assertEqual((first.command, first.value), ("MOVE", 20))
        planner.action_done(1)
        second = planner.next_action(1)
        self.assertEqual((second.speed_level, second.value), (2, 5))
        planner.action_done(2)
        self.assertIsNone(planner.next_action(2))
        self.assertEqual(planner.phase, "DONE")

    def test_close_obstacle_builds_left_bypass_right_sequence(self) -> None:
        planner = self.make_planner()
        planner.start(100, 3, 0)
        planner.observe_distance(40, 0.1)
        left = planner.next_action(0.1)
        self.assertEqual((left.command, left.direction, left.value), ("TURN", "LEFT", 90))
        planner.action_done(1)
        bypass = planner.next_action(1)
        self.assertEqual((bypass.command, bypass.value), ("MOVE", 50))
        planner.action_done(2)
        right = planner.next_action(2)
        self.assertEqual((right.command, right.direction), ("TURN", "RIGHT"))
        planner.action_done(3)
        self.assertIsNone(planner.next_action(3.3))
        planner.observe_distance(120, 3.5)
        self.assertEqual(planner.next_action(3.5).direction, "FWD")

    def test_state_distance_parser(self) -> None:
        self.assertEqual(parse_ultrasonic_distance("STATE,MODE=IDLE,US=47,LPWM=0"), 47)
        self.assertIsNone(parse_ultrasonic_distance("STATE,MODE=IDLE,US=NA"))

    def test_slow_chunk_is_not_repeatedly_interrupted(self) -> None:
        planner = self.make_planner()
        planner.start(100, 3, 0)
        planner.observe_distance(70, 0.1)
        action = planner.next_action(0.1)
        self.assertEqual((action.speed_level, action.value), (1, 5))
        self.assertFalse(planner.observe_distance(65, 0.2))
        self.assertTrue(planner.observe_distance(44, 0.3))


if __name__ == "__main__":
    unittest.main()
