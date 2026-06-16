# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "click>=8.2.1",
#     "rich>=14.1.0",
#     "textual>=6.1.0",
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
# - Rich: MIT License (https://github.com/Textualize/rich)
# - Textual: MIT License (https://github.com/Textualize/textual)

"""
Classic Snake Game with a Textual terminal UI

A polished terminal Snake game powered by Textual and Rich. It opens into a
full-screen command-line game, uses smooth Braille sub-cell rendering in modern
terminals, can use Kitty graphics for true pixel animation, and lets you tune
the board size, speed, player count, and glyph compatibility from the command
line.

Version: 1.0.0
Category: Game
Author: UVPY.RUN

Usage Examples:
    uv run snake.py --width 32 --height 18 --speed 12
    uv run snake.py
    uv run snake.py -w 24 -h 14 -s 4
    uv run snake.py --two-player --width 40 --height 20 --speed 6
    uv run snake.py --mode-smooth --width 32 --height 18
    uv run snake.py --mode-kitty --width 32 --height 18
    uv run snake.py --mode-classic
    uv run snake.py --ascii

Use It For:
    - Trying a real interactive terminal app from one uv command
    - Demoing PEP 723 dependency metadata with Textual installed on demand
    - Playing a quick keyboard game without cloning a repository
    - Checking how Rich styling, Textual key bindings, Braille rendering, and
      Kitty graphics animation feel in a small script

Game Controls (Single Player):
    - WASD or Arrow Keys: Move the snake
    - SPACE: Pause or resume
    - R: Restart
    - Q: Quit

Game Controls (Two Player):
    - Player 1: WASD keys
    - Player 2: Arrow keys
    - SPACE: Pause or resume
    - R: Restart
    - Q: Quit

Game Elements:
    - @: Player 1 snake head / single-player snake head
    - #: Player 1 snake body / single-player snake body
    - &: Player 2 snake head
    - =: Player 2 snake body
    - x: Dead snake body in ASCII mode
    - ×: Dead snake body in styled mode
    - * or ◆: Food
"""

from __future__ import annotations

import base64
import math
import os
import random
import select
import sys
import termios
import time
import tty
import zlib
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import click
from rich import box
from rich.align import Align
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import Footer, Header, Static


DEFAULT_WIDTH = 32
DEFAULT_HEIGHT = 18
DEFAULT_SPEED = 10
STARTING_LENGTH = 3
POINTS_PER_FOOD = 10
RENDER_MODE_SMOOTH = "smooth"
RENDER_MODE_CLASSIC = "classic"
RENDER_MODE_KITTY = "kitty"
SMOOTH_RENDER_FPS = 60
SUBPIXELS_PER_CELL = 4
BRAILLE_BASE = 0x2800
KITTY_RENDER_FPS = 60
KITTY_CELL_PIXELS = 18
KITTY_IMAGE_ID = 260826
KITTY_PLACEMENT_ID = 1
KITTY_CHUNK_SIZE = 4096
BRAILLE_DOT_BITS = {
    (0, 0): 0x01,
    (0, 1): 0x02,
    (0, 2): 0x04,
    (0, 3): 0x40,
    (1, 0): 0x08,
    (1, 1): 0x10,
    (1, 2): 0x20,
    (1, 3): 0x80,
}

CELL_EMPTY = "empty"
CELL_FOOD = "food"
CELL_HEAD_1 = "head1"
CELL_BODY_1 = "body1"
CELL_HEAD_2 = "head2"
CELL_BODY_2 = "body2"
CELL_DEAD = "dead"

GLYPHS = {
    CELL_EMPTY: "·",
    CELL_FOOD: "◆",
    CELL_HEAD_1: "@",
    CELL_BODY_1: "#",
    CELL_HEAD_2: "&",
    CELL_BODY_2: "=",
    CELL_DEAD: "×",
}

ASCII_GLYPHS = {
    CELL_EMPTY: " ",
    CELL_FOOD: "*",
    CELL_HEAD_1: "@",
    CELL_BODY_1: "#",
    CELL_HEAD_2: "&",
    CELL_BODY_2: "=",
    CELL_DEAD: "x",
}

CELL_STYLES = {
    CELL_EMPTY: "dim #365044",
    CELL_FOOD: "bold #ffcc66",
    CELL_HEAD_1: "bold #7dff9b",
    CELL_BODY_1: "#38d878",
    CELL_HEAD_2: "bold #7cc7ff",
    CELL_BODY_2: "#4d8dff",
    CELL_DEAD: "dim #d45d5d",
}

CELL_PRIORITY = {
    CELL_FOOD: 1,
    CELL_DEAD: 2,
    CELL_BODY_1: 3,
    CELL_BODY_2: 3,
    CELL_HEAD_1: 4,
    CELL_HEAD_2: 4,
}


class Direction(Enum):
    """Movement directions with row/column deltas."""

    UP = (-1, 0)
    DOWN = (1, 0)
    LEFT = (0, -1)
    RIGHT = (0, 1)


OPPOSITE_DIRECTIONS = {
    Direction.UP: Direction.DOWN,
    Direction.DOWN: Direction.UP,
    Direction.LEFT: Direction.RIGHT,
    Direction.RIGHT: Direction.LEFT,
}


@dataclass(frozen=True)
class Position:
    """A board position with row and column coordinates."""

    row: int
    col: int

    def __add__(self, direction: Direction) -> "Position":
        dr, dc = direction.value
        return Position(self.row + dr, self.col + dc)


