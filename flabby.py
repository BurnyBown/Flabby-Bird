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
EXIT_RED = (165, 48, 48)

# Set up display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.DOUBLEBUF)
pygame.display.set_caption("Flabby Bartholomew")
clock = pygame.time.Clock()

# Assets
try:
    bart_flap = pygame.image.load('Bart flap.png').convert_alpha()
    bart_no_flap = pygame.image.load('Bart no flap.png').convert_alpha()

    # Load and scale base pipe image
    base_pipe = pygame.image.load('perfect pipe up.png').convert_alpha()
    pipe_scaled_width = PIPE_WIDTH
    pipe_scaled_height = int(base_pipe.get_height() * (PIPE_WIDTH / base_pipe.get_width()))
    base_pipe = pygame.transform.scale(base_pipe, (pipe_scaled_width, pipe_scaled_height)).convert_alpha()

    # Slice pipe: Cap (top 20%) and Body (a 1px slice from the body)
    cap_height = int(pipe_scaled_height * 0.20)
    pipe_cap = base_pipe.subsurface((0, 0, pipe_scaled_width, cap_height))
    body_row_y = int(pipe_scaled_height * 0.90)
    pipe_body = base_pipe.subsurface((0, body_row_y, pipe_scaled_width, 1))

    # Flipped versions for top pipes
    pipe_cap_flipped = pygame.transform.flip(pipe_cap, False, True).convert_alpha()
    pipe_body_flipped = pygame.transform.flip(pipe_body, False, True).convert_alpha()

except pygame.error as e:
    print(f"Error loading assets: {e}")
    sys.exit()

# Fonts
def get_font(size, bold=False, scale=True):
    if scale:
        return pygame.font.SysFont('Arial', int(size * SCALE_FACTOR), bold=bold)
    else:
        return pygame.font.SysFont('Arial', int(size), bold=bold)

font_main = get_font(36, bold=True)
font_small = get_font(24)
font_title = get_font(48, bold=True)
font_ui = get_font(30, scale=False)

def draw_text(text, color, x, y, font=font_main, center=False, max_width=None):
    if max_width and font.size(text)[0] > max_width:
        temp_font_size = int(48 * SCALE_FACTOR)
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

class Bird:
    def __init__(self, x, y, size, gravity):
        self.center_x = float(x)
        self.center_y = float(y)
        self.size = float(size)
        self.vel = 0.0
        self.gravity = gravity
        self.flap_timer = 0
        self.using_flap_sprite = False
        self.rect = pygame.Rect(0, 0, int(size), int(size))
        self.rect.center = (int(self.center_x), int(self.center_y))
        self.mask = None
        self.current_rotated_image = None

    def update(self, dt):
        self.vel += self.gravity
        self.center_y += self.vel
        if self.flap_timer > 0:
            self.flap_timer -= dt
            self.using_flap_sprite = True
        else:
            self.using_flap_sprite = False
        # Update rect center before rotation
        self.rect.center = (int(self.center_x), int(self.center_y))

    def flap(self, strength):
        self.vel = strength
        self.flap_timer = 0.15

    def prepare(self):
        sprite = bart_flap if self.using_flap_sprite else bart_no_flap
        scaled = pygame.transform.scale(sprite, (int(self.size), int(self.size))).convert_alpha()
        rotation = -self.vel * 3
        rotation = max(-90, min(rotation, 30))
        rotated = pygame.transform.rotate(scaled, rotation).convert_alpha()
        # Anchor the rotation to the current rect center
        self.rect = rotated.get_rect(center=self.rect.center)
        self.mask = pygame.mask.from_surface(rotated)
        self.current_rotated_image = rotated

    def draw(self, surface):
        if self.current_rotated_image:
            surface.blit(self.current_rotated_image, self.rect.topleft)

