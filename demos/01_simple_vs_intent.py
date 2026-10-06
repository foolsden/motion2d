"""
Demo 1: Simple vs Intent - Understanding Motion Types
=======================================================
Shows the difference between:
- LEFT: SimpleMotion (instant velocity, no acceleration)
- RIGHT: TopDownMotion (smooth acceleration/deceleration)

Both respond to the same keys:
- Arrow keys or WASD to move
- ESC to quit

Watch how the left ball moves instantly while the right ball accelerates!
"""

import pygame
from motion2d import Motion2D

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 400
FPS = 60



class TextManager:
    # For easier printing text to screen
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
# For easier displaying text, intentionally made as global
text_manager = TextManager()



class Ball:
    """Base ball with shared properties."""

    def __init__(self, pos, color, label):
        self.color = color
        self.label = label
        self.size = 20
        self.speed = 300

    def draw(self, screen):
        """Draw the ball with label."""
        pygame.draw.circle(screen, self.color, (int(self.motion.position.x), int(self.motion.position.y)), self.size)
        pygame.draw.circle(screen, (255, 255, 255), (int(self.motion.position.x), int(self.motion.position.y)), self.size, 2)
        text_manager.write(self.motion.position.x - self.size, self.motion.position.y - self.size - 20, self.label, 18, screen)


class SimpleBall(Ball):
    """
    LEFT: Uses SimpleMotion - instant velocity changes.
    When you press a key, velocity changes IMMEDIATELY.
    No acceleration, no deceleration.
    """

    def __init__(self, pos):
        super().__init__(pos, (255, 50, 50), "SIMPLE")

        # === MOTION2D USAGE ===
        # SimpleMotion - instant velocity
        self.motion = Motion2D.simple(
            pos=pos,
            speed=self.speed,
            max_speed=self.speed
        )
        # === END MOTION2D USAGE ===

    def handle_input(self, keys):
        """SimpleMotion: Instant velocity changes."""
        pressed = False # For checking if key pressed
        # === MOTION2D USAGE ===
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.motion.go_left()
            pressed = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.motion.go_right()
            pressed = True
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.motion.go_up()
            pressed = True
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.motion.go_down()
            pressed = True

        # To make the ball stop if no keypressed, uncomment here
        # if not pressed:
        #     self.motion.stop()
        # To make the ball stop if no keypressed, uncomment here


        # === END MOTION2D USAGE ===

    def update(self, dt):

        # === MOTION2D USAGE ===
        self.motion.update(dt)
        # === END MOTION2D USAGE ===

        # Sync position and velocity
        self.position = self.motion.position
        self.velocity = self.motion.velocity

        self.wrap_position()
        self.motion.position = self.position

    def wrap_position(self):
        """Wrap around screen edges."""
        if self.position.x > SCREEN_WIDTH // 2 - self.size:
            self.position.x = 0
        elif self.position.x < 0:
            self.position.x = SCREEN_WIDTH // 2 - self.size

        if self.position.y > SCREEN_HEIGHT - self.size:
            self.position.y = self.size
        elif self.position.y < self.size:
            self.position.y = SCREEN_HEIGHT - self.size


class IntentBall(Ball):
    """
    RIGHT: Uses TopDownMotion - smooth acceleration/deceleration.
    Press a key and the ball smoothly accelerates.
    Release and it smoothly decelerates to a stop.
    """

    def __init__(self, pos):
        super().__init__(pos, (50, 50, 255), "INTENT")

        # === MOTION2D USAGE ===
        # TopDownMotion - smooth acceleration
        self.motion = Motion2D.top_down(
            pos=pos,
            speed=self.speed,
            acceleration=500,  # How fast to reach max speed
            deceleration=600,  # How fast to slow down
            auto_aim=False
        )
        # === END MOTION2D USAGE ===

    def handle_input(self, keys):
        """TopDownMotion: Smooth acceleration with intent."""
        # === MOTION2D USAGE ===
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.motion.move_left()
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.motion.move_right()
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.motion.move_up()
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.motion.move_down()
        # === END MOTION2D USAGE ===

    def update(self, dt):
        # === MOTION2D USAGE ===
        self.motion.update(dt)
        # === END MOTION2D USAGE ===

        # Sync position and velocity
        self.position = self.motion.position
        self.velocity = self.motion.velocity

        self.wrap_position()
        self.motion.position = self.position

    def wrap_position(self):
        """Wrap around screen edges."""
        if self.position.x > SCREEN_WIDTH - self.size:
            self.position.x = SCREEN_WIDTH // 2 + self.size
        elif self.position.x < SCREEN_WIDTH // 2 + self.size:
            self.position.x = SCREEN_WIDTH - self.size

        if self.position.y > SCREEN_HEIGHT - self.size:
            self.position.y = self.size
        elif self.position.y < self.size:
            self.position.y = SCREEN_HEIGHT - self.size

