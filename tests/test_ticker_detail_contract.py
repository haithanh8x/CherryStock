"""Ticker popup contract: isolation, formatting, all-field explanations."""
from __future__ import annotations

import duckdb
import pytest

from webapp.ticker_detail_contract import (
    FIELDS, FIELD_HINTS, DATE_FIELDS, PARTITIONS,
    detail_query, normalize_ticker, format_field, field_hint,
)


def test_every_displayed_field_has_meaning_and_example():
    assert [len(fields) for fields in FIELDS.values()] == [21, 24, 44]
    for fields in FIELDS.values():
        for field in fields:
            assert all(FIELD_HINTS[field])
            assert "Ví dụ minh họa:" in field_hint(field)


def test_units_do_not_confuse_fraction_score_and_ratio():
    assert format_field("LastSwingPct", -0.1) == "-10.00%"
    assert format_field("FactorCoverage", 0.8) == "80.00%"
    assert format_field("CurrentMoveSpeedPctPerBar", 0.01) == "1.00%/bar"
    assert format_field("ConfidenceScore", 80) == "80"
    assert format_field("DirectionalBias", 0.3) == "0.3"
    assert format_field("CurrentMoveSpeedRatio", 1.5) == "1.50 lần"
    assert format_field("CurrentLastClose", 100) == "100.00 nghìn đồng"
    assert format_field("CurrentMovePct", None) == "—"
    assert format_field("CurrentMovePct", float("nan")) == "—"


def test_ticker_validation_and_query_identifier_allowlist():
    assert normalize_ticker(" mwg ") == "MWG"
    with pytest.raises(ValueError):
        normalize_ticker("MWG'; DROP TABLE x;--")
    with pytest.raises(KeyError):
        detail_query("raw_stock_fa")
    for view in FIELDS:
        assert 'WHERE "Ticker" = ?' in detail_query(view)
        assert "SELECT *" not in detail_query(view)


@pytest.mark.parametrize("view", list(FIELDS))
def test_latest_per_config_keeps_ticker_isolation_and_empty_case(view):
    con = duckdb.connect()
    try:
        con.execute("ATTACH ':memory:' AS CherryMon")
        columns = FIELDS[view]
        # Strings suffice for ordered ISO date fixtures and identifier values.
        con.execute(f'CREATE TABLE CherryMon.main."{view}" (' +
                    ", ".join(f'"{name}" VARCHAR' for name in columns) + ")")
        def insert(ticker, day, config):
            row = {name: None for name in columns}
            row["Ticker"] = ticker
            row[DATE_FIELDS[view]] = day
            for key in PARTITIONS[view]:
                row[key] = config
            con.execute(f'INSERT INTO CherryMon.main."{view}" VALUES (' +
                        ", ".join("?" for _ in columns) + ")",
                        [row[name] for name in columns])
        insert("MWG", "2026-09-24", "1")
        insert("MWG", "2026-09-25", "1")
        insert("MWG", "2026-09-23", "2")
        insert("FPT", "2026-09-26", "1")
        result = con.execute(detail_query(view), ["MWG"]).fetchall()
        assert len(result) == 2
        assert {r[columns.index("Ticker")] for r in result} == {"MWG"}
        assert {r[columns.index(DATE_FIELDS[view])] for r in result} == {"2026-09-25", "2026-09-23"}
        assert con.execute(detail_query(view), ["SHS"]).fetchall() == []
    finally:
        con.close()
