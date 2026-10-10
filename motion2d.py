
import math
from typing import Optional, Union, Sequence

EPSILON = 1e-6

# --- Minimal Vector2 replacement for pygame.math.Vector2 ---
# Designed for Python 3.8+, __slots__, no extra allocations
class Vector2:
    __slots__ = ('x', 'y')

    def __init__(self, *args):
        # Vector2(), Vector2(v), Vector2((x,y)), Vector2(x,y)
        if len(args) == 0:
            self.x = 0.0
            self.y = 0.0
        elif len(args) == 1:
            a = args[0]
            # copy from Vector2-like (has x,y)
            if isinstance(a, Vector2):
                self.x = float(a.x)
                self.y = float(a.y)
            elif isinstance(a, (list, tuple)):
                # allow (x,y) sequence
                if len(a) != 2:
                    raise ValueError("Vector2 sequence must have 2 elements")
                self.x = float(a[0])
                self.y = float(a[1])
            else:
                # object with x,y attributes (duck typing for other vec types)
                try:
                    self.x = float(a[0])  # type: ignore
                    self.y = float(a[1])  # type: ignore
                except Exception:
                    try:
                        self.x = float(a.x)  # type: ignore
                        self.y = float(a.y)  # type: ignore
                    except Exception:
                        raise TypeError("Vector2() arg must be Vector2 or sequence of 2 floats")
        elif len(args) == 2:
            self.x = float(args[0])
            self.y = float(args[1])
        else:
            raise TypeError("Vector2() takes 0, 1 or 2 arguments")

    # ---- core metrics ----
    def length_squared(self):
        # type: () -> float
        return self.x * self.x + self.y * self.y

    def length(self):
        # type: () -> float
        return math.hypot(self.x, self.y)

    def dot(self, other):
        # type: (Union[Vector2, Sequence[float]]) -> float
        try:
            ox = float(other[0])
            oy = float(other[1])
        except Exception:
            ox = float(other.x)
            oy = float(other.y)  # type: ignore
        return self.x * ox + self.y * oy

    def as_polar(self):
        # type: () -> Tuple[float, float]
        # returns (r, angle_deg) like pygame: angle from +X, CCW, degrees
        r = math.hypot(self.x, self.y)
        theta = math.degrees(math.atan2(self.y, self.x))
        return (r, theta)

    def rotate(self, angle_deg):
        # type: (float) -> Vector2
        # CCW rotation, returns new vector (pygame compatible)
        if angle_deg == 0:
            return Vector2(self.x, self.y)
        rad = math.radians(angle_deg)
        c = math.cos(rad)
        s = math.sin(rad)
        return Vector2(self.x * c - self.y * s, self.x * s + self.y * c)

    def normalize(self):
        # type: () -> Vector2
        lsq = self.x * self.x + self.y * self.y
        if lsq <= 1e-12:  # guard - pygame would return (0,0) for very small?
            return Vector2(0.0, 0.0)
        inv = 1.0 / math.sqrt(lsq)
        return Vector2(self.x * inv, self.y * inv)

    def normalize_ip(self):
        # type: () -> None
        lsq = self.x * self.x + self.y * self.y
        if lsq <= 1e-12:
            self.x = 0.0
            self.y = 0.0
            return None
        inv = 1.0 / math.sqrt(lsq)
        self.x *= inv
        self.y *= inv
        return None

    def scale_to_length(self, new_len):
        # type: (float) -> None
        lsq = self.x * self.x + self.y * self.y
        if lsq <= 1e-12:
            return None
        cur = math.sqrt(lsq)
        if cur == 0:
            return None
        f = float(new_len) / cur
        self.x *= f
        self.y *= f
        return None

    # ---- operators ----
    def __add__(self, other):
        try:
            ox = float(other[0])
            oy = float(other[1])
        except Exception:
            ox = float(other.x)
            oy = float(other.y)  # type: ignore
        return Vector2(self.x + ox, self.y + oy)

    def __sub__(self, other):
        try:
            ox = float(other[0])
            oy = float(other[1])
        except Exception:
            ox = float(other.x)
            oy = float(other.y)  # type: ignore
        return Vector2(self.x - ox, self.y - oy)

    def __mul__(self, scalar):
        # type: (float) -> Vector2
        # only scalar mul is used in Motion2D, but allow vector check to error clearly
        if isinstance(scalar, (int, float)):
            return Vector2(self.x * scalar, self.y * scalar)
        # if user does vector * vector, fall back to trying sequence? not needed
        raise TypeError("Vector2 can only be multiplied by scalar")

    def __rmul__(self, scalar):
        if isinstance(scalar, (int, float)):
            return Vector2(self.x * scalar, self.y * scalar)
        raise TypeError("Vector2 can only be multiplied by scalar")

    def __truediv__(self, scalar):
        # type: (float) -> Vector2
        return Vector2(self.x / scalar, self.y / scalar)

    def __neg__(self):
        return Vector2(-self.x, -self.y)

    def __pos__(self):
        return Vector2(self.x, self.y)

    def __iadd__(self, other):
        try:
            ox = float(other[0])
            oy = float(other[1])
        except Exception:
            ox = float(other.x)
            oy = float(other.y)  # type: ignore
        self.x += ox
        self.y += oy
        return self

    def __isub__(self, other):
        try:
            ox = float(other[0])
            oy = float(other[1])
        except Exception:
            ox = float(other.x)
            oy = float(other.y)  # type: ignore
        self.x -= ox
        self.y -= oy
        return self

    def __imul__(self, scalar):
        # type: (float) -> Vector2
        # used as lateral *= exp(-grip*dt)
        s = float(scalar)
        self.x *= s
        self.y *= s
        return self

    def __itruediv__(self, scalar):
        s = float(scalar)
        self.x /= s
        self.y /= s
        return self

    def __iter__(self):
        yield self.x
        yield self.y

    def __getitem__(self, idx):
        if idx == 0:
            return self.x
        if idx == 1:
            return self.y
        raise IndexError("Vector2 index out of range")

    def __setitem__(self, idx, value):
        if idx == 0:
            self.x = float(value)
        elif idx == 1:
            self.y = float(value)
        else:
            raise IndexError("Vector2 index out of range")

    def __eq__(self, other):
        try:
            ox = float(other[0])
            oy = float(other[1])
        except Exception:
            try:
                ox = float(other.x)
                oy = float(other.y)  # type: ignore
            except Exception:
                return False
        return self.x == ox and self.y == oy

    def __repr__(self):
        return "Vector2({:.6g}, {:.6g})".format(self.x, self.y)

    def __bool__(self):
        return self.x != 0.0 or self.y != 0.0

    def copy(self):
        return Vector2(self.x, self.y)

