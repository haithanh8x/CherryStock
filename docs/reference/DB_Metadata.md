# DuckDB Metadata

- Generated at: 2026-09-21T16:23:45.338051+00:00
- Database file: `C:\OneDrive\Working\Datafile\CherryMon.duckdb`
- Output file: `C:\Github\CherryStock\docs\reference\DB_Metadata.md`

## AI context loading guide

Use this generated reference set in the following order:

1. Read `DB_Metadata.md` for database objects, columns, types, nullability and defaults.
2. Read `dim_indicator.csv` for indicator master definitions and runtime/library mappings.
3. Read `dim_indicator_component.csv` for multi-output component contracts.
4. Read `dim_indicator_config.csv` for executable parameter/timeframe configurations.
5. Join the three snapshots by `IndicatorCode`; use `ConfigId` for calculated-value relationships and `ComponentCode` for component relationships.

The CSV files are data snapshots generated from the same DuckDB export run. Do not infer current configuration values from the Markdown schema alone.

- Schema count: 1
- Table/view count: 75

## Schemas

- `main`

## Tables

- `main`.`cal_Indexes` (BASE TABLE)
- `main`.`cal_Trends` (BASE TABLE)
- `main`.`cal_indicator_values` (BASE TABLE)
- `main`.`cal_price_movement_profile` (BASE TABLE)
- `main`.`cal_price_movement_swing` (BASE TABLE)
- `main`.`cal_rs_evaluation_event` (BASE TABLE)
- `main`.`cal_rs_evaluation_metric` (BASE TABLE)
- `main`.`cal_rs_evaluation_run` (BASE TABLE)
- `main`.`cal_rs_source_effectiveness` (BASE TABLE)
- `main`.`cal_rs_source_effectiveness_run` (BASE TABLE)
- `main`.`cal_smart_money_factor_values` (BASE TABLE)
- `main`.`cal_smart_money_ticker_score` (BASE TABLE)
- `main`.`cal_zigzag_current_leg` (BASE TABLE)
- `main`.`cal_zigzag_deviation_evaluation` (BASE TABLE)
- `main`.`cal_zigzag_pilot_evaluation` (BASE TABLE)
- `main`.`cal_zigzag_pivot` (BASE TABLE)
- `main`.`cal_zigzag_regime_evaluation` (BASE TABLE)
- `main`.`dimCalendar` (BASE TABLE)
- `main`.`dim_indicator` (BASE TABLE)
- `main`.`dim_indicator_component` (BASE TABLE)
- `main`.`dim_indicator_config` (BASE TABLE)
- `main`.`dim_movement_context_config` (BASE TABLE)
- `main`.`dim_price_movement_config` (BASE TABLE)
- `main`.`dim_rs_model_version` (BASE TABLE)
- `main`.`dim_smart_money_config` (BASE TABLE)
- `main`.`dim_smart_money_factor` (BASE TABLE)
- `main`.`dim_smart_money_model` (BASE TABLE)
- `main`.`dim_smart_money_state_weight` (BASE TABLE)
- `main`.`dim_zigzag_config` (BASE TABLE)
- `main`.`dim_zigzag_ticker_config` (BASE TABLE)
- `main`.`raw_active_eod` (BASE TABLE)
- `main`.`raw_bctc_cdkt` (BASE TABLE)
- `main`.`raw_bctc_cstc` (BASE TABLE)
- `main`.`raw_bctc_kqkd` (BASE TABLE)
- `main`.`raw_commodity_eod` (BASE TABLE)
- `main`.`raw_foreign_eod` (BASE TABLE)
- `main`.`raw_futures_eod` (BASE TABLE)
- `main`.`raw_futures_intraday` (BASE TABLE)
- `main`.`raw_index_eod` (BASE TABLE)
- `main`.`raw_index_intraday` (BASE TABLE)
- `main`.`raw_industry_eod` (BASE TABLE)
- `main`.`raw_lstTicker` (BASE TABLE)
- `main`.`raw_market_eod` (BASE TABLE)
- `main`.`raw_other_eod` (BASE TABLE)
- `main`.`raw_prop_eod` (BASE TABLE)
- `main`.`raw_stock_eod` (BASE TABLE)
- `main`.`raw_stock_fa` (BASE TABLE)
- `main`.`raw_stock_intraday` (BASE TABLE)
- `main`.`raw_supplydemand_eod` (BASE TABLE)
- `main`.`raw_tblBCTC` (BASE TABLE)
- `main`.`raw_warrant_eod` (BASE TABLE)
- `main`.`raw_warrant_intraday` (BASE TABLE)
- `main`.`sys_data_quality_audit` (BASE TABLE)
- `main`.`sys_rs_model_promotion_audit` (BASE TABLE)
- `main`.`sys_rs_source_promotion_audit` (BASE TABLE)
- `main`.`t` (BASE TABLE)
- `main`.`vw_ACCCNNTD` (VIEW)
- `main`.`vw_ACCCNNTD_Price` (VIEW)
- `main`.`vw_Indicator_config` (VIEW)
- `main`.`vw_RS_Source_Effectiveness` (VIEW)
- `main`.`vw_Ticker` (VIEW)
- `main`.`vw_Ticker_Movement_Context` (VIEW)
- `main`.`vw_Ticker_Movement_Profile` (VIEW)
- `main`.`vw_Ticker_OHLC_D` (VIEW)
- `main`.`vw_Ticker_Price_Movement_Swings` (VIEW)
- `main`.`vw_Ticker_SmartMoney` (VIEW)
- `main`.`vw_Ticker_ZigZag_Current` (VIEW)
- `main`.`vw_Ticker_ZigZag_Pivots` (VIEW)
- `main`.`vw_Ticker_ZigZag_Swings` (VIEW)
- `main`.`vw_Ticker_indicators` (VIEW)
- `main`.`vw_ZigZag_Calibration` (VIEW)
- `main`.`vw_ZigZag_Pilot` (VIEW)
- `main`.`vw_ZigZag_Regime_Evaluation` (VIEW)
- `main`.`vw_ZigZag_Ticker_Config` (VIEW)
- `main`.`vw_raw_stock_eod` (VIEW)

## Objects

### main.cal_Indexes (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `INDEX_NAME` | `VARCHAR` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Date` | `DATE` | `YES` | `` |

### main.cal_Trends (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `MA20` | `DOUBLE` | `YES` | `` |
| `MA50` | `DOUBLE` | `YES` | `` |
| `MA100` | `DOUBLE` | `YES` | `` |
| `MA200` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `MA20_W` | `DOUBLE` | `YES` | `` |
| `MA50_W` | `DOUBLE` | `YES` | `` |
| `MA20_M` | `DOUBLE` | `YES` | `` |
| `MA50_M` | `DOUBLE` | `YES` | `` |

### main.cal_indicator_values (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `ConfigId` | `BIGINT` | `NO` | `` |
| `ComponentCode` | `VARCHAR` | `NO` | `` |
| `Value` | `DOUBLE` | `YES` | `` |
| `CalculatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |

### main.cal_price_movement_profile (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `PriceMovementConfigId` | `BIGINT` | `NO` | `` |
| `ZigZagConfigId` | `BIGINT` | `NO` | `` |
| `ZigZagConfigCode` | `VARCHAR` | `NO` | `` |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `AsOfConfirmedAtDate` | `DATE` | `NO` | `` |
| `ProfileLookbackSwings` | `INTEGER` | `NO` | `` |
| `ConfirmedSwingCount` | `INTEGER` | `NO` | `` |
| `LastSwingSeq` | `BIGINT` | `NO` | `` |
| `LastSwingDirection` | `VARCHAR` | `NO` | `` |
| `LastSwingPct` | `DOUBLE` | `NO` | `` |
| `MedianUpSwingPct` | `DOUBLE` | `YES` | `` |
| `MedianDownSwingAbsPct` | `DOUBLE` | `YES` | `` |
| `MedianAbsSwingPct` | `DOUBLE` | `NO` | `` |
| `MedianTradingBars` | `DOUBLE` | `NO` | `` |
| `MedianAbsVelocityPctPerBar` | `DOUBLE` | `NO` | `` |
| `MedianATRNormalizedMove` | `DOUBLE` | `YES` | `` |
| `MedianPathEfficiency` | `DOUBLE` | `NO` | `` |
| `MedianDirectionalPersistenceRate` | `DOUBLE` | `NO` | `` |
| `DirectionalBias` | `DOUBLE` | `NO` | `` |
| `MovementCharacter` | `VARCHAR` | `NO` | `` |
| `CalculatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |

