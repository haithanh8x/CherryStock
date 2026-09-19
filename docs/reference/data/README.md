# ChatGPT Data Export Contract

## Purpose

`docs/reference/data/**` is the canonical Git-tracked handoff area for bounded CherryStock
data extracts that ChatGPT, TestEngineer or another AI-assisted workflow must inspect.

This directory does not replace DuckDB tables/views or other runtime Source of Truth.

## Mandatory Rule

When CherryStock exports a file specifically so ChatGPT can read, compare, reconcile,
diagnose or validate the result, the file MUST be written under:

```text
docs/reference/data/
```

Do not use ad-hoc handoff paths such as:

```text
export/
tmp/
data/
repository root
Desktop
Downloads
```

## Recommended Layout

Use domain and subject subfolders:

```text
docs/reference/data/
├── zigzag/
│   └── mwg/
├── smart_money/
│   └── mwg/
├── indicators/
└── data_quality/
```

Example ZigZag reconciliation package:

```text
docs/reference/data/zigzag/mwg/
├── MWG_OHLC_202605_202609.csv
├── MWG_ZigZag_Pivots_202605_202609.csv
├── MWG_ZigZag_Swings_202605_202609.csv
└── MWG_ZigZag_Reconciliation.csv
```

## Format Rules

- Prefer CSV with headers for tabular data.
- Use UTF-8.
- Use ISO dates (`YYYY-MM-DD`) where practical.
- Preserve source column names when they are part of the contract.
- Include config/model identity when a result depends on configuration.
- Keep the extract to the smallest ticker/date/config scope sufficient for the review.
- Use deterministic descriptive filenames.
- A date or date range SHOULD appear in historical evidence filenames.

## Git / Ignore Behavior

The repository globally ignores common data formats such as `*.csv` and `*.json`, but
`docs/reference/**` is explicitly unignored in `.gitignore`. Therefore files placed under
this directory can be added and synchronized to GitHub.

## Security

Never place the following here:

- API keys;
- tokens;
- passwords;
- connection secrets;
- private credentials;
- personal/sensitive data that is not explicitly required and safe to commit.

## Source-of-Truth Rule

Files in this directory are reproducible evidence/snapshots.

For current runtime state, prefer the authoritative DuckDB table/view or application contract.
When evidence becomes stale, regenerate it rather than treating the snapshot as live data.
