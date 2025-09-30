# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "click>=8.0.0",
# ]
# ///

# MIT License
#
# Copyright (c) 2025 UVPY.RUN
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Third-party Dependencies:
# - Click: BSD-3-Clause License (https://github.com/pallets/click)
# - Tkinter: Python Software Foundation License (built-in Python library)

"""
Classic Breakout/Brick Breaker Game

A modern implementation of the classic Breakout game using Tkinter.
Features special bricks with power-ups, multiple difficulty levels,
and smooth ball physics with paddle collision detection.

Version: 0.9.0
Category: Game
Author: UVPY.RUN

Usage Examples:
    uv run brick.py
    uv run brick.py --difficulty hard --speed 1.5
    uv run brick.py -d easy -s 0.8 -c 0.3

Game Controls:
    - LEFT/RIGHT Arrow Keys: Move paddle
    - SPACE: Start game
    - Game automatically restarts after win/loss

Special Bricks:
    - M (Multi Ball): Creates additional balls
    - S (Speed Up): Increases ball speed
    - E (Expand Paddle): Makes paddle larger
    - + (Extra Life): Adds one life
    - $ (Bonus Score): Gives extra points

Game Elements:
    - Blue rectangle: Paddle
    - White circle: Ball
    - Colored rectangles: Bricks
    - Special markers: Power-up indicators
"""

import tkinter as tk
from tkinter import messagebox
import random
import math
import click
from typing import List, Tuple, Optional, Set
from enum import Enum

class BrickType(Enum):
    """
    Enumeration for different types of bricks with special effects
    
    Each brick type provides different power-ups or bonuses when destroyed:
    - NORMAL: Standard brick, gives basic score
    - MULTI_BALL: Creates additional balls
    - SPEED_UP: Increases ball speed
    - EXPAND_PADDLE: Makes paddle larger
    - EXTRA_LIFE: Adds one life
    - BONUS_SCORE: Gives extra points
    """
    NORMAL = "normal"
    MULTI_BALL = "multi_ball"
    SPEED_UP = "speed_up"
    EXPAND_PADDLE = "expand_paddle"
    EXTRA_LIFE = "extra_life"
    BONUS_SCORE = "bonus_score"

class Ball:
    """
    Game ball class that handles ball physics and rendering
    
    The ball moves continuously, bounces off walls and paddle,
    and can be destroyed when it goes off screen.
    """
    def __init__(self, canvas: tk.Canvas, x: float, y: float, radius: int = 8, speed_multiplier: float = 1.0):
        """
        Initialize a new ball
        
        Args:
            canvas: Tkinter canvas to draw on
            x, y: Initial position coordinates
            radius: Ball radius in pixels
            speed_multiplier: Speed scaling factor
        """
        self.canvas = canvas
        self.x = x
        self.y = y
        self.radius = radius
        self.base_speed = 5 * speed_multiplier
        # Random horizontal direction, always moving up initially
        self.dx = random.choice([-1, 1]) * self.base_speed
        self.dy = -self.base_speed
        # Create visual representation
        self.ball_id = canvas.create_oval(
            x - radius, y - radius, x + radius, y + radius,
            fill="white", outline="gray", width=2
        )
    
    def move(self) -> None:
        """Update ball position and visual representation"""
        self.x += self.dx
        self.y += self.dy
        # Update the visual position on canvas
        self.canvas.coords(
            self.ball_id,
            self.x - self.radius, self.y - self.radius,
            self.x + self.radius, self.y + self.radius
        )
    
    def bounce_x(self) -> None:
        """Reverse horizontal direction (bounce off vertical surfaces)"""
        self.dx = -self.dx
    
    def bounce_y(self) -> None:
        """Reverse vertical direction (bounce off horizontal surfaces)"""
        self.dy = -self.dy
    
    def speed_up(self, factor: float = 1.2) -> None:
        """
        Increase ball speed by multiplying velocity components
        
        Args:
            factor: Speed multiplication factor (default 1.2 = 20% faster)
        """
        self.dx *= factor
        self.dy *= factor
    
    def destroy(self) -> None:
        """Remove ball from canvas"""
        self.canvas.delete(self.ball_id)
    
    def get_bounds(self) -> Tuple[float, float, float, float]:
        """
        Get ball bounding box for collision detection
        
        Returns:
            Tuple of (left, top, right, bottom) coordinates
        """
        return (
            self.x - self.radius,
            self.y - self.radius,
            self.x + self.radius,
            self.y + self.radius
        )

