from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_SQL = (
    PROJECT_ROOT
    / "src"
    / "DuckDB"
    / "sql"
    / "price_movement_character_v1_profile_view.sql"
)


def test_profile_view_is_bounded_by_recent_confirmed_swings() -> None:
    sql = PROFILE_SQL.read_text(encoding="utf-8")

    assert 'CREATE OR REPLACE VIEW "CherryMon"."main"."vw_Ticker_Movement_Profile"' in sql
    assert "ROW_NUMBER() OVER" in sql
    assert "PARTITION BY s.ConfigId, s.Ticker, s.Direction" in sql
    assert "ORDER BY s.ConfirmedAtDate DESC" in sql
    assert "WHERE rn <= ProfileMaxSwings" in sql


def test_all_price_movement_write_entry_points_apply_bounded_profile_view() -> None:
    expected = "price_movement_character_v1_profile_view.sql"
    files = (
        PROJECT_ROOT / "src" / "cherrystock" / "application" / "services" / "sync_write_pipeline.py",
        PROJECT_ROOT / "scripts" / "initload" / "init_reload_price_movement_character.py",
        PROJECT_ROOT / "scripts" / "run_price_movement.py",
    )

    for path in files:
        text = path.read_text(encoding="utf-8")
        assert expected in text, f"{path} does not apply the bounded movement profile view"
