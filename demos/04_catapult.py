"""
Demo 4: Catapult - Projectile Physics
=================================================
Shows SimpleMotion with:
- Click and drag to aim
- Launch with variable power
- Gravity for realistic arcs
- Bouncing off walls

CONTROLS:
- Click and drag to aim
- Release to launch
- Space to reset
- ESC to quit

FEATURES SHOWN:
- SimpleMotion for projectile physics
- apply_gravity() for realistic arcs
- border bouncing (reflection)
- new instance of simple and advance dt manually to show projection
"""

import pygame
import random
from pygame.math import Vector2
from motion2d import Motion2D

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

class TextManager:
    """For easier printing text to screen"""
    def __init__(self):
        pygame.init()
        self.fonts = {}

    def write(self, x, y, text, size, screen, color=(255, 255, 255)):
        if size not in self.fonts:
            self.fonts[size] = pygame.font.Font(None, size)
        text_surface = self.fonts[size].render(text, True, color)
        screen.blit(text_surface, (x, y))

    def write_center(self, y, text, size, screen, color=(255, 255, 255)):
        if size not in self.fonts:
            self.fonts[size] = pygame.font.Font(None, size)
        text_surface = self.fonts[size].render(text, True, color)
        text_rect = text_surface.get_rect(centerx=screen.get_width() // 2, y=y)
        screen.blit(text_surface, text_rect)
text_manager = TextManager()

class Target:
    """Target to destroy with the projectile."""
    def __init__(self, pos, size=30):
        self.pos = Vector2(pos)
        self.size = size
        self.color = (255, 50, 50)

    def check_collision(self, ball_pos):
        """Check if ball hit this target."""
        distance = self.pos.distance_to(ball_pos)
        return distance < self.size + 20

    def draw(self, screen):
        pos = (int(self.pos.x), int(self.pos.y))

        pygame.draw.circle(screen, self.color, pos, self.size)
        pygame.draw.circle(screen, (255, 255, 255), pos, self.size, 2)

class CatapultBall:
    """The projectile ball using SimpleMotion."""
    def __init__(self, pos):
        self.start_pos = Vector2(pos)
        self.size = 20
        self.color = (255, 200, 50)
        self.trail = []
        self.max_trail = 30
        self.reset()

    def reset(self):
        """Reset ball to catapult position."""
        # === MOTION2D USAGE ===
        self.motion = Motion2D.simple(pos=self.start_pos, speed=0)
        self.motion.stop()
        # === END MOTION2D USAGE ===
        self.trail.clear()
        self.launched = False
        self.in_flight = False

    def launch(self, power, angle):
        """Launch the ball with given power and angle."""
        # === MOTION2D USAGE ===
        self.motion.speed = power
        self.motion.go_angle(angle)
        # === END MOTION2D USAGE ===
        self.launched = True
        self.in_flight = True

    def update(self, dt):
        """Update physics and check for bounces."""
        if not self.in_flight:
            return

        # === MOTION2D USAGE ===
        # Apply gravity
        self.motion.apply_gravity(dt, force=600, max_fall_speed=600)
        self.motion.update(dt)
        # === END MOTION2D USAGE ===

        # Update trail
        self.trail.append(Vector2(self.motion.position))
        if len(self.trail) > self.max_trail:
            self.trail.pop(0)

        # Bounce off walls (with energy loss)
        # Using go_reverse() and damp() to reverse direction and dampening the velocity
        pos = self.motion.position
        vel = self.motion.velocity

        # Left wall
        if pos.x < self.size:
            self.motion.position.x = self.size
            # === MOTION2D USAGE ===
            self.motion.go_reverse(x=True)
            self.motion.damp(x=0.7)
            # === END MOTION2D USAGE ===

        # Right wall
        elif pos.x > SCREEN_WIDTH - self.size:
            self.motion.position.x = SCREEN_WIDTH - self.size
            # === MOTION2D USAGE ===
            self.motion.go_reverse(x=True)
            self.motion.damp(x=0.7)
            # === END MOTION2D USAGE ===

        # Ceiling
        if pos.y < self.size:
            self.motion.position.y = self.size
            # === MOTION2D USAGE ===
            self.motion.go_reverse(y=True)
            self.motion.damp(y=0.7)
            # === END MOTION2D USAGE ===

        # Ground (with friction)
        if pos.y > SCREEN_HEIGHT - self.size - 30:
            self.motion.position.y = SCREEN_HEIGHT - self.size - 30
            # === MOTION2D USAGE ===
            self.motion.go_reverse(y=True)
            self.motion.damp(x=0.9, y=0.5)
            # === END MOTION2D USAGE ===

            # Stop if barely moving
            if abs(vel.y) < 50:
                self.motion.velocity.y = 0
                if abs(vel.x) < 50:
                    self.motion.velocity.x = 0
                    self.in_flight = False

    def draw(self, screen):
        pos = self.motion.position

        # Draw trail with fade
        for i, trail_pos in enumerate(self.trail):
            alpha = int(255 * (i / len(self.trail)) * 0.3)
            if alpha > 0:
                size = max(2, 8 * (i / len(self.trail)))
                surf = pygame.Surface((size * 2 + 2, size * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(surf, (255, 200, 50, alpha), (size + 1, size + 1), size)
                screen.blit(surf, (trail_pos.x - size - 1, trail_pos.y - size - 1))

        # Draw ball
        pygame.draw.circle(screen, self.color, (int(pos.x), int(pos.y)), self.size)
        pygame.draw.circle(screen, (255, 255, 255), (int(pos.x), int(pos.y)), self.size, 2)

class CatapultDemo:
    """Main demo application."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Demo 4: Catapult Demo")
        self.clock = pygame.time.Clock()
        self.running = True

        # Create catapult position (fixed)
        self.catapult_pos = Vector2(150, SCREEN_HEIGHT - 150)
        self.ball = CatapultBall(self.catapult_pos)

        # Create targets
        self.targets = []
        self.spawn_targets()

        # Aiming
        self.aiming = False
        self.aim_start = Vector2(0, 0)
        self.power = 0
        self.angle = 0
        self.power_multiplier = 3

        self.reset_timer = 0

    def spawn_targets(self):
        """Spawn random targets."""
        self.targets = []
        num_targets = random.randint(6, 10)

        for _ in range(num_targets):
            # Random position (avoid catapult area)
            attempts = 0
            while attempts < 50:
                x = random.randint(200, SCREEN_WIDTH - 50)
                y = random.randint(50, SCREEN_HEIGHT - 100)
                # Avoid catapult area
                if Vector2(x, y).distance_to(self.catapult_pos) > 150:
                    break
                attempts += 1

            size = random.randint(20, 45)
            self.targets.append(Target((x, y), size))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    self.reset_level()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Start aiming if ball is ready
                if not self.ball.launched and not self.ball.in_flight:
                    mouse_pos = Vector2(pygame.mouse.get_pos())
                    self.aiming = True
                    self.aim_start = mouse_pos
                    self.power = 0
                    self.angle = 0

            elif event.type == pygame.MOUSEMOTION:
                if self.aiming:
                    drag_vector = self.aim_start - Vector2(pygame.mouse.get_pos())
                    self.power = drag_vector.length() * self.power_multiplier
                    # [0] is the length, [1] is the angle in degrees
                    self.angle = drag_vector.as_polar()[1]

            elif event.type == pygame.MOUSEBUTTONUP:
                if self.aiming and not self.ball.launched:
                    # Launch the ball!
                    self.aiming = False
                    self.launch_ball()

    def launch_ball(self):
        """Calculate launch parameters and fire!"""
        if self.power > 30:  # Minimum power to launch
            self.reset_timer = 0
            self.ball.launch(self.power, self.angle)

    def reset_level(self):
        """Reset the level."""
        self.reset_timer = 0
        self.ball.reset()
        self.spawn_targets()
        self.aiming = False

    def update(self, dt):
        self.ball.update(dt)

        # Check collisions ball with target
        if self.ball.in_flight:
            new_target =  self.targets[:]
            for target in self.targets:
                if target.check_collision(self.ball.motion.position):
                    new_target.remove(target)
            self.targets = new_target

        # Auto-reset when ball stops
        if not self.ball.in_flight and self.ball.launched:
            # Check if all targets are destroyed
            if not self.targets:
                self.reset_level()
            else:
                # pause then put the ball back
                if self.reset_timer > 0.5:
                    self.ball.reset()
                    self.reset_timer = 0
                else:
                    self.reset_timer += dt

    def draw_catapult(self):
        """Draw the catapult structure."""
        pos = self.catapult_pos

        # Base
        pygame.draw.rect(self.screen, (100, 80, 60), (pos.x - 20, pos.y + 10, 40, 15))

        # Angle indicator (invisible if it's not aiming)
        if self.aiming:
            if self.power / self.power_multiplier  > 10:
                arm_end = pos + Vector2(40, 0).rotate(self.angle)
                pygame.draw.line(self.screen, (150, 120, 80), pos, arm_end, 6)

        # Draw power level ring
        pygame.draw.circle(self.screen, (50, 50, 50, 128), (int(pos.x), int(pos.y)), 60, 1)

    def draw_aiming_line(self):
        """Draw the aiming line and power indicator."""
        if not self.aiming:
            return

        # Color based on power (green -> yellow -> red)
        if self.power < 200:
            color = (100, 255, 100)
        elif self.power < 600:
            color = (255, 255, 100)
        else:
            color = (255, 100, 100)

        pygame.draw.line(self.screen, color, self.aim_start, Vector2(pygame.mouse.get_pos()), 3)

        # Draw power indicator
        if self.power > 30:
            # Power ring around base
            radius = min(100, 20 + self.power / 15) # Visual limitation only
            pygame.draw.circle(self.screen, color, self.ball.motion.position, radius, 2)

            # Trajectory preview (dots)
            self.draw_trajectory_preview()

    def draw_trajectory_preview(self):
        """Draw a dotted trajectory preview. No collision detection!"""
        # Check if the original drag is shorter than 20 (power is drag * power_multiplier)
        if self.power / self.power_multiplier < 20:
            return

        # === MOTION2D USAGE ===
        # Just create another simple motion for calculating the preview
        preview = Motion2D.simple(pos= self.ball.motion.position, speed=self.power)
        preview.go_angle(self.angle)
        # === END MOTION2D USAGE ===

        dt = 0.02  # Small time step
        gravity = 600
        step = 30

        for i in range(step):
            # === MOTION2D USAGE ===
            # Simulate the next position by creating an independent timeline
            preview.apply_gravity(dt, gravity, max_fall_speed=600)
            preview.update(dt)
            # === END MOTION2D USAGE ===

            pos = preview.position

            # Check bounds
            if pos.x < 0 or pos.x > SCREEN_WIDTH or pos.y > SCREEN_HEIGHT:
                break

            # Skip the first few dot to draw
            if i >5:
                # Draw dot with decreasing size
                alpha = int(255 * (1 - i / 30))
                size = max(2, 4 * (1 - i / 30))
                pygame.draw.circle(self.screen, (255, 255, 255, alpha), (int(pos.x), int(pos.y)), int(size))

    def draw_info(self):
        y = 10
        # Title
        text_manager.write_center(y, "DEMO 4: Catapult", size=30, screen=self.screen)
        y += 25

        # Controls
        text_manager.write_center(y, "Click and drag from ball to aim | press space to reset | press esc to quit", size=18, screen=self.screen)
        y += 25

        # Motion2D features
        text_manager.write_center(y, "MOTION2D: apply_gravity() + velocity control = projectile physics", size=22, screen=self.screen, color=(0, 0, 0))
        y += 25
        text_manager.write_center(y, "MOTION2D: go_reverse() + damp() if the ball collide with border", size=22, screen=self.screen, color=(0, 0, 0))
        y += 25
        text_manager.write_center(y, "MOTION2D: Create another simplemotion for previewing trajectory", size=22, screen=self.screen, color=(0, 0, 0))

    def draw_background(self):
        """Draw the background scene."""
        # Sky gradient
        for y in range(SCREEN_HEIGHT):
            color = (100 - y // 6, 180 - y // 8, 255 - y // 10)
            pygame.draw.line(self.screen, color, (0, y), (SCREEN_WIDTH, y))

        # Ground with grass
        pygame.draw.rect(self.screen, (100, 200, 80), (0, SCREEN_HEIGHT - 30, SCREEN_WIDTH, 30))
        pygame.draw.rect(self.screen, (80, 180, 60), (0, SCREEN_HEIGHT - 30, SCREEN_WIDTH, 5))

    def draw(self):
        # Background
        self.draw_background()

        # Draw targets
        for target in self.targets:
            target.draw(self.screen)

        # Draw catapult
        self.draw_catapult()

        # Draw ball
        self.ball.draw(self.screen)

        # Draw aiming line (on top)
        self.draw_aiming_line()

        # Draw info
        self.draw_info()

        pygame.display.flip()

    def run(self):
        while self.running:
            # Note that motion2d needs dt!
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()


if __name__ == "__main__":
    demo = CatapultDemo()
    demo.run()