"""Read the left stick of a USB Xbox controller using pygame."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from config import LEFT_STICK_DEADZONE


LEFT_STICK_HORIZONTAL_AXIS = 0
LEFT_STICK_VERTICAL_AXIS = 1
X_BUTTON = 2
Y_BUTTON = 3


@dataclass(frozen=True)
class ControllerState:
    """One controller sample in robot coordinates."""

    x: float
    y: float
    estop_pressed: bool
    reset_pressed: bool
    dpad_x: int
    dpad_y: int

    def as_dict(self) -> dict[str, float]:
        return {
            "x": round(self.x, 3),
            "y": round(self.y, 3),
        }


class XboxController:
    """Manage an Xbox controller and expose its current left-stick state."""

    def __init__(self, deadzone: float = LEFT_STICK_DEADZONE) -> None:
        if not 0.0 <= deadzone < 1.0:
            raise ValueError("deadzone must be in the range [0.0, 1.0)")

        self.deadzone = deadzone
        self._controller: pygame.joystick.Joystick | None = None

    @property
    def name(self) -> str:
        if self._controller is None:
            return "Disconnected"
        return self._controller.get_name()

    def connect(self) -> None:
        pygame.init()
        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            raise RuntimeError(
                "No controller detected. Connect the Xbox controller by USB."
            )

        controller = pygame.joystick.Joystick(0)
        controller.init()

        if controller.get_numaxes() < 2:
            controller.quit()
            raise RuntimeError("The controller does not expose two stick axes.")
        if controller.get_numhats() < 1:
            controller.quit()
            raise RuntimeError("The controller does not expose a D-pad hat.")
        required_button = max(X_BUTTON, Y_BUTTON)
        if controller.get_numbuttons() <= required_button:
            button_count = controller.get_numbuttons()
            controller.quit()
            raise RuntimeError(
                f"The controller exposes only {button_count} buttons; "
                f"button {required_button} is unavailable."
            )

        self._controller = controller

    def read(self) -> ControllerState:
        if self._controller is None:
            raise RuntimeError("Controller is not connected.")

        pygame.event.pump()
        horizontal = self._apply_deadzone(
            self._controller.get_axis(LEFT_STICK_HORIZONTAL_AXIS)
        )
        vertical = self._apply_deadzone(
            self._controller.get_axis(LEFT_STICK_VERTICAL_AXIS)
        )
        dpad_x, dpad_y = self._controller.get_hat(0)

        # Robot coordinates: facing forward is +x; right is +y.
        return ControllerState(
            x=-vertical,
            y=horizontal,
            estop_pressed=bool(self._controller.get_button(Y_BUTTON)),
            reset_pressed=bool(self._controller.get_button(X_BUTTON)),
            dpad_x=dpad_x,
            dpad_y=dpad_y,
        )

    def close(self) -> None:
        if self._controller is not None:
            self._controller.quit()
            self._controller = None
        pygame.quit()

    def _apply_deadzone(self, value: float) -> float:
        if abs(value) <= self.deadzone:
            return 0.0

        sign = 1.0 if value > 0 else -1.0
        adjusted = sign * (abs(value) - self.deadzone) / (1.0 - self.deadzone)
        return max(-1.0, min(1.0, adjusted))

    def __enter__(self) -> "XboxController":
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
