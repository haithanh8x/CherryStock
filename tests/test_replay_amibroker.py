import struct
from datetime import date
from types import SimpleNamespace

import pytest

from src.CrawlStock.readAmi import upsert_stock_eod, upsert_amibroker_intraday
from src.cherrystock.infrastructure.database.connection import DuckDBConnectionFactory
from src.cherrystock.application.services import replay_amibroker as replay


def test_exact_day_upserts_preserve_other_days(tmp_path, monkeypatch):
    monkeypatch.setenv('DUCKDB_ENV', 'local')
    folder = tmp_path / 'source'
    folder.mkdir()
    with (folder / 'AAA.dat').open('wb') as handle:
        for day in (20261109, 20261110, 20261111):
            handle.write(struct.pack('<iiffffff', day, 91530, 10, 11, 9, 10, 100, 0))
    factory = DuckDBConnectionFactory(db_path=tmp_path / 'test.duckdb')
    with factory.writer() as con:
        upsert_stock_eod(str(folder), 'raw_stock_eod', connection=con, replay_date=date(2026, 11, 9))
        upsert_stock_eod(str(folder), 'raw_stock_eod', connection=con, replay_date=date(2026, 11, 10))
        upsert_stock_eod(str(folder), 'raw_stock_eod', connection=con, replay_date=date(2026, 11, 10))
        assert con.execute('SELECT Date FROM raw_stock_eod ORDER BY Date').fetchall() == [(date(2026, 11, 9),), (date(2026, 11, 10),)]
        upsert_amibroker_intraday(str(folder), 'raw_stock_intraday', connection=con, replay_date=date(2026, 11, 10))
        assert con.execute('SELECT Date, COUNT(*) FROM raw_stock_intraday GROUP BY Date').fetchall() == [(date(2026, 11, 10), 1)]


@pytest.mark.parametrize('fail_first', [True, False])
def test_daily_transactions_and_stop_policy(tmp_path, monkeypatch, fail_first):
    monkeypatch.setenv('DUCKDB_ENV', 'local')
    factory = DuckDBConnectionFactory(db_path=tmp_path / 'test.duckdb')
    with factory.writer() as con:
        con.execute('CREATE TABLE raw_stock_eod (Ticker VARCHAR, Date DATE, Open DOUBLE, High DOUBLE, Low DOUBLE, Close DOUBLE, Volume BIGINT, OpenInt DOUBLE)')
        con.execute('CREATE TABLE raw_index_eod (Ticker VARCHAR, Date DATE)')
        con.execute('CREATE TABLE dimCalendar (FullDate DATE, DayNameOfWeek VARCHAR, IsHoliday VARCHAR)')
    days = []
    def load(folder, table, *, connection, replay_date):
        days.append(replay_date)
        connection.execute("INSERT INTO raw_stock_eod VALUES ('AAA',?,10,11,9,10,100,0)", [replay_date])
    def validate(**kwargs):
        if fail_first:
            raise RuntimeError('DQ failure')
    monkeypatch.setattr(replay, 'upsert_stock_eod', load)
    monkeypatch.setattr(replay, '_validate_scope', validate)
    settings = SimpleNamespace(amibroker_eod_targets=((tmp_path, 'raw_stock_eod'),), amibroker_intraday_targets=())
    if fail_first:
        with pytest.raises(RuntimeError, match='DQ failure'):
            replay.replay_amibroker_days(start=date(2026,11,10), end=date(2026,11,11), factory=factory, settings=settings)
    else:
        replay.replay_amibroker_days(start=date(2026,11,10), end=date(2026,11,11), factory=factory, settings=settings)
    assert days == ([date(2026,11,10)] if fail_first else [date(2026,11,10), date(2026,11,11)])
    with factory.reader() as con:
        assert con.execute('SELECT COUNT(*) FROM raw_stock_eod').fetchone()[0] == (0 if fail_first else 2)