class Paddle:
    """
    Player-controlled paddle class
    
    The paddle moves horizontally to bounce the ball and prevent it
    from falling off the bottom of the screen.
    """
    def __init__(self, canvas: tk.Canvas, x: float, y: float, width: int = 120, height: int = 15, speed_multiplier: float = 1.0):
        """
        Initialize the paddle
        
        Args:
            canvas: Tkinter canvas to draw on
            x, y: Initial center position
            width, height: Paddle dimensions
            speed_multiplier: Movement speed scaling factor
        """
        self.canvas = canvas
        self.x = x
        self.y = y
        self.original_width = width  # Store original size for reset
        self.width = width
        self.height = height
        self.speed = 12 * speed_multiplier  # Movement speed
        # Create visual representation
        self.paddle_id = canvas.create_rectangle(
            x - width//2, y - height//2,
            x + width//2, y + height//2,
            fill="blue", outline="darkblue", width=2
        )
    
    def move_left(self) -> None:
        """Move paddle left, respecting left boundary"""
        if self.x - self.width//2 > 0:  # Check left boundary
            self.x -= self.speed
            self.update_position()
    
    def move_right(self, canvas_width: int) -> None:
        """
        Move paddle right, respecting right boundary
        
        Args:
            canvas_width: Width of the game canvas for boundary checking
        """
        if self.x + self.width//2 < canvas_width:  # Check right boundary
            self.x += self.speed
            self.update_position()
    
    def expand(self, factor: float = 1.5) -> None:
        """
        Expand paddle size (power-up effect)
        
        Args:
            factor: Size multiplication factor (default 1.5 = 50% larger)
        """
        self.width = min(200, self.original_width * factor)  # Cap maximum size
        self.update_position()
    
    def reset_size(self) -> None:
        """Reset paddle to original size"""
        self.width = self.original_width
        self.update_position()
    
    def update_position(self) -> None:
        """Update paddle visual position on canvas"""
        self.canvas.coords(
            self.paddle_id,
            self.x - self.width//2, self.y - self.height//2,
            self.x + self.width//2, self.y + self.height//2
        )
    
    def get_bounds(self) -> Tuple[float, float, float, float]:
        """
        Get paddle bounding box for collision detection
        
        Returns:
            Tuple of (left, top, right, bottom) coordinates
        """
        return (
            self.x - self.width//2,
            self.y - self.height//2,
            self.x + self.width//2,
            self.y + self.height//2
        )

class Brick:
    """
    Brick class representing destructible blocks
    
    Bricks can be normal or special types with different colors
    and power-up effects when destroyed.
    """
    def __init__(self, canvas: tk.Canvas, x: float, y: float, width: int = 60, height: int = 20, brick_type: BrickType = BrickType.NORMAL):
        """
        Initialize a brick
        
        Args:
            canvas: Tkinter canvas to draw on
            x, y: Top-left corner position
            width, height: Brick dimensions
            brick_type: Type of brick (normal or special)
        """
        self.canvas = canvas
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.brick_type = brick_type
        self.destroyed = False
        
        # Set color and style based on brick type
        self.color, self.outline = self._get_brick_style()
        
        # Create visual representation
        self.brick_id = canvas.create_rectangle(
            x, y, x + width, y + height,
            fill=self.color, outline=self.outline, width=2
        )
        
        # Add special marker for non-normal bricks
        if brick_type != BrickType.NORMAL:
            self._add_special_marker()
    
    def _get_brick_style(self) -> Tuple[str, str]:
        """
        Get color scheme based on brick type
        
        Returns:
            Tuple of (fill_color, outline_color) for the brick
        """
        styles = {
            BrickType.NORMAL: (random.choice(["red", "orange", "yellow", "green", "blue", "purple"]), "black"),
            BrickType.MULTI_BALL: ("gold", "darkgoldenrod"),
            BrickType.SPEED_UP: ("crimson", "darkred"),
            BrickType.EXPAND_PADDLE: ("cyan", "darkturquoise"),
            BrickType.EXTRA_LIFE: ("lime", "darkgreen"),
            BrickType.BONUS_SCORE: ("magenta", "darkmagenta"),
        }
        return styles[self.brick_type]
    
    def _add_special_marker(self) -> None:
        """Add text marker to identify special brick types"""
        center_x = self.x + self.width // 2
        center_y = self.y + self.height // 2
        
        # Text markers for each special brick type
        markers = {
            BrickType.MULTI_BALL: "M",      # Multi Ball
            BrickType.SPEED_UP: "S",        # Speed Up
            BrickType.EXPAND_PADDLE: "E",   # Expand Paddle
            BrickType.EXTRA_LIFE: "+",      # Extra Life
            BrickType.BONUS_SCORE: "$",     # Bonus Score
        }
        
        if self.brick_type in markers:
            self.marker_id = self.canvas.create_text(
                center_x, center_y, text=markers[self.brick_type],
                fill="white", font=("Arial", 8, "bold")
            )
    
    def destroy(self) -> None:
        """Remove brick from canvas and mark as destroyed"""
        if not self.destroyed:
            self.canvas.delete(self.brick_id)
            # Remove marker if it exists
            if hasattr(self, 'marker_id'):
                self.canvas.delete(self.marker_id)
            self.destroyed = True
    
    def get_bounds(self) -> Tuple[float, float, float, float]:
        """
        Get brick bounding box for collision detection
        
        Returns:
            Tuple of (left, top, right, bottom) coordinates
        """
        return (self.x, self.y, self.x + self.width, self.y + self.height)

