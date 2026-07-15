"""Non-blocking Pi-side planner for keyboard forward-distance avoidance."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlannedAction:
    command: str
    direction: str
    speed_level: int
    value: float
    counts_toward_goal: bool = False


class ObstacleAvoidance:
    """Break a forward goal into measurable moves and insert a left detour."""

    def __init__(self, *, slow_distance_cm: float, stop_distance_cm: float,
                 fast_chunk_cm: float, slow_chunk_cm: float,
                 bypass_distance_cm: float, turn_speed_level: int,
                 bypass_speed_level: int, sensor_settle_seconds: float) -> None:
        self.slow_distance_cm = slow_distance_cm
        self.stop_distance_cm = stop_distance_cm
        self.fast_chunk_cm = fast_chunk_cm
        self.slow_chunk_cm = slow_chunk_cm
        self.bypass_distance_cm = bypass_distance_cm
        self.turn_speed_level = turn_speed_level
        self.bypass_speed_level = bypass_speed_level
        self.sensor_settle_seconds = sensor_settle_seconds
        self.reset()

    def reset(self) -> None:
        self.active = False
        self.remaining_cm = 0.0
        self.requested_speed_level = 1
        self.phase = "IDLE"
        self.pending: PlannedAction | None = None
        self.latest_distance_cm: float | None = None
        self.latest_distance_at = 0.0
        self.check_after = 0.0

    def start(self, distance_cm: float, speed_level: int, now: float = 0.0) -> None:
        self.reset()
        self.active = True
        self.remaining_cm = distance_cm
        self.requested_speed_level = speed_level
        # Require a fresh front reading before the first movement.
        self.phase = "CHECK"
        self.check_after = now

    def observe_distance(self, distance_cm: float | None, now: float) -> bool:
        """Store a reading; return True when the active forward part must stop."""
        self.latest_distance_cm = distance_cm
        self.latest_distance_at = now
        if not (
            self.active and self.pending is not None
            and self.pending.counts_toward_goal and distance_cm is not None
        ):
            return False
        # Stop a fast chunk as soon as the slow zone is entered. Once already
        # moving in level 1 short chunks, stop only at the final clearance.
        return (
            distance_cm <= self.stop_distance_cm
            or (
                distance_cm <= self.slow_distance_cm
                and self.pending.speed_level != 1
            )
        )

    def interrupted_for_obstacle(self) -> None:
        # Do not subtract an interrupted chunk: without an Arduino DONE there is
        # no reliable completed-distance value. This errs toward fulfilling the
        # requested distance rather than silently stopping short.
        self.pending = None

    def action_done(self, now: float) -> None:
        action = self.pending
        self.pending = None
        if action is None:
            return
        if action.counts_toward_goal:
            self.remaining_cm = max(0.0, self.remaining_cm - action.value)
            return
        if self.phase == "TURN_LEFT":
            self.phase = "BYPASS"
        elif self.phase == "BYPASS":
            self.phase = "TURN_RIGHT"
        elif self.phase == "TURN_RIGHT":
            self.phase = "CHECK"
            self.check_after = now + self.sensor_settle_seconds

    def next_action(self, now: float) -> PlannedAction | None:
        if not self.active or self.pending is not None:
            return None
        if self.phase == "CHECK":
            if (
                now < self.check_after
                or self.latest_distance_at <= self.check_after
                or self.latest_distance_cm is None
            ):
                return None
            self.phase = (
                "TURN_LEFT" if self._obstacle_is_close() else "FORWARD"
            )
        if self.phase == "FORWARD":
            if self.remaining_cm <= 0.0:
                self.active = False
                self.phase = "DONE"
                return None
            if self._obstacle_is_close():
                self.phase = "TURN_LEFT"
            else:
                slow = (
                    self.latest_distance_cm is not None
                    and self.latest_distance_cm <= self.slow_distance_cm
                )
                chunk = self.slow_chunk_cm if slow else self.fast_chunk_cm
                self.pending = PlannedAction(
                    "MOVE", "FWD", 1 if slow else self.requested_speed_level,
                    min(chunk, self.remaining_cm), True,
                )
                return self.pending
        if self.phase == "TURN_LEFT":
            self.pending = PlannedAction(
                "TURN", "LEFT", self.turn_speed_level, 90.0
            )
        elif self.phase == "BYPASS":
            self.pending = PlannedAction(
                "MOVE", "FWD", self.bypass_speed_level,
                self.bypass_distance_cm,
            )
        elif self.phase == "TURN_RIGHT":
            self.pending = PlannedAction(
                "TURN", "RIGHT", self.turn_speed_level, 90.0
            )
        return self.pending

    def _obstacle_is_close(self) -> bool:
        return (
            self.latest_distance_cm is not None
            and self.latest_distance_cm <= self.stop_distance_cm
        )


def parse_ultrasonic_distance(state_line: str) -> float | None:
    """Extract US=<cm> from Arduino STATE telemetry; NA means no echo."""
    for field in state_line.split(","):
        if field.startswith("US="):
            value = field[3:]
            if value == "NA":
                return None
            try:
                return float(value)
            except ValueError:
                return None
    return None
