"""Raspberry Pi robot control entry point."""

from __future__ import annotations

import time

import config
from drive_mixer import mix_drive, scale_wheel_speeds
from estop_gpio import EstopGPIO
from input_filter import InputFilter
from serial_sender import SerialSender
from udp_receiver import UDPReceiver


def main() -> None:
    receiver = UDPReceiver(config.UDP_HOST, config.UDP_PORT, config.UDP_MAX_PACKET_SIZE)
    sender: SerialSender | None = None
    estop_gpio: EstopGPIO | None = None
    input_filter = InputFilter(config.FILTER_ALPHA, config.INPUT_DEADZONE)
    interval = 1.0 / config.CONTROL_RATE_HZ
    timed_out = True
    estop_latched = False
    last_left = 0
    last_right = 0

    try:
        estop_gpio = EstopGPIO(config.ESTOP_GPIO_PIN)
        sender = SerialSender(
            config.SERIAL_PORT,
            config.SERIAL_BAUDRATE,
            config.SERIAL_WRITE_TIMEOUT_SECONDS,
            config.SERIAL_COMMAND_FORMAT,
            config.SERIAL_STARTUP_DELAY_SECONDS,
        )
        receiver.start()
        print(f"UDP listening on {config.UDP_HOST}:{config.UDP_PORT}")
        print(f"Arduino connected on {sender.port}")
        print("Press Ctrl+C to stop.")

        next_cycle = time.monotonic()
        next_status = next_cycle
        while True:
            now = time.monotonic()
            for safety_command in receiver.pop_safety_commands():
                if safety_command == "ESTOP":
                    estop_gpio.assert_estop()
                    estop_latched = True
                    input_filter.reset()
                    last_left, last_right = 0, 0
                    print("E-STOP latched: motion forwarding disabled.")
                elif safety_command == "RESET":
                    estop_gpio.reset()
                    sender.send_raw(config.SERIAL_RESET_COMMAND)
                    estop_latched = False
                    input_filter.reset()
                    print("E-STOP reset: motion forwarding enabled.")

            command = receiver.latest()
            stale = command is None or now - command.received_at > config.CONTROL_TIMEOUT_SECONDS

            if estop_latched:
                last_left, last_right = 0, 0
                timed_out = True
            elif stale:
                if not timed_out:
                    print("Control timeout: stopping motors.")
                input_filter.reset()
                last_left, last_right = 0, 0
                sender.send(last_left, last_right)
                timed_out = True
            else:
                filtered_x, filtered_y = input_filter.update(command.x, command.y)
                left, right = mix_drive(
                    filtered_x, filtered_y, config.TURN_SCALE
                )
                left, right = scale_wheel_speeds(
                    left,
                    right,
                    config.MAX_MOTOR_SPEED,
                    config.LEFT_SPEED_SCALE,
                    config.RIGHT_SPEED_SCALE,
                )
                sender.send(left, right)
                last_left, last_right = left, right
                timed_out = False

            if now >= next_status:
                stats = receiver.stats()
                if command is None:
                    rx_detail = "no valid control received"
                else:
                    age_ms = (now - command.received_at) * 1000.0
                    rx_detail = (
                        f"age={age_ms:.0f}ms x={command.x:+.3f} "
                        f"y={command.y:+.3f}"
                    )
                source = (
                    f"{stats.latest_sender[0]}:{stats.latest_sender[1]}"
                    if stats.latest_sender is not None
                    else "none"
                )
                print(
                    "[STATUS] "
                    f"RX packets={stats.packets} valid={stats.valid_packets} "
                    f"invalid={stats.invalid_packets} source={source} "
                    f"({rx_detail}) | MIX L={last_left:+d} R={last_right:+d} "
                    f"{'ESTOP' if estop_latched else ('TIMEOUT/STOP' if timed_out else 'ACTIVE')} | "
                    f"TX commands={sender.commands_sent} bytes={sender.bytes_sent} "
                    f"last='{sender.last_command}' port={sender.port} | "
                    f"ARDUINO replies={sender.responses_received} "
                    f"last='{sender.last_response}'",
                    flush=True,
                )
                while next_status <= now:
                    next_status += config.STATUS_INTERVAL_SECONDS

            next_cycle += interval
            delay = next_cycle - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            else:
                next_cycle = time.monotonic()
    except KeyboardInterrupt:
        print("\nStopped by user.")
    except (RuntimeError, OSError) as error:
        print(f"Fatal error: {error}")
        raise SystemExit(1) from error
    except Exception as error:
        print(f"Fatal error: {error}")
        raise SystemExit(1) from error
    finally:
        receiver.close()
        if sender is not None:
            try:
                sender.stop()
            except Exception as error:
                print(f"Warning: could not send final stop command: {error}")
            finally:
                sender.close()
        if estop_gpio is not None:
            estop_gpio.close()
        print("Motors stopped; resources closed.")


if __name__ == "__main__":
    main()
