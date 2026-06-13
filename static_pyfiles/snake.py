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
full-screen command-line game, uses styled terminal rendering, and lets you tune
the board size, speed, player count, and glyph compatibility from the command
line.

Version: 1.0.0
Category: Game
Author: UVPY.RUN

Usage Examples:
    uv run snake.py --width 32 --height 18 --speed 7
    uv run snake.py
    uv run snake.py -w 24 -h 14 -s 4
    uv run snake.py --two-player --width 40 --height 20 --speed 6
    uv run snake.py --ascii

Use It For:
    - Trying a real interactive terminal app from one uv command
    - Demoing PEP 723 dependency metadata with Textual installed on demand
    - Playing a quick keyboard game without cloning a repository
    - Checking how Rich styling and Textual key bindings feel in a small script

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

import random
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
DEFAULT_SPEED = 7
STARTING_LENGTH = 3
POINTS_PER_FOOD = 10

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
    ):
        super().__init__()
        self.width = width
        self.height = height
        self.speed = speed
        self.two_player = two_player
        self.ascii_only = ascii_only

        self.game_display: Static | None = None
        self.food: Optional[Position] = None
        self.paused = False
        self.won = False
        self.high_score = 0
        self.food_eaten = 0
        self.ticks = 0
        self.last_message = "Eat food, grow longer, and keep moving."

        self._reset_game_state(reset_high_score=True)

    def compose(self) -> ComposeResult:
        """Create Textual widgets for the game shell."""

        yield Header(show_clock=True)
        self.game_display = Static("", id="game")
        yield self.game_display
        yield Footer()

    def on_mount(self) -> None:
        """Start the game timer when the app mounts."""

        self.set_interval(self._tick_interval(), self._game_loop)
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

        glyphs = ASCII_GLYPHS if self.ascii_only else GLYPHS
        board_text = Text()
        for row_index, row in enumerate(self._board_cells()):
            for cell in row:
                board_text.append(glyphs[cell], style=CELL_STYLES[cell])
                board_text.append(" ")
            if row_index < self.height - 1:
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
        heading.append(
            "two-player" if self.two_player else "single-player",
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


@click.command(help="Run a polished Textual Snake game in your terminal.")
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
def main(
    width: int,
    height: int,
    speed: int,
    two_player: bool,
    ascii_only: bool,
) -> None:
    """
    Classic Snake in the terminal.

    Eat food to grow and score points. Avoid the walls, your own tail, and the
    other player in two-player mode.
    """

    app = SnakeGame(width, height, speed, two_player, ascii_only)
    app.run()


if __name__ == "__main__":
    main()
