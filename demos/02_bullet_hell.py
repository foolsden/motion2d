"""
Demo 2: Bullet Hell - go_angle() Demonstration
===============================================
Shows SimpleMotion with go_angle() for directional movement.

Features:
- Player follows mouse using go()
- Auto-spawning bullet patterns
- Click to cycle through different patterns
- Shows how go_angle() creates precise angles

Patterns:
1. Radial Burst - Classic circular spread
2. Spiral - Continuous rotating pattern
3. Flower - Alternating petal pattern
4. Wave - Sinusoidal wave pattern
5. Star - Star-shaped burst

Controls:
- Mouse to move player
- Click to cycle spawn patterns
- ESC to quit

Important part:
- The game decides what the object should do; Motion2D handles how the object moves.
- Angle convention:
    0°   = right
    90°  = down
    180° = left
    270° = up
- The basic syntax is:
    bullet = Motion2D.simple(pos=pos, speed=speed)
    bullet.go_angle(angle)
    bullet.update(dt)
"""

import pygame
import math
from pygame.math import Vector2
from motion2d import Motion2D

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

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



class Player:
    """Simple player that follows the mouse."""

    def __init__(self):
        # === MOTION2D USAGE ===
        # SimpleMotion with instant movement
        self.motion = Motion2D.simple(pos=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), speed=300)
        # === END MOTION2D USAGE ===

    def update(self, dt, mouse_pos):
        # === MOTION2D USAGE ===
        direction = Vector2(mouse_pos) - self.motion.position

        if direction.length() > 10:
            self.motion.go(direction)
        else:
            self.motion.stop()
        self.motion.update(dt)
        # === END MOTION2D USAGE ===

    def draw(self, screen):
        pygame.draw.circle(screen, (50, 255, 50), (int(self.motion.position.x), int(self.motion.position.y)), 15)


class Bullet:
    """Bullet using SimpleMotion with go_angle()."""

    def __init__(self, pos, angle, speed=300, size=4):
        # === MOTION2D USAGE ===
        self.motion = Motion2D.simple(pos=pos, speed=speed)
        # Set direction using go_angle() - clean and simple!
        self.motion.go_angle(angle)
        # === END MOTION2D USAGE ===

        self.size = size
        self.alive = True

    def update(self, dt):
        # === MOTION2D USAGE ===
        self.motion.update(dt)
        # === END MOTION2D USAGE ===

        if self.motion.position.x < -50 or self.motion.position.x > SCREEN_WIDTH + 50 \
           or self.motion.position.y < -50 or self.motion.position.y > SCREEN_HEIGHT + 50:
            self.alive = False

    def draw(self, screen):
        pygame.draw.circle(screen, (255, 255, 100),
                           (int(self.motion.position.x), int(self.motion.position.y)), self.size)

