import pygame
import sys
import random
import os
import time

# Set initial physical window size BEFORE pygame.init()
os.environ['SDL_VIDEO_WINDOW_SIZE'] = '800x1200'

# Initialize Pygame
pygame.init()
pygame.mixer.init()
print(f"Mixer Status: {pygame.mixer.get_init()}")

# Constants (Logical Resolution)
LOGICAL_WIDTH = 400
LOGICAL_HEIGHT = 600
TARGET_FPS = 120
PIPE_WIDTH = 60
PIPE_SPAWN_DISTANCE = 250

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

# Display Setup
screen = pygame.display.set_mode((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SCALED | pygame.RESIZABLE | pygame.DOUBLEBUF, vsync=1)
pygame.display.set_caption("Flabby Bartholomew")

# Persistence
CONFIG_FILE = "config.txt"
HIGHSCORE_FILE = "highscore.txt"

def load_config():
    cfg = {"show_fps": False, "show_hitboxes": False}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=")
                        if k in cfg: cfg[k] = (v == "True")
        except Exception as e:
            print(f"Error loading config: {e}")
    return cfg

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w") as f:
            for k, v in cfg.items():
                f.write(f"{k}={v}\n")
    except Exception as e:
        print(f"Error saving config: {e}")

def load_highscore():
    if os.path.exists(HIGHSCORE_FILE):
        try:
            with open(HIGHSCORE_FILE, "r") as f:
                return int(f.read().strip())
        except:
            return 0
    return 0

def save_highscore(score):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            f.write(str(score))
    except Exception as e:
        print(f"Error saving highscore: {e}")

config = load_config()
highscore = load_highscore()
clock = pygame.time.Clock()

# Assets
try:
    # Use transform.scale for crisp pixels
    bart_flap = pygame.image.load('Bart flap.png').convert_alpha()
    bart_no_flap = pygame.image.load('Bart no flap.png').convert_alpha()

    # Window Icon
    try:
        icon = pygame.image.load('bird.png').convert_alpha()
        pygame.display.set_icon(icon)
    except Exception as e:
        print(f"Icon bird.png not found: {e}")
        pygame.display.set_icon(bart_no_flap)

    # Background
    background_img = None
    if os.path.exists('background.png'):
        background_img = pygame.image.load('background.png').convert()
        background_img = pygame.transform.scale(background_img, (LOGICAL_WIDTH, LOGICAL_HEIGHT))

    # Music
    music_path = os.path.join(os.path.dirname(__file__), 'music.mp3')
    try:
        if os.path.exists(music_path):
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.play(-1)
            pygame.mixer.music.set_volume(0.5)
            print(f"Music loaded successfully: {music_path}")
        else:
            print("NOTE: music.mp3 not found. Check local directory.")
    except Exception as e:
        print(f"Error loading music: {e}")

    # Pipes
    pipe_up_img = pygame.image.load('perfect pipe up.png').convert_alpha()
    pipe_scale = PIPE_WIDTH / pipe_up_img.get_width()
    pipe_h = int(pipe_up_img.get_height() * pipe_scale)
    pipe_up_img = pygame.transform.scale(pipe_up_img, (PIPE_WIDTH, pipe_h))

    # Pre-render pipe surfaces to avoid per-frame scaling
    cap_h = int(pipe_h * 0.20)
    pipe_cap = pipe_up_img.subsurface((0, 0, PIPE_WIDTH, cap_h))
    pipe_body_row = pipe_up_img.subsurface((0, int(pipe_h * 0.90), PIPE_WIDTH, 1))

    pipe_cap_flipped = pygame.transform.flip(pipe_cap, False, True)
    pipe_body_flipped = pygame.transform.flip(pipe_body_row, False, True)

    max_top_pipe = pygame.Surface((PIPE_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA).convert_alpha()
    max_bot_pipe = pygame.Surface((PIPE_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA).convert_alpha()

    body_h = LOGICAL_HEIGHT - cap_h
    if body_h > 0:
        stretched_body_top = pygame.transform.scale(pipe_body_flipped, (PIPE_WIDTH, body_h))
        max_top_pipe.blit(stretched_body_top, (0, 0))
        stretched_body_bot = pygame.transform.scale(pipe_body_row, (PIPE_WIDTH, body_h))
        max_bot_pipe.blit(stretched_body_bot, (0, cap_h))

    max_top_pipe.blit(pipe_cap_flipped, (0, body_h))
    max_bot_pipe.blit(pipe_cap, (0, 0))

except Exception as e:
    print(f"Fatal Error loading assets: {e}")
    sys.exit()

# Fonts
def get_font(size, bold=False):
    return pygame.font.SysFont('Arial', int(size), bold=bold)

font_main = get_font(36, bold=True)
font_small = get_font(24)
font_title = get_font(48, bold=True)
font_ui = get_font(28)

class Bird:
    def __init__(self, x, y, size):
        self.base_x = float(x)
        self.base_y = float(y)
        self.base_size = float(size)
        self.base_gravity = 1800.0
        self.jump_strength = -480.0

        self.x = self.base_x
        self.y = self.base_y
        self.width = self.base_size
        self.height = self.base_size
        self.vel = 0.0
        self.gravity = self.base_gravity

        self.flap_timer = 0.0
        self.using_flap_sprite = False
        self.rect = pygame.Rect(0, 0, int(self.width), int(self.height))
        self.update_appearance()

    def update_appearance(self):
        w, h = round(self.width), round(self.height)
        self.img_flap = pygame.transform.scale(bart_flap, (w, h))
        self.img_no_flap = pygame.transform.scale(bart_no_flap, (w, h))
        self.mask_flap = pygame.mask.from_surface(self.img_flap)
        self.mask_no_flap = pygame.mask.from_surface(self.img_no_flap)
        self.rect.size = (w, h)

    @property
    def mask(self):
        return self.mask_flap if self.using_flap_sprite else self.mask_no_flap

    def jump(self):
        self.vel = self.jump_strength
        self.flap_timer = 0.15

    def update(self, dt, pipes_passed, growth_rate):
        # Apply exponential growth to size and gravity
        diff_scale = (1.0 + growth_rate / 100.0) ** pipes_passed
        new_w = self.base_size * diff_scale
        if abs(new_w - self.width) > 0.01: # Optimization: Only update if size changes
            self.width = new_w
            self.height = self.base_size * diff_scale
            self.gravity = self.base_gravity * diff_scale
            self.update_appearance()

        # Physics
        self.vel += self.gravity * dt
        self.y += self.vel * dt

        if self.flap_timer > 0:
            self.flap_timer -= dt
            self.using_flap_sprite = True
        else:
            self.using_flap_sprite = False

        self.rect.center = (round(self.x), round(self.y))

    def draw(self, surf):
        img = self.img_flap if self.using_flap_sprite else self.img_no_flap
        surf.blit(img, (round(self.rect.x), round(self.rect.y)))

class Pipe:
    def __init__(self, x, y, w, h, is_top):
        self.x_float = float(x)
        self.y = y
        self.w = w
        self.h = h
        self.is_top = is_top
        self.passed = False

        src = max_top_pipe if is_top else max_bot_pipe
        if is_top:
            self.image = src.subsurface((0, LOGICAL_HEIGHT - h, w, h))
        else:
            self.image = src.subsurface((0, 0, w, h))

        self.rect = self.image.get_rect(topleft=(round(self.x_float), self.y))
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, dt, speed):
        self.x_float -= speed * dt
        self.rect.x = round(self.x_float)

    def draw(self, surf):
        surf.blit(self.image, (round(self.rect.x), round(self.rect.y)))

class UIElement:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class Slider(UIElement):
    def __init__(self, x, y, w, label, min_v, max_v, def_v):
        super().__init__(x, y)
        self.w = w
        self.label = label
        self.min_v = min_v
        self.max_v = max_v
        self.val = def_v
        self.rect = pygame.Rect(x, y, w, 10)
        self.dragging = False
        self.handle_rect = pygame.Rect(0, 0, 20, 30)
        self.update_handle()

    def update_handle(self):
        pos = self.x + (self.val - self.min_v) / (self.max_v - self.min_v) * self.w
        self.handle_rect.center = (pos, self.rect.centery)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.handle_rect.collidepoint(event.pos) or self.rect.collidepoint(event.pos):
                self.dragging = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            rel = (event.pos[0] - self.x) / self.w
            rel = max(0, min(1, rel))
            self.val = self.min_v + rel * (self.max_v - self.min_v)
            self.update_handle()

    def draw(self, surf):
        txt = f"{self.label}: {self.val:.2f}"
        draw_text(txt, WHITE, self.x, self.y - 25, font=font_small)
        pygame.draw.rect(surf, (80, 80, 80), self.rect)
        pygame.draw.rect(surf, WHITE, self.handle_rect)

class Checkbox(UIElement):
    def __init__(self, x, y, size, label, initial):
        super().__init__(x, y)
        self.size = size
        self.label = label
        self.val = initial
        self.rect = pygame.Rect(x, y, size, size)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.val = not self.val
                return True
        return False

    def draw(self, surf):
        pygame.draw.rect(surf, WHITE, self.rect, 2)
        if self.val:
            pygame.draw.rect(surf, GREEN, self.rect.inflate(-8, -8))
        draw_text(self.label, WHITE, self.rect.right + 10, self.rect.centery, font=font_small, center=False)

class Button(UIElement):
    def __init__(self, x, y, w, h, text, color=GREEN):
        super().__init__(x, y)
        self.w = w
        self.h = h
        self.text = text
        self.color = color
        self.rect = pygame.Rect(x - w // 2, y - h // 2, w, h)

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

    def draw(self, surf):
        pygame.draw.rect(surf, self.color, self.rect, border_radius=5)
        draw_text(self.text, BLACK, self.rect.centerx, self.rect.centery, font=font_ui, center=True)

def draw_text(text, color, x, y, font=font_main, center=False, max_w=None):
    if max_w and font.size(text)[0] > max_w:
        sz = font.get_height()
        while sz > 10 and get_font(sz, True).size(text)[0] > max_w:
            sz -= 2
        font = get_font(sz, True)

    img = font.render(text, True, color)
    r = img.get_rect()
    if center: r.center = (int(x), int(y))
    else: r.topleft = (int(x), int(y))
    screen.blit(img, r)

def main():
    global highscore
    state = STATE_TITLE
    last_time = time.time()

    # Defaults
    def_speed = 300.0
    def_gap = 150.0
    def_growth = 2.0
    def_vol = 0.5

    # UI Components
    speed_slider = Slider(50, 100, 300, "Pipe Speed", 100, 800, def_speed)
    gap_slider = Slider(50, 175, 300, "Vertical Gap", 100, 300, def_gap)
    growth_slider = Slider(50, 250, 300, "Growth Rate %", 0, 10, def_growth)
    vol_slider = Slider(50, 325, 300, "Music Volume", 0.0, 1.0, def_vol)

    fps_check = Checkbox(50, 380, 25, "Show FPS", config["show_fps"])
    hit_check = Checkbox(220, 380, 25, "Hitboxes", config["show_hitboxes"])

    btn_start = Button(LOGICAL_WIDTH // 2, 320, 160, 50, "Classic Mode")
    btn_debug = Button(50, 30, 80, 30, "Debug", color=(100, 100, 100))
    btn_exit = Button(LOGICAL_WIDTH // 2, 400, 160, 50, "Exit", color=EXIT_RED)
    btn_back = Button(LOGICAL_WIDTH // 2, 500, 120, 40, "Back")
    btn_title = Button(LOGICAL_WIDTH // 2, 480, 180, 50, "Title Screen")
    btn_reset = Button(LOGICAL_WIDTH // 2, 440, 180, 40, "Reset Defaults", color=(150,150,150))

    # Game Session Vars
    bird = Bird(50, LOGICAL_HEIGHT // 2, 30)
    pipes = []
    dist_timer = PIPE_SPAWN_DISTANCE
    score = 0
    pipes_passed = 0
    notify_text = ""
    notify_timer = 0

    def reset_session():
        nonlocal bird, pipes, dist_timer, score, pipes_passed
        bird = Bird(50, LOGICAL_HEIGHT // 2, 30)
        pipes = []
        dist_timer = PIPE_SPAWN_DISTANCE
        score = 0
        pipes_passed = 0

    running = True
    while running:
        # High-precision DT
        now = time.time()
        dt = now - last_time
        last_time = now
        clock.tick(TARGET_FPS)

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f:
                    config["show_fps"] = not config["show_fps"]
                    fps_check.val = config["show_fps"]
                    notify_text = f"FPS: {'ON' if config['show_fps'] else 'OFF'}"
                    notify_timer = 120
                    save_config(config)
                if event.key == pygame.K_h:
                    config["show_hitboxes"] = not config["show_hitboxes"]
                    hit_check.val = config["show_hitboxes"]
                    notify_text = f"Hitboxes: {'ON' if config['show_hitboxes'] else 'OFF'}"
                    notify_timer = 120
                    save_config(config)

        if state == STATE_TITLE:
            for event in events:
                if btn_start.is_clicked(event):
                    reset_session()
                    state = STATE_PLAYING
                if btn_debug.is_clicked(event): state = STATE_DEBUG
                if btn_exit.is_clicked(event): running = False

            screen.fill(BLACK)
            if background_img: screen.blit(background_img, (0,0))
            draw_text("Flabby Bartholomew", WHITE, LOGICAL_WIDTH // 2, 160, font=font_title, center=True, max_w=360)
            draw_text(f"High Score: {highscore}", YELLOW, LOGICAL_WIDTH // 2, 230, font=font_small, center=True)
            btn_start.draw(screen)
            btn_exit.draw(screen)
            btn_debug.draw(screen)

        elif state == STATE_DEBUG:
            for event in events:
                speed_slider.handle_event(event)
                gap_slider.handle_event(event)
                growth_slider.handle_event(event)
                vol_slider.handle_event(event)
                if fps_check.handle_event(event):
                    config["show_fps"] = fps_check.val
                    save_config(config)
                if hit_check.handle_event(event):
                    config["show_hitboxes"] = hit_check.val
                    save_config(config)
                if btn_reset.is_clicked(event):
                    speed_slider.val = def_speed; speed_slider.update_handle()
                    gap_slider.val = def_gap; gap_slider.update_handle()
                    growth_slider.val = def_growth; growth_slider.update_handle()
                    vol_slider.val = def_vol; vol_slider.update_handle()
                if btn_back.is_clicked(event): state = STATE_TITLE

            pygame.mixer.music.set_volume(vol_slider.val)
            screen.fill(BLACK)
            draw_text("Debug Menu", WHITE, LOGICAL_WIDTH // 2, 40, font=font_title, center=True)
            speed_slider.draw(screen)
            gap_slider.draw(screen)
            growth_slider.draw(screen)
            vol_slider.draw(screen)
            fps_check.draw(screen)
            hit_check.draw(screen)
            btn_reset.draw(screen)
            btn_back.draw(screen)

        elif state == STATE_PLAYING:
            for event in events:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    bird.jump()

            bird.update(dt, pipes_passed, growth_slider.val)

            dist_timer += speed_slider.val * dt
            if dist_timer >= PIPE_SPAWN_DISTANCE:
                gap = gap_slider.val
                h = random.randint(50, LOGICAL_HEIGHT - int(gap) - 50)
                pipes.append(Pipe(LOGICAL_WIDTH, 0, PIPE_WIDTH, h, True))
                pipes.append(Pipe(LOGICAL_WIDTH, h + int(gap), PIPE_WIDTH, LOGICAL_HEIGHT - h - int(gap), False))
                dist_timer = 0

            for p in pipes:
                p.update(dt, speed_slider.val)
                if not p.passed and bird.x > p.rect.right:
                    p.passed = True
                    if p.is_top:
                        score += 1
                        pipes_passed += 1

            pipes = [p for p in pipes if p.rect.right > 0]

            # Collision
            for p in pipes:
                if bird.mask.overlap(p.mask, (p.rect.x - bird.rect.x, p.rect.y - bird.rect.y)):
                    state = STATE_GAME_OVER
            if bird.rect.top < 0 or bird.rect.bottom > LOGICAL_HEIGHT:
                state = STATE_GAME_OVER

            if state == STATE_GAME_OVER:
                if score > highscore:
                    highscore = score
                    save_highscore(highscore)

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
                if btn_title.is_clicked(event): state = STATE_TITLE

            screen.fill(BLACK)
            draw_text("GAME OVER", WHITE, LOGICAL_WIDTH // 2, 200, font=font_title, center=True)
            draw_text(f"Score: {score}", WHITE, LOGICAL_WIDTH // 2, 280, font=font_main, center=True)
            draw_text(f"High Score: {highscore}", YELLOW, LOGICAL_WIDTH // 2, 330, font=font_small, center=True)
            btn_title.draw(screen)

        # Notifications
        if notify_timer > 0:
            draw_text(notify_text, YELLOW, 10, LOGICAL_HEIGHT - 30, font=font_small)
            notify_timer -= 1

        if config["show_fps"]:
            fps_img = font_small.render(f"FPS: {int(clock.get_fps())}", True, WHITE)
            screen.blit(fps_img, (LOGICAL_WIDTH - fps_img.get_width() - 10, 10))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
