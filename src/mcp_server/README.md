# CherryMon DuckDB MCP Server

MCP server cho phép AI agent select/update/alter trực tiếp trên local `CherryMon.duckdb`.

## Tools

| Tool | Mô tả |
|---|---|
| `list_tables()` | Liệt kê table/view trong DB |
| `describe_table(table_name)` | Schema cột của table |
| `query(sql, max_rows=100)` | Chỉ nhận SELECT/WITH (read-only connection) |
| `execute(sql, confirm)` | INSERT/UPDATE/DELETE/ALTER/CREATE/DROP — bắt buộc `confirm=true` mới thực thi |
| `table_stats(table_name)` | Số dòng của table |

## Chạy server

```powershell
C:/Program1/Python/Python313/python.exe src/mcp_server/duckdb_mcp.py
```

## Đăng ký trong VS Code (Copilot MCP)

Thêm vào `.vscode/mcp.json`:

```json
{
  "servers": {
    "cherrymon-duckdb": {
      "command": "C:/Program1/Python/Python313/python.exe",
      "args": ["c:/Github/CherryStock/src/mcp_server/duckdb_mcp.py"]
    }
  }
}
```

## Lưu ý

- Server dùng `DuckDBConnectionFactory` của project nên tôn trọng `LOCAL_DB_PATH` / MotherDuck config.
- Read query dùng read-only connection; write dùng writer connection ngắn hạn — không giữ lock file DB.
- DuckDB chỉ cho 1 process mở write connection: nếu agent đang chạy cùng lúc với run.py có thể gặp file-lock error.
