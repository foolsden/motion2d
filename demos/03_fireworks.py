"""
Demo 3: Interactive Fireworks Physics Lab
======================================
Shows SimpleMotion with interactive physics controls:

FEATURES:
- Gravity: Press G to toggle (shows effect on falling)
- Damping: Press D to toggle (shows air resistance)
- Wind: Left/Right arrows to control (affects horizontal motion)
- Auto-fire: 5 fireworks launch randomly
- Click to launch: Launch at mouse position

CONTROLS:
- G: Toggle Gravity
- D: Toggle Damping
- Left/Right: Control Wind Strength
- Click: Launch firework at mouse position
- ESC: Quit

EDUCATIONAL VALUE:
- See how gravity affects particles
- See how damping slows horizontal movement
- See how wind pushes particles sideways
- Compare physics on/off in real-time
"""

import pygame
import random
import math
from pygame.math import Vector2
from motion2d import Motion2D

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Firework colors
COLORS = [
    (255, 50, 50),    # Red
    (50, 255, 50),    # Green
    (50, 50, 255),    # Blue
    (255, 255, 50),   # Yellow
    (255, 50, 255),   # Magenta
    (50, 255, 255),   # Cyan
    (255, 150, 50),   # Orange
    (255, 50, 150),   # Pink
]


# For easier printing text to screen, please ignore this part from the demo
class TextManager:
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
# For easier printing text to screen, please ignore this part from the demo