class PatternManager:
    """Manages different bullet patterns."""
    def __init__(self):
        self.pattern_index = 0
        self.pattern_names = [
            "Radial Burst",
            "Spiral",
            "Flower",
            "Wave",
            "Star"
        ]
        self.spiral_angle = 0
        self.wave_offset = 0
        self.bullet_id = 0

    def get_current_pattern_name(self):
        return self.pattern_names[self.pattern_index]

    def next_pattern(self):
        self.pattern_index = (self.pattern_index + 1) % len(self.pattern_names)
        self.spiral_angle = 0
        self.wave_offset = 0

    def spawn_bullets(self, center, bullets, count=18):
        """Spawn bullets using the current pattern."""
        if self.pattern_index == 0:
            self._radial_burst(center, bullets, count)
        elif self.pattern_index == 1:
            self._spiral(center, bullets, count)
        elif self.pattern_index == 2:
            self._flower(center, bullets, count)
        elif self.pattern_index == 3:
            self._wave(center, bullets, count)
        elif self.pattern_index == 4:
            self._star(center, bullets, count)

    def _radial_burst(self, center, bullets, count):
        """Pattern 1: Classic circular burst."""
        # === MOTION2D USAGE ===
        for i in range(count):
            angle = (i / count) * 360
            bullet = Bullet(center, angle, speed=200)
            bullets.append(bullet)
        # === END MOTION2D USAGE ===

    def _spiral(self, center, bullets, count):
        """Pattern 2: Continuous spiral pattern."""
        # === MOTION2D USAGE ===
        # Each bullet is offset by a growing angle
        for i in range(count):
            angle = (i / count) * 360 + self.spiral_angle
            # Spiral effect: varying speed
            speed = 150 + (i / count) * 100
            bullet = Bullet(center, angle, speed=speed, size=3)
            bullets.append(bullet)
        # === END MOTION2D USAGE ===

        # Rotate spiral for next spawn
        self.spiral_angle += 15  # 15 degrees per spawn

    def _flower(self, center, bullets, count):
        """Pattern 3: Flower petal pattern."""
        # === MOTION2D USAGE ===
        # Alternating angles with different radii
        for i in range(count):
            # Main angle
            base_angle = (i / count) * 360
            # Add some variation to create petals
            petal_offset = math.sin(math.radians(base_angle * 3)) * 30

            # Two layers: inner and outer petals
            for layer in range(2):
                angle = base_angle + petal_offset + (layer * 15)
                speed = 150 + layer * 80
                size = 3 + layer
                bullet = Bullet(center, angle, speed=speed, size=size)
                bullets.append(bullet)
        # === END MOTION2D USAGE ===

    def _wave(self, center, bullets, count):
        """Pattern 4: Sinusoidal wave pattern."""
        # === MOTION2D USAGE ===
        for i in range(count):
            # Distribute bullets along a line
            t = i / count
            angle = self.wave_offset  # Horizontal wave
            # Vary the angle based on sine wave
            wave_angle = math.sin(math.radians(t * 360 * 3)) * 45
            final_angle = angle + wave_angle

            # Speed varies with wave
            speed = 150 + math.sin(math.radians(t * 360 * 2)) * 50

            bullet = Bullet(center, final_angle, speed=speed, size=4)
            bullets.append(bullet)
        # === END MOTION2D USAGE ===

        self.wave_offset += 10  # Move wave for next spawn

    def _star(self, center, bullets, count):
        """Pattern 5: Star-shaped burst."""
        # === MOTION2D USAGE ===
        for i in range(count):
            # Distribute bullets around the circle
            base_angle = (i / count) * 360

            # Star effect: alternating fast/slow speeds
            if i % 2 == 0:
                speed = 250
                size = 4
            else:
                speed = 100
                size = 2

            # Add slight angle offset for star points
            angle = base_angle + (i % 3) * 5

            bullet = Bullet(center, angle, speed=speed, size=size)
            bullets.append(bullet)
        # === END MOTION2D USAGE ===


class BulletHellDemo:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Demo 2: Bullet Hell - go_angle()")
        self.clock = pygame.time.Clock()
        self.running = True

        self.player = Player()
        self.bullets = []
        self.pattern_manager = PatternManager()
        self.pattern_timer = 0
        self.spawn_delay = 0.3  # Spawn every 0.3 seconds

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Click to change pattern
                self.pattern_manager.next_pattern()

    def update(self, dt):
        mouse_pos = pygame.mouse.get_pos()
        self.player.update(dt, mouse_pos)

        # Spawn bullets
        self.pattern_timer += dt
        if self.pattern_timer >= self.spawn_delay:
            count = 18
            if self.pattern_manager.pattern_index == 2:  # Flower needs more
                count = 12
            elif self.pattern_manager.pattern_index == 3:  # Wave needs less
                count = 15
            self.pattern_manager.spawn_bullets(
                self.player.motion.position,
                self.bullets,
                count
            )
            self.pattern_timer = 0

        # Update bullets
        for bullet in self.bullets[:]:
            bullet.update(dt)

        # Clean up dead ones instantly
        self.bullets = [b for b in self.bullets if b.alive]

    def draw_info(self):
        y = 10

        text_manager.write_center(y, "DEMO 2: Bullet Hell - go_angle()",size=22,screen=self.screen)
        y += 30

        text_manager.write_center(y, f"Current Pattern: {self.pattern_manager.get_current_pattern_name()}", size=22, screen=self.screen)
        y += 30


        text_manager.write(10, SCREEN_HEIGHT - 70, "SimpleMotion: Direct velocity-based motion.", size=18, screen=self.screen)
        text_manager.write(10, SCREEN_HEIGHT - 50, "Great for bullets, particles, projectiles, and other objects that don't need character-style movement behavior", size=18, screen=self.screen)


        text_manager.write(10, SCREEN_HEIGHT - 30, f"Bullets: {len(self.bullets)}", size=18, screen=self.screen)

        # Controls
        text_manager.write_center(SCREEN_HEIGHT - 30, "Move: Mouse  |  Click to change pattern  |  ESC to quit", size=22, screen=self.screen)

    def draw(self):
        self.screen.fill((10, 10, 30))

        for x in range(0, SCREEN_WIDTH, 50):
            pygame.draw.line(self.screen, (20, 20, 40), (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, 50):
            pygame.draw.line(self.screen, (20, 20, 40), (0, y), (SCREEN_WIDTH, y))

        # Draw bullets
        for bullet in self.bullets:
            bullet.draw(self.screen)

        # Draw player
        self.player.draw(self.screen)

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
    demo = BulletHellDemo()
    demo.run()