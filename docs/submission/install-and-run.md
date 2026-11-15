# Install and run

The full runbook, with expected numbers and times for every step, is `docs/eda-runbook.md`. This is
the short path.

## Requirements

- Python 3.12 or later, Node.js 18 or later, Git, `bash` and `curl` (on Windows, Git Bash).
- About 2 GB of disk for the data.

## 1. Code and dependencies

```bash
git clone https://github.com/sxbast1anCZ/NASA-Space-Apps-2026.git
cd NASA-Space-Apps-2026
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
```

`npm run build` writes `frontend/dist`; the backend serves it at `/`.

## 2. Data

The data is not in the repository. Download and build it (details in the root `README.md` and the
runbook):

```bash
./scripts/download_firms.sh
./scripts/download_boundaries.sh
python scripts/build_hotspots.py
jupyter nbconvert --to notebook --execute --output-dir /tmp notebooks/01_quality.ipynb
python scripts/harmonize.py
```

For 2026 and NOAA-21, get a free FIRMS MAP_KEY, put it in `.env` (never commit it) and run
`./scripts/download_firms_api.sh` before building. The outlook and the zones need their own scripts
(`scripts/daily_*.py`, `scripts/fire_zones.py`); the app starts without them and shows those layers
empty.

## 3. Run

```bash
uvicorn backend.ui:app --port 8000
```

- Fireguard (full-screen map: History, Now, Outlook): <http://localhost:8000>
- Calendar app: <http://localhost:8000/#classic>
- API docs: <http://localhost:8000/docs>

To work on the frontend with hot reload, keep the backend running and, in another terminal:

```bash
cd frontend && npm run dev
```

Then open <http://localhost:5173> (Vite sends `/api` to port 8000).

## 4. Tests

```bash
pytest tests/
```

149 tests, all passing on 2026-11-15 (about 15 seconds on a laptop).
