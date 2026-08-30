from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CaptionCue:
    start_ms: int
    end_ms: int | None
    text: str


_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")
_VTT_TIME_RE = re.compile(
    r"(?P<start>(?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})\s+-->\s+"
    r"(?P<end>(?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})"
)


def parse_caption_payload(payload: str, ext: str) -> list[CaptionCue]:
    ext = ext.lower()
    if ext == "json3":
        return parse_json3(payload)
    if ext == "vtt":
        return parse_vtt(payload)
    raise ValueError(f"Unsupported caption format: {ext}")


def parse_json3(payload: str) -> list[CaptionCue]:
    data = json.loads(payload)
    cues: list[CaptionCue] = []

    for event in data.get("events", []):
        segs = event.get("segs") or []
        text = "".join(seg.get("utf8", "") for seg in segs)
        text = clean_caption_text(text)
        if not text:
            continue

        start_ms = int(event.get("tStartMs", 0))
        duration_ms = event.get("dDurationMs")
        end_ms = start_ms + int(duration_ms) if duration_ms is not None else None
        cues.append(CaptionCue(start_ms=start_ms, end_ms=end_ms, text=text))

    return dedupe_cues(cues)


def parse_vtt(payload: str) -> list[CaptionCue]:
    cues: list[CaptionCue] = []
    lines = payload.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    index = 0

    while index < len(lines):
        match = _VTT_TIME_RE.search(lines[index])
        if not match:
            index += 1
            continue

        start_ms = parse_timestamp(match.group("start"))
        end_ms = parse_timestamp(match.group("end"))
        index += 1

        text_lines: list[str] = []
        while index < len(lines) and lines[index].strip():
            text_lines.append(lines[index].strip())
            index += 1

        text = clean_caption_text(" ".join(text_lines))
        if text:
            cues.append(CaptionCue(start_ms=start_ms, end_ms=end_ms, text=text))

        index += 1

    return dedupe_cues(cues)


def clean_caption_text(text: str) -> str:
    text = html.unescape(text)
    text = _TAG_RE.sub("", text)
    text = text.replace("\u200b", "")
    text = text.replace("\ufeff", "")
    text = _SPACE_RE.sub(" ", text)
    return text.strip()


def dedupe_cues(cues: list[CaptionCue]) -> list[CaptionCue]:
    deduped: list[CaptionCue] = []
    previous_text = ""

    for cue in cues:
        if cue.text == previous_text:
            continue
        deduped.append(cue)
        previous_text = cue.text

    return deduped


def parse_timestamp(value: str) -> int:
    value = value.replace(",", ".")
    parts = value.split(":")

    if len(parts) == 2:
        hours = 0
        minutes = int(parts[0])
        seconds = float(parts[1])
    elif len(parts) == 3:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
    else:
        raise ValueError(f"Invalid timestamp: {value}")

    return int((hours * 3600 + minutes * 60 + seconds) * 1000)


def format_timestamp(ms: int) -> str:
    total_seconds = ms // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"

