"""
Demo 8: First Platformer
========================
A single-screen platformer showing how Motion2D, the collision core,
and a coordinate-convention util compose together.

THREE LIBRARIES, ONE DEMO:
- Motion2D            — velocity, gravity, intent (physics)
- collision_core      — AABB geometry in top-left space (resolution)
- anchor_util         — center ↔ top-left (convention bridge)

WHY TWO CONVENTIONS?
The player stores its position as its CENTER. Why? Because the
player is a "character" — it can rotate, aim, face directions, and
be the target of a camera. All of those operations are natural from
a center point.

The collision core works in TOP-LEFT space. Why? Because AABB math
is natural in top-left: the rect is [x, x+w] × [y, y+h], no
half-size terms anywhere.

Neither choice is wrong. They serve different purposes. Rather than
forcing one convention onto both libraries (which would make the
loser awkward), we let each keep what's natural for it, and bridge
the boundary explicitly via anchor_util.

This is a real design lesson: conventions don't have to be unified
across a project. They have to be *documented* and *bridged*.

WHAT IT TEACHES:
- The game owns the update order: propose → resolve → commit.
- Motion2D proposes movement via step_velocity(dt).
- The collision core resolves the proposal and reports what was hit.
- The game interprets the hits (grounded, ceiling, moving-platform).
- Coordinates cross library boundaries explicitly, via anchor_util.

CONTROLS:
- Left / Right arrows : Move
- Up arrow / Space    : Jump (hold for higher jump)
- R                   : Reset
- ESC                 : Quit
"""

