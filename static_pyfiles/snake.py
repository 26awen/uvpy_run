# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "click>=8.0.0",
#     "textual>=0.41.0",
# ]
# ///

# MIT License
#
# Copyright (c) 2025 Config-Txt Project
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
# - Textual: MIT License (https://github.com/Textualize/textual)

"""
Classic Snake Game with Terminal UI

A modern implementation of the classic Snake game using the Textual framework.
Features customizable board size, adjustable speed, smooth terminal-based gameplay,
and two-player mode. The snake grows by eating food while avoiding walls and its own body.

Version: 1.0.0
Category: Game
Author: Config-Txt Project

Usage Examples:
    uv run snake.py
    uv run snake.py --width 30 --height 20 --speed 8
    uv run snake.py -w 25 -h 18 -s 3
    uv run snake.py --two-player

Game Controls (Single Player):
    - WASD or Arrow Keys: Move the snake
    - SPACE: Pause/Resume game
    - R: Restart game
    - Q: Quit game

Game Controls (Two Player):
    - Player 1: WASD keys to move
    - Player 2: Arrow keys to move
    - SPACE: Pause/Resume game
    - R: Restart game
    - Q: Quit game

Game Elements:
    - @: Player 1 snake head / Single player snake head
    - #: Player 1 snake body / Single player snake body
    - &: Player 2 snake head
    - =: Player 2 snake body
    - ×: Dead snake body (remains on field)
    - *: Food
"""

import random
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

import click
from textual.app import App, ComposeResult
from textual.widgets import Static
from textual.reactive import reactive
from textual import events


class Direction(Enum):
    """Enumeration for movement directions with row/column deltas"""
    UP = (-1, 0)      # Move up: decrease row
    DOWN = (1, 0)     # Move down: increase row
    LEFT = (0, -1)    # Move left: decrease column
    RIGHT = (0, 1)    # Move right: increase column


@dataclass
class Position:
    """Represents a position on the game board with row and column coordinates"""
    row: int
    col: int
    
    def __add__(self, direction: Direction) -> 'Position':
        """Add a direction to this position to get a new position"""
        dr, dc = direction.value
        return Position(self.row + dr, self.col + dc)
    
    def __eq__(self, other) -> bool:
        """Check if two positions are equal"""
        if isinstance(other, Position):
            return self.row == other.row and self.col == other.col
        return False
    
    def __hash__(self) -> int:
        """Make Position hashable for use in sets and as dict keys"""
        return hash((self.row, self.col))