class SnakeGame(App):
    """Textual Snake with polished rendering and small, testable game logic."""

    CSS = """
    Screen {
        align: center middle;
        background: #07100c;
        color: #dbffe9;
    }

    Header {
        background: #10241d;
        color: #dbffe9;
    }

    Footer {
        background: #10241d;
        color: #dbffe9;
    }

    #game {
        width: auto;
        height: auto;
        margin: 1 2;
    }
    """

    BINDINGS = [
        Binding("space", "toggle_pause", "Pause", show=True),
        Binding("r", "restart", "Restart", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    TITLE = "uvpy.run Snake"
    SUB_TITLE = "Textual terminal showcase"

    score = reactive(0)
    game_over = reactive(False)

    def __init__(
        self,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        speed: int = DEFAULT_SPEED,
        two_player: bool = False,
        ascii_only: bool = False,
        render_mode: str = RENDER_MODE_SMOOTH,
    ):
        super().__init__()
        self.width = width
        self.height = height
        self.speed = speed
        self.two_player = two_player
        self.ascii_only = ascii_only
        self.render_mode = render_mode

        self.game_display: Static | None = None
        self.food: Optional[Position] = None
        self.paused = False
        self.won = False
        self.high_score = 0
        self.food_eaten = 0
        self.ticks = 0
        self.last_message = "Eat food, grow longer, and keep moving."
        self._logic_interval = self._tick_interval()
        self._animation_started_at = time.monotonic()
        self._previous_snake: list[Position] = []
        self._previous_snake1: list[Position] = []
        self._previous_snake2: list[Position] = []

        self._reset_game_state(reset_high_score=True)

    def compose(self) -> ComposeResult:
        """Create Textual widgets for the game shell."""

        yield Header(show_clock=True)
        self.game_display = Static("", id="game")
        yield self.game_display
        yield Footer()

    def on_mount(self) -> None:
        """Start the game timer when the app mounts."""

        self.set_interval(self._logic_interval, self._game_loop)
        if self._uses_smooth_renderer():
            self.set_interval(1 / SMOOTH_RENDER_FPS, self._update_display)
        self._update_display()

    def _tick_interval(self) -> float:
        """Convert the user-facing speed value into a timer interval."""

        return max(0.045, 0.42 - (self.speed - 1) * 0.026)

    def _reset_game_state(self, reset_high_score: bool = False) -> None:
        """Reset positions, scores, and status flags for a fresh round."""

        if reset_high_score:
            self.high_score = 0

        self.food = None
        self.paused = False
        self.won = False
        self.game_over = False
        self.food_eaten = 0
        self.ticks = 0
        self.last_message = "Eat food, grow longer, and keep moving."

        if self.two_player:
            self.direction1 = Direction.RIGHT
            self.direction2 = Direction.LEFT
            self.next_direction1 = self.direction1
            self.next_direction2 = self.direction2
            self.snake1 = self._build_starting_snake(
                Position(self.height // 2, self.width // 4),
                self.direction1,
            )
            self.snake2 = self._build_starting_snake(
                Position(self.height // 2, 3 * self.width // 4),
                self.direction2,
            )
            self.alive1 = True
            self.alive2 = True
            self.score1 = 0
            self.score2 = 0
            self.dead_bodies: list[Position] = []
        else:
            self.direction = Direction.RIGHT
            self.next_direction = self.direction
            self.snake = self._build_starting_snake(
                Position(self.height // 2, self.width // 2),
                self.direction,
            )
            self.score = 0

        self._generate_food()
        self._sync_animation_state()

    def _build_starting_snake(
        self,
        head: Position,
        direction: Direction,
        length: int = STARTING_LENGTH,
    ) -> list[Position]:
        """Build a starting snake body behind the head."""

        dr, dc = direction.value
        return [
            Position(head.row - dr * offset, head.col - dc * offset)
            for offset in range(length)
        ]

    def _occupied_positions(self) -> set[Position]:
        """Return every board position currently occupied by snake bodies."""

        if self.two_player:
            return set(self.snake1) | set(self.snake2) | set(self.dead_bodies)
        return set(self.snake)

    def _generate_food(self) -> None:
        """Generate food at a random empty position on the board."""

        occupied_positions = self._occupied_positions()
        open_positions = [
            Position(row, col)
            for row in range(self.height)
            for col in range(self.width)
            if Position(row, col) not in occupied_positions
        ]

        if not open_positions:
            self.food = None
            self._finish_game("Board cleared. Perfect run.", won=True)
            return

        self.food = random.choice(open_positions)

    def _game_loop(self) -> None:
        """Advance the game by one tick."""

        if self.game_over or self.paused:
            return

        self._begin_step_animation()
        self.ticks += 1
        if self.two_player:
            self._update_two_player()
        else:
            self._update_single_player()

        self._update_display()

    def _update_single_player(self) -> None:
        """Update logic for single-player mode."""

        self.direction = self.next_direction
        new_head = self.snake[0] + self.direction

        if self._is_out_of_bounds(new_head):
            self._finish_game("Wall hit. Press R for a clean restart.")
            return

        will_grow = new_head == self.food
        body_to_check = self.snake if will_grow else self.snake[:-1]
        if new_head in body_to_check:
            self._finish_game("Tail collision. Press R and try a wider turn.")
            return

        self.snake.insert(0, new_head)

        if will_grow:
            self.score += POINTS_PER_FOOD
            self.high_score = max(self.high_score, self.score)
            self.food_eaten += 1
            self.last_message = f"Snack collected. +{POINTS_PER_FOOD} points."
            self._generate_food()
        else:
            self.snake.pop()

    def _is_out_of_bounds(self, position: Position) -> bool:
        """Return whether a position is outside the game board."""

        return (
            position.row < 0
            or position.row >= self.height
            or position.col < 0
            or position.col >= self.width
        )

    def _finish_game(self, message: str, won: bool = False) -> None:
        """Set a final game state and message."""

        self.won = won
        self.game_over = True
        self.last_message = message

    def _kill_player(self, player: int) -> None:
        """Mark a two-player snake as dead and leave its body on the board."""

        if player == 1 and self.alive1:
            self.alive1 = False
            self.dead_bodies.extend(self.snake1)
        elif player == 2 and self.alive2:
            self.alive2 = False
            self.dead_bodies.extend(self.snake2)

    def _update_two_player(self) -> None:
        """Update logic for two-player mode with simultaneous planning."""

        if self.alive1:
            self.direction1 = self.next_direction1
        if self.alive2:
            self.direction2 = self.next_direction2

        planned_heads: dict[int, Position] = {}
        if self.alive1:
            planned_heads[1] = self.snake1[0] + self.direction1
        if self.alive2:
            planned_heads[2] = self.snake2[0] + self.direction2

        dead_players: set[int] = set()
        for player, new_head in planned_heads.items():
            if self._is_out_of_bounds(new_head):
                dead_players.add(player)
                continue

            current_snake = self.snake1 if player == 1 else self.snake2
            other_snake = self.snake2 if player == 1 else self.snake1
            will_grow = new_head == self.food
            own_body = current_snake if will_grow else current_snake[:-1]

            if (
                new_head in own_body
                or new_head in other_snake
                or new_head in self.dead_bodies
            ):
                dead_players.add(player)

        if (
            len(planned_heads) == 2
            and planned_heads[1] == planned_heads[2]
        ):
            dead_players.update({1, 2})

        for player in sorted(dead_players):
            self._kill_player(player)

        original_food = self.food
        food_claims: list[int] = []
        for player in (1, 2):
            if player not in planned_heads:
                continue
            if player == 1 and self.alive1:
                self.snake1.insert(0, planned_heads[player])
                if planned_heads[player] == original_food:
                    self.score1 += POINTS_PER_FOOD
                    food_claims.append(player)
                else:
                    self.snake1.pop()
            elif player == 2 and self.alive2:
                self.snake2.insert(0, planned_heads[player])
                if planned_heads[player] == original_food:
                    self.score2 += POINTS_PER_FOOD
                    food_claims.append(player)
                else:
                    self.snake2.pop()

        if food_claims:
            self.food_eaten += len(food_claims)
            self.high_score = max(self.high_score, self.score1, self.score2)
            players = " and ".join(f"P{player}" for player in food_claims)
            self.last_message = f"{players} scored. +{POINTS_PER_FOOD}."
            self._generate_food()
        elif dead_players:
            fallen = " and ".join(f"P{player}" for player in sorted(dead_players))
            self.last_message = f"{fallen} crashed."

        if not self.alive1 and not self.alive2:
            if self.score1 > self.score2:
                self._finish_game("Game over. Player 1 wins.")
            elif self.score2 > self.score1:
                self._finish_game("Game over. Player 2 wins.")
            else:
                self._finish_game("Game over. Tie game.")

    def _board_cells(self) -> list[list[str]]:
        """Return a symbolic board representation used by the renderer."""

        board = [
            [CELL_EMPTY for _ in range(self.width)]
            for _ in range(self.height)
        ]

        if self.food:
            board[self.food.row][self.food.col] = CELL_FOOD

        if self.two_player:
            for pos in self.dead_bodies:
                if 0 <= pos.row < self.height and 0 <= pos.col < self.width:
                    board[pos.row][pos.col] = CELL_DEAD

            if self.alive1:
                self._draw_snake(board, self.snake1, CELL_HEAD_1, CELL_BODY_1)
            if self.alive2:
                self._draw_snake(board, self.snake2, CELL_HEAD_2, CELL_BODY_2)
        else:
            self._draw_snake(board, self.snake, CELL_HEAD_1, CELL_BODY_1)

        return board

    def _draw_snake(
        self,
        board: list[list[str]],
        snake: list[Position],
        head_cell: str,
        body_cell: str,
    ) -> None:
        """Draw a snake onto the symbolic board."""

        for index, pos in enumerate(snake):
            if 0 <= pos.row < self.height and 0 <= pos.col < self.width:
                board[pos.row][pos.col] = head_cell if index == 0 else body_cell

    def _render_board(self) -> Text:
        """Render the board as styled terminal text."""

        if self._uses_smooth_renderer():
            return self._render_smooth_board()

        return self._render_symbol_board()

    def _uses_smooth_renderer(self) -> bool:
        """Return whether the Braille sub-cell renderer should be active."""

        return self.render_mode == RENDER_MODE_SMOOTH and not self.ascii_only

    def _render_symbol_board(self) -> Text:
        """Render the board as one terminal glyph per game cell."""

        glyphs = ASCII_GLYPHS if self.ascii_only else GLYPHS
        board_text = Text()
        for row_index, row in enumerate(self._board_cells()):
            for cell in row:
                board_text.append(glyphs[cell], style=CELL_STYLES[cell])
                board_text.append(" ")
            if row_index < self.height - 1:
                board_text.append("\n")
        return board_text

    def _sync_animation_state(self) -> None:
        """Reset animation snapshots to the current board positions."""

        self._animation_started_at = time.monotonic() - self._logic_interval
        if self.two_player:
            self._previous_snake1 = list(self.snake1)
            self._previous_snake2 = list(self.snake2)
        else:
            self._previous_snake = list(self.snake)

    def _begin_step_animation(self) -> None:
        """Capture the old positions before advancing one logical step."""

        self._animation_started_at = time.monotonic()
        if self.two_player:
            self._previous_snake1 = list(self.snake1)
            self._previous_snake2 = list(self.snake2)
        else:
            self._previous_snake = list(self.snake)

    def _animation_progress(self) -> float:
        """Return how far the renderer is between the last and current step."""

        if not self._uses_smooth_renderer() or self.game_over or self.paused:
            return 1.0

        elapsed = time.monotonic() - self._animation_started_at
        return min(1.0, max(0.0, elapsed / self._logic_interval))

    def _interpolated_snake(
        self,
        snake: list[Position],
        previous_snake: list[Position],
        progress: float,
    ) -> list[tuple[float, float]]:
        """Return sub-cell snake coordinates for smooth terminal rendering."""

        if not previous_snake or progress >= 1.0:
            return [(float(pos.row), float(pos.col)) for pos in snake]

        positions: list[tuple[float, float]] = []
        for index, current_pos in enumerate(snake):
            previous_pos = (
                previous_snake[index]
                if index < len(previous_snake)
                else previous_snake[-1]
            )
            distance = (
                abs(current_pos.row - previous_pos.row)
                + abs(current_pos.col - previous_pos.col)
            )
            if distance > 1:
                previous_pos = current_pos

            row = previous_pos.row + (current_pos.row - previous_pos.row) * progress
            col = previous_pos.col + (current_pos.col - previous_pos.col) * progress
            positions.append((row, col))

        return positions

    def _blank_pixel_grid(self) -> list[list[str | None]]:
        """Create a 4x4 sub-cell grid for each game board cell."""

        rows = self.height * SUBPIXELS_PER_CELL
        cols = self.width * SUBPIXELS_PER_CELL
        return [[None for _ in range(cols)] for _ in range(rows)]

    def _paint_pixel(
        self,
        pixels: list[list[str | None]],
        row: int,
        col: int,
        cell: str,
    ) -> None:
        """Paint one sub-cell, keeping the most important visible element."""

        if row < 0 or row >= len(pixels) or col < 0 or col >= len(pixels[0]):
            return

        current = pixels[row][col]
        if current is None or CELL_PRIORITY[cell] >= CELL_PRIORITY[current]:
            pixels[row][col] = cell

    def _paint_square(
        self,
        pixels: list[list[str | None]],
        row: float,
        col: float,
        cell: str,
        half_size: float,
    ) -> None:
        """Paint a smooth block centered on a logical board position."""

        center_row = (row + 0.5) * SUBPIXELS_PER_CELL
        center_col = (col + 0.5) * SUBPIXELS_PER_CELL
        min_row = int(center_row - half_size - 1)
        max_row = int(center_row + half_size + 1)
        min_col = int(center_col - half_size - 1)
        max_col = int(center_col + half_size + 1)

        for pixel_row in range(min_row, max_row + 1):
            pixel_center_row = pixel_row + 0.5
            if abs(pixel_center_row - center_row) > half_size:
                continue
            for pixel_col in range(min_col, max_col + 1):
                pixel_center_col = pixel_col + 0.5
                if abs(pixel_center_col - center_col) <= half_size:
                    self._paint_pixel(pixels, pixel_row, pixel_col, cell)

    def _paint_line(
        self,
        pixels: list[list[str | None]],
        start: tuple[float, float],
        end: tuple[float, float],
        cell: str,
        half_size: float,
    ) -> None:
        """Paint a thin continuous path between two logical positions."""

        start_row, start_col = start
        end_row, end_col = end
        distance = max(abs(end_row - start_row), abs(end_col - start_col))
        steps = max(1, int(distance * SUBPIXELS_PER_CELL * 2))

        for step in range(steps + 1):
            progress = step / steps
            row = start_row + (end_row - start_row) * progress
            col = start_col + (end_col - start_col) * progress
            self._paint_square(pixels, row, col, cell, half_size)

    def _paint_smooth_snake(
        self,
        pixels: list[list[str | None]],
        snake: list[Position],
        previous_snake: list[Position],
        head_cell: str,
        body_cell: str,
        progress: float,
    ) -> None:
        """Paint a snake at interpolated sub-cell coordinates."""

        positions = self._interpolated_snake(snake, previous_snake, progress)
        if not positions:
            return

        for index in range(len(positions) - 1, 0, -1):
            self._paint_line(
                pixels,
                positions[index],
                positions[index - 1],
                body_cell,
                half_size=0.82,
            )

        head_row, head_col = positions[0]
        self._paint_square(
            pixels,
            head_row,
            head_col,
            head_cell,
            half_size=1.28,
        )

    def _render_smooth_board(self) -> Text:
        """Render the board with Braille sub-cells for smoother motion."""

        pixels = self._blank_pixel_grid()

        if self.food:
            self._paint_square(
                pixels,
                float(self.food.row),
                float(self.food.col),
                CELL_FOOD,
                half_size=0.92,
            )

        progress = self._animation_progress()
        if self.two_player:
            for pos in self.dead_bodies:
                self._paint_square(
                    pixels,
                    float(pos.row),
                    float(pos.col),
                    CELL_DEAD,
                    half_size=1.0,
                )

            if self.alive1:
                self._paint_smooth_snake(
                    pixels,
                    self.snake1,
                    self._previous_snake1,
                    CELL_HEAD_1,
                    CELL_BODY_1,
                    progress,
                )
            if self.alive2:
                self._paint_smooth_snake(
                    pixels,
                    self.snake2,
                    self._previous_snake2,
                    CELL_HEAD_2,
                    CELL_BODY_2,
                    progress,
                )
        else:
            self._paint_smooth_snake(
                pixels,
                self.snake,
                self._previous_snake,
                CELL_HEAD_1,
                CELL_BODY_1,
                progress,
            )

        return self._pixels_to_braille(pixels)

    def _pixels_to_braille(self, pixels: list[list[str | None]]) -> Text:
        """Pack the sub-cell grid into Braille characters."""

        board_text = Text()
        terminal_rows = self.height
        terminal_cols = self.width * 2

        for terminal_row in range(terminal_rows):
            for terminal_col in range(terminal_cols):
                bits = 0
                style_cell: str | None = None
                style_priority = 0
                base_row = terminal_row * 4
                base_col = terminal_col * 2

                for local_row in range(4):
                    for local_col in range(2):
                        cell = pixels[base_row + local_row][base_col + local_col]
                        if cell is None:
                            continue

                        bits |= BRAILLE_DOT_BITS[(local_col, local_row)]
                        priority = CELL_PRIORITY[cell]
                        if priority >= style_priority:
                            style_cell = cell
                            style_priority = priority

                if bits:
                    board_text.append(
                        chr(BRAILLE_BASE + bits),
                        style=CELL_STYLES[style_cell or CELL_EMPTY],
                    )
                else:
                    board_text.append(" ")

            if terminal_row < terminal_rows - 1:
                board_text.append("\n")

        return board_text

    def _state_label(self) -> Text:
        """Return a concise state label for the board panel."""

        if self.game_over:
            if self.won:
                return Text("CLEARED", style="bold #7dff9b")
            return Text("GAME OVER", style="bold #ff6b6b")
        if self.paused:
            return Text("PAUSED", style="bold #ffcc66")
        return Text("LIVE", style="bold #7dff9b")

    def _score_table(self) -> Table:
        """Build a compact score and run metadata table."""

        table = Table.grid(padding=(0, 2))
        table.add_column(justify="left")
        table.add_column(justify="right")
        table.add_column(justify="right")
        table.add_column(justify="right")

        if self.two_player:
            p1_state = "alive" if self.alive1 else "out"
            p2_state = "alive" if self.alive2 else "out"
            table.add_row(
                Text(f"P1 {self.score1} ({p1_state})", style="#7dff9b"),
                Text(f"P2 {self.score2} ({p2_state})", style="#7cc7ff"),
                Text(f"best {self.high_score}", style="bold #ffcc66"),
                Text(f"speed {self.speed}/15", style="dim"),
            )
        else:
            table.add_row(
                Text(f"score {self.score}", style="bold #7dff9b"),
                Text(f"best {self.high_score}", style="bold #ffcc66"),
                Text(f"food {self.food_eaten}", style="dim"),
                Text(f"speed {self.speed}/15", style="dim"),
            )

        return table

    def _render_controls(self) -> Text:
        """Return mode-specific control help."""

        if self.two_player:
            controls = "P1 WASD  P2 arrows  Space pause  R restart  Q quit"
        else:
            controls = "WASD or arrows move  Space pause  R restart  Q quit"
        return Text(controls, style="dim")

    def _render_message(self) -> Text:
        """Return the current game message with state-aware styling."""

        style = "bold #ff6b6b" if self.game_over and not self.won else "#dbffe9"
        if self.paused:
            style = "bold #ffcc66"
        if self.won:
            style = "bold #7dff9b"
        return Text(self.last_message, style=style)

    def _render_game(self) -> Align:
        """Build the full Rich renderable displayed inside Textual."""

        heading = Text()
        heading.append("uvpy.run Snake", style="bold #7dff9b")
        heading.append("  ")
        render_label = RENDER_MODE_SMOOTH if self._uses_smooth_renderer() else RENDER_MODE_CLASSIC
        heading.append(
            f"{'two-player' if self.two_player else 'single-player'} / {render_label}",
            style="dim",
        )

        board_panel = Panel.fit(
            self._render_board(),
            title=self._state_label(),
            subtitle=f"{self.width}x{self.height}",
            border_style="#38d878" if not self.game_over else "#ff6b6b",
            box=box.SQUARE,
            padding=(0, 1),
        )

        content = Group(
            Align.center(heading),
            self._score_table(),
            board_panel,
            Align.center(self._render_message()),
            Align.center(self._render_controls()),
        )
        return Align.center(content, vertical="middle")

    def _update_display(self) -> None:
        """Update the display widget when the Textual app is mounted."""

        if self.game_display is not None:
            self.game_display.update(self._render_game())

    def _queue_direction(self, direction: Direction, player: int | None = None) -> bool:
        """Queue one legal direction change for the next game tick."""

        if self.game_over:
            return False

        if player == 1:
            current_direction = self.direction1
            if direction == OPPOSITE_DIRECTIONS[current_direction]:
                return False
            self.next_direction1 = direction
            return True

        if player == 2:
            current_direction = self.direction2
            if direction == OPPOSITE_DIRECTIONS[current_direction]:
                return False
            self.next_direction2 = direction
            return True

        current_direction = self.direction
        if direction == OPPOSITE_DIRECTIONS[current_direction]:
            return False
        self.next_direction = direction
        return True

    def on_key(self, event: events.Key) -> None:
        """Handle movement keys; global actions are handled by Textual bindings."""

        key = event.key.lower()
        handled = False

        if self.two_player:
            if self.alive1:
                if key == "w":
                    handled = self._queue_direction(Direction.UP, player=1)
                elif key == "s":
                    handled = self._queue_direction(Direction.DOWN, player=1)
                elif key == "a":
                    handled = self._queue_direction(Direction.LEFT, player=1)
                elif key == "d":
                    handled = self._queue_direction(Direction.RIGHT, player=1)

            if self.alive2:
                if key == "up":
                    handled = self._queue_direction(Direction.UP, player=2)
                elif key == "down":
                    handled = self._queue_direction(Direction.DOWN, player=2)
                elif key == "left":
                    handled = self._queue_direction(Direction.LEFT, player=2)
                elif key == "right":
                    handled = self._queue_direction(Direction.RIGHT, player=2)
        else:
            movement_keys = {
                "w": Direction.UP,
                "up": Direction.UP,
                "s": Direction.DOWN,
                "down": Direction.DOWN,
                "a": Direction.LEFT,
                "left": Direction.LEFT,
                "d": Direction.RIGHT,
                "right": Direction.RIGHT,
            }
            if key in movement_keys:
                handled = self._queue_direction(movement_keys[key])

        if handled:
            event.stop()

    def action_toggle_pause(self) -> None:
        """Pause or resume the game."""

        if self.game_over:
            return
        self.paused = not self.paused
        self.last_message = (
            "Paused. Breathe, then press Space."
            if self.paused
            else "Back in motion."
        )
        self._update_display()

    def action_restart(self) -> None:
        """Restart the current mode while preserving high score."""

        self._reset_game_state(reset_high_score=False)
        self.last_message = "Fresh board. Good luck."
        self._update_display()

    def _restart_game(self) -> None:
        """Backward-compatible restart helper for tests and direct calls."""

        self.action_restart()


RGBColor = tuple[int, int, int]


def rgb(hex_color: str) -> RGBColor:
    """Convert a #rrggbb color into an RGB tuple."""

    color = hex_color.lstrip("#")
    return (
        int(color[0:2], 16),
        int(color[2:4], 16),
        int(color[4:6], 16),
    )


KITTY_COLORS = {
    "background": rgb("#07100c"),
    "grid": rgb("#10241d"),
    "food": rgb("#ffcc66"),
    "food_core": rgb("#fff2a3"),
    "head1": rgb("#7dff9b"),
    "body1": rgb("#38d878"),
    "body1_glow": rgb("#a7ffc0"),
    "body1_shadow": rgb("#143320"),
    "head2": rgb("#7cc7ff"),
    "body2": rgb("#4d8dff"),
    "body2_glow": rgb("#b7dcff"),
    "body2_shadow": rgb("#142842"),
    "dead": rgb("#d45d5d"),
    "eye": rgb("#07100c"),
    "eye_glint": rgb("#f4fff8"),
}


class PixelBuffer:
    """Small RGB drawing surface for Kitty graphics frames."""

    def __init__(self, width: int, height: int, background: RGBColor):
        self.width = width
        self.height = height
        self.data = bytearray(background * (width * height))

    def blend_pixel(self, x: int, y: int, color: RGBColor, alpha: float = 1.0) -> None:
        """Blend a single pixel, clipping silently outside the image."""

        if x < 0 or x >= self.width or y < 0 or y >= self.height or alpha <= 0:
            return

        alpha = min(1.0, alpha)
        index = (y * self.width + x) * 3
        inverse = 1.0 - alpha
        self.data[index] = int(self.data[index] * inverse + color[0] * alpha)
        self.data[index + 1] = int(self.data[index + 1] * inverse + color[1] * alpha)
        self.data[index + 2] = int(self.data[index + 2] * inverse + color[2] * alpha)

    def draw_rect(self, x: int, y: int, width: int, height: int, color: RGBColor) -> None:
        """Draw a clipped solid rectangle."""

        start_x = max(0, x)
        end_x = min(self.width, x + width)
        start_y = max(0, y)
        end_y = min(self.height, y + height)
        for pixel_y in range(start_y, end_y):
            row_start = (pixel_y * self.width + start_x) * 3
            row_end = (pixel_y * self.width + end_x) * 3
            self.data[row_start:row_end] = bytes(color) * (end_x - start_x)

    def draw_circle(
        self,
        center_x: float,
        center_y: float,
        radius: float,
        color: RGBColor,
        opacity: float = 1.0,
    ) -> None:
        """Draw an anti-aliased filled circle."""

        min_x = math.floor(center_x - radius - 1)
        max_x = math.ceil(center_x + radius + 1)
        min_y = math.floor(center_y - radius - 1)
        max_y = math.ceil(center_y + radius + 1)

        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                distance = math.hypot((x + 0.5) - center_x, (y + 0.5) - center_y)
                alpha = (radius + 0.55 - distance) * opacity
                if alpha > 0:
                    self.blend_pixel(x, y, color, alpha)

    def draw_ellipse(
        self,
        center_x: float,
        center_y: float,
        radius_x: float,
        radius_y: float,
        angle: float,
        color: RGBColor,
        opacity: float = 1.0,
    ) -> None:
        """Draw an anti-aliased filled ellipse rotated around its center."""

        cos_angle = math.cos(angle)
        sin_angle = math.sin(angle)
        bound = max(radius_x, radius_y) + 1
        min_x = math.floor(center_x - bound)
        max_x = math.ceil(center_x + bound)
        min_y = math.floor(center_y - bound)
        max_y = math.ceil(center_y + bound)
        softness = 0.65 / max(1.0, min(radius_x, radius_y))

        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                dx = (x + 0.5) - center_x
                dy = (y + 0.5) - center_y
                local_x = dx * cos_angle + dy * sin_angle
                local_y = -dx * sin_angle + dy * cos_angle
                distance = math.hypot(local_x / radius_x, local_y / radius_y)
                alpha = ((1.0 + softness) - distance) / softness * opacity
                if alpha > 0:
                    self.blend_pixel(x, y, color, alpha)

    def draw_line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        radius: float,
        color: RGBColor,
        opacity: float = 1.0,
    ) -> None:
        """Draw a rounded thick line by stamping anti-aliased circles."""

        start_x, start_y = start
        end_x, end_y = end
        distance = math.hypot(end_x - start_x, end_y - start_y)
        steps = max(1, int(distance / max(1.0, radius * 0.45)))

        for step in range(steps + 1):
            progress = step / steps
            x = start_x + (end_x - start_x) * progress
            y = start_y + (end_y - start_y) * progress
            self.draw_circle(x, y, radius, color, opacity)

    def draw_diamond(
        self,
        center_x: float,
        center_y: float,
        radius: float,
        color: RGBColor,
        opacity: float = 1.0,
    ) -> None:
        """Draw an anti-aliased diamond marker."""

        min_x = math.floor(center_x - radius - 1)
        max_x = math.ceil(center_x + radius + 1)
        min_y = math.floor(center_y - radius - 1)
        max_y = math.ceil(center_y + radius + 1)

        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                distance = (
                    abs((x + 0.5) - center_x)
                    + abs((y + 0.5) - center_y)
                )
                alpha = (radius + 0.6 - distance) * opacity
                if alpha > 0:
                    self.blend_pixel(x, y, color, alpha)


class KittySnakeRenderer:
    """Render the snake board as RGB pixels for Kitty graphics."""

    def __init__(
        self,
        width: int,
        height: int,
        cell_pixels: int = KITTY_CELL_PIXELS,
    ):
        self.width = width
        self.height = height
        self.cell_pixels = cell_pixels
        self.pixel_width = width * cell_pixels
        self.pixel_height = height * cell_pixels

    def render(
        self,
        game: SnakeGame,
        progress: float,
    ) -> bytes:
        """Return one RGB frame for the current game state."""

        buffer = PixelBuffer(
            self.pixel_width,
            self.pixel_height,
            KITTY_COLORS["background"],
        )
        self._draw_grid(buffer)

        if game.food:
            self._draw_food(buffer, game.food)

        if game.two_player:
            for pos in game.dead_bodies:
                self._draw_cell_dot(buffer, pos, KITTY_COLORS["dead"], 0.28)

            if game.alive1:
                self._draw_snake(
                    buffer,
                    game,
                    game.snake1,
                    game._previous_snake1,
                    game.direction1,
                    KITTY_COLORS["body1"],
                    KITTY_COLORS["body1_glow"],
                    KITTY_COLORS["body1_shadow"],
                    KITTY_COLORS["head1"],
                    progress,
                )
            if game.alive2:
                self._draw_snake(
                    buffer,
                    game,
                    game.snake2,
                    game._previous_snake2,
                    game.direction2,
                    KITTY_COLORS["body2"],
                    KITTY_COLORS["body2_glow"],
                    KITTY_COLORS["body2_shadow"],
                    KITTY_COLORS["head2"],
                    progress,
                )
        else:
            self._draw_snake(
                buffer,
                game,
                game.snake,
                game._previous_snake,
                game.direction,
                KITTY_COLORS["body1"],
                KITTY_COLORS["body1_glow"],
                KITTY_COLORS["body1_shadow"],
                KITTY_COLORS["head1"],
                progress,
            )

        return bytes(buffer.data)

    def _draw_grid(self, buffer: PixelBuffer) -> None:
        """Draw a restrained board grid into the pixel buffer."""

        for col in range(self.width + 1):
            x = col * self.cell_pixels
            buffer.draw_rect(x, 0, 1, buffer.height, KITTY_COLORS["grid"])
        for row in range(self.height + 1):
            y = row * self.cell_pixels
            buffer.draw_rect(0, y, buffer.width, 1, KITTY_COLORS["grid"])

    def _center(self, row: float, col: float) -> tuple[float, float]:
        """Convert a logical board position to pixel center coordinates."""

        return (
            (col + 0.5) * self.cell_pixels,
            (row + 0.5) * self.cell_pixels,
        )

    def _draw_cell_dot(
        self,
        buffer: PixelBuffer,
        position: Position,
        color: RGBColor,
        radius_ratio: float,
    ) -> None:
        """Draw a circular marker at an integer board position."""

        center_x, center_y = self._center(float(position.row), float(position.col))
        buffer.draw_circle(center_x, center_y, self.cell_pixels * radius_ratio, color)

    def _draw_food(
        self,
        buffer: PixelBuffer,
        position: Position,
    ) -> None:
        """Draw a glowing food pellet."""

        center_x, center_y = self._center(float(position.row), float(position.col))
        buffer.draw_circle(center_x, center_y, self.cell_pixels * 0.34, KITTY_COLORS["food"])
        buffer.draw_circle(
            center_x - self.cell_pixels * 0.08,
            center_y - self.cell_pixels * 0.08,
            self.cell_pixels * 0.14,
            KITTY_COLORS["food_core"],
        )

    def _draw_snake(
        self,
        buffer: PixelBuffer,
        game: SnakeGame,
        snake: list[Position],
        previous_snake: list[Position],
        direction: Direction,
        body_color: RGBColor,
        highlight_color: RGBColor,
        shadow_color: RGBColor,
        head_color: RGBColor,
        progress: float,
    ) -> None:
        """Draw a continuous rounded snake body and expressive head."""

        positions = game._interpolated_snake(snake, previous_snake, progress)
        if not positions:
            return

        pixel_positions = [self._center(row, col) for row, col in positions]
        smooth_path = self._smooth_path(pixel_positions)
        self._draw_tapered_path(
            buffer,
            smooth_path,
            shadow_color,
            radius_scale=1.18,
            opacity=0.5,
            offset=(self.cell_pixels * 0.08, self.cell_pixels * 0.10),
        )
        self._draw_tapered_path(buffer, smooth_path, body_color)
        self._draw_tapered_highlight(buffer, smooth_path, highlight_color)

        head_x, head_y = smooth_path[0]
        head_radius = self.cell_pixels * 0.38
        self._draw_head(buffer, head_x, head_y, head_radius, direction, head_color)

    def _smooth_path(
        self,
        points: list[tuple[float, float]],
    ) -> list[tuple[float, float]]:
        """Round sharp 90-degree corners in a head-to-tail centerline."""

        if len(points) < 3:
            return points

        smoothed: list[tuple[float, float]] = [points[0]]
        corner_radius = self.cell_pixels * 0.45

        for index in range(1, len(points) - 1):
            previous_point = points[index - 1]
            point = points[index]
            next_point = points[index + 1]
            incoming = (previous_point[0] - point[0], previous_point[1] - point[1])
            outgoing = (next_point[0] - point[0], next_point[1] - point[1])
            incoming_length = math.hypot(*incoming)
            outgoing_length = math.hypot(*outgoing)

            if incoming_length == 0 or outgoing_length == 0:
                continue

            incoming_unit = (incoming[0] / incoming_length, incoming[1] / incoming_length)
            outgoing_unit = (outgoing[0] / outgoing_length, outgoing[1] / outgoing_length)
            dot = incoming_unit[0] * outgoing_unit[0] + incoming_unit[1] * outgoing_unit[1]

            if abs(dot) > 0.98:
                smoothed.append(point)
                continue

            radius = min(corner_radius, incoming_length * 0.48, outgoing_length * 0.48)
            enter = (
                point[0] + incoming_unit[0] * radius,
                point[1] + incoming_unit[1] * radius,
            )
            exit_point = (
                point[0] + outgoing_unit[0] * radius,
                point[1] + outgoing_unit[1] * radius,
            )
            smoothed.append(enter)

            samples = max(4, int(radius / 2))
            for sample in range(1, samples):
                t = sample / samples
                one_minus_t = 1.0 - t
                curve_x = (
                    one_minus_t * one_minus_t * enter[0]
                    + 2 * one_minus_t * t * point[0]
                    + t * t * exit_point[0]
                )
                curve_y = (
                    one_minus_t * one_minus_t * enter[1]
                    + 2 * one_minus_t * t * point[1]
                    + t * t * exit_point[1]
                )
                smoothed.append((curve_x, curve_y))

            smoothed.append(exit_point)

        smoothed.append(points[-1])
        return smoothed

    def _path_length(self, points: list[tuple[float, float]]) -> float:
        """Return total length of a pixel path."""

        return sum(
            math.hypot(
                points[index][0] - points[index - 1][0],
                points[index][1] - points[index - 1][1],
            )
            for index in range(1, len(points))
        )

    def _body_radius(self, path_progress: float) -> float:
        """Return a tapered body radius along the head-to-tail path."""

        base = self.cell_pixels * 0.24
        if path_progress < 0.12:
            return base * (0.9 + path_progress / 0.12 * 0.1)
        if path_progress > 0.72:
            tail_progress = (path_progress - 0.72) / 0.28
            return base * (1.0 - 0.62 * tail_progress)
        return base

    def _draw_tapered_path(
        self,
        buffer: PixelBuffer,
        path: list[tuple[float, float]],
        color: RGBColor,
        radius_scale: float = 1.0,
        opacity: float = 1.0,
        offset: tuple[float, float] = (0.0, 0.0),
    ) -> None:
        """Draw the body as a continuous tube with a subtle tapered tail."""

        total_length = max(1.0, self._path_length(path))
        traveled = 0.0

        for index in range(1, len(path)):
            start_x, start_y = path[index - 1]
            end_x, end_y = path[index]
            segment_length = math.hypot(end_x - start_x, end_y - start_y)
            steps = max(1, int(segment_length / max(1.0, self.cell_pixels * 0.12)))

            for step in range(steps + 1):
                segment_progress = step / steps
                distance = traveled + segment_length * segment_progress
                path_progress = min(1.0, distance / total_length)
                radius = self._body_radius(path_progress) * radius_scale
                x = start_x + (end_x - start_x) * segment_progress + offset[0]
                y = start_y + (end_y - start_y) * segment_progress + offset[1]
                buffer.draw_circle(x, y, radius, color, opacity)

            traveled += segment_length

    def _draw_tapered_highlight(
        self,
        buffer: PixelBuffer,
        path: list[tuple[float, float]],
        color: RGBColor,
    ) -> None:
        """Paint a small highlight along the front half of the snake body."""

        total_length = max(1.0, self._path_length(path))
        traveled = 0.0

        for index in range(1, len(path)):
            start_x, start_y = path[index - 1]
            end_x, end_y = path[index]
            segment_length = math.hypot(end_x - start_x, end_y - start_y)
            steps = max(1, int(segment_length / max(1.0, self.cell_pixels * 0.22)))

            for step in range(steps + 1):
                segment_progress = step / steps
                distance = traveled + segment_length * segment_progress
                path_progress = min(1.0, distance / total_length)
                if path_progress > 0.72:
                    continue
                x = start_x + (end_x - start_x) * segment_progress
                y = start_y + (end_y - start_y) * segment_progress
                buffer.draw_circle(
                    x - self.cell_pixels * 0.05,
                    y - self.cell_pixels * 0.10,
                    self._body_radius(path_progress) * 0.32,
                    color,
                    opacity=0.32,
                )

            traveled += segment_length

    def _draw_head(
        self,
        buffer: PixelBuffer,
        head_x: float,
        head_y: float,
        head_radius: float,
        direction: Direction,
        head_color: RGBColor,
    ) -> None:
        """Draw an oriented, slightly elongated snake head."""

        row_delta, col_delta = direction.value
        angle = math.atan2(float(row_delta), float(col_delta))
        forward_x = float(col_delta)
        forward_y = float(row_delta)

        buffer.draw_ellipse(
            head_x + forward_x * head_radius * 0.12,
            head_y + forward_y * head_radius * 0.12,
            head_radius * 1.15,
            head_radius * 0.88,
            angle,
            head_color,
        )
        buffer.draw_circle(
            head_x + forward_x * head_radius * 0.68,
            head_y + forward_y * head_radius * 0.68,
            head_radius * 0.34,
            head_color,
            opacity=0.9,
        )
        self._draw_eyes(buffer, head_x, head_y, head_radius, direction)

    def _draw_eyes(
        self,
        buffer: PixelBuffer,
        head_x: float,
        head_y: float,
        head_radius: float,
        direction: Direction,
    ) -> None:
        """Draw tiny directional eyes on the snake head."""

        row_delta, col_delta = direction.value
        forward_x = float(col_delta)
        forward_y = float(row_delta)
        side_x = -forward_y
        side_y = forward_x
        eye_forward = head_radius * 0.34
        eye_side = head_radius * 0.42
        eye_radius = max(1.4, head_radius * 0.17)
        pupil_radius = max(0.8, eye_radius * 0.45)

        for side in (-1, 1):
            eye_x = head_x + forward_x * eye_forward + side_x * eye_side * side
            eye_y = head_y + forward_y * eye_forward + side_y * eye_side * side
            buffer.draw_circle(eye_x, eye_y, eye_radius, KITTY_COLORS["eye_glint"])
            buffer.draw_circle(eye_x, eye_y, pupil_radius, KITTY_COLORS["eye"])


def kitty_graphics_chunks(
    rgb_data: bytes,
    image_width: int,
    image_height: int,
    columns: int,
    rows: int,
    image_id: int = KITTY_IMAGE_ID,
    placement_id: int = KITTY_PLACEMENT_ID,
) -> list[str]:
    """Return chunked Kitty graphics commands for one RGB frame."""

    compressed = zlib.compress(rgb_data, level=1)
    payload = base64.standard_b64encode(compressed).decode("ascii")
    chunks = [
        payload[index:index + KITTY_CHUNK_SIZE]
        for index in range(0, len(payload), KITTY_CHUNK_SIZE)
    ] or [""]
    commands: list[str] = []

    for index, chunk in enumerate(chunks):
        more = 0 if index == len(chunks) - 1 else 1
        if index == 0:
            control = (
                "a=T,f=24,o=z,"
                f"s={image_width},v={image_height},"
                f"i={image_id},p={placement_id},"
                f"c={columns},r={rows},C=1,q=2,m={more}"
            )
        else:
            control = f"q=2,m={more}"
        commands.append(f"\033_G{control};{chunk}\033\\")

    return commands


class KittySnakeGame:
    """Raw-terminal Snake runner using Kitty graphics for pixel animation."""

    def __init__(
        self,
        width: int,
        height: int,
        speed: int,
        two_player: bool,
    ):
        self.game = SnakeGame(
            width,
            height,
            speed,
            two_player,
            ascii_only=False,
            render_mode=RENDER_MODE_CLASSIC,
        )
        self.renderer = KittySnakeRenderer(width, height)
        self.width = width
        self.height = height
        self.two_player = two_player
        self.input_buffer = b""
        self.running = True
        self.next_tick = time.monotonic() + self.game._logic_interval
        self.last_frame_at = time.monotonic()

    def run(self) -> None:
        """Run the raw terminal game loop."""

        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise click.ClickException("--mode-kitty requires an interactive terminal.")

        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setcbreak(sys.stdin.fileno())
            sys.stdout.write("\033[?1049h\033[?25l\033[2J")
            sys.stdout.flush()
            self._run_loop()
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            sys.stdout.write(
                f"\033_Ga=d,d=I,i={KITTY_IMAGE_ID},q=2;\033\\"
                "\033[2J\033[?25h\033[?1049l"
            )
            sys.stdout.flush()

    def _run_loop(self) -> None:
        """Drive input, logic, and 60 FPS rendering."""

        frame_interval = 1 / KITTY_RENDER_FPS
        next_frame = time.monotonic()

        while self.running:
            now = time.monotonic()
            self.last_frame_at = now
            self._handle_input(now)

            if not self.game.paused and not self.game.game_over:
                while now >= self.next_tick:
                    self._advance_game()
                    logic_interval = self._logic_interval()
                    self.next_tick += logic_interval
                    if now - self.next_tick > logic_interval:
                        self.next_tick = now + logic_interval

            if now >= next_frame:
                self._render_frame()
                next_frame += frame_interval
                if next_frame < now:
                    next_frame = now + frame_interval

            sleep_until = min(self.next_tick, next_frame)
            time.sleep(max(0.001, min(0.01, sleep_until - time.monotonic())))

    def _advance_game(self) -> None:
        """Advance the shared game logic by one step."""

        self.game._begin_step_animation()
        self.game.ticks += 1
        if self.game.two_player:
            self.game._update_two_player()
        else:
            self.game._update_single_player()

    def _logic_interval(self) -> float:
        """Return the current game tick interval."""

        return self.game._logic_interval

    def _animation_progress(self) -> float:
        """Return current pixel interpolation progress."""

        if self.game.paused or self.game.game_over:
            return 1.0
        elapsed = time.monotonic() - self.game._animation_started_at
        return min(1.0, max(0.0, elapsed / self._logic_interval()))

    def _handle_input(self, now: float) -> None:
        """Read and apply all currently available keyboard input."""

        fd = sys.stdin.fileno()
        while select.select([fd], [], [], 0)[0]:
            self.input_buffer += os.read(fd, 32)

        for key in self._consume_keys():
            if key in {"q", "\x03"}:
                self.running = False
                return
            if key == "space":
                self.game.action_toggle_pause()
                self.next_tick = now + self._logic_interval()
                continue
            if key == "r":
                self.game.action_restart()
                self.next_tick = now + self._logic_interval()
                continue
            self._queue_movement(key)

    def _consume_keys(self) -> list[str]:
        """Parse raw terminal bytes into normalized key names."""

        keys: list[str] = []
        while self.input_buffer:
            if self.input_buffer.startswith(b"\x1b["):
                if len(self.input_buffer) < 3:
                    break
                arrow_key = {
                    b"A": "up",
                    b"B": "down",
                    b"C": "right",
                    b"D": "left",
                }.get(self.input_buffer[2:3])
                self.input_buffer = self.input_buffer[3:]
                if arrow_key:
                    keys.append(arrow_key)
                continue

            byte = self.input_buffer[:1]
            self.input_buffer = self.input_buffer[1:]
            if byte == b" ":
                keys.append("space")
            elif byte in {b"q", b"Q"}:
                keys.append("q")
            elif byte in {b"r", b"R"}:
                keys.append("r")
            elif byte == b"\x03":
                keys.append("\x03")
            else:
                character = byte.decode("ascii", errors="ignore").lower()
                if character in {"w", "a", "s", "d"}:
                    keys.append(character)

        return keys

    def _queue_movement(self, key: str) -> None:
        """Map normalized keys to the shared game direction queue."""

        if self.game.two_player:
            if self.game.alive1:
                player1_keys = {
                    "w": Direction.UP,
                    "s": Direction.DOWN,
                    "a": Direction.LEFT,
                    "d": Direction.RIGHT,
                }
                if key in player1_keys:
                    self.game._queue_direction(player1_keys[key], player=1)
            if self.game.alive2:
                player2_keys = {
                    "up": Direction.UP,
                    "down": Direction.DOWN,
                    "left": Direction.LEFT,
                    "right": Direction.RIGHT,
                }
                if key in player2_keys:
                    self.game._queue_direction(player2_keys[key], player=2)
            return

        movement_keys = {
            "w": Direction.UP,
            "up": Direction.UP,
            "s": Direction.DOWN,
            "down": Direction.DOWN,
            "a": Direction.LEFT,
            "left": Direction.LEFT,
            "d": Direction.RIGHT,
            "right": Direction.RIGHT,
        }
        if key in movement_keys:
            self.game._queue_direction(movement_keys[key])

    def _render_frame(self) -> None:
        """Render one Kitty graphics frame plus text HUD."""

        progress = self._animation_progress()
        rgb_data = self.renderer.render(self.game, progress)
        columns = self.width * 2
        rows = self.height
        commands = kitty_graphics_chunks(
            rgb_data,
            self.renderer.pixel_width,
            self.renderer.pixel_height,
            columns,
            rows,
        )

        sys.stdout.write("\033[H\033[2K")
        sys.stdout.write("\033[1;38;2;125;255;155muvpy.run Snake\033[0m")
        sys.stdout.write("  \033[2mkitty pixel mode\033[0m")
        sys.stdout.write("\033[2;1H\033[2K")
        sys.stdout.write(self._score_line())
        sys.stdout.write("\033[3;1H")
        for command in commands:
            sys.stdout.write(command)
        sys.stdout.write(f"\033[{self.height + 4};1H\033[2K")
        sys.stdout.write(self._message_line())
        sys.stdout.write(f"\033[{self.height + 5};1H\033[2K")
        sys.stdout.write(self._controls_line())
        sys.stdout.flush()

    def _score_line(self) -> str:
        """Return a terminal-colored score line."""

        if self.game.two_player:
            p1_state = "alive" if self.game.alive1 else "out"
            p2_state = "alive" if self.game.alive2 else "out"
            return (
                f"\033[38;2;125;255;155mP1 {self.game.score1} ({p1_state})\033[0m  "
                f"\033[38;2;124;199;255mP2 {self.game.score2} ({p2_state})\033[0m  "
                f"\033[38;2;255;204;102mbest {self.game.high_score}\033[0m  "
                f"\033[2mspeed {self.game.speed}/15\033[0m"
            )
        return (
            f"\033[38;2;125;255;155mscore {self.game.score}\033[0m  "
            f"\033[38;2;255;204;102mbest {self.game.high_score}\033[0m  "
            f"\033[2mfood {self.game.food_eaten}  speed {self.game.speed}/15\033[0m"
        )

    def _message_line(self) -> str:
        """Return the current game message with simple ANSI styling."""

        if self.game.game_over and not self.game.won:
            color = "255;107;107"
        elif self.game.paused:
            color = "255;204;102"
        else:
            color = "219;255;233"
        return f"\033[38;2;{color}m{self.game.last_message}\033[0m"

    def _controls_line(self) -> str:
        """Return mode-specific controls for the raw terminal HUD."""

        if self.game.two_player:
            controls = "P1 WASD  P2 arrows  Space pause  R restart  Q quit"
        else:
            controls = "WASD or arrows move  Space pause  R restart  Q quit"
        return f"\033[2m{controls}\033[0m"


@click.command(help="Run a polished Snake game in your terminal.")
@click.option(
    "--width",
    "-w",
    default=DEFAULT_WIDTH,
    show_default=True,
    help="Game board width in cells.",
    type=click.IntRange(10, 50),
)
@click.option(
    "--height",
    "-h",
    default=DEFAULT_HEIGHT,
    show_default=True,
    help="Game board height in cells.",
    type=click.IntRange(8, 30),
)
@click.option(
    "--speed",
    "-s",
    default=DEFAULT_SPEED,
    show_default=True,
    help="Game speed from 1 to 15; higher is faster.",
    type=click.IntRange(1, 15),
)
@click.option(
    "--two-player",
    "-2",
    is_flag=True,
    help="Enable local two-player mode.",
)
@click.option(
    "--ascii",
    "ascii_only",
    is_flag=True,
    help="Use ASCII-safe board glyphs for older terminals.",
)
@click.option(
    "--mode-classic",
    is_flag=True,
    help="Use the original one-cell terminal renderer.",
)
@click.option(
    "--mode-smooth",
    is_flag=True,
    help="Use the 60 FPS Braille sub-cell renderer (default).",
)
@click.option(
    "--mode-kitty",
    is_flag=True,
    help="Use Kitty graphics for true pixel animation.",
)
def main(
    width: int,
    height: int,
    speed: int,
    two_player: bool,
    ascii_only: bool,
    mode_classic: bool,
    mode_smooth: bool,
    mode_kitty: bool,
) -> None:
    """
    Classic Snake in the terminal.

    Eat food to grow and score points. Avoid the walls, your own tail, and the
    other player in two-player mode.
    """

    selected_modes = [mode_classic, mode_smooth, mode_kitty]
    if sum(1 for selected in selected_modes if selected) > 1:
        raise click.UsageError(
            "Choose only one of --mode-classic, --mode-smooth, or --mode-kitty."
        )

    if mode_kitty:
        if ascii_only:
            raise click.UsageError("--ascii cannot be combined with --mode-kitty.")
        KittySnakeGame(width, height, speed, two_player).run()
        return

    render_mode = RENDER_MODE_CLASSIC if mode_classic else RENDER_MODE_SMOOTH
    app = SnakeGame(width, height, speed, two_player, ascii_only, render_mode)
    app.run()


if __name__ == "__main__":
    main()
