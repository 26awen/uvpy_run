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
Arcade Breakout with catchable power-ups

A standalone Tkinter arcade game that keeps the uvpy.run script lightweight
while adding stronger Breakout game feel: neon visuals, catchable power-ups,
combo scoring, multi-ball chaos, later-wave armored bricks, particles, screen
shake, pause/restart controls, and generated sound-effect fallbacks.

Version: 1.0.0
Category: Game
Author: UVPY.RUN

Usage Examples:
    uv run brick.py
    uv run brick.py --difficulty hard --speed 1.35 --special-chance 0.25
    uv run brick.py -d easy -s 0.8 -c 0.35 --muted

Game Controls:
    - LEFT/RIGHT Arrow Keys or A/D: Move paddle
    - Mouse: Move paddle directly
    - SPACE: Launch ball, continue, or resume
    - P: Pause or resume
    - R: Restart
    - Q or Escape: Quit

Special Bricks:
    - M (Multi Ball): Drops a token that creates extra balls when caught
    - S (Speed Up): Drops a token that increases ball speed
    - E (Expand Paddle): Drops a temporary wider paddle token
    - + (Extra Life): Drops an extra life token
    - $ (Bonus Score): Drops a combo-friendly score token

Audio Notes:
    - No external sound files are required
    - Windows uses standard-library pitched beeps
    - macOS/Linux try generated temporary WAV files with system players
    - If audio playback is unavailable, the game falls back to the Tk bell
