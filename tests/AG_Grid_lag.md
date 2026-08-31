# AG Grid Lag — Fix duy nhất: QTabPanels swipeable

## 1. Mục tiêu

Scenario trước đã hoàn tất:

~~~text
Backdrop-filter: FAIL
No significant improvement
Action: REVERT
~~~

Không test lại backdrop-filter trong task này.

Tài liệu này chỉ kiểm tra một nguyên nhân duy nhất:

**QTabPanels đang bật swipeable và có thể xử lý horizontal gesture cùng lúc với AG Grid column resize.**

Nếu bỏ swipeable không cải thiện rõ rệt:

~~~text
REVERT
STOP
~~~

Không tự chuyển sang nguyên nhân tiếp theo.

---

# 2. Phạm vi code

Chỉ được sửa:

~~~text
src/webapp/NiceGUI_chart.py
~~~

Không sửa:

~~~text
src/webapp/NiceGUI_grid.py
src/Presentation/theme.py
src/webapp/NiceGUI_grid_market_tb.py
~~~

Không thay đổi AG Grid config.

---

# 3. Giả thuyết duy nhất

Trong:

~~~text
src/webapp/NiceGUI_chart.py
~~~

main tab panels hiện có dạng:

~~~python
with ui.tab_panels(tabs, value="overview").classes(
    "w-full bg-transparent p-0"
).props("animated keep-alive swipeable"):
~~~

Property:

~~~text
swipeable
~~~

cho phép Quasar QTabPanels nhận horizontal swipe gesture.

AG Grid column resize cũng là horizontal pointer drag.

Interaction path có thể là:

~~~text
pointerdown
→ pointermove
→ AG Grid resize
→ parent QTabPanels swipe gesture processing
→ extra event handling
→ frame drop / drag lag
~~~

Giả thuyết:

**Bỏ swipeable khỏi QTabPanels sẽ làm column resize mượt hơn.**

---

# 4. Thay đổi duy nhất cần thực hiện

Mở:

~~~text
src/webapp/NiceGUI_chart.py
~~~

Tìm:

~~~python
.props("animated keep-alive swipeable")
~~~

Đổi thành:

~~~python
.props("animated keep-alive")
~~~

Không sửa gì khác.

Expected diff:

~~~diff
-.props("animated keep-alive swipeable")
+.props("animated keep-alive")
~~~

---

# 5. Không sửa các event blocker

Trong scenario này phải giữ nguyên:

~~~text
_stop_parent_swipe()
_install_global_tab_swipe_blocker()
~~~

Lý do:

Task này chỉ isolate:

~~~text
swipeable
~~~

Không được đồng thời remove blocker.

Nếu thay cả swipeable và blocker cùng lúc thì không xác định được nguyên nhân nào tạo improvement.

---

# 6. Không làm thêm tối ưu khác

Không:

- sửa backdrop-filter
- remove local pointer blocker
- remove global tab blocker
- tắt persistence timer
- tắt floatingFilter
- tắt animateRows
- đóng Columns Tool Panel
- sửa flex
- sửa width
- đổi AG Grid version
- đổi NiceGUI version
- refactor grid

Sau khi remove swipeable:

~~~text
STOP EDITING
~~~

Chuyển sang test.

---

# 7. Kiểm tra diff trước khi chạy

Chạy:

~~~powershell
cd C:\Github\CherryStock

git diff -- src/webapp/NiceGUI_chart.py
~~~

Expected chỉ có:

~~~diff
-.props("animated keep-alive swipeable")
+.props("animated keep-alive")
~~~

Nếu có thay đổi khác trong file:

- không được tự rollback code của user;
- chỉ xác nhận thay đổi của task này là đúng một dòng;
- không sửa unrelated changes.

---

# 8. Automated test

Chạy test UI/theme liên quan tối thiểu:

~~~powershell
python -m pytest tests/test_theme.py tests/test_rs_ladder.py -v
~~~

Expected:

~~~text
PASS
~~~

Nếu FAIL:

1. đọc exact error;
2. nếu lỗi do thay đổi swipeable: cho phép sửa tối đa một lần;
3. rerun focused test;
4. nếu vẫn FAIL:

~~~text
VERDICT: BLOCKED / REGRESSION
ACTION: REVERT
STOP
~~~

Không đổi sang nguyên nhân khác.

---

# 9. Chạy CherryStock

Chạy:

~~~powershell
python src\webapp\NiceGUI_chart.py
~~~

Mở:

~~~text
http://localhost:8081
~~~

Hard refresh:

~~~text
Ctrl + F5
~~~

Vào:

~~~text
Screener
~~~

Đợi grid load ổn định.

---

# 10. Manual Test A — normal column resize

Chọn một cột ở giữa viewport, ví dụ:

~~~text
Company Name
~~~

hoặc:

~~~text
Industry
~~~

Thực hiện:

1. đặt chuột vào divider của column header;
2. kéo sang trái;
3. kéo sang phải;
4. kéo liên tục khoảng 5 giây;
5. thả chuột;
6. lặp lại 3 lần.

Câu hỏi duy nhất:

~~~text
Resize có mượt hơn rõ rệt không?
~~~

---

# 11. Manual Test B — fast resize

Thực hiện:

1. kéo divider trái/phải nhanh;
2. liên tục khoảng 5 giây;
3. lặp lại 3 lần.

