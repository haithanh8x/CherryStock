"""Bounded DAT-only replay. Never calls current metadata, APX or cloud publishing."""
from datetime import date, timedelta

from CrawlStock.readAmi import upsert_stock_eod, upsert_amibroker_intraday
from Ults.DataValidation import validate_data_quality, persist_data_quality_result
from cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork


def _validate_scope(*, source_table, connection, pipeline_name, **kwargs):
    kwargs.pop('raise_on_fail')
    result = validate_data_quality(connection=connection, **kwargs)
    result['table'] = source_table
    result['metrics']['replay_date'] = kwargs['expected_date'].isoformat()
    persist_data_quality_result(connection=connection, validation_result=result,
                                pipeline_name=pipeline_name)
    if result['status'] == 'FAIL':
        raise RuntimeError(f"Replay DQ failed for {source_table}: " + ' | '.join(result['errors']))


def replay_amibroker_days(*, start: date, end: date, factory, settings) -> None:
    if start > end:
        raise ValueError('Replay start must not be after end.')
    print('[REPLAY] DAT-only: SKIP Yahoo, FA, ticker metadata, APX indicators, '
          'aggregates without as-of support, metadata export and R2 publication.')
    day = start
    while day <= end:
        print(f'[REPLAY] START {day.isoformat()}')
        with DuckDBUnitOfWork(factory) as uow:
            con = uow.connection
            for folder, table in settings.amibroker_eod_targets:
                upsert_stock_eod(str(folder), table, connection=con, replay_date=day)
            # Calendar refresh is bounded to the replay day; no future calendar writes.
            con.execute('''UPDATE main.dimCalendar SET IsHoliday = CASE
                WHEN DayNameOfWeek IN ('Saturday','Sunday') THEN 'Y'
                WHEN EXISTS (SELECT 1 FROM main.raw_index_eod i
                    WHERE i.Date=dimCalendar.FullDate AND i.Ticker='VNINDEX') THEN 'N'
                ELSE 'Y' END WHERE FullDate=?''', [day])
            stock_columns = 'Ticker, Date, Open, High, Low, Close, Volume, OpenInt'
            con.execute(f'''CREATE TEMP VIEW _replay_stock_scope AS
                SELECT {stock_columns} FROM main.raw_stock_eod
                WHERE Date <= DATE '{day.isoformat()}' ''')
            try:
                _validate_scope(
                    source_table='raw_stock_eod',
                    connection=con, table_name='_replay_stock_scope',
                    pipeline_name='AmiBroker EOD replay', expected_date=day,
                    key_cols=['Ticker','Date'],
                    required_cols=['Ticker','Date','Open','High','Low','Close','Volume'],
                    small_count_anomaly_warn_pct=0.005, raise_on_fail=True,
                )
            finally:
                con.execute('DROP VIEW _replay_stock_scope')
            for folder, table in settings.amibroker_intraday_targets:
                upsert_amibroker_intraday(str(folder), table, connection=con, replay_date=day)
                columns = 'Ticker, Date, DateTime, RawTime, TickSeq, Open, High, Low, Close, Volume, OpenInt'
                # Identifier quoting/validation is already owned by the DAT upsert.
                con.execute(f'''CREATE TEMP VIEW _replay_intraday_scope AS
                    SELECT {columns} FROM "{table}" WHERE Date <= DATE '{day.isoformat()}' ''')
                try:
                    _validate_scope(
                        source_table=table,
                        connection=con, table_name='_replay_intraday_scope',
                        pipeline_name=f'AmiBroker Intraday replay {table}', expected_date=day,
                        key_cols=['Ticker','Date','RawTime','TickSeq'],
                        required_cols=['Ticker','Date','DateTime','RawTime','TickSeq','Close','Volume'],
                        max_row_change_pct=1.0, max_symbol_change_pct=0.25,
                        futures_expiry_symbol_warn=(table == 'raw_futures_intraday'),
                        raise_on_fail=True,
                    )
                finally:
                    con.execute('DROP VIEW _replay_intraday_scope')
        print(f'[REPLAY] COMMITTED {day.isoformat()}')
        day += timedelta(days=1)
