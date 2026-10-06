"""
Demo 7: Inertia Dodger
======================
Top-down bullet dodging with inertia, continuous dash, and freeze.

MOTION2D FEATURES SHOWN:
- TopDownMotion with grip=0      → pure inertia (slippery stop)
- Facing(directions=4)           → Zelda-style snap + rect orientation
- auto_aim=True                  → facing follows movement intent
- apply_force()                  → continuous dash (bypassing dash())
- SimpleMotion                   → enemy bullets

TIME_UTIL FEATURES SHOWN:
- Timer (repeat, spill_over)     → bullet spawner without timing drift
- Timer (duration)               → freeze, freeze cooldown, dash, i-frames
- Resource (drain + regen)       → dash meter
- Stopwatch                      → difficulty ramp clock

CONTROLS:
- WASD / Arrows  : Move (has inertia!)
- Mouse Click     : Dash toward mouse (destroys bullets)
- Q / Right Click : Freeze all bullets (2s duration, 6s cooldown)
- R               : Restart (on game over)
- ESC             : Quit

DESIGN NOTES:
- Player rect is 4:3 and swaps orientation based on facing.
  Horizontal facing = wide (32×24). Vertical facing = tall (24×32).
  This makes the player easier/harder to hit depending on orientation.
- During dash, facing stays snapped to the last movement direction.
  The body can "look down" while dashing up-right. This is intentional
  (a charming visual gag). Do NOT "fix" it by aiming facing at the
  dash direction — the mismatch is the point.
"""

import pygame
import random
import math
from pygame.math import Vector2
from motion2d import Motion2D, Facing
from time_util import Timer, Resource, Stopwatch
from text_manager import TextManager


# ============================================================================
# Constants
# ============================================================================

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Player rect — 4:3 in horizontal orientation, swapped for vertical
PLAYER_W = 32
PLAYER_H = 24
BULLET_SIZE = 12

# Movement
ACCELERATION = 2000
DECELERATION = 500    # Low on purpose — slippery, must counter-steer
MAX_SPEED = 320

# Dash (continuous, applied via apply_force each frame)
DASH_FORCE = 2000
DASH_MAX_SPEED = 800    # temporary max_speed during dash
DASH_METER_MAX = 1.0
DASH_METER_REGEN = 0.1
DASH_IFRAMES = 0.40
DASH_INITIAL_COST = 0.15

# Freeze
FREEZE_DURATION = 2.0
FREEZE_COOLDOWN = 6.0

# Bullet spawner
SPAWN_INTERVAL_START = 0.18
SPAWN_INTERVAL_MIN = 0.08
SPAWN_RAMP_PER_SEC = 0.005   # interval shrinks 5ms per elapsed second

text_manager = TextManager(default_size=24)


# ============================================================================
# Player
# ============================================================================

