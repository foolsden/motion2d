"""
Demo 9: Platformer Playground (State Machine Edition)
======================================================
A single-screen sandbox demonstrating how a real game composes
Motion2D primitives into mechanics with *phases* — actions that have
weight, commitment, and recovery, not just instantaneous effects.

THE CENTRAL IDEA:
    Actions aren't events. They're sequences:
        startup -> active -> recovery
    Each phase has its own rules about velocity, input, and physics.
    The weight of a jump, the commitment of a dash, the decision point
    of a wall cling — all emerge from how those phases are structured.

WHAT THIS DEMO TEACHES:
    - Composition: mechanics live OUTSIDE Motion2D, using its
      velocity and step_velocity/authority API.
    - Velocity authority: an alternative pipeline where the game,
      not the library, controls velocity for a phase.
    - State machines: a single enum as source of truth, with a
      `started` flag for one-shot entry logic.
    - Phase weight: startup, active, and recovery windows that make
      actions *feel* like actions.
    - Proximity queries: query_left/query_right for wall contact,
      is_grounded for floor contact.
    - Timer/one-shot flags: simple timers for phases, plain flags
      for instantaneous events (no race conditions).

WHY A STATE MACHINE (not parallel flags):
    Previous iterations used parallel state — separate booleans for
    dashing, clinging, jumping, plus a wall-state enum and three
    TimerSequences. That works, but:
        - "What am I doing?" has many answers.
        - Transition logic is scattered.
        - Entry/exit side effects are easy to forget.
    The state machine collapses all of that into ONE enum and ONE
    disciplined pattern (see STATE LOGIC below).

WHY authority() INSTEAD OF MUTATING gravity/deceleration:
    An earlier version suppressed physics by setting
    motion.gravity = 0, motion.deceleration = 0, then restoring
    hardcoded values afterward. That worked but:
        - The library's configuration was mutated at runtime.
        - Restore values were duplicated constants.
        - Any missed restore leaked state.
    authority(dt, velocity=None) is a per-call alternative pipeline.
    It skips intent, gravity, drag, sleep, and speed limits for one
    frame and returns a delta. No state to forget, no restore to miss.

WHY ONE-SHOT EVENTS USE FLAGS, NOT TIMERS:
    A brief window (e.g., a launch impulse) that fires "the moment a
    phase ends" is a race condition if modeled as a Timer stage —
    the timer may complete in the same update() that transitions into
    it. Instead, the state uses a local `_fired` flag, reset in the
    state's entry block. The impulse fires exactly once, on the first
    frame the phase's end condition is true. No race. No duration to
    tune for safety.

THE STATE MACHINE — HOW IT'S ORGANIZED:
    _update_state(dt, c) has one branch per PState.
    Every branch follows the same shape:

        if not self.started:        # ENTRY — runs exactly once
            ...set up timers, reset flags, capture direction...
            self.started = True

        ...per-frame physics + transition checks...

        if self.state != PState.CURRENT:   # LOCAL EXIT — runs exactly once
            self.started = False

    The `started` flag is the whole mechanism. If a branch transitions
    to another state, its own exit branch clears `started`; the next
    frame, the new state's `not self.started` fires its entry. There is
    no global "previous state" tracking and no chance of a stale flag.

    States that need velocity authority (dash, wall cling, jump crouch)
    are declared in AUTHORITY_STATES. In the update loop, that set
    decides whether to call authority() or step_velocity().

CONTROLS:
    Left / Right or A/D  : Move
    Space / Up / W       : Jump
      - on ground        : crouch -> launch (running jumps are snappier)
      - in air           : double jump (preserves horizontal momentum)
      - on a wall        : freeze -> launch away from the wall
    Shift / X            : Air Dash (Charge -> Dash -> Recovery)
      - dashing into wall: freeze -> bounce -> fall
    Hold into wall       : cling briefly, then slide down
    R                    : Reset
    ESC                  : Quit

WHAT TO WATCH FOR WHILE PLAYING:
    - Press jump while running: the crouch is almost instant; while
      standing, it's noticeable. Both feel committed.
    - Dash into a wall: the dash cancels, the car freezes for a beat,
      then bounces off. The bounce isn't instant.
    - Hold into a wall while falling: freeze, then slide. Release the
      direction and you fall. Hold again and the cling restarts.
    - Jump during cling or slide: freeze briefly, then launch.
      The freeze is the commitment.
"""