import pygame
from pygame.math import Vector2
from motion2d import Motion2D, Facing
from time_util import Timer
from anchor_util import center_to_topleft, topleft_to_center
from collide2d import (
    resolve_swept,
    is_grounded,
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

# Jump forgiveness windows
COYOTE_TIME = 0.10
JUMP_BUFFER = 0.10
JUMP_CUT_MULT = 0.5

# Collision resolution precision.
# The swept resolver sub-steps in units of max_step. Smaller =
# tighter snapping but more sub-steps. 0.5 is a good demo balance.
MAX_STEP = 0.5

# Colors
COLOR_SKY = (30, 30, 45)
COLOR_GRID = (22, 22, 36)
COLOR_PLATFORM = (100, 100, 110)
COLOR_PLATFORM_EDGE = (140, 140, 150)
COLOR_MOVING = (255, 150, 50)
COLOR_MOVING_EDGE = (255, 200, 100)
COLOR_GOAL = (50, 255, 50)
COLOR_GOAL_EDGE = (200, 255, 200)
COLOR_PLAYER = (100, 180, 255)
COLOR_PLAYER_GROUND = (150, 220, 255)
COLOR_PLAYER_FACING = (255, 255, 255)


text_manager = TextManager(default_size=20)


# ============================================================================
# Player
# ============================================================================

class Player:
    """
    Rectangular player with platformer physics.

    [MOTION2D]  PlatformerMotion — gravity, horizontal intent.
    [MOTION2D]  Facing(2, horizontal) — left/right facing.
    [COLLISION] resolve_swept for movement resolution.
    [COLLISION] is_grounded / find_down for ground state.
    [ANCHOR]    center_to_topleft / topleft_to_center at boundaries.
    [TIME_UTIL] Timer for coyote time and jump buffer.
    """

    def __init__(self, x, y):
        # === MOTION2D USAGE ===
        self.motion = Motion2D.platformer(
            pos=(x, y),
            speed=300,
            acceleration=2000,
            deceleration=2500,
            gravity=1200,
            jump_strength=550,
            max_fall_speed=900,
            auto_face=True,
        )
        # === END MOTION2D USAGE ===

        self.size = PLAYER_SIZE
        self.grounded = False

        # === TIME_UTIL USAGE ===
        self.coyote = Timer(duration=COYOTE_TIME, autostart=False)
        self.jump_buffer = Timer(duration=JUMP_BUFFER, autostart=False)
        # === END TIME_UTIL USAGE ===

        self.is_jumping = False
        self.jump_key_was_held = False
        self.riding_platform = None

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    @property
    def rect(self) -> pygame.Rect:
        """Visual/collision AABB, centered on motion.position."""
        return pygame.Rect(
            self.motion.position.x - self.size // 2,
            self.motion.position.y - self.size // 2,
            self.size, self.size,
        )

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_input(self, keys):
        """Add movement intent and arm the jump buffer."""
        # === MOTION2D USAGE ===
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.motion.move_left()
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.motion.move_right()
        # === END MOTION2D USAGE ===

        jump_pressed = (
            keys[pygame.K_UP] or
            keys[pygame.K_SPACE] or
            keys[pygame.K_w]
        )

        # Arm the jump buffer only on a fresh press.
        # This makes "hold to auto-hop" impossible — the key must be
        # released and pressed again for each jump.
        if jump_pressed and not self.jump_key_was_held:
            self.jump_buffer.reset()

        self.jump_key_was_held = jump_pressed


    # ------------------------------------------------------------------
    # Jump
    # ------------------------------------------------------------------

    def try_jump(self):
        """Start a jump if coyote/buffer conditions are met."""
        can_jump = self.grounded or self.coyote.active
        wants_jump = self.jump_buffer.active

        if can_jump and wants_jump:
            # === MOTION2D USAGE ===
            self.motion.jump()
            # === END MOTION2D USAGE ===
            self.is_jumping = True
            self.grounded = False
            self.coyote.stop()
            self.jump_buffer.stop()

    def apply_variable_jump(self, keys):
        """Cut upward velocity when jump is released mid-ascent."""
        jump_held = (
            keys[pygame.K_UP] or
            keys[pygame.K_SPACE] or
            keys[pygame.K_w]
        )

        if self.is_jumping and not jump_held:
            # === MOTION2D USAGE ===
            # Directly modifying velocity is supported; velocity is a
            # public property. This is a game rule, not a hack.
            if self.motion.velocity.y < 0:
                self.motion.velocity.y *= JUMP_CUT_MULT
            # === END MOTION2D USAGE ===
            self.is_jumping = False

        if self.motion.velocity.y >= 0:
            self.is_jumping = False

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt, keys, platforms):
        # 1. Input
        self.handle_input(keys)

        # 2. Jump
        self.try_jump()
        self.apply_variable_jump(keys)

        # 3. Timers
        if self.grounded:
            self.coyote.reset()
        else:
            self.coyote.update(dt)
        self.jump_buffer.update(dt)

        # 4. === MOTION2D USAGE ===
        # Get the proposed movement delta. Velocity is updated inside
        # (intent acceleration, gravity, drag, limits). Position is
        # NOT moved — we'll move it ourselves after collision.
        delta = self.motion.step_velocity(dt)
        # === END MOTION2D USAGE ===

        # 5. Inherit the platform's delta (from LAST frame's riding state)
        # NOTE: On the FIRST frame the player lands on a moving platform,
        # riding_platform was None at the top of this frame, so the platform's
        # dx for this frame is NOT included in delta. This means the player
        # is 1 frame (a few px) "behind" the platform on the landing frame.
        # At demo platform speeds this is imperceptible. A "proper" fix
        # would require predicting the landing before resolve, which adds
        # complexity for negligible benefit.
        if self.riding_platform is not None:
            delta.x += self.riding_platform.dx

        # 6. === COLLISION (moving vs static) ===
        # Convert center → top-left because the collision core works in
        # top-left space. See the module docstring for why we keep two
        # conventions rather than unifying them.
        tlx, tly = center_to_topleft(self.motion.position.x,
                       self.motion.position.y, self.size, self.size)
        # === COLLIDE2D USAGE ===

        # Resolve the proposed movement.
        result = resolve_swept(
            tlx, tly,
            self.size, self.size,
            delta.x, delta.y,
            platforms,
            max_step=MAX_STEP,
        )
        # === END OF COLLIDE2D USAGE ===

        # Translate top-left → center and commit.
        cx, cy = topleft_to_center(
            result.x, result.y, self.size, self.size,
        )

        self.motion.position = Vector2(cx, cy)

        # Zero blocked velocity axes (standard platformer response).
        if result.blocked_x:
            self.motion.velocity.x = 0
        if result.blocked_y:
            self.motion.velocity.y = 0
        # === END COLLISION ===

        # 7. === GROUND QUERY ===
        # Query the ground state independently of movement.
        # This is more accurate than reading resolver hits, because
        # the resolver only reports what was hit DURING this frame's
        # motion — a standing-still player never reports a hit.
        tlx, tly = center_to_topleft(self.motion.position.x,
                       self.motion.position.y, self.size, self.size)
        self.grounded = is_grounded(
            tlx, tly,
            self.size, self.size,
            platforms,
            distance=1.0,
        )
        # === END GROUND QUERY ===

        # 8. Moving platform riding.
        # Update riding state FOR NEXT FRAME
        if self.grounded:
            self.riding_platform = find_down(
                tlx, tly,
                self.size, self.size,
                platforms,
                distance=1.0,
            )
        else:
            self.riding_platform = None

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen):
        color = COLOR_PLAYER_GROUND if self.grounded else COLOR_PLAYER

        rect = self.rect
        pygame.draw.rect(screen, color, rect, border_radius=4)
        pygame.draw.rect(screen, (255, 255, 255), rect, width=2, border_radius=4)

        # Facing indicator (small triangle on the facing side).
        fv = self.motion.heading.vector
        if fv.x > 0:
            tip_x = rect.right + 6
            base_x = rect.right + 1
        else:
            tip_x = rect.left - 6
            base_x = rect.left - 1

        cy = rect.centery
        pygame.draw.polygon(
            screen, COLOR_PLAYER_FACING,
            [(tip_x, cy), (base_x, cy - 5), (base_x, cy + 5)],
        )


    # ------------------------------------------------------------------
    # Respawn logic
    # ------------------------------------------------------------------

    def check_respawn(self):
        if self.motion.position.y > SCREEN_HEIGHT + 100:
            self.motion.position = Vector2(50, 500)
            self.motion.velocity = Vector2(0, 0)
            self.grounded = False
            self.riding_platform = None
            self.is_jumping = False
            self.jump_key_was_held = False