### main.cal_price_movement_swing (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `PriceMovementConfigId` | `BIGINT` | `NO` | `` |
| `ZigZagConfigId` | `BIGINT` | `NO` | `` |
| `ZigZagConfigCode` | `VARCHAR` | `NO` | `` |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `SwingSeq` | `BIGINT` | `NO` | `` |
| `Direction` | `VARCHAR` | `NO` | `` |
| `StartPivotSeq` | `BIGINT` | `NO` | `` |
| `StartDate` | `DATE` | `NO` | `` |
| `StartPrice` | `DOUBLE` | `NO` | `` |
| `EndPivotSeq` | `BIGINT` | `NO` | `` |
| `EndDate` | `DATE` | `NO` | `` |
| `EndPrice` | `DOUBLE` | `NO` | `` |
| `ConfirmedAtDate` | `DATE` | `NO` | `` |
| `SwingPct` | `DOUBLE` | `NO` | `` |
| `TradingBars` | `INTEGER` | `NO` | `` |
| `CalendarDays` | `INTEGER` | `NO` | `` |
| `VelocityPctPerBar` | `DOUBLE` | `NO` | `` |
| `AvgATRPct` | `DOUBLE` | `YES` | `` |
| `ATRNormalizedMove` | `DOUBLE` | `YES` | `` |
| `PathEfficiency` | `DOUBLE` | `NO` | `` |
| `DirectionalPersistenceRate` | `DOUBLE` | `NO` | `` |
| `CalculatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |

### main.cal_rs_evaluation_event (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `EvaluationRunId` | `VARCHAR` | `NO` | `` |
| `ModelVersion` | `VARCHAR` | `NO` | `` |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `AsOfDate` | `DATE` | `NO` | `` |
| `LevelRank` | `VARCHAR` | `NO` | `` |
| `LevelType` | `VARCHAR` | `NO` | `` |
| `LevelPrice` | `DOUBLE` | `NO` | `` |
| `StrengthScore` | `DOUBLE` | `YES` | `` |
| `HorizonEndDate` | `DATE` | `YES` | `` |
| `Touched` | `BOOLEAN` | `YES` | `` |
| `TouchDate` | `DATE` | `YES` | `` |
| `Broken` | `BOOLEAN` | `YES` | `` |
| `BreakDate` | `DATE` | `YES` | `` |
| `Retested` | `BOOLEAN` | `YES` | `` |
| `RetestDate` | `DATE` | `YES` | `` |
| `Held` | `BOOLEAN` | `YES` | `` |
| `BarsToTouch` | `INTEGER` | `YES` | `` |
| `MaxFavorablePct` | `DOUBLE` | `YES` | `` |
| `MaxAdversePct` | `DOUBLE` | `YES` | `` |
| `SourceCount` | `INTEGER` | `YES` | `` |
| `SourceFamilyCount` | `INTEGER` | `YES` | `` |
| `SourcesJson` | `VARCHAR` | `YES` | `` |
| `SourceFamiliesJson` | `VARCHAR` | `YES` | `` |
| `Regime` | `VARCHAR` | `YES` | `` |
| `Split` | `VARCHAR` | `YES` | `` |
| `CreatedAt` | `TIMESTAMP` | `YES` | `CURRENT_TIMESTAMP` |

### main.cal_rs_evaluation_metric (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `EvaluationRunId` | `VARCHAR` | `NO` | `` |
| `ScopeType` | `VARCHAR` | `NO` | `` |
| `ScopeKey` | `VARCHAR` | `NO` | `` |
| `MetricCode` | `VARCHAR` | `NO` | `` |
| `MetricValue` | `DOUBLE` | `YES` | `` |
| `SampleSize` | `INTEGER` | `YES` | `` |
| `CreatedAt` | `TIMESTAMP` | `YES` | `CURRENT_TIMESTAMP` |

### main.cal_rs_evaluation_run (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `EvaluationRunId` | `VARCHAR` | `NO` | `` |
| `ModelVersion` | `VARCHAR` | `NO` | `` |
| `DatasetStart` | `DATE` | `YES` | `` |
| `DatasetEnd` | `DATE` | `YES` | `` |
| `HorizonBars` | `INTEGER` | `NO` | `` |
| `TickerCount` | `INTEGER` | `YES` | `` |
| `SnapshotCount` | `INTEGER` | `YES` | `` |
| `SplitConfigJson` | `VARCHAR` | `YES` | `` |
| `Status` | `VARCHAR` | `NO` | `` |
| `CreatedAt` | `TIMESTAMP` | `YES` | `CURRENT_TIMESTAMP` |
| `CompletedAt` | `TIMESTAMP` | `YES` | `` |
| `Notes` | `VARCHAR` | `YES` | `` |
| `IncludeSourceKeysJson` | `VARCHAR` | `YES` | `` |
| `ExcludeSourceKeysJson` | `VARCHAR` | `YES` | `` |
| `ResearchIndicatorSpecsJson` | `VARCHAR` | `YES` | `` |

### main.cal_rs_source_effectiveness (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `EffectivenessRunId` | `VARCHAR` | `NO` | `` |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `ScopeType` | `VARCHAR` | `NO` | `` |
| `SourceKey` | `VARCHAR` | `NO` | `` |
| `SourceFamily` | `VARCHAR` | `NO` | `` |
| `SourceRole` | `VARCHAR` | `NO` | `` |
| `HorizonBars` | `INTEGER` | `NO` | `` |
| `AttributionMode` | `VARCHAR` | `NO` | `` |
| `MarginalMetric` | `VARCHAR` | `NO` | `` |
| `LineageEventCount` | `INTEGER` | `YES` | `` |
| `ValidationEventCount` | `INTEGER` | `YES` | `` |
| `TestEventCount` | `INTEGER` | `YES` | `` |
| `TouchRate` | `DOUBLE` | `YES` | `` |
| `HoldRateGivenTouch` | `DOUBLE` | `YES` | `` |
| `BreakRateGivenTouch` | `DOUBLE` | `YES` | `` |
| `RetestRateGivenBreak` | `DOUBLE` | `YES` | `` |
| `DirectionalEdgePct` | `DOUBLE` | `YES` | `` |
| `ValidationQuality` | `DOUBLE` | `YES` | `` |
| `TestQuality` | `DOUBLE` | `YES` | `` |
| `ValidationMarginalLift` | `DOUBLE` | `YES` | `` |
| `TestMarginalLift` | `DOUBLE` | `YES` | `` |
| `TemporalStability` | `DOUBLE` | `YES` | `` |
| `RegimeStability` | `DOUBLE` | `YES` | `` |
| `ComplexityDelta` | `DOUBLE` | `YES` | `` |
| `EffectivenessScore` | `DOUBLE` | `YES` | `` |
| `Recommendation` | `VARCHAR` | `NO` | `` |
| `EvidenceJson` | `VARCHAR` | `YES` | `` |
| `CreatedAt` | `TIMESTAMP` | `YES` | `CURRENT_TIMESTAMP` |

### main.cal_rs_source_effectiveness_run (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `EffectivenessRunId` | `VARCHAR` | `NO` | `` |
| `ScopeType` | `VARCHAR` | `NO` | `` |
| `SourceKey` | `VARCHAR` | `NO` | `` |
| `SourceFamily` | `VARCHAR` | `NO` | `` |
| `SourceRole` | `VARCHAR` | `NO` | `` |
| `HorizonBars` | `INTEGER` | `NO` | `` |
| `BaselineRunId` | `VARCHAR` | `NO` | `` |
| `AblationRunId` | `VARCHAR` | `NO` | `` |
| `StandaloneRunId` | `VARCHAR` | `YES` | `` |
| `PolicyJson` | `VARCHAR` | `NO` | `` |
| `Status` | `VARCHAR` | `NO` | `` |
| `CreatedAt` | `TIMESTAMP` | `YES` | `CURRENT_TIMESTAMP` |
| `CompletedAt` | `TIMESTAMP` | `YES` | `` |
| `Notes` | `VARCHAR` | `YES` | `` |

### main.cal_smart_money_factor_values (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `ModelId` | `BIGINT` | `NO` | `` |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `FactorId` | `BIGINT` | `NO` | `` |
| `RawValue` | `DOUBLE` | `YES` | `` |
| `NormalizedValue` | `DOUBLE` | `YES` | `` |
| `DataQuality` | `VARCHAR` | `NO` | `` |
| `SourceCode` | `VARCHAR` | `YES` | `` |
| `CalculatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |

### main.cal_smart_money_ticker_score (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `ModelId` | `BIGINT` | `NO` | `` |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `SmartMoneyScore` | `DOUBLE` | `NO` | `` |
| `ConfidenceScore` | `DOUBLE` | `NO` | `` |
| `MarketState` | `VARCHAR` | `NO` | `` |
| `FactorCoverage` | `DOUBLE` | `NO` | `` |
| `DataQualityStatus` | `VARCHAR` | `NO` | `` |
| `CalculatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |

### main.cal_zigzag_current_leg (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `ConfigId` | `BIGINT` | `NO` | `` |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `AsOfDate` | `DATE` | `NO` | `` |
| `Direction` | `VARCHAR` | `YES` | `` |
| `StartPivotSeq` | `BIGINT` | `YES` | `` |
| `StartPivotDate` | `DATE` | `YES` | `` |
| `StartPivotPrice` | `DOUBLE` | `YES` | `` |
| `CandidatePivotType` | `VARCHAR` | `YES` | `` |
| `CandidatePivotDate` | `DATE` | `YES` | `` |
| `CandidatePivotPrice` | `DOUBLE` | `YES` | `` |
| `LastClose` | `DOUBLE` | `NO` | `` |
| `CurrentMovePct` | `DOUBLE` | `YES` | `` |
| `ReversalFromCandidatePct` | `DOUBLE` | `YES` | `` |
| `Status` | `VARCHAR` | `NO` | `` |
| `CalculatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |

### main.cal_zigzag_deviation_evaluation (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `CalibrationVersion` | `VARCHAR` | `NO` | `` |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `SplitName` | `VARCHAR` | `NO` | `` |
| `DeviationPct` | `DOUBLE` | `NO` | `` |
| `SourceBars` | `BIGINT` | `NO` | `` |
| `PivotCount` | `BIGINT` | `NO` | `` |
| `SwingCount` | `BIGINT` | `NO` | `` |
| `PivotDensityPer100Bars` | `DOUBLE` | `NO` | `` |
| `MedianSwingBars` | `DOUBLE` | `NO` | `` |
| `MedianAbsSwingPct` | `DOUBLE` | `NO` | `` |
| `ShortSwingRate` | `DOUBLE` | `NO` | `` |
| `StructuralValid` | `BOOLEAN` | `NO` | `` |
| `IsEligible` | `BOOLEAN` | `NO` | `` |
| `CalibrationScore` | `DOUBLE` | `NO` | `` |
| `EvaluatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |

### main.cal_zigzag_pilot_evaluation (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `PilotVersion` | `VARCHAR` | `NO` | `` |
| `CalibrationVersion` | `VARCHAR` | `NO` | `` |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `BaselineDeviationPct` | `DOUBLE` | `NO` | `` |
| `CalibratedDeviationPct` | `DOUBLE` | `NO` | `` |
| `BaselineSwingCount` | `BIGINT` | `NO` | `` |
| `CalibratedSwingCount` | `BIGINT` | `NO` | `` |
| `BaselinePivotDensity` | `DOUBLE` | `NO` | `` |
| `CalibratedPivotDensity` | `DOUBLE` | `NO` | `` |
| `BaselineMedianSwingBars` | `DOUBLE` | `NO` | `` |
| `CalibratedMedianSwingBars` | `DOUBLE` | `NO` | `` |
| `BaselineMedianAbsSwingPct` | `DOUBLE` | `NO` | `` |
| `CalibratedMedianAbsSwingPct` | `DOUBLE` | `NO` | `` |
| `BaselineShortSwingRate` | `DOUBLE` | `NO` | `` |
| `CalibratedShortSwingRate` | `DOUBLE` | `NO` | `` |
| `BaselineStructuralValid` | `BOOLEAN` | `NO` | `` |
| `CalibratedStructuralValid` | `BOOLEAN` | `NO` | `` |
| `BaselineScore` | `DOUBLE` | `NO` | `` |
| `CalibratedScore` | `DOUBLE` | `NO` | `` |
| `Decision` | `VARCHAR` | `NO` | `` |
| `EvaluatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |

