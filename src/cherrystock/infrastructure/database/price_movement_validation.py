from __future__ import annotations


def validate_price_movement_historical_contract(connection) -> dict[str, object]:
    """Validate persisted V1 invariants without mutating Price Movement data."""
    row = connection.execute(
        """
        WITH daily_stats AS (
            SELECT
                COUNT(*) AS DailyRows,
                COUNT(DISTINCT Ticker) AS DailyTickers,
                MIN(Date) AS DailyMinDate,
                MAX(Date) AS DailyMaxDate
            FROM "CherryMon"."main"."cal_price_movement_daily"
        ),
        swing_stats AS (
            SELECT
                COUNT(*) AS SwingRows,
                COUNT(DISTINCT Ticker) AS SwingTickers,
                MIN(PivotStartDate) AS SwingMinDate,
                MAX(ConfirmedAtDate) AS SwingMaxConfirmedAt
            FROM "CherryMon"."main"."cal_price_movement_swing"
        ),
        duplicate_daily AS (
            SELECT COUNT(*) AS DuplicateDailyKeys
            FROM (
                SELECT ConfigId, Ticker, Date, COUNT(*) AS RowCount
                FROM "CherryMon"."main"."cal_price_movement_daily"
                GROUP BY ConfigId, Ticker, Date
                HAVING COUNT(*) > 1
            ) AS d
        ),
        duplicate_swing AS (
            SELECT COUNT(*) AS DuplicateSwingKeys
            FROM (
                SELECT ConfigId, Ticker, PivotStartDate, Direction, COUNT(*) AS RowCount
                FROM "CherryMon"."main"."cal_price_movement_swing"
                GROUP BY ConfigId, Ticker, PivotStartDate, Direction
                HAVING COUNT(*) > 1
            ) AS s
        ),
        invalid_swing AS (
            SELECT COUNT(*) AS InvalidSwingRows
            FROM "CherryMon"."main"."cal_price_movement_swing"
            WHERE PivotStartDate > PivotEndDate
               OR PivotEndDate > ConfirmedAtDate
               OR DurationBars < 1
               OR EfficiencyRatio < 0 OR EfficiencyRatio > 1
               OR RegressionR2 < 0 OR RegressionR2 > 1
               OR DirectionalDayRatio < 0 OR DirectionalDayRatio > 1
               OR PersistenceScore < 0 OR PersistenceScore > 100
        ),
        invalid_daily AS (
            SELECT COUNT(*) AS InvalidDailyRows
            FROM "CherryMon"."main"."cal_price_movement_daily"
            WHERE HistoricalSameDirSwingCount < 0
               OR (MagnitudePercentile IS NOT NULL AND (MagnitudePercentile < 0 OR MagnitudePercentile > 100))
               OR (ATRNormMagnitudePercentile IS NOT NULL AND (ATRNormMagnitudePercentile < 0 OR ATRNormMagnitudePercentile > 100))
               OR (VelocityPercentile IS NOT NULL AND (VelocityPercentile < 0 OR VelocityPercentile > 100))
               OR (PersistencePercentile IS NOT NULL AND (PersistencePercentile < 0 OR PersistencePercentile > 100))
               OR (MagnitudeScore IS NOT NULL AND (MagnitudeScore < 0 OR MagnitudeScore > 100))
               OR (VelocityScore IS NOT NULL AND (VelocityScore < 0 OR VelocityScore > 100))
               OR (PersistenceScore IS NOT NULL AND (PersistenceScore < 0 OR PersistenceScore > 100))
        ),
        alternation AS (
            SELECT COUNT(*) AS SameDirectionRepeats
            FROM (
                SELECT
                    ConfigId,
                    Ticker,
                    SwingSeq,
                    Direction,
                    LAG(Direction) OVER (
                        PARTITION BY ConfigId, Ticker
                        ORDER BY SwingSeq, ConfirmedAtDate, PivotStartDate
                    ) AS PreviousDirection
                FROM "CherryMon"."main"."cal_price_movement_swing"
            ) AS ordered_swings
            WHERE PreviousDirection = Direction
        ),
        historical_counts AS (
            SELECT COUNT(*) AS HistoricalCountMismatch
            FROM (
                SELECT
                    d.ConfigId,
                    d.Ticker,
                    d.Date,
                    d.Direction,
                    d.HistoricalSameDirSwingCount AS StoredCount,
                    LEAST(
                        c.ProfileMaxSwings,
                        COUNT(s.PivotStartDate)
                    ) AS ExpectedCount
                FROM "CherryMon"."main"."cal_price_movement_daily" AS d
                INNER JOIN "CherryMon"."main"."dim_price_movement_config" AS c
                    ON c.ConfigId = d.ConfigId
                LEFT JOIN "CherryMon"."main"."cal_price_movement_swing" AS s
                    ON s.ConfigId = d.ConfigId
                   AND s.Ticker = d.Ticker
                   AND s.Direction = d.Direction
                   AND s.ConfirmedAtDate < d.Date
                WHERE d.Direction IN ('UP', 'DOWN')
                GROUP BY
                    d.ConfigId,
                    d.Ticker,
                    d.Date,
                    d.Direction,
                    d.HistoricalSameDirSwingCount,
                    c.ProfileMaxSwings
            ) AS counts
            WHERE StoredCount <> ExpectedCount
        ),
        profile_bounds AS (
            SELECT
                COUNT(*) AS ProfileBoundViolations,
                COALESCE(MAX(p.SwingCount - c.ProfileMaxSwings), 0) AS MaxProfileOverflow
            FROM "CherryMon"."main"."vw_Ticker_Movement_Profile" AS p
            INNER JOIN "CherryMon"."main"."dim_price_movement_config" AS c
                ON c.ConfigId = p.ConfigId
            WHERE p.SwingCount > c.ProfileMaxSwings
        ),
        public_stats AS (
            SELECT
                (SELECT COUNT(*) FROM "CherryMon"."main"."vw_Ticker_Movement_D") AS PublicDailyRows,
                (SELECT COUNT(*) FROM "CherryMon"."main"."vw_Ticker_Movement_Swings") AS PublicSwingRows,
                (SELECT COUNT(*) FROM "CherryMon"."main"."vw_Ticker_Movement_Profile") AS PublicProfileRows
        )
        SELECT
            d.DailyRows,
            d.DailyTickers,
            d.DailyMinDate,
            d.DailyMaxDate,
            s.SwingRows,
            s.SwingTickers,
            s.SwingMinDate,
            s.SwingMaxConfirmedAt,
            dd.DuplicateDailyKeys,
            ds.DuplicateSwingKeys,
            iw.InvalidSwingRows,
            id.InvalidDailyRows,
            a.SameDirectionRepeats,
            h.HistoricalCountMismatch,
            pb.ProfileBoundViolations,
            pb.MaxProfileOverflow,
            p.PublicDailyRows,
            p.PublicSwingRows,
            p.PublicProfileRows
        FROM daily_stats AS d
        CROSS JOIN swing_stats AS s
        CROSS JOIN duplicate_daily AS dd
        CROSS JOIN duplicate_swing AS ds
        CROSS JOIN invalid_swing AS iw
        CROSS JOIN invalid_daily AS id
        CROSS JOIN alternation AS a
        CROSS JOIN historical_counts AS h
        CROSS JOIN profile_bounds AS pb
        CROSS JOIN public_stats AS p
        """
    ).fetchone()

    if row is None:
        raise RuntimeError("Price Movement historical validation returned no result.")

    result = {
        "daily_rows": int(row[0] or 0),
        "daily_tickers": int(row[1] or 0),
        "daily_min_date": row[2],
        "daily_max_date": row[3],
        "swing_rows": int(row[4] or 0),
        "swing_tickers": int(row[5] or 0),
        "swing_min_date": row[6],
        "swing_max_confirmed_at": row[7],
        "duplicate_daily_keys": int(row[8] or 0),
        "duplicate_swing_keys": int(row[9] or 0),
        "invalid_swing_rows": int(row[10] or 0),
        "invalid_daily_rows": int(row[11] or 0),
        "same_direction_repeats": int(row[12] or 0),
        "historical_count_mismatch": int(row[13] or 0),
        "profile_bound_violations": int(row[14] or 0),
        "max_profile_overflow": int(row[15] or 0),
        "public_daily_rows": int(row[16] or 0),
        "public_swing_rows": int(row[17] or 0),
        "public_profile_rows": int(row[18] or 0),
    }

    failures: list[str] = []
    if result["daily_rows"] <= 0:
        failures.append("no persisted daily state rows")
    if result["swing_rows"] <= 0:
        failures.append("no confirmed swing rows")
    for key in (
        "duplicate_daily_keys",
        "duplicate_swing_keys",
        "invalid_swing_rows",
        "invalid_daily_rows",
        "same_direction_repeats",
        "historical_count_mismatch",
        "profile_bound_violations",
    ):
        if result[key] != 0:
            failures.append(f"{key}={result[key]}")
    if result["public_daily_rows"] != result["daily_rows"]:
        failures.append("public daily view row count differs from persisted daily rows")
    if result["public_swing_rows"] != result["swing_rows"]:
        failures.append("public swing view row count differs from persisted swing rows")
    if result["public_profile_rows"] <= 0:
        failures.append("public profile view contains no rows")

    if failures:
        raise RuntimeError(
            "Price Movement historical contract validation failed: "
            + "; ".join(failures)
            + f". Evidence: {result}"
        )

    return result
