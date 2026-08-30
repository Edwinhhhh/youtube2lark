from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from .captions import CaptionCue
from .markdown import build_markdown, safe_filename
from .youtube import CaptionNotFoundError, fetch_captions, fetch_video_info


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = PROJECT_ROOT / "web"
GENERATED_ROOT = PROJECT_ROOT / "generated"


class Yt2FeishuWebHandler(BaseHTTPRequestHandler):
    server_version = "yt2feishu-web/0.1"

    def do_GET(self) -> None:
        if self.path == "/" or self.path == "/index.html":
            self.serve_file(WEB_ROOT / "index.html")
            return

        if self.path.startswith("/assets/"):
            asset_path = WEB_ROOT / self.path.lstrip("/")
            self.serve_file(asset_path)
            return

        if self.path.startswith("/downloads/"):
            filename = unquote(self.path.removeprefix("/downloads/"))
            download_path = (GENERATED_ROOT / filename).resolve()
            if GENERATED_ROOT.resolve() not in download_path.parents:
                self.send_error(HTTPStatus.BAD_REQUEST)
                return
            self.serve_file(download_path, as_attachment=True)
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path != "/api/convert":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            payload = self.read_json()
            result = convert_request(payload)
        except ValueError as exc:
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        except FileNotFoundError:
            self.send_json(
                {
                    "ok": False,
                    "error": "Missing dependency: yt-dlp. Run `pip install -r requirements.txt`.",
                },
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return
        except CaptionNotFoundError as exc:
            self.send_json(
                {
                    "ok": False,
                    "error": (
                        f"{str(exc)}\n\n"
                        "这个视频没有通过 YouTube 暴露可抓取字幕。当前原型只处理已有字幕；"
                        "下一版可以加 Whisper 或飞书妙记做音频转写。"
                    ),
                },
                HTTPStatus.UNPROCESSABLE_ENTITY,
            )
            return
        except RuntimeError as exc:
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_GATEWAY)
            return

        self.send_json({"ok": True, **result})

    def log_message(self, format: str, *args: object) -> None:
        print(f"[web] {self.address_string()} - {format % args}")

    def read_json(self) -> dict[str, object]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            raise ValueError("Request body is empty.")

        raw = self.rfile.read(content_length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be valid JSON.") from exc

        if not isinstance(data, dict):
            raise ValueError("Request body must be a JSON object.")
        return data

    def send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def serve_file(self, path: Path, *, as_attachment: bool = False) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        raw = path.read_bytes()

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        if as_attachment:
            self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.end_headers()
        self.wfile.write(raw)


def convert_request(payload: dict[str, object]) -> dict[str, object]:
    url = str(payload.get("url") or "").strip()
    if not url:
        raise ValueError("Please paste a YouTube URL.")
    if "youtube.com/" not in url and "youtu.be/" not in url:
        raise ValueError("This prototype currently only accepts YouTube URLs.")

    preferred_langs = parse_langs(str(payload.get("langs") or "zh-Hans,zh-Hant,zh-CN,zh,en"))
    extra_args = build_yt_dlp_args(payload)

    info, auto_cookies_used = fetch_video_info_with_cookie_fallback(url, extra_args)

    captions, caption_meta = fetch_captions(info, preferred_langs)
    markdown = make_markdown(info, captions, caption_meta)
    filename = write_markdown(info, markdown)

    return {
        "filename": filename,
        "downloadUrl": f"/downloads/{filename}",
        "markdown": markdown,
        "title": info.get("title") or "YouTube Transcript",
        "channel": info.get("uploader") or info.get("channel") or "",
        "thumbnail": info.get("thumbnail") or "",
        "captionLanguage": caption_meta.get("language", ""),
        "captionSource": caption_meta.get("source", ""),
        "cueCount": len(captions),
        "autoCookiesUsed": auto_cookies_used,
    }


def make_markdown(
    info: dict[str, object],
    captions: list[CaptionCue],
    caption_meta: dict[str, str],
) -> str:
    title = str(info.get("title") or "YouTube Transcript")
    return build_markdown(
        title=title,
        info=info,
        captions=captions,
        caption_meta=caption_meta,
    )


def write_markdown(info: dict[str, object], markdown: str) -> str:
    GENERATED_ROOT.mkdir(parents=True, exist_ok=True)
    title = str(info.get("title") or "YouTube Transcript")
    filename = f"{safe_filename(title)}.md"
    output_path = GENERATED_ROOT / filename
    output_path.write_text(markdown, encoding="utf-8")
    return filename


def parse_langs(value: str) -> list[str]:
    langs = [part.strip() for part in value.split(",") if part.strip()]
    return langs or ["zh-Hans", "zh-Hant", "zh-CN", "zh", "en"]


def build_yt_dlp_args(payload: dict[str, object]) -> list[str]:
    args: list[str] = []
    passthrough = {
        "cookies": "--cookies",
        "cookiesFromBrowser": "--cookies-from-browser",
        "jsRuntimes": "--js-runtimes",
        "remoteComponents": "--remote-components",
    }

    for key, flag in passthrough.items():
        value = str(payload.get(key) or "").strip()
        if value:
            args.extend([flag, value])

    return args


def fetch_video_info_with_cookie_fallback(
    url: str,
    args: list[str],
) -> tuple[dict[str, object], bool]:
    try:
        return fetch_video_info(url, args), False
    except RuntimeError as exc:
        first_error = str(exc)

    fallbacks = cookie_fallback_browsers(first_error, args)
    fallback_errors: list[str] = []
    base_args = without_arg_pair(args, "--cookies-from-browser")

    for browser in fallbacks:
        try:
            return fetch_video_info(url, [*base_args, "--cookies-from-browser", browser]), True
        except RuntimeError as exc:
            fallback_errors.append(f"{browser}: {str(exc).splitlines()[0]}")

    if fallback_errors:
        raise RuntimeError(
            f"{first_error}\n\nCookie fallback attempts also failed:\n"
            + "\n".join(f"- {line}" for line in fallback_errors)
        )
    raise RuntimeError(first_error)


def cookie_fallback_browsers(error: str, args: list[str]) -> list[str]:
    if "--cookies" in args:
        return []
    selected_browser = arg_value(args, "--cookies-from-browser")
    browsers = ["edge", "firefox", "chrome"]

    if "Failed to decrypt with DPAPI" in error:
        return [browser for browser in browsers if browser != selected_browser]

    auth_markers = (
        "Sign in to confirm",
        "not a bot",
        "cookies-from-browser",
    )
    if not selected_browser and any(marker in error for marker in auth_markers):
        return browsers

    return []


def arg_value(args: list[str], flag: str) -> str | None:
    for index, value in enumerate(args):
        if value == flag and index + 1 < len(args):
            return args[index + 1]
    return None


def without_arg_pair(args: list[str], flag: str) -> list[str]:
    cleaned: list[str] = []
    skip_next = False
    for value in args:
        if skip_next:
            skip_next = False
            continue
        if value == flag:
            skip_next = True
            continue
        cleaned.append(value)
    return cleaned


def run(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), Yt2FeishuWebHandler)
    print(f"yt2feishu web prototype running at http://{host}:{port}")
    server.serve_forever()


def main() -> int:
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
