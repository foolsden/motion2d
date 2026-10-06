"""
Demo 10: Custom Motion — Building VehicleMotion
================================================
Shows how to build your OWN motion class on top of Motion2D's
KinematicBody, and drive it with the same workflow the built-in
motion classes use:

    propose delta -> resolve collision -> commit position

WHAT IT TEACHES:
- Motion2D is a set of primitives, not a framework.
- KinematicBody handles position, velocity, drag, and max speed.
  A custom motion class only needs to compute the *velocity*.
- Custom motion composes with the rest of the stack:
  resolve_swept, anchor_util, time_util — all work identically.
- Extension points matter more than API symmetry. VehicleMotion
  is a work-in-progress; the demo shows its current shape and
  documents the direction future versions may take.

THE CAR:
- VehicleMotion is arcade-style: throttle, brake, steer, handbrake.
- Heading and velocity are separate.
- Grip pulls lateral velocity toward zero. Drift emerges.

CONTROLS:
- Up / W              : Throttle
- Down / S            : Brake / reverse
- Left / Right or A/D : Steer
- Space               : Handbrake (reduce grip -> drift)
- R                   : Reset
- ESC                 : Quit
"""

import pygame
from pygame.math import Vector2
from time_util import Timer
from anchor_util import center_to_topleft, topleft_to_center
from collide2d import resolve_swept
from text_manager import TextManager

# Import the custom motion class we're demonstrating.
from carmotion import VehicleMotion


# ============================================================================
# Constants
# ============================================================================

SCREEN_WIDTH = 900
SCREEN_HEIGHT = 640
FPS = 60

MAX_STEP = 0.5

# Colors
COLOR_SKY = (30, 30, 45)
COLOR_GRID = (22, 22, 36)
COLOR_PLATFORM = (100, 100, 110)
COLOR_PLATFORM_EDGE = (140, 140, 150)
COLOR_CAR = (255, 100, 100)
COLOR_CAR_DRIFT = (255, 200, 60)
COLOR_CAR_FACING = (255, 255, 255)
COLOR_SKID = (60, 60, 80)
COLOR_TEXT = (200, 200, 200)

text_manager = TextManager(default_size=20)


# ============================================================================
# Skid mark — a fading rectangle left behind while drifting
# ============================================================================

class SkidMark:
    def __init__(self, pos, size, life=1.2):
        self.pos = Vector2(pos)
        self.size = size
        self.life = life
        self.max_life = life
        self.alive = True

    def update(self, dt):
        self.life -= dt
        if self.life <= 0:
            self.alive = False

    def draw(self, screen):
        alpha = int(120 * (self.life / self.max_life))
        if alpha <= 0:
            return
        surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        surf.fill((*COLOR_SKID, alpha))
        screen.blit(surf, (self.pos.x - self.size / 2, self.pos.y - self.size / 2))


# ============================================================================
# Wall — a static rectangle the car collides with
# ============================================================================

class Wall:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)

    def draw(self, screen):
        pygame.draw.rect(screen, COLOR_PLATFORM, self.rect)
        pygame.draw.rect(screen, COLOR_PLATFORM_EDGE, self.rect, width=2)


# ============================================================================
# Car — owns the VehicleMotion and draws itself rotated
# ============================================================================

