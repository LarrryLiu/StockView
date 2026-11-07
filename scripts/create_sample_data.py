"""Generate fictional chart data; no selection rules are used.

生成虚构图表数据，不使用任何策略筛选规则。
"""

import csv
import math
from datetime import date, timedelta
from pathlib import Path


def main():
    target = Path(__file__).resolve().parents[1] / "collected_stocks"
    target.mkdir(parents=True, exist_ok=True)
    for symbol, base, phase in (("DEMO_A", 40, 0), ("DEMO_B", 65, 1.4)):
        path = target / f"{symbol}.csv"
        if path.exists():
            print(f"Keeping existing file: {path.name}")
            continue
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Date", "Open", "High", "Low", "Close", "Volume"])
            day, index = date(2023, 1, 2), 0
            while day <= date(2025, 12, 31):
                if day.weekday() < 5:
                    opening = base + 5 * math.sin(index / 40 + phase) + index * 0.005
                    closing = opening + 0.4 * math.sin(index / 3 + phase)
                    writer.writerow([day.isoformat(), round(opening, 4),
                                     round(max(opening, closing) + 0.5, 4),
                                     round(min(opening, closing) - 0.5, 4),
                                     round(closing, 4), 100000 + index % 17 * 1000])
                    index += 1
                day += timedelta(days=1)
        print(f"Created fictional data: {path.name}")


if __name__ == "__main__":
    main()