class Pipe:
    def __init__(self, x, gap_y, gap_height):
        self.x_float = float(x)
        self.gap_y = gap_y
        self.gap_height = gap_height
        self.passed = False

        # Pre-render top pipe
        top_height = int(gap_y)
        self.top_rect = pygame.Rect(int(self.x_float), 0, PIPE_WIDTH, top_height)
        self.top_image = pygame.Surface((PIPE_WIDTH, top_height), pygame.SRCALPHA).convert_alpha()
        body_h_top = top_height - cap_height
        if body_h_top > 0:
            stretched_body_top = pygame.transform.scale(pipe_body_flipped, (PIPE_WIDTH, body_h_top)).convert_alpha()
            self.top_image.blit(stretched_body_top, (0, 0))
        self.top_image.blit(pipe_cap_flipped, (0, max(0, top_height - cap_height)))
        self.top_mask = pygame.mask.from_surface(self.top_image)

        # Pre-render bottom pipe
        bottom_y = int(gap_y + gap_height)
        bottom_height = SCREEN_HEIGHT - bottom_y
        self.bottom_rect = pygame.Rect(int(self.x_float), bottom_y, PIPE_WIDTH, bottom_height)
        self.bottom_image = pygame.Surface((PIPE_WIDTH, bottom_height), pygame.SRCALPHA).convert_alpha()
        self.bottom_image.blit(pipe_cap, (0, 0))
        body_h_bottom = bottom_height - cap_height
        if body_h_bottom > 0:
            stretched_body_bottom = pygame.transform.scale(pipe_body, (PIPE_WIDTH, body_h_bottom)).convert_alpha()
            self.bottom_image.blit(stretched_body_bottom, (0, cap_height))
        self.bottom_mask = pygame.mask.from_surface(self.bottom_image)

    def update(self, speed):
        self.x_float -= speed
        self.top_rect.x = int(self.x_float)
        self.bottom_rect.x = int(self.x_float)

    def draw(self, surface):
        surface.blit(self.top_image, (int(self.x_float), self.top_rect.y))
        surface.blit(self.bottom_image, (int(self.x_float), self.bottom_rect.y))

