# Motion2D API Reference

Complete reference for Motion2D's public classes and methods.

For how to use these together, see [workflow.md](workflow.md).
For runnable examples, see [../demos/](../demos/).

**Convention**: All positions are the **center** of the object. All
angles are in **degrees**, measured clockwise from `+X` (matching
Pygame's screen coordinates).

---

## Contents

- [`Motion2D`](#motion2d) — factory
- [`SimpleMotion`](#simplemotion) — constant-speed motion
- [`PlatformerMotion`](#platformermotion) — gravity + horizontal intent
- [`TopDownMotion`](#topdownmotion) — full 2D movement
- [`BaseMotion`](#basemotion) — shared interface
- [`KinematicBody`](#kinematicbody) — the foundation
- [Headings](#headings) — `Rotator`, `Facing`, `NoHeading`

---

## `Motion2D`

Factory for creating motion controllers. This is the recommended
entry point.

### `Motion2D.simple(...) -> SimpleMotion`

```python
Motion2D.simple(
    pos=(0, 0),
    *,
    speed=150,
    max_speed=None,
    drag=0.0,
    sleep_threshold=0.1,
)
```

Creates a `SimpleMotion`. Use for bullets, particles, and any object
that moves at a constant speed without steering.

- `pos` — initial position (center)
- `speed` — movement speed for `go_*` methods
- `max_speed` — hard velocity cap (`None` = no cap)
- `drag` — exponential drag coefficient (0 = no drag)
- `sleep_threshold` — velocity below this snaps to zero

### `Motion2D.platformer(...) -> PlatformerMotion`

```python
Motion2D.platformer(
    pos=(0, 0),
    *,
    speed=350,
    acceleration=3000,
    deceleration=3500,
    gravity=1200,
    jump_strength=500,
    max_fall_speed=900,
    heading=None,
    auto_face=True,
)
```

Creates a `PlatformerMotion`. Use for side-view platformers.

- `speed` — maximum horizontal speed
- `acceleration` / `deceleration` — how fast to reach / leave target speed
- `gravity` — downward acceleration (px/s²)
- `jump_strength` — initial upward velocity on jump
- `max_fall_speed` — terminal velocity
- `heading` — a `Heading` instance; if `None`, a default `Facing` is used
- `auto_face` — if `True`, the heading follows horizontal movement

### `Motion2D.top_down(...) -> TopDownMotion`

```python
Motion2D.top_down(
    pos=(0, 0),
    *,
    speed=400,
    acceleration=2500,
    deceleration=3000,
    max_speed=None,
    heading=None,
    auto_aim=True,
    heading_snap=False,
    grip=0.0,
)
```

Creates a `TopDownMotion`. Use for top-down, twin-stick, and any
game with full 2D movement.

- `speed` — maximum speed in any direction
- `max_speed` — hard velocity cap; if `None`, defaults to `speed`
- `heading` — a `Heading` instance; if `None`, `NoHeading` is used
- `auto_aim` — if `True`, heading follows movement intent
- `heading_snap` — if `True`, `aim` uses snap mode (instant rotation)
- `grip` — lateral damping factor (0 = no grip, higher = vehicle-like)

---

## `SimpleMotion`

Constant-speed motion. No steering, no acceleration curves.

### Constructor

```python
SimpleMotion(
    pos=(0, 0),
    speed=150,
    *,
    max_speed=None,
    drag=0.0,
    sleep_threshold=0.1,
)
```

### Properties

- `position: Vector2` — read/write current position
- `velocity: Vector2` — read/write current velocity
- `current_speed: float` — read-only, `velocity.length()`

### Directional movement

- `go_right()` / `go_left()` / `go_up()` / `go_down()` — set velocity
  along an axis at `speed`.
- `go_angle(angle: float)` — set velocity along `angle` (degrees).
- `go(direction: Vector2)` — set velocity in the direction of `direction`
  (normalized), at `speed`.
- `go_reverse(x=None, y=None)` — flip velocity on the given axes.
  No arguments = flip both.

### Direct control

- `set_velocity(x=None, y=None)` — override velocity components.
- `stop()` — zero velocity.
- `apply_gravity(dt, force=800.0, max_fall_speed=None)` — add downward
  velocity (call before `update`).
- `damp(x=0.99, y=0.99)` — multiply velocity by factors (air resistance).
- `apply_impulse(impulse)` — add to velocity instantly.
- `apply_force(force, dt)` — add to velocity over time.

### Update

- `update(dt)` — advance velocity and position.
- `step_velocity(dt) -> Vector2` — advance velocity only; return the
  proposed position delta without committing. Use with external collision.

---

## `PlatformerMotion`

Gravity-based side-view motion. Horizontal intent, vertical gravity.

### Constructor

See [`Motion2D.platformer`](#motion2dplatformer---platformermotion).

### Methods

- `jump(power=None)` — apply jump velocity. Does **not** check grounded
  state; the game is responsible for that check.
- `update(dt)` — advance velocity and position.
- `step_velocity(dt) -> Vector2` — advance velocity only; return delta.
- `authority(dt, velocity=None) -> Vector2` — advance velocity using
  game-controlled rules (see [BaseMotion](#basemotion)).

---

## `TopDownMotion`

Full 2D movement. Optional auto-aim and lateral grip.

### Constructor

See [`Motion2D.top_down`](#motion2dtop_down---topdownmotion).

### Methods

- `update(dt)` — advance velocity and position.
- `step_velocity(dt) -> Vector2` — advance velocity only; return delta.
- `authority(dt, velocity=None) -> Vector2` — advance velocity using
  game-controlled rules (see [BaseMotion](#basemotion)).

---

## `BaseMotion`

`BaseMotion` is a base class for all intent-based motion controllers

### Properties

- `position: Vector2` — read/write current position (delegates to body)
- `velocity: Vector2` — read/write current velocity
- `current_speed: float` — read-only speed
- `current_heading: Vector2` — read-only unit vector from `heading`

### Intent methods

Call these to accumulate movement intent for the current frame.
Intent is cleared automatically after `step_velocity` or `update`.

- `move_left()` / `move_right()` / `move_up()` / `move_down()` —
  add ±1 on the relevant axis.
- `move_forward()` / `move_backward()` — add heading vector (±).
- `strafe_left()` / `strafe_right()` — add heading-perpendicular vector.
- `add_move(dx, dy)` — add raw direction (normalized if `mag > 1.0`).
- `set_intent(direction)` — replace accumulated intent with `direction`
  (normalized if `length > 1.0`).
- `clear_intent()` — reset intent to zero.

### Steering helpers

- `turn_left(dt)` / `turn_right(dt)` — delegate to `heading.turn_*`.
  Only meaningful for `Rotator` or `Facing`.

### Dash

- `dash(power=800.0)` — apply an impulse in the direction of
  `heading.vector`. Adds to velocity; does not replace it.

### Update

- `update(dt)` — **abstract.** Subclasses implement this; it typically
  advances velocity and position together. Do not rely on it on
  `BaseMotion` directly.
- `step_velocity(dt) -> Vector2` — advance velocity only; return delta.
  Skips position integration and returns the movement that *would* be
  made. Use this when the game owns collision resolution.
- `authority(dt, velocity=None) -> Vector2` — advance velocity using
  game-controlled rules. Skips intent, gravity, drag, sleep threshold,
  and speed limits. If `velocity` is provided, sets the body's velocity
  to it first. Returns the proposed position delta.

**`step_velocity` vs `authority`**:

| | `step_velocity` | `authority` |
|---|---|---|
| Intent | Applied | Ignored |
| Gravity | Applied | Ignored |
| Drag / limits | Applied | Ignored |
| Forced velocity | No | Optional |
| Position commit | No | No |

Call **one or the other** per frame, not both. `authority` is for
phases where the game has full control of velocity (dashes, wind-ups,
freezes, scripted movement). `step_velocity` is for every other frame.

`authority()` is provided by `BaseMotion` and its intent-based subclasses.

`authority` is stateless: there is no flag to set, no `release` to
call, and no reset behavior to remember. The game simply chooses
which method to invoke each frame.

---

## `KinematicBody`

The foundation. Handles position, velocity, drag, speed limits, and
integration. All motion classes compose one of these.

### Constructor

```python
KinematicBody(
    pos=(0, 0),
    *,
    max_speed=None,
    max_x_speed=None,
    max_y_speed=None,
    drag=0.0,
    sleep_threshold=0.1,
)
```

- `max_speed` — total magnitude cap (any axis)
- `max_x_speed` / `max_y_speed` — per-axis caps (independent of `max_speed`)

### Properties

- `position: Vector2` — read/write position
- `velocity: Vector2` — read/write velocity
- `speed: float` — read-only `velocity.length()`

### Velocity control

- `set_velocity(x=None, y=None)` — directly override components.
- `stop(x=True, y=True)` — zero the given axes.
- `apply_impulse(impulse)` — instantaneous velocity change.
- `apply_force(force, dt)` — continuous velocity change.
- `mark_active(x=False, y=False)` — mark axes as "actively controlled"
  so drag and sleep threshold are skipped on those axes this frame.
- `reset(pos=None, vel=None)` — reset position and/or velocity.

### Update

- `update(dt)` — apply drag, limits, and integrate position.
- `step_velocity(dt) -> Vector2` — apply drag and limits, but return
  the proposed delta without moving position. Use with external collision.

---

## Headings

A `Heading` answers "which way is this object facing?" Different
headings give different behaviors.

### `Rotator`

Continuous angular control. Smooth rotation toward a target angle.

```python
Rotator(angle=0.0, rotate_speed=180.0)
```

- `rotate_speed` — degrees per second (positive)
- `.angle: float` — current angle (read/write, wraps at 360)
- `.vector: Vector2` — unit vector in the current direction
- `.rotate(direction, dt)` — rotate at fixed speed (`-1` to `1`)
- `.turn_toward(target_angle, dt) -> bool` — rotate toward `target_angle`.
  Returns `True` if aligned.
- `.aim(direction, dt=1/60, snap=False) -> bool` — aim at a vector.
  `snap=True` jumps instantly; `snap=False` rotates smoothly.
- `.left()` / `.right()` / `.up()` / `.down()` / `.flip()` — set the
  angle to a fixed direction.
- `.turn_left(dt)` / `.turn_right(dt)` — continuous rotation helpers.

### `Facing`

Discrete facing. Snaps to a set of allowed directions.

```python
Facing(initial_vector=(1, 0), directions=0, axis='horizontal')
```

- `directions` — `0` (free), `2`, `4`, or `8`
- `axis` — only used when `directions=2`: `'horizontal'` or `'vertical'`
- `.vector: Vector2` — current unit vector (snapped if directions > 0)
- `.aim(direction, dt=1/60, snap=False) -> bool` — set direction (snapped)
- Direction helpers: `.left()`, `.right()`, `.up()`, `.down()`,
  `.up_left()`, `.up_right()`, `.down_left()`, `.down_right()`,
  `.flip()`, `.set_direction(v)`
- Snapped checks: `.is_left(exact=False)`, `.is_right(...)`,
  `.is_up(...)`, `.is_down(...)`, and diagonal variants.

### `NoHeading`

Null heading. All methods are no-ops or return a default vector.

```python
NoHeading(default_direction=(0, 0))
```

- `.vector: Vector2` — returns `default_direction` (normalized)
- `.aim(...)` — does nothing

Use `NoHeading` when a motion class doesn't need facing.

---

## Internal behavior (worth knowing)

### `dt` clamping

All motion classes clamp `dt` to a maximum of `0.1` seconds per step.
This prevents a single long frame from tunneling an object through a
wall or exploding a phase sequence.

If your game loop has legitimate reasons to use larger `dt`, sub-step
the call:

```python
for _ in range(n_substeps):
    motion.update(dt / n_substeps)
```

### Intent lifecycle

Intent accumulates during the frame, is consumed by `step_velocity` /
`update` / `authority`, and is cleared at the end of that call.

You do not need to call `clear_intent()` manually unless you want to
discard pending intent mid-frame.

### Heading and motion

Headings are independent of motion. A `PlatformerMotion` uses its
heading only to determine facing; movement direction is derived from
intent or the game's explicit velocity setting.

---

## See also

- [`workflow.md`](workflow.md) — how to structure a game around these
  primitives
- [`../demos/`](../demos/) — 10 demos that build up from basics to
  custom motion