### main.cal_zigzag_pivot (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `ConfigId` | `BIGINT` | `NO` | `` |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `PivotSeq` | `BIGINT` | `NO` | `` |
| `PivotType` | `VARCHAR` | `NO` | `` |
| `PivotDate` | `DATE` | `NO` | `` |
| `PivotPrice` | `DOUBLE` | `NO` | `` |
| `ConfirmedAtDate` | `DATE` | `NO` | `` |
| `ConfirmationPrice` | `DOUBLE` | `NO` | `` |
| `DeviationPct` | `DOUBLE` | `NO` | `` |
| `CalculatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |

### main.cal_zigzag_regime_evaluation (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `RegimeVersion` | `VARCHAR` | `NO` | `` |
| `CalibrationVersion` | `VARCHAR` | `NO` | `` |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `BaseDeviationPct` | `DOUBLE` | `NO` | `` |
| `StaticSwingCount` | `BIGINT` | `NO` | `` |
| `RegimeSwingCount` | `BIGINT` | `NO` | `` |
| `StaticShortSwingRate` | `DOUBLE` | `NO` | `` |
| `RegimeShortSwingRate` | `DOUBLE` | `NO` | `` |
| `StaticMedianSwingBars` | `DOUBLE` | `NO` | `` |
| `RegimeMedianSwingBars` | `DOUBLE` | `NO` | `` |
| `StaticMedianAbsSwingPct` | `DOUBLE` | `NO` | `` |
| `RegimeMedianAbsSwingPct` | `DOUBLE` | `NO` | `` |
| `StaticStructuralValid` | `BOOLEAN` | `NO` | `` |
| `RegimeStructuralValid` | `BOOLEAN` | `NO` | `` |
| `StaticScore` | `DOUBLE` | `NO` | `` |
| `RegimeScore` | `DOUBLE` | `NO` | `` |
| `LowVolBars` | `BIGINT` | `NO` | `` |
| `NormalBars` | `BIGINT` | `NO` | `` |
| `HighVolBars` | `BIGINT` | `NO` | `` |
| `EvaluatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |

### main.dimCalendar (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `DateKey` | `BIGINT` | `YES` | `` |
| `FullDate` | `DATE` | `YES` | `` |
| `DayNumberOfWeek` | `BIGINT` | `YES` | `` |
| `DayNameOfWeek` | `VARCHAR` | `YES` | `` |
| `DayNumberOfMonth` | `BIGINT` | `YES` | `` |
| `DayNumberOfYear` | `BIGINT` | `YES` | `` |
| `WeekNumberOfYear` | `VARCHAR` | `YES` | `` |
| `EnglishMonthName` | `VARCHAR` | `YES` | `` |
| `MonthNumberOfYear` | `BIGINT` | `YES` | `` |
| `CalendarQuarter` | `BIGINT` | `YES` | `` |
| `QuarterName` | `VARCHAR` | `YES` | `` |
| `QuarterYear` | `VARCHAR` | `YES` | `` |
| `CalendarYear` | `BIGINT` | `YES` | `` |
| `IsHoliday` | `VARCHAR` | `YES` | `` |

### main.dim_indicator (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `IndicatorCode` | `VARCHAR` | `NO` | `` |
| `IndicatorName` | `VARCHAR` | `NO` | `` |
| `Category` | `VARCHAR` | `NO` | `` |
| `Engine` | `VARCHAR` | `NO` | `` |
| `FunctionName` | `VARCHAR` | `NO` | `` |
| `RequiredInputs` | `JSON` | `NO` | `` |
| `ParameterSchema` | `JSON` | `YES` | `` |
| `Description` | `VARCHAR` | `YES` | `` |
| `IsActive` | `BOOLEAN` | `NO` | `CAST('t' AS BOOLEAN)` |
| `CreatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |
| `UpdatedAt` | `TIMESTAMP` | `YES` | `` |

### main.dim_indicator_component (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `IndicatorCode` | `VARCHAR` | `NO` | `` |
| `ComponentCode` | `VARCHAR` | `NO` | `` |
| `ComponentName` | `VARCHAR` | `NO` | `` |
| `OutputPrefix` | `VARCHAR` | `YES` | `` |
| `SortOrder` | `INTEGER` | `YES` | `` |
| `IsPrimary` | `BOOLEAN` | `NO` | `CAST('f' AS BOOLEAN)` |
| `IsActive` | `BOOLEAN` | `NO` | `CAST('t' AS BOOLEAN)` |
| `ValueSemantic` | `VARCHAR` | `YES` | `` |
| `Unit` | `VARCHAR` | `YES` | `` |

### main.dim_indicator_config (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `ConfigId` | `BIGINT` | `NO` | `nextval('CherryMon.main.seq_indicator_config')` |
| `ConfigCode` | `VARCHAR` | `NO` | `` |
| `IndicatorCode` | `VARCHAR` | `NO` | `` |
| `Timeframe` | `VARCHAR` | `NO` | `` |
| `Parameters` | `JSON` | `NO` | `` |
| `WarmupBars` | `INTEGER` | `YES` | `` |
| `IsEnabled` | `BOOLEAN` | `NO` | `CAST('t' AS BOOLEAN)` |
| `Description` | `VARCHAR` | `YES` | `` |
| `CreatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |
| `UpdatedAt` | `TIMESTAMP` | `YES` | `` |

### main.dim_movement_context_config (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `MovementContextConfigId` | `BIGINT` | `NO` | `` |
| `ConfigCode` | `VARCHAR` | `NO` | `` |
| `ModelVersion` | `VARCHAR` | `NO` | `` |
| `Timeframe` | `VARCHAR` | `NO` | `` |
| `PriceMovementConfigCode` | `VARCHAR` | `NO` | `` |
| `ZigZagConfigCode` | `VARCHAR` | `NO` | `` |
| `LastSwingShallowMaxRatio` | `DOUBLE` | `NO` | `` |
| `LastSwingBelowTypicalMaxRatio` | `DOUBLE` | `NO` | `` |
| `LastSwingTypicalMaxRatio` | `DOUBLE` | `NO` | `` |
| `LastSwingExtendedMaxRatio` | `DOUBLE` | `NO` | `` |
| `TrendQualityModerateEfficiency` | `DOUBLE` | `NO` | `` |
| `TrendQualityModeratePersistence` | `DOUBLE` | `NO` | `` |
| `TrendQualityModerateHighEfficiency` | `DOUBLE` | `NO` | `` |
| `TrendQualityModerateHighPersistence` | `DOUBLE` | `NO` | `` |
| `TrendQualityHighEfficiency` | `DOUBLE` | `NO` | `` |
| `TrendQualityHighPersistence` | `DOUBLE` | `NO` | `` |
| `SpeedVerySlowMaxRatio` | `DOUBLE` | `NO` | `` |
| `SpeedSlowMaxRatio` | `DOUBLE` | `NO` | `` |
| `SpeedNormalMaxRatio` | `DOUBLE` | `NO` | `` |
| `SpeedFastMaxRatio` | `DOUBLE` | `NO` | `` |
| `EffectiveFrom` | `DATE` | `NO` | `CAST('2000-01-01' AS DATE)` |
| `EffectiveTo` | `DATE` | `YES` | `` |
| `IsEnabled` | `BOOLEAN` | `NO` | `CAST('t' AS BOOLEAN)` |
| `CreatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |
| `UpdatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |

### main.dim_price_movement_config (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `ConfigId` | `BIGINT` | `NO` | `` |
| `ConfigCode` | `VARCHAR` | `NO` | `` |
| `ModelVersion` | `VARCHAR` | `NO` | `` |
| `Timeframe` | `VARCHAR` | `NO` | `` |
| `ZigZagConfigCode` | `VARCHAR` | `NO` | `` |
| `ProfileLookbackSwings` | `INTEGER` | `NO` | `` |
| `MinimumProfileSwings` | `INTEGER` | `NO` | `` |
| `TrendBiasThreshold` | `DOUBLE` | `NO` | `` |
| `RangeBiasThreshold` | `DOUBLE` | `NO` | `` |
| `EfficiencyThreshold` | `DOUBLE` | `NO` | `` |
| `ATRPeriod` | `INTEGER` | `NO` | `` |
| `EffectiveFrom` | `DATE` | `NO` | `CAST('2000-01-01' AS DATE)` |
| `EffectiveTo` | `DATE` | `YES` | `` |
| `IsEnabled` | `BOOLEAN` | `NO` | `CAST('t' AS BOOLEAN)` |
| `CreatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |
| `UpdatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |

