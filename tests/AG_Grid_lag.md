# AG Grid Lag — Fix duy nhất: backdrop-filter

## 1. Mục tiêu

Tài liệu này chỉ xử lý một nguyên nhân duy nhất:

**backdrop-filter: blur(12px) trên card chứa AG Grid có thể làm browser repaint/composite nặng khi resize column.**

Không phân tích hoặc sửa bất kỳ nguyên nhân nào khác.

Không sửa:

- QTabPanels swipeable
- mouse/pointer event blocker
- persistence timer
- Columns Tool Panel
- floatingFilter
- animateRows
- AG Grid version
- NiceGUI version

Nếu fix backdrop-filter không cải thiện rõ rệt: **REVERT và STOP**.

Không tự chuyển sang giả thuyết khác.

---

# 2. Phạm vi code

Chỉ được sửa hai file:

~~~text
src/Presentation/theme.py
src/webapp/NiceGUI_chart.py
~~~

Không sửa src/webapp/NiceGUI_grid.py.

---

# 3. Nguyên nhân đang kiểm tra

Trong:

~~~text
src/Presentation/theme.py
~~~

hiện có:

~~~css
.dashboard-card {
    overflow: hidden;
    backdrop-filter: blur(12px);
}
~~~

Stock Screener được render trong card dùng dashboard-card.

Khi resize column:

~~~text
pointermove
→ AG Grid đổi width
→ browser layout lại header/cells
→ repaint
→ composite
→ backdrop-filter blur phải composite lại vùng card lớn
~~~

Giả thuyết duy nhất:

**Bỏ blur riêng khỏi card chứa Stock Screener sẽ làm column resize mượt hơn.**

---

# 4. Thực hiện fix

## Bước 1 — thêm class no-blur cho data grid

Mở:

~~~text
src/Presentation/theme.py
~~~

Trong build_nicegui_css(), ngay sau:

~~~css
.dashboard-card {
    overflow: hidden;
    backdrop-filter: blur(12px);
}
~~~

thêm:

~~~css
.dashboard-data-grid-card {
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
}
~~~

Kết quả:

~~~css
.dashboard-card {
    overflow: hidden;
    backdrop-filter: blur(12px);
}

.dashboard-data-grid-card {
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
}
~~~

Không xóa blur khỏi dashboard-card.

Lý do:

- các card khác giữ visual hiện tại;
- chỉ card chứa grid bỏ blur;
- thay đổi nhỏ và dễ rollback.

---

## Bước 2 — áp class cho Stock Screener

Mở:

~~~text
src/webapp/NiceGUI_chart.py
~~~

Tìm:

~~~python
def market_tab_content() -> None:
~~~

Tìm dòng:

~~~python
with ui.card().classes(card_classes("p-4 w-full")):
~~~

Đổi thành:

~~~python
with ui.card().classes(
    card_classes("p-4 w-full dashboard-data-grid-card")
):
~~~

Chỉ áp class này cho Stock Screener.

Không thêm class vào:

- Overview
- Portfolio
- R/S
- metric cards
- chart cards khác

---

# 5. Dừng sửa code

Sau hai thay đổi trên, không sửa gì thêm.

Đặc biệt không:

- bỏ swipeable
- sửa _stop_parent_swipe()
- sửa _install_global_tab_swipe_blocker()
- tắt ui.timer(1.5, persist_state)
- tắt floatingFilter
- tắt animateRows
- đóng Columns Tool Panel
- sửa width/flex
- refactor AG Grid

Task này chỉ kiểm tra backdrop-filter.

---

# 6. Kiểm tra diff

Chạy:

~~~powershell
cd C:\Github\CherryStock
git diff -- src/Presentation/theme.py src/webapp/NiceGUI_chart.py
~~~

Expected chỉ có:

1. thêm dashboard-data-grid-card
2. thêm class đó vào Stock Screener card

Nếu có thay đổi khác, rollback thay đổi khác trước khi test.

---

# 7. Automated test

Chạy:

~~~powershell
python -m pytest tests/test_theme.py -v
~~~

Expected:

~~~text
PASS
~~~

Nếu FAIL do thay đổi này:

- sửa lỗi trong đúng hai file trên;
- chưa được chạy sang giả thuyết khác.

---

# 8. Chạy CherryStock

Chạy:

~~~powershell
python src\webapp\NiceGUI_chart.py
~~~

Mở:

~~~text
http://localhost:8081
~~~

Vào tab:

~~~text
Screener
~~~

Hard refresh:

~~~text
Ctrl + F5
~~~

---

# 9. Manual test

## Test A — resize column bình thường

Dùng một column như:

~~~text
Company Name
~~~

hoặc:

~~~text
Industry
~~~

Thực hiện:

1. đặt chuột vào divider bên phải header
2. kéo sang trái
3. kéo sang phải
4. kéo qua lại liên tục khoảng 5 giây
5. lặp lại 3 lần

Chỉ trả lời câu hỏi:

**Resize có mượt hơn rõ rệt so với trước fix không?**

---

## Test B — resize nhanh

1. kéo divider nhanh trái/phải
2. thực hiện khoảng 5 giây
3. lặp lại 3 lần

PASS nếu:

- width bám theo con trỏ tốt hơn
- giảm giật nhìn thấy bằng mắt
- không có lỗi visual mới

---

## Test C — resize Ticker

Resize column:

~~~text
Ticker
~~~

Expected:

- resize hoạt động
- pinned state giữ nguyên
- header và cells align

---

## Test D — horizontal scroll

Kéo horizontal scrollbar.

Expected:

- scroll bình thường
- không xuất hiện vùng trắng
- không xuất hiện vùng transparent bất thường

---

## Test E — visual

Kiểm tra Stock Screener:

- background đúng
- border đúng
- text đúng
- grid đúng theme
- layout không thay đổi

Không yêu cầu Stock Screener giữ hiệu ứng glass blur.

---

# 10. Kết luận

Chỉ có ba verdict hợp lệ.

## PASS

Chọn PASS khi:

- resize mượt hơn rõ rệt
- improvement lặp lại được ít nhất 3 lần
- test_theme.py PASS
- không có visual regression

Action:

~~~text
KEEP FIX
~~~

Kết luận:

~~~text
backdrop-filter is a confirmed performance contributor
~~~

---

## FAIL

Chọn FAIL khi:

- resize gần như không thay đổi
- improvement không rõ
- lag vẫn như trước

Action:

~~~text
REVERT FIX
STOP
~~~

Không thử nguyên nhân khác.

---

## REGRESSION

Chọn REGRESSION khi:

- resize có thể mượt hơn
- nhưng UI/theme/layout bị lỗi

Action:

- chỉ sửa cách scope CSS no-blur
- không chuyển sang nguyên nhân khác

---

# 11. Nếu PASS — commit

Chạy:

~~~powershell
git status
git diff
~~~

Expected chỉ có:

~~~text
src/Presentation/theme.py
src/webapp/NiceGUI_chart.py
~~~

Commit:

~~~powershell
git add src/Presentation/theme.py src/webapp/NiceGUI_chart.py
git commit -m "perf(grid): disable backdrop blur for stock screener"
~~~

---

# 12. Nếu FAIL — rollback

Chạy:

~~~powershell
git restore src/Presentation/theme.py
git restore src/webapp/NiceGUI_chart.py
git status
~~~

Sau đó dừng.

Không mở rộng task.

---

# 13. Output bắt buộc cho GLM 5.3 Flash

Chỉ trả đúng format này.

~~~text
AG Grid Backdrop Filter Test
============================

Code change
-----------
dashboard-data-grid-card added: YES/NO
Stock Screener uses class: YES/NO

Automated
---------
tests/test_theme.py: PASS/FAIL

Manual
------
Normal resize: PASS/FAIL
Fast resize: PASS/FAIL
Ticker resize: PASS/FAIL
Horizontal scroll: PASS/FAIL
Visual regression: PASS/FAIL

Performance
-----------
Before: LAG
After: SMOOTHER / SAME / WORSE

Verdict
-------
PASS / FAIL / REGRESSION

Action
------
KEEP FIX / REVERT FIX
~~~

Không thêm reasoning dài.

Không đề xuất nguyên nhân tiếp theo.

Không sửa file khác.

---

# 14. Definition of Done

## DONE — PASS

- dashboard-data-grid-card đã được thêm
- chỉ Stock Screener dùng class này
- tests/test_theme.py PASS
- resize mượt hơn rõ
- không regression
- fix được commit

## DONE — FAIL

- backdrop-filter đã được test
- không cải thiện rõ
- experiment đã revert
- report FAIL
- task dừng

**Không có bước tiếp theo trong tài liệu này.**
