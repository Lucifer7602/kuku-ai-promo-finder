from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable

from .parser import Episode, Event, to_timestamp

HOOK_WORDS = (
    "stop", "wait", "look", "who are you", "who gave", "what are you doing",
    "take your hands", "under arrest", "arrest him", "dying", "can't breathe",
    "poison", "arsenic", "fire", "burn", "explod", "attack", "strike",
    "threat", "hang", "gallows", "my lost son", "this ring", "you are dead",
    "you are not", "betray", "stole", "thief", "witchcraft", "witch",
    "no one will", "let her go", "help me", "someone is coming", "i found it",
)
CLIFF_WORDS = (
    "?", "impossible", "someone is coming", "who?", "where?", "what?",
    "what is your", "where did you", "take her", "hang", "gallows", "arrest",
    "not your", "not lawful", "not duchess", "not wife", "i found", "who sent",
    "who is", "what are you going", "choose your", "ten days", "cut to black",
    "freeze", "cliffhanger", "before an abrupt cut", "as the scene cuts",
)
CONFLICT_WORDS = (
    "betray", "abandon", "humiliat", "threat", "accus", "poison", "murder",
    "kill", "hang", "gallows", "arrest", "prison", "witch", "burn", "fire",
    "stole", "thief", "attack", "blood", "wound", "enemy", "traitor", "dead",
    "secret", "frame", "lie", "revenge", "destroy", "force", "rescue", "refuse",
)


@dataclass
class Candidate:
    rank: int
    episode: int
    start: float
    end: float
    duration: float
    score: float
    hook: str
    cliffhanger: str
    why: str
    hook_score: float
    cliff_score: float
    conflict_score: float
    standalone_score: float

    def as_dict(self) -> dict:
        data = asdict(self)
        data["segments"] = [{
            "episode": self.episode,
            "start": to_timestamp(self.start),
            "end": to_timestamp(self.end),
            "duration_seconds": round(self.duration, 2),
        }]
        data["start_ts"] = to_timestamp(self.start)
        data["end_ts"] = to_timestamp(self.end)
        return data


def _window_events(events: list[Event], start: float, end: float) -> list[Event]:
    return [e for e in events if e.end >= start and e.start <= end]


def _best_event(events: list[Event], start: float, end: float, opening: bool) -> Event | None:
    selected = [e for e in events if e.end >= start and e.start <= end]
    if not selected:
        return None
    if opening:
        def hook_value(e: Event) -> float:
            t = e.text.lower()
            return sum(2 for w in HOOK_WORDS if w in t) + (2 if "!" in t else 0) + (1 if "?" in t else 0) + (2 if e.kind == "action" else 0)
        return max(selected, key=hook_value)
    def cliff_value(e: Event) -> float:
        t = e.text.lower()
        return sum(2 for w in CLIFF_WORDS if w in t) + (2 if "?" in t else 0) + (1 if "!" in t else 0) + (2 if any(x in t for x in ("freeze", "cut to black", "suspense", "abrupt cut")) else 0)
    return max(selected, key=cliff_value)


def score_window(episode: Episode, start: float, end: float) -> Candidate | None:
    duration = end - start
    if duration < 20 or duration > 60 or end > episode.duration + 0.05:
        return None
    events = _window_events(episode.events, start, end)
    if not events:
        return None
    opening_events = [e for e in events if e.start <= start + 3 and e.end >= start]
    ending_events = [e for e in events if e.end >= end - 3 and e.start <= end]
    if not opening_events or not ending_events:
        return None
    hook_event = _best_event(opening_events, start, start + 3, True)
    cliff_event = _best_event(ending_events, end - 3, end, False)
    if hook_event is None or cliff_event is None:
        return None

    opening_text = " ".join(e.text.lower() for e in opening_events)
    ending_text = " ".join(e.text.lower() for e in ending_events)
    all_text = " ".join(e.text.lower() for e in events)
    hook_hits = sum(1 for word in HOOK_WORDS if word in opening_text)
    cliff_hits = sum(1 for word in CLIFF_WORDS if word in ending_text)
    hook_score = min(30.0, 8.0 + hook_hits * 4.0 + (5 if "!" in opening_text else 0) + (3 if "?" in opening_text else 0))
    cliff_score = min(30.0, 8.0 + cliff_hits * 4.0 + (5 if "?" in ending_text else 0) + (2 if "!" in ending_text else 0))
    conflict_hits = sum(1 for word in CONFLICT_WORDS if word in all_text)
    conflict_score = min(20.0, conflict_hits * 2.2)
    names = ("juliana", "alexander", "gerald", "clarissa", "catherine", "rupert", "duchess", "mother", "husband", "wife")
    name_hits = sum(1 for word in names if word in all_text)
    standalone_score = min(15.0, name_hits * 1.7 + (3 if episode.logline else 0))
    duration_score = 5.0 if 30 <= duration <= 50 else 3.0
    action_count = sum(1 for e in events if e.kind in {"action", "camera"})
    visual_score = min(5.0, action_count * 0.35)
    total = round(min(100.0, hook_score + cliff_score + conflict_score + standalone_score + duration_score + visual_score), 1)
    why = (
        f"Opens on {hook_event.kind} / dialogue with a high-attention cue, "
        f"builds through {conflict_hits} conflict signals, and cuts on an unresolved "
        f"final beat. Standalone clarity still needs an editor check."
    )
    return Candidate(
        rank=0, episode=episode.number, start=start, end=end,
        duration=round(duration, 2), score=total,
        hook=hook_event.text, cliffhanger=cliff_event.text, why=why,
        hook_score=round(hook_score, 1), cliff_score=round(cliff_score, 1),
        conflict_score=round(conflict_score, 1), standalone_score=round(standalone_score, 1),
    )


def _overlap_ratio(a: Candidate, b: Candidate) -> float:
    if a.episode != b.episode:
        return 0.0
    intersection = max(0.0, min(a.end, b.end) - max(a.start, b.start))
    union = max(a.end, b.end) - min(a.start, b.start)
    return intersection / union if union else 0.0


def find_candidates(episodes: Iterable[Episode], per_episode: int = 5) -> list[Candidate]:
    all_candidates: list[Candidate] = []
    for episode in episodes:
        starts = sorted({round(e.start, 2) for e in episode.events if e.kind in {"dialogue", "action", "camera"}})
        candidates: list[Candidate] = []
        for start in starts:
            for duration in range(20, 61, 5):
                end = start + duration
                if end <= episode.duration + 0.05:
                    candidate = score_window(episode, start, end)
                    if candidate and candidate.score >= 35:
                        candidates.append(candidate)
        candidates.sort(key=lambda c: c.score, reverse=True)
        selected: list[Candidate] = []
        for candidate in candidates:
            if all(_overlap_ratio(candidate, existing) < 0.55 for existing in selected):
                selected.append(candidate)
            if len(selected) >= per_episode:
                break
        all_candidates.extend(selected)
    all_candidates.sort(key=lambda c: c.score, reverse=True)
    for index, candidate in enumerate(all_candidates, 1):
        candidate.rank = index
    return all_candidates
