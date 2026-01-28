import pygame
import sys
import random

# Initialize Pygame
pygame.init()

# Constants
SCALE_FACTOR = 3
SCREEN_WIDTH = 400 * SCALE_FACTOR
SCREEN_HEIGHT = 600 * SCALE_FACTOR
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
def get_font(size, bold=False):
    return pygame.font.SysFont('Arial', int(size * SCALE_FACTOR), bold=bold)

font_main_size = 36
font_small_size = 24
font_title_size = 48

font_main = get_font(font_main_size, bold=True)
font_small = get_font(font_small_size)
font_title = get_font(font_title_size, bold=True)

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
        rect = img.get_rect(center=(x, y))
        screen.blit(img, rect)
    else:
        screen.blit(img, (x, y))

class Button:
    def __init__(self, x, y, width, height, text, color=GREEN, text_color=BLACK, font=font_main):
        self.rect = pygame.Rect(x - width // 2, y - height // 2, width, height)
        self.text = text
        self.color = color
        self.text_color = text_color
        self.font = font

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect, border_radius=int(5 * SCALE_FACTOR))
        text_img = self.font.render(self.text, True, self.text_color)
        text_rect = text_img.get_rect(center=self.rect.center)
        surface.blit(text_img, text_rect)

    def is_clicked(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                return True
        return False

class TextInput:
    def __init__(self, x, y, width, height, label, initial_value, font=font_small):
        self.rect = pygame.Rect(x, y, width, height)
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
        surface.blit(label_img, (self.rect.x, self.rect.y - 25 * SCALE_FACTOR))

        # Draw box
        pygame.draw.rect(surface, self.color, self.rect, int(2 * SCALE_FACTOR))

        # Draw text
        text_img = self.font.render(self.text, True, WHITE)
        surface.blit(text_img, (self.rect.x + 5 * SCALE_FACTOR, self.rect.y + 5 * SCALE_FACTOR))

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

    # Buttons and Inputs
    start_button = Button(SCREEN_WIDTH // 2, 400 * SCALE_FACTOR, 150 * SCALE_FACTOR, 50 * SCALE_FACTOR, "Start")
    exit_button = Button(SCREEN_WIDTH // 2, 500 * SCALE_FACTOR, 150 * SCALE_FACTOR, 50 * SCALE_FACTOR, "Exit", color=EXIT_RED)
    title_button = Button(SCREEN_WIDTH // 2, 450 * SCALE_FACTOR, 250 * SCALE_FACTOR, 50 * SCALE_FACTOR, "Back to Title Screen")
    close_button = Button(SCREEN_WIDTH // 2, 500 * SCALE_FACTOR, 150 * SCALE_FACTOR, 50 * SCALE_FACTOR, "Close", color=EXIT_RED)

    gravity_input = TextInput(100 * SCALE_FACTOR, 150 * SCALE_FACTOR, 200 * SCALE_FACTOR, 40 * SCALE_FACTOR, "Gravity", gravity)
    size_input = TextInput(100 * SCALE_FACTOR, 250 * SCALE_FACTOR, 200 * SCALE_FACTOR, 40 * SCALE_FACTOR, "Bird Size", bird_width)
    speed_input = TextInput(100 * SCALE_FACTOR, 350 * SCALE_FACTOR, 200 * SCALE_FACTOR, 40 * SCALE_FACTOR, "Pipe Speed", current_pipe_speed)

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

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_d:
                    if state != STATE_DEBUG:
                        previous_state = state
                        state = STATE_DEBUG
                        # Sync inputs with current values
                        gravity_input.text = str(round(gravity, 3))
                        size_input.text = str(round(bird_width, 1))
                        speed_input.text = str(round(current_pipe_speed, 1))
                    else:
                        state = previous_state

        if state == STATE_TITLE:
            for event in events:
                if start_button.is_clicked(event):
                    reset_game()
                    state = STATE_PLAYING
                if exit_button.is_clicked(event):
                    pygame.quit()
                    sys.exit()

            screen.fill(BLACK)
            draw_text("Flabby Bartholomew", WHITE, SCREEN_WIDTH // 2, 150 * SCALE_FACTOR, font=font_title, center=True, max_width=SCREEN_WIDTH - 20 * SCALE_FACTOR)
            start_button.draw(screen)
            exit_button.draw(screen)
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
                top_pipe = pygame.Rect(SCREEN_WIDTH, 0, PIPE_WIDTH, pipe_height)
                bottom_pipe = pygame.Rect(SCREEN_WIDTH, pipe_height + PIPE_GAP, PIPE_WIDTH, SCREEN_HEIGHT - pipe_height - PIPE_GAP)
                pipes.append([top_pipe, bottom_pipe, False])
                last_pipe_time = current_time

            # Move pipes
            for pipe_pair in pipes:
                pipe_pair[0].x -= current_pipe_speed
                pipe_pair[1].x -= current_pipe_speed

            # Remove off-screen pipes
            pipes = [p for p in pipes if p[0].right > 0]

            # Collision detection
            bird_rect = pygame.Rect(bird_x, bird_y, bird_width, bird_height)
            for pipe_pair in pipes:
                if bird_rect.colliderect(pipe_pair[0]) or bird_rect.colliderect(pipe_pair[1]):
                    state = STATE_GAME_OVER

            if bird_y < 0 or bird_y + bird_height > SCREEN_HEIGHT:
                state = STATE_GAME_OVER

            # Scoring and Growth
            for pipe_pair in pipes:
                if not pipe_pair[2] and bird_x > pipe_pair[0].right:
                    pipe_pair[2] = True
                    score += 1
                    # Growth: 5% larger, 10% heavier
                    bird_width *= 1.05
                    bird_height *= 1.05
                    gravity *= 1.10

            # Draw
            screen.fill(BLACK)

            # Draw pipes
            for pipe_pair in pipes:
                top_rect, bottom_rect, _ = pipe_pair

                # Draw top pipe
                # Body (stretched)
                body_height_top = top_rect.height - cap_height
                if body_height_top > 0:
                    stretched_body_top = pygame.transform.scale(pipe_body_flipped, (PIPE_WIDTH, body_height_top))
                    screen.blit(stretched_body_top, (top_rect.x, top_rect.top))
                # Cap
                screen.blit(pipe_cap_flipped, (top_rect.x, top_rect.bottom - cap_height))

                # Draw bottom pipe
                # Cap
                screen.blit(pipe_cap, (bottom_rect.x, bottom_rect.top))
                # Body (stretched)
                body_height_bottom = bottom_rect.height - cap_height
                if body_height_bottom > 0:
                    stretched_body_bottom = pygame.transform.scale(pipe_body, (PIPE_WIDTH, body_height_bottom))
                    screen.blit(stretched_body_bottom, (bottom_rect.x, bottom_rect.top + cap_height))

            # Draw bird
            current_bird_sprite = bart_flap if using_flap_sprite else bart_no_flap
            scaled_bird = pygame.transform.scale(current_bird_sprite, (int(bird_width), int(bird_height)))
            screen.blit(scaled_bird, (bird_x, bird_y))

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

        elif state == STATE_DEBUG:
            for event in events:
                gravity_input.handle_event(event)
                size_input.handle_event(event)
                speed_input.handle_event(event)

                if close_button.is_clicked(event):
                    state = previous_state

                # Apply changes immediately to current and starting values
                new_gravity = gravity_input.get_value()
                if new_gravity is not None:
                    gravity = new_gravity
                    start_gravity = new_gravity

                new_size = size_input.get_value()
                if new_size is not None:
                    bird_width = new_size
                    bird_height = new_size
                    start_bird_size = new_size

                new_speed = speed_input.get_value()
                if new_speed is not None:
                    current_pipe_speed = new_speed
                    start_pipe_speed = new_speed

            screen.fill(BLACK)
            draw_text("DEBUG MENU", WHITE, SCREEN_WIDTH // 2, 50 * SCALE_FACTOR, center=True)

            gravity_input.draw(screen)
            size_input.draw(screen)
            speed_input.draw(screen)

            close_button.draw(screen)
            draw_text("Press 'D' to Resume", WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30 * SCALE_FACTOR, font=font_small, center=True)
            pygame.display.flip()

        clock.tick(FPS)

if __name__ == "__main__":
    main()