class BreakoutGame:
    """
    Main Breakout game class
    
    Manages the complete game including physics, collision detection,
    special effects, and user interface. Supports multiple difficulty
    levels and customizable game parameters.
    """
    def __init__(self, difficulty: str = "normal", speed_multiplier: float = 1.0, special_brick_chance: float = 0.15):
        """
        Initialize the Breakout game
        
        Args:
            difficulty: Game difficulty level (easy/normal/hard)
            speed_multiplier: Speed scaling factor for game objects
            special_brick_chance: Probability of special bricks (0.0-1.0)
        """
        # Create main window
        self.root = tk.Tk()
        self.root.title(f"Breakout Game - {difficulty.title()} Mode")
        self.root.resizable(False, False)
        
        # Set up game canvas
        self.canvas_width = 800
        self.canvas_height = 600
        self.canvas = tk.Canvas(
            self.root,
            width=self.canvas_width,
            height=self.canvas_height,
            bg="black"
        )
        self.canvas.pack()
        
        # Store game parameters
        self.difficulty = difficulty
        self.speed_multiplier = speed_multiplier
        self.special_brick_chance = special_brick_chance
        
        # Initialize game state
        self.score = 0
        self.lives = 3
        self.game_running = False
        
        # Track pressed keys for smooth movement
        self.pressed_keys: Set[str] = set()
        
        # Game object collections
        self.balls: List[Ball] = []
        self.bricks: List[Brick] = []
        
        # Create UI text elements
        self.score_text = self.canvas.create_text(
            50, 20, text=f"Score: {self.score}",
            fill="white", font=("Arial", 14)
        )
        self.lives_text = self.canvas.create_text(
            self.canvas_width - 50, 20, text=f"Lives: {self.lives}",
            fill="white", font=("Arial", 14)
        )
        self.balls_text = self.canvas.create_text(
            self.canvas_width // 2, 20, text="Balls: 1",
            fill="white", font=("Arial", 14)
        )
        
        # Initialize game objects
        self.init_game()
        
        # Set up keyboard event handlers
        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.bind("<KeyRelease>", self.on_key_release)
        self.root.focus_set()
        
        # Show initial start message
        self.show_start_message()
    
    def init_game(self) -> None:
        """Initialize all game objects (paddle, ball, bricks)"""
        # Create paddle at bottom center
        self.paddle = Paddle(
            self.canvas,
            self.canvas_width // 2,
            self.canvas_height - 50,
            speed_multiplier=self.speed_multiplier
        )
        
        # Create initial ball above paddle
        self.balls = [Ball(
            self.canvas,
            self.canvas_width // 2,
            self.canvas_height - 100,
            speed_multiplier=self.speed_multiplier
        )]
        
        # Create brick matrix
        self.create_bricks()
    
    def create_bricks(self) -> None:
        """Create a matrix of bricks with random special types"""
        brick_width = 60
        brick_height = 20
        rows = 8
        cols = 12
        
        # Center the brick matrix horizontally
        start_x = (self.canvas_width - cols * brick_width) // 2
        start_y = 80
        
        self.bricks = []
        for row in range(rows):
            for col in range(cols):
                x = start_x + col * brick_width
                y = start_y + row * brick_height
                
                # Randomly determine brick type based on special_brick_chance
                brick_type = self._get_random_brick_type()
                brick = Brick(self.canvas, x, y, brick_width, brick_height, brick_type)
                self.bricks.append(brick)
    
    def _get_random_brick_type(self) -> BrickType:
        """
        Randomly select brick type based on special brick probability
        
        Returns:
            BrickType: Either NORMAL or one of the special types
        """
        if random.random() < self.special_brick_chance:
            special_types = [
                BrickType.MULTI_BALL,
                BrickType.SPEED_UP,
                BrickType.EXPAND_PADDLE,
                BrickType.EXTRA_LIFE,
                BrickType.BONUS_SCORE,
            ]
            return random.choice(special_types)
        return BrickType.NORMAL
    
    def show_start_message(self) -> None:
        """Display initial game instructions and controls"""
        self.start_text = self.canvas.create_text(
            self.canvas_width // 2, self.canvas_height // 2,
            text="Press SPACE to start\nUse LEFT/RIGHT arrows to move paddle\n\nSpecial Bricks:\nM=Multi Ball, S=Speed Up, E=Expand Paddle\n+=Extra Life, $=Bonus Score",
            fill="white", font=("Arial", 14), justify=tk.CENTER
        )
    
    def on_key_press(self, event) -> None:
        """
        Handle key press events
        
        Tracks pressed keys for smooth movement and handles
        the space key to start the game.
        """
        self.pressed_keys.add(event.keysym)
        
        if event.keysym == "space":
            if not self.game_running:
                self.start_game()
    
    def on_key_release(self, event) -> None:
        """Handle key release events to stop movement"""
        self.pressed_keys.discard(event.keysym)
    
    def handle_input(self) -> None:
        """
        Process continuous keyboard input for smooth paddle movement
        
        Checks for held arrow keys and moves paddle accordingly.
        """
        if not self.game_running:
            return
        
        if "Left" in self.pressed_keys:
            self.paddle.move_left()
        
        if "Right" in self.pressed_keys:
            self.paddle.move_right(self.canvas_width)
    
    def start_game(self) -> None:
        """Start the game by removing start message and beginning game loop"""
        if hasattr(self, 'start_text'):
            self.canvas.delete(self.start_text)
        self.game_running = True
        self.game_loop()
    
    def game_loop(self) -> None:
        """
        Main game loop - runs at ~60 FPS
        
        Handles input, updates ball positions, checks collisions,
        updates UI, and schedules the next frame.
        """
        if not self.game_running:
            return
        
        # Process keyboard input for paddle movement
        self.handle_input()
        
        # Update all balls and check their collisions
        for ball in self.balls[:]:  # Use slice copy to allow safe removal
            ball.move()
            self.check_ball_collisions(ball)
        
        # Remove balls that fell off screen
        self.remove_out_of_bounds_balls()
        
        # Update score and lives display
        self.update_ui()
        
        # Check for win/loss conditions
        if self.check_game_over():
            return
        
        # Schedule next frame (16ms ≈ 60 FPS)
        self.root.after(16, self.game_loop)
    
    def check_ball_collisions(self, ball: Ball) -> None:
        """
        Check and handle all collisions for a single ball
        
        Handles collisions with walls, paddle, and bricks.
        Applies appropriate physics responses and special effects.
        """
        ball_bounds = ball.get_bounds()
        
        # Wall collisions (left, right, top)
        if ball_bounds[0] <= 0 or ball_bounds[2] >= self.canvas_width:
            ball.bounce_x()
        
        if ball_bounds[1] <= 0:  # Top wall
            ball.bounce_y()
        
        # Paddle collision
        paddle_bounds = self.paddle.get_bounds()
        if self.check_collision(ball_bounds, paddle_bounds):
            if ball.dy > 0:  # Only bounce if ball is moving downward
                ball.bounce_y()
                # Adjust angle based on hit position for better control
                hit_pos = (ball.x - self.paddle.x) / (self.paddle.width / 2)
                ball.dx = max(-8, min(8, hit_pos * 6))  # Clamp angle
        
        # Brick collisions
        for brick in self.bricks[:]:
            if brick.destroyed:
                continue
            
            brick_bounds = brick.get_bounds()
            if self.check_collision(ball_bounds, brick_bounds):
                self.handle_brick_collision(brick)
                ball.bounce_y()
                break  # Handle only one collision per frame
    
    def handle_brick_collision(self, brick: Brick) -> None:
        """
        Handle brick destruction and apply special effects
        
        Destroys the brick, awards points, and triggers any
        special power-up effects based on brick type.
        """
        brick.destroy()
        self.bricks.remove(brick)
        
        # Apply effects based on brick type
        if brick.brick_type == BrickType.NORMAL:
            self.score += 10
        elif brick.brick_type == BrickType.MULTI_BALL:
            self.score += 20
            self.add_extra_ball()  # Create additional ball
        elif brick.brick_type == BrickType.SPEED_UP:
            self.score += 15
            # Increase speed of all balls
            for ball in self.balls:
                ball.speed_up(1.2)
        elif brick.brick_type == BrickType.EXPAND_PADDLE:
            self.score += 15
            self.paddle.expand()  # Make paddle larger
        elif brick.brick_type == BrickType.EXTRA_LIFE:
            self.score += 25
            self.lives += 1  # Add one life
        elif brick.brick_type == BrickType.BONUS_SCORE:
            self.score += 50  # Extra points
    
    def add_extra_ball(self) -> None:
        """
        Create an additional ball with random direction
        
        The new ball spawns near an existing ball with
        random velocity for chaotic multi-ball gameplay.
        """
        if len(self.balls) > 0:
            # Base new ball on existing ball position
            base_ball = random.choice(self.balls)
            new_ball = Ball(
                self.canvas,
                base_ball.x + random.randint(-20, 20),
                base_ball.y + random.randint(-20, 20),
                speed_multiplier=self.speed_multiplier
            )
            # Set random direction
            angle = random.uniform(0, 2 * math.pi)
            speed = base_ball.base_speed
            new_ball.dx = speed * math.cos(angle)
            new_ball.dy = speed * math.sin(angle)
            self.balls.append(new_ball)
    
    def remove_out_of_bounds_balls(self) -> None:
        """
        Remove balls that have fallen off the bottom of the screen
        
        If all balls are lost, the player loses a life.
        """
        for ball in self.balls[:]:
            if ball.get_bounds()[3] >= self.canvas_height:  # Ball bottom > canvas height
                ball.destroy()
                self.balls.remove(ball)
        
        # If no balls remain, lose a life
        if not self.balls:
            self.lose_life()
    
    def check_collision(self, rect1: Tuple[float, float, float, float],
                       rect2: Tuple[float, float, float, float]) -> bool:
        """
        Check if two rectangles overlap (collision detection)
        
        Args:
            rect1, rect2: Tuples of (left, top, right, bottom) coordinates
            
        Returns:
            True if rectangles overlap, False otherwise
        """
        return not (rect1[2] < rect2[0] or rect1[0] > rect2[2] or
                   rect1[3] < rect2[1] or rect1[1] > rect2[3])
    
    def lose_life(self) -> None:
        """
        Handle losing a life
        
        Resets ball position and paddle size, or ends game if no lives remain.
        """
        self.lives -= 1
        if self.lives > 0:
            # Reset ball to starting position
            self.balls = [Ball(
                self.canvas,
                self.canvas_width // 2,
                self.canvas_height - 100,
                speed_multiplier=self.speed_multiplier
            )]
            # Reset paddle to original size
            self.paddle.reset_size()
            # Clear any held keys
            self.pressed_keys.clear()
        else:
            self.game_over()
    
    def update_ui(self) -> None:
        """Update the score, lives, and ball count display"""
        self.canvas.itemconfig(self.score_text, text=f"Score: {self.score}")
        self.canvas.itemconfig(self.lives_text, text=f"Lives: {self.lives}")
        self.canvas.itemconfig(self.balls_text, text=f"Balls: {len(self.balls)}")
    
    def check_game_over(self) -> bool:
        """
        Check for win/loss conditions
        
        Returns:
            True if game should end, False to continue
        """
        # Check for win condition (all bricks destroyed)
        active_bricks = [brick for brick in self.bricks if not brick.destroyed]
        if not active_bricks:
            self.win_game()
            return True
        
        # Check for loss condition (no lives remaining)
        if self.lives <= 0:
            self.game_over()
            return True
        
        return False
    
    def win_game(self) -> None:
        """Handle game victory"""
        self.game_running = False
        self.pressed_keys.clear()
        messagebox.showinfo("Congratulations!", f"You won!\nFinal Score: {self.score}")
        self.restart_game()
    
    def game_over(self) -> None:
        """Handle game over"""
        self.game_running = False
        self.pressed_keys.clear()
        messagebox.showinfo("Game Over", f"Game Over!\nFinal Score: {self.score}")
        self.restart_game()
    
    def restart_game(self) -> None:
        """
        Reset the game to initial state
        
        Clears all objects, resets score and lives, and recreates
        the game board for a fresh start.
        """
        # Destroy all balls
        for ball in self.balls:
            ball.destroy()
        
        # Clear canvas and input state
        self.canvas.delete("all")
        self.pressed_keys.clear()
        
        # Reset game state
        self.score = 0
        self.lives = 3
        self.game_running = False
        self.balls = []
        self.bricks = []
        
        # Recreate UI elements
        self.score_text = self.canvas.create_text(
            50, 20, text=f"Score: {self.score}",
            fill="white", font=("Arial", 14)
        )
        self.lives_text = self.canvas.create_text(
            self.canvas_width - 50, 20, text=f"Lives: {self.lives}",
            fill="white", font=("Arial", 14)
        )
        self.balls_text = self.canvas.create_text(
            self.canvas_width // 2, 20, text="Balls: 1",
            fill="white", font=("Arial", 14)
        )
        
        # Reinitialize game objects
        self.init_game()
        self.show_start_message()
    
    def run(self) -> None:
        """Start the Tkinter main event loop"""
        self.root.mainloop()

