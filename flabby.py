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
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
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
    base_pipe = pygame.transform.scale(base_pipe, (pipe_scaled_width, pipe_scaled_height))

    # Slice pipe: Cap (top 20%) and Body (a 1px slice from the body)
    cap_height = int(pipe_scaled_height * 0.20)
    pipe_cap = base_pipe.subsurface((0, 0, pipe_scaled_width, cap_height))
    # Using row at 90% height to avoid potential transparent pixels at the very bottom
    body_row_y = int(pipe_scaled_height * 0.90)
    pipe_body = base_pipe.subsurface((0, body_row_y, pipe_scaled_width, 1))

    # Flipped versions for top pipes
    pipe_cap_flipped = pygame.transform.flip(pipe_cap, False, True)
    pipe_body_flipped = pygame.transform.flip(pipe_body, False, True)

except pygame.error as e:
    print(f"Error loading assets: {e}")
    sys.exit()

# Fonts
def create_pipe_mask(width, height, is_top, cap_img, body_img):
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    cap_h = cap_img.get_height()
    if is_top:
        # Body (stretched)
        body_h = height - cap_h
        if body_h > 0:
            stretched_body = pygame.transform.scale(body_img, (width, body_h))
            surf.blit(stretched_body, (0, 0))
        # Cap
        surf.blit(cap_img, (0, max(0, body_h)))
    else:
        # Cap
        surf.blit(cap_img, (0, 0))
        # Body (stretched)
        body_h = height - cap_h
        if body_h > 0:
            stretched_body = pygame.transform.scale(body_img, (width, body_h))
            surf.blit(stretched_body, (0, cap_h))
    return pygame.mask.from_surface(surf)

def get_font(size, bold=False, scale=True):
    if scale:
        return pygame.font.SysFont('Arial', int(size * SCALE_FACTOR), bold=bold)
    else:
        return pygame.font.SysFont('Arial', int(size), bold=bold)

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
        # Shrink font to fit
        current_size = font_title_size # Start with title size or current font size?
        # Actually, let's just use the font passed in and decrease it.
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
                    # Only allow digits and decimal point
                    if event.unicode.isdigit() or event.unicode == '.':
                        self.text += event.unicode

    def draw(self, surface):
        # Draw label
        label_img = self.font.render(self.label, True, WHITE)
        surface.blit(label_img, (self.rect.x, self.rect.y - 30))

        # Draw box
        pygame.draw.rect(surface, self.color, self.rect, 2)

        # Draw text
        text_img = self.font.render(self.text, True, WHITE)
        surface.blit(text_img, (self.rect.x + 5, self.rect.y + 15))

    def get_value(self):
        try:
            return float(self.text)
        except ValueError:
            return None