import pygame
from enum import Enum, auto
from dataclasses import dataclass
from pygame.math import Vector2

from motion2d import Motion2D
from time_util import Timer
from anchor_util import center_to_topleft, topleft_to_center
from collide2d import (
    resolve_swept,
    is_grounded,
    query_left,
    query_right,
    find_down,
)
from text_manager import TextManager


# ============================================================================
# Constants
# ============================================================================

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

PLAYER_SIZE = 30

COYOTE_TIME = 0.10
JUMP_BUFFER = 0.10
JUMP_CUT_MULT = 0.5
MAX_STEP = 0.5

DASH_SPEED = 800
WALL_SLIDE_SPEED = 150
WALL_JUMP_X = 400
WALL_JUMP_Y = 500
UPDRAFT_FORCE = -2500

JUMP_CROUCH_STANDING  = 0.10
JUMP_CROUCH_RUNNING   = 0.02
JUMP_CROUCH_AIR       = 0.06
JUMP_RUNNING_POWER    = 0.92

DASH_CHARGE_DUR       = 0.22
DASH_ACTIVE_DUR       = 0.32
DASH_RECOVERY_DUR     = 0.20

WALL_CLING_DUR        = 0.30
WALL_JUMP_WINDUP_DUR  = 0.06

DASH_WALL_FREEZE      = 0.06
DASH_WALL_BOUNCE      = 0.05
DASH_WALL_BOUNCE_MULT = 0.2

PLAYER_GRAVITY       = 1200
PLAYER_DECELERATION  = 2500
PLAYER_SPEED         = 300
PLAYER_ACCELERATION  = 2000
PLAYER_JUMP_STRENGTH = 550
PLAYER_MAX_FALL      = 900

COLOR_SKY = (30, 30, 45)
COLOR_GRID = (22, 22, 36)
COLOR_PLATFORM = (100, 100, 110)
COLOR_PLATFORM_EDGE = (140, 140, 150)
COLOR_MOVING = (255, 150, 50)
COLOR_MOVING_EDGE = (255, 200, 100)
COLOR_GOAL = (50, 255, 50)
COLOR_GOAL_EDGE = (200, 255, 200)

COLOR_PLAYER            = (100, 180, 255)
COLOR_PLAYER_GROUND     = (150, 220, 255)
COLOR_PLAYER_CROUCH     = (200, 200, 200)
COLOR_PLAYER_CHARGE     = (255, 255, 100)
COLOR_PLAYER_DASH       = (255, 120, 50)
COLOR_PLAYER_RECOVERY   = (180, 180, 220)
COLOR_PLAYER_CLING      = (255, 200, 100)
COLOR_PLAYER_SLIDE      = (220, 160, 80)
COLOR_PLAYER_WALLJUMP   = (255, 240, 100)
COLOR_PLAYER_BOUNCE     = (255, 100, 150)
COLOR_PLAYER_FACING     = (255, 255, 255)

text_manager = TextManager(default_size=20)


# ============================================================================
# State machine types
# ============================================================================

class PState(Enum):
    IDLE              = auto()
    RUN               = auto()
    AIRBORNE          = auto()
    JUMP_CROUCH       = auto()
    DASH_CHARGE       = auto()
    DASH_ACTIVE       = auto()
    DASH_RECOVERY     = auto()
    DASH_BOUNCE       = auto()
    WALL_CLING        = auto()
    WALL_SLIDE        = auto()
    WALL_JUMP_WINDUP  = auto()


