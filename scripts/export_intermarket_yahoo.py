"""Export validated Yahoo Finance 1Y daily OHLC for GitHub Pages deployment."""
from __future__ import annotations
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import yfinance as yf

SYMBOLS = {
    "vnindex": "^VNINDEX.VN", "spx": "^GSPC", "ndx": "^NDX",
    "btc": "BTC-USD", "gold": "GC=F", "oil": "CL=F",
    "dxy": "DX-Y.NYB", "usdvnd": "VND=X",
}

def export(output: Path) -> None:
    assets = {}
    errors = {}
    for key, symbol in SYMBOLS.items():
        try:
            frame = yf.download(symbol, period="1y", interval="1d", auto_adjust=True,
                                progress=False, threads=False, timeout=20)
            if frame.empty:
                raise ValueError("Yahoo returned empty history")
            if isinstance(frame.columns, pd.MultiIndex):
                frame.columns = frame.columns.get_level_values(0)
            if not all(c in frame.columns for c in ("Open", "High", "Low", "Close")):
                raise ValueError("Missing OHLC columns")
            candles = []
            for idx, row in frame.iterrows():
                o, h, l, c = [float(row[k]) for k in ("Open", "High", "Low", "Close")]
                if not all(math.isfinite(v) and v > 0 for v in (o, h, l, c)):
                    continue
                v = float(row.get("Volume", 0) or 0)
                candles.append({
                    "date": pd.Timestamp(idx).date().isoformat(),
                    "open": o, "high": h, "low": l, "close": c,
                    "volume": v if math.isfinite(v) and v >= 0 else 0,
                })
            candles = list({c["date"]: c for c in candles}.values())
            candles.sort(key=lambda c: c["date"])
            if len(candles) < 100:
                raise ValueError(f"Only {len(candles)} candles (<100)")
            assets[key] = {"symbol": symbol, "asOf": candles[-1]["date"], "candles": candles}
            print(f"[OK] {symbol}: {len(candles)} bars to {candles[-1]['date']}")
        except Exception as exc:
            errors[key] = str(exc)
            print(f"[WARN] {symbol}: {exc}")
    if len(assets) < 5:
        raise RuntimeError(f"Yahoo returned only {len(assets)}/8 valid assets: {errors}")
    payload = {
        "schemaVersion": 1, "provider": "yahoo", "range": "1y", "interval": "1d",
        "generatedAt": datetime.now(timezone.utc).isoformat(), "assets": assets, "errors": errors,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    tmp.replace(output)
    print(f"[SUCCESS] Yahoo snapshot: {len(assets)}/8 assets; {output}")

if __name__ == "__main__":
    export(Path("frontend/public/data/intermarket-1y.json"))
