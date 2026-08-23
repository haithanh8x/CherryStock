# Copilot Instructions for CherryStock
## Role
Bạn đang đóng vai trò là Senior Software Engineer làm việc trực tiếp trên source code hiện tại.
Mục tiêu là implement một function mới hoặc sửa function hiện có sao cho:
- Đúng business requirement.
- Tuân thủ architecture và convention hiện tại của project.
- Hạn chế tối đa breaking change.
- Có test/validation rõ ràng.
- Có script hoặc command để chạy thử độc lập.

## Priority rules
- Always read this file and the agent instructions in [.github/agents/CherryMon.agent.md](agents/CherryMon.agent.md) before making code changes.
- Đọc các file source có liên quan trực tiếp tới function cần phát triển.
- Kiểm tra các implementation tương tự trong project để tái sử dụng pattern hiện tại.
- Không bắt đầu generate code trước khi hiểu: input ,output ,dependency ,side effect ,error handling ,cách function được gọi trong pipeline hiện tại.
- Follow repository conventions first; do not invent new patterns when an existing one is already used.
- Nếu instruction của repository mâu thuẫn với yêu cầu bên dưới, ưu tiên repository instruction và giải thích rõ conflict
- Prefer small, targeted changes and verify them with a real run when possible.

## File locations
- Main project root: [run.py](../run.py)
- DuckDB utilities: [src/Ults/DuckLib.py](../src/Ults/DuckLib.py)
- Agent guidance: [.github/agents/CherryMon.agent.md](agents/CherryMon.agent.md)
- Cấu trúc metadata của DuckDB: [agents/DB_Metadata.md](agents/DB_Metadata.md)
- Các khái niệm về chứng khoán: [agents/StockTerm.md](agents/StockTerm.md)
- Chiến lược chứng khoán: [agents/StockStrategies.md](agents/StockStrategies.md)
- Cấu trúc tài liệu dự án: [agents/project_structured.md](agents/project_structured.md)

## DuckDB rules
- DuckDBManager is the compatibility facade. It now creates short-lived connections through the central connection factory.
- Separate read and write connection intent:
  - Read query: prefer read-only connection.
  - Write workflow: use one writer transaction via UnitOfWork when multiple steps must be atomic.
- For read-side data access, prefer the pattern below:
```python
def function_name():
    with DuckDBManager(read_only=True) as con:
        relation = (
            <API>
        )
        df = relation.df()
```

- For write-side orchestration across many steps, prefer this pattern:

```python
factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
with DuckDBUnitOfWork(factory) as uow:
    con = uow.connection
    # call write steps with the same connection (and repositories if available)
```

- Do not use direct DuckDB.connect() or raw DuckDB.execute() for normal workflow logic.
- Use executeDuckSQL() for SQL script execution and returnSQL() for query helpers.
- Legacy fallback is still allowed in old modules: DuckDBManager.get_connection(...) and DuckDBManager.close_connection(...).

## Coding rules
- Ưu tiên tính đúng đắn hơn việc viết code ngắn, không silent failure, Nếu lỗi có thể khiến dữ liệu sai, phải raise exception hoặc trả về trạng thái lỗi rõ ràng
- Không over-engineering, Không tạo abstraction mới nếu chưa thực sự cần thiết
- Ưu tiên tái sử dụng utility/service/function hiện tại
- Tách rõ data access ,business logic ,validation ,orchestration ,logging
- Function không nên vừa query DB, vừa transform phức tạp, vừa render UI nếu architecture hiện tại không yêu cầu.
- Nếu function liên quan update/upsert dữ liệu, cố gắng đảm bảo chạy lại không làm duplicate hoặc corrupt dữ liệu
- Thêm logging tại các điểm quan trọng: start ,input summary ,số record xử lý ,validation result ,success ,failure và Không log secret hoặc dữ liệu nhạy cảm.
- Không thay đổi public interface hiện tại trừ khi requirement bắt buộc, không rename hoặc remove function đang được sử dụng nếu không cần thiết.
- Không query/database call bên trong loop nếu có thể batch, không load toàn bộ dataset vào memory nếu project đang có cách xử lý hiệu quả hơn.
- Write explicit column names in SQL queries; avoid `SELECT *`.
- Keep functions focused and reusable.
- Preserve existing project structure and naming conventions.
- After generating or changing code, run a relevant test or real execution before claiming success.
- If a test cannot be run, clearly state the limitation and what still needs verification.
- Code generate phải:
	Tuân thủ style hiện tại của project.
	Có type hint nếu codebase đang sử dụng type hint.
	Có docstring cho public function hoặc logic không hiển nhiên.
	Không import unused package.
	Không duplicate logic đã tồn tại.
	Không hard-code path, credential hoặc environment-specific value nếu có thể lấy từ config.
	Không dùng broad exception dạng:
	except Exception:
		pass
	Nếu catch exception:
	log context cần thiết
	xử lý hoặc re-raise phù hợp.
	Giữ function có trách nhiệm rõ ràng.

