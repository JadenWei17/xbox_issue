"""Raspberry Pi robot control entry point."""

from __future__ import annotations

import time

import config
from drive_mixer import apply_minimum_wheel_speed, mix_drive, scale_wheel_speeds
from estop_gpio import EstopGPIO
from input_filter import InputFilter
from obstacle_avoidance import ObstacleAvoidance, parse_ultrasonic_distance
from serial_sender import SerialSender
from telemetry_sender import TelemetrySender
from udp_receiver import UDPReceiver


def main() -> None:
    receiver = UDPReceiver(config.UDP_HOST, config.UDP_PORT, config.UDP_MAX_PACKET_SIZE)
    sender: SerialSender | None = None
    telemetry = TelemetrySender(
        config.TELEMETRY_TARGET_IP, config.TELEMETRY_TARGET_PORT
    )
    estop_gpio: EstopGPIO | None = None
    input_filter = InputFilter(config.FILTER_ALPHA, config.INPUT_DEADZONE)
    avoidance = ObstacleAvoidance(
        slow_distance_cm=config.AVOIDANCE_SLOW_DISTANCE_CM,
        stop_distance_cm=config.AVOIDANCE_STOP_DISTANCE_CM,
        fast_chunk_cm=config.AVOIDANCE_FAST_CHUNK_CM,
        slow_chunk_cm=config.AVOIDANCE_SLOW_CHUNK_CM,
        bypass_distance_cm=config.AVOIDANCE_BYPASS_DISTANCE_CM,
        turn_speed_level=config.AVOIDANCE_TURN_SPEED_LEVEL,
        bypass_speed_level=config.AVOIDANCE_BYPASS_SPEED_LEVEL,
        sensor_settle_seconds=config.AVOIDANCE_SENSOR_SETTLE_SECONDS,
    )
    interval = 1.0 / config.CONTROL_RATE_HZ
    timed_out = True
    estop_latched = False
    last_left = 0
    last_right = 0
    motion_active = False
    motion_started_at = 0.0
    motion_acknowledged = False
    motion_ack_deadline = 0.0

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
            for response in sender.pop_responses():
                if response.startswith("STATE,"):
                    telemetry.publish_state(response)
                    print(f"[ARDUINO] {response}")
                    obstacle_distance = parse_ultrasonic_distance(response)
                    if avoidance.observe_distance(obstacle_distance, now):
                        sender.send_raw(config.SERIAL_IDLE_COMMAND)
                        motion_active = False
                        motion_acknowledged = False
                        avoidance.interrupted_for_obstacle()
                        print(
                            "Avoidance: obstacle entered slow zone; "
                            "current forward segment stopped."
                        )
                elif response in ("DONE,MOVE", "DONE,TURN"):
                    motion_active = False
                    motion_acknowledged = False
                    if avoidance.active:
                        avoidance.action_done(now)
                    print(f"Arduino action completed: {response}")
                elif response.startswith("ACK,"):
                    motion_acknowledged = True
                    print(f"Arduino accepted action: {response}")
                elif response.startswith("ERROR,"):
                    motion_active = False
                    motion_acknowledged = False
                    if avoidance.active:
                        sender.send_raw(config.SERIAL_AVOIDANCE_OFF_COMMAND)
                        avoidance.reset()
                    if response == "ERROR,ESTOP_ACTIVE":
                        estop_latched = True
                    print(f"Arduino rejected command: {response}")
                elif response == "BUSY":
                    print("Arduino rejected new action: BUSY")
                elif response == "WATCHDOG":
                    print("Arduino manual watchdog stopped the motors.")
                elif response.startswith("ESTOP "):
                    if not estop_latched:
                        print("Arduino hardware E-STOP latch detected; press X to reset.")
                    estop_latched = True

            safety_commands = receiver.pop_safety_commands()
            for safety_command in safety_commands:
                if safety_command == "ESTOP":
                    # Redundant stop path: do not rely only on the GPIO line.
                    # Arduino still gives GPIO17 highest priority and latches it.
                    sender.send(0, 0)
                    estop_gpio.assert_estop()
                    estop_latched = True
                    input_filter.reset()
                    last_left, last_right = 0, 0
                    motion_active = False
                    motion_acknowledged = False
                    if avoidance.active:
                        sender.send_raw(config.SERIAL_AVOIDANCE_OFF_COMMAND)
                        avoidance.reset()
                    print("E-STOP latched: motion forwarding disabled.")
                elif safety_command == "RESET":
                    estop_gpio.reset()
                    sender.send_raw(config.SERIAL_RESET_COMMAND)
                    estop_latched = False
                    input_filter.reset()
                    motion_active = False
                    motion_acknowledged = False
                    if avoidance.active:
                        sender.send_raw(config.SERIAL_AVOIDANCE_OFF_COMMAND)
                        avoidance.reset()
                    print("E-STOP reset: motion forwarding enabled.")
                elif safety_command == "IDLE":
                    sender.send_raw(config.SERIAL_IDLE_COMMAND)
                    input_filter.reset()
                    last_left, last_right = 0, 0
                    motion_active = False
                    motion_acknowledged = False
                    if avoidance.active:
                        sender.send_raw(config.SERIAL_AVOIDANCE_OFF_COMMAND)
                        avoidance.reset()
                    timed_out = True
                    print("Keyboard mode waiting: Arduino set to IDLE.")

            actions = [*receiver.pop_distance_moves(), *receiver.pop_turn_moves()]
            actions.sort(key=lambda action: action.received_at)
            safety_blocks_action = any(
                command in ("ESTOP", "RESET") for command in safety_commands
            )
            if actions and not estop_latched and not safety_blocks_action:
                move = actions[0]
                if motion_active or avoidance.active:
                    print("Action rejected locally: BUSY")
                elif hasattr(move, "distance_cm") and move.direction == "FWD":
                    avoidance.start(move.distance_cm, move.speed_level, now)
                    sender.send_raw(config.SERIAL_AVOIDANCE_ON_COMMAND)
                    print(
                        "Avoidance started: "
                        f"forward goal={move.distance_cm:.1f} cm"
                    )
                elif hasattr(move, "distance_cm"):
                    sender.send_raw(config.SERIAL_MOVE_COMMAND_FORMAT.format(
                        direction="REV" if move.direction == "BWD" else move.direction,
                        speed_level=move.speed_level, distance_cm=move.distance_cm))
                    print(f"Motion sent: MOVE,{move.direction},{move.speed_level},{move.distance_cm:.1f}")
                else:
                    sender.send_raw(config.SERIAL_TURN_COMMAND_FORMAT.format(
                        direction=move.direction, speed_level=move.speed_level,
                        angle_deg=move.angle_deg))
                    print(f"Motion sent: TURN,{move.direction},{move.speed_level},{move.angle_deg:.1f}")
                if not motion_active and not avoidance.active:
                    motion_active = True
                    motion_started_at = move.received_at
                    motion_acknowledged = False
                    motion_ack_deadline = now + config.MOVE_ACK_TIMEOUT_SECONDS
                    input_filter.reset()

            planned = avoidance.next_action(now)
            if planned is not None and not motion_active and not estop_latched:
                if planned.command == "MOVE":
                    sender.send_raw(config.SERIAL_MOVE_COMMAND_FORMAT.format(
                        direction=planned.direction,
                        speed_level=planned.speed_level,
                        distance_cm=planned.value,
                    ))
                else:
                    sender.send_raw(config.SERIAL_TURN_COMMAND_FORMAT.format(
                        direction=planned.direction,
                        speed_level=planned.speed_level,
                        angle_deg=planned.value,
                    ))
                motion_active = True
                motion_started_at = now
                motion_acknowledged = False
                motion_ack_deadline = now + config.MOVE_ACK_TIMEOUT_SECONDS
                print(
                    f"Avoidance action: {planned.command},{planned.direction},"
                    f"{planned.speed_level},{planned.value:.1f}"
                )
            elif avoidance.phase == "DONE":
                sender.send_raw(config.SERIAL_AVOIDANCE_OFF_COMMAND)
                avoidance.reset()
                print("Avoidance completed: requested forward distance reached.")

            command = receiver.latest()
            if (
                motion_active
                and command is not None
                and command.received_at > motion_started_at
            ):
                motion_active = False
                motion_acknowledged = False
                if avoidance.active:
                    sender.send_raw(config.SERIAL_AVOIDANCE_OFF_COMMAND)
                    avoidance.reset()
                print("Distance move cancelled by manual control.")
            if (
                motion_active
                and not motion_acknowledged
                and now >= motion_ack_deadline
            ):
                motion_active = False
                sender.send(0, 0)
                if avoidance.active:
                    sender.send_raw(config.SERIAL_AVOIDANCE_OFF_COMMAND)
                    avoidance.reset()
                print("Distance move cancelled: Arduino ACK timeout.")
            stale = command is None or now - command.received_at > config.CONTROL_TIMEOUT_SECONDS

            if estop_latched:
                last_left, last_right = 0, 0
                timed_out = True
            elif motion_active:
                last_left, last_right = 0, 0
                timed_out = False
            elif stale:
                if not timed_out:
                    print("Control timeout: stopping motors.")
                    input_filter.reset()
                    last_left, last_right = 0, 0
                    # Send one explicit stop, then let Arduino's manual
                    # watchdog transition MANUAL -> IDLE. Repeating zero at
                    # 30 Hz would keep refreshing the MANUAL command timer.
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
                left, right = apply_minimum_wheel_speed(
                    left,
                    right,
                    config.MANUAL_MIN_MOTOR_SPEED,
                    config.MAX_MOTOR_SPEED,
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
                        f"{'ESTOP' if estop_latched else ('MOTION' if motion_active else ('TIMEOUT/STOP' if timed_out else 'ACTIVE'))} | "
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
        telemetry.close()
        print("Motors stopped; resources closed.")


if __name__ == "__main__":
    main()