class Car:
    def __init__(self, pos, preset="sport"):
        self.size = 36        # bounding box (used for collision)
        self.motion = VehicleMotion.preset(preset, pos=pos)

        # Skid marks emitted while drifting.
        self.skid_marks = []
        self._skid_timer = Timer(duration=0.04, autostart=False)

    @property
    def rect(self):
        """AABB around the car for collision (top-left, matches collide2d)."""
        return pygame.Rect(
            self.motion.position.x - self.size // 2,
            self.motion.position.y - self.size // 2,
            self.size, self.size,
        )

    def handle_input(self, keys):
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.motion.throttle(1.0)
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.motion.brake(1.0)
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.motion.steer(-1.0)
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.motion.steer(1.0)
        if keys[pygame.K_SPACE]:
            self.motion.handbrake(True)

    def update(self, dt, walls):
        # === CUSTOM MOTION: COLLISION INTEGRATION ===
        # VehicleMotion currently uses the simple update() path — it
        # advances velocity AND position together. For external collision,
        # we:
        #   1. Save the position
        #   2. Let VehicleMotion do its update
        #   3. Compute the delta it wanted to move
        #   4. Restore the saved position
        #   5. Resolve the delta against the world
        #   6. Commit the resolved position
        #
        # This is the honest state of VehicleMotion v1.2. A future version
        # may expose step_velocity() to make this cleaner.
        # --- What a future VehicleMotion.step_velocity() would look like ---
        #
        # def step_velocity(self, dt):
        #     # ... the velocity portion of update() ...
        #     return self.body.step_velocity(dt)
        #
        # Then Demo 10's Car.update would become:
        #
        #     delta = self.motion.step_velocity(dt)
        #     result = resolve_swept(...)
        #     self.motion.body.position = Vector2(result.x, result.y)
        #
        # Same workflow as Demo 8 and 9. Not implemented yet, but the
        # direction is clear.
        pos_before = Vector2(self.motion.position)
        self.motion.update(dt)
        delta = self.motion.position - pos_before
        # === END CUSTOM MOTION USAGE ===

        # 2. Resolve collision using the same workflow as Demo 8/9.
        tlx, tly = center_to_topleft(
            self.motion.position.x, self.motion.position.y,
            self.size, self.size,
        )
        # Undo the motion's internal position integration so we can
        # resolve the delta against the world ourselves.
        self.motion.body.position = pos_before

        result = resolve_swept(
            tlx - delta.x, tly - delta.y,   # top-left before move
            self.size, self.size,
            delta.x, delta.y, [w.rect for w in walls],
            max_step=MAX_STEP,
        )
        cx, cy = topleft_to_center(result.x, result.y, self.size, self.size)
        self.motion.body.position = Vector2(cx, cy)

        # Kill velocity on blocked axes.
        if result.blocked_x:
            self.motion.velocity.x = 0
        if result.blocked_y:
            self.motion.velocity.y = 0

        # 3. Skid marks while drifting.
        self._skid_timer.update(dt)
        if self.motion.is_drifting:
            if self._skid_timer.done:
                self._skid_timer.reset()
                # Emit two marks (left and right of the car).
                right = Vector2(1, 0).rotate(self.motion.heading_angle + 90)
                offset = right * (self.size * 0.35)
                self.skid_marks.append(
                    SkidMark(self.motion.position + offset, 6)
                )
                self.skid_marks.append(
                    SkidMark(self.motion.position - offset, 6)
                )

        # 4. Update and prune skid marks.
        for m in self.skid_marks:
            m.update(dt)
        self.skid_marks = [m for m in self.skid_marks if m.alive]

    def reset(self, pos, angle=0.0):
        self.motion.reset(pos=pos, angle=angle)
        self.skid_marks.clear()

    def draw(self, screen):
        # Skid marks first (below the car).
        for m in self.skid_marks:
            m.draw(screen)

        # --- draw the car as a rotated rectangle ---
        pos = self.motion.position
        angle_rad = math.radians(self.motion.heading_angle)

        # Local-space corners (half-extents).
        half_l = self.size * 0.55   # length
        half_w = self.size * 0.30   # width

        local_corners = [
            (-half_l, -half_w),
            ( half_l, -half_w),
            ( half_l,  half_w),
            (-half_l,  half_w),
        ]

        # Rotate + translate to world.
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        world_corners = []
        for lx, ly in local_corners:
            wx = pos.x + cos_a * lx - sin_a * ly
            wy = pos.y + sin_a * lx + cos_a * ly
            world_corners.append((wx, wy))

        body_color = COLOR_CAR_DRIFT if self.motion.is_drifting else COLOR_CAR
        pygame.draw.polygon(screen, body_color, world_corners)
        pygame.draw.polygon(screen, (255, 255, 255), world_corners, 2)

        # Small dot on the front so we can see which way it's facing.
        front_x = pos.x + cos_a * (half_l + 4)
        front_y = pos.y + sin_a * (half_l + 4)
        pygame.draw.circle(screen, (255, 255, 255),
                           (int(front_x), int(front_y)), 3)


# Need math for the draw function.
import math


# ============================================================================
# Game
# ============================================================================

class VehicleDemo:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Demo 10: Custom Motion — VehicleMotion")
        text_manager.bind(screen=self.screen)
        self.clock = pygame.time.Clock()
        self.running = True
        self.reset()

    def reset(self):
        self.car = Car((150, 200))

        # An arena with walls.
        self.walls = [
            Wall(-50, -100, 50, SCREEN_HEIGHT + 200),       # left
            Wall(SCREEN_WIDTH, -100, 50, SCREEN_HEIGHT + 200),  # right
            Wall(-50, -50, SCREEN_WIDTH + 100, 50),         # top
            Wall(-50, SCREEN_HEIGHT, SCREEN_WIDTH + 100, 50),  # bottom
            # Interior obstacles.
            Wall(300, 150, 200, 30),
            Wall(650, 400, 30, 200),
            Wall(400, 480, 200, 30),
        ]

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
        self.car.handle_input(keys)
        self.car.update(dt, self.walls)

    def draw(self):
        self.screen.fill(COLOR_SKY)

        for x in range(0, SCREEN_WIDTH, 40):
            pygame.draw.line(self.screen, COLOR_GRID, (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, 40):
            pygame.draw.line(self.screen, COLOR_GRID, (0, y), (SCREEN_WIDTH, y))

        for w in self.walls:
            w.draw(self.screen)

        self.car.draw(self.screen)

        # --- HUD ---
        text_manager.write_centered(
            8, "DEMO 10: Custom Motion — VehicleMotion",
            size=26, color=(255, 255, 255),
        )
        text_manager.write(
            10, 45,
            "Up/W: Throttle | Down/S: Brake | Left/Right: Steer | "
            "Space: Handbrake (drift) | R: Reset | ESC: Quit",
            size=14, color=(180, 180, 180),
        )

        # Live car diagnostics.
        speed = self.car.motion.speed
        slip = self.car.motion.slip_angle
        drifting = self.car.motion.is_drifting
        status_color = (255, 200, 60) if drifting else (150, 200, 255)

        text_manager.write(
            SCREEN_WIDTH - 260, 10,
            f"Speed: {int(speed):>4}  px/s",
            size=16, color=(200, 255, 200),
        )
        text_manager.write(
            SCREEN_WIDTH - 260, 32,
            f"Slip:  {slip:+6.1f}°",
            size=16, color=(200, 200, 255),
        )
        text_manager.write(
            SCREEN_WIDTH - 260, 54,
            f"DRIFTING" if drifting else "        ",
            size=16, color=status_color,
        )
        text_manager.write(
            SCREEN_WIDTH - 260, 76,
            f"Skid marks: {len(self.car.skid_marks)}",
            size=14, color=(140, 140, 160),
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
    VehicleDemo().run()
