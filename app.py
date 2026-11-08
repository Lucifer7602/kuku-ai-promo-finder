from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import streamlit as st

# Always load this checkout's package, not another installed package with the
# same name. This is especially useful when Streamlit is launched from a
# different working directory on Windows.
APP_DIR = Path(__file__).resolve().parent
APP_DIR_STR = str(APP_DIR)
if APP_DIR_STR in sys.path:
    sys.path.remove(APP_DIR_STR)
sys.path.insert(0, APP_DIR_STR)

import promofinder.scorer as scorer_module
from promofinder.parser import parse_screenplay
from promofinder.scorer import find_candidates

EXPECTED_SCORER = (APP_DIR / "promofinder" / "scorer.py").resolve()
LOADED_SCORER = Path(scorer_module.__file__).resolve()
SCORER_MATCHES_PROJECT = LOADED_SCORER == EXPECTED_SCORER

st.set_page_config(page_title="Microdrama Promo Finder", page_icon="🎬", layout="wide")
st.title("Microdrama Promo Finder")
st.caption("A free, local-first screenplay screening tool. It suggests candidates; an editor makes the final call.")

# Show runtime identity immediately, even before a screenplay is uploaded.
# This lets users confirm the correct checkout is running before analysis.
with st.expander("Runtime diagnostics — verify the project currently running", expanded=True):
    st.write(f"**App file running:** `{Path(__file__).resolve()}`")
    st.write(f"**Scorer file loaded:** `{LOADED_SCORER}`")
    st.write(f"**Expected scorer file:** `{EXPECTED_SCORER}`")
    st.write(f"**Scorer loaded from this project:** {'YES' if SCORER_MATCHES_PROJECT else 'NO'}")

with st.sidebar:
    st.header("Run settings")
    per_episode = st.slider("Maximum candidates per episode", min_value=1, max_value=10, value=5)
    st.caption("Candidates are screenplay-based suggestions, not finished video edits.")

uploaded = st.file_uploader("Upload a UTF-8 screenplay text file (.txt)", type=["txt"])
manual_text = st.text_area("Or paste screenplay text", height=180, placeholder="Paste timestamped screenplay text here...")

col1, col2 = st.columns([1, 1])
with col1:
    analyze_clicked = st.button(
        "Find promo candidates",
        type="primary",
        disabled=(uploaded is None and not manual_text.strip()),
    )
with col2:
    clear_clicked = st.button("Clear previous results")

if clear_clicked:
    st.session_state.pop("run", None)
    st.rerun()

if analyze_clicked:
    if uploaded is not None:
        source_text = uploaded.getvalue().decode("utf-8-sig", errors="replace")
        source_name = uploaded.name
        source_type = "uploaded file"
    else:
        source_text = manual_text
        source_name = "pasted_text.txt"
        source_type = "pasted text"

    episodes = parse_screenplay(source_text)
    candidates = find_candidates(episodes, per_episode=per_episode)
    candidate_counts = Counter(c.episode for c in candidates)
    parsed_numbers = [e.number for e in episodes]
    number_counts = Counter(parsed_numbers)
    missing_episode_numbers = (
        [n for n in range(min(parsed_numbers), max(parsed_numbers) + 1) if n not in number_counts]
        if parsed_numbers else []
    )
    duplicate_episode_numbers = sorted(n for n, count in number_counts.items() if count > 1)
    episodes_without_events = [e.number for e in episodes if not e.events]
    episode_counts = [
        {"Episode": f"{e.number:02d}", "Timestamped blocks": len(e.events),
         "Selected candidates": candidate_counts.get(e.number, 0)}
        for e in episodes
    ]

    st.session_state["run"] = {
        "source_name": source_name,
        "source_type": source_type,
        "source_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        "source_characters": len(source_text),
        "episodes": [e.as_dict() for e in episodes],
        "candidates": [c.as_dict() for c in candidates],
        "candidate_counts": episode_counts,
        "per_episode_limit": per_episode,
        "app_file": str(Path(__file__).resolve()),
        "scorer_file": str(LOADED_SCORER),
        "expected_scorer_file": str(EXPECTED_SCORER),
        "scorer_matches_project": SCORER_MATCHES_PROJECT,
        "timestamped_blocks": sum(len(e.events) for e in episodes),
        "missing_episode_numbers": missing_episode_numbers,
        "duplicate_episode_numbers": duplicate_episode_numbers,
        "episodes_without_events": episodes_without_events,
    }

