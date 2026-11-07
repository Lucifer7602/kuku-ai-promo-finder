# Run on Windows

1. Install Python 3.10+ from https://www.python.org/downloads/ and enable **Add Python to PATH** during setup.
2. Download or clone this repository.
3. Open Command Prompt in the project folder.
4. Run:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
streamlit run app.py
```

The browser opens the local app. Upload the fictional `examples/demo_microdrama.txt` to test safely.

To run the batch CLI instead:

```bat
python -m promofinder.cli examples/demo_microdrama.txt --out demo_run --per-episode 5
```

The app uses only local deterministic rules; it makes no paid API calls.
