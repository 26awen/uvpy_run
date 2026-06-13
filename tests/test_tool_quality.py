import ast
import importlib.util
import json
import os
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

    def test_calendar_can_start_weeks_on_sunday(self):
        result = subprocess.run(
            [
                sys.executable,
                str(STATIC_PYFILES_ROOT / "cld.py"),
                "-y",
                "2025",
                "-m",
                "1",
                "-s",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Su Mo Tu We Th Fr Sa", result.stdout)

    def test_invalid_cli_arguments_fail_before_running_tools(self):
        cases = [
            ["aria2rpc_watch.py", "127.0.0.1", "--interval", "-1"],
            ["aria2rpc_watch.py", "127.0.0.1", "--port", "70000"],
            ["brick.py", "--speed", "0.1"],
            ["brick.py", "--special-chance", "1.5"],
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

    def test_image_tools_return_nonzero_when_processing_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            text_file = Path(tmp) / "not-an-image.txt"
            text_file.write_text("not an image", encoding="utf-8")

            cases = [
                ["imgtr.py", str(text_file)],
                ["imgtrans.py", "--input", str(text_file)],
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

    def test_image_tool_metadata_distinguishes_single_and_batch_workflows(self):
        imgtr = parse_tool_metadata(STATIC_PYFILES_ROOT / "imgtr.py").to_dict()
        imgtrans = parse_tool_metadata(STATIC_PYFILES_ROOT / "imgtrans.py").to_dict()

        self.assertIn("single", imgtr["overview"].lower())
        self.assertIn("batch", imgtrans["title"].lower())
        self.assertIn("imgtrans.py", imgtr["overview"])
        self.assertIn("imgtr.py", imgtrans["overview"])


if __name__ == "__main__":
    unittest.main()
