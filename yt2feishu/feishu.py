from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def build_import_command(
    markdown_path: Path,
    title: str,
    *,
    cli_path: str | None = None,
    upload_images: bool = False,
    verbose: bool = False,
    dry_run: bool = False,
) -> list[str]:
    feishu_cli = cli_path or shutil.which("feishu-cli")
    if not feishu_cli:
        raise FileNotFoundError("feishu-cli")

    command = [feishu_cli, "doc", "import", str(markdown_path), "--title", title]
    if upload_images:
        command.append("--upload-images")
    if verbose:
        command.append("--verbose")
    if dry_run:
        command.append("--dry-run")
    return command


def upload_markdown(
    markdown_path: Path,
    title: str,
    *,
    cli_path: str | None = None,
    upload_images: bool = False,
    verbose: bool = False,
    dry_run: bool = False,
) -> str:
    command = build_import_command(
        markdown_path,
        title,
        cli_path=cli_path,
        upload_images=upload_images,
        verbose=verbose,
        dry_run=dry_run,
    )

    result = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"feishu-cli failed: {detail}")

    return result.stdout.strip()
