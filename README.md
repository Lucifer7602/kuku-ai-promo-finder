# Microdrama Promo Finder

A small, local-first screening tool for timestamped microdrama screenplays. It proposes 20-60 second promo windows and gives editors evidence for the opening hook and ending cliffhanger. It does not edit video or predict campaign performance.

**Repository:** https://github.com/Lucifer7602/kuku-ai-promo-finder

## What it does

1. Parses episode headers, loglines, scene boundaries, and timestamped dialogue/action/camera blocks.
2. Generates candidate continuous windows in the 20-60 second range.
3. Scores candidates with inspectable rules for hook, cliffhanger, conflict, standalone clarity, and duration/visual cues.
4. Exports candidate results as JSON and CSV for editorial review.

The score is a heuristic prioritization aid, not a measure of audience performance. An editor must verify each suggestion against the final video and correct script-to-video timing drift.

## Run locally

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

python -m pip install -r requirements.txt
streamlit run app.py
```

Upload a UTF-8 `.txt` screenplay or paste screenplay text into the app.

## Command line

```bash
python -m promofinder.cli examples/demo_microdrama.txt --out demo_run --per-episode 5
```

Outputs: `episode_summary.json`, `auto_candidates.json`, `auto_candidates.csv`, and `run_manifest.json`.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Scoring approach

- Hook: 30 points
- Cliffhanger: 30 points
- Conflict: 20 points
- Standalone clarity: 15 points
- Duration and visual cues: 10 points

The current version is deterministic and does not call a paid API. `promofinder/model_interface.py` defines a model-agnostic interface for a future optional LLM reranker; timestamp parsing and duration validation remain code-controlled.

## Deploy on Streamlit Community Cloud

1. Sign in at https://share.streamlit.io/ with GitHub.
2. Create an app from this repository.
3. Select branch `main` and main file path `app.py`.
4. Deploy. Streamlit installs dependencies from the root `requirements.txt`.

This source repository is not itself a hosted app; paste the resulting Streamlit URL into your submission materials after successful deployment.

## Privacy and confidentiality

The Kuku assignment brief states that its supplied screenplay pack is confidential and must not be published or shared. This repository contains only source code, synthetic demo input, and synthetic demo output. Do not commit Kuku screenplay text, episode-specific extracts, raw outputs, private recommendations, or any other confidential input-pack material here. Share required raw outputs only via the designated submission channel or an access-controlled folder.
