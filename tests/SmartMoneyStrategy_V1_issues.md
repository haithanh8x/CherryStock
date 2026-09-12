# SmartMoneyStrategy V1 — Runbook Execution Issues Export

- **Runbook:** `docs/runbook/SmartMoneyStrategy_V1.md`
- **Requirement:** `REQ-0026`
- **Execution date:** 2026-09-12
- **Executor:** Local TestEngineer agent (GitHub Copilot)
- **Final verdict:** `PASS` / Action: `KEEP`
- **Purpose:** Export cho ChatGPT cập nhật runbook lần sau.

---

## Issue 1 — Integration test fail ngay ở bước collect (import sai convention)

**Bước:** Phase 4 — `python -m pytest tests\test_smart_money_integration.py -v`

**Hiện tượng:**

```text
ModuleNotFoundError: No module named 'calcEngine'
```

**Nguyên nhân gốc:**

- `tests/test_smart_money_integration.py` dùng import không có prefix `src.`:

```python
from calcEngine.smartMoneyScore import ...
from cherrystock.infrastructure... import ...
```

- Convention thực tế của repo (không có `conftest.py`, không có `pythonpath` trong `[tool.pytest.ini_options]` của `pyproject.toml`) là **bắt buộc prefix `src.`**:

```python
from src.calcEngine.smartMoneyScore import ...
from src.cherrystock.infrastructure... import ...
```

- Runbook không có bước kiểm tra import convention của test trước khi chạy, và không có hướng xử lý cho lỗi **collection error** (khác với test FAIL — runbook chỉ định nghĩa FAIL/REGRESSION, không định nghĩa lỗi collect).

**Đã xử lý:** FIX ONCE (sửa 2 dòng import) → retest PASS.

**Đề xuất cập nhật runbook:**

1. Thêm vào Phase 4 (hoặc Phase 2): bước pre-check "test module phải import được" và quy ước import `src.` prefix.
2. Định nghĩa rõ: lỗi collection/import ≠ REGRESSION của strategy; phân loại thành FAIL với FIX ONCE budget riêng.
3. Hoặc sửa tận gốc: thêm `pythonpath = ["src"]` (hoặc `["."]`) vào `[tool.pytest.ini_options]` trong `pyproject.toml` để cả hai kiểu import đều chạy được.

---

## Issue 2 — Preflight runner fail khi chạy trực tiếp (thiếu PYTHONPATH)

**Bước:** Phase 6 — `python scripts\run_smart_money_preflight.py`

**Hiện tượng:**

```text
ModuleNotFoundError: No module named 'src'
```

**Nguyên nhân gốc:**

- Script dùng `from src.Ults.DuckLib import DuckDBManager` nhưng khi chạy `python scripts\...py`, Python đặt `scripts/` làm `sys.path[0]`, không phải repo root.
- Repo không cài package ở chế độ editable trong env này (hoặc `src` layout không tự resolve), nên mọi script chạy trực tiếp đều phụ thuộc biến môi trường `PYTHONPATH`.
- Runbook ghi lệnh chạy trực tiếp mà không ghi rõ yêu cầu `PYTHONPATH` — lệnh trong runbook **không reproducible như đã viết**.

**Đã xử lý:** chạy lại với `$env:PYTHONPATH="C:\Github\CherryStock"` → PASS. (Không tính là FIX vì không sửa code.)

**Đề xuất cập nhật runbook:**

1. Chuẩn hóa mọi lệnh `python scripts\...` trong runbook thành một trong hai dạng:
   - chạy từ repo root với `PYTHONPATH` set sẵn, hoặc
   - dùng `python -m scripts.run_smart_money_preflight` (nếu `scripts` là package), hoặc
   - thêm wrapper `.ps1` chuẩn.
2. Hoặc sửa tận gốc: thêm `pyproject.toml` config / `src` editable install để script chạy trực tiếp không cần PYTHONPATH.

---

## Issue 3 — Agent tự lặp lệnh không cần thiết (anti-loop violation, không phải lỗi runbook)

**Hiện tượng:** Trong quá trình chẩn đoán Issue 1, agent lặp lại cùng một lệnh `Select-String ... "sys.path"` nhiều lần liên tiếp dù kết quả không đổi.

**Nguyên nhân gốc:** Hành vi của agent thực thi, không phải thiếu sót của runbook — nhưng runbook chưa có bước "chẩn đoán import error" có cấu trúc để agent không phải dò dần.

**Đề xuất cập nhật runbook:** Thêm mục "Chẩn đoán lỗi test" ngắn gọn:

- Bước 1: đọc traceback, xác định module import fail.
- Bước 2: so sánh import với 1 test file PASS cùng thư mục (convention check).
- Bước 3: sửa đúng 1 lần, retest đúng 1 lần.

→ Giúp agent đi thẳng vào fix thay vì dò tìm lặp lại.

---

## Issue 4 (nhỏ) — Metadata export cần PYTHONPATH tương tự

**Bước:** Phase 8 — `python -c "from src.Ults import DuckLib; ..."`

Lệnh này chạy OK vì `python -c` dùng cwd làm `sys.path[0]` (khác với `python scripts\x.py`). Không fail, nhưng **không nhất quán** với Issue 2 — dễ gây nhầm cho agent lần sau.

**Đề xuất:** Ghi chú trong runbook sự khác biệt này (`python -c` OK từ repo root, `python scripts\x.py` cần PYTHONPATH), hoặc chuẩn hóa cả hai theo cùng một cách chạy.

---

## Tóm tắt

| # | Bước | Loại lỗi | Nguyên nhân chính | Fix đề xuất |
|---|---|---|---|---|
| 1 | Phase 4 | Collection error | Test import thiếu prefix `src.`; runbook không có convention check | Sửa import hoặc thêm `pythonpath` vào pytest config |
| 2 | Phase 6 | ModuleNotFoundError | Script chạy trực tiếp thiếu `PYTHONPATH`; lệnh runbook không reproducible | Chuẩn hóa cách chạy script trong runbook |
| 3 | Phase 4 (diag) | Agent loop | Không có runbook chẩn đoán có cấu trúc | Thêm mục chẩn đoán lỗi test |
| 4 | Phase 8 | Không nhất quán | `python -c` vs `python script.py` khác `sys.path` | Ghi chú rõ trong runbook |

**Trạng thái cuối:** Verdict PASS / Action KEEP — các issue trên không ảnh hưởng kết quả validation, chỉ ảnh hưởng khả năng reproducible của runbook.
