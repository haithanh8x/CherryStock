"""
FireAnt financial history client (v3) - authenticated with Bearer token.

Why v3:
- Chrome DevTools cURL shows FireAnt REST requests include:
      Authorization: Bearer <access_token>
- Therefore HTTP 401 from anonymous requests is expected.
- This script NEVER hard-codes the token. Read it from environment variable:
      FIREANT_TOKEN

Install:
    pip install requests pandas

PowerShell:
    $env:FIREANT_TOKEN="YOUR_FIREANT_ACCESS_TOKEN"
    python .\fireant_financial_v3.py --symbol MWG

Optional:
    python .\fireant_financial_v3.py --symbol MWG --q-max 2048 --y-max 512
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Iterable

import requests

try:
    import pandas as pd
except ImportError:
    pd = None


BASE_URL = "https://restv2.fireant.vn"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-GB,en;q=0.9,en-US;q=0.8,vi;q=0.7,ru;q=0.6",
    "Origin": "https://fireant.vn",
    "Referer": "https://fireant.vn/",
    "Sec-CH-UA": '"Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
}


class FireAntError(RuntimeError):
    pass


class FireAntClient:
    def __init__(
        self,
        token: str | None = None,
        *,
        timeout: float = 30.0,
        sleep_between_requests: float = 0.20,
    ) -> None:
        token = token or os.getenv("FIREANT_TOKEN")
        if not token:
            raise FireAntError(
                "Missing FireAnt token.\n"
                "PowerShell:\n"
                '  $env:FIREANT_TOKEN="YOUR_TOKEN"\n'
                "Then run the script again."
            )

        token = token.strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()

        self.timeout = timeout
        self.sleep_between_requests = sleep_between_requests
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.session.headers["Authorization"] = f"Bearer {token}"

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "FireAntClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{BASE_URL}{path}"
        r = self.session.get(url, params=params, timeout=self.timeout)

        if r.status_code >= 400:
            body = r.text[:1500]
            raise FireAntError(
                f"HTTP {r.status_code}: {r.url}\n"
                f"Response: {body}"
            )

        try:
            return r.json()
        except ValueError as exc:
            raise FireAntError(
                f"Invalid JSON from {r.url}: {r.text[:1000]}"
            ) from exc

    def get_financial_data(
        self,
        symbol: str,
        period_type: str,
        count: int,
    ) -> list[dict[str, Any]]:
        period_type = period_type.upper()
        if period_type not in {"Q", "Y"}:
            raise ValueError("period_type must be Q or Y")

        data = self._get(
            f"/symbols/{symbol.upper()}/financial-data",
            {
                "type": period_type,
                "count": int(count),
            },
        )

        if not isinstance(data, list):
            raise FireAntError(
                f"Unexpected financial-data response: {type(data).__name__}"
            )

        return data

    def get_fundamental(self, symbol: str) -> dict[str, Any]:
        data = self._get(f"/symbols/{symbol.upper()}/fundamental")
        if not isinstance(data, dict):
            raise FireAntError(
                f"Unexpected fundamental response: {type(data).__name__}"
            )
        return data

    def get_dividends(
        self,
        symbol: str,
        count: int = 100,
    ) -> list[dict[str, Any]]:
        data = self._get(
            f"/symbols/{symbol.upper()}/dividends",
            {"count": int(count)},
        )
        if not isinstance(data, list):
            raise FireAntError(
                f"Unexpected dividends response: {type(data).__name__}"
            )
        return data

    @staticmethod
    def _period_key(
        row: dict[str, Any],
        period_type: str,
    ) -> tuple[Any, ...]:
        if period_type == "Q":
            return (
                row.get("symbol"),
                row.get("year"),
                row.get("quarter"),
            )
        return (row.get("symbol"), row.get("year"))

    @staticmethod
    def _sort_key(row: dict[str, Any]) -> tuple[int, int]:
        def i(v: Any) -> int:
            try:
                return int(v or 0)
            except (TypeError, ValueError):
                return 0

        return i(row.get("year")), i(row.get("quarter"))

    def get_all_financial_history(
        self,
        symbol: str,
        period_type: str,
        *,
        count_steps: Iterable[int] | None = None,
        max_count: int = 2048,
        stop_after_same_result: int = 2,
    ) -> list[dict[str, Any]]:
        if count_steps is None:
            count_steps = [
                5, 10, 20, 50, 100, 200, 500,
                1000, 1500, 2000, max_count
            ]

        steps = sorted({
            min(int(x), int(max_count))
            for x in count_steps
            if int(x) > 0
        })

        best: dict[tuple[Any, ...], dict[str, Any]] = {}
        previous_unique: int | None = None
        unchanged_runs = 0

        for count in steps:
            rows = self.get_financial_data(
                symbol,
                period_type,
                count,
            )

            for row in rows:
                best[self._period_key(row, period_type)] = row

            ordered = sorted(rows, key=self._sort_key)

            oldest = "N/A"
            newest = "N/A"

            if ordered:
                a, b = ordered[0], ordered[-1]
                if period_type == "Q":
                    oldest = f"{a.get('year')} Q{a.get('quarter')}"
                    newest = f"{b.get('year')} Q{b.get('quarter')}"
                else:
                    oldest = str(a.get("year"))
                    newest = str(b.get("year"))

            unique = len(best)

            print(
                f"[{symbol.upper()} {period_type}] "
                f"count={count:<5} "
                f"returned={len(rows):<5} "
                f"unique={unique:<5} "
                f"oldest={oldest:<10} "
                f"newest={newest}"
            )

            if previous_unique == unique:
                unchanged_runs += 1
            else:
                unchanged_runs = 0

            previous_unique = unique

            if unchanged_runs >= stop_after_same_result:
                print(
                    f"[{symbol.upper()} {period_type}] "
                    "No more history discovered; stop."
                )
                break

            if count >= max_count:
                break

            if self.sleep_between_requests:
                time.sleep(self.sleep_between_requests)

        out = list(best.values())
        out.sort(key=self._sort_key)
        return out


def flatten(row: dict[str, Any]) -> dict[str, Any]:
    result = {
        k: v
        for k, v in row.items()
        if k != "financialValues"
    }

    fv = row.get("financialValues")
    if isinstance(fv, dict):
        result.update(fv)

    return result


def save(
    symbol: str,
    q: list[dict[str, Any]],
    y: list[dict[str, Any]],
    fundamental: dict[str, Any] | None,
    dividends: list[dict[str, Any]] | None,
    output_dir: str,
) -> None:
    p = Path(output_dir)
    p.mkdir(parents=True, exist_ok=True)

    symbol = symbol.upper()

    (p / f"{symbol}_financial_Q_full_raw.json").write_text(
        json.dumps(q, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    (p / f"{symbol}_financial_Y_full_raw.json").write_text(
        json.dumps(y, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    if fundamental is not None:
        (p / f"{symbol}_fundamental.json").write_text(
            json.dumps(
                fundamental,
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )

    if dividends is not None:
        (p / f"{symbol}_dividends.json").write_text(
            json.dumps(
                dividends,
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )

    if pd is not None:
        pd.DataFrame([flatten(x) for x in q]).to_csv(
            p / f"{symbol}_financial_Q_full.csv",
            index=False,
            encoding="utf-8-sig",
        )
        pd.DataFrame([flatten(x) for x in y]).to_csv(
            p / f"{symbol}_financial_Y_full.csv",
            index=False,
            encoding="utf-8-sig",
        )


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="MWG")
    ap.add_argument("--q-max", type=int, default=2048)
    ap.add_argument("--y-max", type=int, default=512)
    ap.add_argument("--output-dir", default=".")
    ap.add_argument("--skip-dividends", action="store_true")
    ap.add_argument("--skip-fundamental", action="store_true")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    symbol = args.symbol.upper()

    with FireAntClient() as fa:
        print("Authentication: OK (Bearer token supplied)")

        print("\nQuarterly:")
        q = fa.get_all_financial_history(
            symbol,
            "Q",
            max_count=args.q_max,
        )

        print("\nYearly:")
        y = fa.get_all_financial_history(
            symbol,
            "Y",
            max_count=args.y_max,
        )

        fundamental = None
        if not args.skip_fundamental:
            fundamental = fa.get_fundamental(symbol)

        dividends = None
        if not args.skip_dividends:
            dividends = fa.get_dividends(symbol, count=100)

    save(
        symbol,
        q,
        y,
        fundamental,
        dividends,
        args.output_dir,
    )

    print("\nDone.")
    print("Quarterly periods:", len(q))
    print("Yearly periods    :", len(y))
    print("Output directory  :", Path(args.output_dir).resolve())


if __name__ == "__main__":
    main()