# Motion2D Workflow

How to structure a game around Motion2D's primitives.

For the API surface itself, see [api.md](api.md).

This guide answers *when* and *why* to use each part of the
library — not *what* each method does.

---

## Contents

1. [Choosing your motion class](#1-choosing-your-motion-class)
2. [Choosing your path](#2-choosing-your-path)
3. [Path 1 — Self-contained motion](#3-path-1--self-contained-motion)
4. [Path 2 — Motion + external collision](#4-path-2--motion--external-collision)
5. [Game-controlled velocity](#5-game-controlled-velocity)
6. [Structuring action phases](#6-structuring-action-phases)
7. [Common pitfalls](#7-common-pitfalls)

---
## 1. Choosing your motion class

Motion2D ships three motion classes. Each answers a different
question about how an object moves.

### `SimpleMotion` — "moves at constant speed"

No acceleration. No intent. No steering. Velocity changes only when
you change it.

```python
bullet = Motion2D.simple(pos=(100, 100), speed=400)
bullet.go_angle(45)   # now moving at 400 px/s at 45°
bullet.update(dt)     # every frame — position advances
```

**Use when:** the object doesn't decide where to go. It just goes.

**Examples:** bullets, particles, moving platforms, collectibles,
any scripted projectile.

**Don't use when:** the object steers, accelerates, or responds to
input.

### `PlatformerMotion` — "side-view character with gravity"

Horizontal movement is intent-driven. Vertical is gravity-driven.
No diagonal control, no free 2D steering.

```python
player = Motion2D.platformer(pos=(100, 100), speed=300, jump_strength=550)

if keys[K_LEFT]:  player.move_left()
if keys[K_RIGHT]: player.move_right()
if keys[K_SPACE] and grounded: player.jump()

player.update(dt)
```

**Use when:** the game has a floor, gravity pulls things down, and
the character moves left or right.

**Examples:** side-scrolling platformers, Metroidvania, runners.

**Don't use when:** the object moves freely in 2D (top-down), or
doesn't fall.

### `TopDownMotion` — "full 2D movement, no gravity"

Movement is intent-driven in any direction. No gravity. Optional
auto-aim and lateral grip.

```python
player = Motion2D.top_down(pos=(100, 100), speed=300)

if keys[K_w]: player.move_up()
if keys[K_s]: player.move_down()
if keys[K_a]: player.move_left()
if keys[K_d]: player.move_right()

player.update(dt)
```

**Use when:** the object moves in all directions with no gravity.
The camera angle doesn't matter — "top-down" describes *the
motion model*, not the view.

**Examples:** twin-stick shooters, top-down RPGs, bullet-hell
dodgers, side-view games without gravity (spaceship, driller,
asteroid).

**Don't use when:** the object falls (use `PlatformerMotion`), or
the object just moves in a straight line (use `SimpleMotion`).

### Side-by-side

| | `SimpleMotion` | `PlatformerMotion` | `TopDownMotion` |
|---|---|---|---|
| Steering | none | horizontal | full 2D |
| Gravity | none | yes | none |
| Acceleration | none | yes | yes |
| Intent system | no | yes | yes |
| Typical use | bullets, particles | platformers | twin-stick, top-down |
| "Decides where to go?" | no | yes | yes |
| "Falls?" | no | yes | no |

### The bigger point

**The classes are about motion models, not about camera angles or
game genres.**

A side-view game where the player drills through terrain without
gravity uses `TopDownMotion`. A top-down game with a jump button
uses `PlatformerMotion` (with a top-down camera). **The class
matches the physics, not the view.**

If none of the three fits, build your own on `KinematicBody`. See
the "Custom motion" section in the README.

---

## 2. Choosing your path

Motion2D can be used two ways. Pick the one that matches your
game's collision model.

**Path 1** — the motion object owns position. Use when your game
has no external collision system, or collision is trivial.

```python
motion.update(dt)
```

**Path 2** — the motion object proposes movement, your game commits
position. Use when you have (or plan to have) your own collision
resolution.

```python
delta = motion.step_velocity(dt)
# ... resolve collision with `delta` ...
motion.position = result
```

**Pick one and stay on it for the whole object.** Mixing the two
paths per frame will produce inconsistent results.

---

## 3. Path 1 — Self-contained motion

Simplest setup. The motion object advances its own velocity and
position, in one call.

```python
player = Motion2D.top_down(pos=(100, 100), speed=300)

# In your game loop:
player.move_right()
player.update(dt)
```

**What happens inside `update(dt)`:**

1. Intent is applied to velocity.
2. Gravity, drag, and speed limits are applied (class-dependent).
3. Velocity is integrated into position.
4. Intent is cleared.

**Use Path 1 when:**

- Your game has no obstacles, or
- You resolve collisions by teleporting the object back afterward, or
- You're prototyping and want to move forward quickly.

**Don't use Path 1 when:**

- You need to stop the object *before* it penetrates a wall.
- Collision between moving objects needs to be considered.

Move to Path 2 for those.

---

## 4. Path 2 — Motion + external collision

The motion object still owns velocity, but the game owns position.
Every frame, you ask the motion for the movement it *wants* to make,
resolve that movement against the world, and commit the result.

```python
# In your game loop:
delta = player.step_velocity(dt)

result = my_collision_resolver(
    player.position, delta, world
)

player.position = result.position
```

**The flow is:**

```
motion
  │
  │ proposed delta (Vector2)
  ▼
collision resolver (your code)
  │
  │ resolved position (Vector2)
  ▼
motion.position = resolved
```

**What stays the same as Path 1:**

- Intent is still applied to velocity.
- Gravity, drag, and speed limits are still applied.
- Intent is still cleared after the call.

**What's different:**

- `step_velocity` returns the proposed movement but doesn't move
  the object.
- The game decides where the object actually goes.

**Use Path 2 when:**

- The object must stop at walls without penetrating.
- Multiple objects can collide with each other.
- Collision response is game-specific (slide, bounce, trigger an
  event, change state).

**Motion2D does not need to know how your collision works.** Any
resolver that takes a position and a proposed delta, and returns a
resolved position, will work.

---


## 5. Game-controlled velocity

Sometimes normal physics shouldn't be in charge.

A dash may want to override velocity directly. A wind-up may want
to freeze the player. A scripted launch may want to bypass gravity
and drag entirely.

For those frames, Motion2D provides a second pipeline:

```python
delta = motion.authority(dt, velocity=(300, 0))
```

**What `authority` does:**

- Skips intent, gravity, drag, sleep threshold, and speed limits.
- If `velocity` is provided, sets the body's velocity to it.
- Returns the proposed delta.

**What `authority` does not do:**

- It doesn't clear intent.
- It doesn't run collision.
- It doesn't move the object.
- It doesn't persist across frames.

**`authority` is stateless.** There is no flag to set, no
`release()` to call, and no reset behavior to remember. The game
simply chooses which pipeline to run each frame:

```python
if in_special_state:
    delta = motion.authority(dt, velocity=(300, 0))
else:
    delta = motion.step_velocity(dt)

# Then, in both cases:
result = my_collision_resolver(motion.position, delta, world)
motion.position = result.position
```

**Use `authority` when:**

- You want velocity to be *exactly* what you set, with no
  additional physics applied.
- Normal input intent should be ignored for this frame.
- Gravity and drag should not interfere.

**Don't use `authority` when:**

- You only want to *modify* velocity (e.g., wall slide — gravity
  still applies, then you clamp). Use `step_velocity` and adjust
  velocity afterward instead.

**Rule of thumb:** `authority` means "the game owns velocity this
frame." Anything less than that is `step_velocity` plus a
modification.

---

## 6. Structuring action phases

Actions like dash, wall jump, or jump wind-up have *phases*.
A dash might have `charge → active → recovery`. A jump might have
`crouch → launch`.

Motion2D doesn't know about phases. The game owns that structure.
But Motion2D's `authority` fits naturally into a phase-based system.

**A common pattern: a state machine where each state uses the
right pipeline.**

```python
def update(self, dt, world):
    # Get world conditions (grounded, walls, etc.)
    c = self.sense_world(world)

    # Update state machine (transitions + per-frame rules)
    self._update_state(dt, c)

    # Choose the pipeline based on current state
    if self.state in AUTHORITY_STATES:
        delta = self.motion.authority(dt)
    else:
        delta = self.motion.step_velocity(dt)

    # Resolve and commit
    result = resolve_swept(
        self.motion.position, delta, world
    )
    self.motion.position = result.position
```

**`AUTHORITY_STATES` is a set of states where the game fully
controls velocity** — typically dash, wind-up, and freeze states.

**States that only *modify* velocity (like wall slide) stay outside
the set and use `step_velocity`.**

**Why a set, not a flag:** the decision lives in the state machine's
definition, not in the motion object. No persistent state to manage.

**The state machine idiom:**

```python
if not self.started:
    # Entry logic (runs once per state entry)
    ...
    self.started = True

# Per-frame physics + transitions
...

if self.state != PREVIOUS_STATE:
    # Exit logic (runs once)
    self.started = False
```

The `started` flag is local to the state machine, not to Motion2D.
**Motion2D doesn't need to know you have a state machine.**

---

## 7. Common pitfalls

### Pitfall — calling both pipelines in one frame

```python
delta = motion.step_velocity(dt)
delta = motion.authority(dt)  # ← step_velocity's work is lost
```

**Call one or the other, once per frame, per object.**

### Pitfall — using `authority` when you meant to modify

```python
# Want: gravity still applies, but clamp fall speed
delta = motion.authority(dt)  # ← this skips gravity entirely
```

**Use `step_velocity` and modify velocity afterward:**

```python
delta = motion.step_velocity(dt)
if motion.velocity.y > max_fall:
    motion.velocity.y = max_fall
# (velocity change takes effect next frame; for same-frame
#  effect, modify before calling step_velocity)
```

### Pitfall — forgetting that `step_velocity` consumes intent

Both `step_velocity` and `update` clear the intent at the end of
the call. **Don't call `move_right()` after `step_velocity` in the
same frame and expect it to have effect.**

```python
delta = motion.step_velocity(dt)  # ← intent is cleared here
motion.move_right()               # ← too late
```

**Add intent before, not after.**

### Pitfall — mixing `update` and `step_velocity`

`update` internally calls `step_velocity` and then commits position.
If you call both, position will be committed twice.

```python
motion.update(dt)                # moves position
delta = motion.step_velocity(dt) # ALSO moves velocity; you'll
                                 # commit position again if you're
                                 # not careful
```

**Pick one path per object and stay on it.**

### Pitfall — expecting `dt` to be exactly what you passed

All methods clamp `dt` to `MAX_DT = 0.1`. If a single frame takes
longer than that, the object will move as if `dt = 0.1`, not
`dt = 0.2`. **Intentional** — prevents tunneling on long frames.
But if your game has legitimate reasons to step 0.2s at once,
sub-step the call:

```python
for _ in range(2):
    delta = motion.step_velocity(dt / 2)
    result = resolve(...)
    motion.position = result.position
```

### Pitfall — expecting `authority` to persist

```python
motion.authority(dt, velocity=(300, 0))  # frame N
# ... next frame, normal physics runs again ...
motion.step_velocity(dt)                  # frame N+1
```

**`authority` is per-call. It does not stay on.** If your dash
lasts 20 frames, call `authority` on all 20 frames. If you forget
one, that frame uses normal physics — self-correcting, not stuck.

### Pitfall — headings and intent

A heading's `aim` method updates the heading's *direction*, not
movement intent. **Setting `heading.aim((1, 0))` doesn't make the
object move right** — it makes it *face* right.

Movement comes from `move_*` methods or from setting velocity
directly.

---

## See also

- [api.md](api.md) — method reference
- [../demos/](../demos/) — ten demos that build up from basics to
  custom motion
