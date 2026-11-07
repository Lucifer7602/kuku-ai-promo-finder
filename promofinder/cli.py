from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .parser import parse_screenplay
from .scorer import find_candidates


def main() -> None:
    parser = argparse.ArgumentParser(description="Find 20-60 second promo candidates in a timestamped screenplay.")
    parser.add_argument("input", help="UTF-8 .txt screenplay file")
    parser.add_argument("--out", default="raw_outputs", help="Output folder (default: raw_outputs)")
    parser.add_argument("--per-episode", type=int, default=5, help="Maximum non-overlapping candidates per episode")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)
    text = input_path.read_text(encoding="utf-8", errors="replace")
    episodes = parse_screenplay(text)
    candidates = find_candidates(episodes, per_episode=args.per_episode)

    episode_summary = [{"episode": e.number, "duration_seconds": round(e.duration, 2), "event_count": len(e.events)} for e in episodes]
    candidate_json = [candidate.as_dict() for candidate in candidates]
    (output_dir / "episode_summary.json").write_text(json.dumps(episode_summary, indent=2), encoding="utf-8")
    (output_dir / "auto_candidates.json").write_text(json.dumps(candidate_json, indent=2), encoding="utf-8")
    with (output_dir / "auto_candidates.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["rank", "episode", "start_ts", "end_ts", "duration", "score", "hook", "cliffhanger", "why"])
        writer.writeheader()
        for candidate in candidates:
            row = candidate.as_dict()
            writer.writerow({key: row.get(key, "") for key in writer.fieldnames})
    manifest = {
        "input_file_name": input_path.name,
        "episodes_parsed": len(episodes),
        "episode_numbers": [episode.number for episode in episodes],
        "timestamped_events_parsed": sum(len(e.events) for e in episodes),
        "candidate_count": len(candidates),
        "per_episode_limit": args.per_episode,
        "scoring": "transparent_rules_v1_no_external_api",
        "note": "These are unedited machine suggestions. Review footage and transcript boundaries before publishing.",
    }
    (output_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    print(f"Wrote files to: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
