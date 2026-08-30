from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Any
from urllib.request import Request, urlopen

from .captions import CaptionCue, parse_caption_payload


class CaptionNotFoundError(RuntimeError):
    pass


@dataclass(frozen=True)
class CaptionTrack:
    language: str
    source: str
    ext: str
    url: str


def fetch_video_info(url: str, extra_args: list[str] | None = None) -> dict[str, Any]:
    command = resolve_yt_dlp_command()
    extra_args = extra_args or []
    result = subprocess.run(
        [*command, *extra_args, "-J", "--skip-download", url],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        if "Sign in to confirm" in detail or "not a bot" in detail:
            detail = (
                f"{detail}\n\n"
                "Tip: YouTube is asking yt-dlp for an authenticated browser session. "
                "Try passing --cookies-from-browser chrome, or export a cookies.txt file "
                "and pass it with --cookies."
            )
        if "Failed to decrypt with DPAPI" in detail:
            detail = (
                f"{detail}\n\n"
                "Tip: Chrome cookies could not be decrypted on Windows. "
                "Try --cookies-from-browser edge or --cookies-from-browser firefox if you are "
                "logged into YouTube there, or export a Netscape-format cookies.txt file and "
                "pass it with --cookies."
            )
        if "No supported JavaScript runtime" in detail:
            detail = (
                f"{detail}\n\n"
                "Tip: install a supported JavaScript runtime, then pass something like "
                "--js-runtimes node --remote-components ejs:github."
            )
        raise RuntimeError(f"yt-dlp failed: {detail}")

    return json.loads(result.stdout)


def fetch_captions(
    info: dict[str, Any],
    preferred_langs: list[str],
) -> tuple[list[CaptionCue], dict[str, str]]:
    track = choose_caption_track(info, preferred_langs)
    payload = download_text(track.url)
    cues = parse_caption_payload(payload, track.ext)

    if not cues:
        raise CaptionNotFoundError(
            f"Caption track {track.language} ({track.source}) did not contain readable text."
        )

    return cues, {
        "language": track.language,
        "source": track.source,
        "format": track.ext,
    }


def choose_caption_track(info: dict[str, Any], preferred_langs: list[str]) -> CaptionTrack:
    subtitles = info.get("subtitles") or {}
    automatic_captions = info.get("automatic_captions") or {}
    supported_exts = ("json3", "vtt")

    for source_name, source in (("manual", subtitles), ("automatic", automatic_captions)):
        for language in ordered_languages(source, preferred_langs):
            tracks = source.get(language) or []
            for ext in supported_exts:
                for track in tracks:
                    if track.get("ext") == ext and track.get("url"):
                        return CaptionTrack(
                            language=language,
                            source=source_name,
                            ext=ext,
                            url=track["url"],
                        )

    available = sorted(set(subtitles) | set(automatic_captions))
    if available:
        raise CaptionNotFoundError(
            "No supported caption track found. "
            f"Preferred languages: {', '.join(preferred_langs)}. "
            f"Available languages: {', '.join(available[:40])}."
        )
    raise CaptionNotFoundError("This video does not expose captions through yt-dlp.")


def ordered_languages(source: dict[str, Any], preferred_langs: list[str]) -> list[str]:
    ordered: list[str] = []
    for preferred in preferred_langs:
        if preferred in source and preferred not in ordered:
            ordered.append(preferred)

    for language in source:
        if any(language.startswith(f"{preferred}-") for preferred in preferred_langs):
            if language not in ordered:
                ordered.append(language)

    for language in source:
        if language not in ordered:
            ordered.append(language)

    return ordered


def download_text(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 yt2feishu/0.1",
        },
    )
    with urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def resolve_yt_dlp_command() -> list[str]:
    executable = shutil.which("yt-dlp")
    if executable:
        return [executable]

    module_check = subprocess.run(
        [sys.executable, "-c", "import yt_dlp"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if module_check.returncode == 0:
        return [sys.executable, "-m", "yt_dlp"]

    raise FileNotFoundError("yt-dlp")
