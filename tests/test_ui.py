"""Smoke tests of the extra endpoints of the full-screen map (backend/ui.py)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend import ui  # noqa: E402,F401  (adds its routes to the app of backend.main)
from test_api import client  # noqa: E402,F401  (the fixture with a small data folder)


def test_ui_routes_come_before_the_static_mount():
    kinds = [type(r).__name__ for r in ui.app.router.routes]
    assert "Mount" not in kinds[:-1] or kinds.index("Mount") > max(i for i, k in enumerate(kinds) if k != "Mount")


def test_ui_days_reads_the_data_folder_of_the_test_and_long_periods_are_refused(client):
    days = client.get("/api/ui/days", params={"from": "2024-02-01", "to": "2024-02-05"}).json()["days"]
    assert sum(d["hotspots"] for d in days) == 15.0     # 2 February 2024: 10 in Chile, 5 in Argentina
    assert client.get("/api/ui/hotspots", params={"from": "2024-01-01", "to": "2024-12-31"}).status_code == 422
