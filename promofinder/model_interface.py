"""Stable boundary for swapping the rules scorer for an LLM reranker.

No provider SDK is imported here and no network/API call is made. A future
adapter can implement CandidateJudge and return the same JSON-shaped result.
"""
from __future__ import annotations
from typing import Protocol, TypedDict


class JudgeResult(TypedDict):
    hook_strength: int
    cliffhanger_strength: int
    standalone_clarity: int
    rationale: str


class CandidateJudge(Protocol):
    def judge(self, payload: dict) -> JudgeResult:
        """Judge one candidate using only the supplied screenplay evidence."""
        ...


# Payload contract for a future model adapter:
# {
#   "episode": 12,
#   "logline": "...",
#   "segments": [{"start": "00:43.70", "end": "01:27.21"}],
#   "opening_events": [{"kind": "dialogue|action|camera", "text": "..."}],
#   "middle_events": [...],
#   "ending_events": [...]
# }
# Keep exact timestamps in Python. The model judges quality; code validates that
# durations remain 20-60 seconds and that every quote is traceable to an event.
