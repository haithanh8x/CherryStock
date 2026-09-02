# CherryMon Architecture Constitution

## Purpose
File này định nghĩa các nguyên tắc kiến trúc ổn định của CherryStock/CherryMon. Chi tiết operational rule phải nằm trong domain instructions tương ứng để tránh instruction drift.

Repository instructions luôn được đọc trước khi chỉnh sửa code.

## Project responsibilities
- `src/Datafile` / data-loading modules: chuẩn hóa dữ liệu nguồn để nạp vào DuckDB.
- `src/Amibroker`: Amibroker explore/analysis/backtest/AFL integration.
- `src/calcEngine`: technical/composite/net-flow calculations.
- `src/Chart`: chart preparation/rendering.
- `src/CrawlStock`: external market-data ingestion.
- `src/DuckDB`: DuckDB SQL/schema/view scripts.
- `src/Orchestrator`: orchestration/scheduling/invocation.
- `src/Telegram`: notification/alert integrations.
- `src/Ults`: shared utilities such as DuckLib, Timing and DataValidation.
- `run.py`: primary project execution/orchestration entry point.
- `scripts/`: focused initialization, migration and standalone execution scripts.
- `tests/`: automated validation.

When the physical repository differs from this high-level map, follow the actual current structure and update architecture documentation if the difference is intentional.

## Dependency principles
1. UI/chart code should consume prepared data contracts rather than embed complex database/business logic.
2. Orchestration coordinates workflows; it should not duplicate domain calculations.
3. Shared database access goes through project database utilities/repositories, never ad-hoc connection patterns.
4. Validation is read-oriented and separate from persistence/orchestration side effects.
5. Source-of-Truth objects must be explicit; downstream consumers should use the declared public view/contract instead of internal persistence tables when one exists.
6. New cross-cutting architecture decisions should be captured in `docs/adr/`.

## Agent Harness routing

The executable router is `../copilot-instructions.md`. The canonical role, outcome, handoff and material map is `docs/architecture/agent-harness/README.md`.

- Requirement readiness and backlog → `BusinessAnalyst.agent.md`
- Architecture/design readiness → `SolutionArchitect.agent.md`
- Concrete indicator lifecycle → `Indicator_Management.agent.md`
- Clear general implementation → `GeneralCoding.agent.md`
- Independent validation verdict → `TestEngineer.agent.md`

The default repository agent orchestrates each request. Do not require every task to pass through every role.

## Domain instruction routing
For detailed rules, use the domain owner file:

- DuckDB / SQL / transactions / data quality → `../instructions/database.instructions.md`
- Indicator Engine → `../instructions/indicators.instructions.md`
- Charts → `../instructions/chart.instructions.md`
- Crawlers → `../instructions/crawler.instructions.md`
- Testing / execution validation → `../instructions/testing.instructions.md`

Do not duplicate those rules here.

## Naming principles
DuckDB object prefixes:
- `raw_*`: raw/source datasets.
- `cal_*`: calculated/internal persistence datasets.
- `dim_*`: dimensions/configuration/master data.
- `vw_*`: public/query-oriented views.
- `sys_*`: operational/audit/monitoring data, not market-data source of truth.

Indicator output naming follows:

```text
<INDICATOR><PERIOD>_<TIMEFRAME>
```

where timeframe suffix is:
- `_D` Daily
- `_W` Weekly
- `_M` Monthly

Examples: `MA20_D`, `EMA50_W`, `RSI14_M`.

## Key CherryMon data contracts
Important objects include:
- `"CherryMon"."main"."raw_stock_eod"`
- `"CherryMon"."main"."raw_stock_fa"`
- `"CherryMon"."main"."raw_stock_index"`
- `"CherryMon"."main"."dimCalendar"`
- `"CherryMon"."main"."vw_ACCCNNTD_Price"`
- `"CherryMon"."main"."sys_data_quality_audit"`

Indicator Engine contracts:
- `dim_indicator`
- `dim_indicator_component`
- `dim_indicator_config`
- `vw_Indicator_config` — configuration Single Source of Truth.
- `cal_indicator_values` — internal long-format persistence.
- `vw_Ticker_indicators` — public/calculated indicator Single Source of Truth.

For current database context, read `docs/reference/DB_Metadata.md` first for schema, then load `docs/reference/dim_indicator.parquet`, `docs/reference/dim_indicator_component.parquet` and `docs/reference/dim_indicator_config.parquet` for actual indicator dimension values. Join the snapshots by `IndicatorCode`; use the indicator architecture documents for behavioral rules.

## Knowledge architecture
CherryStock repository Markdown is the engineering knowledge Single Source of Truth.

```text
GitHub repository
    ├── .github/               AI governance
    ├── docs/                  requirements / architecture / ADR / development knowledge
    ├── src/                   implementation
    ├── tests/                 validation
    └── scripts/               execution/migration utilities
```

VS Code and Obsidian must open the same local repository. Obsidian is a navigation/knowledge-graph interface, not a second documentation store.

Start knowledge navigation from `docs/00_HOME.md`.