# ============================================================================
# Platforms
# ============================================================================

class StaticPlatform:
    """A platform that never moves."""
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.dx = 0

    def update(self, dt):
        pass # No op

    def draw(self, screen):
        pygame.draw.rect(screen, COLOR_PLATFORM, self.rect)
        pygame.draw.rect(screen, COLOR_PLATFORM_EDGE, self.rect, width=2)


class MovingPlatform:
    """
    A platform that moves horizontally using SimpleMotion.

    The thin height (5px) is intentional — see the class docstring.
    A thick platform lets the player stand beside it, which triggers
    a corner-collision artifact with the moving platform.

    [MOTION2D] SimpleMotion — not PlatformerMotion. The platform
    doesn't fall; it just moves. SimpleMotion is the right tool.
    """

    def __init__(self, x, y, w, h, speed, travel_dist):
        # h=5 is intentional: a thin platform reduces the chance of
        # the player standing *beside* it (rather than on top), which
        # triggers a corner-collision artifact where the player gets
        # "gripped" by the moving platform. With a tall platform, the
        # player can easily overlap the platform's side while standing
        # on adjacent ground, causing the resolver to lock both axes.
        # A thin platform means being "beside" it requires precise
        # alignment, which rarely happens in normal play.
        self.w = w
        self.h = h
        self.start_x = x
        self.travel_dist = travel_dist
        self.dx = 0.0
        self.dy = 0.0

        # === MOTION2D USAGE ===
        self.motion = Motion2D.simple(pos=(x, y), speed=speed)
        self.motion.go_right()
        # === END MOTION2D USAGE ===

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            self.motion.position.x,
            self.motion.position.y,
            self.w, self.h,
        )

    def update(self, dt):
        last_x = self.motion.position.x

        # === MOTION2D USAGE ===
        self.motion.update(dt)
        # === END MOTION2D USAGE ===

        # Clamp BEFORE reversing, so overshoot never enters dx
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
        pygame.display.set_caption("Demo 8: First Platformer")
        text_manager.bind(screen=self.screen)
        self.clock = pygame.time.Clock()
        self.running = True
        self.reset()

    def reset(self):
        self.player = Player(50, 500)

        self.moving_bridge = MovingPlatform(
            x=300, y=250, w=150, h=5,
            speed=100, travel_dist=250,
        )

        self.platforms = [
            # Left wall (off-screen, so only its right edge shows)
            StaticPlatform(-50, 0, 50, SCREEN_HEIGHT),
            # Right wall
            StaticPlatform(SCREEN_WIDTH, 0, 50, SCREEN_HEIGHT),
            # Ground start and end
            StaticPlatform(0, 550, 200, 50),
            StaticPlatform(600, 550, 200, 50),
            # Middle steps
            StaticPlatform(250, 450, 100, 20),
            StaticPlatform(50, 250, 100, 20),
            StaticPlatform(150, 350, 100, 20),
            StaticPlatform(150, 150, 225, 20),
            # Wall
            StaticPlatform(350, 300, 20, 150),
            StaticPlatform(265, 175, 20, 125),
            StaticPlatform(545, 300, 20, 250),
            StaticPlatform(450, 25, 20, 150),
            # Moving bridge
            self.moving_bridge,
        ]

        self.goal_rect = pygame.Rect(700, 500, 50, 50)
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

        # Platforms first, so their dx/dy is fresh for the player.
        for p in self.platforms:
            p.update(dt)

        # Player
        self.player.update(dt, keys, self.platforms)

        # Fall-off-world respawn
        self.player.check_respawn()

        # Win check
        if not self.won and self.player.rect.colliderect(self.goal_rect):
            self.won = True

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw_background(self):
        self.screen.fill(COLOR_SKY)
        for x in range(0, SCREEN_WIDTH, 40):
            pygame.draw.line(self.screen, COLOR_GRID, (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, 40):
            pygame.draw.line(self.screen, COLOR_GRID, (0, y), (SCREEN_WIDTH, y))

    def draw_hud(self):
        text_manager.write_centered(8, "DEMO 8: First Platformer", size=26)

        text_manager.write(
            10, 45,
            "Arrows: Move | Up / Space: Jump (hold for higher) | R: Reset | ESC: Quit",
            size=18, color=(180, 180, 180),
        )

        text_manager.write_centered(
            SCREEN_HEIGHT - 26,
            "MOTION2D: step_velocity + PlatformerMotion  |  COLLISION: resolve_swept  |  ANCHOR: center, topleft",
            size=16, color=(120, 180, 255),
        )

        # Debug (top-right)
        px = int(self.player.motion.position.x)
        py = int(self.player.motion.position.y)
        vx = int(self.player.motion.velocity.x)
        vy = int(self.player.motion.velocity.y)
        state = "GROUNDED" if self.player.grounded else "AIRBORNE"

        text_manager.write(
            SCREEN_WIDTH - 220, 10,
            f"State: {state}",
            size=16,
            color=(200, 255, 200) if self.player.grounded else (255, 200, 200),
        )
        text_manager.write(
            SCREEN_WIDTH - 220, 32,
            f"Pos: ({px}, {py})",
            size=14, color=(160, 160, 160),
        )
        text_manager.write(
            SCREEN_WIDTH - 220, 50,
            f"Vel: ({vx}, {vy})",
            size=14, color=(160, 160, 160),
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

    def draw(self):
        self.draw_background()

        for p in self.platforms:
            p.draw(self.screen)

        pygame.draw.rect(self.screen, COLOR_GOAL, self.goal_rect, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_GOAL_EDGE, self.goal_rect, width=3, border_radius=6)

        self.player.draw(self.screen)
        self.draw_hud()

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