@click.command()
@click.option('--difficulty', '-d', 
              type=click.Choice(['easy', 'normal', 'hard'], case_sensitive=False),
              default='normal', 
              help='Game difficulty level')
@click.option('--speed', '-s', 
              type=float, 
              default=1.0, 
              help='Game speed multiplier (0.5-3.0)')
@click.option('--special-chance', '-c', 
              type=float, 
              default=0.15, 
              help='Chance of special bricks appearing (0.0-1.0)')
def main(difficulty: str, speed: float, special_chance: float) -> None:
    """
    Classic Breakout game with special brick features.
    
    Use LEFT/RIGHT arrow keys to move the paddle.
    Press SPACE to start the game.
    
    Special Bricks:
    - M (Multi Ball): Creates additional balls
    - S (Speed Up): Increases ball speed
    - E (Expand Paddle): Makes paddle larger
    - + (Extra Life): Adds one life
    - $ (Bonus Score): Gives extra points
    """
    # 验证参数
    if not (0.5 <= speed <= 3.0):
        click.echo("Speed multiplier must be between 0.5 and 3.0")
        return
    
    if not (0.0 <= special_chance <= 1.0):
        click.echo("Special brick chance must be between 0.0 and 1.0")
        return
    
    # 根据难度调整参数
    difficulty_settings = {
        'easy': {'speed_mult': speed * 0.8, 'special_mult': special_chance * 1.5},
        'normal': {'speed_mult': speed, 'special_mult': special_chance},
        'hard': {'speed_mult': speed * 1.3, 'special_mult': special_chance * 0.7}
    }
    
    settings = difficulty_settings[difficulty.lower()]
    final_special_chance = min(1.0, settings['special_mult'])
    
    click.echo(f"Starting Breakout Game...")
    click.echo(f"Difficulty: {difficulty.title()}")
    click.echo(f"Speed: {settings['speed_mult']:.1f}x")
    click.echo(f"Special Brick Chance: {final_special_chance:.1%}")
    
    game = BreakoutGame(
        difficulty=difficulty.lower(),
        speed_multiplier=settings['speed_mult'],
        special_brick_chance=final_special_chance
    )
    game.run()

if __name__ == "__main__":
    main()