class SplitScreenDemo:
    """
    Split screen demo showing Simple vs Intent.
    """
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Demo 1: Simple vs Intent - Motion2D")
        self.clock = pygame.time.Clock()
        self.running = True

        self.left_ball = SimpleBall((SCREEN_WIDTH // 4, SCREEN_HEIGHT // 2))
        self.right_ball = IntentBall((3 * SCREEN_WIDTH // 4, SCREEN_HEIGHT // 2))

        self.divider_x = SCREEN_WIDTH // 2

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

    def update(self, dt):
        keys = pygame.key.get_pressed()

        # Both balls respond to same input
        self.left_ball.handle_input(keys)
        self.right_ball.handle_input(keys)

        self.left_ball.update(dt)
        self.right_ball.update(dt)

    def draw_info(self):
        """Draw educational information."""
        y = 10
        x = 10

        text_manager.write(x, y, "Demo 1: Simple vs Intent", 28, self.screen)
        y += 35

        left_info = [
            "LEFT: SimpleMotion",
            "No acceleration / instant velocity changes",
            "Move indefinitely unless stop() is issued, check the source code",
            "Arrow keys affect velocity directly",
            "Helpers (go_(direction)) is replacing velocity, for diagonal use go()"
        ]
        for text in left_info:
            text_manager.write(x, y, text, 16, self.screen)
            y += 22
        y = 10 + 35

        right_info = [
            "RIGHT: TopDownMotion (intent-based)",
            "Smooth acceleration / deceleration",
            "Arrow keys affect acceleration, acceleration affect velocity",
            "Helpers (move_(direction)) is addition, so diagonal is a default"
        ]
        for text in right_info:
            text_manager.write(SCREEN_WIDTH // 2 + x, y, text, 16, self.screen)
            y += 22

        text_manager.write_center(SCREEN_HEIGHT - 20, 'Controls: Arrow Keys / WASD  |  ESC to quit', 26, self.screen)

        left_speed = self.left_ball.velocity.length()
        left_bar_width = min(150, left_speed / 300 * 150)
        pygame.draw.rect(self.screen, (100, 100, 100), (10, SCREEN_HEIGHT - 60, 150, 8))
        pygame.draw.rect(self.screen, (255, 100, 100), (10, SCREEN_HEIGHT - 60, left_bar_width, 8))
        text_manager.write(10, SCREEN_HEIGHT - 80, f"Speed: {int(left_speed)}", 18, self.screen)

        right_speed = self.right_ball.velocity.length()
        right_bar_width = min(150, right_speed / 300 * 150)
        pygame.draw.rect(self.screen, (100, 100, 100), (SCREEN_WIDTH // 2 + 10, SCREEN_HEIGHT - 60, 150, 8))
        pygame.draw.rect(self.screen, (100, 100, 255), (SCREEN_WIDTH // 2 + 10, SCREEN_HEIGHT - 60, right_bar_width, 8))
        text_manager.write(SCREEN_WIDTH // 2 + 10, SCREEN_HEIGHT - 80, f"Speed: {int(right_speed)}", 18, self.screen)

    def draw(self):
        for y in range(SCREEN_HEIGHT):
            color = (20, 20, 40 + y // 4)
            pygame.draw.line(self.screen, color, (0, y), (SCREEN_WIDTH, y))

        pygame.draw.line(self.screen, (100, 100, 150),
                        (self.divider_x, 0), (self.divider_x, SCREEN_HEIGHT), 2)

        self.left_ball.draw(self.screen)
        self.right_ball.draw(self.screen)

        self.draw_info()
        pygame.display.flip()

    def run(self):
        # Note that motion2d needs dt!
        dt = self.clock.tick(FPS) / 1000.0
        while self.running:
            self.handle_events()
            self.update(dt)
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()

if __name__ == "__main__":
    demo = SplitScreenDemo()
    demo.run()