def main():
    state = STATE_TITLE
    FACTORY_GRAVITY, FACTORY_BIRD_SIZE, FACTORY_PIPE_SPEED, FACTORY_PIPE_GAP, FACTORY_SPEED_INC = 0.5 * SCALE_FACTOR, 30 * SCALE_FACTOR, 3 * SCALE_FACTOR, 350, 1.0
    start_gravity, start_bird_size, start_pipe_speed, start_pipe_gap, start_speed_increase = FACTORY_GRAVITY, FACTORY_BIRD_SIZE, FACTORY_PIPE_SPEED, FACTORY_PIPE_GAP, FACTORY_SPEED_INC
    show_fps = False

    bird, pipes, score = None, [], 0
    current_pipe_speed, current_pipe_gap, speed_increase_percent = start_pipe_speed, start_pipe_gap, start_speed_increase
    last_pipe_time = 0

    btn_w, btn_h = 200, 60
    start_button = Button(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, btn_w, btn_h, "Start")
    exit_button = Button(SCREEN_WIDTH // 2, (SCREEN_HEIGHT // 2) + 100, btn_w, btn_h, "Exit", color=EXIT_RED)
    debug_button = Button(60, 40, 100, 40, "Debug", color=(100, 100, 100), text_color=WHITE)
    title_button = Button(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, btn_w + 100, btn_h, "Back to Title Screen")
    reset_button = Button(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 150, btn_w + 50, btn_h, "Reset to Default", color=YELLOW)
    back_button = Button(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 70, btn_w, btn_h, "Back")
    fps_toggle_btn = Button(SCREEN_WIDTH - 150, 100, 200, 60, "FPS: OFF")
    gravity_input = TextInput(100, 150, 200, 40, "Gravity", round(start_gravity, 3))
    size_input = TextInput(100, 250, 200, 40, "Bird Size", int(start_bird_size))
    speed_input = TextInput(100, 350, 200, 40, "Pipe Speed", int(start_pipe_speed))
    gap_input = TextInput(100, 450, 200, 40, "Pipe Gap", int(start_pipe_gap))
    increase_input = TextInput(100, 550, 200, 40, "Speed Inc %", start_speed_increase)

    def reset_game():
        nonlocal bird, pipes, score, current_pipe_speed, current_pipe_gap, speed_increase_percent, last_pipe_time
        bird = Bird(50 * SCALE_FACTOR, SCREEN_HEIGHT // 2, start_bird_size, start_gravity)
        pipes, score = [], 0
        current_pipe_speed, current_pipe_gap, speed_increase_percent = float(start_pipe_speed), float(start_pipe_gap), float(start_speed_increase)
        last_pipe_time = pygame.time.get_ticks()

    while True:
        current_time, events = pygame.time.get_ticks(), pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()

        if state == STATE_TITLE:
            for event in events:
                if start_button.is_clicked(event): reset_game(); state = STATE_PLAYING
                if debug_button.is_clicked(event): state = STATE_DEBUG
                if exit_button.is_clicked(event): pygame.quit(); sys.exit()
            screen.fill(BLACK)
            draw_text("Flabby Bartholomew", WHITE, SCREEN_WIDTH // 2, int(SCREEN_HEIGHT * 0.2), font=font_title, center=True, max_width=SCREEN_WIDTH - 20 * SCALE_FACTOR)
            start_button.draw(screen); exit_button.draw(screen); debug_button.draw(screen)

        elif state == STATE_DEBUG:
            for event in events:
                gravity_input.handle_event(event); size_input.handle_event(event); speed_input.handle_event(event); gap_input.handle_event(event); increase_input.handle_event(event)
                if fps_toggle_btn.is_clicked(event): show_fps = not show_fps; fps_toggle_btn.text = f"FPS: {'ON' if show_fps else 'OFF'}"
                if reset_button.is_clicked(event):
                    start_gravity, start_bird_size, start_pipe_speed, start_pipe_gap, start_speed_increase = FACTORY_GRAVITY, FACTORY_BIRD_SIZE, FACTORY_PIPE_SPEED, FACTORY_PIPE_GAP, FACTORY_SPEED_INC
                    show_fps = False
                    gravity_input.text, size_input.text, speed_input.text, gap_input.text, increase_input.text = str(round(start_gravity, 3)), str(int(start_bird_size)), str(int(start_pipe_speed)), str(int(start_pipe_gap)), str(start_speed_increase)
                    fps_toggle_btn.text = "FPS: OFF"
                if back_button.is_clicked(event):
                    start_gravity, start_bird_size, start_pipe_speed, start_pipe_gap, start_speed_increase = gravity_input.get_value() or start_gravity, size_input.get_value() or start_bird_size, speed_input.get_value() or start_pipe_speed, gap_input.get_value() or start_pipe_gap, increase_input.get_value() or start_speed_increase
                    state = STATE_TITLE
            screen.fill(BLACK)
            draw_text("Debug Menu", WHITE, SCREEN_WIDTH // 2, 50, font=font_title, center=True)
            gravity_input.draw(screen); size_input.draw(screen); speed_input.draw(screen); gap_input.draw(screen); increase_input.draw(screen)
            fps_toggle_btn.draw(screen); reset_button.draw(screen); back_button.draw(screen)

        elif state == STATE_PLAYING:
            for event in events:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE: bird.flap(-8 * SCALE_FACTOR)
            bird.update(1/FPS)
            if current_time - last_pipe_time > PIPE_FREQUENCY:
                gap_y = random.randint(50, SCREEN_HEIGHT - int(current_pipe_gap) - 50)
                pipes.append(Pipe(SCREEN_WIDTH, gap_y, current_pipe_gap))
                last_pipe_time = current_time
            for p in pipes: p.update(current_pipe_speed)
            pipes = [p for p in pipes if p.x_float + PIPE_WIDTH > 0]
            bird.prepare()
            if bird.rect.top < 0 or bird.rect.bottom > SCREEN_HEIGHT: state = STATE_GAME_OVER
            for p in pipes:
                rel_top, rel_bottom = (p.top_rect.x - bird.rect.x, p.top_rect.y - bird.rect.y), (p.bottom_rect.x - bird.rect.x, p.bottom_rect.y - bird.rect.y)
                if bird.mask.overlap(p.top_mask, rel_top) or bird.mask.overlap(p.bottom_mask, rel_bottom): state = STATE_GAME_OVER
                if not p.passed and bird.center_x > p.x_float + PIPE_WIDTH:
                    p.passed = True; score += 1; bird.size *= 1.05; bird.gravity *= 1.05; current_pipe_speed *= (1 + speed_increase_percent / 100)
            screen.fill(BLACK)
            for p in pipes: p.draw(screen)
            bird.draw(screen)
            draw_text(f"Score: {score}", WHITE, 10 * SCALE_FACTOR, 10 * SCALE_FACTOR, font=font_small)

        elif state == STATE_GAME_OVER:
            for event in events:
                if title_button.is_clicked(event): state = STATE_TITLE
            screen.fill(BLACK)
            draw_text("GAME OVER", WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100 * SCALE_FACTOR, center=True)
            draw_text(f"Final Score: {score}", WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50 * SCALE_FACTOR, center=True)
            title_button.draw(screen)

        if show_fps:
            fps_img = font_small.render(f"FPS: {int(clock.get_fps())}", True, WHITE)
            screen.blit(fps_img, (SCREEN_WIDTH - fps_img.get_width() - 10, 10))
        pygame.display.flip(); clock.tick(FPS)

if __name__ == "__main__": main()