### main.dim_rs_model_version (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `ModelVersion` | `VARCHAR` | `NO` | `` |
| `ParentVersion` | `VARCHAR` | `YES` | `` |
| `Status` | `VARCHAR` | `NO` | `` |
| `Signature` | `VARCHAR` | `NO` | `` |
| `ConfigJson` | `VARCHAR` | `NO` | `` |
| `ComplexityScore` | `DOUBLE` | `YES` | `` |
| `CreatedAt` | `TIMESTAMP` | `YES` | `CURRENT_TIMESTAMP` |
| `PromotedAt` | `TIMESTAMP` | `YES` | `` |
| `Notes` | `VARCHAR` | `YES` | `` |

### main.dim_smart_money_config (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `ModelId` | `BIGINT` | `NO` | `` |
| `ConfigKey` | `VARCHAR` | `NO` | `` |
| `ConfigValue` | `VARCHAR` | `NO` | `` |
| `ValueType` | `VARCHAR` | `NO` | `` |
| `EffectiveFrom` | `DATE` | `NO` | `CAST('2000-01-01' AS DATE)` |
| `EffectiveTo` | `DATE` | `YES` | `` |
| `UpdatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |

### main.dim_smart_money_factor (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `FactorId` | `BIGINT` | `NO` | `` |
| `FactorCode` | `VARCHAR` | `NO` | `` |
| `FactorName` | `VARCHAR` | `NO` | `` |
| `Category` | `VARCHAR` | `NO` | `` |
| `NormalizationMethod` | `VARCHAR` | `NO` | `` |
| `ContributionType` | `VARCHAR` | `NO` | `` |
| `IsEnabled` | `BOOLEAN` | `NO` | `CAST('t' AS BOOLEAN)` |
| `Description` | `VARCHAR` | `YES` | `` |

### main.dim_smart_money_model (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `ModelId` | `BIGINT` | `NO` | `` |
| `ModelCode` | `VARCHAR` | `NO` | `` |
| `ModelVersion` | `VARCHAR` | `NO` | `` |
| `Description` | `VARCHAR` | `YES` | `` |
| `IsEnabled` | `BOOLEAN` | `NO` | `CAST('t' AS BOOLEAN)` |
| `EffectiveFrom` | `DATE` | `NO` | `CAST('2000-01-01' AS DATE)` |
| `EffectiveTo` | `DATE` | `YES` | `` |
| `CreatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |
| `UpdatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |

### main.dim_smart_money_state_weight (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `ModelId` | `BIGINT` | `NO` | `` |
| `MarketState` | `VARCHAR` | `NO` | `` |
| `FactorId` | `BIGINT` | `NO` | `` |
| `Weight` | `DOUBLE` | `NO` | `` |
| `EffectiveFrom` | `DATE` | `NO` | `CAST('2000-01-01' AS DATE)` |
| `EffectiveTo` | `DATE` | `YES` | `` |
| `UpdatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |

### main.dim_zigzag_config (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `ConfigId` | `BIGINT` | `NO` | `` |
| `ConfigCode` | `VARCHAR` | `NO` | `` |
| `ModelVersion` | `VARCHAR` | `NO` | `` |
| `Timeframe` | `VARCHAR` | `NO` | `` |
| `DeviationPct` | `DOUBLE` | `NO` | `` |
| `PivotPriceSource` | `VARCHAR` | `NO` | `` |
| `ConfirmationPriceSource` | `VARCHAR` | `NO` | `` |
| `MinimumSwingBars` | `INTEGER` | `NO` | `` |
| `EffectiveFrom` | `DATE` | `NO` | `CAST('2000-01-01' AS DATE)` |
| `EffectiveTo` | `DATE` | `YES` | `` |
| `IsEnabled` | `BOOLEAN` | `NO` | `CAST('t' AS BOOLEAN)` |
| `CreatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |
| `UpdatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |

### main.dim_zigzag_ticker_config (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `CalibrationVersion` | `VARCHAR` | `NO` | `` |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Timeframe` | `VARCHAR` | `NO` | `` |
| `BaseDeviationPct` | `DOUBLE` | `NO` | `` |
| `SelectionMethod` | `VARCHAR` | `NO` | `` |
| `TrainScore` | `DOUBLE` | `NO` | `` |
| `ValidationScore` | `DOUBLE` | `NO` | `` |
| `TestScore` | `DOUBLE` | `NO` | `` |
| `Status` | `VARCHAR` | `NO` | `'RECOMMENDED'` |
| `IsActive` | `BOOLEAN` | `NO` | `CAST('f' AS BOOLEAN)` |
| `EffectiveFrom` | `DATE` | `YES` | `` |
| `EffectiveTo` | `DATE` | `YES` | `` |
| `UpdatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |

### main.raw_active_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_bctc_cdkt (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `index` | `VARCHAR` | `YES` | `` |
| `column01` | `VARCHAR` | `YES` | `` |
| `Bất động sản đầu tư` | `BIGINT` | `YES` | `` |
| `Các khoản phải thu ngắn hạn` | `BIGINT` | `YES` | `` |
| `Các khoản đầu tư tài chính dài hạn` | `BIGINT` | `YES` | `` |
| `Các khoản đầu tư tài chính ngắn hạn` | `BIGINT` | `YES` | `` |
| `Công ty kiểm toán` | `VARCHAR` | `YES` | `` |
| `Giai đoạn` | `VARCHAR` | `YES` | `` |
| `Hàng tồn kho` | `BIGINT` | `YES` | `` |
| `Hợp nhất` | `VARCHAR` | `YES` | `` |
| `Kiểm toán` | `VARCHAR` | `YES` | `` |
| `Lợi nhuận sau thuế chưa phân phối` | `BIGINT` | `YES` | `` |
| `Lợi ích của cổ đông thiểu số` | `BIGINT` | `YES` | `` |
| `Nợ dài hạn` | `BIGINT` | `YES` | `` |
| `Nợ ngắn hạn` | `BIGINT` | `YES` | `` |
| `Nợ phải trả` | `BIGINT` | `YES` | `` |
| `Thặng dư vốn cổ phần` | `BIGINT` | `YES` | `` |
| `Tiền và các khoản tương đương tiền` | `BIGINT` | `YES` | `` |
| `Tài sản cố định` | `BIGINT` | `YES` | `` |
| `Tài sản dài hạn` | `BIGINT` | `YES` | `` |
| `Tài sản ngắn hạn` | `BIGINT` | `YES` | `` |
| `Tài sản ngắn hạn khác` | `BIGINT` | `YES` | `` |
| `Tổng cộng nguồn vốn` | `BIGINT` | `YES` | `` |
| `Tổng cộng tài sản` | `BIGINT` | `YES` | `` |
| `Vốn chủ sở hữu` | `BIGINT` | `YES` | `` |
| `Vốn đầu tư của chủ sở hữu` | `BIGINT` | `YES` | `` |
| `Ý kiến kiểm toán` | `VARCHAR` | `YES` | `` |
| `Ticker` | `VARCHAR` | `YES` | `` |

### main.raw_bctc_cstc (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `index` | `VARCHAR` | `YES` | `` |
| `column01` | `VARCHAR` | `YES` | `` |
| `Chỉ số giá thị trường trên giá trị sổ sách (P/B)` | `VARCHAR` | `YES` | `` |
| `Chỉ số giá thị trường trên thu nhập (P/E)` | `VARCHAR` | `YES` | `` |
| `Công ty kiểm toán` | `VARCHAR` | `YES` | `` |
| `Giai đoạn` | `VARCHAR` | `YES` | `` |
| `Giá trị sổ sách của cổ phiếu (BVPS)` | `VARCHAR` | `YES` | `` |
| `Hợp nhất` | `VARCHAR` | `YES` | `` |
| `Khả năng thanh toán lãi vay` | `VARCHAR` | `YES` | `` |
| `Kiểm toán` | `VARCHAR` | `YES` | `` |
| `Thu nhập trên mỗi cổ phần của 4 quý gần nhất (EPS)` | `VARCHAR` | `YES` | `` |
| `Tỷ suất lợi nhuận gộp biên` | `VARCHAR` | `YES` | `` |
| `Tỷ suất lợi nhuận trên vốn chủ sở hữu bình quân (ROEA)` | `VARCHAR` | `YES` | `` |
| `Tỷ suất sinh lợi trên doanh thu thuần` | `VARCHAR` | `YES` | `` |
| `Tỷ suất sinh lợi trên tổng tài sản bình quân (ROAA)` | `VARCHAR` | `YES` | `` |
| `Tỷ số Nợ trên Tổng tài sản` | `VARCHAR` | `YES` | `` |
| `Tỷ số Nợ vay trên Vốn chủ sở hữu` | `VARCHAR` | `YES` | `` |
| `Tỷ số thanh toán hiện hành (ngắn hạn)` | `VARCHAR` | `YES` | `` |
| `Ý kiến kiểm toán` | `VARCHAR` | `YES` | `` |
| `Ticker` | `VARCHAR` | `YES` | `` |

### main.raw_bctc_kqkd (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `index` | `VARCHAR` | `YES` | `` |
| `column01` | `VARCHAR` | `YES` | `` |
| `Chi phí bán hàng` | `BIGINT` | `YES` | `` |
| `Chi phí quản lý doanh nghiệp` | `BIGINT` | `YES` | `` |
| `Chi phí tài chính` | `BIGINT` | `YES` | `` |
| `Công ty kiểm toán` | `VARCHAR` | `YES` | `` |
| `Doanh thu hoạt động tài chính` | `BIGINT` | `YES` | `` |
| `Doanh thu thuần về bán hàng và cung cấp dịch vụ` | `BIGINT` | `YES` | `` |
| `Giai đoạn` | `VARCHAR` | `YES` | `` |
| `Giá vốn hàng bán` | `BIGINT` | `YES` | `` |
| `Hợp nhất` | `VARCHAR` | `YES` | `` |
| `Kiểm toán` | `VARCHAR` | `YES` | `` |
| `Lãi cơ bản trên cổ phiếu (VNÐ)` | `BIGINT` | `YES` | `` |
| `Lợi nhuận gộp về bán hàng và cung cấp dịch vụ` | `BIGINT` | `YES` | `` |
| `Lợi nhuận khác` | `BIGINT` | `YES` | `` |
| `Lợi nhuận sau thuế của cổ đông Công ty mẹ` | `BIGINT` | `YES` | `` |
| `Lợi nhuận sau thuế thu nhập doanh nghiệp` | `BIGINT` | `YES` | `` |
| `Lợi nhuận thuần từ hoạt động kinh doanh` | `BIGINT` | `YES` | `` |
| `Phần lợi nhuận/lỗ từ công ty liên kết liên doanh` | `BIGINT` | `YES` | `` |
| `Tổng lợi nhuận kế toán trước thuế` | `BIGINT` | `YES` | `` |
| `Ý kiến kiểm toán` | `VARCHAR` | `YES` | `` |
| `Ticker` | `VARCHAR` | `YES` | `` |

### main.raw_commodity_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_foreign_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_futures_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_futures_intraday (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `DateTime` | `TIMESTAMP` | `NO` | `` |
| `RawTime` | `INTEGER` | `NO` | `` |
| `TickSeq` | `BIGINT` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_index_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_index_intraday (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `DateTime` | `TIMESTAMP` | `NO` | `` |
| `RawTime` | `INTEGER` | `NO` | `` |
| `TickSeq` | `BIGINT` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_industry_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_lstTicker (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Stock` | `VARCHAR` | `YES` | `` |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Company Name` | `VARCHAR` | `YES` | `` |
| `Industry` | `VARCHAR` | `YES` | `` |
| `IndustryCode` | `VARCHAR` | `YES` | `` |
| `Expected Price` | `DOUBLE` | `YES` | `` |
| `Watchlist` | `VARCHAR` | `YES` | `` |
| `EcoSystem` | `DOUBLE` | `YES` | `` |
| `Sở hữu Nhà Nước` | `DOUBLE` | `YES` | `` |
| `Owner Type` | `VARCHAR` | `YES` | `` |
| `Margin` | `VARCHAR` | `YES` | `` |
| `Status` | `VARCHAR` | `YES` | `` |
| `Notes` | `DOUBLE` | `YES` | `` |

### main.raw_market_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_other_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_prop_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_stock_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_stock_fa (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `YES` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Full Name` | `VARCHAR` | `YES` | `` |
| `Market` | `VARCHAR` | `YES` | `` |
| `Capital` | `BIGINT` | `YES` | `` |
| `Sector` | `VARCHAR` | `YES` | `` |
| `ICB ID` | `BIGINT` | `YES` | `` |
| `ICB` | `VARCHAR` | `YES` | `` |
| `Industry` | `VARCHAR` | `YES` | `` |
| `Shares Float` | `BIGINT` | `YES` | `` |
| `Shares Outstanding` | `BIGINT` | `YES` | `` |
| `EPS` | `DOUBLE` | `YES` | `` |
| `PE` | `DOUBLE` | `YES` | `` |
| `Book Value` | `DOUBLE` | `YES` | `` |
| `ROA` | `DOUBLE` | `YES` | `` |
| `ROE` | `DOUBLE` | `YES` | `` |

