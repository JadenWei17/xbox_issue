"""Read the Xbox controller and send its state to the Raspberry Pi."""

from __future__ import annotations

import time

from config import SEND_INTERVAL_SECONDS, SEND_RATE_HZ
from network import RaspberryPiClient
from xbox_controller import XboxController


def main() -> None:
    controller = XboxController()
    client = RaspberryPiClient()
    previous_estop_pressed = False
    previous_reset_pressed = False

    try:
        controller.connect()
        print(f"Controller: {controller.name}")
        print(f"Sending UDP left-stick states at {SEND_RATE_HZ:g} Hz.")
        print("Press Ctrl+C to stop.")

        next_send_time = time.monotonic()

        while True:
            state = controller.read()
            if state.estop_pressed and not previous_estop_pressed:
                client.send({"command": "ESTOP"})
                print("ESTOP sent.", flush=True)
            if state.reset_pressed and not previous_reset_pressed:
                client.send({"command": "RESET"})
                print("RESET sent.", flush=True)
            previous_estop_pressed = state.estop_pressed
            previous_reset_pressed = state.reset_pressed

            data = state.as_dict()
            client.send(data)
            print(data, flush=True)

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
        client.close()
        controller.close()


if __name__ == "__main__":
    main()
