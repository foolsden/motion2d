# Motion2D

**A small, extensible 2D motion library for games.**

Movement looks simple.

Give an object a position. Add some velocity. Multiply by `dt`.

Then the game grows. Acceleration. Gravity. Friction. Jumping.
Collision. Dashes. A car that doesn't move anything like the player.

Suddenly "move the object" is its own system.

**Motion2D is an attempt to keep that system small, reusable, and
out of the way.**

---

## The idea

Motion2D provides motion primitives. Your game composes them into
behavior.

```text
Game behavior
     ↓
Motion  (Motion2D)
     ↓
Proposed movement (delta)
     ↓
Collision / game rules  (your code)
     ↓
Committed position
```

Motion2D handles the movement side. Your game decides what that
movement means.

The same primitives can drive a platformer, a top-down character,
a vehicle, or something that doesn't exist yet.

---

## Quick start

```python
from motion2d import Motion2D

player = Motion2D.top_down(pos=(100, 100), speed=300)

# In your game loop:
player.move_right()
player.update(dt)
```

That's it. The motion object owns its own position, velocity, and
integration.

---

## With your own collision

If you want to resolve movement against your own world, ask
Motion2D for the proposed delta instead of committing position:

```python
delta = player.step_velocity(dt)

# Your collision system decides where the object actually goes.
result = my_collision_system(player.position, delta)

player.position = result.position
```

Motion2D does not need to own your collision system.

---

## Game-controlled velocity

Sometimes normal physics shouldn't be in charge. A dash may want to
override velocity directly. A wind-up may want to freeze the player.

For those frames, Motion2D provides an alternative pipeline:

```python
delta = motion.authority(dt, velocity=(300, 0))
```

`authority()` returns the proposed delta for this frame, using
velocity you specify. It skips intent, gravity, drag, and speed
limits.

There is no persistent authority flag and no `release_authority()`.
The game simply chooses which method to call each frame:

```python
if special_state:
    delta = motion.authority(dt, velocity=(300, 0))
else:
    delta = motion.step_velocity(dt)
```

---

## Custom motion

When Motion2D doesn't have the motion class you need, build one on
top of `KinematicBody`.

A custom VehicleMotion class is included in the demos as an example
of building a motion system on top of KinematicBody.

Motion2D doesn't need to know how every object moves. It just
provides useful primitives for building those motion systems.

---

## What's included

- `Motion2D` — factory for creating motion controllers
- `KinematicBody` — core position / velocity / drag / integration
- `SimpleMotion`, `PlatformerMotion`, `TopDownMotion` — built-in
  motion classes
- `Rotator`, `Facing`, `NoHeading` — heading types

Motion2D is intentionally small. A few classes, a few methods, one
workflow. The demos explore what's possible with them.

> Some demos use small external helper modules. These are not part
> of Motion2D.

---

## Docs and demos

- [`docs/api.md`](docs/api.md) — reference for every public class
  and method
- [`docs/workflow.md`](docs/workflow.md) — how to structure a game
  around Motion2D
- [`demos/`](demos/) — ten demos that build up from primitives to
  custom motion. Start with Demo 1 and work forward.

---

## What Motion2D is not

Motion2D is not a physics engine, a collision framework, or a game
engine.

If your game needs something Motion2D doesn't provide, you can build
it yourself and reuse the pieces that are useful.

---

## Status

Motion2D is a small personal library and still evolving. The core is
stable. The demos are both examples and ongoing tests of the
library's design.

Some extensions — such as the `VehicleMotion` example in the demos —
are intentionally less finished. That's fine. The goal is a solid
foundation that grows when a real game gives it a reason to.
