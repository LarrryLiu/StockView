"""Local chart viewer for manually supplied watchlists.

手动观察名单的本地图表查看器；不包含自动选股或策略计算。
"""

from __future__ import annotations

import csv
import json
import math
import re
from datetime import date
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "collected_stocks"
PICKS_FILE = BASE_DIR / "picks.json"
SYMBOL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024


@app.before_request
def local_hosts_only():
    if request.host.partition(":")[0].lower() not in {"127.0.0.1", "localhost"}:
        return jsonify(error="Local access only. / 仅支持本机访问。"), 400


@app.after_request
def response_headers(response):
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; "
        "base-uri 'none'; form-action 'none'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


def load_watchlists():
    payload = json.loads(PICKS_FILE.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("picks.json must contain a month-to-watchlist object")
    for month, rows in payload.items():
        if not MONTH.fullmatch(month) or not isinstance(rows, list):
            raise ValueError("Invalid watchlist month or rows")
        for row in rows:
            if not isinstance(row, dict) or not SYMBOL.fullmatch(str(row.get("symbol", ""))):
                raise ValueError("Invalid watchlist symbol")
            cutoff = date.fromisoformat(row["cutoff"])
            if cutoff.strftime("%Y-%m") != month:
                raise ValueError("A watchlist cutoff must belong to its month")
    return payload


def load_bars(symbol: str, cutoff: str):
    if not SYMBOL.fullmatch(symbol):
        raise ValueError("Invalid symbol")
    path = (DATA_DIR / f"{symbol}.csv").resolve()
    if not path.is_relative_to(DATA_DIR.resolve()):
        raise ValueError("CSV must be inside collected_stocks")
    rows = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for source in csv.DictReader(handle):
            day = date.fromisoformat(source["Date"]).isoformat()
            # Apply the stored cutoff before weekly/monthly aggregation.
            # 先按保存的历史日期截取，再聚合周线和月线。
            if day > cutoff:
                continue
            bar = {key.lower(): float(source[key]) for key in ("Open", "High", "Low", "Close", "Volume")}
            if not all(math.isfinite(value) for value in bar.values()):
                raise ValueError("Non-finite OHLCV value")
            if (min(bar[key] for key in ("open", "high", "low", "close")) <= 0
                or bar["volume"] < 0
                or bar["high"] < max(bar["open"], bar["close"], bar["low"])
                or bar["low"] > min(bar["open"], bar["close"], bar["high"])):
                raise ValueError("Invalid OHLCV range")
            if day in rows:
                raise ValueError("Duplicate daily date")
            rows[day] = {"time": day, **bar}
    return [rows[day] for day in sorted(rows)]


def aggregate(bars, timeframe):
    if timeframe == "day":
        return bars
    grouped = {}
    for bar in bars:
        day = date.fromisoformat(bar["time"])
        key = day.isocalendar()[:2] if timeframe == "week" else (day.year, day.month)
        if key not in grouped:
            grouped[key] = dict(bar)
        else:
            current = grouped[key]
            current.update(time=bar["time"], high=max(current["high"], bar["high"]),
                           low=min(current["low"], bar["low"]), close=bar["close"],
                           volume=current["volume"] + bar["volume"])
    return list(grouped.values())


@app.get("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/assets/<filename>")
def assets(filename):
    if filename not in {"app.css", "app.js"}:
        abort(404)
    return send_from_directory(BASE_DIR / "assets", filename)


@app.get("/vendor/<filename>")
def vendor(filename):
    if filename != "lightweight-charts.standalone.production.js":
        abort(404)
    return send_from_directory(BASE_DIR / "vendor", filename)


@app.get("/healthz")
def health():
    return jsonify(app="stockview-public-viewer", status="ok")


@app.get("/api/watchlists")
def watchlists():
    try:
        return jsonify(load_watchlists())
    except (OSError, ValueError, KeyError, TypeError):
        return jsonify(error="Check picks.json. / 请检查观察名单文件。"), 400


@app.get("/api/candles")
def candles():
    symbol = request.args.get("symbol", "")
    month = request.args.get("month", "")
    timeframe = request.args.get("timeframe", "day")
    if not SYMBOL.fullmatch(symbol) or not MONTH.fullmatch(month) or timeframe not in {"day", "week", "month"}:
        return jsonify(error="Invalid chart request. / 图表参数无效。"), 400
    try:
        row = next((item for item in load_watchlists().get(month, []) if item["symbol"] == symbol), None)
        if row is None:
            abort(404)
        bars = aggregate(load_bars(symbol, row["cutoff"]), timeframe)
        return jsonify(symbol=symbol, cutoff=row["cutoff"], timeframe=timeframe, bars=bars)
    except FileNotFoundError:
        return jsonify(error="CSV missing. Run the sample generator or add your own data. / 缺少 CSV。"), 404
    except (OSError, ValueError, KeyError, TypeError):
        return jsonify(error="Invalid watchlist or CSV data. / 观察名单或 CSV 数据无效。"), 400