VectorLike = Union[Vector2, Sequence[float]]


EPSILON = 1e-6

VectorLike = Union[Vector2, Sequence[float]]

# Safety clamp for frame time. Applied at each entry point that
# consumes dt. The clamp is idempotent — clamping an already-clamped
# value is a no-op — so duplicated application is safe.
MAX_DT = 0.1


class Heading:
    """
    Base class for all heading types.
    The common shared method is only aim, the rest are user-called specific.
    """

    @property
    def vector(self) -> Vector2:
        """Return direction as Vector2."""
        raise NotImplementedError()

    def aim(self, direction: VectorLike, dt: float = 1 / 60, snap: bool = False) -> bool:
        """Aim toward a direction."""
        raise NotImplementedError()

    def turn_left(self, dt: float = 1 / 60) -> None:
        raise NotImplementedError

    def turn_right(self, dt: float = 1 / 60) -> None:
        raise NotImplementedError


class Rotator(Heading):
    """
    Simple, responsive angular controller.
    No inertia, no physics, no oscillation.

    Perfect for turrets, aiming, or any object that rotates smoothly.
    """

    def __init__(self, angle: float = 0.0, rotate_speed: float = 180.0):
        if rotate_speed < 0:
            raise ValueError("rotate_speed must be non-negative")

        self.angle = float(angle) % 360
        self.rotate_speed = float(rotate_speed)

    @property
    def vector(self) -> Vector2:
        return Vector2(1, 0).rotate(self.angle)

    def rotate(self, direction: float, dt: float) -> None:
        """Apply rotation at fixed speed."""
        if dt <= 0 or direction == 0:
            return
        direction = max(-1.0, min(1.0, float(direction)))
        step = self.rotate_speed * direction * dt
        self.angle = (self.angle + step) % 360.0

    def turn_toward(self, target_angle: float, dt: float) -> bool:
        """Rotate toward target angle at fixed speed. Return True if it align, False if it's turning"""
        if dt <= 0:
            return False

        target_angle = float(target_angle) % 360.0
        # Check if already at target (with tolerance)
        if abs(target_angle - self.angle) < EPSILON:
            return True

        difference = (target_angle - self.angle + 180.0) % 360.0 - 180.0
        speed = self.rotate_speed * dt

        if abs(difference) <= speed:
            self.angle = target_angle
            return True
        else:
            self.angle += speed if difference > 0 else -speed
            self.angle %= 360.0
            return False

    def aim(self, direction: VectorLike = (1, 0), dt: float = 1 / 60, snap: bool = False) -> bool:
        """
        Unified aiming method. dt is only used when snap is False.
        Return True if it's aligned, False if it's still turning
        """
        direction = Vector2(direction)
        if direction.length_squared() > EPSILON:
            target_angle = direction.as_polar()[1] % 360.0
            if snap:
                self.angle = target_angle
                return True
            else:
                return self.turn_toward(target_angle, dt)
        return False

    # --- Helpers ---
    def left(self) -> None:
        self.angle = 180.0

    def right(self) -> None:
        self.angle = 0.0

    def up(self) -> None:
        self.angle = 270.0

    def down(self) -> None:
        self.angle = 90.0

    def flip(self) -> None:
        self.angle = (self.angle + 180.0) % 360.0

    def turn_left(self, dt: float = 1 / 60) -> None:
        self.rotate(-1, dt)

    def turn_right(self, dt: float = 1 / 60) -> None:
        self.rotate(1, dt)


