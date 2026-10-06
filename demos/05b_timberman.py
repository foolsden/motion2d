"""
Demo 5b: Timberman - Facing as a State Tracker
===================================================
Shows how Layer 2 (Facing) can be used independently
of a physics body to manage game state, positioning,
and particle directions.

Controls:
- LEFT ARROW / A : Chop Left side
- RIGHT ARROW / D : Chop Right side
- R : Restart (if you hit a branch)
- ESC : Quit
"""

import pygame
import random
from pygame.math import Vector2
from motion2d import Motion2D, Facing

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
TREE_X = SCREEN_WIDTH // 2


MAX_TIMER_START = 2.0      # seconds at easiest difficulty
MAX_TIMER_MIN   = 0.5      # seconds at hardest difficulty
BAR_WIDTH_START = 300      # px when max_timer == MAX_TIMER_START
BAR_WIDTH_MIN   = 150      # px when max_timer == MAX_TIMER_MIN
BAR_HEIGHT      = 20
BAR_COLOR_BG    = (40, 40, 40)
BAR_COLOR_FILL  = (80, 200, 120)
BAR_COLOR_EDGE  = (220, 220, 220)

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


class Woodchip:
    def __init__(self, start_pos, player_facing_vector):
        # === MOTION2D USAGE ===
        self.motion = Motion2D.simple(pos=start_pos, speed=random.randint(300, 600))
        # === END OF MOTION2D USAGE ===

        flight_dir = Vector2(-player_facing_vector.x, random.uniform(-1.5, -0.2)).normalize()
        self.motion.go(flight_dir)
        self.active = True

    def update(self, dt):
        # === MOTION2D USAGE ===
        self.motion.apply_gravity(dt, force=1200)
        self.motion.update(dt)
        # === END OF MOTION2D USAGE ===

        if self.motion.position.y > SCREEN_HEIGHT:
            self.active = False

    def draw(self, screen):
        pos = (int(self.motion.position.x), int(self.motion.position.y))
        pygame.draw.rect(screen, (200, 150, 100), (pos[0], pos[1], 8, 8))


class Lumberjack:
    def __init__(self):
        # === MOTION2D USAGE ===
        self.facing = Facing(directions=2, axis='horizontal')
        self.facing.right()
        # === END OF MOTION2D USAGE ===
        self.y_pos = SCREEN_HEIGHT - 100
        self.color = (50, 100, 255)
        self.dead = False

    @property
    def vector(self):
        return self.facing.vector

    def chop(self, direction):
        if self.dead:
            return
        if direction == -1:
            self.facing.left()
        elif direction == 1:
            self.facing.right()

    def draw(self, screen):
        # Position is calculated dynamically using the vector. No if-statements!
        # If vector is (1,0), offset is +60. If (-1,0), offset is -60.
        x_pos = TREE_X + (self.vector.x * 60)

        rect = pygame.Rect(0, 0, 40, 60)
        rect.center = (int(x_pos), self.y_pos)

        color = (255, 50, 50) if self.dead else self.color
        pygame.draw.rect(screen, color, rect)

        # Draw the axe pointing toward the tree
        axe_end = Vector2(rect.center) + (self.vector * -30)
        pygame.draw.line(screen, (200, 200, 200), rect.center, axe_end, 5)


class TimbermanDemo:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Demo 5b: Timberman (Facing State)")
        self.clock = pygame.time.Clock()
        self.running = True
        self.reset_game()

    def reset_game(self):
        self.player = Lumberjack()
        self.woodchips = []
        self.branches = [None, *[Facing() for _ in range(5)]]
        for branch in self.branches:
            if branch is not None:
                random.choice([branch.left, branch.right])()

        self.max_timer = MAX_TIMER_START
        self.current_timer = self.max_timer

    def handle_chop(self, heading):
        if self.player.dead:
            return

        self.player.chop(heading)
        self.max_timer *= .995
        self.current_timer = self.max_timer

        for _ in range(5):
            self.woodchips.append(Woodchip((TREE_X, self.player.y_pos), self.player.vector))

        self.branches.pop(0)
        self.branches.append(Facing())
        random.choice([self.branches[-1].left, self.branches[-1].right])()

        if (self.branches[0].is_left() and self.player.facing.is_left()) or (self.branches[0].is_right() and self.player.facing.is_right()):
            self.player.dead = True

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r and self.player.dead:
                    self.reset_game()
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self.handle_chop(-1)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.handle_chop(1)

    def draw_bar(self, pos):
        t = (self.max_timer - MAX_TIMER_MIN) / (MAX_TIMER_START - MAX_TIMER_MIN)
        bg_width = BAR_WIDTH_MIN + (t * (BAR_WIDTH_START - BAR_WIDTH_MIN))

        fill_width = (bg_width * (self.current_timer / self.max_timer)) - 4

        bg_rect = pygame.Rect(0, 0, bg_width, BAR_HEIGHT)
        bg_rect.center = pos
        pygame.draw.rect(self.screen, BAR_COLOR_BG, bg_rect, border_radius=6)

        if fill_width > 0:
            fill_rect = pygame.Rect(0, 0, fill_width, BAR_HEIGHT - 4)
            fill_rect.center = pos
            pygame.draw.rect(self.screen, BAR_COLOR_FILL, fill_rect, border_radius=4)

        pygame.draw.rect(self.screen, BAR_COLOR_EDGE, bg_rect, width=2, border_radius=6)

    def update(self, dt):
        for chip in self.woodchips:
            chip.update(dt)
        self.woodchips = [c for c in self.woodchips if c.active]

        # Decrease timer
        if not self.player.dead:
            self.current_timer -= dt
            if self.current_timer <= 0:
                self.player.dead = True

    def draw(self):
        self.screen.fill((135, 206, 235)) # Sky blue

        # Draw Tree Trunk
        pygame.draw.rect(self.screen, (101, 67, 33), (TREE_X - 20, 100, 40, SCREEN_HEIGHT))

        # Draw Branches
        branch_y = SCREEN_HEIGHT - 100
        for branch_side in self.branches:
            if branch_side is not None:
                bx = TREE_X + (branch_side.vector.x * 60)
                rect = pygame.Rect(0, 0, 80, 20)
                rect.center = (bx, branch_y)
                pygame.draw.rect(self.screen, (34, 139, 34), rect)
            branch_y -= 80 # Move up the tree for the next branch

        self.player.draw(self.screen)
        for chip in self.woodchips:
            chip.draw(self.screen)

        if self.player.dead:
            text_manager.write_center(SCREEN_HEIGHT//2, "GAME OVER - Press R to Restart", 36, self.screen)

        text_manager.write(10, 10, 'Press left or right to avoid the falling branch as quickly as possible before the timer is 0', 20, self.screen, (0, 0, 0))
        text_manager.write(10, SCREEN_HEIGHT - 40, 'Facing as state also as position demo', 36, self.screen, (0, 0, 0))

        self.draw_bar((TREE_X, 50))

        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()

if __name__ == "__main__":
    demo = TimbermanDemo()
    demo.run()