"""

from __future__ import annotations

import atexit
import math
import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
import wave
from dataclasses import dataclass
from enum import Enum

import click


CANVAS_WIDTH = 900
CANVAS_HEIGHT = 640
FRAME_MS = 16
PADDLE_Y = CANVAS_HEIGHT - 62
START_BALL_Y_OFFSET = 26
MAX_BALLS = 6
MAX_BALL_SPEED = 14.0
MIN_BALL_SPEED = 4.2
COMBO_TIMEOUT_FRAMES = 150
PADDLE_BOOST_FRAMES = 650
WAVE_SPEED_BONUS = 1.06

MODE_READY = "ready"
MODE_PLAYING = "playing"
MODE_PAUSED = "paused"
MODE_LEVEL_CLEAR = "level_clear"
MODE_GAME_OVER = "game_over"

NEON_TEXT = "#d9fff7"
DIM_TEXT = "#76b8aa"
BG = "#05080f"
GRID = "#10202b"
PADDLE_FILL = "#25d6ff"
PADDLE_EDGE = "#ffffff"
BALL_FILL = "#f8fffb"
BALL_GLOW = "#43ffd0"

ROW_COLORS = [
    "#ff4d6d",
    "#ff8c42",
    "#ffd166",
    "#72ef36",
    "#06d6a0",
    "#4cc9f0",
    "#7b2cff",
    "#d946ef",
    "#ff3d91",
    "#5bf0ff",
]

SPECIAL_TYPES = [
    "multi_ball",
    "speed_up",
    "expand_paddle",
    "extra_life",
    "bonus_score",
]


class BrickType(Enum):
    """Types of bricks and their catchable power-up drops."""

    NORMAL = "normal"
    MULTI_BALL = "multi_ball"
    SPEED_UP = "speed_up"
    EXPAND_PADDLE = "expand_paddle"
    EXTRA_LIFE = "extra_life"
    BONUS_SCORE = "bonus_score"


BRICK_MARKERS = {
    BrickType.MULTI_BALL: "M",
    BrickType.SPEED_UP: "S",
    BrickType.EXPAND_PADDLE: "E",
    BrickType.EXTRA_LIFE: "+",
    BrickType.BONUS_SCORE: "$",
}

POWERUP_NAMES = {
    BrickType.MULTI_BALL: "Multi-ball",
    BrickType.SPEED_UP: "Speed up",
    BrickType.EXPAND_PADDLE: "Wide paddle",
    BrickType.EXTRA_LIFE: "Extra life",
    BrickType.BONUS_SCORE: "Bonus score",
}

POWERUP_COLORS = {
    BrickType.MULTI_BALL: "#ffd166",
    BrickType.SPEED_UP: "#ff4d6d",
    BrickType.EXPAND_PADDLE: "#4cc9f0",
    BrickType.EXTRA_LIFE: "#72ef36",
    BrickType.BONUS_SCORE: "#d946ef",
}

SCORE_BY_BRICK_TYPE = {
    BrickType.NORMAL: 10,
    BrickType.MULTI_BALL: 20,
    BrickType.SPEED_UP: 18,
    BrickType.EXPAND_PADDLE: 18,
    BrickType.EXTRA_LIFE: 25,
    BrickType.BONUS_SCORE: 35,
}

SOUND_PROFILES = {
    "wall": (440, 35),
    "paddle": (660, 45),
    "brick": (880, 50),
    "powerup": (1046, 80),
    "miss": (180, 120),
    "level": (784, 140),
    "game_over": (140, 220),
}


@dataclass(frozen=True)
class DifficultySettings:
    """Resolved values after applying difficulty and CLI multipliers."""

    speed_multiplier: float
    special_chance: float
    lives: int
    rows: int
    cols: int
    paddle_width: int


@dataclass
class Particle:
    """A short-lived visual spark emitted by collisions and power-ups."""

    item_id: int
    dx: float
    dy: float
    life: int
    radius: float


@dataclass
class FloatingText:
    """Score and status text that floats away after a collision."""

    item_id: int
    dy: float
    life: int


def clamp(value: float, lower: float, upper: float) -> float:
    """Return value constrained to the inclusive range."""

    return max(lower, min(upper, value))


def resolve_difficulty(
    difficulty: str,
    speed: float,
    special_chance: float,
) -> DifficultySettings:
    """Resolve user options into the small tuning set used by the game."""

    presets = {
        "easy": {
            "speed": 0.82,
            "special": 1.55,
            "lives": 4,
            "rows": 7,
            "cols": 11,
            "paddle": 150,
        },
        "normal": {
            "speed": 1.0,
            "special": 1.0,
            "lives": 3,
            "rows": 8,
            "cols": 12,
            "paddle": 132,
        },
        "hard": {
            "speed": 1.28,
            "special": 0.82,
            "lives": 3,
            "rows": 9,
            "cols": 12,
            "paddle": 112,
        },
    }
    preset = presets[difficulty.lower()]
    return DifficultySettings(
        speed_multiplier=speed * preset["speed"],
        special_chance=clamp(special_chance * preset["special"], 0.0, 0.65),
        lives=preset["lives"],
        rows=preset["rows"],
        cols=preset["cols"],
        paddle_width=preset["paddle"],
    )


class SoundEngine:
    """Generated sound effects with graceful fallbacks and no asset files."""

    def __init__(self, enabled: bool = True, root: tk.Tk | None = None):
        self.enabled = enabled
        self.root = root
        self.player = self._find_system_player()
        self.generated_files: dict[str, str] = {}
        if enabled:
            atexit.register(self.cleanup)

    def attach_root(self, root: tk.Tk) -> None:
        """Attach the Tk root so bell fallback can be used."""

        self.root = root

    def play(self, sound_name: str) -> None:
        """Play a tiny generated sound, or do nothing when disabled."""

        if not self.enabled:
            return

        frequency, duration = SOUND_PROFILES.get(sound_name, SOUND_PROFILES["wall"])

        if sys.platform.startswith("win"):
            self._play_windows_beep(frequency, duration)
            return

        if self.player:
            path = self._get_wave_path(sound_name, frequency, duration)
            if path:
                try:
                    subprocess.Popen(
                        [self.player, path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return
                except OSError:
                    self.player = None

        self._bell()

    def cleanup(self) -> None:
        """Remove temporary audio files created during this process."""

        for path in self.generated_files.values():
            try:
                os.remove(path)
            except OSError:
                pass

    def _play_windows_beep(self, frequency: int, duration: int) -> None:
        def worker() -> None:
            try:
                import winsound

                winsound.Beep(frequency, duration)
            except Exception:
                self._bell()

        threading.Thread(target=worker, daemon=True).start()

    def _bell(self) -> None:
        if not self.root:
            return
        try:
            self.root.bell()
        except tk.TclError:
            pass

    def _find_system_player(self) -> str | None:
        for player in ("afplay", "paplay", "aplay"):
            found = shutil.which(player)
            if found:
                return found
        return None

    def _get_wave_path(self, name: str, frequency: int, duration_ms: int) -> str | None:
        if name in self.generated_files:
            return self.generated_files[name]

        try:
            path = self._write_wave_file(name, frequency, duration_ms)
        except OSError:
            return None

        self.generated_files[name] = path
        return path

    def _write_wave_file(self, name: str, frequency: int, duration_ms: int) -> str:
        sample_rate = 22050
        sample_count = max(1, int(sample_rate * duration_ms / 1000))
        path = os.path.join(tempfile.gettempdir(), f"uvpy_breakout_{name}.wav")

        with wave.open(path, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)

            frames = bytearray()
            for index in range(sample_count):
                t = index / sample_rate
                fade = min(1.0, index / 80, (sample_count - index) / 120)
                value = int(12000 * fade * math.sin(2 * math.pi * frequency * t))
                frames.extend(struct.pack("<h", value))
            wav.writeframes(bytes(frames))

        return path


class Ball:
    """Game ball with glow, speed caps, and paddle-controlled launch."""

    def __init__(
        self,
        canvas: tk.Canvas,
        x: float,
        y: float,
        radius: int = 8,
        speed_multiplier: float = 1.0,
        stuck_to_paddle: bool = False,
    ):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.prev_x = x
        self.prev_y = y
        self.radius = radius
        self.base_speed = clamp(5.2 * speed_multiplier, MIN_BALL_SPEED, MAX_BALL_SPEED)
        self.dx = 0.0
        self.dy = 0.0
        self.stuck_to_paddle = stuck_to_paddle

        self.glow_id = canvas.create_oval(
            x - radius - 5,
            y - radius - 5,
            x + radius + 5,
            y + radius + 5,
            fill="",
            outline=BALL_GLOW,
            width=2,
            tags=("world", "ball"),
        )
        self.ball_id = canvas.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            fill=BALL_FILL,
            outline="#d8fff5",
            width=2,
            tags=("world", "ball"),
        )

    def launch(self, angle_offset: float = 0.0) -> None:
        """Launch a stuck ball upward with a little controllable variety."""

        angle = clamp(angle_offset, -0.85, 0.85)
        speed = self.base_speed
        self.dx = speed * math.sin(angle)
        self.dy = -abs(speed * math.cos(angle))
        self.stuck_to_paddle = False

    def move(self) -> None:
        """Advance the ball and redraw both glow and body."""

        if self.stuck_to_paddle:
            return

        self.prev_x = self.x
        self.prev_y = self.y
        self.x += self.dx
        self.y += self.dy
        self.update_position()

    def set_position(self, x: float, y: float) -> None:
        """Move the ball without changing velocity."""

        self.prev_x = self.x
        self.prev_y = self.y
        self.x = x
        self.y = y
        self.update_position()

    def update_position(self) -> None:
        """Redraw the ball at its logical coordinates."""

        self.canvas.coords(
            self.glow_id,
            self.x - self.radius - 5,
            self.y - self.radius - 5,
            self.x + self.radius + 5,
            self.y + self.radius + 5,
        )
        self.canvas.coords(
            self.ball_id,
            self.x - self.radius,
            self.y - self.radius,
            self.x + self.radius,
            self.y + self.radius,
        )

    def bounce_x(self) -> None:
        self.dx = -self.dx

    def bounce_y(self) -> None:
        self.dy = -self.dy

    def speed_up(self, factor: float = 1.12) -> None:
        """Increase speed while respecting the arcade-friendly cap."""

        self.dx *= factor
        self.dy *= factor
        self.normalize_speed()

    def normalize_speed(self) -> None:
        """Keep the ball from becoming too slow or too fast."""

        speed = math.hypot(self.dx, self.dy)
        if speed == 0:
            return
        target = clamp(speed, MIN_BALL_SPEED, MAX_BALL_SPEED)
        scale = target / speed
        self.dx *= scale
        self.dy *= scale

        if abs(self.dy) < MIN_BALL_SPEED * 0.45:
            self.dy = math.copysign(MIN_BALL_SPEED * 0.45, self.dy or -1)

    def destroy(self) -> None:
        self.canvas.delete(self.glow_id)
        self.canvas.delete(self.ball_id)

    def get_bounds(self) -> tuple[float, float, float, float]:
        return (
            self.x - self.radius,
            self.y - self.radius,
            self.x + self.radius,
            self.y + self.radius,
        )

    def get_previous_bounds(self) -> tuple[float, float, float, float]:
        return (
            self.prev_x - self.radius,
            self.prev_y - self.radius,
            self.prev_x + self.radius,
            self.prev_y + self.radius,
        )


class Paddle:
    """Player paddle with keyboard and mouse control."""

    def __init__(
        self,
        canvas: tk.Canvas,
        x: float,
        y: float,
        width: int = 132,
        height: int = 17,
        speed_multiplier: float = 1.0,
    ):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.original_width = width
        self.width = width
        self.height = height
        self.speed = 13.5 * clamp(speed_multiplier, 0.75, 1.6)
        self.glow_id = canvas.create_rectangle(
            x - width // 2 - 4,
            y - height // 2 - 4,
            x + width // 2 + 4,
            y + height // 2 + 4,
            fill="",
            outline="#135e76",
            width=2,
            tags=("world", "paddle"),
        )
        self.paddle_id = canvas.create_rectangle(
            x - width // 2,
            y - height // 2,
            x + width // 2,
            y + height // 2,
            fill=PADDLE_FILL,
            outline=PADDLE_EDGE,
            width=2,
            tags=("world", "paddle"),
        )
        self.highlight_id = canvas.create_line(
            x - width // 2 + 8,
            y - height // 2 + 4,
            x + width // 2 - 8,
            y - height // 2 + 4,
            fill="#bffff4",
            width=2,
            tags=("world", "paddle"),
        )

    def move_left(self) -> None:
        self.move_by(-self.speed)

    def move_right(self, canvas_width: int) -> None:
        self.move_by(self.speed, canvas_width)

    def move_by(self, dx: float, canvas_width: int = CANVAS_WIDTH) -> None:
        self.move_to(self.x + dx, canvas_width)

    def move_to(self, x: float, canvas_width: int = CANVAS_WIDTH) -> None:
        half = self.width / 2
        self.x = clamp(x, half, canvas_width - half)
        self.update_position()

    def expand(self, factor: float = 1.45) -> None:
        self.width = min(215, int(self.original_width * factor))
        self.update_position()

    def reset_size(self) -> None:
        self.width = self.original_width
        self.update_position()

    def update_position(self) -> None:
        half_width = self.width / 2
        half_height = self.height / 2
        self.canvas.coords(
            self.glow_id,
            self.x - half_width - 4,
            self.y - half_height - 4,
            self.x + half_width + 4,
            self.y + half_height + 4,
        )
        self.canvas.coords(
            self.paddle_id,
            self.x - half_width,
            self.y - half_height,
            self.x + half_width,
            self.y + half_height,
        )
        self.canvas.coords(
            self.highlight_id,
            self.x - half_width + 8,
            self.y - half_height + 4,
            self.x + half_width - 8,
            self.y - half_height + 4,
        )

    def get_bounds(self) -> tuple[float, float, float, float]:
        return (
            self.x - self.width / 2,
            self.y - self.height / 2,
            self.x + self.width / 2,
            self.y + self.height / 2,
        )


class Brick:
    """Destructible brick, including optional later-wave armor."""

    def __init__(
        self,
        canvas: tk.Canvas,
        x: float,
        y: float,
        width: int,
        height: int,
        brick_type: BrickType = BrickType.NORMAL,
        color: str = "#ff4d6d",
        hit_points: int = 1,
    ):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.brick_type = brick_type
        self.hit_points = hit_points
        self.max_hit_points = hit_points
        self.destroyed = False
        self.color = POWERUP_COLORS.get(brick_type, color)
        self.outline = "#faffff" if brick_type != BrickType.NORMAL else "#1b2838"
        self.item_ids: list[int] = []

        self.shadow_id = canvas.create_rectangle(
            x + 3,
            y + 4,
            x + width + 3,
            y + height + 4,
            fill="#02040a",
            outline="",
            tags=("world", "brick"),
        )
        self.brick_id = canvas.create_rectangle(
            x,
            y,
            x + width,
            y + height,
            fill=self.color,
            outline=self.outline,
            width=2,
            tags=("world", "brick"),
        )
        self.highlight_id = canvas.create_line(
            x + 4,
            y + 4,
            x + width - 4,
            y + 4,
            fill="#ffffff",
            width=1,
            tags=("world", "brick"),
        )
        self.item_ids.extend([self.shadow_id, self.brick_id, self.highlight_id])

        self.marker_id: int | None = None
        if brick_type != BrickType.NORMAL:
            self.marker_id = canvas.create_text(
                x + width / 2,
                y + height / 2,
                text=BRICK_MARKERS[brick_type],
                fill="#06101a",
                font=("Arial", 9, "bold"),
                tags=("world", "brick"),
            )
            self.item_ids.append(self.marker_id)

        self.armor_id: int | None = None
        if self.max_hit_points > 1:
            self.armor_id = canvas.create_line(
                x + 7,
                y + height - 5,
                x + width - 7,
                y + height - 5,
                fill="#ffffff",
                width=2,
                tags=("world", "brick"),
            )
            self.item_ids.append(self.armor_id)

    def hit(self) -> bool:
        """Damage the brick and return True when it was destroyed."""

        if self.destroyed:
            return False

        self.hit_points -= 1
        if self.hit_points <= 0:
            self.destroy()
            return True

        self.canvas.itemconfig(self.brick_id, fill="#2f4053", outline="#ffffff")
        if self.armor_id:
            self.canvas.itemconfig(self.armor_id, fill="#ffdd66")
        return False

    def destroy(self) -> None:
        if self.destroyed:
            return
        for item_id in self.item_ids:
            self.canvas.delete(item_id)
        self.destroyed = True

    def get_bounds(self) -> tuple[float, float, float, float]:
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)


class PowerUp:
    """A falling token that applies its effect only when caught."""

    def __init__(self, canvas: tk.Canvas, x: float, y: float, kind: BrickType):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.kind = kind
        self.radius = 13
        self.dy = 2.25
        self.color = POWERUP_COLORS[kind]

        self.token_id = canvas.create_oval(
            x - self.radius,
            y - self.radius,
            x + self.radius,
            y + self.radius,
            fill=self.color,
            outline="#ffffff",
            width=2,
            tags=("world", "powerup"),
        )
        self.text_id = canvas.create_text(
            x,
            y,
            text=BRICK_MARKERS[kind],
            fill="#06101a",
            font=("Arial", 11, "bold"),
            tags=("world", "powerup"),
        )

    def move(self, speed_bonus: float = 1.0) -> None:
        self.y += self.dy * speed_bonus
        self.canvas.coords(
            self.token_id,
            self.x - self.radius,
            self.y - self.radius,
            self.x + self.radius,
            self.y + self.radius,
        )
        self.canvas.coords(self.text_id, self.x, self.y)

    def destroy(self) -> None:
        self.canvas.delete(self.token_id)
        self.canvas.delete(self.text_id)

    def get_bounds(self) -> tuple[float, float, float, float]:
        return (
            self.x - self.radius,
            self.y - self.radius,
            self.x + self.radius,
            self.y + self.radius,
        )


class BreakoutGame:
    """Tkinter Breakout tuned for one-file arcade play."""

    def __init__(
        self,
        difficulty: str = "normal",
        speed_multiplier: float = 1.0,
        special_brick_chance: float = 0.15,
        sound_enabled: bool = True,
    ):
        self.difficulty = difficulty.lower()
        self.settings = resolve_difficulty(
            self.difficulty,
            speed_multiplier,
            special_brick_chance,
        )

        self.root = tk.Tk()
        self.root.title(f"uvpy.run Breakout - {self.difficulty.title()}")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(
            self.root,
            width=CANVAS_WIDTH,
            height=CANVAS_HEIGHT,
            bg=BG,
            highlightthickness=0,
        )
        self.canvas.pack()

        self.sound = SoundEngine(enabled=sound_enabled, root=self.root)
        self.pressed_keys: set[str] = set()

        self.score = 0
        self.high_score = 0
        self.lives = self.settings.lives
        self.level = 1
        self.combo = 0
        self.combo_timer = 0
        self.paddle_boost_timer = 0
        self.mode = MODE_READY
        self.game_running = False
        self.shake_frames = 0
        self.shake_magnitude = 0.0
        self.shake_offset = (0.0, 0.0)

        self.balls: list[Ball] = []
        self.bricks: list[Brick] = []
        self.powerups: list[PowerUp] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.stars: list[int] = []
        self.overlay_ids: list[int] = []

        self._create_background()
        self._create_hud()
        self.restart_game(show_intro=True)

        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.bind("<KeyRelease>", self.on_key_release)
        self.root.bind("<Motion>", self.on_mouse_move)
        self.root.focus_set()

    def _create_background(self) -> None:
        self.canvas.create_rectangle(
            0,
            0,
            CANVAS_WIDTH,
            CANVAS_HEIGHT,
            fill=BG,
            outline="",
            tags=("background",),
        )
        for x in range(0, CANVAS_WIDTH, 60):
            self.canvas.create_line(
                x,
                48,
                x,
                CANVAS_HEIGHT,
                fill=GRID,
                width=1,
                tags=("background",),
            )
        for y in range(80, CANVAS_HEIGHT, 42):
            self.canvas.create_line(
                0,
                y,
                CANVAS_WIDTH,
                y,
                fill=GRID,
                width=1,
                tags=("background",),
            )
        for _ in range(54):
            x = random.randint(12, CANVAS_WIDTH - 12)
            y = random.randint(52, CANVAS_HEIGHT - 16)
            size = random.choice((1, 1, 2))
            star_id = self.canvas.create_oval(
                x,
                y,
                x + size,
                y + size,
                fill=random.choice(("#275a66", "#3a7d88", "#1e4556")),
                outline="",
                tags=("background", "star"),
            )
            self.stars.append(star_id)
        self.canvas.tag_lower("background")

    def _create_hud(self) -> None:
        self.score_text = self.canvas.create_text(
            18,
            20,
            anchor="w",
            text="Score 0",
            fill=NEON_TEXT,
            font=("Arial", 14, "bold"),
        )
        self.high_score_text = self.canvas.create_text(
            160,
            20,
            anchor="w",
            text="High 0",
            fill=DIM_TEXT,
            font=("Arial", 12, "bold"),
        )
        self.level_text = self.canvas.create_text(
            CANVAS_WIDTH // 2,
            20,
            text="Wave 1",
            fill=NEON_TEXT,
            font=("Arial", 14, "bold"),
        )
        self.combo_text = self.canvas.create_text(
            CANVAS_WIDTH // 2,
            42,
            text="",
            fill="#ffd166",
            font=("Arial", 11, "bold"),
        )
        self.balls_text = self.canvas.create_text(
            CANVAS_WIDTH - 150,
            20,
            anchor="e",
            text="Balls 1",
            fill=DIM_TEXT,
            font=("Arial", 12, "bold"),
        )
        self.lives_text = self.canvas.create_text(
            CANVAS_WIDTH - 18,
            20,
            anchor="e",
            text="Lives 3",
            fill=NEON_TEXT,
            font=("Arial", 14, "bold"),
        )

    def restart_game(self, show_intro: bool = False) -> None:
        """Start a fresh run while keeping the current high score."""

        self.clear_screen_shake()
        self.canvas.delete("world")
        self._clear_overlay()
        self.score = 0
        self.lives = self.settings.lives
        self.level = 1
        self.combo = 0
        self.combo_timer = 0
        self.paddle_boost_timer = 0
        self.balls = []
        self.bricks = []
        self.powerups = []
        self.particles = []
        self.floating_texts = []
        self._build_wave()
        title = "uvpy.run BREAKOUT" if show_intro else "New run ready"
        self._show_overlay(
            title,
            "SPACE launch | arrows/A-D or mouse move | P pause | R restart",
        )
        self._set_mode(MODE_READY)
        self.update_ui()

    def _build_wave(self) -> None:
        """Create paddle, bricks, and a stuck launch ball for this wave."""

        self.canvas.delete("world")
        self.balls = []
        self.bricks = []
        self.powerups = []
        self.particles = []
        self.floating_texts = []

        self.paddle = Paddle(
            self.canvas,
            CANVAS_WIDTH / 2,
            PADDLE_Y,
            width=self.settings.paddle_width,
            speed_multiplier=self.settings.speed_multiplier,
        )
        self.create_bricks()
        self.prepare_launch_ball()

    def prepare_launch_ball(self) -> None:
        for ball in self.balls:
            ball.destroy()
        self.balls = [
            Ball(
                self.canvas,
                self.paddle.x,
                self.paddle.y - START_BALL_Y_OFFSET,
                speed_multiplier=self.settings.speed_multiplier * self.wave_speed(),
                stuck_to_paddle=True,
            )
        ]

    def create_bricks(self) -> None:
        """Create a centered matrix with specials and light wave variation."""

        rows = min(10, self.settings.rows + (self.level - 1) // 2)
        cols = self.settings.cols
        gap = 5
        brick_width = int((CANVAS_WIDTH - 120 - gap * (cols - 1)) / cols)
        brick_height = 23
        start_x = (CANVAS_WIDTH - (cols * brick_width + (cols - 1) * gap)) / 2
        start_y = 78

        for row in range(rows):
            for col in range(cols):
                if self._is_gap_in_wave_pattern(row, col):
                    continue

                x = start_x + col * (brick_width + gap)
                y = start_y + row * (brick_height + gap)
                brick_type = self._get_random_brick_type(row)
                color = ROW_COLORS[(row + self.level - 1) % len(ROW_COLORS)]
                hit_points = 2 if self.level >= 2 and row == 0 and col % 2 == 0 else 1
                self.bricks.append(
                    Brick(
                        self.canvas,
                        x,
                        y,
                        brick_width,
                        brick_height,
                        brick_type,
                        color,
                        hit_points=hit_points,
                    )
                )

    def _is_gap_in_wave_pattern(self, row: int, col: int) -> bool:
        if self.level == 1:
            return False
        if self.level % 3 == 0:
            return row % 2 == 1 and col in {0, self.settings.cols - 1}
        if self.level % 2 == 0:
            return (row + col) % 11 == 0
        return False

    def _get_random_brick_type(self, row: int) -> BrickType:
        chance = self.settings.special_chance
        if row <= 1:
            chance *= 0.75
        if random.random() >= chance:
            return BrickType.NORMAL
        return BrickType(random.choice(SPECIAL_TYPES))

    def wave_speed(self) -> float:
        return WAVE_SPEED_BONUS ** (self.level - 1)

    def _set_mode(self, mode: str) -> None:
        self.mode = mode
        self.game_running = mode == MODE_PLAYING

    def start_game(self) -> None:
        """Launch or resume based on the current mode."""

        if self.mode == MODE_GAME_OVER:
            self.restart_game(show_intro=False)
            return
        if self.mode == MODE_LEVEL_CLEAR:
            self.level += 1
            self._build_wave()
            self._clear_overlay()
            self._set_mode(MODE_READY)
            self.update_ui()

        if self.mode == MODE_READY:
            self._clear_overlay()
            self._launch_stuck_balls()
            self._set_mode(MODE_PLAYING)
            self.game_loop()
            return

        if self.mode == MODE_PAUSED:
            self._clear_overlay()
            self._set_mode(MODE_PLAYING)
            self.game_loop()

    def _launch_stuck_balls(self) -> None:
        for ball in self.balls:
            if ball.stuck_to_paddle:
                hit_offset = (ball.x - CANVAS_WIDTH / 2) / (CANVAS_WIDTH / 2)
                ball.launch(hit_offset * 0.45)
        self.sound.play("paddle")

    def toggle_pause(self) -> None:
        if self.mode == MODE_PLAYING:
            self._set_mode(MODE_PAUSED)
            self._show_overlay("Paused", "SPACE or P resume | R restart")
        elif self.mode == MODE_PAUSED:
            self.start_game()

    def on_key_press(self, event) -> None:
        self.pressed_keys.add(event.keysym)

        if event.keysym == "space":
            self.start_game()
        elif event.keysym in {"p", "P"}:
            self.toggle_pause()
        elif event.keysym in {"r", "R"}:
            self.restart_game(show_intro=False)
        elif event.keysym in {"q", "Q", "Escape"}:
            self.root.destroy()

    def on_key_release(self, event) -> None:
        self.pressed_keys.discard(event.keysym)

    def on_mouse_move(self, event) -> None:
        if self.mode not in {MODE_PLAYING, MODE_READY}:
            return
        self.paddle.move_to(event.x, CANVAS_WIDTH)
        self._update_stuck_balls()

    def handle_input(self) -> None:
        if self.mode not in {MODE_PLAYING, MODE_READY}:
            return

        if "Left" in self.pressed_keys or "a" in self.pressed_keys or "A" in self.pressed_keys:
            self.paddle.move_left()
        if "Right" in self.pressed_keys or "d" in self.pressed_keys or "D" in self.pressed_keys:
            self.paddle.move_right(CANVAS_WIDTH)

        self._update_stuck_balls()

    def _update_stuck_balls(self) -> None:
        for ball in self.balls:
            if ball.stuck_to_paddle:
                ball.set_position(self.paddle.x, self.paddle.y - START_BALL_Y_OFFSET)

    def game_loop(self) -> None:
        if self.mode != MODE_PLAYING:
            return

        self.clear_screen_shake()
        self.handle_input()
        self._update_timers()
        self._twinkle_stars()

        for ball in self.balls[:]:
            ball.move()
            self.check_ball_collisions(ball)

        self.update_powerups()
        self.update_effects()
        self.remove_out_of_bounds_balls()
        self.update_ui()

        if self.check_game_over():
            return

        self.apply_screen_shake()
        self.root.after(FRAME_MS, self.game_loop)

    def _update_timers(self) -> None:
        if self.combo_timer > 0:
            self.combo_timer -= 1
            if self.combo_timer == 0:
                self.combo = 0

        if self.paddle_boost_timer > 0:
            self.paddle_boost_timer -= 1
            if self.paddle_boost_timer == 0:
                self.paddle.reset_size()
                self._update_stuck_balls()

    def _twinkle_stars(self) -> None:
        if random.random() > 0.22 or not self.stars:
            return
        star_id = random.choice(self.stars)
        self.canvas.itemconfig(
            star_id,
            fill=random.choice(("#275a66", "#3a7d88", "#6bdff0", "#1e4556")),
        )

    def check_ball_collisions(self, ball: Ball) -> None:
        bounds = ball.get_bounds()

        if bounds[0] <= 0:
            ball.x = ball.radius
            ball.bounce_x()
            self.sound.play("wall")
        elif bounds[2] >= CANVAS_WIDTH:
            ball.x = CANVAS_WIDTH - ball.radius
            ball.bounce_x()
            self.sound.play("wall")

        if bounds[1] <= 48:
            ball.y = 48 + ball.radius
            ball.bounce_y()
            self.sound.play("wall")

        paddle_bounds = self.paddle.get_bounds()
        if ball.dy > 0 and self.check_collision(ball.get_bounds(), paddle_bounds):
            ball.y = paddle_bounds[1] - ball.radius - 1
            ball.dy = -abs(ball.dy)
            hit_pos = (ball.x - self.paddle.x) / (self.paddle.width / 2)
            speed = clamp(math.hypot(ball.dx, ball.dy) * 1.012, MIN_BALL_SPEED, MAX_BALL_SPEED)
            ball.dx = clamp(hit_pos, -1.0, 1.0) * speed * 0.82
            ball.dy = -math.sqrt(max(MIN_BALL_SPEED, speed * speed - ball.dx * ball.dx))
            ball.update_position()
            self.spawn_particles(ball.x, self.paddle.y - 8, PADDLE_FILL, 8)
            self.sound.play("paddle")

        for brick in self.bricks[:]:
            if brick.destroyed:
                continue
            if self.check_collision(ball.get_bounds(), brick.get_bounds()):
                self.resolve_brick_bounce(ball, brick)
                self.handle_brick_collision(brick)
                break

    def resolve_brick_bounce(self, ball: Ball, brick: Brick) -> None:
        previous = ball.get_previous_bounds()
        left, top, right, bottom = brick.get_bounds()

        if previous[3] <= top or previous[1] >= bottom:
            ball.bounce_y()
        elif previous[2] <= left or previous[0] >= right:
            ball.bounce_x()
        else:
            ball.bounce_y()
        ball.normalize_speed()

    def handle_brick_collision(self, brick: Brick) -> None:
        center_x, center_y = brick.center()
        destroyed = brick.hit()

        if not destroyed:
            self.score += 2
            self.spawn_particles(center_x, center_y, "#ffdd66", 6)
            self.add_floating_text(center_x, center_y, "Armor", "#ffdd66")
            self.sound.play("wall")
            return

        self.bricks.remove(brick)
        self.combo += 1
        self.combo_timer = COMBO_TIMEOUT_FRAMES
        base_points = SCORE_BY_BRICK_TYPE[brick.brick_type]
        combo_bonus = min(125, max(0, self.combo - 1) * 5)
        gained = base_points + combo_bonus
        self.score += gained
        self.high_score = max(self.high_score, self.score)

        self.spawn_particles(center_x, center_y, brick.color, 14)
        self.add_floating_text(center_x, center_y, f"+{gained}", brick.color)
        self.start_screen_shake(4, 2.0)
        self.sound.play("brick")

        if brick.brick_type != BrickType.NORMAL:
            self.spawn_powerup(center_x, center_y, brick.brick_type)

    def spawn_powerup(self, x: float, y: float, kind: BrickType) -> None:
        self.powerups.append(PowerUp(self.canvas, x, y, kind))

    def apply_powerup(self, powerup: PowerUp) -> None:
        name = POWERUP_NAMES[powerup.kind]
        self.sound.play("powerup")
        self.start_screen_shake(6, 2.7)

        if powerup.kind == BrickType.MULTI_BALL:
            self.add_extra_ball()
            self.add_extra_ball()
        elif powerup.kind == BrickType.SPEED_UP:
            for ball in self.balls:
                ball.speed_up(1.14)
        elif powerup.kind == BrickType.EXPAND_PADDLE:
            self.paddle.expand()
            self.paddle_boost_timer = PADDLE_BOOST_FRAMES
        elif powerup.kind == BrickType.EXTRA_LIFE:
            self.lives = min(9, self.lives + 1)
        elif powerup.kind == BrickType.BONUS_SCORE:
            bonus = 120 + self.combo * 10
            self.score += bonus
            self.high_score = max(self.high_score, self.score)
            name = f"Bonus +{bonus}"

        self.add_floating_text(powerup.x, self.paddle.y - 28, name, powerup.color)

    def add_extra_ball(self) -> None:
        if not self.balls or len(self.balls) >= MAX_BALLS:
            return
        base_ball = random.choice(self.balls)
        angle = random.uniform(-0.95, 0.95)
        new_ball = Ball(
            self.canvas,
            base_ball.x + random.randint(-10, 10),
            base_ball.y - 8,
            speed_multiplier=self.settings.speed_multiplier * self.wave_speed(),
        )
        new_ball.launch(angle)
        self.balls.append(new_ball)

    def update_powerups(self) -> None:
        speed_bonus = clamp(self.wave_speed(), 1.0, 1.35)
        for powerup in self.powerups[:]:
            powerup.move(speed_bonus)

            if self.check_collision(powerup.get_bounds(), self.paddle.get_bounds()):
                self.apply_powerup(powerup)
                powerup.destroy()
                self.powerups.remove(powerup)
                continue

            if powerup.y - powerup.radius > CANVAS_HEIGHT:
                powerup.destroy()
                self.powerups.remove(powerup)

    def remove_out_of_bounds_balls(self) -> None:
        for ball in self.balls[:]:
            if ball.get_bounds()[1] > CANVAS_HEIGHT + 10:
                ball.destroy()
                self.balls.remove(ball)
                self.sound.play("miss")

        if not self.balls:
            self.lose_life()

    def lose_life(self) -> None:
        self.lives -= 1
        self.combo = 0
        self.combo_timer = 0

        for powerup in self.powerups:
            powerup.destroy()
        self.powerups = []

        if self.lives > 0:
            self.paddle.reset_size()
            self.paddle_boost_timer = 0
            self.prepare_launch_ball()
            self.pressed_keys.clear()
            self._show_overlay("Ball lost", "SPACE launch when ready")
            self._set_mode(MODE_READY)
            self.update_ui()
        else:
            self.game_over()

    def check_game_over(self) -> bool:
        if not self.bricks:
            self.win_game()
            return True
        if self.lives <= 0:
            self.game_over()
            return True
        return False

    def win_game(self) -> None:
        self._set_mode(MODE_LEVEL_CLEAR)
        self.pressed_keys.clear()
        self.high_score = max(self.high_score, self.score)
        self.sound.play("level")
        self._show_overlay(
            f"Wave {self.level} clear",
            "SPACE starts the next wave with faster bricks and ball speed",
        )

    def game_over(self) -> None:
        self._set_mode(MODE_GAME_OVER)
        self.pressed_keys.clear()
        self.high_score = max(self.high_score, self.score)
        self.sound.play("game_over")
        self._show_overlay(
            "Game over",
            f"Final score {self.score} | High score {self.high_score} | SPACE or R restart",
        )

    def update_effects(self) -> None:
        for particle in self.particles[:]:
            particle.life -= 1
            particle.dy += 0.08
            self.canvas.move(particle.item_id, particle.dx, particle.dy)
            if particle.life <= 0:
                self.canvas.delete(particle.item_id)
                self.particles.remove(particle)

        for floating_text in self.floating_texts[:]:
            floating_text.life -= 1
            self.canvas.move(floating_text.item_id, 0, floating_text.dy)
            if floating_text.life <= 0:
                self.canvas.delete(floating_text.item_id)
                self.floating_texts.remove(floating_text)

    def spawn_particles(self, x: float, y: float, color: str, count: int) -> None:
        for _ in range(count):
            radius = random.uniform(1.5, 3.5)
            item_id = self.canvas.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill=color,
                outline="",
                tags=("world", "particle"),
            )
            self.particles.append(
                Particle(
                    item_id=item_id,
                    dx=random.uniform(-2.8, 2.8),
                    dy=random.uniform(-3.2, 1.1),
                    life=random.randint(18, 34),
                    radius=radius,
                )
            )

    def add_floating_text(self, x: float, y: float, text: str, color: str) -> None:
        item_id = self.canvas.create_text(
            x,
            y,
            text=text,
            fill=color,
            font=("Arial", 12, "bold"),
            tags=("world", "float"),
        )
        self.floating_texts.append(FloatingText(item_id=item_id, dy=-0.75, life=48))

    def start_screen_shake(self, frames: int, magnitude: float) -> None:
        self.shake_frames = max(self.shake_frames, frames)
        self.shake_magnitude = max(self.shake_magnitude, magnitude)

    def clear_screen_shake(self) -> None:
        ox, oy = self.shake_offset
        if ox or oy:
            self.canvas.move("world", -ox, -oy)
            self.shake_offset = (0.0, 0.0)

    def apply_screen_shake(self) -> None:
        if self.shake_frames <= 0:
            self.shake_magnitude = 0.0
            return

        self.shake_frames -= 1
        dx = random.uniform(-self.shake_magnitude, self.shake_magnitude)
        dy = random.uniform(-self.shake_magnitude, self.shake_magnitude)
        self.canvas.move("world", dx, dy)
        self.shake_offset = (dx, dy)
        self.shake_magnitude *= 0.82

    def check_collision(
        self,
        rect1: tuple[float, float, float, float],
        rect2: tuple[float, float, float, float],
    ) -> bool:
        return not (
            rect1[2] < rect2[0]
            or rect1[0] > rect2[2]
            or rect1[3] < rect2[1]
            or rect1[1] > rect2[3]
        )

    def update_ui(self) -> None:
        self.canvas.itemconfig(self.score_text, text=f"Score {self.score}")
        self.canvas.itemconfig(self.high_score_text, text=f"High {self.high_score}")
        self.canvas.itemconfig(self.level_text, text=f"Wave {self.level}")
        self.canvas.itemconfig(self.lives_text, text=f"Lives {self.lives}")
        self.canvas.itemconfig(self.balls_text, text=f"Balls {len(self.balls)}")
        combo = f"Combo x{self.combo}" if self.combo >= 2 else ""
        self.canvas.itemconfig(self.combo_text, text=combo)

    def _show_overlay(self, title: str, subtitle: str) -> None:
        self._clear_overlay()
        panel = self.canvas.create_rectangle(
            185,
            242,
            CANVAS_WIDTH - 185,
            396,
            fill="#08141d",
            outline="#43ffd0",
            width=2,
            tags=("overlay",),
        )
        headline = self.canvas.create_text(
            CANVAS_WIDTH / 2,
            292,
            text=title,
            fill=NEON_TEXT,
            font=("Arial", 24, "bold"),
            tags=("overlay",),
        )
        details = self.canvas.create_text(
            CANVAS_WIDTH / 2,
            340,
            text=subtitle,
            fill="#bdeee3",
            font=("Arial", 12, "bold"),
            width=460,
            justify=tk.CENTER,
            tags=("overlay",),
        )
        self.overlay_ids = [panel, headline, details]

    def _clear_overlay(self) -> None:
        self.canvas.delete("overlay")
        self.overlay_ids = []

    def run(self) -> None:
        self.root.mainloop()


@click.command()
@click.option(
    "--difficulty",
    "-d",
    type=click.Choice(["easy", "normal", "hard"], case_sensitive=False),
    default="normal",
    help="Game difficulty level.",
)
@click.option(
    "--speed",
    "-s",
    type=click.FloatRange(0.5, 3.0),
    default=1.0,
    help="Game speed multiplier (0.5-3.0).",
)
@click.option(
    "--special-chance",
    "-c",
    type=click.FloatRange(0.0, 1.0),
    default=0.18,
    help="Chance of special bricks appearing before difficulty tuning.",
)
@click.option(
    "--sound/--muted",
    default=True,
    help="Enable or disable generated sound effects.",
)
def main(difficulty: str, speed: float, special_chance: float, sound: bool) -> None:
    """
    Play a standalone Tkinter Breakout arcade game.

    The script intentionally stays on Tkinter to keep one-command uv execution
    lightweight. Sound effects are generated or delegated to platform beeps,
    so no bundled audio assets are needed.
    """

    settings = resolve_difficulty(difficulty, speed, special_chance)
    click.echo("Starting uvpy.run Breakout...")
    click.echo(f"Difficulty: {difficulty.title()}")
    click.echo(f"Speed: {settings.speed_multiplier:.2f}x")
    click.echo(f"Special Brick Chance: {settings.special_chance:.1%}")
    click.echo(f"Sound: {'on' if sound else 'muted'}")

    game = BreakoutGame(
        difficulty=difficulty,
        speed_multiplier=speed,
        special_brick_chance=special_chance,
        sound_enabled=sound,
    )
    game.run()


if __name__ == "__main__":
    main()