class Facing(Heading):
    """
    Simple 2D facing direction.

    directions:
        0 = free / continuous direction
        2 = two directions only
        4 = four cardinal directions
        8 = eight snapped directions

    axis:
        only used when directions == 2
        "horizontal" = left/right
        "vertical"   = up/down
    """

    def __init__(self, initial_vector: VectorLike = (1, 0), directions: int = 0, axis: str = 'horizontal'):
        if directions not in (0, 2, 4, 8):
            raise ValueError("directions must be 0, 2, 4, or 8")

        if axis.lower() not in ['horizontal', 'vertical']:
            raise ValueError("axis must be 'horizontal' or 'vertical'")

        self.directions = directions
        self.axis = axis.lower()
        self._name_direction = None
        if self.directions == 2 and self.axis == 'vertical':
            self._vector = Vector2(0, 1)
        else:
            self._vector = Vector2(1, 0)
        self.aim(initial_vector)

    @property
    def vector(self) -> Vector2:
        return self._vector

    def aim(self, direction: VectorLike = (1, 0), dt: float = 1 / 60, snap: bool = False) -> bool:
        """Facing doesn't need the dt and snap and will be ignored"""
        vec = Vector2(direction)
        if vec.length_squared() <= EPSILON:
            return True
        self._vector = vec

        if self.directions == 0:
            self._vector = self._vector.normalize()
            self._name_direction = None
            return True

        elif self.directions == 2:
            if self.axis == 'horizontal':
                if abs(self._vector.x) > EPSILON:
                    self._name_direction = 'right' if self._vector.x > 0 else 'left'
                    self._vector = Vector2(1 if self._vector.x > 0 else -1, 0)
                    return True
            elif self.axis == 'vertical':
                if abs(self._vector.y) > EPSILON:
                    self._name_direction = 'down' if self._vector.y > 0 else 'up'
                    self._vector = Vector2(0, 1 if self._vector.y > 0 else -1)
                    return True

        elif self.directions == 4:
            if abs(self._vector.x) >= abs(self._vector.y):
                self._name_direction = 'right' if self._vector.x > 0 else 'left'
                self._vector = Vector2(1 if self._vector.x > 0 else -1, 0)
                return True
            else:
                self._name_direction = 'down' if self._vector.y > 0 else 'up'
                self._vector = Vector2(0, 1 if self._vector.y > 0 else -1)
                return True

        elif self.directions == 8:
            self._vector = self._vector.normalize()
            angle = self._vector.as_polar()[1]
            snapped = round(angle / 45) * 45
            self._vector = Vector2(1, 0).rotate(snapped)

            # Map the exact angle directly to the string, avoiding float traps
            angle_map = {
                0: 'right',
                45: 'down_right',
                90: 'down',
                135: 'down_left',
                180: 'left',
                -135: 'up_left',
                -90: 'up',
                -45: 'up_right'
            }
            # Handle float rounding oddities safely
            normalized_angle = int(snapped) if snapped != -180 else 180
            if normalized_angle in angle_map:
                self._name_direction = angle_map[normalized_angle]
                return True

        return False

    # --- Helpers ---
    def set_direction(self, vector) -> None:
        self.aim(vector)

    def up_left(self) -> None:
        self.aim((-1, -1))

    def left(self) -> None:
        self.aim((-1, 0))

    def down_left(self) -> None:
        self.aim((-1, 1))

    def down(self) -> None:
        self.aim((0, 1))

    def down_right(self) -> None:
        self.aim((1, 1))

    def right(self) -> None:
        self.aim((1, 0))

    def up_right(self) -> None:
        self.aim((1, -1))

    def up(self) -> None:
        self.aim((0, -1))

    def flip(self) -> None:
        self.aim(self.vector * -1)

    def is_left(self, exact: bool = False) -> bool:
        if self.directions == 0:
            return self._vector.x < -0.5
        else:
            if exact:
                return self._name_direction == 'left'
            else:
                return 'left' in self._name_direction

    def is_right(self, exact: bool = False) -> bool:
        if self.directions == 0:
            return self._vector.x > 0.5
        else:
            if exact:
                return self._name_direction == 'right'
            else:
                return 'right' in self._name_direction

    def is_up(self, exact: bool = False) -> bool:
        if self.directions == 0:
            return self._vector.y < -0.5
        else:
            if exact:
                return self._name_direction == 'up'
            else:
                return 'up' in self._name_direction

    def is_down(self, exact: bool = False) -> bool:
        if self.directions == 0:
            return self._vector.y > 0.5
        else:
            if exact:
                return self._name_direction == 'down'
            else:
                return 'down' in self._name_direction

    def is_up_left(self) -> bool:
        if self.directions == 0:
            return self._vector.x < -0.5 and self._vector.y < -0.5
        else:
            return self._name_direction == 'up_left'

    def is_up_right(self) -> bool:
        if self.directions == 0:
            return self._vector.x > 0.5 and self._vector.y < -0.5
        else:
            return self._name_direction == 'up_right'

    def is_down_right(self) -> bool:
        if self.directions == 0:
            return self._vector.x > 0.5 and self._vector.y > 0.5
        else:
            return self._name_direction == 'down_right'

    def is_down_left(self) -> bool:
        if self.directions == 0:
            return self._vector.x < -0.5 and self._vector.y > 0.5
        else:
            return self._name_direction == 'down_left'

    def turn_left(self, dt: float = 1 / 60) -> None:
        '''Don't forget to use keydown instead of keypress because this is instant!'''
        if self.directions == 2:
            self.flip()
        elif self.directions == 4:
            self._vector = self._vector.rotate(-90)
        elif self.directions == 8:
            self._vector = self._vector.rotate(-45)

    def turn_right(self, dt: float = 1 / 60) -> None:
        '''Don't forget to use keydown instead of keypress because this is instant!'''
        if self.directions == 2:
            self.flip()
        elif self.directions == 4:
            self._vector = self._vector.rotate(90)
        elif self.directions == 8:
            self._vector = self._vector.rotate(45)