run = st.session_state.get("run")
if run:
    if not run["episodes"]:
        st.error("No episodes were recognised. Check that the file contains episode headers in the documented format, then review the README example.")
    else:
        st.success(f"Parsed {len(run['episodes'])} episodes; found {len(run['candidates'])} candidate windows.")
    if run["missing_episode_numbers"]:
        st.warning(f"Possible missing episode numbers between the first and last parsed episode: {run['missing_episode_numbers']}")
    if run["duplicate_episode_numbers"]:
        st.warning(f"Duplicate episode numbers detected: {run['duplicate_episode_numbers']}")
    if run["episodes_without_events"]:
        st.warning(f"These episodes have headers but no timestamped blocks were parsed: {run['episodes_without_events']}")

    if not run["scorer_matches_project"]:
        st.error(
            "Runtime mismatch: the app imported a scorer outside this project folder. "
            "Use the scorer path shown in Run diagnostics to identify the wrong copy."
        )

    rows = []
    for c in run["candidates"]:
        rows.append({
            "Rank": c["rank"], "Episode": c["episode"], "Start": c["start_ts"],
            "End": c["end_ts"], "Duration (s)": c["duration"], "Score": c["score"],
            "Hook": c["hook"], "Cliffhanger": c["cliffhanger"],
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.warning("No candidates passed the first-pass threshold. Review the source format and try again.")

    with st.expander("Run diagnostics — use this to verify the 50-episode run"):
        st.write(f"**Input:** {run['source_name']} ({run['source_type']})")
        st.write(f"**Episodes parsed:** {len(run['episodes'])}")
        st.write(f"**Timestamped blocks parsed:** {run['timestamped_blocks']}")
        st.write(f"**Missing episode numbers in parsed range:** {run['missing_episode_numbers']}")
        st.write(f"**Duplicate episode numbers:** {run['duplicate_episode_numbers']}")
        st.write(f"**Episodes with zero parsed blocks:** {run['episodes_without_events']}")
        st.write(f"**Maximum candidates per episode selected:** {run['per_episode_limit']}")
        st.write(f"**Total candidates returned:** {len(run['candidates'])}")
        st.write(f"**App file running:** `{run['app_file']}`")
        st.write(f"**Scorer file loaded:** `{run['scorer_file']}`")
        st.write(f"**Expected scorer file:** `{run['expected_scorer_file']}`")
        st.write(f"**Scorer loaded from this project:** {'YES' if run['scorer_matches_project'] else 'NO'}")
        st.write(f"**Input SHA-256:** `{run['source_sha256']}`")
        st.write(f"**Input character count:** {run['source_characters']}")
        st.dataframe(pd.DataFrame(run["candidate_counts"]), use_container_width=True, hide_index=True)

    st.download_button(
        "Download JSON", json.dumps(run, indent=2),
        file_name="promo_candidates.json", mime="application/json",
    )
    st.download_button(
        "Download CSV", df.to_csv(index=False),
        file_name="promo_candidates.csv", mime="text/csv",
    )

with st.expander("How to read the score"):
    st.markdown("""
    - **Hook (30):** high-attention language or action in the first 3 seconds.
    - **Cliffhanger (30):** unresolved question, threat, reveal, or suspense cue in the final 3 seconds.
    - **Conflict (20):** betrayal, danger, accusation, arrest, loss, or rescue language.
    - **Standalone (15):** character and stakes signals inside the selected window.
    - **Duration / visual (10):** favors 30-50 seconds and windows with visual/action events.

    The score is a transparent heuristic, not a prediction of watch-through or conversion. The script may describe a visual moment that does not survive the final edit; always check the actual video.
    """)
