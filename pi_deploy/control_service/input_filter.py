"""Real-time filtering for joystick input."""

from __future__ import annotations


class InputFilter:
    """Deadzone followed by an exponential moving average."""

    def __init__(self, alpha: float, deadzone: float = 0.0) -> None:
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1]")
        if not 0.0 <= deadzone < 1.0:
            raise ValueError("deadzone must be in [0, 1)")
        self.alpha = alpha
        self.deadzone = deadzone
        self._x = 0.0
        self._y = 0.0

    def update(self, x: float, y: float) -> tuple[float, float]:
        x = self._apply_deadzone(x)
        y = self._apply_deadzone(y)
        # A centered stick is a stop request, not another value to smooth.
        # Clear each axis immediately so an EMA tail cannot keep driving the
        # motors after the operator releases the stick.
        if x == 0.0:
            self._x = 0.0
        else:
            self._x += self.alpha * (x - self._x)
        if y == 0.0:
            self._y = 0.0
        else:
            self._y += self.alpha * (y - self._y)
        return self._x, self._y

    def reset(self) -> None:
        self._x = 0.0
        self._y = 0.0

    def _apply_deadzone(self, value: float) -> float:
        if abs(value) <= self.deadzone:
            return 0.0
        sign = 1.0 if value > 0.0 else -1.0
        return sign * (abs(value) - self.deadzone) / (1.0 - self.deadzone)