class NoHeading(Heading):
    """
    Null heading that does nothing.
    All methods are no-ops or return default values.
    Note that all heading related movement will cause no movement with this.
    """

    def __init__(self, default_direction: VectorLike = (0, 0)):
        self._default = Vector2(default_direction)
        if self._default.length_squared() > EPSILON:
            self._default.normalize_ip()
        else:
            self._default = Vector2(0, 0)

    @property
    def vector(self) -> Vector2:
        """Return default direction."""
        return self._default

    def aim(self, direction: VectorLike = (1, 0), dt: float = 1 / 60, snap: bool = False) -> bool:
        """ For polymorphism purposes, intentionally no operation here"""
        return False

    def turn_left(self, dt: float = 1 / 60) -> None:
        pass

    def turn_right(self, dt: float = 1 / 60) -> None:
        pass


class KinematicBody:
    """
    Pure 2D kinematic engine.

    Handles position, velocity, forces, drag, and integration.
    """

    def __init__(
        self,
        pos: VectorLike = (0, 0),
        *,
        max_speed: Optional[float] = None,
        max_x_speed: Optional[float] = None,
        max_y_speed: Optional[float] = None,
        drag: float = 0.0,
        sleep_threshold: float = 0.1,  # Velocity below this is rounded to zero
    ):
        if drag < 0:
            raise ValueError("drag must be non-negative")
        for name, value in (("max_speed", max_speed),
                            ("max_x_speed", max_x_speed),
                            ("max_y_speed", max_y_speed)):
            if value is not None and value <= 0:
                raise ValueError(f"{name} must be positive or None")
        if sleep_threshold < 0:
            raise ValueError("sleep_threshold must be non-negative")

        self.pos = Vector2(pos)
        self.vel = Vector2(0, 0)
        self.max_speed = max_speed
        self.max_x_speed = max_x_speed
        self.max_y_speed = max_y_speed
        self.drag = float(drag)
        self.sleep_threshold = float(sleep_threshold)

        # Internal: track which axes received input (for drag skipping)
        self._active_x = False
        self._active_y = False

    @property
    def position(self) -> Vector2:
        return self.pos

    @position.setter
    def position(self, value: VectorLike) -> None:
        self.pos = Vector2(value)

    @property
    def velocity(self) -> Vector2:
        return self.vel

    @velocity.setter
    def velocity(self, value: VectorLike) -> None:
        self.vel = Vector2(value)

    @property
    def speed(self) -> float:
        return self.vel.length()

    def mark_active(self, x: bool = False, y: bool = False) -> None:
        """Mark axes as actively receiving input (prevents drag on these axes)."""
        if x:
            self._active_x = True
        if y:
            self._active_y = True

    def apply_force(self, force: VectorLike, dt: float) -> None:
        """Apply a continuous mass-independent force."""
        if dt <= 0:
            return
        f = Vector2(force)
        self.vel += f * dt
        if abs(f.x) > EPSILON:
            self._active_x = True
        if abs(f.y) > EPSILON:
            self._active_y = True

    def apply_impulse(self, impulse: VectorLike) -> None:
        """Apply an instantaneous velocity change."""
        imp = Vector2(impulse)
        self.vel += imp
        if abs(imp.x) > EPSILON:
            self._active_x = True
        if abs(imp.y) > EPSILON:
            self._active_y = True

    def set_velocity(self, x: Optional[float] = None, y: Optional[float] = None) -> None:
        """Directly override velocity components."""
        if x is not None:
            self.vel.x = float(x)
        if y is not None:
            self.vel.y = float(y)

    def stop(self, x: bool = True, y: bool = True) -> None:
        """Instantly stop selected velocity axes."""
        if x:
            self.vel.x = 0.0
        if y:
            self.vel.y = 0.0

    def reset(self, pos: Optional[VectorLike] = None, vel: Optional[VectorLike] = None) -> None:
        """Reset position and/or velocity."""
        if pos is not None:
            self.pos = Vector2(pos)
        if vel is not None:
            self.vel = Vector2(vel)
        self._active_x = False
        self._active_y = False

    def step_velocity(self, dt: float) -> Vector2:
        """
        Advance the body's velocity state by one timestep.
        Does NOT commit position.

        Returns the proposed position delta (velocity * effective_dt).
        The effective dt is clamped to MAX_DT for safety; callers receive
        the delta computed with the same dt the velocity was updated with,
        so external collision sees the actual movement proposed.

        Use this when the game owns collision:
            delta = motion.step_velocity(dt)
            result = my_collision_resolver(position, delta)
            motion.position = result.position

        Contrast with update(dt), which also integrates position.
        """
        if dt <= 0:
            self._active_x = False
            self._active_y = False
            return Vector2(0, 0)

        dt = min(float(dt), MAX_DT)  # Safety clamp

        # Apply exponential drag (only on axes without input)
        if self.drag > 0:
            factor = math.exp(-self.drag * dt)
            if not self._active_x:
                self.vel.x *= factor
            if not self._active_y:
                self.vel.y *= factor

        # Sleep threshold (only on inactive axes)
        if not self._active_x and abs(self.vel.x) < self.sleep_threshold:
            self.vel.x = 0.0
        if not self._active_y and abs(self.vel.y) < self.sleep_threshold:
            self.vel.y = 0.0

        # Apply speed limits
        if self.max_x_speed is not None:
            self.vel.x = max(-self.max_x_speed, min(self.max_x_speed, self.vel.x))
        if self.max_y_speed is not None:
            self.vel.y = max(-self.max_y_speed, min(self.max_y_speed, self.vel.y))
        if self.max_speed is not None and self.vel.length_squared() > self.max_speed ** 2:
            self.vel.scale_to_length(self.max_speed)

        # Compute proposed delta (with the effective, clamped dt)
        delta = self.vel * dt

        # Reset active flags
        self._active_x = False
        self._active_y = False

        return delta

    def update(self, dt: float) -> None:
        """Apply damping/limits and advance position by dt seconds."""
        delta = self.step_velocity(dt)
        self.pos += delta