class Player:
    """
    Rectangular player with inertia, 4-direction facing, and continuous dash.
    [MOTION2D] TopDownMotion with grip=0 for pure inertia.
    [MOTION2D] Facing(4) for Zelda-style directional snap.
    [MOTION2D] auto_aim=True so the motion updates facing from intent.
    [MOTION2D] apply_force() for continuous dash (bypassing dash()).
    [TIME_UTIL] Resource for the dash meter.
    [TIME_UTIL] Timer for post-dash invulnerability.
    """

    def __init__(self, pos):
        # === MOTION2D USAGE ===
        # Facing(4) — Zelda-style snap with horizontal priority.
        # Horizontal priority is built into Facing: when both axes are
        # pressed, |x| >= |y| snaps to horizontal.
        self.facing = Facing(initial_vector=(1, 0), directions=4)

        # grip=0 → velocity is not auto-aligned to heading.
        # auto_aim=True → motion updates facing from movement intent.
        self.motion = Motion2D.top_down(
            pos=pos,
            speed=MAX_SPEED,
            acceleration=ACCELERATION,
            deceleration=DECELERATION,
            heading=self.facing,
            auto_aim=True,
            grip=0.0,
        )
        # === END OF MOTION2D USAGE ===

        # Dash direction is a raw Vector2, independent of facing.
        # Storing a Vector2 (not a Rotator) keeps this simple — the
        # direction doesn't need to change during the dash.
        self.dash_dir = Vector2(1, 0)
        self.is_dashing = False
        self.dash_mouse_held = False  # Track physical click state

        # [TIME_UTIL] Dash meter — Resource drains & regenerates
        self.dash_meter = Resource(maximum=DASH_METER_MAX, regen_rate=DASH_METER_REGEN)

        # [TIME_UTIL] Post-dash invulnerability
        self.iframes = Timer(duration=DASH_IFRAMES, repeat=False, autostart=False)

        # [TIME_UTIL] Dash-exit braking window.
        # After the dash ends, apply strong exponential braking for
        # a short period so the player returns to normal speed quickly.
        # Without this, the low global deceleration (the whole point of
        # inertia) would make dash exit feel sticky for over a second.
        self.dash_exit = Timer(duration=0.3, repeat=False, autostart=False)

        # Hit flash (visual only)
        self.hit_flash = Timer(duration=0.3, repeat=False, autostart=False)

    def handle_input(self, keys):
        """
        Only adds intent. Does NOT clear intent — update() clears it.
        Does NOT aim facing manually — auto_aim=True handles that.
        """
        if not self.is_dashing:
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                # === MOTION2D USAGE ===
                self.motion.move_up()
                # === END OF MOTION2D USAGE ===
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                # === MOTION2D USAGE ===
                self.motion.move_down()
                # === END OF MOTION2D USAGE ===
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                # === MOTION2D USAGE ===
                self.motion.move_left()
                # === END IFMOTION2D USAGE ===
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                # === MOTION2D USAGE ===
                self.motion.move_right()
                # === END OF MOTION2D USAGE ===

    def handle_event(self, event):
        """Processes discrete events for dashing and state transitions."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.dash_mouse_held = True
            self._try_start_dash()

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dash_mouse_held = False
            self._stop_dash()

    def _try_start_dash(self):
        """Attempts to start dashing toward the mouse if conditions permit."""
        if self.is_dashing:
            return

        # 1. Check if resource covers initial activation cost
        if not self.dash_meter.can_spend(DASH_INITIAL_COST):
            return

        # 2. Check mouse vector
        mouse_pos = pygame.mouse.get_pos()
        to_mouse = Vector2(mouse_pos) - self.motion.position
        if to_mouse.length_squared() <= 0.001:
            return

        # 3. Pay cost and engage dash
        self.dash_meter.spend(DASH_INITIAL_COST)
        self.dash_dir = to_mouse.normalize()
        self.is_dashing = True

        self.iframes.reset()
        self.dash_exit.stop()

    def _stop_dash(self):
        """Disengages dash state and starts braking transition."""
        if self.is_dashing:
            self.is_dashing = False
            self.dash_exit.reset()

    def update(self, dt):
        # [TIME_UTIL] Update i-frames and hit flash
        self.iframes.update(dt)
        self.hit_flash.update(dt)
        self.dash_exit.update(dt)

        # Continuous dash via apply_force.
        # dash() is a one-shot impulse along heading; here we want a
        # sustained push along a direction independent of facing. So we
        # bypass dash() and use the primitive apply_force() directly.
        if self.is_dashing:
            # === MOTION2D USAGE ===
            # Dash overrides normal WASD intent
            self.motion.clear_intent()
            # === END OF MOTION2D USAGE ===

        # 2. Dash physics & continuous consumption
        if self.is_dashing:
            self.motion.clear_intent()
            self.motion.body.max_speed = DASH_MAX_SPEED
            self.motion.body.apply_force(self.dash_dir * DASH_FORCE, dt)

            # Continuous drain (1.0 units per second)
            drained = self.dash_meter.drain(1.0 * dt)

            # Force cancel if meter empties completely
            if drained <= 0 or self.dash_meter.is_empty:
                self._stop_dash()
        else:
            self.motion.body.max_speed = MAX_SPEED

            # REGEN RULE: Regenerate ONLY if the mouse button is physically released
            if not self.dash_mouse_held:
                self.dash_meter.update(dt)

        # Dash-exit braking
        if self.dash_exit.active:
            # === MOTION2D USAGE ===
            # Exponential decay of velocity. The rate here is much
            # higher than the global deceleration so the exit is
            # decisive. Math.exp with a high rate → fast drop.
            self.motion.body.vel *= math.exp(-6.0 * dt)
            # === END OF MOTION2D USAGE ===

        # === MOTION2D USAGE ===
        # Physics update. auto_aim will aim facing at intent.
        self.motion.update(dt)
        # === END OF MOTION2D USAGE ===

        # Clamp to screen using the *current* rect orientation
        r = self.rect()
        pos = self.motion.position
        pos.x = max(r.width / 2, min(SCREEN_WIDTH - r.width / 2, pos.x))
        pos.y = max(r.height / 2, min(SCREEN_HEIGHT - r.height / 2, pos.y))
        self.motion.position = pos


    @property
    def is_invulnerable(self) -> bool:
        return self.is_dashing or self.iframes.active

    def take_hit(self):
        self.hit_flash.reset()

    def rect(self) -> pygame.Rect:
        """
        AABB that swaps dimensions based on facing direction.

        4:3 horizontal (32×24) when facing left/right.
        3:4 vertical (24×32) when facing up/down.

        This creates a gameplay mechanic: you dodge better along the
        axis perpendicular to your facing.
        """
        pos = self.motion.position
        fv = self.facing.vector

        # Facing(4) guarantees the vector is on one of 4 axes, so
        # abs(fv.x) vs abs(fv.y) cleanly identifies the orientation.
        if abs(fv.x) > abs(fv.y):
            w, h = PLAYER_W, PLAYER_H
        else:
            w, h = PLAYER_H, PLAYER_W

        r = pygame.Rect(0, 0, w, h)
        r.center = (int(pos.x), int(pos.y))
        return r

    def draw(self, screen):
        pos = self.motion.position

        # Dash trail
        if self.is_dashing:
            for i in range(4):
                alpha = 120 - i * 30
                offset = -self.dash_dir * (i + 1) * 10
                trail_pos = pos + offset
                surf = pygame.Surface((PLAYER_W, PLAYER_H), pygame.SRCALPHA)
                pygame.draw.rect(surf, (150, 220, 255, alpha),
                                 (0, 0, PLAYER_W, PLAYER_H), border_radius=4)
                screen.blit(surf, (trail_pos.x - PLAYER_W / 2,
                                   trail_pos.y - PLAYER_H / 2))

        # Body color
        if self.hit_flash.active and int(self.hit_flash.elapsed * 30) % 2 == 0:
            body_color = (255, 100, 100)
        elif self.iframes.active:
            body_color = (255, 255, 180)
        else:
            body_color = (100, 180, 255)

        # Body — use the rect() so the visual matches the hitbox
        rect = self.rect()
        pygame.draw.rect(screen, body_color, rect, border_radius=4)
        pygame.draw.rect(screen, (255, 255, 255), rect, width=2, border_radius=4)

        # Facing indicator: a small dot on the facing side
        fv = self.facing.vector
        indicator = pos + fv * 10
        pygame.draw.circle(screen, (255, 255, 255),
                           (int(indicator.x), int(indicator.y)), 3)


# ============================================================================
# Bullet
# ============================================================================
class Bullet:
    """
    Square bullet using SimpleMotion.

    [MOTION2D] SimpleMotion for straight-line flight.

    Freeze handling is done by the game loop (skipping update()),
    not by the bullet itself. Motion2D has no pause API because
    "pause" is a game-level concern, not a physics-level one.
    """
    def __init__(self, pos, direction, speed):
        # === MOTION2D USAGE ===
        # SimpleMotion for the bullet flight
        self.motion = Motion2D.simple(pos=pos, speed=speed)
        self.motion.go(direction)
        # === END OF MOTION2D USAGE ===

        self._trail = []
        self._max_trail = 6

        self.alive = True

    def update(self, dt):
        """Advance the bullet. Only called when not frozen."""
        # === MOTION2D USAGE ===
        # SimpleMotion tick
        self.motion.update(dt)
        # === END OF MOTION2D USAGE ===

        self._trail.append(Vector2(self.motion.position))
        if len(self._trail) > self._max_trail:
            self._trail.pop(0)

        # Off-screen cleanup
        pos = self.motion.position
        margin = 40
        if (pos.x < -margin or pos.x > SCREEN_WIDTH + margin or
            pos.y < -margin or pos.y > SCREEN_HEIGHT + margin):
            self.alive = False

    def rect(self) -> pygame.Rect:
        pos = self.motion.position
        r = pygame.Rect(0, 0, BULLET_SIZE, BULLET_SIZE)
        r.center = (int(pos.x), int(pos.y))
        return r

    def draw(self, screen, frozen):
        for i, tpos in enumerate(self._trail):
            alpha = int((i / max(1, len(self._trail))) * 80)
            if alpha > 0:
                surf = pygame.Surface((BULLET_SIZE, BULLET_SIZE), pygame.SRCALPHA)
                color = (150, 200, 255, alpha) if frozen else (255, 100, 100, alpha)
                pygame.draw.rect(surf, color, (0, 0, BULLET_SIZE, BULLET_SIZE), border_radius=2)
                screen.blit(surf, (tpos.x - BULLET_SIZE / 2, tpos.y - BULLET_SIZE / 2))

        rect = self.rect()
        if frozen:
            color = (150, 200, 255)
            border = (200, 230, 255)
        else:
            color = (255, 80, 80)
            border = (255, 200, 200)
        pygame.draw.rect(screen, color, rect, border_radius=2)
        pygame.draw.rect(screen, border, rect, width=2, border_radius=2)


# ============================================================================
# Game
# ============================================================================

class InertiaDodger:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        text_manager.bind(screen=self.screen)
        pygame.display.set_caption("Demo 7: Inertia Dodger")
        self.clock = pygame.time.Clock()
        self.running = True
        self.reset()

    def reset(self):
        self.player = Player((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.bullets = []
        self.game_over = False

        # [TIME_UTIL] Stopwatch drives the difficulty ramp.
        # Interval is a pure function of elapsed time, so difficulty
        # scales with wall-clock time regardless of frame rate or
        # how often bullets happen to fire.
        self.difficulty = Stopwatch(autostart=True)

        # [TIME_UTIL] Bullet spawner as a repeating Timer.
        # spill_over=True is critical — the leftover time after each
        # fire carries into the next cycle, preventing timing drift
        # over long sessions.
        self.bullet_spawner = Timer(duration=SPAWN_INTERVAL_START, repeat=True, spill_over=True, on_repeat=self._on_bullet_fired)

        # [TIME_UTIL] Freeze duration + cooldown
        self.freeze_timer = Timer(duration=FREEZE_DURATION, repeat=False, autostart=False)
        self.freeze_cooldown = Timer(duration=FREEZE_COOLDOWN, repeat=False, autostart=False)

    @property
    def is_frozen(self) -> bool:
        return self.freeze_timer.active

    def _on_bullet_fired(self, timer):
        """Called by the spawner Timer on each repeat. Timer parameter is forwarded by Timer class automatically"""
        self.spawn_bullet()
        # Difficulty ramp: interval shrinks as elapsed time grows.
        # Pure function of Stopwatch — no per-fire accumulation.
        t = self.difficulty.elapsed
        self.bullet_spawner.duration = max(
            SPAWN_INTERVAL_MIN,
            SPAWN_INTERVAL_START - t * SPAWN_RAMP_PER_SEC,
        )

    def spawn_bullet(self):
        edge = random.randint(0, 3)
        margin = 20
        if edge == 0:
            pos = Vector2(random.randint(0, SCREEN_WIDTH), -margin)
        elif edge == 1:
            pos = Vector2(SCREEN_WIDTH + margin, random.randint(0, SCREEN_HEIGHT))
        elif edge == 2:
            pos = Vector2(random.randint(0, SCREEN_WIDTH), SCREEN_HEIGHT + margin)
        else:
            pos = Vector2(-margin, random.randint(0, SCREEN_HEIGHT))

        to_player = self.player.motion.position - pos
        if to_player.length_squared() > 0:
            base_dir = to_player.normalize()
            angle = random.uniform(-30, 30)
            base_dir = base_dir.rotate(angle)
        else:
            base_dir = Vector2(1, 0)

        speed = random.uniform(140, 220)
        self.bullets.append(Bullet(pos, base_dir, speed))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_r and self.game_over:
                    self.reset()

            # 2. GAMEPLAY GUARD (One big check for all playing actions)
            if self.game_over:
                continue  # Ignore all gameplay inputs below when game over

            # 3. GAMEPLAY CONTROLS (Only reachable when alive)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    self.try_freeze()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 3:
                    self.try_freeze()

            self.player.handle_event(event)

    def try_freeze(self):
        if self.freeze_cooldown.active or self.is_frozen:
            return
        self.freeze_timer.reset()
        self.freeze_cooldown.reset()

    def update(self, dt):
        if self.game_over:
            return

        keys = pygame.key.get_pressed()

        # Keyboard movement input only
        self.player.handle_input(keys)
        self.player.update(dt)

        # [TIME_UTIL] Tick timers
        self.difficulty.update(dt)
        self.bullet_spawner.update(dt)
        self.freeze_timer.update(dt)
        self.freeze_cooldown.update(dt)

        # === MOTION2D USAGE ===
        # Bullets only tick when not frozen.
        # This is the cleanest way to pause motion — no velocity
        # hacks, no restore logic. The library ticks when the game
        # tells it to. Frozen bullets stay at their current position.
        if not self.is_frozen:
            for b in self.bullets:
                b.update(dt)
        # === END OF MOTION2D USAGE ===

        # Collisions
        player_rect = self.player.rect()
        for b in self.bullets:
            if not b.alive:
                continue
            if player_rect.colliderect(b.rect()):
                if self.player.is_dashing:
                    b.alive = False
                elif not self.player.is_invulnerable:
                    self.player.take_hit()
                    self.game_over = True
                    break

        # Cleanup
        self.bullets = [b for b in self.bullets if b.alive]

    # -------- drawing --------

    def draw_meter(self, x, y, w, h, fraction, fill_color, label=""):
        fraction = max(0.0, min(1.0, fraction))
        pygame.draw.rect(self.screen, (30, 30, 45), (x, y, w, h), border_radius=3)
        fill_w = int(w * fraction)
        if fill_w > 0:
            pygame.draw.rect(self.screen, fill_color, (x, y, fill_w, h), border_radius=3)
        pygame.draw.rect(self.screen, (90, 90, 120), (x, y, w, h), width=1, border_radius=3)
        if label:
            text_manager.write(x, y - 10, label, size=12, color=(200, 200, 200))

    def draw_hud(self):
        text_manager.write_centered(8, "DEMO 7: Inertia Dodger", size=32)

        # Dash meter
        self.draw_meter(x=10, y=70, w=160, h=14, fraction=self.player.dash_meter.fraction, fill_color=(100, 200, 255), label="DASH")

        # Freeze cooldown / active
        if self.is_frozen:
            frac = self.freeze_timer.remaining_fraction
            color = (150, 220, 255)
        elif not self.freeze_cooldown.active:
            frac = 1.0
            color = (200, 255, 200)
        else:
            frac = 1 - self.freeze_cooldown.remaining_fraction
            color = (120, 120, 160)

        self.draw_meter(x=10, y=110, w=160, h=14, fraction=frac, fill_color=color, label="FREEZE")

        text_manager.write_centered(SCREEN_HEIGHT - 26, "WASD: Move | L-Click: Dash | Q / R-Click: Freeze | ESC: Quit", size=18, color=(170, 170, 170))

        text_manager.write_centered(SCREEN_HEIGHT - 50, "MOTION2D: TopDownMotion(grip=0) + Facing(4) + apply_force()  |  TIME_UTIL: Timer + Resource + Stopwatch", size=18, color=(120, 180, 255))

        if self.game_over:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            self.screen.blit(overlay, (0, 0))
            text_manager.write_centered(SCREEN_HEIGHT // 2 - 20, "GAME OVER", size=60, color=(255, 100, 100))
            text_manager.write_centered(SCREEN_HEIGHT // 2 + 40, "Press R to Restart", size=24, color=(220, 220, 220))

    def draw(self):
        self.screen.fill((12, 12, 22))

        # Grid
        for x in range(0, SCREEN_WIDTH, 40):
            pygame.draw.line(self.screen, (20, 20, 34), (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, 40):
            pygame.draw.line(self.screen, (20, 20, 34), (0, y), (SCREEN_WIDTH, y))

        # Bullets
        frozen = self.is_frozen
        for b in self.bullets:
            b.draw(self.screen, frozen)

        # Player
        self.player.draw(self.screen)

        self.draw_hud()

        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()


if __name__ == "__main__":
    InertiaDodger().run()