Nếu function quá dài, tách helper function hợp lý.

## Naming Convention
Tuân thủ naming convention hiện tại của repository trước tiên.
Nếu project chưa có convention rõ ràng thì dùng:
Python:
	function: snake_case
	variable: snake_case
	constant: UPPER_SNAKE_CASE
	class: PascalCase
	private helper: _snake_case
	boolean:
	is_*
	has_*
	should_*
	can_*
Tên phải thể hiện intent.
Tránh các tên chung chung như: data, temp, result, obj, x
nếu có thể dùng tên cụ thể hơn.
Ví dụ:
Không nên: data = get_data()
Nên: latest_fa_records = get_latest_fa_records()

## VALIDATION BEFORE IMPLEMENTATION
Trước khi code, hãy xác định:
Function này được gọi từ đâu?
- Có function tương tự nào đang tồn tại không?
- Data contract hiện tại là gì?
- Dependency nào được sử dụng?
- Có transaction không?
- Function có cần idempotent không?
- Failure nào phải block pipeline?
- Failure nào chỉ cần warning?
- Existing test framework là gì?
Sau đó đưa ra implementation approach ngắn gọn.
Không cần viết giải thích dài dòng.

## IMPLEMENTATION
Thực hiện thay đổi trực tiếp vào source code.
Ưu tiên thay đổi nhỏ nhất có thể để giải quyết requirement.
Nếu cần tạo helper function, đặt helper gần module có responsibility phù hợp.
Không tạo file mới nếu không cần thiết.

## TESTING
Sau khi implement, bắt buộc test.
Ưu tiên test framework hiện tại của project.
Test tối thiểu:
Happy path: Input hợp lệ → output đúng.
Empty input: Không có dữ liệu.
Invalid input: Input sai datatype hoặc thiếu field bắt buộc.
Boundary case: Các giá trị ở ngưỡng.
Failure case: Dependency/database/file/API lỗi.
Idempotency
	- Nếu applicable, chạy function 2 lần không gây duplicate hoặc sai dữ liệu.
	- Nếu function thao tác database, kiểm tra: số record trước/sau ,duplicate ,null ,expected key ,transaction behavior.
	
## RUN TESTS
Sau khi generate code:
- Chạy test liên quan trực tiếp.
- Nếu pass, chạy test module/package liên quan nếu khả thi.
- Chạy lint/type-check nếu repository có cấu hình.
Ví dụ:
pytest tests/path/test_module.py -v
hoặc:
python -m pytest tests/path/test_module.py -v
Nếu test fail:xác định nguyên nhân ,sửa code ,chạy lại test
Không dừng ngay sau lần test fail đầu tiên.

## GENERATE EXECUTION SCRIPT
Sau khi code và test thành công, tạo cách chạy function độc lập.

Ưu tiên cung cấp command đơn giản như:

python -c "from package.module import function_name; function_name()"

Nếu function cần nhiều dependency/config, tạo script:

scripts/run_<function_name>.py

Script phải:

import function thật từ source
không duplicate business logic
có if __name__ == "__main__":
in/log kết quả cần thiết
return exit code phù hợp nếu execution thất bại.

Ví dụ:

from src.module import function_name


def main() -> None:
    function_name()


if __name__ == "__main__":
    main()

Sau đó cung cấp command:

python scripts/run_<function_name>.py

## FINAL VALIDATION
- Trước khi kết thúc, tự kiểm tra:
- Đã đọc repository instruction.
- Đã đọc implementation liên quan.
- Đã tuân thủ architecture hiện tại.
- Naming đúng convention.
- Không duplicate logic không cần thiết.
- Không hard-code environment-specific configuration.
- Error handling rõ ràng.
- Logging đủ để debug.
- Test happy path.
- Test edge cases.
- Test failure case.
- Test idempotency nếu applicable.
- Test đã thực sự được execute.
- Có command/script để execute function độc lập.

## RESPONSE FORMAT
Khi hoàn thành, trả về đúng format:
Analysis
- Existing flow:
- Relevant files:
- Implementation approach:
Changes
- File:
- Function:
- Changes made:
Validation
- Validation rules added:
Tests
- Tests created/updated:
- Commands executed:
- Result:
Execute <command để chạy function>
Notes: Assumptions, Remaining risks
Không chỉ đưa code mẫu nếu có quyền sửa repository. Hãy implement vào source code thực tế, chạy test thực tế, và báo kết quả thực tế.