# States where we take full velocity authority: gravity, drag, speed
# limits, intent processing — all bypassed. We set velocity by hand.
AUTHORITY_STATES = {
    PState.JUMP_CROUCH,
    PState.DASH_CHARGE,
    PState.DASH_ACTIVE,
    PState.DASH_RECOVERY,
    PState.DASH_BOUNCE,
    PState.WALL_CLING,
    PState.WALL_JUMP_WINDUP,
}

# States that own their vertical axis — updrafts don't apply.
DASH_STATES = {
    PState.DASH_CHARGE,
    PState.DASH_ACTIVE,
    PState.DASH_RECOVERY,
    PState.DASH_BOUNCE,
}


@dataclass
class Conditions:
    """What is true this frame. Read-only from the state's perspective."""
    # world
    grounded: bool
    wall_left: bool
    wall_right: bool
    # input held
    left: bool
    right: bool
    jump_held: bool
    # input edges / short-term memory
    jump_pressed: bool
    dash_pressed: bool
    jump_buffered: bool
    coyote: bool


# ============================================================================
# Player
# ============================================================================

class Player:
    def __init__(self, x, y):
        self.size = PLAYER_SIZE

        # === MOTION2D ===
        self.motion = Motion2D.platformer(
            pos=(x, y),
            speed=PLAYER_SPEED,
            acceleration=PLAYER_ACCELERATION,
            deceleration=PLAYER_DECELERATION,
            gravity=PLAYER_GRAVITY,
            jump_strength=PLAYER_JUMP_STRENGTH,
            max_fall_speed=PLAYER_MAX_FALL,
            auto_face=True,
        )
        # Headroom for the dash impulse. Intent-driven movement still
        # targets `speed`, so this cap only matters during authority frames.
        self.motion.body.max_x_speed = DASH_SPEED

        # --- state machine ---
        self.state = PState.IDLE
        self.started = False

        # --- shared conditions ---
        self.coyote = Timer(duration=COYOTE_TIME, autostart=False)
        self.jump_buffer = Timer(duration=JUMP_BUFFER, autostart=False)

        # --- input edges ---
        self._jump_was_held = False
        self._dash_was_held = False

        # --- abilities ---
        self.double_jump_avail = True
        self.dash_available = True

        # --- per-state scratch ---
        self.state_timer = Timer(duration=0.1, autostart=False)
        self._jump_from_ground = True
        self._jump_is_running = False
        self._jump_power_mult = 1.0
        self._dash_dir = Vector2(1, 0)
        self._wall_side = None
        self._wall_dir_x = 0
        self._bounce_dir_x = 0
        self._bounce_fired = False

        # --- collision memory (for cross-frame reactions) ---
        self._last_blocked_x = False

        # --- misc ---
        self.is_jumping = False
        self.riding_platform = None

    # ------------------------------------------------------------------
    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            self.motion.position.x - self.size // 2,
            self.motion.position.y - self.size // 2,
            self.size, self.size,
        )

    # ------------------------------------------------------------------
    # Transition helpers (called from inside a state branch)
    # ------------------------------------------------------------------
    def _begin_jump(self, from_ground: bool, running: bool) -> None:
        self._jump_from_ground = from_ground
        self._jump_is_running = running
        self.jump_buffer.stop()
        if from_ground:
            self.coyote.stop()
        else:
            self.double_jump_avail = False
        self.state = PState.JUMP_CROUCH

    def _begin_dash(self, c: Conditions) -> None:
        if c.left:
            self._dash_dir = Vector2(-1, 0)
        elif c.right:
            self._dash_dir = Vector2(1, 0)
        else:
            self._dash_dir = Vector2(self.motion.heading.vector.x, 0)
            if self._dash_dir.length_squared() == 0:
                self._dash_dir = Vector2(1, 0)
        self.motion.heading.aim((self._dash_dir.x, 0), snap=True)
        self.dash_available = False
        self.state = PState.DASH_CHARGE

    # ------------------------------------------------------------------
    # Master update
    # ------------------------------------------------------------------
    def update(self, dt, keys, platforms, updrafts):
        # ---- 1. probe world ----
        tlx, tly = center_to_topleft(
            self.motion.position.x, self.motion.position.y,
            self.size, self.size,
        )
        grounded = is_grounded(tlx, tly, self.size, self.size, platforms)
        wall_left = query_left(tlx, tly, self.size, self.size, platforms)
        wall_right = query_right(tlx, tly, self.size, self.size, platforms)

        # ---- 2. input edges + holds ----
        left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        jump_held = (keys[pygame.K_UP] or keys[pygame.K_SPACE]
                     or keys[pygame.K_w])
        dash_held = keys[pygame.K_LSHIFT] or keys[pygame.K_x]

        jump_pressed = jump_held and not self._jump_was_held
        dash_pressed = dash_held and not self._dash_was_held
        self._jump_was_held = jump_held
        self._dash_was_held = dash_held

        # ---- 3. condition timers (memory) ----
        if grounded:
            self.coyote.reset()
        else:
            self.coyote.update(dt)

        if jump_pressed:
            self.jump_buffer.reset()
        else:
            self.jump_buffer.update(dt)

        # ---- 4. grounded ability refresh ----
        if grounded:
            self.double_jump_avail = True
            self.dash_available = True

        # ---- 5. build conditions ----
        c = Conditions(
            grounded=grounded,
            wall_left=wall_left,
            wall_right=wall_right,
            left=left, right=right,
            jump_held=jump_held,
            jump_pressed=jump_pressed,
            dash_pressed=dash_pressed,
            jump_buffered=self.jump_buffer.active,
            coyote=self.coyote.active,
        )

        # ---- 6. state logic (transitions + per-state velocity) ----
        self._update_state(dt, c)

        # ---- 7. updrafts (suppressed during dash family) ----
        if self.state not in DASH_STATES:
            for zone in updrafts:
                if self.rect.colliderect(zone):
                    self.motion.velocity.y += UPDRAFT_FORCE * dt
                    self.motion.velocity.y = max(self.motion.velocity.y, -600)

        # ---- 8. variable jump cut ----
        if self.is_jumping:
            if not jump_held and self.motion.velocity.y < 0:
                self.motion.velocity.y *= JUMP_CUT_MULT
                self.is_jumping = False
            elif self.motion.velocity.y >= 0:
                self.is_jumping = False

        # ---- 9. delta: authority vs normal physics ----
        if self.state in AUTHORITY_STATES:
            delta = self.motion.authority(dt)
        else:
            delta = self.motion.step_velocity(dt)

        if self.riding_platform is not None:
            delta.x += self.riding_platform.dx

        # ---- 10. collision ----
        result = resolve_swept(
            tlx, tly, self.size, self.size,
            delta.x, delta.y, platforms, max_step=MAX_STEP,
        )
        cx, cy = topleft_to_center(result.x, result.y, self.size, self.size)
        self.motion.position = Vector2(cx, cy)

        # stash for next frame's state logic (dash-into-wall check)
        self._last_blocked_x = result.blocked_x

        if result.blocked_x:
            self.motion.velocity.x = 0
        if result.blocked_y:
            self.motion.velocity.y = 0

        # ---- 11. riding state for next frame ----
        if grounded:
            self.riding_platform = find_down(
                tlx, tly, self.size, self.size, platforms,
            )
        else:
            self.riding_platform = None

    # ==================================================================
    # STATE LOGIC
    # ==================================================================
    # One branch per state. The pattern in every branch:
    #
    #   if not self.started:   <- ENTRY (once)
    #       ...setup...
    #       self.started = True
    #
    #   ...transition checks...
    #
    #   if self.state != PState.CURRENT:   <- LOCAL EXIT (once)
    #       self.started = False
    #
    # Physics is applied inline, in the branch. Intent-using states
    # (IDLE/RUN/AIRBORNE) call move_left/right. Authority states set
    # velocity directly.
    # ==================================================================
    def _update_state(self, dt: float, c: Conditions) -> None:
        # Fresh intent every frame. States add to it as needed.
        self.motion.clear_intent()

        # ------------------------------------------------------------------
        if self.state == PState.IDLE:
            if not self.started:
                self.started = True

            if not c.grounded:
                self.state = PState.AIRBORNE
            elif c.dash_pressed and self.dash_available:
                self._begin_dash(c)
            elif c.jump_buffered:
                self._begin_jump(from_ground=True, running=False)
            elif c.left or c.right:
                self.state = PState.RUN

            if self.state != PState.IDLE:
                self.started = False
            return

        # ------------------------------------------------------------------
        if self.state == PState.RUN:
            if not self.started:
                self.started = True

            if c.left:  self.motion.move_left()
            if c.right: self.motion.move_right()

            if not c.grounded:
                self.state = PState.AIRBORNE
            elif c.dash_pressed and self.dash_available:
                self._begin_dash(c)
            elif c.jump_buffered:
                running = abs(self.motion.velocity.x) > PLAYER_SPEED * 0.5
                self._begin_jump(from_ground=True, running=running)
            elif not (c.left or c.right):
                self.state = PState.IDLE

            if self.state != PState.RUN:
                self.started = False
            return

        # ------------------------------------------------------------------
        if self.state == PState.AIRBORNE:
            if not self.started:
                self.started = True

            if c.left:  self.motion.move_left()
            if c.right: self.motion.move_right()

            if c.grounded:
                self.state = PState.RUN if (c.left or c.right) else PState.IDLE
            elif c.wall_left and c.left:
                self._wall_side = 'left'
                self.state = PState.WALL_CLING
            elif c.wall_right and c.right:
                self._wall_side = 'right'
                self.state = PState.WALL_CLING
            elif c.dash_pressed and self.dash_available:
                self._begin_dash(c)
            elif c.jump_buffered:
                if c.coyote:
                    self._begin_jump(from_ground=True, running=False)
                elif self.double_jump_avail:
                    self._begin_jump(from_ground=False, running=False)

            if self.state != PState.AIRBORNE:
                self.started = False
            return

        # ------------------------------------------------------------------
        if self.state == PState.JUMP_CROUCH:
            if not self.started:
                if self._jump_from_ground:
                    dur = (JUMP_CROUCH_RUNNING if self._jump_is_running
                           else JUMP_CROUCH_STANDING)
                else:
                    dur = JUMP_CROUCH_AIR
                self.state_timer.reset(dur)
                self._jump_power_mult = (JUMP_RUNNING_POWER
                                         if self._jump_is_running else 1.0)
                self.started = True

            self.state_timer.update(dt)

            # --- physics: hold still during crouch ---
            if self._jump_from_ground:
                if not self._jump_is_running:
                    self.motion.velocity = Vector2(0, 0)
                else:
                    self.motion.velocity.y = 0
            else:
                if self.motion.velocity.y < 0:
                    self.motion.velocity.y = 0

            # --- transition: fire the impulse, go airborne ---
            if self.state_timer.done:
                power = PLAYER_JUMP_STRENGTH * self._jump_power_mult
                self.motion.jump(power=power)
                self.is_jumping = True
                self.state = PState.AIRBORNE

            if self.state != PState.JUMP_CROUCH:
                self.started = False
            return

        # ------------------------------------------------------------------
        if self.state == PState.DASH_CHARGE:
            if not self.started:
                self.state_timer.reset(DASH_CHARGE_DUR)
                self.started = True

            self.state_timer.update(dt)
            self.motion.velocity.x *= 0.6
            self.motion.velocity.y = 0

            if self.state_timer.done:
                self.state = PState.DASH_ACTIVE

            if self.state != PState.DASH_CHARGE:
                self.started = False
            return

        # ------------------------------------------------------------------
        if self.state == PState.DASH_ACTIVE:
            if not self.started:
                self.state_timer.reset(DASH_ACTIVE_DUR)
                self.started = True

            self.state_timer.update(dt)
            self.motion.velocity = Vector2(self._dash_dir.x * DASH_SPEED, 0)

            if self._last_blocked_x:
                self._bounce_dir_x = -self._dash_dir.x
                self._bounce_fired = False
                self.state = PState.DASH_BOUNCE
            elif self.state_timer.done:
                self.state = PState.DASH_RECOVERY

            if self.state != PState.DASH_ACTIVE:
                self.started = False
            return

        # ------------------------------------------------------------------
        if self.state == PState.DASH_RECOVERY:
            if not self.started:
                self.state_timer.reset(DASH_RECOVERY_DUR)
                self.started = True

            self.state_timer.update(dt)
            self.motion.velocity.x *= 0.7
            self.motion.velocity.y = 0

            if self.state_timer.done:
                self.state = PState.AIRBORNE

            if self.state != PState.DASH_RECOVERY:
                self.started = False
            return

        # ------------------------------------------------------------------
        if self.state == PState.DASH_BOUNCE:
            if not self.started:
                self.state_timer.reset(DASH_WALL_FREEZE + DASH_WALL_BOUNCE)
                self._bounce_fired = False
                self.started = True

            self.state_timer.update(dt)

            if self.state_timer.elapsed < DASH_WALL_FREEZE:
                self.motion.velocity = Vector2(0, 0)
            elif not self._bounce_fired:
                self.motion.velocity = Vector2(
                    self._bounce_dir_x * DASH_SPEED * DASH_WALL_BOUNCE_MULT,
                    -100,
                )
                self._bounce_fired = True

            if self.state_timer.done:
                self.state = PState.AIRBORNE

            if self.state != PState.DASH_BOUNCE:
                self.started = False
            return

        # ------------------------------------------------------------------
        if self.state == PState.WALL_CLING:
            if not self.started:
                self.state_timer.reset(WALL_CLING_DUR)
                self.started = True

            self.state_timer.update(dt)
            self.motion.velocity = Vector2(0, 0)

            still_touching = (
                (self._wall_side == 'left'  and c.wall_left  and c.left) or
                (self._wall_side == 'right' and c.wall_right and c.right)
            )

            if c.grounded:
                self.state = PState.IDLE
            elif not still_touching:
                self.state = PState.AIRBORNE
            elif c.jump_buffered:
                self._wall_dir_x = 1 if self._wall_side == 'left' else -1
                self.motion.heading.aim((self._wall_dir_x, 0), snap=True)
                self.state = PState.WALL_JUMP_WINDUP
            elif self.state_timer.done:
                self.state = PState.WALL_SLIDE

            if self.state != PState.WALL_CLING:
                self.started = False
            return

        # ------------------------------------------------------------------
        if self.state == PState.WALL_SLIDE:
            if not self.started:
                self.started = True

            self.motion.velocity.x = 0
            if self.motion.velocity.y > WALL_SLIDE_SPEED:
                self.motion.velocity.y = WALL_SLIDE_SPEED

            still_touching = (
                (self._wall_side == 'left'  and c.wall_left  and c.left) or
                (self._wall_side == 'right' and c.wall_right and c.right)
            )

            if c.grounded:
                self.state = PState.IDLE
            elif not still_touching:
                self.state = PState.AIRBORNE
            elif c.jump_buffered:
                self._wall_dir_x = 1 if self._wall_side == 'left' else -1
                self.motion.heading.aim((self._wall_dir_x, 0), snap=True)
                self.state = PState.WALL_JUMP_WINDUP

            if self.state != PState.WALL_SLIDE:
                self.started = False
            return

        # ------------------------------------------------------------------
        if self.state == PState.WALL_JUMP_WINDUP:
            if not self.started:
                self.state_timer.reset(WALL_JUMP_WINDUP_DUR)
                self.started = True

            self.state_timer.update(dt)
            self.motion.velocity = Vector2(0, 0)

            if self.state_timer.done:
                self.motion.velocity = Vector2(
                    self._wall_dir_x * WALL_JUMP_X,
                    -WALL_JUMP_Y,
                )
                self.is_jumping = True
                self.state = PState.AIRBORNE

            if self.state != PState.WALL_JUMP_WINDUP:
                self.started = False
            return

    # ==================================================================
    # Draw
    # ==================================================================
    def draw(self, screen):
        state_colors = {
            PState.DASH_BOUNCE:      COLOR_PLAYER_BOUNCE,
            PState.WALL_JUMP_WINDUP: COLOR_PLAYER_WALLJUMP,
            PState.WALL_CLING:       COLOR_PLAYER_CLING,
            PState.WALL_SLIDE:       COLOR_PLAYER_SLIDE,
            PState.JUMP_CROUCH:      COLOR_PLAYER_CROUCH,
            PState.DASH_CHARGE:      COLOR_PLAYER_CHARGE,
            PState.DASH_ACTIVE:      COLOR_PLAYER_DASH,
            PState.DASH_RECOVERY:    COLOR_PLAYER_RECOVERY,
            PState.IDLE:             COLOR_PLAYER_GROUND,
            PState.RUN:              COLOR_PLAYER_GROUND,
        }
        color = state_colors.get(self.state, COLOR_PLAYER)

        if self.state == PState.DASH_ACTIVE:
            for i in range(5):
                alpha = 120 - i * 25
                offset = -self._dash_dir * (i + 1) * 8
                trail = self.motion.position + offset
                surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
                pygame.draw.rect(
                    surf, (255, 200, 100, alpha),
                    (0, 0, self.size, self.size), border_radius=4,
                )
                screen.blit(surf, (trail.x - self.size / 2,
                                   trail.y - self.size / 2))

        rect = self.rect
        pygame.draw.rect(screen, color, rect, border_radius=4)
        pygame.draw.rect(screen, (255, 255, 255), rect,
                         width=2, border_radius=4)

        fv = self.motion.heading.vector
        if fv.x > 0:
            tip_x, base_x = rect.right + 6, rect.right + 1
        else:
            tip_x, base_x = rect.left - 6, rect.left - 1
        pygame.draw.polygon(
            screen, COLOR_PLAYER_FACING,
            [(tip_x, rect.centery),
             (base_x, rect.centery - 5),
             (base_x, rect.centery + 5)],
        )

    # ------------------------------------------------------------------
    def check_respawn(self):
        if self.motion.position.y > SCREEN_HEIGHT + 100:
            self.reset_state(Vector2(100, 450))

    def reset_state(self, pos):
        self.motion.position = pos
        self.motion.velocity = Vector2(0, 0)
        self.motion.clear_intent()

        self.state = PState.IDLE
        self.started = False

        self.coyote.stop()
        self.jump_buffer.stop()
        self.state_timer.stop()

        self._jump_was_held = False
        self._dash_was_held = False
        self._last_blocked_x = False

        self.double_jump_avail = True
        self.dash_available = True
        self.is_jumping = False
        self.riding_platform = None

        self._wall_side = None
        self._bounce_fired = False
        self._bounce_dir_x = 0