### main.raw_stock_intraday (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `DateTime` | `TIMESTAMP` | `NO` | `` |
| `RawTime` | `INTEGER` | `NO` | `` |
| `TickSeq` | `BIGINT` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_supplydemand_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_tblBCTC (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `DT` | `DATE` | `YES` | `` |
| `Quarter` | `VARCHAR` | `YES` | `` |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `Chi phí bán hàng` | `BIGINT` | `YES` | `` |
| `Chi phí quản lý doanh nghiệp` | `BIGINT` | `YES` | `` |
| `Chi phí tài chính` | `BIGINT` | `YES` | `` |
| `Công ty kiểm toán` | `VARCHAR` | `YES` | `` |
| `Doanh thu hoạt động tài chính` | `BIGINT` | `YES` | `` |
| `Doanh thu thuần về bán hàng và cung cấp dịch vụ` | `BIGINT` | `YES` | `` |
| `Giai đoạn (kqkd)` | `VARCHAR` | `YES` | `` |
| `Giá vốn hàng bán` | `BIGINT` | `YES` | `` |
| `Hợp nhất (kqkd)` | `VARCHAR` | `YES` | `` |
| `Kiểm toán (kqkd)` | `VARCHAR` | `YES` | `` |
| `Lãi cơ bản trên cổ phiếu (VNÐ)` | `BIGINT` | `YES` | `` |
| `Lợi nhuận gộp về bán hàng và cung cấp dịch vụ` | `BIGINT` | `YES` | `` |
| `Lợi nhuận khác` | `BIGINT` | `YES` | `` |
| `Lợi nhuận sau thuế của cổ đông Công ty mẹ` | `BIGINT` | `YES` | `` |
| `Lợi nhuận sau thuế thu nhập doanh nghiệp` | `BIGINT` | `YES` | `` |
| `Lợi nhuận thuần từ hoạt động kinh doanh` | `BIGINT` | `YES` | `` |
| `Phần lợi nhuận/lỗ từ công ty liên kết liên doanh` | `BIGINT` | `YES` | `` |
| `Tổng lợi nhuận kế toán trước thuế` | `BIGINT` | `YES` | `` |
| `Ý kiến kiểm toán (kqkd)` | `VARCHAR` | `YES` | `` |
| `Bất động sản đầu tư` | `BIGINT` | `YES` | `` |
| `Các khoản phải thu ngắn hạn` | `BIGINT` | `YES` | `` |
| `Các khoản đầu tư tài chính dài hạn` | `BIGINT` | `YES` | `` |
| `Các khoản đầu tư tài chính ngắn hạn` | `BIGINT` | `YES` | `` |
| `Công ty kiểm toán (cdkt)` | `VARCHAR` | `YES` | `` |
| `Giai đoạn (cdkt)` | `VARCHAR` | `YES` | `` |
| `Hàng tồn kho` | `BIGINT` | `YES` | `` |
| `Hợp nhất (cdkt)` | `VARCHAR` | `YES` | `` |
| `Kiểm toán (cdkt)` | `VARCHAR` | `YES` | `` |
| `Lợi nhuận sau thuế chưa phân phối` | `BIGINT` | `YES` | `` |
| `Lợi ích của cổ đông thiểu số` | `BIGINT` | `YES` | `` |
| `Nợ dài hạn` | `BIGINT` | `YES` | `` |
| `Nợ ngắn hạn` | `BIGINT` | `YES` | `` |
| `Nợ phải trả` | `BIGINT` | `YES` | `` |
| `Thặng dư vốn cổ phần` | `BIGINT` | `YES` | `` |
| `Tiền và các khoản tương đương tiền` | `BIGINT` | `YES` | `` |
| `Tài sản cố định` | `BIGINT` | `YES` | `` |
| `Tài sản dài hạn` | `BIGINT` | `YES` | `` |
| `Tài sản ngắn hạn` | `BIGINT` | `YES` | `` |
| `Tài sản ngắn hạn khác` | `BIGINT` | `YES` | `` |
| `Tổng cộng nguồn vốn` | `BIGINT` | `YES` | `` |
| `Tổng cộng tài sản` | `BIGINT` | `YES` | `` |
| `Vốn chủ sở hữu` | `BIGINT` | `YES` | `` |
| `Vốn đầu tư của chủ sở hữu` | `BIGINT` | `YES` | `` |
| `Ý kiến kiểm toán (cdkt)` | `VARCHAR` | `YES` | `` |
| `Chỉ số giá thị trường trên giá trị sổ sách (P/B)` | `VARCHAR` | `YES` | `` |
| `Chỉ số giá thị trường trên thu nhập (P/E)` | `VARCHAR` | `YES` | `` |
| `Công ty kiểm toán (cstc)` | `VARCHAR` | `YES` | `` |
| `Giai đoạn (cstc)` | `VARCHAR` | `YES` | `` |
| `Giá trị sổ sách của cổ phiếu (BVPS)` | `VARCHAR` | `YES` | `` |
| `Hợp nhất (cstc)` | `VARCHAR` | `YES` | `` |
| `Khả năng thanh toán lãi vay (TIE)` | `VARCHAR` | `YES` | `` |
| `Kiểm toán (cstc)` | `VARCHAR` | `YES` | `` |
| `Thu nhập trên mỗi cổ phần của 4 quý gần nhất (EPS)` | `VARCHAR` | `YES` | `` |
| `Tỷ suất lợi nhuận gộp biên (GPM)` | `VARCHAR` | `YES` | `` |
| `Tỷ suất lợi nhuận trên vốn chủ sở hữu bình quân (ROEA)` | `VARCHAR` | `YES` | `` |
| `Tỷ suất sinh lợi trên doanh thu thuần (ROS)` | `VARCHAR` | `YES` | `` |
| `Tỷ suất sinh lợi trên tổng tài sản bình quân (ROAA)` | `VARCHAR` | `YES` | `` |
| `Tỷ số Nợ trên Tổng tài sản (DAR)` | `VARCHAR` | `YES` | `` |
| `Tỷ số Nợ vay trên Vốn chủ sở hữu (D/E)` | `VARCHAR` | `YES` | `` |
| `Tỷ số thanh toán hiện hành (Current Ratio)` | `VARCHAR` | `YES` | `` |
| `Ý kiến kiểm toán (cstc)` | `VARCHAR` | `YES` | `` |

### main.raw_warrant_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_warrant_intraday (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `DateTime` | `TIMESTAMP` | `NO` | `` |
| `RawTime` | `INTEGER` | `NO` | `` |
| `TickSeq` | `BIGINT` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.sys_data_quality_audit (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `validation_id` | `VARCHAR` | `YES` | `` |
| `checked_at` | `TIMESTAMP` | `YES` | `` |
| `pipeline_name` | `VARCHAR` | `YES` | `` |
| `table_name` | `VARCHAR` | `YES` | `` |
| `expected_date` | `DATE` | `YES` | `` |
| `max_date` | `DATE` | `YES` | `` |
| `status` | `VARCHAR` | `YES` | `` |
| `row_count_current` | `BIGINT` | `YES` | `` |
| `row_count_previous` | `BIGINT` | `YES` | `` |
| `row_count_change_pct` | `DOUBLE` | `YES` | `` |
| `symbol_count_current` | `BIGINT` | `YES` | `` |
| `symbol_count_previous` | `BIGINT` | `YES` | `` |
| `symbol_count_change_pct` | `DOUBLE` | `YES` | `` |
| `missing_symbol_count` | `BIGINT` | `YES` | `` |
| `new_symbol_count` | `BIGINT` | `YES` | `` |
| `duplicate_count` | `BIGINT` | `YES` | `` |
| `row_count_zscore` | `DOUBLE` | `YES` | `` |
| `symbol_count_zscore` | `DOUBLE` | `YES` | `` |
| `metrics` | `JSON` | `YES` | `` |
| `errors` | `JSON` | `YES` | `` |
| `warnings` | `JSON` | `YES` | `` |

### main.sys_rs_model_promotion_audit (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `DecisionId` | `VARCHAR` | `NO` | `` |
| `BaselineVersion` | `VARCHAR` | `NO` | `` |
| `ChallengerVersion` | `VARCHAR` | `NO` | `` |
| `EvaluationRunId` | `VARCHAR` | `YES` | `` |
| `Promote` | `BOOLEAN` | `NO` | `` |
| `ValidationQualityDelta` | `DOUBLE` | `YES` | `` |
| `TestQualityDelta` | `DOUBLE` | `YES` | `` |
| `ComplexityDelta` | `DOUBLE` | `YES` | `` |
| `WorstRegimeDelta` | `DOUBLE` | `YES` | `` |
| `ReasonsJson` | `VARCHAR` | `YES` | `` |
| `PolicyJson` | `VARCHAR` | `YES` | `` |
| `DecidedAt` | `TIMESTAMP` | `YES` | `CURRENT_TIMESTAMP` |
| `Notes` | `VARCHAR` | `YES` | `` |

### main.sys_rs_source_promotion_audit (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `DecisionId` | `VARCHAR` | `NO` | `` |
| `EffectivenessRunId` | `VARCHAR` | `NO` | `` |
| `SourceKey` | `VARCHAR` | `NO` | `` |
| `SourceFamily` | `VARCHAR` | `NO` | `` |
| `SourceRole` | `VARCHAR` | `NO` | `` |
| `HorizonBars` | `INTEGER` | `NO` | `` |
| `Outcome` | `VARCHAR` | `NO` | `` |
| `TickerCount` | `INTEGER` | `YES` | `` |
| `PositiveTickerCount` | `INTEGER` | `YES` | `` |
| `PositiveTickerRatio` | `DOUBLE` | `YES` | `` |
| `AvgEffectivenessScore` | `DOUBLE` | `YES` | `` |
| `AvgValidationLift` | `DOUBLE` | `YES` | `` |
| `AvgTestLift` | `DOUBLE` | `YES` | `` |
| `AvgTemporalStability` | `DOUBLE` | `YES` | `` |
| `AvgRegimeStability` | `DOUBLE` | `YES` | `` |
| `MaxComplexityDelta` | `DOUBLE` | `YES` | `` |
| `ReasonsJson` | `VARCHAR` | `YES` | `` |
| `PolicyJson` | `VARCHAR` | `NO` | `` |
| `Applied` | `BOOLEAN` | `NO` | `CAST('f' AS BOOLEAN)` |
| `DecidedAt` | `TIMESTAMP` | `YES` | `CURRENT_TIMESTAMP` |
| `Notes` | `VARCHAR` | `YES` | `` |

### main.t (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `NO` | `` |
| `value` | `VARCHAR` | `YES` | `` |

### main.vw_ACCCNNTD (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `Date` | `DATE` | `YES` | `` |
| `NetVol` | `DOUBLE` | `YES` | `` |
| `NetVal` | `DOUBLE` | `YES` | `` |
| `BuyVol` | `DOUBLE` | `YES` | `` |
| `BuyVal` | `DOUBLE` | `YES` | `` |
| `SellVol` | `DOUBLE` | `YES` | `` |
| `SellVal` | `BIGINT` | `YES` | `` |
| `DataSource` | `VARCHAR` | `YES` | `` |

### main.vw_ACCCNNTD_Price (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `Date` | `DATE` | `YES` | `` |
| `AvgPrice` | `DOUBLE` | `YES` | `` |
| `AC_NetVol` | `DOUBLE` | `YES` | `` |
| `NN_NetVol` | `DOUBLE` | `YES` | `` |
| `TD_NetVol` | `DOUBLE` | `YES` | `` |
| `CC_NetVol` | `DOUBLE` | `YES` | `` |
| `AC_NetVal` | `DOUBLE` | `YES` | `` |
| `NN_NetVal` | `DOUBLE` | `YES` | `` |
| `TD_NetVal` | `DOUBLE` | `YES` | `` |
| `CC_NetVal` | `DOUBLE` | `YES` | `` |

### main.vw_Indicator_config (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `ConfigId` | `BIGINT` | `YES` | `` |
| `ConfigCode` | `VARCHAR` | `YES` | `` |
| `IndicatorCode` | `VARCHAR` | `YES` | `` |
| `Timeframe` | `VARCHAR` | `YES` | `` |
| `Parameters` | `JSON` | `YES` | `` |
| `WarmupBars` | `INTEGER` | `YES` | `` |
| `ConfigIsEnabled` | `BOOLEAN` | `YES` | `` |
| `ConfigDescription` | `VARCHAR` | `YES` | `` |
| `ConfigCreatedAt` | `TIMESTAMP` | `YES` | `` |
| `ConfigUpdatedAt` | `TIMESTAMP` | `YES` | `` |
| `IndicatorName` | `VARCHAR` | `YES` | `` |
| `Category` | `VARCHAR` | `YES` | `` |
| `Engine` | `VARCHAR` | `YES` | `` |
| `FunctionName` | `VARCHAR` | `YES` | `` |
| `RequiredInputs` | `JSON` | `YES` | `` |
| `ParameterSchema` | `JSON` | `YES` | `` |
| `IndicatorDescription` | `VARCHAR` | `YES` | `` |
| `IndicatorIsActive` | `BOOLEAN` | `YES` | `` |
| `IndicatorCreatedAt` | `TIMESTAMP` | `YES` | `` |
| `IndicatorUpdatedAt` | `TIMESTAMP` | `YES` | `` |
| `ComponentCode` | `VARCHAR` | `YES` | `` |
| `ComponentName` | `VARCHAR` | `YES` | `` |
| `OutputPrefix` | `VARCHAR` | `YES` | `` |
| `SortOrder` | `INTEGER` | `YES` | `` |
| `ValueSemantic` | `VARCHAR` | `YES` | `` |
| `Unit` | `VARCHAR` | `YES` | `` |
| `IsPrimary` | `BOOLEAN` | `YES` | `` |
| `ComponentIsActive` | `BOOLEAN` | `YES` | `` |

### main.vw_RS_Source_Effectiveness (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `ScopeType` | `VARCHAR` | `YES` | `` |
| `SourceKey` | `VARCHAR` | `YES` | `` |
| `SourceFamily` | `VARCHAR` | `YES` | `` |
| `SourceRole` | `VARCHAR` | `YES` | `` |
| `HorizonBars` | `INTEGER` | `YES` | `` |
| `AttributionMode` | `VARCHAR` | `YES` | `` |
| `MarginalMetric` | `VARCHAR` | `YES` | `` |
| `LineageEventCount` | `INTEGER` | `YES` | `` |
| `ValidationEventCount` | `INTEGER` | `YES` | `` |
| `TestEventCount` | `INTEGER` | `YES` | `` |
| `TouchRate` | `DOUBLE` | `YES` | `` |
| `HoldRateGivenTouch` | `DOUBLE` | `YES` | `` |
| `BreakRateGivenTouch` | `DOUBLE` | `YES` | `` |
| `RetestRateGivenBreak` | `DOUBLE` | `YES` | `` |
| `DirectionalEdgePct` | `DOUBLE` | `YES` | `` |
| `ValidationQuality` | `DOUBLE` | `YES` | `` |
| `TestQuality` | `DOUBLE` | `YES` | `` |
| `ValidationMarginalLift` | `DOUBLE` | `YES` | `` |
| `TestMarginalLift` | `DOUBLE` | `YES` | `` |
| `TemporalStability` | `DOUBLE` | `YES` | `` |
| `RegimeStability` | `DOUBLE` | `YES` | `` |
| `ComplexityDelta` | `DOUBLE` | `YES` | `` |
| `EffectivenessScore` | `DOUBLE` | `YES` | `` |
| `Recommendation` | `VARCHAR` | `YES` | `` |
| `EvidenceJson` | `VARCHAR` | `YES` | `` |
| `EffectivenessRunId` | `VARCHAR` | `YES` | `` |
| `CompletedAt` | `TIMESTAMP` | `YES` | `` |

### main.vw_Ticker (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `Stock` | `VARCHAR` | `YES` | `` |
| `Company Name` | `VARCHAR` | `YES` | `` |
| `Industry` | `VARCHAR` | `YES` | `` |
| `IndustryCode` | `VARCHAR` | `YES` | `` |
| `Status` | `VARCHAR` | `YES` | `` |
| `MarketCap` | `BIGINT` | `YES` | `` |
| `Shares Outstanding` | `BIGINT` | `YES` | `` |
| `FreeFloat` | `BIGINT` | `YES` | `` |
| `EPS` | `DOUBLE` | `YES` | `` |
| `PE` | `DOUBLE` | `YES` | `` |
| `Book Value` | `DOUBLE` | `YES` | `` |
| `ROA` | `DOUBLE` | `YES` | `` |
| `ROE` | `DOUBLE` | `YES` | `` |

### main.vw_Ticker_Movement_Context (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `MovementContextConfigId` | `BIGINT` | `YES` | `` |
| `MovementContextConfigCode` | `VARCHAR` | `YES` | `` |
| `MovementContextModelVersion` | `VARCHAR` | `YES` | `` |
| `Timeframe` | `VARCHAR` | `YES` | `` |
| `PriceMovementConfigCode` | `VARCHAR` | `YES` | `` |
| `PriceMovementModelVersion` | `VARCHAR` | `YES` | `` |
| `ZigZagConfigCode` | `VARCHAR` | `YES` | `` |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `ContextAsOfDate` | `DATE` | `YES` | `` |
| `ProfileAsOfConfirmedAtDate` | `DATE` | `YES` | `` |
| `CurrentLegAsOfDate` | `DATE` | `YES` | `` |
| `ContextStatus` | `VARCHAR` | `YES` | `` |
| `TrendRegime` | `VARCHAR` | `YES` | `` |
| `TrendQuality` | `VARCHAR` | `YES` | `` |
| `TypicalSwingPct` | `DOUBLE` | `YES` | `` |
| `TypicalSwingBars` | `DOUBLE` | `YES` | `` |
| `TypicalMoveSpeedPctPerBar` | `DOUBLE` | `YES` | `` |
| `MedianATRNormalizedMove` | `DOUBLE` | `YES` | `` |
| `MedianPathEfficiency` | `DOUBLE` | `YES` | `` |
| `MedianDirectionalPersistenceRate` | `DOUBLE` | `YES` | `` |
| `DirectionalBias` | `DOUBLE` | `YES` | `` |
| `ProfileLookbackSwings` | `INTEGER` | `YES` | `` |
| `ConfirmedSwingCount` | `INTEGER` | `YES` | `` |
| `LastSwingSeq` | `BIGINT` | `YES` | `` |
| `LastSwingDirection` | `VARCHAR` | `YES` | `` |
| `LastSwingPct` | `DOUBLE` | `YES` | `` |
| `LastSwingTypicalPct` | `DOUBLE` | `YES` | `` |
| `LastSwingExtentRatio` | `DOUBLE` | `YES` | `` |
| `LastSwingState` | `VARCHAR` | `YES` | `` |
| `CurrentLegDirection` | `VARCHAR` | `YES` | `` |
| `CurrentMovePct` | `DOUBLE` | `YES` | `` |
| `CurrentTradingBars` | `BIGINT` | `YES` | `` |
| `CurrentMoveSpeedPctPerBar` | `DOUBLE` | `YES` | `` |
| `CurrentMoveSpeedRatio` | `DOUBLE` | `YES` | `` |
| `CurrentMoveSpeedState` | `VARCHAR` | `YES` | `` |
| `CurrentLegStatus` | `VARCHAR` | `YES` | `` |
| `CurrentStartPivotSeq` | `BIGINT` | `YES` | `` |
| `CurrentStartPivotDate` | `DATE` | `YES` | `` |
| `CurrentStartPivotPrice` | `DOUBLE` | `YES` | `` |
| `CurrentCandidatePivotType` | `VARCHAR` | `YES` | `` |
| `CurrentCandidatePivotDate` | `DATE` | `YES` | `` |
| `CurrentCandidatePivotPrice` | `DOUBLE` | `YES` | `` |
| `CurrentLastClose` | `DOUBLE` | `YES` | `` |
| `ReversalFromCandidatePct` | `DOUBLE` | `YES` | `` |

### main.vw_Ticker_Movement_Profile (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `PriceMovementConfigCode` | `VARCHAR` | `YES` | `` |
| `PriceMovementModelVersion` | `VARCHAR` | `YES` | `` |
| `Timeframe` | `VARCHAR` | `YES` | `` |
| `PriceMovementConfigId` | `BIGINT` | `YES` | `` |
| `ZigZagConfigId` | `BIGINT` | `YES` | `` |
| `ZigZagConfigCode` | `VARCHAR` | `YES` | `` |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `AsOfConfirmedAtDate` | `DATE` | `YES` | `` |
| `ProfileLookbackSwings` | `INTEGER` | `YES` | `` |
| `ConfirmedSwingCount` | `INTEGER` | `YES` | `` |
| `LastSwingSeq` | `BIGINT` | `YES` | `` |
| `LastSwingDirection` | `VARCHAR` | `YES` | `` |
| `LastSwingPct` | `DOUBLE` | `YES` | `` |
| `MedianUpSwingPct` | `DOUBLE` | `YES` | `` |
| `MedianDownSwingAbsPct` | `DOUBLE` | `YES` | `` |
| `MedianAbsSwingPct` | `DOUBLE` | `YES` | `` |
| `MedianTradingBars` | `DOUBLE` | `YES` | `` |
| `MedianAbsVelocityPctPerBar` | `DOUBLE` | `YES` | `` |
| `MedianATRNormalizedMove` | `DOUBLE` | `YES` | `` |
| `MedianPathEfficiency` | `DOUBLE` | `YES` | `` |
| `MedianDirectionalPersistenceRate` | `DOUBLE` | `YES` | `` |
| `DirectionalBias` | `DOUBLE` | `YES` | `` |
| `MovementCharacter` | `VARCHAR` | `YES` | `` |
| `CalculatedAt` | `TIMESTAMP` | `YES` | `` |

### main.vw_Ticker_OHLC_D (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `Date` | `DATE` | `YES` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `TradingValue` | `BIGINT` | `YES` | `` |
| `TradingValue_Source` | `VARCHAR` | `YES` | `` |
| `TradingValue_IsProxy` | `BOOLEAN` | `YES` | `` |
| `BuyUp_Val` | `BIGINT` | `YES` | `` |
| `BuyUp_Vol` | `BIGINT` | `YES` | `` |
| `SellDown_Val` | `BIGINT` | `YES` | `` |
| `SellDown_Vol` | `BIGINT` | `YES` | `` |
| `ATO_Val` | `BIGINT` | `YES` | `` |
| `ATO_Vol` | `BIGINT` | `YES` | `` |
| `ATC_Val` | `BIGINT` | `YES` | `` |
| `ATC_Vol` | `BIGINT` | `YES` | `` |

### main.vw_Ticker_Price_Movement_Swings (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `PriceMovementConfigCode` | `VARCHAR` | `YES` | `` |
| `PriceMovementModelVersion` | `VARCHAR` | `YES` | `` |
| `Timeframe` | `VARCHAR` | `YES` | `` |
| `PriceMovementConfigId` | `BIGINT` | `YES` | `` |
| `ZigZagConfigId` | `BIGINT` | `YES` | `` |
| `ZigZagConfigCode` | `VARCHAR` | `YES` | `` |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `SwingSeq` | `BIGINT` | `YES` | `` |
| `Direction` | `VARCHAR` | `YES` | `` |
| `StartPivotSeq` | `BIGINT` | `YES` | `` |
| `StartDate` | `DATE` | `YES` | `` |
| `StartPrice` | `DOUBLE` | `YES` | `` |
| `EndPivotSeq` | `BIGINT` | `YES` | `` |
| `EndDate` | `DATE` | `YES` | `` |
| `EndPrice` | `DOUBLE` | `YES` | `` |
| `ConfirmedAtDate` | `DATE` | `YES` | `` |
| `SwingPct` | `DOUBLE` | `YES` | `` |
| `TradingBars` | `INTEGER` | `YES` | `` |
| `CalendarDays` | `INTEGER` | `YES` | `` |
| `VelocityPctPerBar` | `DOUBLE` | `YES` | `` |
| `AvgATRPct` | `DOUBLE` | `YES` | `` |
| `ATRNormalizedMove` | `DOUBLE` | `YES` | `` |
| `PathEfficiency` | `DOUBLE` | `YES` | `` |
| `DirectionalPersistenceRate` | `DOUBLE` | `YES` | `` |
| `CalculatedAt` | `TIMESTAMP` | `YES` | `` |

### main.vw_Ticker_SmartMoney (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `Date` | `DATE` | `YES` | `` |
| `ModelCode` | `VARCHAR` | `YES` | `` |
| `ModelVersion` | `VARCHAR` | `YES` | `` |
| `SmartMoneyScore` | `DOUBLE` | `YES` | `` |
| `ConfidenceScore` | `DOUBLE` | `YES` | `` |
| `MarketState` | `VARCHAR` | `YES` | `` |
| `FactorCoverage` | `DOUBLE` | `YES` | `` |
| `DataQualityStatus` | `VARCHAR` | `YES` | `` |
| `TradeAction` | `VARCHAR` | `YES` | `` |
| `TradeActionConfidenceScore` | `DOUBLE` | `YES` | `` |
| `FreshFlowScore` | `DOUBLE` | `YES` | `` |
| `RelativeLiquidityScore` | `DOUBLE` | `YES` | `` |
| `LiquidityAccelerationScore` | `DOUBLE` | `YES` | `` |
| `RelativeStrengthScore` | `DOUBLE` | `YES` | `` |
| `AccumulationScore` | `DOUBLE` | `YES` | `` |
| `AccumulationMemoryScore` | `DOUBLE` | `YES` | `` |
| `SupplyLockScore` | `DOUBLE` | `YES` | `` |
| `LimitUpScore` | `DOUBLE` | `YES` | `` |
| `TrendScore` | `DOUBLE` | `YES` | `` |
| `DistributionScore` | `DOUBLE` | `YES` | `` |

### main.vw_Ticker_ZigZag_Current (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `ConfigId` | `BIGINT` | `YES` | `` |
| `ConfigCode` | `VARCHAR` | `YES` | `` |
| `ModelVersion` | `VARCHAR` | `YES` | `` |
| `Timeframe` | `VARCHAR` | `YES` | `` |
| `DeviationPct` | `DOUBLE` | `YES` | `` |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `AsOfDate` | `DATE` | `YES` | `` |
| `Direction` | `VARCHAR` | `YES` | `` |
| `StartPivotSeq` | `BIGINT` | `YES` | `` |
| `StartPivotDate` | `DATE` | `YES` | `` |
| `StartPivotPrice` | `DOUBLE` | `YES` | `` |
| `CandidatePivotType` | `VARCHAR` | `YES` | `` |
| `CandidatePivotDate` | `DATE` | `YES` | `` |
| `CandidatePivotPrice` | `DOUBLE` | `YES` | `` |
| `LastClose` | `DOUBLE` | `YES` | `` |
| `CurrentMovePct` | `DOUBLE` | `YES` | `` |
| `ReversalFromCandidatePct` | `DOUBLE` | `YES` | `` |
| `Status` | `VARCHAR` | `YES` | `` |
| `CalculatedAt` | `TIMESTAMP` | `YES` | `` |

### main.vw_Ticker_ZigZag_Pivots (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `ConfigId` | `BIGINT` | `YES` | `` |
| `ConfigCode` | `VARCHAR` | `YES` | `` |
| `ModelVersion` | `VARCHAR` | `YES` | `` |
| `Timeframe` | `VARCHAR` | `YES` | `` |
| `DeviationPct` | `DOUBLE` | `YES` | `` |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `PivotSeq` | `BIGINT` | `YES` | `` |
| `PivotType` | `VARCHAR` | `YES` | `` |
| `PivotDate` | `DATE` | `YES` | `` |
| `PivotPrice` | `DOUBLE` | `YES` | `` |
| `ConfirmedAtDate` | `DATE` | `YES` | `` |
| `ConfirmationPrice` | `DOUBLE` | `YES` | `` |
| `CalculatedAt` | `TIMESTAMP` | `YES` | `` |

### main.vw_Ticker_ZigZag_Swings (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `ConfigId` | `BIGINT` | `YES` | `` |
| `ConfigCode` | `VARCHAR` | `YES` | `` |
| `ModelVersion` | `VARCHAR` | `YES` | `` |
| `Timeframe` | `VARCHAR` | `YES` | `` |
| `DeviationPct` | `DOUBLE` | `YES` | `` |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `SwingSeq` | `BIGINT` | `YES` | `` |
| `Direction` | `VARCHAR` | `YES` | `` |
| `StartPivotSeq` | `BIGINT` | `YES` | `` |
| `StartPivotType` | `VARCHAR` | `YES` | `` |
| `StartDate` | `DATE` | `YES` | `` |
| `StartPrice` | `DOUBLE` | `YES` | `` |
| `EndPivotSeq` | `BIGINT` | `YES` | `` |
| `EndPivotType` | `VARCHAR` | `YES` | `` |
| `EndDate` | `DATE` | `YES` | `` |
| `EndPrice` | `DOUBLE` | `YES` | `` |
| `ConfirmedAtDate` | `DATE` | `YES` | `` |
| `SwingPct` | `DOUBLE` | `YES` | `` |
| `CalendarDays` | `BIGINT` | `YES` | `` |

### main.vw_Ticker_indicators (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `Date` | `DATE` | `YES` | `` |
| `ConfigId` | `BIGINT` | `YES` | `` |
| `ComponentCode` | `VARCHAR` | `YES` | `` |
| `Value` | `DOUBLE` | `YES` | `` |
| `IndicatorCode` | `VARCHAR` | `YES` | `` |
| `Timeframe` | `VARCHAR` | `YES` | `` |
| `WarmupBars` | `INTEGER` | `YES` | `` |

### main.vw_ZigZag_Calibration (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `CalibrationVersion` | `VARCHAR` | `YES` | `` |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `SplitName` | `VARCHAR` | `YES` | `` |
| `DeviationPct` | `DOUBLE` | `YES` | `` |
| `SourceBars` | `BIGINT` | `YES` | `` |
| `PivotCount` | `BIGINT` | `YES` | `` |
| `SwingCount` | `BIGINT` | `YES` | `` |
| `PivotDensityPer100Bars` | `DOUBLE` | `YES` | `` |
| `MedianSwingBars` | `DOUBLE` | `YES` | `` |
| `MedianAbsSwingPct` | `DOUBLE` | `YES` | `` |
| `ShortSwingRate` | `DOUBLE` | `YES` | `` |
| `StructuralValid` | `BOOLEAN` | `YES` | `` |
| `IsEligible` | `BOOLEAN` | `YES` | `` |
| `CalibrationScore` | `DOUBLE` | `YES` | `` |
| `EvaluatedAt` | `TIMESTAMP` | `YES` | `` |

### main.vw_ZigZag_Pilot (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `PilotVersion` | `VARCHAR` | `YES` | `` |
| `CalibrationVersion` | `VARCHAR` | `YES` | `` |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `BaselineDeviationPct` | `DOUBLE` | `YES` | `` |
| `CalibratedDeviationPct` | `DOUBLE` | `YES` | `` |
| `BaselineSwingCount` | `BIGINT` | `YES` | `` |
| `CalibratedSwingCount` | `BIGINT` | `YES` | `` |
| `BaselineShortSwingRate` | `DOUBLE` | `YES` | `` |
| `CalibratedShortSwingRate` | `DOUBLE` | `YES` | `` |
| `BaselineMedianSwingBars` | `DOUBLE` | `YES` | `` |
| `CalibratedMedianSwingBars` | `DOUBLE` | `YES` | `` |
| `BaselineScore` | `DOUBLE` | `YES` | `` |
| `CalibratedScore` | `DOUBLE` | `YES` | `` |
| `Decision` | `VARCHAR` | `YES` | `` |
| `EvaluatedAt` | `TIMESTAMP` | `YES` | `` |

### main.vw_ZigZag_Regime_Evaluation (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `RegimeVersion` | `VARCHAR` | `YES` | `` |
| `CalibrationVersion` | `VARCHAR` | `YES` | `` |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `BaseDeviationPct` | `DOUBLE` | `YES` | `` |
| `StaticSwingCount` | `BIGINT` | `YES` | `` |
| `RegimeSwingCount` | `BIGINT` | `YES` | `` |
| `StaticShortSwingRate` | `DOUBLE` | `YES` | `` |
| `RegimeShortSwingRate` | `DOUBLE` | `YES` | `` |
| `StaticMedianSwingBars` | `DOUBLE` | `YES` | `` |
| `RegimeMedianSwingBars` | `DOUBLE` | `YES` | `` |
| `StaticMedianAbsSwingPct` | `DOUBLE` | `YES` | `` |
| `RegimeMedianAbsSwingPct` | `DOUBLE` | `YES` | `` |
| `StaticStructuralValid` | `BOOLEAN` | `YES` | `` |
| `RegimeStructuralValid` | `BOOLEAN` | `YES` | `` |
| `StaticScore` | `DOUBLE` | `YES` | `` |
| `RegimeScore` | `DOUBLE` | `YES` | `` |
| `LowVolBars` | `BIGINT` | `YES` | `` |
| `NormalBars` | `BIGINT` | `YES` | `` |
| `HighVolBars` | `BIGINT` | `YES` | `` |
| `EvaluatedAt` | `TIMESTAMP` | `YES` | `` |

### main.vw_ZigZag_Ticker_Config (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `CalibrationVersion` | `VARCHAR` | `YES` | `` |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `Timeframe` | `VARCHAR` | `YES` | `` |
| `BaseDeviationPct` | `DOUBLE` | `YES` | `` |
| `SelectionMethod` | `VARCHAR` | `YES` | `` |
| `TrainScore` | `DOUBLE` | `YES` | `` |
| `ValidationScore` | `DOUBLE` | `YES` | `` |
| `TestScore` | `DOUBLE` | `YES` | `` |
| `Status` | `VARCHAR` | `YES` | `` |
| `IsActive` | `BOOLEAN` | `YES` | `` |
| `EffectiveFrom` | `DATE` | `YES` | `` |
| `EffectiveTo` | `DATE` | `YES` | `` |
| `UpdatedAt` | `TIMESTAMP` | `YES` | `` |

### main.vw_raw_stock_eod (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `Date` | `DATE` | `YES` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |
| `Market` | `VARCHAR` | `YES` | `` |
| `Market_Source` | `VARCHAR` | `YES` | `` |
| `Market_IsPointInTime` | `BOOLEAN` | `YES` | `` |
| `ReferencePrice` | `DOUBLE` | `YES` | `` |
| `ReferencePrice_Source` | `VARCHAR` | `YES` | `` |
| `ReferencePrice_IsProxy` | `BOOLEAN` | `YES` | `` |
| `PriceBandRate` | `DOUBLE` | `YES` | `` |
| `PriceBandRuleQuality` | `VARCHAR` | `YES` | `` |
| `CeilingPrice` | `DOUBLE` | `YES` | `` |
| `FloorPrice` | `DOUBLE` | `YES` | `` |
| `LimitUp` | `BOOLEAN` | `YES` | `` |
| `LimitUpStreak` | `BIGINT` | `YES` | `` |
| `LimitDown` | `BOOLEAN` | `YES` | `` |
| `LimitDownStreak` | `BIGINT` | `YES` | `` |

## Indicator metadata snapshots

| DuckDB source | CSV file | Rows |
| --- | --- | ---: |
| `CherryMon`.`main`.`dim_indicator` | `dim_indicator.csv` | 66 |
| `CherryMon`.`main`.`dim_indicator_component` | `dim_indicator_component.csv` | 10 |
| `CherryMon`.`main`.`dim_indicator_config` | `dim_indicator_config.csv` | 27 |
