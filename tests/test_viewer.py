import json
from pathlib import Path

import pytest
import viewer


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    (data / "DEMO.csv").write_text(
        "Date,Open,High,Low,Close,Volume\n"
        "2025-11-26,10,12,9,11,100\n"
        "2025-11-27,11,13,10,12,200\n"
        "2025-11-28,12,14,11,13,300\n"
        "2025-12-01,900,999,800,950,9999\n", encoding="utf-8")
    picks = tmp_path / "picks.json"
    picks.write_text(json.dumps({"2025-11": [{"symbol": "DEMO", "name": "Fictional", "cutoff": "2025-11-28"}]}))
    monkeypatch.setattr(viewer, "DATA_DIR", data)
    monkeypatch.setattr(viewer, "PICKS_FILE", picks)
    return viewer.app.test_client()


def test_future_data_is_excluded(client):
    response = client.get("/api/candles?symbol=DEMO&month=2025-11&cutoff=2099-01-01")
    assert response.status_code == 200
    assert response.json["cutoff"] == "2025-11-28"
    assert len(response.json["bars"]) == 3
    assert max(bar["close"] for bar in response.json["bars"]) == 13


@pytest.mark.parametrize("frame", ["week", "month"])
def test_aggregation_uses_only_visible_bars(client, frame):
    response = client.get(f"/api/candles?symbol=DEMO&month=2025-11&timeframe={frame}")
    assert response.json["bars"] == [{"time": "2025-11-28", "open": 10, "high": 14, "low": 9, "close": 13, "volume": 600}]


def test_unknown_symbol_is_not_exposed(client):
    assert client.get("/api/candles?symbol=UNKNOWN&month=2025-11").status_code == 404


@pytest.mark.parametrize("query", ["symbol=../DEMO&month=2025-11", "symbol=DEMO&month=invalid", "symbol=DEMO&month=2025-11&timeframe=invalid"])
def test_invalid_parameters(client, query):
    assert client.get("/api/candles?" + query).status_code == 400


def test_local_hosts_and_static_allowlist(client):
    assert client.get("/", headers={"Host": "untrusted.invalid"}).status_code == 400
    assert client.get("/viewer.py").status_code == 404
    assert client.get("/assets/secret.json").status_code == 404
    assert client.get("/healthz").json["status"] == "ok"
    assert client.get("/assets/app.js").status_code == 200


def test_symlink_cannot_escape_data_directory(client, tmp_path):
    outside = tmp_path / "outside.csv"
    outside.write_text("Date,Open,High,Low,Close,Volume\n2025-11-28,1,1,1,1,1\n")
    (viewer.DATA_DIR / "DEMO.csv").unlink()
    (viewer.DATA_DIR / "DEMO.csv").symlink_to(outside)
    assert client.get("/api/candles?symbol=DEMO&month=2025-11").status_code == 400


def test_cutoff_must_match_watchlist_month(client):
    viewer.PICKS_FILE.write_text(json.dumps({"2025-11": [{"symbol": "DEMO", "cutoff": "2025-12-01"}]}))
    assert client.get("/api/watchlists").status_code == 400


def test_nonfinite_prices_are_rejected(client):
    (viewer.DATA_DIR / "DEMO.csv").write_text("Date,Open,High,Low,Close,Volume\n2025-11-28,1,NaN,1,1,10\n")
    assert client.get("/api/candles?symbol=DEMO&month=2025-11").status_code == 400
