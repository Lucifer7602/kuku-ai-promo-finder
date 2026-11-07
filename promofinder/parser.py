from __future__ import annotations

import re
from dataclasses import asdict, dataclass

TIME_RE = re.compile(r"^(?P<minutes>\d{2}):(?P<seconds>\d{2})(?:\.(?P<centis>\d{1,2}))?$")
EP_RE = re.compile(
    r"EPISODE NUMBER:\s*Episode\s*(?P<number>\d+)\s*\n"
    r"EPISODE LOGLINE:\s*(?P<logline>.*?)\n"
    r"CONTINUITY NOTES:\s*(?P<continuity>.*?)\n",
    re.IGNORECASE | re.DOTALL,
)
BLOCK_RE = re.compile(
    r"\*\*(?P<role>[^*]+)\*\*:?\s*\n"
    r"Start:\s*\((?P<start>\d{2}:\d{2}(?:\.\d+)?)\)\s*\|\s*"
    r"End:\s*\((?P<end>\d{2}:\d{2}(?:\.\d+)?)\)\s*\n"
    r"(?P<body>.*?)(?=\n\n\*\*|\nSCENE\s*\d+|\n--- SCRIPT END ---|\Z)",
    re.IGNORECASE | re.DOTALL,
)
SCENE_RE = re.compile(r"Scene end:\s*(\d{2}:\d{2}(?:\.\d+)?)", re.IGNORECASE)


def to_seconds(value: str) -> float:
    match = TIME_RE.match(value.strip())
    if not match:
        raise ValueError(f"Unsupported timestamp: {value!r}")
    centis = match.group("centis") or "0"
    fraction = float("0." + centis) if match.group("centis") else 0.0
    return int(match.group("minutes")) * 60 + int(match.group("seconds")) + fraction


def to_timestamp(seconds: float) -> str:
    seconds = max(0.0, seconds)
    minutes = int(seconds // 60)
    whole_seconds = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis == 100:
        whole_seconds += 1
        centis = 0
    if whole_seconds == 60:
        minutes += 1
        whole_seconds = 0
    return f"{minutes:02d}:{whole_seconds:02d}.{centis:02d}"


@dataclass
class Event:
    role: str
    start: float
    end: float
    text: str
    kind: str

    def as_dict(self) -> dict:
        result = asdict(self)
        result["start_ts"] = to_timestamp(self.start)
        result["end_ts"] = to_timestamp(self.end)
        return result


@dataclass
class Episode:
    number: int
    logline: str
    continuity: str
    duration: float
    events: list[Event]

    def as_dict(self) -> dict:
        return {
            "episode": self.number,
            "logline": self.logline,
            "continuity": self.continuity,
            "duration_seconds": round(self.duration, 2),
            "event_count": len(self.events),
            "events": [event.as_dict() for event in self.events],
        }


def _clean_text(body: str) -> str:
    text = body.strip()
    if len(text) >= 2 and text[0] in ('"', "'") and text[-1] == text[0]:
        text = text[1:-1]
    return re.sub(r"\s+", " ", text).strip()


def parse_screenplay(text: str) -> list[Episode]:
    """Parse episode metadata and timestamped dialogue/action/camera blocks.

    Malformed blocks are skipped rather than crashing the entire run. Every
    returned event retains its source timestamp.
    """
    matches = list(EP_RE.finditer(text))
    episodes: list[Episode] = []
    for index, match in enumerate(matches):
        number = int(match.group("number"))
        section_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[match.start():section_end]
        events: list[Event] = []
        max_end = 0.0
        for block in BLOCK_RE.finditer(section):
            role = re.sub(r"\s+", " ", block.group("role").strip()).rstrip(":").strip()
            try:
                start = to_seconds(block.group("start"))
                end = to_seconds(block.group("end"))
            except ValueError:
                continue
            if end < start:
                continue
            body = _clean_text(block.group("body"))
            if not body:
                continue
            role_upper = role.upper()
            if role_upper == "CAMERA":
                kind = "camera"
            elif role_upper == "ACTION":
                kind = "action"
            elif role_upper in {"SOUND FX", "SOUND EFFECT", "SFX"}:
                kind = "sound"
            else:
                kind = "dialogue"
            events.append(Event(role=role, start=start, end=end, text=body, kind=kind))
            max_end = max(max_end, end)
        scene_ends = [to_seconds(x) for x in SCENE_RE.findall(section)]
        duration = max([max_end, *scene_ends], default=max_end)
        episodes.append(Episode(
            number=number,
            logline=re.sub(r"\s+", " ", match.group("logline")).strip(),
            continuity=re.sub(r"\s+", " ", match.group("continuity")).strip(),
            duration=duration,
            events=sorted(events, key=lambda e: (e.start, e.end)),
        ))
    return episodes