# ============================================================================
# Environment (unchanged)
# ============================================================================

class StaticPlatform:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.dx = 0.0

    def update(self, dt):
        pass

    def draw(self, screen):
        pygame.draw.rect(screen, COLOR_PLATFORM, self.rect)
        pygame.draw.rect(screen, COLOR_PLATFORM_EDGE, self.rect, width=2)


class MovingPlatform:
    def __init__(self, x, y, w, h, speed, travel_dist):
        self.w, self.h = w, h
        self.start_x = x
        self.travel_dist = travel_dist
        self.dx = 0.0
        self.motion = Motion2D.simple(pos=(x, y), speed=speed)
        self.motion.go_right()

    @property
    def rect(self):
        return pygame.Rect(
            self.motion.position.x, self.motion.position.y, self.w, self.h,
        )

    def update(self, dt):
        last_x = self.motion.position.x
        self.motion.update(dt)
        if self.motion.position.x > self.start_x + self.travel_dist:
            self.motion.position.x = self.start_x + self.travel_dist
            self.motion.go_reverse()
        elif self.motion.position.x < self.start_x:
            self.motion.position.x = self.start_x
            self.motion.go_reverse()
        self.dx = self.motion.position.x - last_x

    def draw(self, screen):
        rect = self.rect
        pygame.draw.rect(screen, COLOR_MOVING, rect)
        pygame.draw.rect(screen, COLOR_MOVING_EDGE, rect, width=2)


