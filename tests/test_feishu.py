import unittest
from pathlib import Path

from yt2feishu.feishu import build_import_command


class FeishuCommandTests(unittest.TestCase):
    def test_build_import_command_with_optional_flags(self):
        command = build_import_command(
            Path("note.md"),
            "Video Note",
            cli_path="feishu-cli",
            upload_images=True,
            verbose=True,
            dry_run=True,
        )

        self.assertEqual(
            command,
            [
                "feishu-cli",
                "doc",
                "import",
                "note.md",
                "--title",
                "Video Note",
                "--upload-images",
                "--verbose",
                "--dry-run",
            ],
        )


if __name__ == "__main__":
    unittest.main()
