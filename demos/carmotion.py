"""
VehicleMotion v1.2
Arcade vehicle controller – heading + velocity + grip

Integrates with motion2d.KinematicBody for position/velocity/drag/max-speed.
Extensible via hooks for future transmissions, surfaces, and handling effects.

Core idea:
    Heading and velocity may disagree.
    Grip pulls the lateral component of velocity toward zero.
    Drift emerges naturally.
"""

from __future__ import annotations
import math
from typing import Union

# Integrate with your existing motion2d library!
from motion2d import KinematicBody, Vector2


def _angle_to_vec(deg: float) -> Vector2:
    """Convert degrees to unit Vector2 (avoiding pygame.Vector2.from_angle)."""
    rad = math.radians(deg)
    return Vector2(math.cos(rad), math.sin(rad))


class VehicleMotion:
    """
    Arcade-style vehicle controller.

    Usage:
        car = VehicleMotion((0, 0), max_speed=500, acceleration=2000, grip=8.0)
        car.throttle(1.0)
        car.steer(0.5)
        car.update(1/60)
    """

    def __init__(
        self,
        pos: Union[tuple, Vector2] = (0, 0),
        *,
        max_speed: float = 450.0,
        acceleration: float = 1800.0,
        brake_force: float = 3200.0,
        turn_speed: float = 140.0,
        grip: float = 9.0,
        handbrake_grip: float = 2.8,
        drag: float = 0.8,           # reduced because KinematicBody applies it per-second
        sleep_threshold: float = 0.1,
        angle: float = 0.0,
        steering_falloff: float = 0.65,  # how much speed reduces turning (0=no falloff, 1=full)
        min_turn_factor: float = 0.35,   # minimum steering effectiveness at top speed
    ):
        # 1. Reuse KinematicBody (handles pos, vel, drag, max_speed, integration)
        self.body = KinematicBody(
            pos=pos,
            max_speed=max_speed,
            drag=drag,
            sleep_threshold=sleep_threshold
        )

        # 2. Heading is a raw float (rate-based steering, per Grok's advice)
        self.angle = float(angle) % 360.0

        # 3. Core physics parameters (NO drive type in v1!)
        self.acceleration = float(acceleration)
        self.brake_force = float(brake_force)
        self.turn_speed = float(turn_speed)
        self.grip = float(grip)
        self.handbrake_grip = float(handbrake_grip)
        self.steering_falloff = float(steering_falloff)
        self.min_turn_factor = float(min_turn_factor)

        # 4. Inputs (cleared after each update)
        self._throttle = 0.0
        self._brake = 0.0
        self._steer = 0.0
        self._handbrake = False

        # 5. Diagnostics
        self.slip_angle = 0.0
        self.is_drifting = False

    # ------------------------------------------------------------------
    # Input API
    # ------------------------------------------------------------------
    def throttle(self, amount: float) -> None:
        self._throttle = max(0.0, min(1.0, float(amount)))

    def brake(self, amount: float) -> None:
        self._brake = max(0.0, min(1.0, float(amount)))

    def steer(self, amount: float) -> None:
        self._steer = max(-1.0, min(1.0, float(amount)))

    def handbrake(self, active: bool = True) -> None:
        self._handbrake = bool(active)

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------
    @property
    def position(self) -> Vector2:
        return self.body.position

    @property
    def velocity(self) -> Vector2:
        return self.body.velocity

    @velocity.setter
    def velocity(self, value: Vector2) -> None:
        self.body.velocity = value

    @property
    def speed(self) -> float:
        return self.body.speed

    @property
    def heading_angle(self) -> float:
        return self.angle

    # ------------------------------------------------------------------
    # EXTENSION HOOKS – override these in subclasses for advanced physics
    # ------------------------------------------------------------------
    def _get_acceleration(self) -> float:
        """
        Return current forward acceleration (units/s²).
        Future: multiply by transmission efficiency, gear ratio, or torque curve.
        """
        return self._throttle * self.acceleration

    def _get_brake_deceleration(self) -> float:
        """
        Return current braking deceleration (units/s²).
        Future: add engine braking, regenerative braking, or surface modifiers.
        """
        return self._brake * self.brake_force

    def _get_turn_speed(self) -> float:
        """
        Return current turning rate (degrees/s).
        Override for power-steering, understeer/oversteer bias, or drift assists.
        """
        speed = self.speed
        if speed < 1.0:
            return 0.0  # cannot turn while stationary

        # Speed-sensitive steering: less turning at high speeds
        factor = 1.0 - (speed / self.body.max_speed) * self.steering_falloff
        factor = max(self.min_turn_factor, factor)
        return self._steer * self.turn_speed * factor

    def _get_grip(self) -> float:
        """
        Return lateral grip damping factor (1/s).
        Future: modify based on surface type, downforce, tire wear, or weight transfer.
        """
        if self._handbrake:
            return self.handbrake_grip
        return self.grip

    # ------------------------------------------------------------------
    # Main update
    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        if dt <= 0.0:
            self._clear_inputs()
            return
        dt = min(float(dt), 0.05)  # safety clamp

        speed = self.speed

        # 1. Steering (rate-based, speed-sensitive)
        self.angle += self._get_turn_speed() * dt
        self.angle %= 360.0

        # 2. Decompose current velocity along heading and right
        heading = _angle_to_vec(self.angle)
        right = _angle_to_vec(self.angle + 90.0)

        forward_speed = self.body.vel.dot(heading)
        lateral_speed = self.body.vel.dot(right)

        # 3. Propulsion (throttle) – pure, honest acceleration!
        forward_speed += self._get_acceleration() * dt

        # 4. Braking (always opposes current forward movement)
        brake_dec = self._get_brake_deceleration() * dt
        if abs(forward_speed) > 0.5:
            if forward_speed > 0.0:
                forward_speed = max(0.0, forward_speed - brake_dec)
            else:
                forward_speed = min(0.0, forward_speed + brake_dec)

        # NOTE: Drag and max_speed are handled AUTOMATICALLY by self.body.update(dt)
        #       so we don't need to clamp forward_speed or apply drag here.

        # 5. Lateral grip (exponential damping toward zero)
        lateral_speed *= math.exp(-self._get_grip() * dt)

        # 6. Recombine into a world-space velocity
        self.body.vel = heading * forward_speed + right * lateral_speed

        # 7. Let KinematicBody handle drag, max-speed, sleep, and position integration
        self.body.update(dt)

        # 8. Diagnostics
        if speed > 1.0:
            vel_angle = math.degrees(math.atan2(self.body.vel.y, self.body.vel.x))
        else:
            vel_angle = self.angle

        self.slip_angle = (vel_angle - self.angle + 540.0) % 360.0 - 180.0
        self.is_drifting = (speed > 80.0) and (abs(self.slip_angle) > 18.0)

        # 9. Clear inputs (matches BaseMotion style – prevents sticky controls)
        self._clear_inputs()

    def _clear_inputs(self) -> None:
        """Reset all input states. Called automatically at end of update()."""
        self._throttle = 0.0
        self._brake = 0.0
        self._steer = 0.0
        self._handbrake = False

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------
    def stop(self) -> None:
        """Instantly stop the vehicle and clear all inputs."""
        self.body.vel = Vector2(0.0, 0.0)
        self._clear_inputs()

    def reset(self, pos=(0, 0), angle: float = 0.0) -> None:
        """Reset position, heading, velocity, and inputs."""
        self.body.position = Vector2(*pos) if not isinstance(pos, Vector2) else pos.copy()
        self.body.vel = Vector2(0.0, 0.0)
        self.angle = float(angle) % 360.0
        self._clear_inputs()
        self.slip_angle = 0.0
        self.is_drifting = False

    # ------------------------------------------------------------------
    # Presets (NO drive type – purely handling & physics differences)
    # ------------------------------------------------------------------
    @classmethod
    def preset(cls, name: str, pos=(0, 0)) -> "VehicleMotion":
        name = name.lower().strip()
        presets = {
            "mom_car": dict(
                max_speed=420, acceleration=1600, brake_force=3000,
                turn_speed=120, grip=11.0, handbrake_grip=3.5, drag=0.8,
            ),
            "sport": dict(
                max_speed=580, acceleration=2400, brake_force=3800,
                turn_speed=160, grip=8.5, handbrake_grip=2.5, drag=0.6,
            ),
            "arcade": dict(
                max_speed=520, acceleration=2200, brake_force=3400,
                turn_speed=170, grip=6.0, handbrake_grip=1.8, drag=0.5,
            ),
            "truck": dict(
                max_speed=320, acceleration=900, brake_force=2800,
                turn_speed=70, grip=10.0, handbrake_grip=4.0, drag=1.2,
            ),
            "drift": dict(
                max_speed=500, acceleration=2100, brake_force=3000,
                turn_speed=155, grip=5.2, handbrake_grip=1.4, drag=0.4,
            ),
            "f1": dict(
                max_speed=720, acceleration=3200, brake_force=5200,
                turn_speed=200, grip=13.0, handbrake_grip=6.0, drag=0.3,
            ),
        }
        if name not in presets:
            raise ValueError(f"Unknown preset '{name}'. Available: {list(presets.keys())}")
        return cls(pos=pos, **presets[name])


# ------------------------------------------------------------------
# Quick self-test
# ------------------------------------------------------------------
if __name__ == "__main__":
    car = VehicleMotion.preset("sport")
    print("Created:", car)
    print("(Transmission & drivetrain intentionally removed for v1)")

    # Simulate 1 second of full throttle + slight turn
    for _ in range(60):
        car.throttle(1.0)
        car.steer(0.3)
        car.update(1 / 60)

    print(f"After 1s: speed={car.speed:.1f}, slip={car.slip_angle:.1f}°, drifting={car.is_drifting}")
    print(f"Position: {car.position}")