PASS performance nếu:

- column width bám pointer tốt hơn;
- giảm giật rõ;
- giảm delay khi đổi hướng kéo;
- không có visual glitch.

---

# 12. Manual Test C — pinned Ticker

Resize:

~~~text
Ticker
~~~

Expected:

- resize hoạt động;
- pinned state giữ nguyên;
- header và cells align;
- không đổi tab.

---

# 13. Manual Test D — horizontal scrollbar

Kéo horizontal scrollbar của AG Grid.

Expected:

- scrollbar drag bình thường;
- tab không tự chuyển;
- grid không mất interaction;
- không có console error.

---

# 14. Manual Test E — tab click navigation

Click lần lượt:

~~~text
Overview
Screener
Portfolio
R/S
Operations
~~~

Expected:

- click tab vẫn hoạt động;
- tab transition vẫn hoạt động;
- keep-alive vẫn hoạt động;
- Screener state không reset bất thường.

---

# 15. Manual Test F — kiểm tra hành vi swipe

Sau khi bỏ swipeable:

Expected:

~~~text
click tab navigation: PASS
mouse drag trong grid: không đổi tab
horizontal scrollbar: không đổi tab
~~~

Không yêu cầu swipe ngang giữa các tab tiếp tục hoạt động.

Đây là intentional behavior của experiment.

---

# 16. Performance verdict

Chỉ có ba verdict hợp lệ.

## PASS

Chọn PASS khi:

- resize mượt hơn rõ rệt;
- improvement lặp lại ít nhất 3 lần;
- không đổi tab ngoài ý muốn;
- automated tests PASS;
- click tab vẫn hoạt động.

Action:

~~~text
KEEP FIX
STOP
~~~

Kết luận:

~~~text
QTabPanels swipeable is a confirmed AG Grid resize performance contributor.
~~~

---

## FAIL

Chọn FAIL khi:

- resize gần như giống trước;
- lag vẫn rõ;
- improvement không đáng kể.

Action:

~~~text
REVERT FIX
STOP
~~~

Không test event blockers trong task này.

---

## REGRESSION

Chọn REGRESSION khi:

- resize cải thiện;
- nhưng tab/navigation/grid interaction bị lỗi không chấp nhận được.

Action:

~~~text
REVERT FIX
STOP
~~~

Không tự thiết kế workaround mới.

---

# 17. Nếu PASS — commit

Kiểm tra:

~~~powershell
git diff -- src/webapp/NiceGUI_chart.py
~~~

Chỉ stage file này:

~~~powershell
git add src/webapp/NiceGUI_chart.py
git commit -m "perf(ui): disable swipeable main tab panels"
~~~

Sau commit:

~~~text
STOP
~~~

Không tiếp tục optimize AG Grid.

---

# 18. Nếu FAIL hoặc REGRESSION — revert đúng thay đổi này

Nếu working tree không có unrelated edit trong cùng dòng/file, có thể dùng:

~~~powershell
git restore src/webapp/NiceGUI_chart.py
~~~

Nếu file đang có unrelated local changes:

- không dùng git restore toàn file;
- chỉ đổi đúng property trở lại:

~~~python
.props("animated keep-alive swipeable")
~~~

Sau đó:

~~~text
STOP
~~~

---

# 19. Output bắt buộc cho GLM 5.3 Flash

Chỉ trả format sau:

~~~text
AG Grid Swipeable Test
======================

Previous scenario
-----------------
Backdrop-filter: FAIL

Code change
-----------
swipeable removed: YES/NO
Other AG Grid changes: YES/NO

Automated
---------
test_theme.py: PASS/FAIL
test_rs_ladder.py: PASS/FAIL

Manual
------
Normal resize: PASS/FAIL
Fast resize: PASS/FAIL
Ticker resize: PASS/FAIL
Horizontal scrollbar: PASS/FAIL
Tab click navigation: PASS/FAIL
Unexpected tab switch: YES/NO

Performance
-----------
Before: LAG
After: SMOOTHER / SAME / WORSE

Verdict
-------
PASS / FAIL / REGRESSION / BLOCKED

Action
------
KEEP FIX / REVERT FIX / STOP
~~~

Không thêm hypothesis mới.

Không sửa event blocker.

Không sửa persistence.

Không reasoning tiếp sau verdict.

---

# 20. Anti-loop instruction

Sau khi có:

~~~text
PASS
FAIL
REGRESSION
BLOCKED
~~~

thì task đã kết thúc.

Không được:

~~~text
FAIL swipeable
→ test blocker
→ test timer
→ test floatingFilter
~~~

Phải:

~~~text
FAIL swipeable
→ REVERT
→ STOP
~~~

Scenario tiếp theo chỉ được thực hiện bằng task/test-plan riêng.

---

# 21. Definition of Done

## DONE — PASS

- swipeable đã được remove;
- automated tests PASS;
- resize mượt hơn rõ;
- tab click navigation PASS;
- không unexpected tab switch;
- fix được giữ/commit;
- STOP.

## DONE — FAIL

- swipeable đã được test;
- không cải thiện đáng kể;
- change đã revert;
- report FAIL;
- STOP.

## DONE — REGRESSION/BLOCKED

- exact issue đã được ghi;
- change đã revert nếu cần;
- không mở rộng scope;
- STOP.

**Không có bước tiếp theo trong tài liệu này.**