# ============================================================================
# Game
# ============================================================================

class PlatformerDemo:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Demo 9: Platformer Playground (State Machine)")
        text_manager.bind(screen=self.screen)
        self.clock = pygame.time.Clock()
        self.running = True
        self.reset()

    def reset(self):
        self.player = Player(100, 450)

        self.platforms = [
            StaticPlatform(-50, 0, 50, SCREEN_HEIGHT),
            StaticPlatform(SCREEN_WIDTH, 0, 50, SCREEN_HEIGHT),
            StaticPlatform(0, 500, 250, 100),
            StaticPlatform(50, 150, 150, 20),
            StaticPlatform(350, 350, 100, 20),
            StaticPlatform(550, 150, 20, 350),
            StaticPlatform(750, 100, 20, 450),
            StaticPlatform(600, 100, 120, 20),
        ]

        self.updrafts = [pygame.Rect(250, 200, 80, 400)]

        self.moving_bridge = MovingPlatform(
            x=250, y=550, w=150, h=5, speed=100, travel_dist=300,
        )
        self.platforms.append(self.moving_bridge)

        self.goal_rect = pygame.Rect(700, 50, 50, 50)
        self.won = False

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_r:
                    self.reset()

    def update(self, dt):
        keys = pygame.key.get_pressed()
        for p in self.platforms:
            p.update(dt)
        self.player.update(dt, keys, self.platforms, self.updrafts)
        self.player.check_respawn()
        if not self.won and self.player.rect.colliderect(self.goal_rect):
            self.won = True

    def draw(self):
        self.screen.fill(COLOR_SKY)
        for x in range(0, SCREEN_WIDTH, 40):
            pygame.draw.line(self.screen, COLOR_GRID, (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, 40):
            pygame.draw.line(self.screen, COLOR_GRID, (0, y), (SCREEN_WIDTH, y))

        for zone in self.updrafts:
            surf = pygame.Surface((zone.w, zone.h), pygame.SRCALPHA)
            surf.fill((100, 200, 255, 40))
            t = pygame.time.get_ticks() / 1000.0
            offset = (t * 200) % 40
            for y in range(int(zone.h + 40)):
                if (y - int(offset)) % 40 == 0:
                    draw_y = zone.h - y + offset
                    if 0 < draw_y < zone.h:
                        pygame.draw.line(
                            surf, (150, 220, 255, 120),
                            (10, draw_y), (zone.w - 10, draw_y), 2,
                        )
            self.screen.blit(surf, zone)

        for p in self.platforms:
            p.draw(self.screen)
        pygame.draw.rect(self.screen, COLOR_GOAL, self.goal_rect, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_GOAL_EDGE, self.goal_rect,
                         width=3, border_radius=6)

        self.player.draw(self.screen)

        text_manager.write_centered(8, "DEMO 9: Platformer Playground", size=26)
        text_manager.write(
            10, 45,
            "Arrows: Move | Space: Jump | Space in air: Double Jump | "
            "Shift: Air Dash | Wall: hold into it, Jump to launch",
            size=14, color=(180, 180, 180),
        )

        p = self.player
        hud = [
            f"State: {p.state.name}",
            f"Double Jump: {'READY' if p.double_jump_avail else 'USED'}",
            f"Dash:        {'READY' if p.dash_available else 'USED'}",
        ]
        text_manager.write_multiple_line(
            SCREEN_WIDTH - 260, 10, hud, size=16, color=(200, 255, 200),
        )

        if self.won:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            self.screen.blit(overlay, (0, 0))
            text_manager.write_centered(
                SCREEN_HEIGHT // 2 - 20, "YOU WIN!",
                size=64, color=(100, 255, 100),
            )
            text_manager.write_centered(
                SCREEN_HEIGHT // 2 + 40, "Press R to play again",
                size=24, color=(220, 220, 220),
            )

        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.1)
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()


if __name__ == "__main__":
    PlatformerDemo().run()
