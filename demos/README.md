# Motion2D Demos

Ten demos, each demonstrating one facet of Motion2D.

**Start with Demo 1 and read forward.** The demos generally build in
complexity. Start with Demo 1 and read forward, or jump directly to
a demo that matches what you're looking for.

---

## The demos

| # | Name | Motion class | What it teaches |
|---|------|--------------|-----------------|
| 01 | Simple vs Intent | `SimpleMotion`, `TopDownMotion` | Direct velocity vs intent-driven movement |
| 02 | Bullet Hell | `SimpleMotion` | `go_angle()` for directional movement |
| 03 | Fireworks | `SimpleMotion` | Gravity and `damp()` for external effects |
| 04 | Catapult | `SimpleMotion` | Projectile motion, gravity, damp |
| 05a | Missile Command | `Rotator` | Heading without any motion |
| 05b | Timberman | `Facing` | Discrete facing as game state |
| 06 | Zen Driller | `TopDownMotion` | Vehicle-style grip and drift |
| 07 | Inertia Dodger | `TopDownMotion` | `step_velocity` + twin-stick + timers |
| 08 | First Platformer | `PlatformerMotion` | The collision workflow, end-to-end |
| 09 | Platformer Playground | `PlatformerMotion`, `authority()` | Phases, state machines, action weight |
| 10 | Custom Motion | `KinematicBody` | Building your own motion class |

---

## How to read them

**Demos 1–5**: single-concept demos. Each shows one motion class
or one feature in isolation. Read the header docstring, run the
demo, adjust parameters in the source.

**Demo 6–7**: complete micro-games. Demonstrate how motion
primitives compose with a game loop, timers, and player input.

**Demo 8**: the main example of the collision workflow —
`step_velocity` → resolve → commit. If you only read one demo,
read this one.

**Demo 9**: the state-machine + authority pattern. Demonstrates
how to structure phased actions (dash, wall jump, jump wind-up)
with a clean state machine and `authority()` for velocity override.

**Demo 10**: building a custom motion class on `KinematicBody`.
Read this when you need motion that Motion2D doesn't provide.

---

## External helpers

Demos 8–10 use small helper modules that are **not part of
Motion2D**:

- a collision library (for `resolve_swept` and queries)
- a time/timer library (for `Timer`, `TimerSequence`)
- a coordinate-convention util (for center ↔ top-left conversion)

They're included in this folder as examples of how Motion2D
composes with the rest of a game. **They are not required to use
Motion2D** — Path 1 in [`docs/workflow.md`](../docs/workflow.md)
needs none of them.

---

## Notes

- Every demo is single-file. Copy the one you want, adjust the
  constants at the top, and experiment.
- Demos assume Python 3.8+ and Pygame. See the [main README](../README.md)
  for setup.
- Header docstrings are the primary documentation. Read them in a
  text editor; they explain the *why*, not just the *what*.