class SimpleMotion:
    """
    Simple motion controller for basic objects.

    Perfect for bullets, particles, collectibles, and projectiles.
    """

    def __init__(
        self,
        pos: VectorLike = (0, 0),
        speed: float = 150,
        *,
        max_speed: Optional[float] = None,
        drag: float = 0.0,
        sleep_threshold: float = 0.1
    ):
        self.body = KinematicBody(
            pos=pos,
            max_speed=max_speed,
            drag=drag,
            sleep_threshold=sleep_threshold
        )
        if speed < 0:
            raise ValueError("speed must be non-negative")
        self.speed = float(speed)

    @property
    def position(self) -> Vector2:
        return self.body.position

    @position.setter
    def position(self, value: VectorLike) -> None:
        self.body.position = value

    @property
    def velocity(self) -> Vector2:
        return self.body.velocity

    @velocity.setter
    def velocity(self, value: VectorLike) -> None:
        self.body.velocity = value

    @property
    def current_speed(self) -> float:
        """Matches BaseMotion API for checking actual physical speed."""
        return self.body.speed

    def go_right(self) -> None:
        self.body.velocity = Vector2(self.speed, 0)

    def go_left(self) -> None:
        self.body.velocity = Vector2(-self.speed, 0)

    def go_up(self) -> None:
        self.body.velocity = Vector2(0, -self.speed)

    def go_down(self) -> None:
        self.body.velocity = Vector2(0, self.speed)

    def go_angle(self, angle: float) -> None:
        rad = math.radians(angle)
        self.body.velocity = Vector2(math.cos(rad), math.sin(rad)) * self.speed

    def go_reverse(self, x: Optional[bool] = None, y: Optional[bool] = None) -> None:
        if x is None and y is None:
            x = True
            y = True
        if x:
            self.body.velocity.x *= -1
        if y:
            self.body.velocity.y *= -1

    def go(self, direction: VectorLike) -> None:
        vec = Vector2(direction)
        if vec.length_squared() > EPSILON:
            self.body.velocity = vec.normalize() * self.speed

    def set_velocity(self, x: Optional[float] = None, y: Optional[float] = None) -> None:
        self.body.set_velocity(x, y)

    def stop(self) -> None:
        self.body.stop()

    def apply_gravity(self, dt: float, force: float = 800.0, max_fall_speed: Optional[float] = None) -> None:
        """Apply downward gravity. Call before update()."""
        if dt <= 0:
            return

        self.body.velocity.y += force * dt

        if max_fall_speed is not None:
            self.body.velocity.y = min(self.body.velocity.y, float(max_fall_speed))

    def damp(self, x: float = 0.99, y: float = 0.99) -> None:
        """
        Apply dampening (air resistance) to velocity.

        This multiplies velocity by the given factors on each axis.
        Call this manually before update() for realistic deceleration.

        Args:
            x: Dampening factor for X axis (0.0 to 1.0)
            y: Dampening factor for Y axis (0.0 to 1.0)

        Example:
            # Fast horizontal decay, slow vertical decay
            motion.damp(x=0.95, y=0.99)
            motion.update(dt)

        Raises:
            ValueError: If factor is outside [0.0, 1.0]
        """
        if not (0.0 <= x <= 1.0):
            raise ValueError(f"x factor must be between 0.0 and 1.0, got {x}")
        if not (0.0 <= y <= 1.0):
            raise ValueError(f"y factor must be between 0.0 and 1.0, got {y}")

        self.body.velocity.x *= x
        self.body.velocity.y *= y

    def apply_impulse(self, impulse: VectorLike) -> None:
        self.body.apply_impulse(impulse)

    def apply_force(self, force: VectorLike, dt: float) -> None:
        self.body.apply_force(force, dt)

    def step_velocity(self, dt: float) -> Vector2:
        """
        Advance velocity only (drag, sleep, speed limits via body).
        Does NOT commit position. Returns proposed position delta.

        Call this OR update() — not both — per frame.
        """
        return self.body.step_velocity(dt)

    def update(self, dt: float) -> None:
        """Update position based on current velocity."""
        if dt <= 0:
            return
        self.body.update(dt)


