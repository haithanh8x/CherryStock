# Copilot Instructions for CherryStock

## Priority rules
- Always read this file and the agent instructions in [.github/agents/CherryMon.agent.md](.github/agents/CherryMon.agent.md) before making code changes.
- Follow repository conventions first; do not invent new patterns when an existing one is already used.
- Prefer small, targeted changes and verify them with a real run when possible.

## DuckDB rules
- Always use DuckDBManager for database connections.
- For data access, prefer the pattern below:

```python
def function_name():
    with DuckDBManager() as con:
        relation = (
            <API>
        )
        df = relation.df()
```

- Do not use direct DuckDB.connect() or raw DuckDB.execute() for normal workflow logic.
- Use executeDuckSQL() for SQL script execution and returnSQL() for query helpers.

## Coding rules
- Write explicit column names in SQL queries; avoid `SELECT *`.
- Keep functions focused and reusable.
- Preserve existing project structure and naming conventions.
- After generating or changing code, run a relevant test or real execution before claiming success.
- If a test cannot be run, clearly state the limitation and what still needs verification.

## File locations
- Main project root: [run.py](run.py)
- DuckDB utilities: [Ults/DuckLib.py](Ults/DuckLib.py)
- Agent guidance: [.github/agents/CherryMon.agent.md](.github/agents/CherryMon.agent.md)
- Cấu trúc metadata của DuckDB: [agents/DB_Metadata.md](agents/DB_Metadata.md)
- Các khái niệm về chứng khoán: [agents/StockTerm.md](agents/StockTerm.md)
- Chiến lược chứng khoán: [agents/StockStrategies.md](agents/StockStrategies.md)
- Cấu trúc tài liệu dự án: [agents/project_structured.md](agents/project_structured.md)