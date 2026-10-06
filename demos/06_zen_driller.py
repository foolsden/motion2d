"""
Demo 6: Zen Driller - Matrix-Breaking "Side-View" TopDown
===================================================
Shows how TopDownMotion handles freeform inertia and
dynamic max_speed, disguised as a side-view digging game.

Controls:
- ARROW KEYS / WASD : Steer the drill
- ESC : Quit
"""

import pygame
from motion2d import Motion2D, Rotator

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

class TextManager:
    """For easier printing text to screen"""
    def __init__(self):
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


class DrillPod:
    def __init__(self, pos):
        # === MOTION2D USAGE ===
        # We use a Rotator with TopDownMotion to get smooth auto-aiming inertia.
        rotator = Rotator(rotate_speed=200)
        # Omnidirectional TopDown controller
        self.motion = Motion2D.top_down(
            pos=pos,
            speed=500,
            acceleration=1500,
            deceleration=100,
            heading=rotator,
            auto_aim=False,  # Disable auto-aim for tank controls!
            grip=10.0,
        )
        # === END OF MOTION2D USAGE ===
        self.radius = 20

    def draw(self, screen):
        pos = (int(self.motion.position.x), int(self.motion.position.y))

        # Draw the main pod body
        pygame.draw.circle(screen, (200, 200, 200), pos, self.radius)

        # Draw the drill bit pointing in the Rotator's current visual vector
        drill_tip = self.motion.position + (self.motion.heading.vector * 35)
        pygame.draw.line(screen, (255, 150, 50), pos, (int(drill_tip.x), int(drill_tip.y)), 8)


class ZenDrillerDemo:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Demo 6: Zen Driller (Dynamic Terrain & Inertia)")
        self.clock = pygame.time.Clock()
        self.running = True

        self.drill = DrillPod((SCREEN_WIDTH // 2, 100))

        # [TERRAIN] Create a solid dirt surface with alpha transparency
        self.dirt_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.dirt_surface.fill((101, 67, 33, 255)) # Solid brown dirt

        # Carve out a starting cavern at the top
        pygame.draw.circle(self.dirt_surface, (0, 0, 0, 0), (SCREEN_WIDTH // 2, 100), 80)

        # Create the eraser brush for carving pixels
        self.brush_size = 25
        self.brush = pygame.Surface((self.brush_size * 2, self.brush_size * 2), pygame.SRCALPHA)
        self.brush.fill((255, 255, 255, 255))
        pygame.draw.circle(self.brush, (255, 255, 255, 0), (self.brush_size, self.brush_size), self.brush_size)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                self.running = False

    def update(self, dt):
        keys = pygame.key.get_pressed()

        # [TANK CONTROLS] Left and Right steer the Rotator manually
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            # === MOTION2D USAGE ===
            self.drill.motion.turn_left(dt)
            # === END OF MOTION2D USAGE ===
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            # === MOTION2D USAGE ===
            self.drill.motion.turn_right(dt)
            # === END OF MOTION2D USAGE ===

        # [TANK CONTROLS] Up and Down apply gas along the heading vector
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            # === MOTION2D USAGE ===
            self.drill.motion.move_forward()
            # === END OF MOTION2D USAGE ===
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            # === MOTION2D USAGE ===
            self.drill.motion.move_backward()
            # === END OF MOTION2D USAGE ===

        # Dynamic Movement Sensor
        vel = self.drill.motion.velocity
        if vel.length_squared() > 1.0:
            # If moving, put the sensor 35 pixels in the direction of actual travel
            sensor_dir = vel.normalize()
        else:
            # If stopped, default to looking at the nose
            sensor_dir = self.drill.motion.heading.vector

        sensor_pos = self.drill.motion.position + (sensor_dir * 35)

        px = int(max(0, min(SCREEN_WIDTH - 1, sensor_pos.x)))
        py = int(max(0, min(SCREEN_HEIGHT - 1, sensor_pos.y)))

        # Read the alpha value of the pixel at the drill TIP
        pixel_alpha = self.dirt_surface.get_at((px, py)).a

        if pixel_alpha > 10:
            # Drilling through dirt: lower the max speed ceiling
            # Accessing directly through the layer 1 (kinematics body)
            self.drill.motion.body.max_speed = 100
        else:
            # Flying through empty space: raise the max speed ceiling
            self.drill.motion.body.max_speed = 300

        # === MOTION2D USAGE ===
        self.drill.motion.update(dt)
        # === END OF MOTION2D USAGE ===

        # [TERRAIN] Carve away the dirt at the new position
        bx = self.drill.motion.position.x - self.brush_size
        by = self.drill.motion.position.y - self.brush_size
        self.dirt_surface.blit(self.brush, (bx, by), special_flags=pygame.BLEND_RGBA_MIN)

    def draw(self):
        # Draw sky background
        self.screen.fill((135, 206, 235))

        # Draw destructible dirt
        self.screen.blit(self.dirt_surface, (0, 0))

        self.drill.draw(self.screen)

        # UI
        state = "DRILLING" if self.drill.motion.body.max_speed <= 100 else "FLYING"
        text_manager.write(10, 10, f"ZEN DRILLER - State: {state} | Speed Limit: {self.drill.motion.body.max_speed}", 32, self.screen, (255, 255, 255))

        text_manager.write(10, SCREEN_HEIGHT - 68, 'TopDown in action within a side view demos. Arrow or WASD to move, esc to exit', 22, self.screen)
        text_manager.write(10, SCREEN_HEIGHT - 45, 'TopDown Motion is using intent -> acceleration -> velocity -> position', 22, self.screen)
        text_manager.write(10, SCREEN_HEIGHT - 22, 'You can access directly layer 1 (body) for advance control of variable', 22, self.screen)

        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()

if __name__ == "__main__":
    demo = ZenDrillerDemo()
    demo.run()