def main():
    # Game state variables
    state = STATE_TITLE
    previous_state = STATE_TITLE

    # Starting mechanics (can be changed in debug)
    start_gravity = 0.5 * SCALE_FACTOR
    start_bird_size = 30 * SCALE_FACTOR
    start_pipe_speed = PIPE_SPEED

    # Bird variables
    bird_x = 50 * SCALE_FACTOR
    bird_y = SCREEN_HEIGHT // 2
    bird_width = start_bird_size
    bird_height = start_bird_size
    bird_vel = 0
    gravity = start_gravity
    jump_strength = -8 * SCALE_FACTOR
    flap_timer = 0
    using_flap_sprite = False

    # Pipe variables
    pipes = [] # Each element is [top_rect, bottom_rect, passed]
    last_pipe_time = pygame.time.get_ticks()
    current_pipe_speed = start_pipe_speed

    score = 0
    running = True

    # Buttons and Inputs (Fixed size 200x60, relative positions)
    btn_w, btn_h = 200, 60
    start_button = Button(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, btn_w, btn_h, "Start")
    exit_button = Button(SCREEN_WIDTH // 2, (SCREEN_HEIGHT // 2) + 100, btn_w, btn_h, "Exit", color=EXIT_RED)
    title_button = Button(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, btn_w + 100, btn_h, "Back to Title Screen")
    close_button = Button(SCREEN_WIDTH // 2, (SCREEN_HEIGHT // 2) + 100, btn_w, btn_h, "Close", color=EXIT_RED)

    # Debug inputs on the left side
    gravity_input = TextInput(50, 250, 200, 40, "Gravity", round(gravity, 3))
    size_input = TextInput(50, 350, 200, 40, "Bird Size", int(bird_width))
    speed_input = TextInput(50, 450, 200, 40, "Pipe Speed", int(current_pipe_speed))

    def reset_game():
        nonlocal bird_y, bird_width, bird_height, bird_vel, gravity, pipes, score, last_pipe_time, flap_timer, using_flap_sprite, current_pipe_speed
        bird_y = SCREEN_HEIGHT // 2
        bird_width = start_bird_size
        bird_height = start_bird_size
        bird_vel = 0
        gravity = start_gravity
        pipes = []
        score = 0
        last_pipe_time = pygame.time.get_ticks()
        flap_timer = 0
        using_flap_sprite = False
        current_pipe_speed = start_pipe_speed

    while running:
        current_time = pygame.time.get_ticks()
        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()


        if state == STATE_TITLE:
            for event in events:
                gravity_input.handle_event(event)
                size_input.handle_event(event)
                speed_input.handle_event(event)

                if start_button.is_clicked(event):
                    # Update starting values from inputs
                    val = gravity_input.get_value()
                    if val is not None: start_gravity = val
                    val = size_input.get_value()
                    if val is not None: start_bird_size = val
                    val = speed_input.get_value()
                    if val is not None: start_pipe_speed = val

                    reset_game()
                    state = STATE_PLAYING
                if exit_button.is_clicked(event):
                    pygame.quit()
                    sys.exit()

            screen.fill(BLACK)
            draw_text("Flabby Bartholomew", WHITE, SCREEN_WIDTH // 2, int(SCREEN_HEIGHT * 0.2), font=font_title, center=True, max_width=SCREEN_WIDTH - 20 * SCALE_FACTOR)
            start_button.draw(screen)
            exit_button.draw(screen)

            # Draw debug inputs
            gravity_input.draw(screen)
            size_input.draw(screen)
            speed_input.draw(screen)

            pygame.display.flip()

        elif state == STATE_PLAYING:
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        bird_vel = jump_strength
                        flap_timer = 0.15 # seconds

            # Bird physics
            bird_vel += gravity
            bird_y += bird_vel

            # Animation
            if flap_timer > 0:
                flap_timer -= 1/FPS
                using_flap_sprite = True
            else:
                using_flap_sprite = False

            # Pipe spawning
            if current_time - last_pipe_time > PIPE_FREQUENCY:
                pipe_height = random.randint(50, SCREEN_HEIGHT - PIPE_GAP - 50)
                top_rect = pygame.Rect(SCREEN_WIDTH, 0, PIPE_WIDTH, pipe_height)
                bottom_rect = pygame.Rect(SCREEN_WIDTH, pipe_height + PIPE_GAP, PIPE_WIDTH, SCREEN_HEIGHT - pipe_height - PIPE_GAP)

                # Create masks for pixel-perfect collision
                top_mask = create_pipe_mask(PIPE_WIDTH, pipe_height, True, pipe_cap_flipped, pipe_body_flipped)
                bottom_mask = create_pipe_mask(PIPE_WIDTH, SCREEN_HEIGHT - pipe_height - PIPE_GAP, False, pipe_cap, pipe_body)

                pipes.append({
                    "top_rect": top_rect,
                    "bottom_rect": bottom_rect,
                    "top_mask": top_mask,
                    "bottom_mask": bottom_mask,
                    "passed": False
                })
                last_pipe_time = current_time

            # Move pipes (using floats for smooth movement, but here they are ints)
            for p in pipes:
                p["top_rect"].x -= int(current_pipe_speed)
                p["bottom_rect"].x -= int(current_pipe_speed)

            # Remove off-screen pipes
            pipes = [p for p in pipes if p["top_rect"].right > 0]

            # Prepare bird sprite and mask
            current_bird_sprite = bart_flap if using_flap_sprite else bart_no_flap
            scaled_bird = pygame.transform.scale(current_bird_sprite, (int(bird_width), int(bird_height)))

            # Rotate bird based on velocity
            bird_rotation = -bird_vel * 3
            bird_rotation = max(-90, min(bird_rotation, 30))
            rotated_bird = pygame.transform.rotate(scaled_bird, bird_rotation)
            rotated_rect = rotated_bird.get_rect(center=(int(bird_x + bird_width // 2), int(bird_y + bird_height // 2)))
            bird_mask = pygame.mask.from_surface(rotated_bird)

            # Collision detection (Mask-based)
            for p in pipes:
                # Top pipe
                top_offset = (p["top_rect"].x - rotated_rect.x, p["top_rect"].y - rotated_rect.y)
                if bird_mask.overlap(p["top_mask"], top_offset):
                    state = STATE_GAME_OVER
                # Bottom pipe
                bottom_offset = (p["bottom_rect"].x - rotated_rect.x, p["bottom_rect"].y - rotated_rect.y)
                if bird_mask.overlap(p["bottom_mask"], bottom_offset):
                    state = STATE_GAME_OVER

            if rotated_rect.top < 0 or rotated_rect.bottom > SCREEN_HEIGHT:
                state = STATE_GAME_OVER

            # Scoring and Growth
            for p in pipes:
                if not p["passed"] and bird_x > p["top_rect"].right:
                    p["passed"] = True
                    score += 1
                    # Growth: 5% larger, 5% heavier (proportional)
                    bird_width *= 1.05
                    bird_height *= 1.05
                    gravity *= 1.05

            # Draw
            screen.fill(BLACK)

            # Draw pipes (using int() for coordinates)
            for p in pipes:
                tr = p["top_rect"]
                br = p["bottom_rect"]

                # Draw top pipe
                body_h_top = tr.height - cap_height
                if body_h_top > 0:
                    stretched_body_top = pygame.transform.scale(pipe_body_flipped, (PIPE_WIDTH, int(body_h_top)))
                    screen.blit(stretched_body_top, (int(tr.x), int(tr.top)))
                screen.blit(pipe_cap_flipped, (int(tr.x), int(tr.bottom - cap_height)))

                # Draw bottom pipe
                screen.blit(pipe_cap, (int(br.x), int(br.top)))
                body_h_bottom = br.height - cap_height
                if body_h_bottom > 0:
                    stretched_body_bottom = pygame.transform.scale(pipe_body, (PIPE_WIDTH, int(body_h_bottom)))
                    screen.blit(stretched_body_bottom, (int(br.x), int(br.top + cap_height)))

            # Draw bird
            screen.blit(rotated_bird, rotated_rect.topleft)

            draw_text(f"Score: {score}", WHITE, 10 * SCALE_FACTOR, 10 * SCALE_FACTOR, font=font_small)
            pygame.display.flip()

        elif state == STATE_GAME_OVER:
            for event in events:
                if title_button.is_clicked(event):
                    state = STATE_TITLE

            screen.fill(BLACK)
            draw_text("GAME OVER", WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100 * SCALE_FACTOR, center=True)
            draw_text(f"Final Score: {score}", WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50 * SCALE_FACTOR, center=True)
            title_button.draw(screen)
            pygame.display.flip()


        clock.tick(FPS)

if __name__ == "__main__":
    main()