class BaseMotion:
    """
    Base class for all intent-based motion controllers.

    Provides:
    - Intent system (move_left, move_right, etc.)
    - Heading helpers
    """

    def __init__(
        self,
        pos: VectorLike = (0, 0),
        body: Optional[KinematicBody] = None,
        heading: Optional[Heading] = None
    ):
        self.body = body if body is not None else KinematicBody(pos=pos)
        self.heading = heading if heading is not None else NoHeading()
        self._move_intent = Vector2(0, 0)

    @property
    def position(self) -> Vector2:
        return self.body.position

    @position.setter
    def position(self, value: VectorLike) -> None:
        self.body.position = value

    @property
    def velocity(self) -> Vector2:
        return self.body.velocity

    @velocity.setter
    def velocity(self, value: VectorLike) -> None:
        self.body.velocity = value

    @property
    def current_speed(self) -> float:
        return self.body.speed

    @property
    def current_heading(self) -> Vector2:
        return self.heading.vector

    # --- Intent Methods ---
    def move_left(self) -> None:
        self._move_intent.x -= 1.0

    def move_right(self) -> None:
        self._move_intent.x += 1.0

    def move_up(self) -> None:
        self._move_intent.y -= 1.0

    def move_down(self) -> None:
        self._move_intent.y += 1.0

    def move_forward(self) -> None:
        self._move_intent += self.heading.vector

    def move_backward(self) -> None:
        self._move_intent -= self.heading.vector

    def strafe_left(self) -> None:
        head = self.heading.vector
        self._move_intent += Vector2(head.y, -head.x)

    def strafe_right(self) -> None:
        head = self.heading.vector
        self._move_intent += Vector2(-head.y, head.x)

    def turn_left(self, dt: float) -> None:
        """Steer left. Pass your game's dt."""
        self.heading.turn_left(dt)

    def turn_right(self, dt: float) -> None:
        """Steer right. Pass your game's dt."""
        self.heading.turn_right(dt)

    def add_move(self, dx: float, dy: float) -> None:
        """Add to movement intent (accumulates)."""
        mag = math.hypot(dx, dy)
        if mag > EPSILON:
            if mag > 1.0:
                dx /= mag
                dy /= mag
            self._move_intent.x += dx
            self._move_intent.y += dy

    def set_intent(self, direction: VectorLike) -> None:
        """Set (replace!) 2D movement intent with proper normalization."""
        vec = Vector2(direction)
        length = vec.length()
        if length <= EPSILON:
            self._move_intent = Vector2(0, 0)
        elif length > 1.0:
            self._move_intent = vec / length
        else:
            self._move_intent = vec

    def clear_intent(self) -> None:
        self._move_intent = Vector2(0, 0)

    def dash(self, power: float = 800.0) -> None:
        """
        Apply a dash impulse in the current heading direction.

        Two speeds:
        - motion.speed — intent-driven acceleration target
        - body.max_x_speed / body.max_speed — hard velocity cap

        Intent-driven movement (holding a direction) never exceeds
        motion.speed, so raising body.max_x_speed allows impulses
        (like dashes) to exceed normal move speed without any
        effect on intent-driven movement.

        Typical usage for a "dash exceeds move speed" feel:

            # At setup:
            motion.body.max_x_speed = dash_speed  # e.g. 600

            # Every dash:
            motion.dash(power=dash_power)

        No restoration needed — intent-driven movement self-limits
        at motion.speed, so velocity naturally decays back down.
        """
        self.body.apply_impulse(self.heading.vector * power)

    @staticmethod
    def _approach(current: float, target: float, amount: float) -> float:
        """Approach target value by amount."""
        diff = target - current
        if abs(diff) <= amount:
            return target
        return current + math.copysign(amount, diff)

    def _normalize_intent(self) -> None:
        """Normalize intent vector if length > 1."""
        if self._move_intent.length_squared() > 1.0:
            self._move_intent.normalize_ip()

    def step_velocity(self, dt: float) -> Vector2:
        """
        Advance the motion's velocity state by one timestep.
        Does NOT commit position. Returns the proposed position delta.

        Subclasses implement this to include their own velocity logic
        (intent acceleration, gravity, auto-face, etc.) and then
        delegate to body.step_velocity(dt) for drag/limits/delta.

        Calling step_velocity OR update consumes the current intent —
        call one, not both, per frame.
        """
        raise NotImplementedError("Subclasses must implement step_velocity()")

    def authority(self, dt: float, velocity: Optional[VectorLike] = None) -> Vector2:
        """
        Alternate velocity pipeline. Skips ALL normal physics processing:
          - no intent acceleration
          - no gravity
          - no drag
          - no sleep threshold
          - no speed limits

        If velocity is provided, body.vel is set to it first.

        Returns the proposed position delta (velocity * dt, dt clamped to
        MAX_DT). If dt <= 0, returns Vector2(0, 0) without modifying velocity.

        Call this INSTEAD of step_velocity() on frames where the game has
        full velocity authority. Do not call both in the same frame.

        Collision is unaffected. Intent is unaffected (call clear_intent()
        yourself if you need to).
        """
        if dt <= 0:
            return Vector2(0, 0)
        if velocity is not None:
            self.body.vel = Vector2(velocity)
        dt = min(float(dt), MAX_DT)
        return self.body.vel * dt

    def update(self, dt: float) -> None:
        raise NotImplementedError("Subclasses must implement update()")


