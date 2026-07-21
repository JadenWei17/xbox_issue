"""Read the Xbox controller and send its state to the Raspberry Pi."""

from __future__ import annotations

import time
from enum import Enum

from .config import SEND_INTERVAL_SECONDS, SEND_RATE_HZ
from .keyboard_input import KeyboardInput, parse_motion_command
from .network import RaspberryPiClient
from .runtime_status import write_status
from .xbox_controller import XboxController


class ControlMode(Enum):
    MANUAL = "MANUAL_MODE"
    DISTANCE = "DISTANCE_MODE"


def main() -> None:
    controller = XboxController()
    client = RaspberryPiClient()
    previous_estop_pressed = False
    previous_reset_pressed = False
    previous_dpad = (0, 0)
    mode = ControlMode.MANUAL
    keyboard = KeyboardInput()
    next_status_write = 0.0
    next_control_log = 0.0

    try:
        controller.connect()
        keyboard.start()
        print(f"Controller: {controller.name}")
        print(f"Sending UDP left-stick states at {SEND_RATE_HZ:g} Hz.")
        print("D-pad Up: MANUAL_MODE; D-pad Right: DISTANCE_MODE.")
        print("Motion command: w/s <level 1-2> <distance_cm>; a/d <level 1-2> <angle_deg>.")
        print("Press Ctrl+C to stop.")

        next_send_time = time.monotonic()

        while True:
            now = time.monotonic()
            if now >= next_status_write:
                write_status(mode.value)
                next_status_write = now + 1.0
            state = controller.read()
            if state.estop_pressed and not previous_estop_pressed:
                client.send({"command": "ESTOP"})
                print("ESTOP sent.", flush=True)
            if state.reset_pressed and not previous_reset_pressed:
                client.send({"command": "RESET"})
                print("RESET sent.", flush=True)
            previous_estop_pressed = state.estop_pressed
            previous_reset_pressed = state.reset_pressed

            dpad = (state.dpad_x, state.dpad_y)
            requested_mode = mode
            if dpad != previous_dpad:
                if state.dpad_y > 0:
                    requested_mode = ControlMode.MANUAL
                elif state.dpad_x > 0:
                    requested_mode = ControlMode.DISTANCE
            previous_dpad = dpad

            mode_changed = requested_mode is not mode
            if requested_mode is not mode:
                if requested_mode is ControlMode.DISTANCE:
                    client.send({"command": "IDLE"})
                else:
                    client.send({"x": 0.0, "y": 0.0})
                mode = requested_mode
                write_status(mode.value)
                print(f"Mode: {mode.value} (stop sent).", flush=True)

            for line in keyboard.pop_lines():
                if mode is not ControlMode.DISTANCE:
                    print("Ignored keyboard command outside DISTANCE_MODE.", flush=True)
                    continue
                try:
                    command = parse_motion_command(line)
                except ValueError as error:
                    print(f"Invalid motion command: {error}", flush=True)
                else:
                    client.send(command.as_dict())
                    print(f"Command sent: {command.as_dict()}", flush=True)

            if mode is ControlMode.MANUAL and not mode_changed:
                data = state.as_dict()
                client.send(data)
                if now >= next_control_log:
                    print(data, flush=True)
                    next_control_log = now + 1.0

            next_send_time += SEND_INTERVAL_SECONDS
            delay = next_send_time - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            else:
                # If a cycle overruns, restart timing instead of sending a burst.
                next_send_time = time.monotonic()

    except KeyboardInterrupt:
        print("\nStopped.")
    except RuntimeError as error:
        print(f"Error: {error}")
        raise SystemExit(1) from error
    finally:
        write_status("STOPPED")
        client.close()
        controller.close()


if __name__ == "__main__":
    main()
