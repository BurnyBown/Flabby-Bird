import pygame
import sys
import random

# Initialize Pygame
pygame.init()

# Constants
SCALE_FACTOR = 3
SCREEN_WIDTH = 400 * SCALE_FACTOR
SCREEN_HEIGHT = min(600 * SCALE_FACTOR, 800)
FPS = 60
PIPE_WIDTH = 60 * SCALE_FACTOR
PIPE_GAP = 150 * SCALE_FACTOR
PIPE_SPEED = 3 * SCALE_FACTOR
PIPE_FREQUENCY = 1500 # milliseconds

# States
STATE_TITLE = "TITLE"
STATE_PLAYING = "PLAYING"
STATE_GAME_OVER = "GAME_OVER"
STATE_DEBUG = "DEBUG"

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
EXIT_RED = (165, 48, 48)

# Set up display with DOUBLEBUF to prevent screen tearing
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.DOUBLEBUF)
pygame.display.set_caption("Flabby Bartholomew")
clock = pygame.time.Clock()

# Assets
try:
    bart_flap = pygame.image.load('Bart flap.png').convert_alpha()
    bart_no_flap = pygame.image.load('Bart no flap.png').convert_alpha()

    # Load and scale base pipe image
    base_pipe = pygame.image.load('perfect pipe up.png').convert_alpha()
    # Scale width to PIPE_WIDTH, maintain aspect ratio for initial scaling
    pipe_scaled_width = PIPE_WIDTH
    pipe_scaled_height = int(base_pipe.get_height() * (PIPE_WIDTH / base_pipe.get_width()))
    base_pipe = pygame.transform.scale(base_pipe, (pipe_scaled_width, pipe_scaled_height)).convert_alpha()

    # Slice pipe: Cap (top 20%) and Body (a 1px slice from the body)
    cap_height = int(pipe_scaled_height * 0.20)
    pipe_cap = base_pipe.subsurface((0, 0, pipe_scaled_width, cap_height))
    # Using row at 90% height to avoid potential transparent pixels at the very bottom
    body_row_y = int(pipe_scaled_height * 0.90)
    pipe_body = base_pipe.subsurface((0, body_row_y, pipe_scaled_width, 1))

    # Flipped versions for top pipes
    pipe_cap_flipped = pygame.transform.flip(pipe_cap, False, True).convert_alpha()
    pipe_body_flipped = pygame.transform.flip(pipe_body, False, True).convert_alpha()

    # Pre-render max height pipes for performance (The Stutter Fix)
    # This avoids scaling/stretching surfaces during the game loop.
    max_top_pipe_surface = pygame.Surface((PIPE_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA).convert_alpha()
    max_bottom_pipe_surface = pygame.Surface((PIPE_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA).convert_alpha()

    # Build max_top_pipe (Cap at the bottom)
    body_height = SCREEN_HEIGHT - cap_height
    if body_height > 0:
        stretched_body_top = pygame.transform.scale(pipe_body_flipped, (PIPE_WIDTH, body_height)).convert_alpha()
        max_top_pipe_surface.blit(stretched_body_top, (0, 0))
    max_top_pipe_surface.blit(pipe_cap_flipped, (0, body_height))

    # Build max_bottom_pipe (Cap at the top)
    max_bottom_pipe_surface.blit(pipe_cap, (0, 0))
    if body_height > 0:
        stretched_body_bottom = pygame.transform.scale(pipe_body, (PIPE_WIDTH, body_height)).convert_alpha()
        max_bottom_pipe_surface.blit(stretched_body_bottom, (0, cap_height))

except pygame.error as e:
    print(f"Error loading assets: {e}")
    sys.exit()

# Fonts
def get_font(size, bold=False, scale=True):
    if scale:
        return pygame.font.SysFont('Arial', int(size * SCALE_FACTOR), bold=bold)
    else:
        return pygame.font.SysFont('Arial', int(size), bold=bold)

class Bird:
    def __init__(self, x, y, size, gravity, jump_strength):
        self.x = float(x)
        self.y = float(y) # Centered Y position
        self.vel = 0.0
        self.width = float(size)
        self.height = float(size)
        self.gravity = float(gravity)
        self.jump_strength = jump_strength
        self.flap_timer = 0
        self.using_flap_sprite = False

        self.update_base_sprites()
        # The Rattle Fix: Anchor centered on Y position
        self.rect = self.base_no_flap.get_rect(center=(int(self.x), int(self.y)))

    def update_base_sprites(self):
        self.base_flap = pygame.transform.scale(bart_flap, (int(self.width), int(self.height))).convert_alpha()
        self.base_no_flap = pygame.transform.scale(bart_no_flap, (int(self.width), int(self.height))).convert_alpha()
        # Pre-calculate masks for pixel-perfect hitboxes
        self.mask_flap = pygame.mask.from_surface(self.base_flap)
        self.mask_no_flap = pygame.mask.from_surface(self.base_no_flap)

    @property
    def mask(self):
        return self.mask_flap if self.using_flap_sprite else self.mask_no_flap

    def jump(self):
        self.vel = self.jump_strength
        self.flap_timer = 0.15

    def grow(self, speed_increase_percent):
        self.width *= 1.05
        self.height *= 1.05
        self.gravity *= 1.05
        self.update_base_sprites()

    def update(self, dt):
        self.vel += self.gravity
        self.y += self.vel

        if self.flap_timer > 0:
            self.flap_timer -= dt
            self.using_flap_sprite = True
        else:
            self.using_flap_sprite = False

        # No rotation logic (The Rattle Fix): The bird remains horizontal
        self.rect.center = (int(self.x), int(self.y))

    def draw(self, surface):
        image = self.base_flap if self.using_flap_sprite else self.base_no_flap
        # Blit Accuracy: ensuring coordinates are passed as (int(x), int(y))
        surface.blit(image, (int(self.rect.x), int(self.rect.y)))

class Pipe:
    def __init__(self, x, y, width, height, is_top, max_pipe_surface):
        self.x_float = float(x)
        self.y = y
        self.width = width
        self.height = height
        self.is_top = is_top
        self.passed = False

        # Use pre-rendered subsurface (The Stutter Fix)
        if is_top:
            # Sliced from bottom of max_top_pipe to have the cap at the bottom
            self.image = max_pipe_surface.subsurface((0, SCREEN_HEIGHT - height, width, height))
        else:
            # Sliced from top of max_bottom_pipe to have the cap at the top
            self.image = max_pipe_surface.subsurface((0, 0, width, height))

        self.rect = self.image.get_rect(topleft=(int(self.x_float), self.y))
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, speed):
        self.x_float -= speed
        # Integer-Locked Movement: ensuring the pipe never moves by a fraction of a pixel
        self.rect.x = int(self.x_float)

    def draw(self, surface):
        # Blit Accuracy: ensuring coordinates are passed as (int(x), int(y))
        surface.blit(self.image, (int(self.rect.x), int(self.rect.y)))

font_main_size = 36
font_small_size = 24
font_title_size = 48
ui_font_size = 30

font_main = get_font(font_main_size, bold=True)
font_small = get_font(font_small_size)
font_title = get_font(font_title_size, bold=True)
font_ui = get_font(ui_font_size, scale=False)

def draw_text(text, color, x, y, font=font_main, center=False, max_width=None):
    if max_width and font.size(text)[0] > max_width:
        temp_font_size = int(font_title_size * SCALE_FACTOR)
        while temp_font_size > 10 and pygame.font.SysFont('Arial', temp_font_size, bold=True).size(text)[0] > max_width:
            temp_font_size -= 2
        font = pygame.font.SysFont('Arial', temp_font_size, bold=True)

    img = font.render(text, True, color)
    if center:
        rect = img.get_rect(center=(int(x), int(y)))
        screen.blit(img, rect)
    else:
        screen.blit(img, (int(x), int(y)))

class Button:
    def __init__(self, x, y, width, height, text, color=GREEN, text_color=BLACK, font=font_ui):
        self.rect = pygame.Rect(int(x - width // 2), int(y - height // 2), width, height)
        self.text = text
        self.color = color
        self.text_color = text_color
        self.font = font

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect, border_radius=5)
        text_img = self.font.render(self.text, True, self.text_color)
        text_rect = text_img.get_rect(center=self.rect.center)
        surface.blit(text_img, text_rect)

    def is_clicked(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                return True
        return False

class TextInput:
    def __init__(self, x, y, width, height, label, initial_value, font=font_ui):
        self.rect = pygame.Rect(int(x), int(y), width, height)
        self.label = label
        self.text = str(initial_value)
        self.font = font
        self.active = False
        self.color_active = WHITE
        self.color_inactive = (150, 150, 150)
        self.color = self.color_inactive

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = True
            else:
                self.active = False
            self.color = self.color_active if self.active else self.color_inactive

        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    self.active = False
                    self.color = self.color_inactive
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    if event.unicode.isdigit() or event.unicode == '.':
                        self.text += event.unicode

    def draw(self, surface):
        label_img = self.font.render(self.label, True, WHITE)
        surface.blit(label_img, (self.rect.x, self.rect.y - 30))
        pygame.draw.rect(surface, self.color, self.rect, 2)
        text_img = self.font.render(self.text, True, WHITE)
        surface.blit(text_img, (self.rect.x + 5, self.rect.y + 15))

    def get_value(self):
        try:
            return float(self.text)
        except ValueError:
            return None

def main():
    state = STATE_TITLE

    # Starting mechanics
    FACTORY_GRAVITY = 0.5 * SCALE_FACTOR
    FACTORY_BIRD_SIZE = 30 * SCALE_FACTOR
    FACTORY_PIPE_SPEED = 3 * SCALE_FACTOR
    FACTORY_PIPE_GAP = 350
    FACTORY_SPEED_INC = 1.0

    start_gravity = FACTORY_GRAVITY
    start_bird_size = FACTORY_BIRD_SIZE
    start_pipe_speed = float(FACTORY_PIPE_SPEED)
    start_pipe_gap = float(FACTORY_PIPE_GAP)
    start_speed_increase = FACTORY_SPEED_INC
    show_fps = False
    show_hitboxes = False

    # Mechanics
    jump_strength = -8 * SCALE_FACTOR
    current_pipe_gap = start_pipe_gap
    speed_increase_percent = start_speed_increase

    bird = Bird(50.0 * SCALE_FACTOR, SCREEN_HEIGHT // 2, start_bird_size, start_gravity, jump_strength)
    pipes = []
    last_pipe_time = pygame.time.get_ticks()
    # Integer-Locked Movement: ensure starting speed is an integer
    current_pipe_speed = float(round(start_pipe_speed))

    score = 0
    running = True

    # Buttons and Inputs
    btn_w, btn_h = 200, 60
    start_button = Button(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, btn_w, btn_h, "Start")
    exit_button = Button(SCREEN_WIDTH // 2, (SCREEN_HEIGHT // 2) + 100, btn_w, btn_h, "Exit", color=EXIT_RED)
    debug_button = Button(60, 40, 100, 40, "Debug", color=(100, 100, 100), text_color=WHITE)
    title_button = Button(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, btn_w + 100, btn_h, "Back to Title Screen")

    # Debug Menu Components
    reset_button = Button(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 150, btn_w + 50, btn_h, "Reset to Default", color=YELLOW)
    back_button = Button(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 70, btn_w, btn_h, "Back")
    fps_toggle_btn = Button(SCREEN_WIDTH - 150, 100, 200, 60, "FPS: OFF")
    hitbox_toggle_btn = Button(SCREEN_WIDTH - 150, 180, 200, 60, "Hitboxes: OFF")

    # Debug inputs
    gravity_input = TextInput(100, 150, 200, 40, "Gravity", round(start_gravity, 3))
    size_input = TextInput(100, 250, 200, 40, "Bird Size", int(start_bird_size))
    speed_input = TextInput(100, 350, 200, 40, "Pipe Speed", int(start_pipe_speed))
    gap_input = TextInput(100, 450, 200, 40, "Pipe Gap", int(start_pipe_gap))
    increase_input = TextInput(100, 550, 200, 40, "Speed Inc %", start_speed_increase)

    def reset_game():
        nonlocal bird, pipes, score, last_pipe_time, current_pipe_speed, current_pipe_gap, speed_increase_percent
        bird = Bird(50.0 * SCALE_FACTOR, SCREEN_HEIGHT // 2, start_bird_size, start_gravity, jump_strength)
        pipes = []
        score = 0
        last_pipe_time = pygame.time.get_ticks()
        current_pipe_speed = float(round(start_pipe_speed))
        current_pipe_gap = float(start_pipe_gap)
        speed_increase_percent = float(start_speed_increase)

    while running:
        current_time = pygame.time.get_ticks()
        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_h:
                    show_hitboxes = not show_hitboxes
                    hitbox_toggle_btn.text = f"Hitboxes: {'ON' if show_hitboxes else 'OFF'}"
                if event.key == pygame.K_f:
                    show_fps = not show_fps
                    fps_toggle_btn.text = f"FPS: {'ON' if show_fps else 'OFF'}"

        if state == STATE_TITLE:
            for event in events:
                if start_button.is_clicked(event):
                    reset_game()
                    state = STATE_PLAYING
                if debug_button.is_clicked(event):
                    state = STATE_DEBUG
                if exit_button.is_clicked(event):
                    pygame.quit()
                    sys.exit()

            screen.fill(BLACK)
            draw_text("Flabby Bartholomew", WHITE, SCREEN_WIDTH // 2, int(SCREEN_HEIGHT * 0.2), font=font_title, center=True, max_width=SCREEN_WIDTH - 20 * SCALE_FACTOR)
            start_button.draw(screen)
            exit_button.draw(screen)
            debug_button.draw(screen)

            if show_fps:
                fps_text = f"FPS: {int(clock.get_fps())}"
                fps_img = font_small.render(fps_text, True, WHITE)
                screen.blit(fps_img, (SCREEN_WIDTH - fps_img.get_width() - 10, 10))

            pygame.display.flip()

        elif state == STATE_DEBUG:
            for event in events:
                gravity_input.handle_event(event)
                size_input.handle_event(event)
                speed_input.handle_event(event)
                gap_input.handle_event(event)
                increase_input.handle_event(event)

                if fps_toggle_btn.is_clicked(event):
                    show_fps = not show_fps
                    fps_toggle_btn.text = f"FPS: {'ON' if show_fps else 'OFF'}"

                if hitbox_toggle_btn.is_clicked(event):
                    show_hitboxes = not show_hitboxes
                    hitbox_toggle_btn.text = f"Hitboxes: {'ON' if show_hitboxes else 'OFF'}"

                if reset_button.is_clicked(event):
                    start_gravity = FACTORY_GRAVITY
                    start_bird_size = FACTORY_BIRD_SIZE
                    start_pipe_speed = FACTORY_PIPE_SPEED
                    start_pipe_gap = FACTORY_PIPE_GAP
                    start_speed_increase = FACTORY_SPEED_INC
                    show_fps = False
                    show_hitboxes = False

                    gravity_input.text = str(round(start_gravity, 3))
                    size_input.text = str(int(start_bird_size))
                    speed_input.text = str(int(start_pipe_speed))
                    gap_input.text = str(int(start_pipe_gap))
                    increase_input.text = str(start_speed_increase)
                    fps_toggle_btn.text = "FPS: OFF"
                    hitbox_toggle_btn.text = "Hitboxes: OFF"

                if back_button.is_clicked(event):
                    val = gravity_input.get_value()
                    if val is not None: start_gravity = val
                    val = size_input.get_value()
                    if val is not None: start_bird_size = val
                    val = speed_input.get_value()
                    if val is not None: start_pipe_speed = val
                    val = gap_input.get_value()
                    if val is not None: start_pipe_gap = val
                    val = increase_input.get_value()
                    if val is not None: start_speed_increase = val
                    state = STATE_TITLE

            screen.fill(BLACK)
            draw_text("Debug Menu", WHITE, SCREEN_WIDTH // 2, 50, font=font_title, center=True)
            gravity_input.draw(screen)
            size_input.draw(screen)
            speed_input.draw(screen)
            gap_input.draw(screen)
            increase_input.draw(screen)
            fps_toggle_btn.draw(screen)
            hitbox_toggle_btn.draw(screen)
            reset_button.draw(screen)
            back_button.draw(screen)

            if show_fps:
                fps_text = f"FPS: {int(clock.get_fps())}"
                fps_img = font_small.render(fps_text, True, WHITE)
                screen.blit(fps_img, (SCREEN_WIDTH - fps_img.get_width() - 10, 10))

            pygame.display.flip()

        elif state == STATE_PLAYING:
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        bird.jump()

            bird.update(1/FPS)

            if current_time - last_pipe_time > PIPE_FREQUENCY:
                pipe_height = random.randint(50, SCREEN_HEIGHT - int(current_pipe_gap) - 50)
                top_pipe = Pipe(SCREEN_WIDTH, 0, PIPE_WIDTH, pipe_height, True, max_top_pipe_surface)
                bottom_pipe = Pipe(SCREEN_WIDTH, pipe_height + int(current_pipe_gap), PIPE_WIDTH, SCREEN_HEIGHT - pipe_height - int(current_pipe_gap), False, max_bottom_pipe_surface)
                pipes.append(top_pipe)
                pipes.append(bottom_pipe)
                last_pipe_time = current_time

            for p in pipes:
                p.update(current_pipe_speed)

            pipes = [p for p in pipes if p.rect.right > 0]

            for p in pipes:
                offset = (p.rect.x - bird.rect.x, p.rect.y - bird.rect.y)
                if bird.mask.overlap(p.mask, offset):
                    state = STATE_GAME_OVER

            if bird.rect.top < 0 or bird.rect.bottom > SCREEN_HEIGHT:
                state = STATE_GAME_OVER

            for p in pipes:
                if not p.passed and bird.x > p.rect.right:
                    p.passed = True
                    if p.is_top:
                        score += 1
                        bird.grow(speed_increase_percent)
                        # Integer-Locked Movement: rounding the new speed
                        current_pipe_speed = float(round(current_pipe_speed * (1 + speed_increase_percent / 100)))

            screen.fill(BLACK)
            for p in pipes:
                p.draw(screen)
            bird.draw(screen)

            # Enhanced Diagnostic: Hitbox Rendering
            if show_hitboxes:
                # Draw Bird Mask Outline (Red)
                bird_outline = bird.mask.outline()
                if bird_outline:
                    bird_points = [(p[0] + bird.rect.x, p[1] + bird.rect.y) for p in bird_outline]
                    if len(bird_points) > 1:
                        pygame.draw.lines(screen, RED, True, bird_points, 2)

                # Draw Pipe Mask Outlines (Green)
                for p in pipes:
                    pipe_outline = p.mask.outline()
                    if pipe_outline:
                        pipe_points = [(pt[0] + p.rect.x, pt[1] + p.rect.y) for pt in pipe_outline]
                        if len(pipe_points) > 1:
                            pygame.draw.lines(screen, GREEN, True, pipe_points, 2)

            draw_text(f"Score: {score}", WHITE, 10 * SCALE_FACTOR, 10 * SCALE_FACTOR, font=font_small)

            if show_fps:
                fps_text = f"FPS: {int(clock.get_fps())}"
                fps_img = font_small.render(fps_text, True, WHITE)
                screen.blit(fps_img, (SCREEN_WIDTH - fps_img.get_width() - 10, 10))

            pygame.display.flip()

        elif state == STATE_GAME_OVER:
            for event in events:
                if title_button.is_clicked(event):
                    state = STATE_TITLE

            screen.fill(BLACK)
            draw_text("GAME OVER", WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100 * SCALE_FACTOR, center=True)
            draw_text(f"Final Score: {score}", WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50 * SCALE_FACTOR, center=True)
            title_button.draw(screen)

            if show_fps:
                fps_text = f"FPS: {int(clock.get_fps())}"
                fps_img = font_small.render(fps_text, True, WHITE)
                screen.blit(fps_img, (SCREEN_WIDTH - fps_img.get_width() - 10, 10))

            pygame.display.flip()

        clock.tick(FPS)

if __name__ == "__main__":
    main()