class Spark:
    """
    A spark particle with configurable physics.

    DEMONSTRATES:
    - SimpleMotion for physics
    - Conditional gravity (toggleable)
    - Conditional damping (toggleable)
    - External wind force
    """

    def __init__(self, pos, angle, speed, color, lifespan, size=3):
        # === MOTION2D USAGE ===
        # Create a SimpleMotion controller for this spark
        # This handles position, velocity, and physics
        self.motion = Motion2D.simple(
            pos=pos,
            speed=speed,
            max_speed=600 # Speed cap
        )
        self.motion.go_angle(angle)
        # === END MOTION2D USAGE ===

        # Damping factors (with random variation)
        self.damp_x = random.uniform(0.95, 0.99)
        self.damp_y = random.uniform(0.98, 1.0)

        self.color = color
        self.lifespan = lifespan
        self.max_lifespan = lifespan
        self.alive = True
        self.size = size

    def update(self, dt, gravity_enabled, damping_enabled, wind_strength):
        if not self.alive:
            return

        # === MOTION2D USAGE ===
        # Apply wind (external force)
        if abs(wind_strength) > 0.1:
            self.motion.apply_force((wind_strength * 50, 0), dt)

        # Apply damping (toggleable)
        if damping_enabled:
            self.motion.damp(x=self.damp_x, y=self.damp_y)

        # Apply gravity (toggleable)
        if gravity_enabled:
            self.motion.apply_gravity(dt, force=800, max_fall_speed=500)

        # Update physics (integrates velocity into position)
        self.motion.update(dt)
        # === END MOTION2D USAGE ===

        # Reduce lifespan
        self.lifespan -= dt
        if self.lifespan <= 0:
            self.alive = False

    def draw(self, screen):
        """Draw the spark with fade effect."""
        if not self.alive:
            return

        pos = self.motion.position
        # Fade out as lifespan decreases
        alpha = int((self.lifespan / self.max_lifespan) * 255)

        # Draw main spark with glow
        glow_size = self.size * 3
        surf = pygame.Surface((glow_size * 2 + 2, glow_size * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(
            surf,
            (*self.color, alpha // 4),
            (glow_size + 1, glow_size + 1),
            glow_size
        )
        screen.blit(surf, (pos.x - glow_size - 1, pos.y - glow_size - 1))

        # Draw main spark
        pygame.draw.circle(screen, self.color, (int(pos.x), int(pos.y)), self.size)


class Firework:
    """
    A complete firework with multiple sparks.

    DEMONSTRATES:
    - Creating many SimpleMotion objects
    - go_angle() for circular bursts
    - Random velocity generation
    """

    def __init__(self, pos, color=None, spark_count=60):
        self.sparks = []
        self.alive = True

        if color is None:
            color = random.choice(COLORS)

        # Create sparks in a circular burst
        for i in range(spark_count):
            angle = (i / spark_count) * 360 + random.uniform(-5, 5)
            speed = random.uniform(150, 400)

            spark = Spark(
                pos=pos,
                angle=angle,
                speed=speed,
                color=color,
                lifespan=random.uniform(1.0, 2.5),
                size=random.uniform(2, 4)
            )
            self.sparks.append(spark)

    def update(self, dt, gravity_enabled, damping_enabled, wind_strength):
        self.alive = False
        for spark in self.sparks:
            spark.update(dt, gravity_enabled, damping_enabled, wind_strength)
            if spark.alive:
                self.alive = True

    def draw(self, screen):
        for spark in self.sparks:
            spark.draw(screen)


class Rocket:
    """
    A rising rocket that explodes into a firework.
    """

    def __init__(self, start_pos, target_pos, color=None):
        self.target_pos = Vector2(target_pos)
        self.alive = True
        self.color = color if color else (255, 200, 100)

        # === MOTION2D USAGE ===
        # Create motion for the rocket
        self.motion = Motion2D.simple(pos=start_pos, speed=0)

        # Calculate direction to target
        direction = Vector2(target_pos) - Vector2(start_pos)
        if direction.length() > 0:
            direction = direction.normalize()

        self.motion.velocity = direction * 400
        # === END MOTION2D USAGE ===

    def update(self, dt):
        """Move rocket and check if reached target."""
        if not self.alive:
            return

        # === MOTION2D USAGE ===
        # Just update - velocity stays constant
        self.motion.update(dt)
        # === END MOTION2D USAGE ===

        # Check if reached target
        if self.motion.position.y <= self.target_pos.y:
            self.alive = False

    def draw(self, screen):
        """Draw the rocket."""
        if not self.alive:
            return

        # Draw rocket body
        pos = self.motion.position
        pygame.draw.circle(screen, (255, 200, 100), (int(pos.x), int(pos.y)), 4)
        pygame.draw.circle(screen, (255, 255, 255), (int(pos.x), int(pos.y)), 2)


class FireworksDemo:
    """
    Main demo application.
    """

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Demo 3: Interactive Fireworks Demo")
        self.clock = pygame.time.Clock()
        self.running = True

        # Physics toggles
        self.gravity_enabled = True
        self.damping_enabled = True
        self.wind_strength = 0.0  # Positive = right, Negative = left

        # Game objects
        self.fireworks = []
        self.rockets = []

        # Auto-fire system
        self.auto_fire_timer = 0
        self.auto_fire_interval = 2.0  # Seconds between auto-fires
        self.rocket_count = 0

        # Background
        self.background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.background.fill((10, 10, 30))

        # Stars
        self.stars = []
        for _ in range(80):
            self.stars.append((
                random.randint(0, SCREEN_WIDTH),
                random.randint(0, SCREEN_HEIGHT),
                random.uniform(0.5, 2),
                random.uniform(0.3, 1.0)
            ))

        # Wind particles (visual indicator)
        self.wind_particles = []

    def launch_firework(self, target_pos, color=None):
        """Launch a rocket toward target position."""
        start_pos = (target_pos[0] + random.randint(-50, 50), SCREEN_HEIGHT + 10)
        rocket = Rocket(start_pos, target_pos, color)
        self.rockets.append(rocket)
        self.rocket_count += 1

    def launch_random_firework(self):
        """Launch a firework at a random position with random color."""
        x = random.randint(100, SCREEN_WIDTH - 100)
        y = random.randint(100, SCREEN_HEIGHT - 200)
        color = random.choice(COLORS)
        self.launch_firework((x, y), color)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_g:
                    # Toggle gravity
                    self.gravity_enabled = not self.gravity_enabled
                elif event.key == pygame.K_d:
                    # Toggle damping
                    self.damping_enabled = not self.damping_enabled
                elif event.key == pygame.K_LEFT:
                    # Wind left (negative)
                    self.wind_strength = max(-5.0, self.wind_strength - 0.5)
                elif event.key == pygame.K_RIGHT:
                    # Wind right (positive)
                    self.wind_strength = min(5.0, self.wind_strength + 0.5)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Launch firework at mouse position
                color = random.choice(COLORS)
                self.launch_firework(pygame.mouse.get_pos(), color)

    def update_wind_particles(self, dt):
        """Create particles to visualize wind."""
        if abs(self.wind_strength) > 0.1:
            # Add wind particles
            if random.random() < abs(self.wind_strength) * 0.05:
                x = 0 if self.wind_strength > 0 else SCREEN_WIDTH
                y = random.randint(0, SCREEN_HEIGHT)
                self.wind_particles.append({
                    'pos': Vector2(x, y),
                    'life': 1.0,
                    'speed': abs(self.wind_strength) * 50
                })

        # Update wind particles
        for particle in self.wind_particles[:]:
            particle['pos'].x += particle['speed'] * dt * (1 if self.wind_strength > 0 else -1)
            particle['life'] -= dt * 0.5
            if particle['life'] <= 0 or particle['pos'].x < -50 or particle['pos'].x > SCREEN_WIDTH + 50:
                self.wind_particles.remove(particle)

    def draw_wind_particles(self):
        """Draw wind visualization particles."""
        for particle in self.wind_particles:
            alpha = int(particle['life'] * 150)
            size = int(3 * particle['life'])
            if size > 0:
                surf = pygame.Surface((size * 2 + 2, size * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(
                    surf,
                    (200, 200, 255, alpha),
                    (size + 1, size + 1),
                    size
                )
                self.screen.blit(surf, (particle['pos'].x - size - 1, particle['pos'].y - size - 1))


    def update(self, dt):
        # Update rockets
        for rocket in self.rockets[:]:
            rocket.update(dt)
            if not rocket.alive:
                # Create firework at rocket's target position
                firework = Firework(rocket.target_pos)
                self.fireworks.append(firework)
                self.rockets.remove(rocket)

        # Update fireworks with physics toggles
        for firework in self.fireworks[:]:
            firework.update(
                dt,
                self.gravity_enabled,
                self.damping_enabled,
                self.wind_strength
            )
            if not firework.alive:
                self.fireworks.remove(firework)

        # Auto-fire system
        self.auto_fire_timer += dt
        if self.auto_fire_timer >= self.auto_fire_interval:
            self.launch_random_firework()
            self.auto_fire_timer = 0
            # Randomize interval for variety
            self.auto_fire_interval = random.uniform(1.0, 3.0)

        # Update wind particles
        self.update_wind_particles(dt)

    def draw_stars(self):
        """Draw twinkling stars."""
        time = pygame.time.get_ticks() / 1000
        for x, y, size, speed in self.stars:
            brightness = 128 + int(127 * math.sin(time * speed))
            pygame.draw.circle(
                self.screen,
                (brightness, brightness, brightness),
                (int(x), int(y)),
                int(size)
            )

    def draw_info(self):
        y = 10

        # Title
        text_manager.write_center(
            y,
            "DEMO 3: Interactive Fireworks Physics Lab",
            size=24,
            screen=self.screen
        )
        y += 35

        # Physics status with colors
        status_color = (100, 255, 100) if self.gravity_enabled else (255, 100, 100)
        text_manager.write_center(
            y,
            f"Gravity: {'ON' if self.gravity_enabled else 'OFF'} (Press G to toggle)",
            size=20,
            screen=self.screen,
            color=status_color
        )
        y += 28

        status_color = (100, 255, 100) if self.damping_enabled else (255, 100, 100)
        text_manager.write_center(
            y,
            f"Damping: {'ON' if self.damping_enabled else 'OFF'} (Press D to toggle)",
            size=20,
            screen=self.screen,
            color=status_color
        )
        y += 28

        # Wind indicator with direction
        wind_direction = "→" if self.wind_strength > 0.1 else "←" if self.wind_strength < -0.1 else "○"
        wind_color = (100, 200, 255) if abs(self.wind_strength) > 0.1 else (150, 150, 150)
        text_manager.write_center(
            y,
            f"Wind: {wind_direction} {abs(self.wind_strength):.1f} (Left/Right arrows)",
            size=20,
            screen=self.screen,
            color=wind_color
        )
        y += 28

        # Controls
        text_manager.write_center(
            SCREEN_HEIGHT - 60,
            "G: Toggle Gravity | D: Toggle Damping | ← →: Wind | Click: Launch | ESC: Quit",
            size=18,
            screen=self.screen,
            color=(200, 200, 200)
        )

        # Stats
        text_manager.write(
            10,
            SCREEN_HEIGHT - 30,
            f"Fireworks: {len(self.fireworks)} | Rockets: {len(self.rockets)} | Sparks: {sum(len(f.sparks) for f in self.fireworks)}",
            size=16,
            screen=self.screen,
            color=(150, 150, 150)
        )

        # Educational hints
        hints = []
        if not self.gravity_enabled:
            hints.append("Gravity OFF - Sparks float in space!")
        elif self.gravity_enabled and not self.damping_enabled:
            hints.append("Damping OFF - Sparks keep horizontal speed!")
        elif abs(self.wind_strength) > 1.0:
            hints.append(f"Wind blowing {'right' if self.wind_strength > 0 else 'left'}!")

        if hints:
            text_manager.write_center(
                SCREEN_HEIGHT - 90,
                hints[0],
                size=18,
                screen=self.screen,
                color=(255, 255, 100)
            )

    def draw(self):
        # Clear
        self.screen.blit(self.background, (0, 0))

        # Draw stars
        self.draw_stars()

        # Draw wind particles
        self.draw_wind_particles()

        # Draw fireworks
        for firework in self.fireworks:
            firework.draw(self.screen)

        # Draw rockets
        for rocket in self.rockets:
            rocket.draw(self.screen)

        # Draw info overlay
        self.draw_info()

        # Wind indicator line at bottom
        if abs(self.wind_strength) > 0.1:
            wind_x = SCREEN_WIDTH // 2 + int(self.wind_strength * 30)
            pygame.draw.line(
                self.screen,
                (100, 200, 255),
                (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 5),
                (wind_x, SCREEN_HEIGHT - 5),
                3
            )
            # Arrow tip
            if self.wind_strength > 0:
                pygame.draw.polygon(
                    self.screen,
                    (100, 200, 255),
                    [(wind_x, SCREEN_HEIGHT - 5), (wind_x - 8, SCREEN_HEIGHT - 10), (wind_x - 8, SCREEN_HEIGHT)]
                )
            else:
                pygame.draw.polygon(
                    self.screen,
                    (100, 200, 255),
                    [(wind_x, SCREEN_HEIGHT - 5), (wind_x + 8, SCREEN_HEIGHT - 10), (wind_x + 8, SCREEN_HEIGHT)]
                )

        pygame.display.flip()

    def run(self):
        while self.running:
            # Note that motion2d needs dt!
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()

        pygame.quit()


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    demo = FireworksDemo()
    demo.run()