class PlatformerMotion(BaseMotion):
    """
    Platformer-specific motion controller.

    Default heading: Facing(directions=2, axis='horizontal') — the
    standard left/right facing used by most 2D platformers. Pass a
    custom heading to override.

    NOTE:
    - Use max_fall_speed instead of drag to limit falling speed.
    - Your game must handle collision and grounded state.
      This controller applies gravity and horizontal movement only.
    """

    def __init__(
        self,
        pos: VectorLike = (0, 0),
        *,
        body: Optional[KinematicBody] = None,
        heading: Optional[Heading] = None,
        speed: float = 350,
        acceleration: float = 3000,
        deceleration: float = 3500,
        gravity: float = 1200,
        jump_strength: float = 500,
        max_fall_speed: float = 900,
        auto_face: bool = True
    ):
        if speed <= 0 or acceleration <= 0:
            raise ValueError("speed and acceleration must be positive")
        if gravity < 0 or jump_strength < 0:
            raise ValueError("gravity_strength and jump_strength must be non-negative")
        if max_fall_speed is not None and max_fall_speed <= 0:
            raise ValueError("max_fall_speed must be positive or None")

        if body is None:
            body = KinematicBody(pos=pos, max_x_speed=speed)

        if heading is None:
            heading = Facing(directions=2, axis='horizontal')

        super().__init__(body=body, heading=heading)

        self.speed = speed
        self.acceleration = acceleration
        self.gravity = gravity
        self.jump_strength = jump_strength
        self.max_fall_speed = max_fall_speed
        self.auto_face = auto_face

        if deceleration is None:
            deceleration = acceleration
        elif deceleration <= 0:
            raise ValueError("deceleration must be positive")

        self.deceleration = float(deceleration)

    def jump(self, power: Optional[float] = None) -> None:
        """Apply jump velocity (does NOT check if grounded)."""
        p = abs(float(power if power is not None else self.jump_strength))
        if p > 0:
            self.body.set_velocity(y=-p)

    def step_velocity(self, dt: float) -> Vector2:
        """
        Advance platformer velocity state. Does NOT commit position.
        Returns proposed position delta for this frame.

        Handles: horizontal intent acceleration, gravity + max fall speed,
        auto-facing, then body drag/limits. Emits the delta computed
        by the body using the same effective dt.
        """
        if dt <= 0:
            self._move_intent = Vector2(0, 0)
            return Vector2(0, 0)

        dt = min(float(dt), MAX_DT)

        self._normalize_intent()

        # Mark horizontal axis as active if we're moving
        x = abs(self._move_intent.x) > EPSILON
        self.body.mark_active(x=x, y=False)  # Gravity always applies

        # Horizontal movement
        target_x = self._move_intent.x * self.speed
        rate = self.acceleration if x > EPSILON else self.deceleration
        self.body.vel.x = self._approach(self.body.vel.x, target_x, rate * dt)

        # Gravity
        self.body.vel.y += self.gravity * dt
        if self.max_fall_speed is not None and self.body.vel.y > self.max_fall_speed:
            self.body.vel.y = self.max_fall_speed

        # Auto-face movement direction
        if self.auto_face and self._move_intent.length_squared() > EPSILON:
            # Platformers typically only face left/right, but we preserve Y for slopes
            self.heading.aim((self._move_intent.x, 0), dt, snap=True)

        # Clear intent for next frame
        self._move_intent = Vector2(0, 0)

        # Delegate velocity finalization (drag, limits) to body and
        # get back the proposed position delta for this frame.
        return self.body.step_velocity(dt)

    def update(self, dt: float) -> None:
        """Update platformer motion (velocity + position)."""
        delta = self.step_velocity(dt)
        self.body.pos += delta


