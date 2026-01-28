import pygame
import sys
import random

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 400
SCREEN_HEIGHT = 600
FPS = 60
PIPE_WIDTH = 60
PIPE_GAP = 150
PIPE_SPEED = 3
PIPE_FREQUENCY = 1500 # milliseconds

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)

# Set up display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Flabby Bird")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 36)

def draw_text(text, color, x, y):
    img = font.render(text, True, color)
    screen.blit(img, (x, y))

def main():
    # Bird variables
    bird_x = 50
    bird_y = 300
    bird_width = 30
    bird_height = 30
    bird_vel = 0
    gravity = 0.5
    jump_strength = -8

    # Pipe variables
    pipes = [] # Each element is [top_rect, bottom_rect, passed]
    last_pipe_time = pygame.time.get_ticks()

    score = 0

    running = True
    game_over = False

    while running:
        current_time = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and not game_over:
                    bird_vel = jump_strength
                if event.key == pygame.K_r and game_over:
                    # Reset variables
                    bird_y = 300
                    bird_width = 30
                    bird_height = 30
                    bird_vel = 0
                    gravity = 0.5
                    pipes = []
                    score = 0
                    game_over = False
                    last_pipe_time = pygame.time.get_ticks()

        if not game_over:
            # Bird physics
            bird_vel += gravity
            bird_y += bird_vel

            # Pipe spawning
            if current_time - last_pipe_time > PIPE_FREQUENCY:
                pipe_height = random.randint(50, SCREEN_HEIGHT - PIPE_GAP - 50)
                top_pipe = pygame.Rect(SCREEN_WIDTH, 0, PIPE_WIDTH, pipe_height)
                bottom_pipe = pygame.Rect(SCREEN_WIDTH, pipe_height + PIPE_GAP, PIPE_WIDTH, SCREEN_HEIGHT - pipe_height - PIPE_GAP)
                pipes.append([top_pipe, bottom_pipe, False])
                last_pipe_time = current_time

            # Move pipes
            for pipe_pair in pipes:
                pipe_pair[0].x -= PIPE_SPEED
                pipe_pair[1].x -= PIPE_SPEED

            # Remove off-screen pipes
            pipes = [p for p in pipes if p[0].right > 0]

        # Collision detection
        bird_rect = pygame.Rect(bird_x, bird_y, bird_width, bird_height)
        if not game_over:
            for pipe_pair in pipes:
                if bird_rect.colliderect(pipe_pair[0]) or bird_rect.colliderect(pipe_pair[1]):
                    game_over = True

            if bird_y < 0 or bird_y + bird_height > SCREEN_HEIGHT:
                game_over = True

            # Scoring and Growth
            for pipe_pair in pipes:
                if not pipe_pair[2] and bird_x > pipe_pair[0].right:
                    pipe_pair[2] = True
                    score += 1
                    # Growth: 5% larger, 10% heavier
                    bird_width *= 1.05
                    bird_height *= 1.05
                    gravity *= 1.10

        # Draw everything
        screen.fill(BLACK)

        # Draw pipes
        for pipe_pair in pipes:
            pygame.draw.rect(screen, GREEN, pipe_pair[0])
            pygame.draw.rect(screen, GREEN, pipe_pair[1])

        # Draw bird
        bird_rect = pygame.Rect(bird_x, bird_y, bird_width, bird_height)
        pygame.draw.rect(screen, YELLOW, bird_rect)

        # Draw score
        draw_text(f"Score: {score}", WHITE, 10, 10)

        if game_over:
            draw_text("GAME OVER", WHITE, SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT // 2 - 50)
            draw_text(f"Final Score: {score}", WHITE, SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT // 2)
            draw_text("Press 'R' to Restart", WHITE, SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 50)

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
