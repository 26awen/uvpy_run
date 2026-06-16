import ast
import importlib.util
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from click.testing import CliRunner

from tool_metadata import build_remote_usage_examples, parse_tool_metadata


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_PYFILES_ROOT = PROJECT_ROOT / "static_pyfiles"
ALLOWED_CATEGORIES = {
    "Developer",
    "File",
    "Game",
    "Image",
    "Network",
    "Security",
    "System",
    "Text",
    "Time",
}


def tool_files():
    return sorted(STATIC_PYFILES_ROOT.glob("*.py"))


def load_tool_module(filename):
    path = STATIC_PYFILES_ROOT / filename
    module_name = f"uvpy_tool_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class ToolCatalogQualityTests(unittest.TestCase):
    def test_every_script_has_standard_metadata(self):
        for path in tool_files():
            with self.subTest(script=path.name):
                content = path.read_text(encoding="utf-8")
                info = parse_tool_metadata(path).to_dict()
                module_docstring = ast.get_docstring(ast.parse(content))

                self.assertIn("# /// script", content)
                self.assertIn("# ///", content)
                self.assertIsNotNone(module_docstring)
                self.assertNotEqual(info["requires_python"], "N/A")
                self.assertIsInstance(info["dependencies"], list)
                self.assertTrue(info["title"])
                self.assertFalse(info["title"].startswith("Python Script:"))
                self.assertTrue(info["overview"])
                self.assertGreaterEqual(len(info["doc_sections"]), 1)
                self.assertNotEqual(info["version"], "N/A")
                self.assertNotEqual(info["category"], "N/A")
                self.assertIn(info["category"], ALLOWED_CATEGORIES)
                self.assertNotEqual(info["author"], "N/A")
                self.assertGreaterEqual(len(info["usage_examples"]), 1)

                for field_name in ("Version:", "Category:", "Author:", "Usage Examples:"):
                    self.assertIn(field_name, module_docstring)
                for dependency in info["dependencies"]:
                    self.assertIsInstance(dependency, str)
                    self.assertTrue(dependency.strip())

    def test_usage_examples_are_copy_ready_for_the_current_script(self):
        for path in tool_files():
            with self.subTest(script=path.name):
                info = parse_tool_metadata(path).to_dict()
                local_prefix = f"uv run {path.name}"
                remote_prefix = f"uv run https://uvpy.run/{path.name}"

                for example in info["usage_examples"]:
                    self.assertTrue(example.startswith(local_prefix), example)
                    self.assertNotIn(f"python {path.name}", example)
                    mentioned_scripts = re.findall(
                        r"(?:uv run|python)\s+([a-zA-Z_][a-zA-Z0-9_]*\.py)",
                        example,
                    )
                    self.assertEqual(mentioned_scripts, [path.name])

                remote_examples = build_remote_usage_examples(
                    info["usage_examples"],
                    "https://uvpy.run",
                    path.name,
                )
                for remote_example in remote_examples:
                    self.assertTrue(remote_example.startswith(remote_prefix), remote_example)

    def test_every_script_exposes_help(self):
        for path in tool_files():
            with self.subTest(script=path.name):
                result = subprocess.run(
                    [sys.executable, str(path), "--help"],
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=20,
                )

                output = result.stdout + result.stderr
                self.assertEqual(result.returncode, 0, output)
                self.assertIn("usage:", output.lower())