class TopDownMotion(BaseMotion):
    """
    Top-down motion controller.
    Optional auto-aim and grip (will absorb sideways energy, no speed preservation)
    """

    def __init__(
        self,
        pos: VectorLike = (0, 0),
        *,
        body: Optional[KinematicBody] = None,
        heading: Optional[Heading] = None,
        speed: float = 400,
        acceleration: float = 2500,
        deceleration: float = 3000,
        max_speed: Optional[float] = None,
        auto_aim: bool = True,
        heading_snap: bool = False,
        grip: float = 0.0,
    ):
        if speed <= 0 or acceleration <= 0:
            raise ValueError("speed and acceleration must be positive")

        if max_speed is None:
            max_speed = speed

        if body is None:
            body = KinematicBody(pos=pos, max_speed=max_speed)

        if heading is None:
            heading = NoHeading()

        if grip < 0:
            raise ValueError("grip must be non-negative")

        super().__init__(body=body, heading=heading)

        self.speed = speed
        self.acceleration = acceleration
        self.heading_snap = heading_snap
        self.auto_aim = auto_aim
        self.grip = float(grip)

        if deceleration is None:
            deceleration = acceleration
        elif deceleration <= 0:
            raise ValueError("deceleration must be positive")

        self.deceleration = float(deceleration)

    def _apply_grip(self, dt: float) -> None:
        """
        Apply lateral damping: kill sideways velocity relative to heading,
        preserve forward velocity.

        This is the physics of a tire: forward motion is preserved,
        sideways motion is resisted. Total speed may drop during hard
        turns (sideways energy is absorbed), but velocity never flips
        direction.

        Only has effect when heading is manually controlled
        (auto_aim=False) and grip > 0.
        """
        if self.grip <= 0:
            return

        heading_vec = self.heading.vector
        if heading_vec.length_squared() <= EPSILON:
            return

        vel = self.body.vel
        if vel.length_squared() <= EPSILON:
            return

        heading_dir = heading_vec.normalize()

        # Split velocity into forward (along heading) and lateral (perpendicular)
        forward_speed = vel.dot(heading_dir)
        forward = heading_dir * forward_speed
        lateral = vel - forward

        # Damp the lateral component (frame-rate independent exponential decay)
        lateral *= math.exp(-self.grip * dt)

        # Recombine — forward is preserved, lateral is damped
        self.body.vel = forward + lateral

    def step_velocity(self, dt: float) -> Vector2:
        """
        Advance top-down velocity state. Does NOT commit position.
        Returns proposed position delta for this frame.

        Handles: intent acceleration toward speed, grip lateral damping,
        auto-aim, then body drag/limits.
        """
        if dt <= 0:
            self._move_intent = Vector2(0, 0)
            return Vector2(0, 0)

        dt = min(float(dt), MAX_DT)

        # Normalize intent
        self._normalize_intent()

        # Mark active axes
        self.body.mark_active(
            x=abs(self._move_intent.x) > EPSILON,
            y=abs(self._move_intent.y) > EPSILON
        )

        target = self._move_intent * self.speed
        rate = self.acceleration if self._move_intent.length_squared() > EPSILON else self.deceleration
        amount = rate * dt

        diff = target - self.body.vel
        dist = diff.length()

        if dist <= amount:
            self.body.vel = target
        else:
            self.body.vel += diff.normalize() * amount

        self._apply_grip(dt)

        # Auto-aim
        if self.auto_aim and self._move_intent.length_squared() > EPSILON:
            self.heading.aim(self._move_intent, dt, snap=self.heading_snap)

        # Clear intent for next frame
        self._move_intent = Vector2(0, 0)

        # Delegate velocity finalization to body, get back proposed delta
        return self.body.step_velocity(dt)

    def update(self, dt: float) -> None:
        """Update top-down motion (velocity + position)."""
        delta = self.step_velocity(dt)
        self.body.pos += delta


class Motion2D:
    """
    Factory for creating motion controllers.

    This is the main entry point for creating motion controllers.
    """

    @staticmethod
    def simple(
        pos: VectorLike = (0, 0),
        *,
        speed: float = 150,
        max_speed: Optional[float] = None,
        drag: float = 0.0,
        sleep_threshold: float = 0.1
    ) -> SimpleMotion:
        """Create a simple motion controller for bullets, particles, etc."""
        return SimpleMotion(
            pos=pos,
            speed=speed,
            max_speed=max_speed,
            drag=drag,
            sleep_threshold=sleep_threshold
        )

    @staticmethod
    def platformer(
        pos: VectorLike = (0, 0),
        *,
        speed: float = 350,
        acceleration: float = 3000,
        deceleration: float = 3500,
        gravity: float = 1200,
        jump_strength: float = 500,
        max_fall_speed: float = 900,
        heading: Optional[Heading] = None,
        auto_face: bool = True,
    ) -> PlatformerMotion:
        """Create a platformer motion controller."""
        return PlatformerMotion(
            pos=pos,
            heading=heading,
            speed=speed,
            acceleration=acceleration,
            deceleration=deceleration,
            gravity=gravity,
            jump_strength=jump_strength,
            max_fall_speed=max_fall_speed,
            auto_face=auto_face,
        )

    @staticmethod
    def top_down(
        pos: VectorLike = (0, 0),
        *,
        speed: float = 400,
        acceleration: float = 2500,
        deceleration: float = 3000,
        max_speed: Optional[float] = None,
        heading: Optional[Heading] = None,
        auto_aim: bool = True,
        heading_snap: bool = False,
        grip: float = 0.0,
    ) -> TopDownMotion:
        """Create a top-down motion controller."""
        return TopDownMotion(
            pos=pos,
            heading=heading,
            speed=speed,
            max_speed = max_speed,
            acceleration=acceleration,
            deceleration=deceleration,
            auto_aim=auto_aim,
            heading_snap=heading_snap,
            grip=grip,
        )


__all__ = [
    'KinematicBody',
    'Heading',
    'Rotator',
    'Facing',
    'NoHeading',
    'BaseMotion',
    'PlatformerMotion',
    'TopDownMotion',
    'SimpleMotion',
    'Motion2D',
    'Vector2',
]

__version__ = "1.1.0"
__author__ = "Motion2D Contributors"


# HISTORY
# v1.1.0:
# - Remove pygame.Vector2 depedency

# v1.0.0:
# - Fixes dt <=0 in authority()
# - Fixes rotator aim() with supplied direction
# - Fixes turn_toward return False instead of None
# - Conclude the demos, upgrade into v1.0

# v0.9.2:
# - Added authority() in basemotion, for override beside velocity calculation

# v0.9.1:
# - PlatformerMotion default heading is now Facing(2, horizontal)
#   instead of Facing(0). This matches the platformer convention
#   (left/right facing) and enforces the constraint that a platformer
#   character should not face diagonally. Users who need different
#   facing behavior should pass a heading explicitly.
