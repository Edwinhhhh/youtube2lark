from __future__ import annotations

import re
from typing import Any

from .captions import CaptionCue, format_timestamp


_FILENAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
_SPACE_RE = re.compile(r"\s+")


def build_markdown(
    title: str,
    info: dict[str, Any],
    captions: list[CaptionCue],
    caption_meta: dict[str, str],
) -> str:
    url = info.get("webpage_url") or info.get("original_url") or ""
    uploader = info.get("uploader") or info.get("channel") or ""
    duration = format_duration(info.get("duration"))
    upload_date = format_upload_date(info.get("upload_date"))
    language = caption_meta.get("language", "")
    caption_source = caption_meta.get("source", "")

    lines = [
        f"# {title}",
        "",
        "## Source",
        "",
        f"- URL: {url}",
        f"- Channel: {uploader}",
        f"- Upload date: {upload_date}",
        f"- Duration: {duration}",
        f"- Caption language: {language}",
        f"- Caption source: {caption_source}",
        "",
        "## Notes",
        "",
        "- Summary: TODO",
        "- Key points: TODO",
        "",
        "## Transcript",
        "",
    ]

    for cue in captions:
        lines.append(f"[{format_timestamp(cue.start_ms)}] {cue.text}")

    lines.append("")
    return "\n".join(lines)


def safe_filename(value: str, max_length: int = 80) -> str:
    value = _FILENAME_RE.sub(" ", value)
    value = _SPACE_RE.sub(" ", value).strip()
    value = value.rstrip(". ")
    if not value:
        return "youtube-transcript"
    return value[:max_length].rstrip(". ")


def format_duration(seconds: Any) -> str:
    if seconds is None:
        return ""

    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return str(seconds)

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    rest = seconds % 60

    if hours:
        return f"{hours}:{minutes:02d}:{rest:02d}"
    return f"{minutes}:{rest:02d}"


def format_upload_date(value: Any) -> str:
    if not value:
        return ""

    value = str(value)
    if len(value) == 8 and value.isdigit():
        return f"{value[:4]}-{value[4:6]}-{value[6:]}"
    return value

