"""
Demo 5a: Missile Command - Decoupled Architecture
===================================================
Shows how Layer 2 (Rotator) and Layer 1 (SimpleMotion)
can be used entirely independently of each other.

Controls:
- MOUSE MOVE : Aim Turret (gradual rotation)
- MOUSE CLICK: Fire Interceptor
- ESC : Quit
"""

import pygame
import random
from pygame.math import Vector2
from motion2d import Motion2D, Rotator

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


class Turret:
    def __init__(self, pos):
        self.pos = Vector2(pos)
        # === MOTION2D 1. Layer 2 ONLY. No physics body, just aiming logic. ===
        self.rotator = Rotator(angle=270, rotate_speed=120)
        # === END MOTION2D USAGE ===

        self.locked = False

    def aim(self, target_pos, dt):
        # Calculate the vector toward the mouse and feed it to the rotator
        target_vector = Vector2(target_pos) - self.pos
        if target_vector.length() > 5:
            # === MOTION2D ===
            self.locked = self.rotator.aim(target_vector, dt)
            # === END MOTION2D USAGE ===
        else:
            self.locked = False

    def draw(self, screen):
        # Multiply the pure vector by 40 pixels to draw the gun barrel
        barrel_end = self.pos + (self.rotator.vector * 40)
        if self.locked:
            pygame.draw.circle(screen, (0, 255, 0), (int(self.pos.x), int(self.pos.y)), 20)
        else:
            pygame.draw.circle(screen, (255, 0, 0), (int(self.pos.x), int(self.pos.y)), 20)
        pygame.draw.line(screen, (200, 200, 200), self.pos, barrel_end, 6)


class EnemyMissile:
    def __init__(self, start_pos, target_pos):
        # Calculate direction to target and tell the missile to go
        direction = Vector2(target_pos) - Vector2(start_pos)

        # === MOTION2D USAGE ===
        self.motion = Motion2D.simple(pos=start_pos, speed=50)
        self.motion.go(direction)
        # === END MOTION2D USAGE ===

        self.active = True

    def update(self, dt):
        # === MOTION2D USAGE ===
        self.motion.update(dt)
        # === END MOTION2D USAGE ===

        # Destroy if it hits the ground
        if self.motion.position.y >= SCREEN_HEIGHT - 30:
            self.active = False

    def draw(self, screen):
        pygame.draw.circle(screen, (255, 50, 50), self.motion.position, 4)


class Interceptor:
    def __init__(self, start_pos, angle, target_pos):
        # === MOTION2D USAGE ===
        self.motion = Motion2D.simple(pos=start_pos, speed=400)
        # Fire strictly along the turret's CURRENT visual vector, not the mouse position!
        self.motion.go_angle(angle)
        # === END MOTION2D USAGE ===

        # Measure how far it needs to travel before detonating
        self.target_distance = start_pos.distance_to(target_pos)
        self.distance_traveled = 0.0
        self.active = True

    def update(self, dt):
        # === MOTION2D USAGE ===
        self.motion.update(dt)
        # === END MOTION2D USAGE ===

        # Track distance using speed * dt
        self.distance_traveled += self.motion.speed * dt
        if self.distance_traveled >= self.target_distance:
            self.active = False

        if not (-50 < self.motion.position.x < SCREEN_WIDTH + 50) or not (-50 < self.motion.position.y < SCREEN_HEIGHT - 25):
            self.active = False

    def draw(self, screen):
        pygame.draw.circle(screen, (50, 255, 255), self.motion.position, 3)


class MissileCommandDemo:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Demo 5a: Missile Command Clone (Decoupled Layers)")
        self.clock = pygame.time.Clock()
        self.running = True

        self.turret = Turret((SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30))
        self.enemies = []
        self.interceptors = []
        self.explosions = [] # Stores (Vector2_pos, current_radius)
        self.enemy_spawn_timer = 0.0

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = pygame.mouse.get_pos()
                # === MOTION2D USAGE ===
                interceptor = Interceptor(start_pos=self.turret.pos, angle=self.turret.rotator.angle, target_pos=mouse_pos)
                # === END MOTION2D USAGE ===
                self.interceptors.append(interceptor)

    def update(self, dt):
        mouse_pos = pygame.mouse.get_pos()
        self.turret.aim(mouse_pos, dt)

        # Spawn enemies
        self.enemy_spawn_timer -= dt
        if self.enemy_spawn_timer <= 0:
            start_x = random.randint(50, SCREEN_WIDTH - 50)
            target_x = random.randint(50, SCREEN_WIDTH - 50)
            self.enemies.append(EnemyMissile((start_x, 0), (target_x, SCREEN_HEIGHT)))
            self.enemy_spawn_timer = 1.0

        # Update entities
        for e in self.enemies: e.update(dt)

        for i in self.interceptors:
            i.update(dt)
            if not i.active:
                self.explosions.append([Vector2(i.motion.position), 5.0]) # Start radius 5

        # Update Explosions (grow up to radius 40, then disappear)
        for exp in self.explosions:
            exp[1] += 60 * dt
        self.explosions = [exp for exp in self.explosions if exp[1] < 40]

        # Clean up dead missiles
        self.enemies = [e for e in self.enemies if e.active]
        self.interceptors = [i for i in self.interceptors if i.active]

        # Check Collisions (Explosion vs Enemy)
        for exp in self.explosions:
            exp_pos, exp_radius = exp[0], exp[1]
            for enemy in self.enemies:
                if enemy.motion.position.distance_to(exp_pos) < exp_radius:
                    enemy.active = False

    def draw(self):
        self.screen.fill((20, 20, 30))
        pygame.draw.rect(self.screen, (50, 150, 50), (0, SCREEN_HEIGHT - 30, SCREEN_WIDTH, 30))

        for e in self.enemies: e.draw(self.screen)
        for i in self.interceptors: i.draw(self.screen)

        # Draw explosions
        for exp in self.explosions:
            pygame.draw.circle(self.screen, (255, 200, 50), (int(exp[0].x), int(exp[0].y)), int(exp[1]))

        self.turret.draw(self.screen)

        # Text
        y = 10

        # Title
        text_manager.write_center(y, "DEMO 5a: Missile Command - Rotator Without Motion", size=24, screen=self.screen)
        y += 35
        text_manager.write_center(y, "Rotator works independently - no motion required!", size=18, screen=self.screen, color=(100, 255, 100))
        y += 18
        text_manager.write_center(y, "Turret locked at mouse: green, rotating: red", size=18, screen=self.screen, color=(100, 255, 100))


        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()

if __name__ == "__main__":
    demo = MissileCommandDemo()
    demo.run()