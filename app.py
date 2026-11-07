from __future__ import annotations

import json
import streamlit as st
import pandas as pd

from promofinder.parser import parse_screenplay
from promofinder.scorer import find_candidates

st.set_page_config(page_title="Microdrama Promo Finder", page_icon="🎬", layout="wide")
st.title("Microdrama Promo Finder")
st.caption("A free, local-first screenplay screening tool. It suggests candidates; an editor makes the final call.")

with st.sidebar:
    st.header("Run settings")
    per_episode = st.slider("Maximum candidates per episode", min_value=1, max_value=10, value=5)
    st.caption("Candidates are screenplay-based suggestions, not finished video edits.")

uploaded = st.file_uploader("Upload a UTF-8 screenplay text file (.txt)", type=["txt"])
manual_text = st.text_area("Or paste screenplay text", height=180, placeholder="Paste timestamped screenplay text here...")

if st.button("Find promo candidates", type="primary", disabled=(uploaded is None and not manual_text.strip())):
    if uploaded is not None:
        source_text = uploaded.getvalue().decode("utf-8", errors="replace")
        source_name = uploaded.name
    else:
        source_text = manual_text
        source_name = "pasted_text.txt"

    episodes = parse_screenplay(source_text)
    candidates = find_candidates(episodes, per_episode=per_episode)
    st.session_state["run"] = {
        "source_name": source_name,
        "episodes": [e.as_dict() for e in episodes],
        "candidates": [c.as_dict() for c in candidates],
    }

run = st.session_state.get("run")
if run:
    st.success(f"Parsed {len(run['episodes'])} episodes; found {len(run['candidates'])} candidate windows.")
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
    st.download_button("Download JSON", json.dumps(run, indent=2), file_name="promo_candidates.json", mime="application/json")
    st.download_button("Download CSV", df.to_csv(index=False), file_name="promo_candidates.csv", mime="text/csv")

with st.expander("How to read the score"):
    st.markdown("""
    - **Hook (30):** high-attention language or action in the first 3 seconds.
    - **Cliffhanger (30):** unresolved question, threat, reveal, or suspense cue in the final 3 seconds.
    - **Conflict (20):** betrayal, danger, accusation, arrest, loss, or rescue language.
    - **Standalone (15):** character and stakes signals inside the selected window.
    - **Duration / visual (10):** favors 30-50 seconds and windows with visual/action events.

    The score is a transparent heuristic, not a prediction of watch-through or conversion. The script may describe a visual moment that does not survive the final edit; always check the actual video.
    """)
