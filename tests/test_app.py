import os
import unittest

import main
from tool_metadata import build_remote_usage_examples, parse_tool_metadata


class RouteSmokeTests(unittest.TestCase):
    def setUp(self):
        self.client = main.app.test_client()

    def test_homepage_renders_tool_directory(self):
        response = self.client.get("/", headers={"Host": "localhost:9999"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"passwordgen.py", response.data)
        self.assertIn(b"How uvpy.run works", response.data)
        self.assertIn(b"PEP 723 inline script metadata", response.data)
        self.assertIn(b"Tool directory", response.data)
        self.assertIn(b"Search by name, category, or description", response.data)
        self.assertIn(b"data-category=\"Security\"", response.data)
        self.assertIn(b"Details", response.data)
        self.assertIn(b"Source", response.data)
        self.assertIn(b"https://github.com/26awen/uvpy_run", response.data)
        self.assertIn(
            b'document.querySelectorAll(".filter-button[data-category]")',
            response.data,
        )
        self.assertNotIn(
            b'document.querySelectorAll("[data-category]")',
            response.data,
        )

    def test_all_detail_pages_render(self):
        script_names = sorted(
            filename[:-3]
            for filename in os.listdir(main.STATIC_PYFILES_ROOT)
            if filename.endswith(".py")
        )

        self.assertTrue(script_names)

        for script_name in script_names:
            with self.subTest(script_name=script_name):
                response = self.client.get(
                    f"/detail/{script_name}",
                    headers={"Host": "localhost:9999"},
                )

                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Run this script", response.data)
                self.assertIn(b"Source preview", response.data)
                self.assertIn(b"https://github.com/26awen/uvpy_run", response.data)

    def test_raw_python_script_is_served(self):
        response = self.client.get(
            "/passwordgen.py",
            headers={"Host": "localhost:9999"},
        )

        try:
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Generate secure passwords", response.data)
        finally:
            response.close()

    def test_missing_python_script_returns_404(self):
        response = self.client.get(
            "/does_not_exist.py",
            headers={"Host": "localhost:9999"},
        )

        self.assertEqual(response.status_code, 404)

    def test_non_python_catch_all_returns_404(self):
        response = self.client.get(
            "/does-not-exist",
            headers={"Host": "localhost:9999"},
        )

        self.assertEqual(response.status_code, 404)

    def test_static_files_use_single_flask_static_route(self):
        static_rules = [rule for rule in main.app.url_map.iter_rules() if rule.rule.startswith("/static/")]
        response = self.client.get(
            "/static/favicon.svg",
            headers={"Host": "localhost:9999"},
        )

        try:
            self.assertEqual(len(static_rules), 1)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"<svg", response.data)
        finally:
            response.close()


class MetadataParsingTests(unittest.TestCase):
    def test_password_tool_metadata(self):
        info = parse_tool_metadata(
            os.path.join(main.STATIC_PYFILES_ROOT, "passwordgen.py")
        ).to_dict()

        self.assertEqual(
            info["title"],
            "Generate secure passwords with customizable options",
        )
        self.assertEqual(info["category"], "Security")
        self.assertEqual(info["requires_python"], ">=3.12")
        self.assertEqual(info["dependencies"], [])
        self.assertIn("uv run passwordgen.py -l 16 -c 3", info["usage_examples"])

    def test_docstring_sections_drop_source_list_markers(self):
        info = parse_tool_metadata(
            os.path.join(main.STATIC_PYFILES_ROOT, "brick.py")
        ).to_dict()

        game_controls = next(
            section for section in info["doc_sections"] if section["title"] == "Game Controls"
        )

        self.assertIn("LEFT/RIGHT Arrow Keys: Move paddle", game_controls["lines"])
        self.assertNotIn("- LEFT/RIGHT Arrow Keys: Move paddle", game_controls["lines"])

    def test_multiline_pep723_dependencies_are_parsed(self):
        info = parse_tool_metadata(
            os.path.join(main.STATIC_PYFILES_ROOT, "qr.py")
        ).to_dict()

        self.assertEqual(info["requires_python"], ">=3.12")
        self.assertEqual(info["dependencies"], ["click>=8.0.0", "qrcode[pil]>=7.0.0"])

    def test_remote_usage_examples_are_copy_ready(self):
        examples = build_remote_usage_examples(
            [
                "uv run passwordgen.py",
                "uv run passwordgen.py -l 16 -c 3",
                "python passwordgen.py --no-symbols",
            ],
            "https://uvpy.run",
            "passwordgen.py",
        )

        self.assertEqual(
            examples,
            [
                "uv run https://uvpy.run/passwordgen.py",
                "uv run https://uvpy.run/passwordgen.py -l 16 -c 3",
                "uv run https://uvpy.run/passwordgen.py --no-symbols",
            ],
        )


if __name__ == "__main__":
    unittest.main()
