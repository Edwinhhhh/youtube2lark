from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from .feishu import build_import_command
from .feishu import upload_markdown
from .markdown import build_markdown, safe_filename
from .youtube import CaptionNotFoundError, fetch_captions, fetch_video_info, resolve_yt_dlp_command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yt2feishu",
        description="Convert YouTube captions to Markdown and optionally upload to Feishu Docs.",
    )
    parser.add_argument("url", nargs="?", help="YouTube video URL")
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Check local dependencies without fetching a YouTube video.",
    )
    parser.add_argument(
        "--out-dir",
        default="notes",
        help="Directory where the Markdown file will be written. Default: notes",
    )
    parser.add_argument(
        "--langs",
        default="zh-Hans,zh-Hant,zh-CN,zh,en",
        help="Comma-separated language preference list. Default: zh-Hans,zh-Hant,zh-CN,zh,en",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Import the generated Markdown into Feishu Docs with feishu-cli.",
    )
    parser.add_argument(
        "--feishu-cli",
        help="Path to feishu-cli. Defaults to the first feishu-cli found on PATH.",
    )
    parser.add_argument(
        "--feishu-upload-images",
        action="store_true",
        help="Pass --upload-images to feishu-cli doc import.",
    )
    parser.add_argument(
        "--feishu-verbose",
        action="store_true",
        help="Pass --verbose to feishu-cli doc import.",
    )
    parser.add_argument(
        "--feishu-dry-run",
        action="store_true",
        help="Pass --dry-run to feishu-cli doc import.",
    )
    parser.add_argument(
        "--title",
        help="Override the generated Markdown and Feishu document title.",
    )
    parser.add_argument(
        "--cookies",
        help="Path to a Netscape-format cookies.txt file passed through to yt-dlp.",
    )
    parser.add_argument(
        "--cookies-from-browser",
        help="Browser name passed through to yt-dlp, for example: chrome, edge, firefox.",
    )
    parser.add_argument(
        "--js-runtimes",
        help="JavaScript runtime passed through to yt-dlp, for example: node or deno:/path/to/deno.",
    )
    parser.add_argument(
        "--remote-components",
        help="Remote component source passed through to yt-dlp, for example: ejs:github.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.doctor:
        return run_doctor(args)
    if not args.url:
        parser.error("the following arguments are required: url")

    preferred_langs = [lang.strip() for lang in args.langs.split(",") if lang.strip()]

    try:
        info = fetch_video_info(args.url, build_yt_dlp_args(args))
        captions, caption_meta = fetch_captions(info, preferred_langs)
    except FileNotFoundError as exc:
        print(f"Missing dependency: {exc}", file=sys.stderr)
        print("Install yt-dlp and make sure it is available on PATH.", file=sys.stderr)
        return 2
    except CaptionNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 4

    title = args.title or info.get("title") or "YouTube Transcript"
    markdown = build_markdown(
        title=title,
        info=info,
        captions=captions,
        caption_meta=caption_meta,
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{safe_filename(title)}.md"
    out_path.write_text(markdown, encoding="utf-8")
    print(f"Markdown written: {out_path.resolve()}")

    if args.upload:
        try:
            upload_output = upload_markdown(
                out_path,
                title,
                cli_path=args.feishu_cli,
                upload_images=args.feishu_upload_images,
                verbose=args.feishu_verbose,
                dry_run=args.feishu_dry_run,
            )
        except FileNotFoundError:
            print(
                "Missing dependency: feishu-cli is not available on PATH.\n"
                "Install it, then run `feishu-cli config create-app --save` before uploading.",
                file=sys.stderr,
            )
            return 5
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 6
        print(upload_output)

    return 0


def build_yt_dlp_args(args: argparse.Namespace) -> list[str]:
    ytdlp_args: list[str] = []
    if args.cookies:
        ytdlp_args.extend(["--cookies", args.cookies])
    if args.cookies_from_browser:
        ytdlp_args.extend(["--cookies-from-browser", args.cookies_from_browser])
    if args.js_runtimes:
        ytdlp_args.extend(["--js-runtimes", args.js_runtimes])
    if args.remote_components:
        ytdlp_args.extend(["--remote-components", args.remote_components])
    return ytdlp_args


def run_doctor(args: argparse.Namespace) -> int:
    checks: list[tuple[str, bool, str]] = []

    try:
        command = resolve_yt_dlp_command()
        version = run_version(command)
        checks.append(("yt-dlp", True, " ".join(command) + f" ({version})"))
    except FileNotFoundError:
        checks.append(("yt-dlp", False, "missing; install with `pip install -r requirements.txt`"))

    node = shutil.which("node")
    if node:
        checks.append(("node", True, f"{node} ({run_version([node])})"))
    else:
        checks.append(("node", False, "missing; useful for yt-dlp YouTube JS challenges"))

    feishu_cli = args.feishu_cli or shutil.which("feishu-cli")
    if feishu_cli:
        checks.append(("feishu-cli", True, feishu_cli))
        try:
            command = build_import_command(
                Path("example.md"),
                "Example",
                cli_path=feishu_cli,
                upload_images=args.feishu_upload_images,
                verbose=args.feishu_verbose,
                dry_run=args.feishu_dry_run,
            )
            checks.append(("feishu import command", True, quote_command(command)))
        except FileNotFoundError:
            checks.append(("feishu import command", False, "could not build command"))
    else:
        checks.append(("feishu-cli", False, "missing; see FEISHU_SETUP.md"))

    for name, ok, detail in checks:
        mark = "OK" if ok else "MISSING"
        print(f"[{mark}] {name}: {detail}")

    required_ok = all(ok for name, ok, _ in checks if name in {"yt-dlp"})
    return 0 if required_ok else 1


def run_version(command: list[str]) -> str:
    result = subprocess.run(
        [*command, "--version"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return (result.stdout or result.stderr).strip().splitlines()[0]


def quote_command(command: list[str]) -> str:
    return " ".join(f'"{part}"' if " " in part else part for part in command)


if __name__ == "__main__":
    raise SystemExit(main())