class ToolRiskCoherenceTests(unittest.TestCase):
    def test_password_generator_uses_cryptographic_randomness(self):
        source = (STATIC_PYFILES_ROOT / "passwordgen.py").read_text(encoding="utf-8")

        self.assertIn("secrets.SystemRandom", source)
        self.assertNotIn("import random", source)

    def test_secret_generator_returns_expected_encodings(self):
        tool = load_tool_module("flask_secret.py")

        hex_secret = tool.generate_secret(32, "hex")
        urlsafe_secret = tool.generate_secret(32, "urlsafe")
        base64_secret = tool.generate_secret(32, "base64")

        self.assertRegex(hex_secret, r"^[0-9a-f]{64}$")
        self.assertGreaterEqual(len(urlsafe_secret), 32)
        self.assertNotIn("=", base64_secret)

    def test_mkdir_batch_supports_dry_run_and_conflict_reporting(self):
        tool = load_tool_module("mkdir_batch.py")

        with tempfile.TemporaryDirectory() as tmp:
            preview = tool.create_folders_batch(
                tmp,
                "project",
                count=2,
                start_index=1,
                dry_run=True,
            )
            self.assertTrue(preview.dry_run)
            self.assertFalse((Path(tmp) / "project_1").exists())

            created = tool.create_folders_batch(tmp, "project", count=2, start_index=1)
            self.assertEqual(len(created.created), 2)
            self.assertTrue((Path(tmp) / "project_1").is_dir())
            self.assertTrue((Path(tmp) / "project_2").is_dir())

            rerun = tool.create_folders_batch(tmp, "project", count=2, start_index=1)
            self.assertEqual(rerun.created, [])
            self.assertEqual(len(rerun.existing), 2)

            with self.assertRaises(FileExistsError):
                tool.create_folders_batch(
                    tmp,
                    "project",
                    count=2,
                    start_index=1,
                    fail_existing=True,
                )

    def test_today_calendar_can_start_weeks_on_sunday(self):
        result = subprocess.run(
            [
                sys.executable,
                str(STATIC_PYFILES_ROOT / "today.py"),
                "-y",
                "2025",
                "-m",
                "1",
                "-s",
                "--no-highlight",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r"Su\s+Mo\s+Tu\s+We\s+Th\s+Fr\s+Sa")

    def test_today_calendar_highlights_today_by_default(self):
        result = subprocess.run(
            [
                sys.executable,
                str(STATIC_PYFILES_ROOT / "today.py"),
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("today", result.stdout)
        self.assertIn("timezone", result.stdout)
        self.assertRegex(result.stdout, r"UTC[+-]\d{2}:\d{2}")
        self.assertIn("highlight on", result.stdout)

    def test_disk_usage_helpers_prioritize_readable_mounts(self):
        tool = load_tool_module("disk_usage.py")
        root = tool.DiskUsage(
            mountpoint="/",
            device="/dev/root",
            fstype="ext4",
            total=1000,
            used=900,
            free=100,
            percent=90.0,
            opts="rw",
        )
        data = tool.DiskUsage(
            mountpoint="/data",
            device="/dev/data",
            fstype="ext4",
            total=1000,
            used=500,
            free=500,
            percent=50.0,
            opts="rw",
        )

        self.assertEqual(tool.format_bytes(1536), "1.5 KB")
        self.assertEqual(tool.usage_status(90).label, "critical")
        self.assertEqual(
            [
                usage.mountpoint
                for usage in tool.sort_disk_usages([data, root], "percent")
            ],
            ["/", "/data"],
        )
        self.assertEqual(
            [usage.mountpoint for usage in tool.sort_disk_usages([data, root], "free")],
            ["/", "/data"],
        )
        self.assertEqual(tool.limit_disk_usages([root, data], 1), ([root], 1))
        noisy_mount = type(
            "Partition",
            (),
            {
                "mountpoint": "/System/Volumes/Preboot",
                "device": "/dev/disk1s2",
                "fstype": "apfs",
                "opts": "rw",
            },
        )()
        useful_mount = type(
            "Partition",
            (),
            {
                "mountpoint": "/System/Volumes/Data",
                "device": "/dev/disk3s5",
                "fstype": "apfs",
                "opts": "rw",
            },
        )()
        macos_readonly_root = type(
            "Partition",
            (),
            {
                "mountpoint": "/",
                "device": "/dev/disk3s1s1",
                "fstype": "apfs",
                "opts": "ro,local,rootfs",
            },
        )()
        linux_root = type(
            "Partition",
            (),
            {
                "mountpoint": "/",
                "device": "/dev/root",
                "fstype": "ext4",
                "opts": "rw",
            },
        )()

        self.assertTrue(tool.is_noisy_mount(noisy_mount))
        self.assertFalse(tool.is_noisy_mount(useful_mount))
        self.assertTrue(
            tool.is_noisy_mount(
                macos_readonly_root,
                has_macos_data_volume=True,
            )
        )
        self.assertFalse(
            tool.is_noisy_mount(
                macos_readonly_root,
                has_macos_data_volume=False,
            )
        )
        self.assertFalse(
            tool.is_noisy_mount(
                linux_root,
                has_macos_data_volume=True,
            )
        )

    def test_disk_usage_filters_noisy_mounts_and_emits_json(self):
        tool = load_tool_module("disk_usage.py")
        runner = CliRunner()
        sample = tool.DiskUsage(
            mountpoint="/",
            device="/dev/root",
            fstype="ext4",
            total=1000,
            used=250,
            free=750,
            percent=25.0,
            opts="rw",
        )

        tool.collect_disk_usages = lambda include_all=False: ([sample], 3)

        result = runner.invoke(tool.main, ["--json"])
        payload = json.loads(result.output)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(payload["skipped_count"], 3)
        self.assertEqual(payload["partitions"][0]["mountpoint"], "/")
        self.assertEqual(payload["partitions"][0]["status"], "ok")

    def test_disk_usage_rejects_overlapping_thresholds(self):
        tool = load_tool_module("disk_usage.py")
        runner = CliRunner()

        result = runner.invoke(tool.main, ["--warn", "90", "--critical", "80"])

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("--warn must be below --critical", result.output)

    def test_aria2_watcher_help_and_metadata_are_aria2c_first(self):
        result = subprocess.run(
            [
                sys.executable,
                str(STATIC_PYFILES_ROOT / "aria2rpc_watch.py"),
                "--help",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )

        output = result.stdout + result.stderr
        info = parse_tool_metadata(STATIC_PYFILES_ROOT / "aria2rpc_watch.py").to_dict()

        self.assertEqual(result.returncode, 0, output)
        self.assertIn("aria2c JSON-RPC", output)
        self.assertIn("HOST defaults to 127.0.0.1", output)
        self.assertIn("--once", output)
        self.assertIn("aria2c", info["title"])
        self.assertIn("uv run aria2rpc_watch.py", info["usage_examples"])

    def test_aria2_watcher_transfer_helpers_cover_rpc_rows(self):
        tool = load_tool_module("aria2rpc_watch.py")
        active = {
            "gid": "abc123456789",
            "status": "active",
            "totalLength": "1048576",
            "completedLength": "524288",
            "downloadSpeed": "1024",
            "connections": "3",
            "files": [{"path": "/tmp/ubuntu.iso", "uris": []}],
        }
        stopped = {
            "gid": "deadbeef",
            "status": "complete",
            "totalLength": "10",
            "completedLength": "10",
        }
        snapshot = tool.Aria2Snapshot(
            stats={"downloadSpeed": "2048", "uploadSpeed": "0"},
            active=[active],
            waiting=[],
            stopped=[stopped],
        )

        visible, hidden_count = tool.visible_downloads(
            snapshot,
            rows=1,
            include_stopped=True,
        )

        self.assertEqual(tool.download_name(active), "ubuntu.iso")
        self.assertAlmostEqual(tool.progress_percent(active), 50.0)
        self.assertEqual(tool.format_eta(tool.eta_seconds(active)), "8m 32s")
        self.assertEqual(visible, [active])
        self.assertEqual(hidden_count, 1)
        with self.assertRaises(tool.Aria2RpcError):
            tool.extract_rpc_result(
                {"error": {"code": 1, "message": "Unauthorized"}}
            )

    def test_aria2_watcher_once_mode_reports_connection_failure(self):
        result = subprocess.run(
            [
                sys.executable,
                str(STATIC_PYFILES_ROOT / "aria2rpc_watch.py"),
                "--once",
                "--no-screen",
                "--port",
                "1",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )

        output = result.stdout + result.stderr

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Cannot reach aria2c JSON-RPC", output)
        self.assertIn("Start local aria2c RPC", output)

    def test_invalid_cli_arguments_fail_before_running_tools(self):
        cases = [
            ["aria2rpc_watch.py", "127.0.0.1", "--interval", "-1"],
            ["aria2rpc_watch.py", "127.0.0.1", "--port", "70000"],
            ["brick.py", "--speed", "0.1"],
            ["brick.py", "--special-chance", "1.5"],
            ["qr.py", "hello", "--size", "0"],
            ["qr.py", "hello", "--border", "-1"],
        ]

        for command in cases:
            with self.subTest(command=command):
                result = subprocess.run(
                    [sys.executable, str(STATIC_PYFILES_ROOT / command[0]), *command[1:]],
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=20,
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Invalid value", result.stderr)

    def test_nospace_requires_exactly_one_input_source(self):
        result = subprocess.run(
            [
                sys.executable,
                str(STATIC_PYFILES_ROOT / "nospace.py"),
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Provide text", result.stderr)

        conflict = subprocess.run(
            [
                sys.executable,
                str(STATIC_PYFILES_ROOT / "nospace.py"),
                "hello",
                "--text",
                "world",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )

        self.assertNotEqual(conflict.returncode, 0)
        self.assertIn("Choose one input source", conflict.stderr)

    def test_nospace_quiet_mode_outputs_cleaned_text(self):
        result = subprocess.run(
            [
                sys.executable,
                str(STATIC_PYFILES_ROOT / "nospace.py"),
                "--quiet",
                "tabs\tand spaces",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "tabs\tandspaces\n")

        all_whitespace = subprocess.run(
            [
                sys.executable,
                str(STATIC_PYFILES_ROOT / "nospace.py"),
                "--quiet",
                "--all-whitespace",
                "tabs\tand spaces",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )

        self.assertEqual(
            all_whitespace.returncode,
            0,
            all_whitespace.stdout + all_whitespace.stderr,
        )
        self.assertEqual(all_whitespace.stdout, "tabsandspaces\n")

    def test_qr_generates_png_and_creates_output_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "nested" / "hello.png"
            result = subprocess.run(
                [
                    sys.executable,
                    str(STATIC_PYFILES_ROOT / "qr.py"),
                    "https://uvpy.run",
                    "--output",
                    str(output_path),
                    "--size",
                    "4",
                    "--border",
                    "1",
                    "--error-correction",
                    "q",
                    "--style",
                    "rounded",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=20,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(output_path.is_file())
            self.assertTrue(output_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertIn("terminal preview", result.stdout)
            self.assertIn("PNG generated", result.stdout)
            self.assertIn("correction", result.stdout)

    def test_qr_refuses_to_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "qrcode.png"
            output_path.write_text("existing", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(STATIC_PYFILES_ROOT / "qr.py"),
                    "https://uvpy.run",
                    "--output",
                    str(output_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=20,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("already exists", result.stderr)
            self.assertEqual(output_path.read_text(encoding="utf-8"), "existing")

            overwrite = subprocess.run(
                [
                    sys.executable,
                    str(STATIC_PYFILES_ROOT / "qr.py"),
                    "https://uvpy.run",
                    "--output",
                    str(output_path),
                    "--force",
                    "--no-terminal",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=20,
            )

            self.assertEqual(overwrite.returncode, 0, overwrite.stdout + overwrite.stderr)
            self.assertTrue(output_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))

    def test_qr_dry_run_does_not_write_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "nested" / "dry-run.png"
            result = subprocess.run(
                [
                    sys.executable,
                    str(STATIC_PYFILES_ROOT / "qr.py"),
                    "https://uvpy.run",
                    "--output",
                    str(output_path),
                    "--dry-run",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=20,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(output_path.exists())
            self.assertFalse(output_path.parent.exists())
            self.assertIn("dry run", result.stdout)
            self.assertIn("terminal preview", result.stdout)

    def test_breakout_arcade_tuning_stays_lightweight(self):
        tool = load_tool_module("brick.py")

        easy = tool.resolve_difficulty("easy", speed=1.0, special_chance=0.4)
        hard = tool.resolve_difficulty("hard", speed=1.0, special_chance=0.4)
        extreme = tool.resolve_difficulty("normal", speed=3.0, special_chance=1.0)

        self.assertGreater(easy.lives, hard.lives)
        self.assertGreater(easy.paddle_width, hard.paddle_width)
        self.assertGreater(hard.speed_multiplier, easy.speed_multiplier)
        self.assertLessEqual(extreme.special_chance, 0.65)
        self.assertEqual(set(tool.SCORE_BY_BRICK_TYPE), set(tool.BrickType))

        special_types = set(tool.BrickType) - {tool.BrickType.NORMAL}
        self.assertEqual(set(tool.BRICK_MARKERS), special_types)
        self.assertEqual(set(tool.POWERUP_COLORS), special_types)

        sound = tool.SoundEngine(enabled=False)
        sound.play("brick")
        self.assertEqual(sound.generated_files, {})

    def test_snake_starts_with_visible_body_and_allows_tail_following(self):
        tool = load_tool_module("snake.py")
        game = tool.SnakeGame(width=10, height=8, speed=1)

        self.assertEqual(len(game.snake), tool.STARTING_LENGTH)
        self.assertEqual(game.snake[0], tool.Position(4, 5))
        self.assertEqual(game.snake[-1], tool.Position(4, 3))

        game.snake = [
            tool.Position(2, 2),
            tool.Position(2, 1),
            tool.Position(1, 1),
            tool.Position(1, 2),
        ]
        game.direction = tool.Direction.UP
        game.next_direction = tool.Direction.UP
        game.food = tool.Position(7, 7)

        game._update_single_player()

        self.assertFalse(game.game_over)
        self.assertEqual(game.snake[0], tool.Position(1, 2))
        self.assertEqual(len(game.snake), 4)

    def test_snake_queues_only_one_safe_turn_per_tick(self):
        tool = load_tool_module("snake.py")
        game = tool.SnakeGame(width=10, height=8, speed=1)

        self.assertTrue(game._queue_direction(tool.Direction.UP))
        self.assertFalse(game._queue_direction(tool.Direction.LEFT))

        self.assertEqual(game.direction, tool.Direction.RIGHT)
        self.assertEqual(game.next_direction, tool.Direction.UP)

        game.food = tool.Position(7, 7)
        game._update_single_player()

        self.assertEqual(game.direction, tool.Direction.UP)
        self.assertEqual(game.snake[0], tool.Position(3, 5))

    def test_snake_updates_score_high_score_and_food_count(self):
        tool = load_tool_module("snake.py")
        game = tool.SnakeGame(width=10, height=8, speed=1)
        game.snake = [
            tool.Position(2, 2),
            tool.Position(2, 1),
            tool.Position(2, 0),
        ]
        game.direction = tool.Direction.RIGHT
        game.next_direction = tool.Direction.RIGHT
        game.food = tool.Position(2, 3)

        game._update_single_player()

        self.assertEqual(game.score, tool.POINTS_PER_FOOD)
        self.assertEqual(game.high_score, tool.POINTS_PER_FOOD)
        self.assertEqual(game.food_eaten, 1)
        self.assertEqual(len(game.snake), tool.STARTING_LENGTH + 1)
        self.assertIn("Snack collected", game.last_message)

    def test_snake_smooth_renderer_uses_braille_subcells(self):
        tool = load_tool_module("snake.py")
        game = tool.SnakeGame(width=10, height=8, speed=1)

        interpolated = game._interpolated_snake(
            [tool.Position(2, 2)],
            [tool.Position(2, 1)],
            0.5,
        )
        rendered = game._render_smooth_board()

        self.assertEqual(interpolated, [(2.0, 1.5)])
        self.assertTrue(
            any(0x2800 <= ord(character) <= 0x28FF for character in rendered.plain)
        )

    def test_snake_classic_mode_preserves_original_glyph_renderer(self):
        tool = load_tool_module("snake.py")
        game = tool.SnakeGame(
            width=10,
            height=8,
            speed=1,
            render_mode=tool.RENDER_MODE_CLASSIC,
        )

        rendered = game._render_board().plain

        self.assertIn("@", rendered)
        self.assertIn("#", rendered)
        self.assertNotIn("⣿", rendered)

    def test_snake_kitty_renderer_builds_rgb_frame_and_escape_chunks(self):
        tool = load_tool_module("snake.py")
        game = tool.SnakeGame(
            width=10,
            height=8,
            speed=1,
            render_mode=tool.RENDER_MODE_CLASSIC,
        )
        renderer = tool.KittySnakeRenderer(width=10, height=8, cell_pixels=4)

        frame = renderer.render(game, progress=1.0)
        chunks = tool.kitty_graphics_chunks(
            frame,
            renderer.pixel_width,
            renderer.pixel_height,
            columns=20,
            rows=8,
        )

        self.assertEqual(len(frame), 10 * 4 * 8 * 4 * 3)
        self.assertGreater(len(set(frame)), 1)
        self.assertTrue(chunks[0].startswith("\x1b_Ga=T,f=24,o=z,s=40,v=32"))
        self.assertIn("c=20,r=8", chunks[0])
        self.assertTrue(chunks[-1].endswith("\x1b\\"))

    def test_snake_kitty_renderer_smooths_corners_and_tapers_tail(self):
        tool = load_tool_module("snake.py")
        renderer = tool.KittySnakeRenderer(width=10, height=8, cell_pixels=10)

        path = renderer._smooth_path([(50.0, 50.0), (50.0, 30.0), (30.0, 30.0)])

        self.assertGreater(len(path), 3)
        self.assertNotIn((50.0, 30.0), path)
        self.assertGreater(renderer._body_radius(0.5), renderer._body_radius(1.0))

    def test_snake_fancy_mode_is_kitty_only_single_player(self):
        fancy_without_kitty = subprocess.run(
            [sys.executable, str(STATIC_PYFILES_ROOT / "snake.py"), "--fancy"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )
        fancy_two_player = subprocess.run(
            [
                sys.executable,
                str(STATIC_PYFILES_ROOT / "snake.py"),
                "--mode-kitty",
                "--fancy",
                "--two-player",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )

        self.assertNotEqual(fancy_without_kitty.returncode, 0)
        self.assertIn("--fancy can only be used with --mode-kitty", fancy_without_kitty.stderr)
        self.assertNotEqual(fancy_two_player.returncode, 0)
        self.assertIn("single-player Kitty mode", fancy_two_player.stderr)

    def test_snake_fancy_powerup_spawns_on_open_cell(self):
        tool = load_tool_module("snake.py")
        game = tool.SnakeGame(width=10, height=8, speed=1)
        game.food = tool.Position(4, 4)
        state = tool.FancyState(width=10, height=8, rng=random.Random(4))

        self.assertTrue(state.spawn_powerup(game))

        self.assertIsNotNone(state.powerup)
        self.assertNotIn(state.powerup.position, game.snake)
        self.assertNotEqual(state.powerup.position, game.food)

    def test_snake_kitty_renderer_draws_fancy_state(self):
        tool = load_tool_module("snake.py")
        game = tool.SnakeGame(width=10, height=8, speed=1)
        renderer = tool.KittySnakeRenderer(width=10, height=8, cell_pixels=4)
        state = tool.FancyState(width=10, height=8, rng=random.Random(5))
        state.powerup = tool.FancyPowerup(
            tool.FANCY_POWERUP_GHOST_BITE,
            tool.Position(3, 3),
        )
        state.moon_gates = (
            tool.Position(1, 1),
            tool.Position(3, 8),
            tool.Position(6, 8),
        )
        state.slow_charm_ticks = 5
        state.ghost_bite_ticks = 5
        state.add_burst(tool.Position(4, 4), tool.KITTY_COLORS["prism_blue"], 4, 2.0)

        frame = renderer.render(game, progress=1.0, fancy_state=state)

        self.assertEqual(len(frame), renderer.pixel_width * renderer.pixel_height * 3)
        self.assertGreater(len(set(frame)), 1)

    def test_snake_fancy_slow_charm_slows_game_temporarily(self):
        tool = load_tool_module("snake.py")
        slow_runner = tool.KittySnakeGame(
            width=10,
            height=8,
            speed=1,
            two_player=False,
            fancy=True,
        )
        fast_runner = tool.KittySnakeGame(
            width=10,
            height=8,
            speed=15,
            two_player=False,
            fancy=True,
        )
        slow_runner.fancy_state.powerup = tool.FancyPowerup(
            tool.FANCY_POWERUP_SLOW_CHARM,
            slow_runner.game.snake[0],
        )
        fast_runner.fancy_state.powerup = tool.FancyPowerup(
            tool.FANCY_POWERUP_SLOW_CHARM,
            fast_runner.game.snake[0],
        )

        self.assertTrue(slow_runner.fancy_state.maybe_activate_powerup(slow_runner.game))
        self.assertTrue(fast_runner.fancy_state.maybe_activate_powerup(fast_runner.game))

        slow_multiplier = slow_runner._logic_interval() / slow_runner.game._logic_interval
        fast_multiplier = fast_runner._logic_interval() / fast_runner.game._logic_interval
        self.assertGreater(fast_multiplier, slow_multiplier)
        self.assertLess(
            fast_runner.fancy_state.slow_charm_ticks,
            slow_runner.fancy_state.slow_charm_ticks,
        )
        self.assertIn("Slow Charm", fast_runner.game.last_message)

    def test_snake_fancy_ghost_bite_activates_body_phase(self):
        tool = load_tool_module("snake.py")
        game = tool.SnakeGame(width=10, height=8, speed=1)
        state = tool.FancyState(width=10, height=8, rng=random.Random(6))
        state.powerup = tool.FancyPowerup(tool.FANCY_POWERUP_GHOST_BITE, game.snake[0])

        self.assertTrue(state.maybe_activate_powerup(game))

        self.assertEqual(state.ghost_bite_ticks, tool.FANCY_GHOST_BITE_TICKS)
        self.assertIn("Ghost Bite", game.last_message)

    def test_snake_fancy_moon_gate_teleports_head(self):
        tool = load_tool_module("snake.py")
        runner = tool.KittySnakeGame(width=10, height=8, speed=1, two_player=False, fancy=True)
        runner.game.snake = [
            tool.Position(2, 2),
            tool.Position(2, 1),
            tool.Position(2, 0),
        ]
        runner.game.direction = tool.Direction.RIGHT
        runner.game.next_direction = tool.Direction.RIGHT
        runner.game.food = tool.Position(7, 7)
        runner.fancy_state.moon_gates = (tool.Position(2, 3), tool.Position(5, 5))
        runner.fancy_state.moon_gate_ticks = 10

        runner._advance_game()

        self.assertFalse(runner.game.game_over)
        self.assertEqual(runner.game.snake[0], tool.Position(5, 5))

        large_game = tool.SnakeGame(width=32, height=18, speed=1)
        large_state = tool.FancyState(width=32, height=18, rng=random.Random(7))
        gate_count = large_state.activate_moon_gate(large_game)

        self.assertEqual(gate_count, 6)
        self.assertEqual(len(set(large_state.moon_gates)), 6)
        self.assertEqual(
            large_state.teleport_target(large_state.moon_gates[0]),
            large_state.moon_gates[1],
        )
        self.assertEqual(
            large_state.teleport_target(large_state.moon_gates[-1]),
            large_state.moon_gates[0],
        )

    def test_snake_fancy_tail_shield_absorbs_one_self_collision(self):
        tool = load_tool_module("snake.py")
        runner = tool.KittySnakeGame(width=10, height=8, speed=1, two_player=False, fancy=True)
        runner.game.snake = [
            tool.Position(2, 2),
            tool.Position(1, 2),
            tool.Position(1, 1),
            tool.Position(2, 1),
        ]
        runner.game.direction = tool.Direction.UP
        runner.game.next_direction = tool.Direction.UP
        runner.game.food = tool.Position(7, 7)
        runner.fancy_state.tail_shield_charges = 1
        runner.fancy_state.tail_shield_ticks = 10

        runner._advance_game()

        self.assertFalse(runner.game.game_over)
        self.assertEqual(runner.game.snake[0], tool.Position(1, 2))
        self.assertEqual(runner.fancy_state.tail_shield_charges, 0)
        self.assertIn("Tail Shield cracked", runner.game.last_message)

    def test_snake_fancy_ghost_bite_allows_self_collision(self):
        tool = load_tool_module("snake.py")
        runner = tool.KittySnakeGame(width=10, height=8, speed=1, two_player=False, fancy=True)
        runner.game.snake = [
            tool.Position(2, 2),
            tool.Position(1, 2),
            tool.Position(1, 1),
            tool.Position(2, 1),
        ]
        runner.game.direction = tool.Direction.UP
        runner.game.next_direction = tool.Direction.UP
        runner.game.food = tool.Position(7, 7)
        runner.fancy_state.ghost_bite_ticks = 10

        runner._advance_game()

        self.assertFalse(runner.game.game_over)
        self.assertEqual(runner.game.snake[0], tool.Position(1, 2))
        self.assertIn("Ghost Bite phased", runner.game.last_message)

    def test_image_tools_return_nonzero_when_processing_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            text_file = Path(tmp) / "not-an-image.txt"
            text_file.write_text("not an image", encoding="utf-8")

            cases = [
                ["image.py", str(text_file)],
                ["image.py", "--input", str(text_file)],
            ]

            for command in cases:
                with self.subTest(command=command):
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(STATIC_PYFILES_ROOT / command[0]),
                            *command[1:],
                        ],
                        cwd=PROJECT_ROOT,
                        capture_output=True,
                        text=True,
                        timeout=20,
                    )

                    self.assertNotEqual(result.returncode, 0)

    def test_terminal_proxy_ip_json_output_is_machine_readable(self):
        tool = load_tool_module("terminal_proxy_ip.py")
        sample_payload = {
            "ip": "203.0.113.10",
            "city": "Example City",
            "region": "Example Region",
            "country": "ZZ",
            "loc": "1.23,4.56",
        }
        runner = CliRunner()

        tool.get_ip_info = lambda: sample_payload
        result = runner.invoke(tool.main, ["--format", "json"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(json.loads(result.output), sample_payload)
        self.assertNotIn("Fetching", result.output)

        tool.fetch_ip_info = lambda url: sample_payload
        result = runner.invoke(tool.lookup, ["8.8.8.8", "--format", "json"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(json.loads(result.output), sample_payload)
        self.assertNotIn("Looking up", result.output)

        missing_argument = runner.invoke(tool.lookup, [])
        self.assertNotEqual(missing_argument.exit_code, 0)
        self.assertIn("Missing argument", missing_argument.output)

    def test_image_tool_metadata_covers_single_and_batch_workflows(self):
        image_tool = parse_tool_metadata(STATIC_PYFILES_ROOT / "image.py").to_dict()

        overview = image_tool["overview"].lower()
        examples = "\n".join(image_tool["usage_examples"])

        self.assertIn("single-file", overview)
        self.assertIn("batch", overview)
        self.assertIn("--input", examples)
        self.assertIn("--dry-run", examples)


if __name__ == "__main__":
    unittest.main()
