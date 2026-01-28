import pygame
import sys
import random
import os

# Initialize Pygame
pygame.init()

# Constants (Logical Resolution for SCALED mode)
SCREEN_WIDTH = 400
SCREEN_HEIGHT = 600
FPS = 60
PIPE_WIDTH = 60
PIPE_SPAWN_DISTANCE = 250  # Pixels between pipe spawns

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

# Set up display with SCALED and DOUBLEBUF for Mac/Retina optimization
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED | pygame.DOUBLEBUF)
pygame.display.set_caption("Flabby Bartholomew")

# Config and Persistence
CONFIG_FILE = "config.txt"

def load_config():
    config = {"highscore": 0, "show_fps": False, "show_hitboxes": False}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                for line in f:
                    key, val = line.strip().split("=")
                    if key == "highscore": config["highscore"] = int(val)
                    elif key == "show_fps": config["show_fps"] = val == "True"
                    elif key == "show_hitboxes": config["show_hitboxes"] = val == "True"
        except:
            pass
    return config

def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            for key, val in config.items():
                f.write(f"{key}={val}\n")
    except:
        pass

config = load_config()
clock = pygame.time.Clock()

# Assets
try:
    # Use pygame.transform.scale for crisp pixels
    bart_flap = pygame.image.load('Bart flap.png').convert_alpha()
    bart_no_flap = pygame.image.load('Bart no flap.png').convert_alpha()

    # Window Icon
    try:
        icon = pygame.image.load('bird.png')
        pygame.display.set_icon(icon)
    except:
        pygame.display.set_icon(bart_no_flap)

    # Background
    background_img = None
    if os.path.exists('background.png'):
        background_img = pygame.image.load('background.png').convert()
        background_img = pygame.transform.scale(background_img, (SCREEN_WIDTH, SCREEN_HEIGHT))

    # Music
    if os.path.exists('music.mp3'):
        pygame.mixer.music.load('music.mp3')
        pygame.mixer.music.play(-1)
        pygame.mixer.music.set_volume(0.5)

    # Pipes
    base_pipe = pygame.image.load('perfect pipe up.png').convert_alpha()
    pipe_scaled_width = PIPE_WIDTH
    pipe_scaled_height = int(base_pipe.get_height() * (PIPE_WIDTH / base_pipe.get_width()))
    base_pipe = pygame.transform.scale(base_pipe, (pipe_scaled_width, pipe_scaled_height))

    cap_height = int(pipe_scaled_height * 0.20)
    pipe_cap = base_pipe.subsurface((0, 0, pipe_scaled_width, cap_height))
    body_row_y = int(pipe_scaled_height * 0.90)
    pipe_body = base_pipe.subsurface((0, body_row_y, pipe_scaled_width, 1))

    pipe_cap_flipped = pygame.transform.flip(pipe_cap, False, True)
    pipe_body_flipped = pygame.transform.flip(pipe_body, False, True)

    max_top_pipe_surface = pygame.Surface((PIPE_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA).convert_alpha()
    max_bottom_pipe_surface = pygame.Surface((PIPE_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA).convert_alpha()

    body_height = SCREEN_HEIGHT - cap_height
    if body_height > 0:
        stretched_body_top = pygame.transform.scale(pipe_body_flipped, (PIPE_WIDTH, body_height))
        max_top_pipe_surface.blit(stretched_body_top, (0, 0))
    max_top_pipe_surface.blit(pipe_cap_flipped, (0, body_height))

    max_bottom_pipe_surface.blit(pipe_cap, (0, 0))
    if body_height > 0:
        stretched_body_bottom = pygame.transform.scale(pipe_body, (PIPE_WIDTH, body_height))
        max_bottom_pipe_surface.blit(stretched_body_bottom, (0, cap_height))

except pygame.error as e:
    print(f"Error loading assets: {e}")
    sys.exit()

# Fonts
def get_font(size, bold=False):
    return pygame.font.SysFont('Arial', int(size), bold=bold)

class Bird:
    def __init__(self, x, y, size, gravity, jump_strength):
        self.x = float(x)
        self.y = float(y)
        self.vel = 0.0
        self.width = float(size)
        self.height = float(size)
        self.gravity = float(gravity)
        self.jump_strength = float(jump_strength)
        self.flap_timer = 0.0
        self.using_flap_sprite = False
        self.update_base_sprites()
        self.rect = self.base_no_flap.get_rect(center=(int(self.x), int(self.y)))

    def update_base_sprites(self):
        # Crisp scaling
        self.base_flap = pygame.transform.scale(bart_flap, (int(self.width), int(self.height)))
        self.base_no_flap = pygame.transform.scale(bart_no_flap, (int(self.width), int(self.height)))
        self.mask_flap = pygame.mask.from_surface(self.base_flap)
        self.mask_no_flap = pygame.mask.from_surface(self.base_no_flap)

    @property
    def mask(self):
        return self.mask_flap if self.using_flap_sprite else self.mask_no_flap

    def jump(self):
        self.vel = self.jump_strength
        self.flap_timer = 0.15

    def grow(self):
        self.width *= 1.02
        self.height *= 1.02
        self.gravity *= 1.02
        self.update_base_sprites()

    def update(self, dt):
        self.vel += self.gravity * dt
        self.y += self.vel * dt

        if self.flap_timer > 0:
            self.flap_timer -= dt
            self.using_flap_sprite = True
        else:
            self.using_flap_sprite = False

        self.rect.center = (int(self.x), int(self.y))

    def draw(self, surface):
        image = self.base_flap if self.using_flap_sprite else self.base_no_flap
        surface.blit(image, (int(self.rect.x), int(self.rect.y)))

class Pipe:
    def __init__(self, x, y, width, height, is_top, max_pipe_surface):
        self.x_float = float(x)
        self.y = y
        self.width = width
        self.height = height
        self.is_top = is_top
        self.passed = False

        if is_top:
            self.image = max_pipe_surface.subsurface((0, SCREEN_HEIGHT - height, width, height))
        else:
            self.image = max_pipe_surface.subsurface((0, 0, width, height))

        self.rect = self.image.get_rect(topleft=(int(self.x_float), self.y))
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, dt, speed):
        self.x_float -= speed * dt
        self.rect.x = int(self.x_float)

    def draw(self, surface):
        surface.blit(self.image, (int(self.rect.x), int(self.rect.y)))

font_main = get_font(36, bold=True)
font_small = get_font(24)
font_title = get_font(48, bold=True)
font_ui = get_font(30)

def draw_text(text, color, x, y, font=font_main, center=False, max_width=None):
    if max_width and font.size(text)[0] > max_width:
        temp_size = font.get_height()
        while temp_size > 10 and get_font(temp_size, bold=True).size(text)[0] > max_width:
            temp_size -= 2
        font = get_font(temp_size, bold=True)

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
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

class Slider:
    def __init__(self, x, y, width, label, min_val, max_val, initial_val):
        self.rect = pygame.Rect(x, y, width, 10)
        self.label = label
        self.min_val = min_val
        self.max_val = max_val
        self.val = initial_val
        self.handle_rect = pygame.Rect(x + (initial_val - min_val) / (max_val - min_val) * width - 10, y - 10, 20, 30)
        self.dragging = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.handle_rect.collidepoint(event.pos):
                self.dragging = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.handle_rect.centerx = max(self.rect.left, min(event.pos[0], self.rect.right))
                rel = (self.handle_rect.centerx - self.rect.left) / self.rect.width
                self.val = self.min_val + rel * (self.max_val - self.min_val)

    def draw(self, surface):
        draw_text(f"{self.label}: {self.val:.2f}", WHITE, self.rect.left, self.rect.top - 25, font=font_small)
        pygame.draw.rect(surface, (100, 100, 100), self.rect)
        pygame.draw.rect(surface, WHITE, self.handle_rect)

class TextInput:
    def __init__(self, x, y, width, height, label, initial_value):
        self.rect = pygame.Rect(x, y, width, height)
        self.label = label
        self.text = str(initial_value)
        self.active = False
        self.color = (150, 150, 150)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
            self.color = WHITE if self.active else (150, 150, 150)
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE: self.text = self.text[:-1]
            elif event.unicode.isdigit() or event.unicode == '.': self.text += event.unicode

    def draw(self, surface):
        draw_text(self.label, WHITE, self.rect.x, self.rect.y - 25, font=font_small)
        pygame.draw.rect(surface, self.color, self.rect, 2)
        draw_text(self.text, WHITE, self.rect.x + 5, self.rect.y + 5, font=font_small)

    def get_value(self):
        try: return float(self.text)
        except: return None

def main():
    state = STATE_TITLE

    # Defaults
    DEFAULT_GRAVITY = 1800.0  # 0.5 * 3600
    DEFAULT_JUMP = -480.0     # -8 * 60
    DEFAULT_SPEED = 300.0
    DEFAULT_GAP = 150.0
    DEFAULT_GROWTH = 2.0

    current_gravity = DEFAULT_GRAVITY
    current_pipe_speed = DEFAULT_SPEED
    current_pipe_gap = DEFAULT_GAP
    current_growth = DEFAULT_GROWTH

    bird = Bird(50, SCREEN_HEIGHT // 2, 30, current_gravity, DEFAULT_JUMP)
    pipes = []
    distance_since_last_pipe = PIPE_SPAWN_DISTANCE # Spawn immediately
    score = 0
    running = True

    # Buttons
    start_btn = Button(SCREEN_WIDTH // 2, 300, 150, 50, "Start")
    exit_btn = Button(SCREEN_WIDTH // 2, 400, 150, 50, "Exit", color=EXIT_RED)
    debug_btn = Button(50, 30, 80, 30, "Debug", color=(100, 100, 100), text_color=WHITE)
    title_btn = Button(SCREEN_WIDTH // 2, 450, 200, 50, "Title Screen")

    # Debug UI
    speed_input = TextInput(50, 100, 100, 30, "Pipe Speed", DEFAULT_SPEED)
    gap_input = TextInput(50, 160, 100, 30, "Vert Gap", DEFAULT_GAP)
    growth_input = TextInput(50, 220, 100, 30, "Growth %", DEFAULT_GROWTH)
    volume_slider = Slider(50, 300, 300, "Volume", 0.0, 1.0, 0.5)
    back_btn = Button(SCREEN_WIDTH // 2, 500, 100, 40, "Back")

    def reset_game():
        nonlocal bird, pipes, score, distance_since_last_pipe, current_gravity, current_pipe_speed, current_pipe_gap, current_growth
        current_gravity = DEFAULT_GRAVITY
        current_pipe_speed = speed_input.get_value() or DEFAULT_SPEED
        current_pipe_gap = gap_input.get_value() or DEFAULT_GAP
        current_growth = growth_input.get_value() or DEFAULT_GROWTH
        bird = Bird(50, SCREEN_HEIGHT // 2, 30, current_gravity, DEFAULT_JUMP)
        pipes = []
        distance_since_last_pipe = PIPE_SPAWN_DISTANCE
        score = 0

    while running:
        dt = clock.tick(FPS) / 1000.0
        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                save_config(config)
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f:
                    config["show_fps"] = not config["show_fps"]
                if event.key == pygame.K_h:
                    config["show_hitboxes"] = not config["show_hitboxes"]

        if state == STATE_TITLE:
            for event in events:
                if start_btn.is_clicked(event):
                    reset_game()
                    state = STATE_PLAYING
                if debug_btn.is_clicked(event): state = STATE_DEBUG
                if exit_btn.is_clicked(event):
                    save_config(config)
                    pygame.quit()
                    sys.exit()

            screen.fill(BLACK)
            if background_img: screen.blit(background_img, (0,0))
            draw_text("Flabby Bartholomew", WHITE, SCREEN_WIDTH // 2, 150, font=font_title, center=True, max_width=SCREEN_WIDTH-40)
            draw_text(f"High Score: {config['highscore']}", YELLOW, SCREEN_WIDTH // 2, 220, font=font_small, center=True)
            start_btn.draw(screen)
            exit_btn.draw(screen)
            debug_btn.draw(screen)

        elif state == STATE_DEBUG:
            for event in events:
                speed_input.handle_event(event)
                gap_input.handle_event(event)
                growth_input.handle_event(event)
                volume_slider.handle_event(event)
                if back_btn.is_clicked(event): state = STATE_TITLE

            pygame.mixer.music.set_volume(volume_slider.val)
            screen.fill(BLACK)
            draw_text("Debug Menu", WHITE, SCREEN_WIDTH // 2, 40, font=font_title, center=True)
            speed_input.draw(screen)
            gap_input.draw(screen)
            growth_input.draw(screen)
            volume_slider.draw(screen)
            back_btn.draw(screen)

        elif state == STATE_PLAYING:
            for event in events:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    bird.jump()

            bird.update(dt)

            distance_since_last_pipe += current_pipe_speed * dt
            if distance_since_last_pipe >= PIPE_SPAWN_DISTANCE:
                h = random.randint(50, SCREEN_HEIGHT - int(current_pipe_gap) - 50)
                pipes.append(Pipe(SCREEN_WIDTH, 0, PIPE_WIDTH, h, True, max_top_pipe_surface))
                pipes.append(Pipe(SCREEN_WIDTH, h + int(current_pipe_gap), PIPE_WIDTH, SCREEN_HEIGHT - h - int(current_pipe_gap), False, max_bottom_pipe_surface))
                distance_since_last_pipe = 0

            for p in pipes:
                p.update(dt, current_pipe_speed)
                if not p.passed and bird.x > p.rect.right:
                    p.passed = True
                    if p.is_top:
                        score += 1
                        bird.grow()
                        current_pipe_speed *= (1 + current_growth / 100.0)

            pipes = [p for p in pipes if p.rect.right > 0]

            for p in pipes:
                if bird.mask.overlap(p.mask, (p.rect.x - bird.rect.x, p.rect.y - bird.rect.y)):
                    state = STATE_GAME_OVER
            if bird.rect.top < 0 or bird.rect.bottom > SCREEN_HEIGHT:
                state = STATE_GAME_OVER

            if state == STATE_GAME_OVER:
                if score > config["highscore"]:
                    config["highscore"] = score
                    save_config(config)

            screen.fill(BLACK)
            if background_img: screen.blit(background_img, (0,0))
            for p in pipes: p.draw(screen)
            bird.draw(screen)

            if config["show_hitboxes"]:
                for obj, color in [(bird, RED)] + [(p, GREEN) for p in pipes]:
                    outline = obj.mask.outline()
                    if outline:
                        pygame.draw.lines(screen, color, True, [(pt[0] + obj.rect.x, pt[1] + obj.rect.y) for pt in outline], 2)

            draw_text(f"Score: {score}", WHITE, 15, 15, font=font_small)

        elif state == STATE_GAME_OVER:
            for event in events:
                if title_btn.is_clicked(event): state = STATE_TITLE

            screen.fill(BLACK)
            draw_text("GAME OVER", WHITE, SCREEN_WIDTH // 2, 200, font=font_title, center=True)
            draw_text(f"Score: {score}", WHITE, SCREEN_WIDTH // 2, 280, font=font_main, center=True)
            draw_text(f"High Score: {config['highscore']}", YELLOW, SCREEN_WIDTH // 2, 330, font=font_small, center=True)
            title_btn.draw(screen)

        if config["show_fps"]:
            fps_img = font_small.render(f"FPS: {int(clock.get_fps())}", True, WHITE)
            screen.blit(fps_img, (SCREEN_WIDTH - fps_img.get_width() - 10, 10))

        pygame.display.flip()

if __name__ == "__main__":
    main()