class SnakeGame(App):
    """
    Main Snake Game application using Textual framework
    
    This class handles the game logic, display, and user input for the Snake game.
    The snake moves continuously in the current direction, growing when it eats food.
    """
    
    CSS = """
    Screen {
        background: black;
    }
    
    #game {
        background: black;
        color: white;
        border: solid green;
        margin: 1;
        padding: 1;
        text-align: center;
    }
    """
    
    # Reactive attributes
    score = reactive(0)
    game_over = reactive(False)
    
    def __init__(self, width: int = 20, height: int = 15, speed: int = 5, two_player: bool = False):
        """
        Initialize the Snake game with specified dimensions and speed
        
        Args:
            width: Game board width in characters
            height: Game board height in characters
            speed: Game speed level (1-15, higher is faster)
            two_player: Enable two-player mode
        """
        super().__init__()
        self.width = width
        self.height = height
        self.speed = speed
        self.two_player = two_player
        
        # Initialize game state
        if two_player:
            # Player 1 starts on left side, Player 2 on right side
            self.snake1: List[Position] = [Position(height // 2, width // 4)]
            self.snake2: List[Position] = [Position(height // 2, 3 * width // 4)]
            self.direction1 = Direction.RIGHT
            self.direction2 = Direction.LEFT
            self.alive1 = True
            self.alive2 = True
            self.score1 = 0
            self.score2 = 0
            # Store dead snake bodies
            self.dead_bodies: List[Position] = []
        else:
            # Single player mode
            self.snake: List[Position] = [Position(height // 2, width // 2)]  # Start in center
            self.direction = Direction.RIGHT  # Initial movement direction
        
        self.food: Optional[Position] = None  # Food position
        self.paused = False  # Pause state
        
        # Generate initial food
        self._generate_food()
    
    def compose(self) -> ComposeResult:
        """Create the game display widget"""
        self.game_display = Static("", id="game")
        yield self.game_display
        self._update_display()
    
    def on_mount(self) -> None:
        """Start the game timer when app loads"""
        # Calculate update interval based on speed (faster speed = shorter interval)
        interval = max(0.05, 0.5 - (self.speed - 1) * 0.03)
        self.set_interval(interval, self._game_loop)
        self.title = "Snake Game"
    
    def _generate_food(self) -> None:
        """Generate food at a random empty position on the board"""
        while True:
            # Generate random position within board boundaries
            food_pos = Position(
                random.randint(0, self.height - 1),
                random.randint(0, self.width - 1)
            )
            # Ensure food doesn't spawn on snake bodies or dead bodies
            occupied_positions = []
            if self.two_player:
                occupied_positions.extend(self.snake1)
                occupied_positions.extend(self.snake2)
                occupied_positions.extend(self.dead_bodies)
            else:
                occupied_positions.extend(self.snake)
            
            if food_pos not in occupied_positions:
                self.food = food_pos
                break
    
    def _game_loop(self) -> None:
        """
        Main game update loop - called at regular intervals
        
        Handles snake movement, collision detection, food consumption,
        and game state updates.
        """
        if self.game_over or self.paused:
            return
        
        if self.two_player:
            self._update_two_player()
        else:
            self._update_single_player()
        
        self._update_display()
    
    def _update_single_player(self) -> None:
        """Update logic for single player mode"""
        # Calculate new head position based on current direction
        new_head = self.snake[0] + self.direction
        
        # Check wall collision
        if (new_head.row < 0 or new_head.row >= self.height or
            new_head.col < 0 or new_head.col >= self.width):
            self.game_over = True
            return
        
        # Check self collision (snake hitting its own body)
        if new_head in self.snake:
            self.game_over = True
            return
        
        # Add new head to snake
        self.snake.insert(0, new_head)
        
        # Check if snake ate food
        if new_head == self.food:
            self.score += 10  # Increase score
            self._generate_food()  # Generate new food
            # Snake grows (don't remove tail)
        else:
            # Remove tail (snake moves without growing)
            self.snake.pop()
    
    def _update_two_player(self) -> None:
        """Update logic for two player mode"""
        new_heads = []
        
        # Calculate new head positions for both players
        if self.alive1:
            new_head1 = self.snake1[0] + self.direction1
            new_heads.append((1, new_head1))
        
        if self.alive2:
            new_head2 = self.snake2[0] + self.direction2
            new_heads.append((2, new_head2))
        
        # Check collisions for each alive snake
        for player, new_head in new_heads:
            # Check wall collision
            if (new_head.row < 0 or new_head.row >= self.height or
                new_head.col < 0 or new_head.col >= self.width):
                if player == 1:
                    self.alive1 = False
                    self.dead_bodies.extend(self.snake1)
                else:
                    self.alive2 = False
                    self.dead_bodies.extend(self.snake2)
                continue
            
            # Check collision with own body
            current_snake = self.snake1 if player == 1 else self.snake2
            if new_head in current_snake:
                if player == 1:
                    self.alive1 = False
                    self.dead_bodies.extend(self.snake1)
                else:
                    self.alive2 = False
                    self.dead_bodies.extend(self.snake2)
                continue
            
            # Check collision with other snake's body
            other_snake = self.snake2 if player == 1 else self.snake1
            if new_head in other_snake:
                if player == 1:
                    self.alive1 = False
                    self.dead_bodies.extend(self.snake1)
                else:
                    self.alive2 = False
                    self.dead_bodies.extend(self.snake2)
                continue
            
            # Check collision with dead bodies
            if new_head in self.dead_bodies:
                if player == 1:
                    self.alive1 = False
                    self.dead_bodies.extend(self.snake1)
                else:
                    self.alive2 = False
                    self.dead_bodies.extend(self.snake2)
                continue
        
        # Move alive snakes
        if self.alive1:
            new_head1 = self.snake1[0] + self.direction1
            self.snake1.insert(0, new_head1)
            
            # Check if snake1 ate food
            if new_head1 == self.food:
                self.score1 += 10
                self._generate_food()
            else:
                self.snake1.pop()
        
        if self.alive2:
            new_head2 = self.snake2[0] + self.direction2
            self.snake2.insert(0, new_head2)
            
            # Check if snake2 ate food
            if new_head2 == self.food:
                self.score2 += 10
                self._generate_food()
            else:
                self.snake2.pop()
        
        # Check if game is over (both snakes dead)
        if not self.alive1 and not self.alive2:
            self.game_over = True
    
    def _update_display(self) -> None:
        """
        Update the visual display of the game board
        
        Creates a 2D grid representation and renders the snake(s), food,
        score, and game status messages. Uses horizontal spacing to match
        vertical line spacing for better visual consistency.
        """
        # Create empty game board
        board = [[' ' for _ in range(self.width)] for _ in range(self.height)]
        
        if self.two_player:
            # Place dead bodies first (so they can be overwritten by alive snakes)
            for pos in self.dead_bodies:
                if 0 <= pos.row < self.height and 0 <= pos.col < self.width:
                    board[pos.row][pos.col] = '×'  # Dead body symbol
            
            # Place snake1 on board (Player 1)
            if self.alive1:
                for i, pos in enumerate(self.snake1):
                    if 0 <= pos.row < self.height and 0 <= pos.col < self.width:
                        if i == 0:  # Snake head
                            board[pos.row][pos.col] = '@'
                        else:  # Snake body
                            board[pos.row][pos.col] = '#'
            
            # Place snake2 on board (Player 2)
            if self.alive2:
                for i, pos in enumerate(self.snake2):
                    if 0 <= pos.row < self.height and 0 <= pos.col < self.width:
                        if i == 0:  # Snake head
                            board[pos.row][pos.col] = '&'  # Different head symbol for player 2
                        else:  # Snake body
                            board[pos.row][pos.col] = '='  # Different body symbol for player 2
        else:
            # Single player mode - place snake on board
            for i, pos in enumerate(self.snake):
                if 0 <= pos.row < self.height and 0 <= pos.col < self.width:
                    if i == 0:  # Snake head
                        board[pos.row][pos.col] = '@'
                    else:  # Snake body
                        board[pos.row][pos.col] = '#'
        
        # Place food on board
        if self.food:
            board[self.food.row][self.food.col] = '*'
        
        # Build display string with borders and UI
        lines = []
        
        if self.two_player:
            # Show scores for both players
            status1 = "DEAD" if not self.alive1 else "ALIVE"
            status2 = "DEAD" if not self.alive2 else "ALIVE"
            lines.append(f"Player 1 (@#): {self.score1} ({status1}) | Player 2 (&=): {self.score2} ({status2})")
        else:
            lines.append(f"Score: {self.score}")
        
        # Add horizontal spacing to match vertical line spacing for better visual consistency
        # Calculate border width for spaced characters (each cell takes 2 characters: content + space)
        border_width = self.width * 2
        lines.append("┌" + "─" * border_width + "┐")  # Top border with box drawing chars
        
        # Add game board rows with side borders, with spacing between characters
        for row in board:
            # Add space after each character for better visual consistency
            row_str = " ".join(row) + " "  # Space between chars + trailing space
            lines.append("│" + row_str + "│")
        
        lines.append("└" + "─" * border_width + "┘")  # Bottom border
        
        # Add status message based on game state
        if self.game_over:
            if self.two_player:
                if self.score1 > self.score2:
                    lines.append("GAME OVER! Player 1 WINS! Press R to restart, Q to quit")
                elif self.score2 > self.score1:
                    lines.append("GAME OVER! Player 2 WINS! Press R to restart, Q to quit")
                else:
                    lines.append("GAME OVER! TIE GAME! Press R to restart, Q to quit")
            else:
                lines.append("GAME OVER! Press R to restart, Q to quit")
        elif self.paused:
            lines.append("PAUSED - Press SPACE to resume")
        else:
            if self.two_player:
                lines.append("P1: WASD | P2: Arrows | SPACE: Pause | R: Restart | Q: Quit")
            else:
                lines.append("WASD/Arrows: Move | SPACE: Pause | R: Restart | Q: Quit")
        
        # Update the display widget
        self.game_display.update("\n".join(lines))
    
    def on_key(self, event: events.Key) -> None:
        """
        Handle keyboard input for game controls
        
        Processes movement keys (WASD/arrows) and game control keys
        (space, R, Q). Prevents reverse direction to avoid instant death.
        In two-player mode: Player 1 uses WASD, Player 2 uses arrow keys.
        """
        key = event.key.lower()
        
        if self.two_player:
            # Player 1 controls (WASD) - only if alive
            if self.alive1:
                if key == "w" and self.direction1 != Direction.DOWN:
                    self.direction1 = Direction.UP
                elif key == "s" and self.direction1 != Direction.UP:
                    self.direction1 = Direction.DOWN
                elif key == "a" and self.direction1 != Direction.RIGHT:
                    self.direction1 = Direction.LEFT
                elif key == "d" and self.direction1 != Direction.LEFT:
                    self.direction1 = Direction.RIGHT
            
            # Player 2 controls (Arrow keys) - only if alive
            if self.alive2:
                if key == "up" and self.direction2 != Direction.DOWN:
                    self.direction2 = Direction.UP
                elif key == "down" and self.direction2 != Direction.UP:
                    self.direction2 = Direction.DOWN
                elif key == "left" and self.direction2 != Direction.RIGHT:
                    self.direction2 = Direction.LEFT
                elif key == "right" and self.direction2 != Direction.LEFT:
                    self.direction2 = Direction.RIGHT
        else:
            # Single player mode - movement keys (prevent moving in opposite direction)
            if key in ["w", "up"] and self.direction != Direction.DOWN:
                self.direction = Direction.UP
            elif key in ["s", "down"] and self.direction != Direction.UP:
                self.direction = Direction.DOWN
            elif key in ["a", "left"] and self.direction != Direction.RIGHT:
                self.direction = Direction.LEFT
            elif key in ["d", "right"] and self.direction != Direction.LEFT:
                self.direction = Direction.RIGHT
        
        # Game control keys (same for both modes)
        if key == "space":
            # Toggle pause (only if game is not over)
            if not self.game_over:
                self.paused = not self.paused
                self._update_display()
        
        elif key == "r":
            # Restart game
            self._restart_game()
        
        elif key == "q":
            # Quit game
            self.exit()
    
    def _restart_game(self) -> None:
        """
        Reset the game to initial state
        
        Resets snake position(s), direction(s), score(s), and game flags.
        Generates new food and updates display.
        """
        if self.two_player:
            # Reset both snakes
            self.snake1 = [Position(self.height // 2, self.width // 4)]
            self.snake2 = [Position(self.height // 2, 3 * self.width // 4)]
            self.direction1 = Direction.RIGHT
            self.direction2 = Direction.LEFT
            self.alive1 = True
            self.alive2 = True
            self.score1 = 0
            self.score2 = 0
            self.dead_bodies = []
        else:
            # Single player mode
            self.snake = [Position(self.height // 2, self.width // 2)]  # Reset to center
            self.direction = Direction.RIGHT  # Reset direction
            self.score = 0  # Reset score
        
        self.game_over = False  # Clear game over flag
        self.paused = False  # Clear pause flag
        self._generate_food()  # Generate new food
        self._update_display()  # Update display


@click.command()
@click.option('--width', '-w', default=20, help='Game board width', type=click.IntRange(10, 50))
@click.option('--height', '-h', default=15, help='Game board height', type=click.IntRange(8, 30))
@click.option('--speed', '-s', default=5, help='Game speed (1-15)', type=click.IntRange(1, 15))
@click.option('--two-player', '-2', is_flag=True, help='Enable two-player mode')
def main(width: int, height: int, speed: int, two_player: bool) -> None:
    """
    Classic Snake Game in terminal.
    
    Controls:
    - WASD or Arrow Keys: Move the snake
    - SPACE: Pause/Resume
    - R: Restart game
    - Q: Quit
    
    Goal: Eat the food (*) to grow and increase score.
    Avoid hitting walls or yourself!
    """
    app = SnakeGame(width, height, speed, two_player)
    app.run()


if __name__ == '__main__':
    main()
